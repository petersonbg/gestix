from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracao.models import Empresa
from caixa.models import Caixa, MovimentacaoCaixa
from clientes.models import Cliente
from contas_receber.models import ContaReceber
from estoque.models import MovimentacaoEstoque
from produtos.models import Produto

from .models import HistoricoOrdemServico, ItemProdutoOS, ItemServicoOS, OrdemServico, Servico


class OrdemServicoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='gerente-os', password='senha')
        self.user.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        self.client.login(username='gerente-os', password='senha')
        self.cliente = Cliente.objects.create(nome='Cliente OS', tipo_pessoa='fisica', cpf_cnpj='12345678901', telefone='27999999999')
        self.servico = Servico.objects.create(nome='Manutenção', valor_padrao=Decimal('100.00'))
        self.produto = Produto.objects.create(nome='Peça A', codigo_interno='P-OS-1', unidade_medida='UN', preco_custo=Decimal('10.00'), preco_venda=Decimal('25.00'), estoque_atual=5)

    def criar_os(self, **kwargs):
        dados = {'cliente': self.cliente, 'responsavel': self.user, 'descricao_problema': 'Equipamento não liga.'}
        dados.update(kwargs)
        return OrdemServico.objects.create(**dados)

    def test_criar_os_gera_numero_e_cliente(self):
        ordem = self.criar_os()
        self.assertTrue(ordem.numero.startswith('OS-'))
        self.assertEqual(ordem.cliente, self.cliente)

    def test_adicionar_servico_produto_e_calcular_totais(self):
        ordem = self.criar_os(desconto=Decimal('10.00'))
        ItemServicoOS.objects.create(ordem_servico=ordem, servico=self.servico, quantidade=2, valor_unitario=Decimal('100.00'))
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.recalcular_totais()
        self.assertEqual(ordem.subtotal_servicos, Decimal('200.00'))
        self.assertEqual(ordem.subtotal_produtos, Decimal('50.00'))
        self.assertEqual(ordem.total, Decimal('240.00'))

    def test_concluir_com_estoque_baixa_produto_e_registra_historico(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.concluir(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 3)
        self.assertTrue(MovimentacaoEstoque.objects.filter(origem='ORDEM_SERVICO', quantidade=2).exists())
        self.assertTrue(HistoricoOrdemServico.objects.filter(ordem_servico=ordem, acao='CONCLUSAO').exists())

    def test_bloqueia_conclusao_sem_estoque(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=6, valor_unitario=Decimal('25.00'))
        with self.assertRaisesMessage(ValidationError, 'Estoque insuficiente'):
            ordem.concluir(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)

    def test_cancelar_os_nao_baixa_estoque(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.cancelar(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)
        self.assertEqual(ordem.status, OrdemServico.Status.CANCELADA)

    def test_imprimir_os(self):
        ordem = self.criar_os()
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ORDEM DE SERVIÇO')
        self.assertContains(response, ordem.numero)

        Empresa.objects.create(
            nome_fantasia='Assistência GESTIX', razao_social='Assistência Técnica GESTIX Ltda',
            cnpj='11.222.333/0001-44', inscricao_estadual='11223344',
            telefone='(27) 3222-1111', whatsapp='(27) 97777-6666',
            email='os@gestix.test', logradouro='Rua das Oficinas', numero='80',
            bairro='Industrial', cidade='Vila Velha', estado='ES', cep='29100-000',
        )
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        for texto in ['Assistência GESTIX', 'Assistência Técnica GESTIX Ltda',
                      '11.222.333/0001-44', '11223344', '(27) 3222-1111',
                      '(27) 97777-6666', 'os@gestix.test', 'Rua das Oficinas, 80', 'Vila Velha - ES']:
            self.assertContains(response, texto)
        self.assertContains(response, 'size: A4 portrait')

    def test_filtrar_por_status(self):
        self.criar_os(status=OrdemServico.Status.ABERTA)
        self.criar_os(status=OrdemServico.Status.EM_ANDAMENTO)
        response = self.client.get(reverse('ordens_servico:list'), {'status': OrdemServico.Status.EM_ANDAMENTO})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ordens']), 1)


    def test_buscas_dinamicas_retornam_registros_ativos(self):
        for rota, termo in [('buscar_clientes', 'Cliente'), ('buscar_produtos', 'Peça'), ('buscar_servicos', 'Manutenção')]:
            response = self.client.get(reverse(f'ordens_servico:{rota}'), {'q': termo})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.json()['resultados']), 1)

    def test_pagamento_a_vista_registra_entrada_no_caixa(self):
        ordem = self.criar_os(status=OrdemServico.Status.CONCLUIDA, total=Decimal('100.00'))
        Caixa.abrir(usuario=self.user, valor_inicial=Decimal('0.00'))
        ordem.registrar_pagamento(usuario=self.user, forma_pagamento=OrdemServico.FormaPagamento.PIX, valor=Decimal('100.00'))
        self.assertTrue(MovimentacaoCaixa.objects.filter(descricao=f'Recebimento da OS nº {ordem.numero}', valor=Decimal('100.00')).exists())
        ordem.refresh_from_db()
        self.assertEqual(ordem.valor_pago, Decimal('100.00'))

    def test_pagamento_crediario_gera_parcelas_com_arredondamento(self):
        ordem = self.criar_os(status=OrdemServico.Status.CONCLUIDA, total=Decimal('100.00'))
        ordem.registrar_pagamento(
            usuario=self.user,
            forma_pagamento=OrdemServico.FormaPagamento.CREDIARIO,
            valor=Decimal('100.00'),
            parcelas=3,
            primeiro_vencimento=timezone.localdate(),
            intervalo=30,
        )
        parcelas = list(ContaReceber.objects.filter(ordem_servico=ordem).order_by('numero_parcela'))
        self.assertEqual(len(parcelas), 3)
        self.assertEqual(sum((parcela.valor for parcela in parcelas), Decimal('0.00')), Decimal('100.00'))

    def test_dashboard_mostra_ordem_atrasada(self):
        self.criar_os(data_previsao=timezone.localdate() - timedelta(days=1))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['os_atrasadas_qtd'], 1)
