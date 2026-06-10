from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from accounts.models import LogAtividade

from .forms import EmpresaForm
from .models import ConfiguracaoSistema, Empresa
from .services import formatar_contato_empresa, formatar_endereco_empresa




class EmpresaLogotiposTests(TestCase):
    @staticmethod
    def imagem_raster(nome='logo.png', formato='PNG', tamanho=(32, 32)):
        conteudo = BytesIO()
        Image.new('RGBA' if formato == 'PNG' else 'RGB', tamanho, '#0d6efd').save(
            conteudo, format=formato
        )
        return SimpleUploadedFile(
            nome,
            conteudo.getvalue(),
            content_type='image/png' if formato == 'PNG' else 'image/jpeg',
        )

    @staticmethod
    def svg(nome='logo.svg', conteudo=None):
        conteudo = conteudo or (
            b'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="400">'
            b'<rect width="1200" height="400" fill="#0d6efd"/></svg>'
        )
        return SimpleUploadedFile(nome, conteudo, content_type='image/svg+xml')

    def formulario(self, *, logo=None, logo_impressao=None):
        arquivos = {}
        if logo is not None:
            arquivos['logo'] = logo
        if logo_impressao is not None:
            arquivos['logo_impressao'] = logo_impressao
        return EmpresaForm(
            data={'cor_primaria': '#0D6EFD', 'cor_secundaria': '#6C757D'},
            files=arquivos,
            instance=Empresa(pk=1),
        )

    def test_logo_sistema_aceita_png_jpg_jpeg_e_svg_validos(self):
        arquivos = [
            self.imagem_raster('logo.png'),
            self.imagem_raster('logo.jpg', formato='JPEG'),
            self.imagem_raster('logo.jpeg', formato='JPEG'),
            self.svg(),
        ]

        for arquivo in arquivos:
            with self.subTest(nome=arquivo.name):
                formulario = self.formulario(logo=arquivo)
                self.assertTrue(formulario.is_valid(), formulario.errors)

    def test_logo_impressao_aceita_somente_png_e_svg_validos(self):
        for arquivo in [self.imagem_raster('impressao.png'), self.svg('impressao.svg')]:
            with self.subTest(nome=arquivo.name):
                formulario = self.formulario(logo_impressao=arquivo)
                self.assertTrue(formulario.is_valid(), formulario.errors)

        formulario = self.formulario(
            logo_impressao=self.imagem_raster('impressao.jpg', formato='JPEG')
        )
        self.assertFalse(formulario.is_valid())
        self.assertIn('Formato não permitido', formulario.errors['logo_impressao'][0])

    def test_rejeita_extensoes_nao_permitidas_e_conteudo_disfarcado(self):
        formulario_webp = self.formulario(
            logo=SimpleUploadedFile('logo.webp', b'arquivo', content_type='image/webp')
        )
        formulario_png_disfarcado = self.formulario(
            logo=self.imagem_raster('logo.png', formato='JPEG')
        )

        self.assertFalse(formulario_webp.is_valid())
        self.assertIn('Formato não permitido', formulario_webp.errors['logo'][0])
        self.assertFalse(formulario_png_disfarcado.is_valid())
        self.assertIn('corrompido', formulario_png_disfarcado.errors['logo'][0])

    def test_rejeita_logos_acima_dos_limites(self):
        logo_sistema = SimpleUploadedFile('logo.png', b'0' * (2 * 1024 * 1024 + 1))
        logo_impressao = SimpleUploadedFile('logo.svg', b'0' * (5 * 1024 * 1024 + 1))

        formulario = self.formulario(logo=logo_sistema, logo_impressao=logo_impressao)

        self.assertFalse(formulario.is_valid())
        self.assertIn('no máximo 2 MB', formulario.errors['logo'][0])
        self.assertIn('no máximo 5 MB', formulario.errors['logo_impressao'][0])

    def test_rejeita_imagem_raster_e_svg_corrompidos(self):
        raster = SimpleUploadedFile('logo.png', b'nao-e-uma-imagem', content_type='image/png')
        svg = self.svg('impressao.svg', b'<svg><elemento-incompleto></svg')

        formulario = self.formulario(logo=raster, logo_impressao=svg)

        self.assertFalse(formulario.is_valid())
        self.assertIn('imagem está corrompido', formulario.errors['logo'][0])
        self.assertIn('SVG está corrompido', formulario.errors['logo_impressao'][0])

    def test_formulario_exibe_ajudas_e_restricoes_de_selecao(self):
        formulario = EmpresaForm(instance=Empresa(pk=1))

        self.assertEqual(formulario.fields['logo'].label, 'Logo do Sistema')
        self.assertEqual(formulario.fields['logo_impressao'].label, 'Logo de Impressão')
        self.assertEqual(
            formulario.fields['logo'].help_text,
            'Recomendado: PNG transparente 512x512',
        )
        self.assertEqual(
            formulario.fields['logo_impressao'].help_text,
            'Recomendado: PNG ou SVG horizontal 1200x400',
        )
        self.assertEqual(
            formulario.fields['logo'].widget.attrs['accept'], '.png,.jpg,.jpeg,.svg'
        )
        self.assertEqual(
            formulario.fields['logo_impressao'].widget.attrs['accept'], '.png,.svg'
        )

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
        for url in [reverse('administracao:home'), reverse('administracao:dados_empresa'), reverse('administracao:dados_empresa_editar'), reverse('administracao:configuracoes_sistema'), reverse('administracao:usuarios_permissoes'), reverse('administracao:logs_atividade')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)

    def test_home_exibe_cards_e_resumos_administrativos(self):
        LogAtividade.objects.create(usuario=self.admin, acao='teste', modulo='administracao')
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:home'))

        self.assertEqual(response.status_code, 200)
        for titulo in ['Dados da Empresa', 'Configurações do Sistema', 'Usuários e Permissões', 'Logs de Atividade']:
            self.assertContains(response, titulo)
        self.assertEqual(response.context['usuarios_total'], 4)
        self.assertEqual(response.context['usuarios_ativos'], 4)
        self.assertGreaterEqual(response.context['grupos_total'], 4)
        self.assertGreaterEqual(response.context['logs_total'], 1)
        self.assertIsNotNone(response.context['ultimo_log'])

    def test_administrador_e_gerente_acessam_usuarios_e_logs(self):
        for usuario in [self.admin, self.gerente]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse('administracao:usuarios_permissoes')).status_code, 200)
            self.assertEqual(self.client.get(reverse('administracao:logs_atividade')).status_code, 200)

    def test_vendedor_e_estoquista_nao_acessam_usuarios_e_logs(self):
        for usuario in [self.vendedor, self.estoquista]:
            self.client.force_login(usuario)
            for nome_url in ['usuarios_permissoes', 'logs_atividade']:
                response = self.client.get(reverse(f'administracao:{nome_url}'))
                self.assertRedirects(response, reverse('dashboard'))

    def test_helpers_formatam_endereco_e_contato_da_empresa(self):
        empresa = Empresa(
            logradouro='Av. Central', numero='150', bairro='Centro',
            cidade='Montanha', estado='ES', telefone='(27) 3333-3333',
            celular='(27) 98888-8888', whatsapp='(27) 99999-9999',
        )

        self.assertEqual(
            formatar_endereco_empresa(empresa),
            'Av. Central, 150 - Centro - Montanha/ES',
        )
        self.assertEqual(formatar_contato_empresa(empresa), '(27) 99999-9999')

    def test_helpers_ignoram_campos_vazios_e_aplicam_fallback_de_contato(self):
        empresa = Empresa(logradouro='Rua Única', cidade='Vitória', telefone='(27) 3333-3333')
        self.assertEqual(formatar_endereco_empresa(empresa), 'Rua Única - Vitória')
        self.assertEqual(formatar_contato_empresa(empresa), '(27) 3333-3333')

        empresa.telefone = ''
        empresa.celular = '(27) 97777-7777'
        self.assertEqual(formatar_contato_empresa(empresa), '(27) 97777-7777')

    def test_formulario_empresa_exibe_ajuda_dos_logotipos(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:dados_empresa_editar'))

        self.assertContains(response, 'Recomendado: PNG transparente 512x512')
        self.assertContains(response, 'Recomendado: PNG ou SVG horizontal 1200x400')
        self.assertContains(response, 'accept=".png,.jpg,.jpeg,.svg"')
        self.assertContains(response, 'accept=".png,.svg"')

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
