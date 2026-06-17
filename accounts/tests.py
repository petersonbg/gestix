from datetime import timedelta
from decimal import Decimal
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.utils import OperationalError
from django.http import HttpResponse
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import path, reverse
from django.utils import timezone
from django.views import View

from administracao.models import ConfiguracaoSistema
from caixa.models import Caixa
from clientes.models import Cliente
from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from .middleware import ULTIMA_ATIVIDADE_SESSAO
from .models import LogAtividade, PerfilUsuario
from .permissions import (
    PerfilRequiredMixin, perfil_required, usuario_eh_admin, usuario_eh_estoquista,
    usuario_eh_gerente, usuario_eh_vendedor, usuario_tem_perfil,
)
from .utils import registrar_log


@perfil_required(['ADMINISTRADOR'])
def view_decorator_admin(request):
    return HttpResponse('decorator ok')


class ViewMixinAdmin(PerfilRequiredMixin, View):
    perfis_permitidos = ['ADMINISTRADOR', 'GERENTE']

    def get(self, request):
        return HttpResponse('mixin ok')


urlpatterns = [
    path('teste/decorator-admin/', view_decorator_admin, name='teste_decorator_admin'),
    path('teste/mixin-admin/', ViewMixinAdmin.as_view(), name='teste_mixin_admin'),
    path('dashboard/', lambda request: HttpResponse('dashboard'), name='dashboard'),
    path('accounts/login/', lambda request: HttpResponse('login'), name='login'),
    path('acesso-negado/', lambda request: HttpResponse('acesso negado'), name='acesso_negado'),
]


class LogoutInatividadeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-timeout',
            password='senha',
            email='timeout@gestix.test',
        )
        self.client.login(username='admin-timeout', password='senha')

    def definir_ultima_atividade(self, instante):
        session = self.client.session
        session[ULTIMA_ATIVIDADE_SESSAO] = instante.timestamp()
        session.save()

    def test_backend_aplica_tempo_configurado_em_minutos(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 30
        configuracao.save()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(ULTIMA_ATIVIDADE_SESSAO, self.client.session)
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 1798)
        self.assertLessEqual(self.client.session.get_expiry_age(), 1800)

    def test_sessao_expirada_redireciona_para_login(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 1
        configuracao.save()
        self.definir_ultima_atividade(timezone.now() - timedelta(seconds=61))

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sem_configuracao_cria_padrao_de_quinze_minutos(self):
        ConfiguracaoSistema.objects.all().delete()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        configuracao = ConfiguracaoSistema.objects.get(pk=1)
        self.assertEqual(configuracao.tempo_logout_inatividade, 15)
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 898)
        self.assertLessEqual(self.client.session.get_expiry_age(), 900)

    def test_javascript_recebe_tempo_configurado(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 27
        configuracao.save()

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'const timeoutMinutes = Number(27);')
        self.assertContains(response, reverse('session_keepalive'))
        self.assertContains(response, "window.location.replace(loginPath)")

    def test_keepalive_exige_login_e_renova_atividade(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 15
        configuracao.save()
        instante_antigo = timezone.now() - timedelta(minutes=5)
        self.definir_ultima_atividade(instante_antigo)

        response = self.client.post(reverse('session_keepalive'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ativa': True})
        self.assertGreater(self.client.session[ULTIMA_ATIVIDADE_SESSAO], instante_antigo.timestamp())

        self.client.logout()
        response = self.client.post(reverse('session_keepalive'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('session_keepalive')}",
            fetch_redirect_response=False,
        )


class AuditoriaLogsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='admin-log', password='senha')
        self.admin.groups.add(Group.objects.get_or_create(name='Administrador')[0])
        self.vendedor = User.objects.create_user(username='vendedor-log', password='senha')
        self.vendedor.groups.add(Group.objects.get_or_create(name='Vendedor')[0])

    def test_registrar_log_manual_com_objeto_request_ip_e_user_agent(self):
        request = type('Request', (), {
            'META': {
                'REMOTE_ADDR': '127.0.0.1',
                'HTTP_USER_AGENT': 'Teste Browser',
            }
        })()
        cliente = Cliente.objects.create(
            nome='Cliente Log',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='52998224725',
        )

        registrar_log(self.admin, 'CRIACAO', 'clientes', 'Cliente criado.', objeto=cliente, request=request)

        log = LogAtividade.objects.get()
        self.assertEqual(log.usuario, self.admin)
        self.assertEqual(log.acao, LogAtividade.Acao.CRIACAO)
        self.assertEqual(log.objeto_tipo, 'clientes.cliente')
        self.assertEqual(log.objeto_id, str(cliente.pk))
        self.assertEqual(log.ip_usuario, '127.0.0.1')
        self.assertEqual(log.user_agent, 'Teste Browser')

    def test_login_registra_log(self):
        self.client.post(reverse('login'), {'username': self.admin.username, 'password': 'senha'})

        self.assertTrue(LogAtividade.objects.filter(usuario=self.admin, acao=LogAtividade.Acao.LOGIN).exists())

    def test_finalizacao_de_venda_registra_log(self):
        cliente = Cliente.objects.create(nome='Cliente Venda Log', tipo_pessoa='fisica', cpf_cnpj='11122233344')
        produto = Produto.objects.create(nome='Produto Log', unidade_medida='UN', preco_venda=Decimal('10.00'), estoque_atual=5)
        Caixa.abrir(usuario=self.vendedor, valor_inicial=Decimal('0.00'))
        venda = Venda.objects.create(cliente=cliente, usuario=self.vendedor, forma_pagamento=Venda.FormaPagamento.PIX)
        ItemVenda.objects.create(venda=venda, produto=produto, quantidade=1, valor_unitario=Decimal('10.00'))
        venda.recalcular_totais()

        venda.finalizar(usuario=self.vendedor)

        self.assertTrue(LogAtividade.objects.filter(
            usuario=self.vendedor,
            acao=LogAtividade.Acao.FINALIZACAO,
            modulo='vendas',
            objeto_id=str(venda.pk),
        ).exists())

    def test_fechamento_de_caixa_registra_log(self):
        caixa = Caixa.abrir(usuario=self.vendedor, valor_inicial=Decimal('20.00'))

        caixa.fechar(usuario=self.vendedor, valor_fechamento_informado=Decimal('20.00'))

        self.assertTrue(LogAtividade.objects.filter(
            usuario=self.vendedor,
            acao=LogAtividade.Acao.FECHAMENTO_CAIXA,
            modulo='caixa',
            objeto_id=str(caixa.pk),
        ).exists())

    def test_usuario_nao_admin_nao_acessa_logs(self):
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse('administracao:logs_atividade'))

        self.assertRedirects(response, reverse('acesso_negado'))

    def test_logs_aparecem_ordenados_por_data_decrescente(self):
        antigo = LogAtividade.objects.create(usuario=self.admin, acao=LogAtividade.Acao.LOGIN, modulo='accounts', descricao='Auditoria Antigo')
        novo = LogAtividade.objects.create(usuario=self.admin, acao=LogAtividade.Acao.LOGOUT, modulo='accounts', descricao='Auditoria Novo')
        LogAtividade.objects.filter(pk=antigo.pk).update(criado_em=timezone.now() - timedelta(days=1))
        LogAtividade.objects.filter(pk=novo.pk).update(criado_em=timezone.now())
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:logs_atividade'), {'q': 'Auditoria'})

        logs = list(response.context['logs'])
        self.assertEqual(logs[0].descricao, 'Auditoria Novo')


@override_settings(ROOT_URLCONF='accounts.tests')
class PerfilUsuarioInfraTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='perfil-admin', password='senha')
        self.gerente = User.objects.create_user(username='perfil-gerente', password='senha')
        self.vendedor = User.objects.create_user(username='perfil-vendedor', password='senha')
        self.estoquista = User.objects.create_user(username='perfil-estoquista', password='senha')
        self.sem_perfil = User.objects.create_user(username='perfil-sem', password='senha')
        PerfilUsuario.objects.create(usuario=self.admin, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        PerfilUsuario.objects.create(usuario=self.gerente, perfil=PerfilUsuario.Perfil.GERENTE)
        PerfilUsuario.objects.create(usuario=self.vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        PerfilUsuario.objects.create(usuario=self.estoquista, perfil=PerfilUsuario.Perfil.ESTOQUISTA)

    def test_helpers_por_perfil(self):
        self.assertTrue(usuario_eh_admin(self.admin))
        self.assertTrue(usuario_eh_gerente(self.gerente))
        self.assertTrue(usuario_eh_vendedor(self.vendedor))
        self.assertTrue(usuario_eh_estoquista(self.estoquista))
        self.assertTrue(usuario_tem_perfil(self.admin, ['ADMINISTRADOR', 'GERENTE']))
        self.assertFalse(usuario_tem_perfil(self.sem_perfil, ['ADMINISTRADOR']))

    def test_usuario_sem_perfil_bloqueado_e_logado(self):
        self.client.force_login(self.sem_perfil)

        response = self.client.get(reverse('teste_decorator_admin'))

        self.assertRedirects(response, reverse('acesso_negado'), fetch_redirect_response=False)
        self.assertTrue(LogAtividade.objects.filter(usuario=self.sem_perfil, acao=LogAtividade.Acao.ERRO).exists())

    def test_decorator_permite_admin_e_bloqueia_vendedor(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('teste_decorator_admin')), 'decorator ok')

        self.client.force_login(self.vendedor)
        response = self.client.get(reverse('teste_decorator_admin'))

        self.assertRedirects(response, reverse('acesso_negado'), fetch_redirect_response=False)

    def test_mixin_permite_gerente_e_bloqueia_estoquista(self):
        self.client.force_login(self.gerente)
        self.assertContains(self.client.get(reverse('teste_mixin_admin')), 'mixin ok')

        self.client.force_login(self.estoquista)
        response = self.client.get(reverse('teste_mixin_admin'))

        self.assertRedirects(response, reverse('acesso_negado'), fetch_redirect_response=False)

    def test_acesso_negado_renderiza_no_urlconf_real(self):
        with override_settings(ROOT_URLCONF='gestix.urls'):
            self.client.force_login(self.admin)
            response = self.client.get(reverse('acesso_negado'), HTTP_HOST='testserver')

        self.assertContains(response, 'Você não possui permissão para acessar este recurso.')


class PermissoesAplicadasModulosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='mod-admin', password='senha')
        self.gerente = User.objects.create_user(username='mod-gerente', password='senha')
        self.vendedor = User.objects.create_user(username='mod-vendedor', password='senha')
        self.estoquista = User.objects.create_user(username='mod-estoquista', password='senha')
        PerfilUsuario.objects.create(usuario=self.admin, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        PerfilUsuario.objects.create(usuario=self.gerente, perfil=PerfilUsuario.Perfil.GERENTE)
        PerfilUsuario.objects.create(usuario=self.vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        PerfilUsuario.objects.create(usuario=self.estoquista, perfil=PerfilUsuario.Perfil.ESTOQUISTA)
        self.produto = Produto.objects.create(
            nome='Produto restrito',
            unidade_medida='UN',
            preco_venda=Decimal('10.00'),
            estoque_atual=5,
        )

    def assert_acesso_negado(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('acesso_negado'))

    def test_vendedor_nao_acessa_contas_pagar_por_url_manual(self):
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse('contas_pagar:list'))

        self.assert_acesso_negado(response)

    def test_vendedor_nao_edita_produtos(self):
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse('produtos:update', args=[self.produto.pk]))

        self.assert_acesso_negado(response)

    def test_estoquista_nao_acessa_vendas(self):
        self.client.force_login(self.estoquista)

        response = self.client.get(reverse('vendas:list'))

        self.assert_acesso_negado(response)

    def test_gerente_nao_acessa_backup_e_restauracao(self):
        self.client.force_login(self.gerente)

        response = self.client.post(reverse('administracao:backup'), {'acao': 'restaurar'})

        self.assert_acesso_negado(response)

    def test_menu_do_vendedor_exibe_apenas_modulos_permitidos(self):
        self.client.force_login(self.vendedor)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Clientes')
        self.assertContains(response, 'Vendas')
        self.assertContains(response, 'Caixa')
        self.assertContains(response, 'Ordens de serviço')
        self.assertNotContains(response, 'Produtos')
        self.assertNotContains(response, 'Contas a pagar')
        self.assertNotContains(response, 'Backup e Restauração')
        self.assertNotContains(response, 'Logs de Atividade')

    def test_menu_do_estoquista_exibe_estoque_produtos_e_os(self):
        self.client.force_login(self.estoquista)

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Produtos')
        self.assertContains(response, 'Estoque')
        self.assertContains(response, 'Ordens de serviço')
        self.assertNotContains(response, 'Vendas')
        self.assertNotContains(response, 'Caixa')
        self.assertNotContains(response, 'Contas a pagar')


