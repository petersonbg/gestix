from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import ConfiguracaoSistema, Empresa


class AdministracaoAcessoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='admin-app', password='senha')
        cls.admin.groups.add(Group.objects.get_or_create(name='Administrador')[0])
        cls.gerente = User.objects.create_user(username='gerente-app', password='senha')
        cls.gerente.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        cls.vendedor = User.objects.create_user(username='vendedor-app', password='senha')
        cls.vendedor.groups.add(Group.objects.get_or_create(name='Vendedor')[0])
        cls.estoquista = User.objects.create_user(username='estoquista-app', password='senha')
        cls.estoquista.groups.add(Group.objects.get_or_create(name='Estoquista')[0])

    def dados_empresa(self, **alteracoes):
        dados = {
            'razao_social': 'GESTIX Tecnologia Ltda', 'nome_fantasia': 'GESTIX',
            'cnpj': '12.345.678/0001-99', 'inscricao_estadual': 'ISENTO',
            'inscricao_municipal': '12345', 'cep': '29000-000',
            'logradouro': 'Rua Principal', 'numero': '100', 'complemento': 'Sala 1',
            'bairro': 'Centro', 'cidade': 'Vitória', 'estado': 'es',
            'telefone': '(27) 3333-3333', 'celular': '(27) 99999-9999',
            'whatsapp': '(27) 99999-9999', 'email': 'contato@gestix.local',
            'site': 'https://gestix.local', 'cor_primaria': '#112233',
            'cor_secundaria': '#445566', 'responsavel': 'Responsável',
            'observacoes': 'Cadastro principal.',
        }
        dados.update(alteracoes)
        return dados

    def test_views_exigem_login(self):
        for url in [reverse('administracao:home'), reverse('administracao:dados_empresa'), reverse('administracao:dados_empresa_editar'), reverse('administracao:configuracoes_sistema')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)

    def test_administrador_visualiza_e_edita_empresa(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('administracao:dados_empresa_editar'), self.dados_empresa())
        self.assertRedirects(response, reverse('administracao:dados_empresa'))
        empresa = Empresa.get_solo()
        self.assertEqual(empresa.nome_fantasia, 'GESTIX')
        self.assertEqual(empresa.logradouro, 'Rua Principal')
        self.assertEqual(empresa.estado, 'ES')

        response = self.client.get(reverse('administracao:dados_empresa'))
        self.assertContains(response, 'GESTIX')
        self.assertContains(response, 'Rua Principal')

    def test_gerente_visualiza_mas_nao_acessa_edicao(self):
        Empresa.get_solo().save()
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(reverse('administracao:dados_empresa')).status_code, 200)
        response = self.client.get(reverse('administracao:dados_empresa_editar'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_vendedor_e_estoquista_nao_acessam(self):
        for usuario in [self.vendedor, self.estoquista]:
            self.client.force_login(usuario)
            response = self.client.get(reverse('administracao:home'))
            self.assertRedirects(response, reverse('dashboard'))

    def test_apenas_um_cadastro_de_empresa(self):
        empresa = Empresa.get_solo()
        self.assertEqual(empresa.pk, 1)
        outra = Empresa(pk=2, nome_fantasia='Outra empresa')
        with self.assertRaisesMessage(ValidationError, 'apenas um cadastro'):
            outra.save()
        self.assertEqual(Empresa.objects.count(), 1)

    def test_empresa_nao_pode_ser_excluida(self):
        empresa = Empresa.get_solo()
        with self.assertRaisesMessage(ValidationError, 'não pode ser excluído'):
            empresa.delete()

    def dados_configuracao(self, **alteracoes):
        dados = {
            'notificacoes_aniversario_ativas': '',
            'dias_antecedencia_aniversario': 5,
            'tempo_logout_inatividade': 30,
            'mostrar_logo_impressoes': 'on',
            'mostrar_assinatura_cliente': '',
            'mensagem_rodape_documentos': 'Obrigado pela preferência.',
        }
        dados.update(alteracoes)
        return dados

    def test_administrador_edita_configuracao_existente(self):
        self.client.force_login(self.admin)
        response = self.client.post(
            reverse('administracao:configuracoes_sistema'),
            self.dados_configuracao(),
        )
        self.assertRedirects(response, reverse('administracao:configuracoes_sistema'))
        configuracao = ConfiguracaoSistema.get_solo()
        self.assertFalse(configuracao.notificacoes_aniversario_ativas)
        self.assertEqual(configuracao.dias_antecedencia_aniversario, 5)
        self.assertEqual(configuracao.tempo_logout_inatividade, 30)
        self.assertTrue(configuracao.mostrar_logo_impressoes)
        self.assertFalse(configuracao.mostrar_assinatura_cliente)
        self.assertEqual(configuracao.mensagem_rodape_documentos, 'Obrigado pela preferência.')

    def test_gerente_visualiza_mas_nao_edita_configuracoes(self):
        configuracao = ConfiguracaoSistema.get_solo()
        self.client.force_login(self.gerente)
        response = self.client.get(reverse('administracao:configuracoes_sistema'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].fields['tempo_logout_inatividade'].disabled)

        response = self.client.post(
            reverse('administracao:configuracoes_sistema'),
            self.dados_configuracao(tempo_logout_inatividade=60),
        )
        self.assertRedirects(response, reverse('administracao:configuracoes_sistema'))
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.tempo_logout_inatividade, 15)

    def test_configuracao_e_registro_unico_e_nao_pode_ser_excluida(self):
        configuracao = ConfiguracaoSistema.get_solo()
        self.assertEqual(configuracao.pk, 1)
        with self.assertRaisesMessage(ValidationError, 'apenas um registro'):
            ConfiguracaoSistema(pk=2).save()
        with self.assertRaisesMessage(ValidationError, 'não pode ser excluída'):
            configuracao.delete()

    def test_url_antiga_de_configuracoes_redireciona_para_administracao(self):
        self.client.force_login(self.admin)
        response = self.client.get('/configuracoes/')
        self.assertRedirects(response, reverse('administracao:configuracoes_sistema'), fetch_redirect_response=False)
