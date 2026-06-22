from io import BytesIO
from pathlib import Path
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from accounts.models import LogAtividade
from ordens_servico.models import Servico

from .backup_services import registrar_backup
from .forms import BackupRestoreForm, EmpresaForm
from .models import BackupRegistro, CategoriaProduto, ConfiguracaoSistema, Empresa
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
        for url in [reverse('administracao:home'), reverse('administracao:dados_empresa'), reverse('administracao:dados_empresa_editar'), reverse('administracao:configuracoes_sistema'), reverse('administracao:diagnostico_rede'), reverse('administracao:usuarios_permissoes'), reverse('administracao:logs_atividade')]:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse('login'), response.url)

    def test_home_exibe_cards_e_resumos_administrativos(self):
        LogAtividade.objects.create(usuario=self.admin, acao='teste', modulo='administracao')
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:home'))

        self.assertEqual(response.status_code, 200)
        for titulo in ['Endereço de acesso na rede', 'Dados da Empresa', 'Configurações do Sistema', 'Usuários e Permissões', 'Logs de Atividade']:
            self.assertContains(response, titulo)
        self.assertEqual(response.context['usuarios_total'], 4)
        self.assertEqual(response.context['usuarios_ativos'], 4)
        self.assertGreaterEqual(response.context['grupos_total'], 4)
        self.assertGreaterEqual(response.context['logs_total'], 1)
        self.assertIsNotNone(response.context['ultimo_log'])

    def test_diagnostico_rede_exibe_hostname_ip_porta_e_url(self):
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:diagnostico_rede'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Hostname')
        self.assertContains(response, 'IP atual')
        self.assertContains(response, 'Porta utilizada')
        self.assertContains(response, response.context['rede'].recommended_url)
        self.assertIn(response.context['rede'].hostname, response.context['allowed_hosts'])
        self.assertIn(response.context['rede'].mdns_hostname, response.context['allowed_hosts'])

    def test_administrador_acessa_usuarios_e_logs_e_gerente_apenas_usuarios(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse('administracao:usuarios_permissoes')).status_code, 200)
        self.assertEqual(self.client.get(reverse('administracao:logs_atividade')).status_code, 200)

        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(reverse('administracao:usuarios_permissoes')).status_code, 200)
        self.assertRedirects(self.client.get(reverse('administracao:logs_atividade')), reverse('acesso_negado'))

    def test_vendedor_e_estoquista_nao_acessam_usuarios_e_logs(self):
        for usuario in [self.vendedor, self.estoquista]:
            self.client.force_login(usuario)
            for nome_url in ['usuarios_permissoes', 'logs_atividade']:
                response = self.client.get(reverse(f'administracao:{nome_url}'))
                self.assertRedirects(response, reverse('acesso_negado'))

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
            self.assertRedirects(response, reverse('acesso_negado'))

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


class BackupRestauracaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_user(username='admin-backup', password='senha')
        cls.admin.groups.add(Group.objects.get_or_create(name='Administrador')[0])
        cls.gerente = User.objects.create_user(username='gerente-backup', password='senha')
        cls.gerente.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        cls.vendedor = User.objects.create_user(username='vendedor-backup', password='senha')
        cls.vendedor.groups.add(Group.objects.get_or_create(name='Vendedor')[0])

    def test_acesso_negado_para_usuario_nao_admin(self):
        for usuario in (self.gerente, self.vendedor):
            self.client.force_login(usuario)
            response = self.client.get(reverse('administracao:backup'))
            self.assertRedirects(response, reverse('acesso_negado'))

        self.client.logout()
        response = self.client.get(reverse('administracao:backup'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)

    def test_listagem_do_historico(self):
        BackupRegistro.objects.create(
            tipo=BackupRegistro.Tipo.BACKUP,
            nome_arquivo='gestix_backup_20260616_120000.dump',
            arquivo='gestix_backup_20260616_120000.dump',
            tamanho_arquivo=2048,
            usuario=self.admin,
            status=BackupRegistro.Status.SUCESSO,
            mensagem='Backup gerado com sucesso.',
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('administracao:backup'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gestix_backup_20260616_120000.dump')
        self.assertContains(response, 'SUCESSO')
        self.assertContains(response, 'Baixar Backup')

    def test_criacao_de_registro_de_backup(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            caminho = Path(tmpdir) / 'gestix_backup_20260616_120000.dump'
            caminho.write_bytes(b'PGDMP')

            registro = registrar_backup(
                tipo=BackupRegistro.Tipo.BACKUP,
                caminho=caminho,
                usuario=self.admin,
                status=BackupRegistro.Status.SUCESSO,
                mensagem='Criado no teste.',
            )

        self.assertEqual(registro.nome_arquivo, 'gestix_backup_20260616_120000.dump')
        self.assertEqual(registro.tamanho_arquivo, 5)
        self.assertEqual(registro.usuario, self.admin)

    def test_validacao_de_extensao(self):
        form = BackupRestoreForm(
            data={'confirmar_restauracao': 'on'},
            files={'arquivo_backup': SimpleUploadedFile('backup.txt', b'invalido')},
        )

        self.assertFalse(form.is_valid())
        self.assertIn('Envie um arquivo .dump ou .backup.', form.errors['arquivo_backup'])

    def test_upload_invalido_sem_arquivo(self):
        self.client.force_login(self.admin)

        response = self.client.post(
            reverse('administracao:backup'),
            {'acao': 'restaurar', 'confirmar_restauracao': 'on'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Revise o arquivo enviado para restauração')
        self.assertFalse(BackupRegistro.objects.filter(tipo=BackupRegistro.Tipo.RESTAURACAO).exists())

    def test_gerar_backup_pela_tela_registra_sucesso(self):
        self.client.force_login(self.admin)
        caminho = Path('backups') / 'gestix_backup_20260616_120000.dump'

        with patch('administracao.views.gerar_backup', return_value=caminho) as gerar:
            response = self.client.post(reverse('administracao:backup'), {'acao': 'gerar'})

        self.assertRedirects(response, reverse('administracao:backup'))
        gerar.assert_called_once()

    @override_settings(BACKUP_ROOT=Path(tempfile.gettempdir()) / 'gestix_test_backups')
    def test_download_protegido_por_admin(self):
        backup_dir = Path(tempfile.gettempdir()) / 'gestix_test_backups'
        backup_dir.mkdir(parents=True, exist_ok=True)
        arquivo = backup_dir / 'gestix_backup_download.dump'
        arquivo.write_bytes(b'PGDMP')
        registro = BackupRegistro.objects.create(
            tipo=BackupRegistro.Tipo.BACKUP,
            nome_arquivo=arquivo.name,
            arquivo=arquivo.name,
            tamanho_arquivo=arquivo.stat().st_size,
            usuario=self.admin,
            status=BackupRegistro.Status.SUCESSO,
        )

        self.client.force_login(self.vendedor)
        response = self.client.get(reverse('administracao:backup_download', args=[registro.pk]))
        self.assertRedirects(response, reverse('acesso_negado'))

        self.client.force_login(self.admin)
        response = self.client.get(reverse('administracao:backup_download', args=[registro.pk]))
        self.assertEqual(response.status_code, 200)


class CategoriaProdutoTests(TestCase):
    def setUp(self):
        self.administrador = get_user_model().objects.create_user(
            username='admin-categorias', password='senha'
        )
        self.gerente = get_user_model().objects.create_user(
            username='gerente-categorias', password='senha'
        )
        self.vendedor = get_user_model().objects.create_user(
            username='vendedor-categorias', password='senha'
        )
        grupo_admin, _ = Group.objects.get_or_create(name='Administrador')
        grupo_gerente, _ = Group.objects.get_or_create(name='Gerente')
        grupo_vendedor, _ = Group.objects.get_or_create(name='Vendedor')
        self.administrador.groups.add(grupo_admin)
        self.gerente.groups.add(grupo_gerente)
        self.vendedor.groups.add(grupo_vendedor)

    def test_administrador_cria_categorias_geral_e_veiculos(self):
        self.client.force_login(self.administrador)
        for nome, tipo in [('Peças', 'GERAL'), ('Veículos', 'VEICULOS')]:
            resposta = self.client.post(
                reverse('administracao:categoria_produto_criar'),
                {'nome': nome, 'descricao': '', 'tipo': tipo, 'ativo': 'on'},
            )
            self.assertEqual(resposta.status_code, 302)

        self.assertTrue(CategoriaProduto.objects.filter(nome='Peças', tipo='GERAL').exists())
        self.assertTrue(
            CategoriaProduto.objects.filter(nome='Veículos', tipo='VEICULOS').exists()
        )

    def test_nome_da_categoria_e_unico(self):
        CategoriaProduto.objects.create(nome='Duplicada')
        categoria = CategoriaProduto(nome='Duplicada')
        with self.assertRaises(ValidationError):
            categoria.full_clean()

    def test_gerente_visualiza_mas_nao_edita_categoria(self):
        categoria = CategoriaProduto.objects.create(nome='Somente leitura')
        self.client.force_login(self.gerente)
        self.assertEqual(
            self.client.get(reverse('administracao:categorias_produtos')).status_code,
            200,
        )
        resposta = self.client.get(
            reverse('administracao:categoria_produto_editar', kwargs={'pk': categoria.pk})
        )
        self.assertEqual(resposta.status_code, 302)

    def test_vendedor_nao_acessa_cadastro_de_categorias(self):
        self.client.force_login(self.vendedor)
        resposta = self.client.get(reverse('administracao:categorias_produtos'))
        self.assertEqual(resposta.status_code, 302)


class ServicoAdministracaoTests(TestCase):
    def setUp(self):
        self.administrador = get_user_model().objects.create_user(
            username='admin-servicos', password='senha'
        )
        self.gerente = get_user_model().objects.create_user(
            username='gerente-servicos', password='senha'
        )
        self.vendedor = get_user_model().objects.create_user(
            username='vendedor-servicos', password='senha'
        )
        self.estoquista = get_user_model().objects.create_user(
            username='estoquista-servicos', password='senha'
        )
        for usuario, grupo in (
            (self.administrador, 'Administrador'),
            (self.gerente, 'Gerente'),
            (self.vendedor, 'Vendedor'),
            (self.estoquista, 'Estoquista'),
        ):
            usuario.groups.add(Group.objects.get_or_create(name=grupo)[0])
        self.servico = Servico.objects.create(
            nome='Revisão administrativa',
            descricao='Serviço gerenciado pela Administração.',
            valor_padrao='100.00',
        )

    def test_administrador_cadastra_edita_visualiza_e_inativa_servico(self):
        self.client.force_login(self.administrador)
        resposta = self.client.post(reverse('administracao:servico_criar'), {
            'nome': 'Instalação administrativa',
            'descricao': 'Instalação completa',
            'valor_padrao': '120.00',
            'ativo': 'on',
        })
        self.assertRedirects(resposta, reverse('administracao:servicos'))
        servico = Servico.objects.get(nome='Instalação administrativa')
        self.assertEqual(
            self.client.get(reverse('administracao:servico_detalhe', args=[servico.pk])).status_code,
            200,
        )
        resposta = self.client.post(reverse('administracao:servico_editar', args=[servico.pk]), {
            'nome': 'Instalação atualizada',
            'descricao': 'Instalação completa',
            'valor_padrao': '150.00',
            'ativo': 'on',
        })
        self.assertRedirects(resposta, reverse('administracao:servico_detalhe', args=[servico.pk]))
        resposta = self.client.post(
            reverse('administracao:servico_alterar_ativo', args=[servico.pk])
        )
        self.assertRedirects(resposta, reverse('administracao:servico_detalhe', args=[servico.pk]))
        servico.refresh_from_db()
        self.assertFalse(servico.ativo)

    def test_gerente_visualiza_mas_nao_cadastra_edita_ou_inativa(self):
        self.client.force_login(self.gerente)
        self.assertEqual(self.client.get(reverse('administracao:servicos')).status_code, 200)
        self.assertEqual(
            self.client.get(reverse('administracao:servico_detalhe', args=[self.servico.pk])).status_code,
            200,
        )
        for url in (
            reverse('administracao:servico_criar'),
            reverse('administracao:servico_editar', args=[self.servico.pk]),
        ):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.client.post(reverse('administracao:servico_alterar_ativo', args=[self.servico.pk]))
        self.servico.refresh_from_db()
        self.assertTrue(self.servico.ativo)

    def test_vendedor_e_estoquista_nao_acessam_servicos_da_administracao(self):
        for usuario in (self.vendedor, self.estoquista):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(reverse('administracao:servicos')).status_code, 302)

    def test_servico_administrativo_aparece_no_dropdown_da_os_somente_quando_ativo(self):
        self.client.force_login(self.administrador)
        resposta = self.client.get(reverse('ordens_servico:create'))
        self.assertContains(resposta, self.servico.nome)
        self.assertContains(resposta, f'value="{self.servico.pk}"')

        self.servico.ativo = False
        self.servico.save(update_fields=['ativo'])
        resposta = self.client.get(reverse('ordens_servico:create'))
        self.assertNotContains(resposta, self.servico.nome)

    def test_menu_administracao_exibe_servicos(self):
        self.client.force_login(self.administrador)
        resposta = self.client.get(reverse('administracao:home'))
        self.assertContains(resposta, 'Serviços')
        self.assertContains(resposta, reverse('administracao:servicos'))

    def test_valor_padrao_tem_default_zero_e_nao_aceita_negativo(self):
        servico = Servico.objects.create(nome='Sem valor informado')
        self.assertEqual(servico.valor_padrao, 0)
        invalido = Servico(nome='Valor negativo', valor_padrao='-0.01')
        with self.assertRaises(ValidationError):
            invalido.full_clean()
