from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse

from dashboard.models import ConfiguracaoSistema

from .models import DadosEmpresa


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

    def test_views_exigem_login(self):
        for url in [
            reverse('administracao:home'),
            reverse('administracao:dados_empresa'),
            reverse('administracao:configuracoes_sistema'),
        ]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)

    def test_administrador_visualiza_e_edita_dados_empresa(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('administracao:dados_empresa'), {
            'razao_social': 'GESTIX Tecnologia Ltda',
            'nome_fantasia': 'GESTIX',
            'cnpj': '12.345.678/0001-99',
            'inscricao_estadual': 'ISENTO',
            'telefone': '(27) 99999-9999',
            'email': 'contato@gestix.local',
            'endereco': 'Rua Principal, 100',
            'cidade': 'Vitória',
            'estado': 'es',
            'cep': '29000-000',
        })
        self.assertRedirects(response, reverse('administracao:dados_empresa'))
        empresa = DadosEmpresa.get_solo()
        self.assertEqual(empresa.nome_fantasia, 'GESTIX')
        self.assertEqual(empresa.estado, 'ES')

    def test_gerente_visualiza_mas_nao_edita(self):
        empresa = DadosEmpresa.get_solo()
        empresa.nome_fantasia = 'Nome original'
        empresa.save()
        self.client.force_login(self.gerente)

        response = self.client.get(reverse('administracao:dados_empresa'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['pode_editar'])
        self.assertTrue(response.context['form'].fields['nome_fantasia'].disabled)

        response = self.client.post(reverse('administracao:dados_empresa'), {'nome_fantasia': 'Alterado'})
        self.assertRedirects(response, reverse('administracao:dados_empresa'))
        empresa.refresh_from_db()
        self.assertEqual(empresa.nome_fantasia, 'Nome original')

    def test_vendedor_e_estoquista_nao_acessam(self):
        for usuario in [self.vendedor, self.estoquista]:
            self.client.force_login(usuario)
            response = self.client.get(reverse('administracao:home'))
            self.assertRedirects(response, reverse('dashboard'))

    def test_administrador_edita_configuracao_existente(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('administracao:configuracoes_sistema'), {
            'notificacoes_aniversario_ativas': '',
            'dias_antecedencia_aniversario': 5,
        })
        self.assertRedirects(response, reverse('administracao:configuracoes_sistema'))
        configuracao = ConfiguracaoSistema.get_solo()
        self.assertFalse(configuracao.notificacoes_aniversario_ativas)
        self.assertEqual(configuracao.dias_antecedencia_aniversario, 5)

    def test_url_antiga_de_configuracoes_redireciona_para_administracao(self):
        self.client.force_login(self.admin)
        response = self.client.get('/configuracoes/')
        self.assertRedirects(response, reverse('administracao:configuracoes_sistema'), fetch_redirect_response=False)