class HomeRouteTests(SimpleTestCase):
    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_rota_inicial_renderiza_sem_banco_e_sem_manifesto_estatico(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GESTIX')
        self.assertRegex(response.content.decode(), r'/static/css/home(\.[0-9a-f]+)?\.css')

    @patch('administracao.services.ConfiguracaoSistema.get_solo', side_effect=OperationalError)
    def test_configuracao_usa_valores_padrao_se_tabela_ainda_nao_existe(self, get_solo):
        from administracao.services import obter_configuracao_sistema

        configuracao = obter_configuracao_sistema()

        get_solo.assert_called_once_with()
        self.assertIsNone(configuracao.pk)
        self.assertEqual(configuracao.tempo_logout_inatividade, 15)
        self.assertTrue(configuracao.notificacoes_aniversario_ativas)


class ArquivosEstaticosAdminTests(SimpleTestCase):
    def test_configuracao_estatica_tem_fallback_quando_whitenoise_nao_esta_instalado(self):
        from django.conf import settings

        self.assertEqual(settings.STATIC_URL, '/static/')
        self.assertEqual(settings.STATIC_ROOT, settings.BASE_DIR / 'staticfiles')
        self.assertIn(settings.BASE_DIR / 'static', settings.STATICFILES_DIRS)
        security_index = settings.MIDDLEWARE.index('django.middleware.security.SecurityMiddleware')

        if settings.WHITENOISE_AVAILABLE:
            self.assertEqual(
                settings.STORAGES['staticfiles']['BACKEND'],
                'whitenoise.storage.CompressedManifestStaticFilesStorage',
            )
            self.assertEqual(
                settings.MIDDLEWARE[security_index + 1],
                'whitenoise.middleware.WhiteNoiseMiddleware',
            )
        else:
            self.assertEqual(
                settings.STORAGES['staticfiles']['BACKEND'],
                'django.contrib.staticfiles.storage.StaticFilesStorage',
            )
            self.assertNotIn('whitenoise.middleware.WhiteNoiseMiddleware', settings.MIDDLEWARE)

    def test_django_encontra_css_do_admin_e_estaticos_do_projeto(self):
        from django.contrib.staticfiles import finders

        self.assertIsNotNone(finders.find('admin/css/base.css'))
        self.assertIsNotNone(finders.find('css/home.css'))


class ConfiguracaoRedeLocalTests(SimpleTestCase):
    def test_exemplo_de_ambiente_configura_host_e_origem_da_rede(self):
        env_example = (Path(__file__).resolve().parents[1] / '.env.example').read_text(encoding='utf-8')

        self.assertIn('ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50', env_example)
        self.assertIn('http://192.168.1.50:8000', env_example)
        self.assertIn('USE_HTTPS=False', env_example)

    @override_settings(ALLOWED_HOSTS=['192.168.1.50'])
    def test_rota_inicial_aceita_host_da_rede_local(self):
        response = self.client.get('/', HTTP_HOST='192.168.1.50')

        self.assertEqual(response.status_code, 200)

    def test_listas_de_rede_sao_lidas_do_ambiente(self):
        from gestix.settings import env_list

        with patch.dict(os.environ, {'GESTIX_TEST_HOSTS': '10.0.0.10, servidor.local ,'}):
            self.assertEqual(env_list('GESTIX_TEST_HOSTS'), ['10.0.0.10', 'servidor.local'])

    def test_docker_publica_porta_e_escuta_em_todas_as_interfaces(self):
        compose = (Path(__file__).resolve().parents[1] / 'docker-compose.yml').read_text(encoding='utf-8')

        self.assertIn('python manage.py runserver 0.0.0.0:8000', compose)
        self.assertIn('- "${WEB_PORT:-8000}:8000"', compose)
        self.assertIn('CSRF_TRUSTED_ORIGINS:', compose)

    def test_launcher_mantem_localhost_e_informa_endereco_de_rede(self):
        launcher = (Path(__file__).resolve().parents[1] / 'launcher' / 'gestix_launcher.py').read_text(encoding='utf-8')

        self.assertIn("APP_URL = 'http://localhost:8000'", launcher)
        self.assertIn("GESTIX_NETWORK_URL", launcher)
        self.assertIn('Outros dispositivos da rede', launcher)
