from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente

from .forms import VendaForm
from .models import Venda


class ClienteBuscaVendaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username='admin', password='senha', email='admin@example.com')
        self.client.login(username='admin', password='senha')

    def criar_cliente(self, nome, cpf_cnpj, telefone='27999999999', ativo=True):
        return Cliente.objects.create(
            nome=nome,
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            email=f'{nome.lower().replace(" ", ".")}@example.com',
            endereco='Rua das Vendas, 10',
            inscricao_estadual='ISENTO',
            ativo=ativo,
        )

    def test_busca_clientes_exige_login(self):
        self.client.logout()
        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'Jo'})
        self.assertEqual(response.status_code, 302)

    def test_busca_clientes_retorna_vazio_para_consulta_curta(self):
        self.criar_cliente('João da Silva', '12345678900')
        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'J'})
        self.assertEqual(response.json()['results'], [])

    def test_busca_clientes_por_nome_cpf_cnpj_e_telefone(self):
        cliente_nome = self.criar_cliente('João da Silva', '12345678900', telefone='2711111111')
        cliente_cpf = self.criar_cliente('Maria Documento', '98765432100', telefone='2722222222')
        cliente_telefone = self.criar_cliente('Pedro Telefone', '11122233344', telefone='27987654321')

        por_nome = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'João'}).json()['results']
        por_cpf = self.client.get(reverse('vendas:buscar_clientes'), {'q': '654321'}).json()['results']
        por_telefone = self.client.get(reverse('vendas:buscar_clientes'), {'q': '987654'}).json()['results']

        self.assertEqual(por_nome[0]['id'], cliente_nome.pk)
        self.assertEqual(por_cpf[0]['id'], cliente_cpf.pk)
        self.assertEqual(por_telefone[0]['id'], cliente_telefone.pk)

    def test_busca_clientes_exibe_campos_e_limita_dez_ativos(self):
        cliente = self.criar_cliente('Cliente Ativo', '22233344455', telefone='2733333333')
        self.criar_cliente('Cliente Inativo', '99988877766', ativo=False)
        for indice in range(11):
            self.criar_cliente(f'Cliente Limite {indice:02d}', f'800000000{indice:02d}')

        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'Cliente'})

        results = response.json()['results']
        self.assertEqual(len(results), 10)
        ids = [item['id'] for item in results]
        self.assertIn(cliente.pk, ids)
        self.assertNotIn(Cliente.objects.get(nome='Cliente Inativo').pk, ids)
        primeiro = results[0]
        self.assertIn('nome', primeiro)
        self.assertIn('cpf_cnpj', primeiro)
        self.assertIn('telefone', primeiro)
        self.assertIn('email', primeiro)

    def test_formulario_venda_sem_cliente_exibe_mensagem_amigavel(self):
        form = VendaForm(data={
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.DINHEIRO,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Selecione um cliente para continuar.', form.errors['cliente'])

    def test_formulario_venda_rejeita_cliente_inativo(self):
        cliente = self.criar_cliente('Cliente Inativo Form', '55566677788', ativo=False)
        form = VendaForm(data={
            'cliente': cliente.pk,
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.PIX,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Selecione um cliente ativo para continuar.', form.errors['cliente'])

    def test_formulario_venda_com_cliente_valido(self):
        cliente = self.criar_cliente('Cliente Valido', '44455566677')
        form = VendaForm(data={
            'cliente': cliente.pk,
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.PIX,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['cliente'], cliente)

    def test_recibo_exibe_dados_completos_do_cliente(self):
        cliente = self.criar_cliente('Cliente Recibo', '77788899900', telefone='2744445555')
        venda = Venda.objects.create(
            cliente=cliente,
            usuario=self.user,
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            forma_pagamento=Venda.FormaPagamento.DINHEIRO,
        )

        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))

        self.assertContains(response, 'Dados do Cliente', html=False)
        self.assertContains(response, 'Cliente Recibo')
        self.assertContains(response, '77788899900')
        self.assertContains(response, '2744445555')
        self.assertContains(response, 'cliente.recibo@example.com')
        self.assertContains(response, 'Rua das Vendas, 10')
        self.assertContains(response, 'ISENTO')

from django.utils import timezone

from caixa.models import Caixa, MovimentacaoCaixa
from contas_receber.models import ContaReceber
from produtos.models import Produto
from .models import ItemVenda


class VendaCrediarioTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='vendedor-crediario', password='senha')
        self.cliente = Cliente.objects.create(
            nome='Cliente Crediario',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='32165498700',
            telefone='27999990000',
            email='crediario@example.com',
        )
        self.produto = Produto.objects.create(
            nome='Produto Crediario',
            codigo_interno='CR001',
            unidade_medida='UN',
            preco_custo=Decimal('10.00'),
            preco_venda=Decimal('100.00'),
            estoque_atual=20,
        )

    def criar_venda_crediario(self, *, total_unitario=Decimal('100.00'), quantidade=1, parcelas=2, entrada=Decimal('0.00')):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.CREDIARIO,
            quantidade_parcelas=parcelas,
            data_primeiro_vencimento=timezone.localdate(),
            intervalo_parcelas=30,
            valor_entrada=entrada,
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=quantidade,
            valor_unitario=total_unitario,
        )
        venda.recalcular_totais()
        return venda

    def test_finalizar_venda_com_usuario_nullable_na_venda(self):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=None,
            forma_pagamento=Venda.FormaPagamento.CREDIARIO,
            quantidade_parcelas=1,
            data_primeiro_vencimento=timezone.localdate(),
            intervalo_parcelas=30,
            valor_entrada=Decimal('0.00'),
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=1,
            valor_unitario=Decimal('100.00'),
        )
        venda.recalcular_totais()

        venda.finalizar(usuario=self.user)

        venda.refresh_from_db()
        self.assertEqual(venda.status, Venda.Status.FINALIZADA)
        self.assertEqual(ContaReceber.objects.filter(venda=venda).count(), 1)

    def test_venda_crediario_com_cliente_valido_gera_parcelas_e_baixa_estoque(self):
        venda = self.criar_venda_crediario(parcelas=2)

        venda.finalizar(usuario=self.user)

        self.assertEqual(venda.status, Venda.Status.FINALIZADA)
        self.assertEqual(ContaReceber.objects.filter(venda=venda).count(), 2)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 19)

    def test_venda_crediario_sem_cliente_eh_bloqueada(self):
        venda = Venda(
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.CREDIARIO,
            quantidade_parcelas=1,
            data_primeiro_vencimento=timezone.localdate(),
        )

        with self.assertRaises(ValidationError):
            venda.full_clean()

    def test_geracao_correta_de_parcelas_com_entrada(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('1000.00'), parcelas=4, entrada=Decimal('200.00'))

        parcelas = ContaReceber.gerar_para_venda(venda)

        self.assertEqual([parcela.valor for parcela in parcelas], [Decimal('200.00')] * 4)
        self.assertEqual(sum(parcela.valor for parcela in parcelas), Decimal('800.00'))

    def test_arredondamento_de_parcelas_ajusta_ultima_parcela(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=3)

        parcelas = ContaReceber.gerar_para_venda(venda)

        self.assertEqual([parcela.valor for parcela in parcelas], [Decimal('33.33'), Decimal('33.33'), Decimal('33.34')])
        self.assertEqual(sum(parcela.valor for parcela in parcelas), Decimal('100.00'))

    def test_crediario_com_entrada_registra_apenas_entrada_no_caixa(self):
        caixa = Caixa.abrir(usuario=self.user, valor_inicial=Decimal('50.00'))
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=2, entrada=Decimal('20.00'))

        venda.finalizar(usuario=self.user)

        movimento = MovimentacaoCaixa.objects.get(venda=venda)
        self.assertEqual(movimento.tipo, MovimentacaoCaixa.Tipo.ENTRADA)
        self.assertEqual(movimento.valor, Decimal('20.00'))
        self.assertEqual(caixa.saldo_calculado(), Decimal('70.00'))
        self.assertEqual(sum(conta.valor for conta in ContaReceber.objects.filter(venda=venda)), Decimal('80.00'))

    def test_crediario_sem_entrada_nao_exige_caixa_e_nao_movimenta_caixa(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=2, entrada=Decimal('0.00'))

        venda.finalizar(usuario=self.user)

        self.assertFalse(MovimentacaoCaixa.objects.filter(venda=venda).exists())
        self.assertEqual(ContaReceber.objects.filter(venda=venda).count(), 2)

    def test_recebimento_de_parcela_com_caixa_aberto(self):
        Caixa.abrir(usuario=self.user, valor_inicial=Decimal('0.00'))
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=1)
        venda.finalizar(usuario=self.user)
        conta = ContaReceber.objects.get(venda=venda)

        conta.receber(
            usuario=self.user,
            valor_recebido=Decimal('100.00'),
            forma_recebimento=ContaReceber.FormaRecebimento.PIX,
            data_pagamento=timezone.localdate(),
        )

        conta.refresh_from_db()
        self.assertEqual(conta.status, ContaReceber.Status.PAGA)
        self.assertEqual(conta.valor_pago, Decimal('100.00'))
        self.assertTrue(MovimentacaoCaixa.objects.filter(venda=venda, valor=Decimal('100.00')).exists())

    def test_bloqueia_recebimento_sem_caixa_aberto(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=1)
        venda.finalizar(usuario=self.user)
        conta = ContaReceber.objects.get(venda=venda)

        with self.assertRaisesMessage(ValidationError, 'É necessário abrir o caixa antes de receber parcelas.'):
            conta.receber(
                usuario=self.user,
                valor_recebido=Decimal('100.00'),
                forma_recebimento=ContaReceber.FormaRecebimento.DINHEIRO,
            )

    def test_cancelamento_de_venda_crediario_cancela_parcelas_abertas(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=2)
        venda.finalizar(usuario=self.user)

        venda.cancelar()

        self.assertEqual(set(ContaReceber.objects.filter(venda=venda).values_list('status', flat=True)), {ContaReceber.Status.CANCELADA})
