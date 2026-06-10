from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from caixa.models import Caixa, MovimentacaoCaixa
from fornecedores.models import Fornecedor

from .models import CategoriaDespesa, ContaPagar


class ContaPagarTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='gerente-pagar', password='senha')
        self.user.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        self.client.login(username='gerente-pagar', password='senha')
        self.categoria = CategoriaDespesa.objects.create(nome='Energia Teste')
        self.fornecedor = Fornecedor.objects.create(razao_social='Fornecedor Teste', cnpj='12345678000199')

    def criar_conta(self, **kwargs):
        dados = {
            'descricao': 'Conta de energia',
            'fornecedor': self.fornecedor,
            'categoria': self.categoria,
            'data_emissao': timezone.localdate(),
            'data_vencimento': timezone.localdate() + timedelta(days=5),
            'valor': Decimal('100.00'),
            'usuario_criacao': self.user,
        }
        dados.update(kwargs)
        return ContaPagar.objects.create(**dados)

    def test_criar_conta_a_pagar(self):
        conta = self.criar_conta()

        self.assertEqual(conta.status, ContaPagar.Status.ABERTA)
        self.assertEqual(conta.saldo, Decimal('100.00'))

    def test_pagar_conta(self):
        conta = self.criar_conta()

        conta.pagar(
            usuario=self.user,
            valor_pago=Decimal('100.00'),
            forma_pagamento=ContaPagar.FormaPagamento.PIX,
            data_pagamento=timezone.localdate(),
        )

        conta.refresh_from_db()
        self.assertEqual(conta.status, ContaPagar.Status.PAGA)
        self.assertEqual(conta.valor_pago, Decimal('100.00'))
        self.assertEqual(conta.usuario_pagamento, self.user)

    def test_impede_pagamento_acima_do_valor(self):
        conta = self.criar_conta()

        with self.assertRaises(ValidationError):
            conta.pagar(
                usuario=self.user,
                valor_pago=Decimal('101.00'),
                forma_pagamento=ContaPagar.FormaPagamento.PIX,
                data_pagamento=timezone.localdate(),
            )

    def test_impede_pagamento_de_conta_cancelada(self):
        conta = self.criar_conta(status=ContaPagar.Status.CANCELADA)

        with self.assertRaisesMessage(ValidationError, 'Não é possível pagar conta cancelada.'):
            conta.pagar(
                usuario=self.user,
                valor_pago=Decimal('100.00'),
                forma_pagamento=ContaPagar.FormaPagamento.PIX,
                data_pagamento=timezone.localdate(),
            )

    def test_impede_pagamento_duplicado(self):
        conta = self.criar_conta(status=ContaPagar.Status.PAGA, valor_pago=Decimal('100.00'), data_pagamento=timezone.localdate())

        with self.assertRaisesMessage(ValidationError, 'Esta conta já está paga.'):
            conta.pagar(
                usuario=self.user,
                valor_pago=Decimal('1.00'),
                forma_pagamento=ContaPagar.FormaPagamento.PIX,
                data_pagamento=timezone.localdate(),
            )

    def test_marca_conta_vencida_como_atrasada_dinamicamente(self):
        conta = self.criar_conta(data_vencimento=timezone.localdate() - timedelta(days=2))

        self.assertEqual(conta.status_exibicao, ContaPagar.Status.ATRASADA)
        self.assertEqual(conta.dias_atraso, 2)

    def test_pagamento_em_dinheiro_movimenta_caixa(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('200.00'))
        conta = self.criar_conta(valor=Decimal('80.00'))

        conta.pagar(
            usuario=self.user,
            valor_pago=Decimal('80.00'),
            forma_pagamento=ContaPagar.FormaPagamento.DINHEIRO,
            data_pagamento=timezone.localdate(),
        )

        movimento = MovimentacaoCaixa.objects.get(descricao='Pagamento de conta: Conta de energia')
        self.assertEqual(movimento.tipo, MovimentacaoCaixa.Tipo.SAIDA)
        self.assertEqual(movimento.valor, Decimal('80.00'))
        self.assertEqual(caixa.saldo_calculado(), Decimal('120.00'))

    def test_dashboard_exibe_contas_a_pagar_atrasadas(self):
        self.criar_conta(data_vencimento=timezone.localdate() - timedelta(days=3), valor=Decimal('90.00'))

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Contas a pagar atrasadas')
        self.assertEqual(response.context['contas_pagar_atrasadas_qtd'], 1)
        self.assertEqual(response.context['contas_pagar_atrasadas_total'], Decimal('90.00'))
