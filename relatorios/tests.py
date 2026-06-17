from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import PerfilUsuario
from caixa.models import Caixa, MovimentacaoCaixa
from clientes.models import Cliente
from contas_pagar.models import CategoriaDespesa, ContaPagar
from contas_receber.models import ContaReceber
from fornecedores.models import Fornecedor
from produtos.models import Produto
from vendas.models import Venda


class RelatoriosTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='rel-admin', password='senha')
        self.gerente = User.objects.create_user(username='rel-gerente', password='senha')
        self.vendedor = User.objects.create_user(username='rel-vendedor', password='senha')
        self.estoquista = User.objects.create_user(username='rel-estoquista', password='senha')
        self.sem_perfil = User.objects.create_user(username='rel-sem', password='senha')
        PerfilUsuario.objects.create(usuario=self.admin, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        PerfilUsuario.objects.create(usuario=self.gerente, perfil=PerfilUsuario.Perfil.GERENTE)
        PerfilUsuario.objects.create(usuario=self.vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        PerfilUsuario.objects.create(usuario=self.estoquista, perfil=PerfilUsuario.Perfil.ESTOQUISTA)
        self.cliente = Cliente.objects.create(
            nome='Cliente Relatorio',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='11144477735',
        )

    def assert_acesso_negado(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('acesso_negado'))

    def criar_venda(self, dias=0, total='100.00', status=Venda.Status.FINALIZADA):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=self.vendedor,
            subtotal=Decimal(total),
            desconto=Decimal('10.00'),
            total=Decimal(total) - Decimal('10.00'),
            forma_pagamento=Venda.FormaPagamento.PIX,
            status=status,
        )
        Venda.objects.filter(pk=venda.pk).update(data=timezone.now() + timedelta(days=dias))
        venda.refresh_from_db()
        return venda

    def test_acesso_permitido_por_perfil(self):
        for usuario, url in [
            (self.admin, reverse('relatorios:contas_pagar')),
            (self.gerente, reverse('relatorios:caixa_diario')),
            (self.vendedor, reverse('relatorios:vendas')),
            (self.estoquista, reverse('relatorios:estoque_baixo')),
        ]:
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(url).status_code, 200)

    def test_acesso_negado_por_perfil(self):
        for usuario, url in [
            (self.vendedor, reverse('relatorios:contas_pagar')),
            (self.estoquista, reverse('relatorios:vendas')),
            (self.sem_perfil, reverse('relatorios:vendas')),
        ]:
            self.client.force_login(usuario)
            self.assert_acesso_negado(self.client.get(url))

    def test_filtro_de_vendas_por_data_e_calculo_de_totais(self):
        venda_periodo = self.criar_venda(dias=0, total='120.00')
        self.criar_venda(dias=-10, total='300.00')
        hoje = timezone.localdate().isoformat()
        self.client.force_login(self.gerente)

        response = self.client.get(reverse('relatorios:vendas'), {'data_inicial': hoje, 'data_final': hoje})

        self.assertEqual(response.status_code, 200)
        self.assertIn(venda_periodo, list(response.context['vendas']))
        self.assertEqual(response.context['resumo']['quantidade'], 1)
        self.assertEqual(response.context['resumo']['subtotal'], Decimal('120'))
        self.assertEqual(response.context['resumo']['desconto'], Decimal('10'))
        self.assertEqual(response.context['resumo']['total'], Decimal('110'))

    def test_relatorio_de_estoque_baixo(self):
        Produto.objects.create(
            nome='Produto Baixo',
            unidade_medida='UN',
            preco_custo=Decimal('5.00'),
            preco_venda=Decimal('10.00'),
            estoque_atual=2,
            estoque_minimo=5,
        )
        Produto.objects.create(
            nome='Produto Normal',
            unidade_medida='UN',
            preco_venda=Decimal('10.00'),
            estoque_atual=10,
            estoque_minimo=5,
        )
        self.client.force_login(self.estoquista)

        response = self.client.get(reverse('relatorios:estoque_baixo'))

        self.assertContains(response, 'Produto Baixo')
        self.assertNotContains(response, 'Produto Normal')
        self.assertEqual(response.context['resumo']['quantidade'], 1)
        self.assertEqual(response.context['resumo']['total_falta'], 3)
        self.assertEqual(response.context['resumo']['valor_reposicao'], Decimal('15.00'))

    def test_exportacao_csv_de_vendas(self):
        self.criar_venda()
        self.client.force_login(self.admin)

        response = self.client.get(reverse('relatorios:vendas'), {'formato': 'csv'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv; charset=utf-8')
        self.assertIn('relatorio_vendas.csv', response['Content-Disposition'])
        self.assertIn('Cliente Relatorio', response.content.decode('utf-8'))

    def test_impressao_de_estoque_baixo(self):
        Produto.objects.create(
            nome='Produto Impressao',
            unidade_medida='UN',
            preco_venda=Decimal('10.00'),
            estoque_atual=0,
            estoque_minimo=1,
        )
        self.client.force_login(self.admin)

        response = self.client.get(reverse('relatorios:estoque_baixo'), {'imprimir': '1'})

        self.assertContains(response, '@page')
        self.assertContains(response, 'Produto Impressao')

    def test_contas_e_caixa_renderizam_resumos(self):
        fornecedor = Fornecedor.objects.create(razao_social='Fornecedor Relatorio', cnpj='11222333000181')
        categoria = CategoriaDespesa.objects.create(nome='Categoria Relatorio')
        ContaReceber.objects.create(
            cliente=self.cliente,
            venda=self.criar_venda(),
            numero_parcela=1,
            total_parcelas=1,
            data_vencimento=timezone.localdate() - timedelta(days=1),
            valor=Decimal('50.00'),
        )
        ContaPagar.objects.create(
            descricao='Conta Relatorio',
            fornecedor=fornecedor,
            categoria=categoria,
            data_vencimento=timezone.localdate() - timedelta(days=1),
            valor=Decimal('30.00'),
        )
        caixa = Caixa.objects.create(usuario_abertura=self.admin, valor_inicial=Decimal('10.00'))
        MovimentacaoCaixa.objects.create(
            caixa=caixa,
            tipo=MovimentacaoCaixa.Tipo.VENDA,
            descricao='Venda teste',
            valor=Decimal('20.00'),
            forma_pagamento=MovimentacaoCaixa.FormaPagamento.DINHEIRO,
            usuario=self.admin,
        )
        self.client.force_login(self.gerente)

        receber = self.client.get(reverse('relatorios:contas_receber'))
        pagar = self.client.get(reverse('relatorios:contas_pagar'))
        caixa_response = self.client.get(reverse('relatorios:caixa_diario'))

        self.assertEqual(receber.context['resumo']['parcelas_atrasadas'], 1)
        self.assertEqual(pagar.context['resumo']['atrasado'], Decimal('30'))
        self.assertEqual(caixa_response.context['resumo']['vendido'], Decimal('20'))
