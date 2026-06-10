from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from .forms import ProdutoForm
from .models import Produto


class ProdutoCodigoInternoTests(TestCase):
    def criar_produto(self, **dados):
        valores = {
            'nome': 'Produto de teste',
            'unidade_medida': 'UN',
            'preco_venda': Decimal('10.00'),
        }
        valores.update(dados)
        return Produto.objects.create(**valores)

    def test_gera_codigo_interno_automaticamente(self):
        primeiro = self.criar_produto(nome='Primeiro')
        segundo = self.criar_produto(nome='Segundo')

        self.assertEqual(primeiro.codigo_interno, 'PROD000001')
        self.assertEqual(segundo.codigo_interno, 'PROD000002')
        self.assertNotEqual(primeiro.codigo_interno, segundo.codigo_interno)

    def test_mantem_codigo_interno_informado(self):
        produto = self.criar_produto(codigo_interno='LEGADO-123')

        self.assertEqual(produto.codigo_interno, 'LEGADO-123')

    def test_nao_reutiliza_codigo_de_produto_excluido(self):
        primeiro = self.criar_produto(nome='Primeiro')
        segundo = self.criar_produto(nome='Segundo')
        segundo.delete()

        terceiro = self.criar_produto(nome='Terceiro')

        self.assertEqual(primeiro.codigo_interno, 'PROD000001')
        self.assertEqual(terceiro.codigo_interno, 'PROD000003')

    def test_codigo_manual_sequencial_avanca_proxima_numeracao(self):
        self.criar_produto(codigo_interno='PROD000010')

        produto = self.criar_produto(nome='Próximo')

        self.assertEqual(produto.codigo_interno, 'PROD000011')


class ProdutoPrecoCustoTests(TestCase):
    def test_cria_produto_sem_preco_de_custo(self):
        produto = Produto.objects.create(
            nome='Sem custo',
            unidade_medida='UN',
            preco_venda=Decimal('15.00'),
        )

        self.assertEqual(produto.preco_custo, Decimal('0.00'))

    def test_formulario_converte_preco_de_custo_vazio_para_zero(self):
        formulario = ProdutoForm(
            data={
                'nome': 'Sem custo no formulário',
                'descricao': '',
                'codigo_barras': '',
                'categoria': '',
                'unidade_medida': 'UN',
                'preco_custo': '',
                'preco_venda': '20.00',
                'estoque_minimo': '0',
                'fornecedor': '',
                'ncm': '',
                'ativo': 'on',
            }
        )

        self.assertTrue(formulario.is_valid(), formulario.errors)
        produto = formulario.save()
        self.assertEqual(produto.preco_custo, Decimal('0.00'))
        self.assertEqual(produto.codigo_interno, 'PROD000001')

    def test_impede_precos_negativos(self):
        produto_custo_negativo = Produto(
            nome='Custo negativo',
            unidade_medida='UN',
            preco_custo=Decimal('-1.00'),
            preco_venda=Decimal('10.00'),
        )
        produto_venda_negativa = Produto(
            nome='Venda negativa',
            unidade_medida='UN',
            preco_custo=Decimal('0.00'),
            preco_venda=Decimal('-1.00'),
        )

        with self.assertRaises(ValidationError):
            produto_custo_negativo.full_clean()
        with self.assertRaises(ValidationError):
            produto_venda_negativa.full_clean()


@override_settings(
    STORAGES={
        'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
        'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
    }
)
class ProdutoViewsTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-produtos',
            password='senha-segura',
            email='admin@example.com',
        )
        self.client.force_login(self.usuario)
        self.produto = Produto.objects.create(
            nome='Produto existente',
            unidade_medida='UN',
            preco_custo=Decimal('5.00'),
            preco_venda=Decimal('10.00'),
        )

    def dados_formulario(self, **alteracoes):
        dados = {
            'nome': self.produto.nome,
            'descricao': '',
            'codigo_interno': 'CODIGO-ALTERADO',
            'codigo_barras': '',
            'categoria': '',
            'unidade_medida': 'UN',
            'preco_custo': '',
            'preco_venda': '12.00',
            'estoque_minimo': '0',
            'fornecedor': '',
            'ncm': '',
            'ativo': 'on',
        }
        dados.update(alteracoes)
        return dados

    def test_cadastro_exibe_aviso_de_codigo_automatico(self):
        resposta = self.client.get(reverse('produtos:create'))

        self.assertContains(resposta, 'Gerado automaticamente ao salvar.')
        self.assertTrue(resposta.context['form'].fields['codigo_interno'].disabled)
        self.assertFalse(resposta.context['form'].fields['preco_custo'].required)

    def test_edicao_nao_altera_codigo_interno(self):
        codigo_original = self.produto.codigo_interno

        resposta = self.client.post(
            reverse('produtos:update', kwargs={'pk': self.produto.pk}),
            self.dados_formulario(),
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertEqual(resposta.url, self.produto.get_absolute_url())
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.codigo_interno, codigo_original)
        self.assertEqual(self.produto.preco_custo, Decimal('0.00'))
