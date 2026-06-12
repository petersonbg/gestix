from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from administracao.models import ConfiguracaoSistema, Empresa
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

    def test_recibo_exibe_dados_resumidos_do_cliente_em_a5(self):
        cliente = self.criar_cliente('Cliente Recibo', '77788899900', telefone='2744445555')
        venda = Venda.objects.create(
            cliente=cliente,
            usuario=self.user,
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            forma_pagamento=Venda.FormaPagamento.DINHEIRO,
        )

        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))

        self.assertContains(response, 'Cliente Recibo')
        self.assertContains(response, '77788899900')
        self.assertContains(response, '2744445555')
        self.assertContains(response, 'cliente.recibo@example.com')
        self.assertContains(response, 'Rua das Vendas, 10')
        self.assertNotContains(response, 'ISENTO')
        self.assertContains(response, 'GESTIX')
        self.assertContains(response, 'size: 140mm 210mm')
        self.assertContains(response, 'margin: 5mm')
        self.assertContains(response, 'height: 200mm')
        self.assertContains(response, 'Assinatura do Cliente')
        self.assertContains(response, 'assinaturas assinaturas--single')
        self.assertContains(response, 'assinatura-box')
        self.assertContains(response, 'linha-assinatura')
        self.assertContains(response, 'max-height: 25mm')
        self.assertContains(response, 'width: 130mm')
        self.assertContains(response, 'print-compact')

    def test_recibo_renderiza_vinte_produtos_sem_ocultar_itens(self):
        cliente = self.criar_cliente('Cliente Muitos Produtos', '66677788899')
        venda = Venda.objects.create(
            cliente=cliente,
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.DINHEIRO,
        )
        for indice in range(20):
            produto = Produto.objects.create(
                nome=f'Item de venda {indice + 1:02d}',
                codigo_interno=f'VEN-{indice + 1:02d}',
                unidade_medida='UN',
                preco_venda=Decimal('5.00'),
            )
            ItemVenda.objects.create(
                venda=venda,
                produto=produto,
                quantidade=1,
                valor_unitario=Decimal('5.00'),
            )
        venda.recalcular_totais()

        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.count(b'Item de venda'), 20)
        self.assertContains(response, 'R$ 100,00')
        self.assertContains(response, 'allow-page-overflow')

    def test_recibo_exibe_cabecalho_da_empresa_e_respeita_logo(self):
        empresa = Empresa.objects.create(
            nome_fantasia='Loja GESTIX',
            razao_social='GESTIX Comércio Ltda',
            cnpj='12.345.678/0001-90',
            inscricao_estadual='123.456.789',
            telefone='(27) 3333-4444',
            whatsapp='(27) 99999-8888',
            email='financeiro@gestix.test',
            logradouro='Avenida Central',
            numero='250',
            bairro='Centro',
            cidade='Vitória',
            estado='ES',
            cep='29000-000',
            logo_impressao='empresa/logos/impressao/logo-recibo.png',
        )
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.mostrar_logo_impressoes = True
        configuracao.save()
        cliente = self.criar_cliente('Cliente Empresa', '32165498700')
        venda = Venda.objects.create(cliente=cliente, usuario=self.user, total=Decimal('10.00'))

        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))

        for texto in ['Loja GESTIX', empresa.cnpj, empresa.whatsapp,
                      'Avenida Central, 250 - Centro - Vitória/ES', 'Contato:']:
            self.assertContains(response, texto)
        for texto in ['GESTIX Comércio Ltda', empresa.inscricao_estadual, empresa.email, empresa.telefone]:
            self.assertNotContains(response, texto)
        self.assertContains(response, empresa.logo_impressao.url)

        configuracao.mostrar_logo_impressoes = False
        configuracao.save()
        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))
        self.assertNotContains(response, empresa.logo_impressao.url)

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

    def test_cancelamento_simples_nao_altera_venda_finalizada_nem_parcelas(self):
        venda = self.criar_venda_crediario(total_unitario=Decimal('100.00'), parcelas=2)
        venda.finalizar(usuario=self.user)

        with self.assertRaisesMessage(ValidationError, 'Venda finalizada não pode ser cancelada'):
            venda.cancelar(usuario=self.user, motivo='Tentativa inválida.')

        venda.refresh_from_db()
        self.assertEqual(venda.status, Venda.Status.FINALIZADA)
        self.assertEqual(
            set(ContaReceber.objects.filter(venda=venda).values_list('status', flat=True)),
            {ContaReceber.Status.ABERTA},
        )


class VendaCancelamentoRascunhoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='cancelador', password='senha')
        self.user.groups.add(Group.objects.get_or_create(name='Vendedor')[0])
        self.client.force_login(self.user)
        self.cliente = Cliente.objects.create(
            nome='Cliente Cancelamento',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='12312312312',
        )
        self.produto = Produto.objects.create(
            nome='Produto Cancelamento',
            codigo_interno='CANCEL-001',
            unidade_medida='UN',
            preco_custo=Decimal('10.00'),
            preco_venda=Decimal('25.00'),
            estoque_atual=10,
        )

    def criar_venda(self, status=Venda.Status.RASCUNHO):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.PIX,
            status=status,
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=self.produto,
            quantidade=2,
            valor_unitario=Decimal('25.00'),
        )
        venda.recalcular_totais()
        return venda

    def test_nova_venda_tem_status_rascunho_e_formulario_nao_permite_status(self):
        from .forms import VendaForm

        venda = Venda(cliente=self.cliente, usuario=self.user)
        self.assertEqual(venda.status, Venda.Status.RASCUNHO)
        self.assertNotIn('status', VendaForm().fields)

    def test_cancelar_venda_em_rascunho_sem_movimentacoes(self):
        from accounts.models import LogAtividade
        from estoque.models import MovimentacaoEstoque

        venda = self.criar_venda()
        response = self.client.post(
            reverse('vendas:cancelar', kwargs={'pk': venda.pk}),
            {'motivo': 'Cliente desistiu da compra.'},
        )

        self.assertRedirects(response, venda.get_absolute_url())
        venda.refresh_from_db()
        self.produto.refresh_from_db()
        self.assertEqual(venda.status, Venda.Status.CANCELADA)
        self.assertEqual(venda.usuario_cancelamento, self.user)
        self.assertEqual(venda.motivo_cancelamento, 'Cliente desistiu da compra.')
        self.assertIsNotNone(venda.cancelada_em)
        self.assertEqual(self.produto.estoque_atual, 10)
        self.assertFalse(MovimentacaoEstoque.objects.filter(origem=f'Venda #{venda.pk}').exists())
        self.assertFalse(MovimentacaoCaixa.objects.filter(venda=venda).exists())
        self.assertFalse(ContaReceber.objects.filter(venda=venda).exists())
        self.assertTrue(LogAtividade.objects.filter(
            usuario=self.user,
            modulo='vendas',
            descricao__contains='Cliente desistiu da compra.',
        ).exists())

    def test_impedir_cancelamento_de_venda_finalizada(self):
        venda = self.criar_venda(status=Venda.Status.FINALIZADA)

        response = self.client.post(
            reverse('vendas:cancelar', kwargs={'pk': venda.pk}),
            {'motivo': 'Tentativa inválida.'},
        )

        self.assertRedirects(response, venda.get_absolute_url())
        venda.refresh_from_db()
        self.assertEqual(venda.status, Venda.Status.FINALIZADA)
        self.assertIsNone(venda.cancelada_em)

    def test_impedir_edicao_de_venda_cancelada(self):
        venda = self.criar_venda()
        venda.cancelar(usuario=self.user, motivo='Cancelada para teste.')

        response = self.client.get(reverse('vendas:update', kwargs={'pk': venda.pk}))

        self.assertRedirects(response, venda.get_absolute_url())

    def test_model_impede_alteracao_de_venda_cancelada(self):
        venda = self.criar_venda()
        venda.cancelar(usuario=self.user, motivo='Cancelada para teste.')
        venda.desconto = Decimal('1.00')

        with self.assertRaisesMessage(ValidationError, 'Venda cancelada não pode ser alterada.'):
            venda.save()

    def test_impedir_finalizacao_de_venda_cancelada(self):
        venda = self.criar_venda()
        venda.cancelar(usuario=self.user, motivo='Cancelada para teste.')

        with self.assertRaisesMessage(ValidationError, 'Venda cancelada não pode ser finalizada.'):
            venda.finalizar(usuario=self.user)

    def test_canceladas_nao_aparecem_na_listagem_ativa(self):
        ativa = self.criar_venda()
        cancelada = self.criar_venda()
        cancelada.cancelar(usuario=self.user, motivo='Não deve aparecer nas ativas.')

        response = self.client.get(reverse('vendas:list'))

        self.assertContains(response, f'#{ativa.pk}')
        self.assertNotContains(response, f'#{cancelada.pk}')
        response = self.client.get(reverse('vendas:list'), {'status': 'canceladas'})
        self.assertContains(response, f'#{cancelada.pk}')
