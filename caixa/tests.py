from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from clientes.models import Cliente
from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from .models import Caixa, MovimentacaoCaixa


class CaixaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='vendedor', password='senha')
        self.cliente = Cliente.objects.create(
            nome='Cliente Caixa',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='12345678900',
        )
        self.produto = Produto.objects.create(
            nome='Produto Caixa',
            codigo_interno='CX001',
            unidade_medida='UN',
            preco_custo=Decimal('5.00'),
            preco_venda=Decimal('10.00'),
            estoque_atual=10,
        )

    def criar_venda(self):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.PIX,
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=2,
            valor_unitario=Decimal('10.00'),
        )
        venda.recalcular_totais()
        return venda

    def test_abrir_caixa(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))

        self.assertEqual(caixa.status, Caixa.Status.ABERTO)
        self.assertEqual(caixa.valor_inicial, Decimal('100.00'))
        self.assertEqual(Caixa.caixa_aberto_do_usuario(self.user), caixa)

    def test_impede_dois_caixas_abertos_para_o_mesmo_usuario(self):
        Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))

        with self.assertRaises(ValidationError):
            Caixa.abrir(usuario=self.user, valor_inicial=Decimal('50.00'))

    def test_lancar_suprimento(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))

        MovimentacaoCaixa.registrar(
            caixa=caixa,
            tipo=MovimentacaoCaixa.Tipo.SUPRIMENTO,
            descricao='Troco adicional',
            valor=Decimal('25.00'),
            usuario=self.user,
        )

        self.assertEqual(caixa.saldo_calculado(), Decimal('125.00'))

    def test_lancar_sangria(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))

        MovimentacaoCaixa.registrar(
            caixa=caixa,
            tipo=MovimentacaoCaixa.Tipo.SANGRIA,
            descricao='Retirada parcial',
            valor=Decimal('30.00'),
            usuario=self.user,
        )

        self.assertEqual(caixa.saldo_calculado(), Decimal('70.00'))

    def test_finalizar_venda_com_caixa_aberto_registra_movimentacao(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))
        venda = self.criar_venda()

        venda.finalizar(usuario=self.user)

        movimentacao = MovimentacaoCaixa.objects.get(venda=venda)
        self.assertEqual(movimentacao.caixa, caixa)
        self.assertEqual(movimentacao.tipo, MovimentacaoCaixa.Tipo.VENDA)
        self.assertEqual(movimentacao.valor, Decimal('20.00'))
        self.assertEqual(movimentacao.forma_pagamento, Venda.FormaPagamento.PIX)
        self.assertEqual(caixa.saldo_calculado(), Decimal('120.00'))

    def test_bloqueia_venda_sem_caixa_aberto(self):
        venda = self.criar_venda()

        with self.assertRaisesMessage(ValidationError, 'É necessário abrir o caixa antes de finalizar vendas.'):
            venda.finalizar(usuario=self.user)

        venda.refresh_from_db()
        self.assertEqual(venda.status, Venda.Status.RASCUNHO)
        self.assertFalse(MovimentacaoCaixa.objects.filter(venda=venda).exists())

    def test_fechar_caixa(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))
        MovimentacaoCaixa.registrar(
            caixa=caixa,
            tipo=MovimentacaoCaixa.Tipo.SUPRIMENTO,
            descricao='Troco',
            valor=Decimal('20.00'),
            usuario=self.user,
        )

        caixa.fechar(usuario=self.user, valor_fechamento_informado=Decimal('115.00'))

        caixa.refresh_from_db()
        self.assertEqual(caixa.status, Caixa.Status.FECHADO)
        self.assertEqual(caixa.valor_fechamento_calculado, Decimal('120.00'))
        self.assertEqual(caixa.diferenca, Decimal('-5.00'))

    def test_impede_movimentacao_em_caixa_fechado(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('100.00'))
        caixa.fechar(usuario=self.user, valor_fechamento_informado=Decimal('100.00'))

        with self.assertRaises(ValidationError):
            MovimentacaoCaixa.registrar(
                caixa=caixa,
                tipo=MovimentacaoCaixa.Tipo.SAIDA,
                descricao='Saída após fechamento',
                valor=Decimal('10.00'),
                usuario=self.user,
            )

