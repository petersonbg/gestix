from datetime import timedelta
import os
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db.utils import OperationalError
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from administracao.models import ConfiguracaoSistema

from .middleware import ULTIMA_ATIVIDADE_SESSAO
from .models import LogAtividade
from .utils import registrar_log


class AuditoriaTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('auditor', password='senha')

    def test_registrar_log_manual_com_ip_user_agent_e_objeto(self):
        request = RequestFactory().post(
            '/',
            HTTP_X_FORWARDED_FOR='203.0.113.10, 10.0.0.1',
            HTTP_USER_AGENT='Navegador de homologação',
        )
        log = registrar_log(
            self.user,
            LogAtividade.Acao.EDICAO,
            'accounts',
            'Registro de teste.',
            objeto=self.user,
            request=request,
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.ip_usuario, '203.0.113.10')
        self.assertEqual(log.user_agent, 'Navegador de homologação')
        self.assertEqual(log.objeto_tipo, 'auth.user')
        self.assertEqual(log.objeto_id, str(self.user.pk))

    def test_login_registra_log(self):
        self.client.login(username='auditor', password='senha')
        self.assertTrue(LogAtividade.objects.filter(
            usuario=self.user,
            acao=LogAtividade.Acao.LOGIN,
        ).exists())

    @patch('accounts.models.LogAtividade.objects.create', side_effect=RuntimeError)
    def test_falha_ao_registrar_log_nao_quebra_fluxo(self, criar):
        self.assertIsNone(registrar_log(self.user, 'EDICAO', 'accounts', 'Teste'))


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


class HomeRouteTests(SimpleTestCase):
    @override_settings(DEBUG=False, ALLOWED_HOSTS=['testserver'])
    def test_rota_inicial_renderiza_sem_banco_e_sem_manifesto_estatico(self):
        response = self.client.get(reverse('home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'GESTIX')
        self.assertContains(response, '/static/css/home.css')

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
        self.assertIn('- "8000:8000"', compose)
        self.assertIn('CSRF_TRUSTED_ORIGINS:', compose)

    def test_launcher_mantem_localhost_e_informa_endereco_de_rede(self):
        launcher = (Path(__file__).resolve().parents[1] / 'launcher' / 'gestix_launcher.py').read_text(encoding='utf-8')

        self.assertIn("APP_URL = 'http://localhost:8000'", launcher)
        self.assertIn("GESTIX_NETWORK_URL", launcher)
        self.assertIn('Outros dispositivos da rede', launcher)
