from datetime import date, timedelta

from decimal import Decimal
from time import perf_counter
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from clientes.models import Cliente
from caixa.models import Caixa, MovimentacaoCaixa
from contas_pagar.models import CategoriaDespesa, ContaPagar
from contas_receber.models import ContaReceber
from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from administracao.models import ConfiguracaoSistema
from accounts.models import PerfilUsuario
from .services import (
    buscar_aniversariantes,
    buscar_aniversariantes_configurados,
    buscar_dashboard_executiva,
    buscar_dashboard_financeira,
    grafico_projecao_financeira,
)


class AniversariantesServiceTests(TestCase):
    def criar_cliente(self, nome, data_nascimento=None, ativo=True):
        return Cliente.objects.create(
            nome=nome,
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj=f'{nome}-cpf',
            data_nascimento=data_nascimento,
            ativo=ativo,
        )

    def test_cliente_sem_data_nao_gera_notificacao(self):
        self.criar_cliente('Sem Data')
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_cliente_inativo_nao_gera_notificacao(self):
        self.criar_cliente('Inativo', date(1990, 6, 1), ativo=False)
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_aniversario_no_dia_atual(self):
        cliente = self.criar_cliente('Hoje', date(1990, 6, 1))
        resultado = buscar_aniversariantes(0, hoje=date(2026, 6, 1))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 0)
        self.assertEqual(resultado[0].idade, 36)

    def test_aniversario_dentro_do_periodo_de_antecedencia(self):
        cliente = self.criar_cliente('Em Breve', date(1990, 6, 10))
        resultado = buscar_aniversariantes(15, hoje=date(2026, 6, 1))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 9)

    def test_aniversario_fora_do_periodo(self):
        self.criar_cliente('Fora', date(1990, 6, 20))
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_aniversario_na_virada_do_ano(self):
        cliente = self.criar_cliente('Virada', date(1990, 1, 2))
        resultado = buscar_aniversariantes(7, hoje=date(2026, 12, 28))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 5)
        self.assertEqual(resultado[0].data_aniversario_no_ano, date(2027, 1, 2))

    def test_aniversario_29_fevereiro_em_ano_nao_bissexto(self):
        cliente = self.criar_cliente('Bissexto', date(1992, 2, 29))
        resultado = buscar_aniversariantes(0, hoje=date(2027, 2, 28))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].data_aniversario_no_ano, date(2027, 2, 28))


class DashboardAniversariantesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='senha')
        PerfilUsuario.objects.create(usuario=self.user, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        self.client.login(username='admin', password='senha')

    def test_dashboard_exibe_nova_estrutura_financeira(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Indicadores Financeiros Principais')
        self.assertContains(response, 'Financeiro Imediato')
        self.assertContains(response, 'Alertas Financeiros')
        self.assertNotContains(response, 'Endereço de acesso na rede')

    def test_notificacoes_ativadas_no_dashboard(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = True
        configuracao.dias_antecedencia_aniversario = 7
        configuracao.save()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Aniversariantes')

    def test_notificacoes_desativadas_no_dashboard(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = False
        configuracao.dias_antecedencia_aniversario = 7
        configuracao.save()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Notificações de aniversário desativadas.')
        self.assertEqual(response.context['aniversariantes'], [])

    def test_configuracao_padrao_e_criada_automaticamente(self):
        ConfiguracaoSistema.objects.all().delete()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        configuracao = ConfiguracaoSistema.objects.get(pk=1)
        self.assertTrue(configuracao.notificacoes_aniversario_ativas)
        self.assertEqual(configuracao.dias_antecedencia_aniversario, 0)
        self.assertEqual(response.context['configuracao_sistema'], configuracao)

    @patch('dashboard.services.buscar_aniversariantes')
    def test_servico_usa_dias_de_antecedencia_configurados(self, buscar_mock):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = True
        configuracao.dias_antecedencia_aniversario = 12
        configuracao.save()
        buscar_mock.return_value = []
        hoje = date(2026, 6, 1)

        configuracao_retornada, aniversariantes = buscar_aniversariantes_configurados(hoje=hoje)

        self.assertEqual(configuracao_retornada, configuracao)
        self.assertEqual(aniversariantes, [])
        buscar_mock.assert_called_once_with(12, hoje=hoje)

    @patch('dashboard.services.buscar_aniversariantes')
    def test_servico_nao_busca_clientes_quando_notificacoes_estao_desativadas(self, buscar_mock):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = False
        configuracao.dias_antecedencia_aniversario = 30
        configuracao.save()

        configuracao_retornada, aniversariantes = buscar_aniversariantes_configurados()

        self.assertEqual(configuracao_retornada, configuracao)
        self.assertEqual(aniversariantes, [])
        buscar_mock.assert_not_called()


class DashboardFinanceiraTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='gerente', password='senha')
        PerfilUsuario.objects.create(usuario=self.user, perfil=PerfilUsuario.Perfil.GERENTE)
        self.client.login(username='gerente', password='senha')
        self.cliente = Cliente.objects.create(
            nome='Cliente Atraso',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='atraso-001',
        )
        self.venda = Venda.objects.create(cliente=self.cliente, usuario=self.user)
        self.categoria = CategoriaDespesa.objects.create(nome='Operacional')
        self.caixa = Caixa.objects.create(
            usuario_abertura=self.user,
            valor_inicial=Decimal('100.00'),
        )

    def criar_conta_receber(self, *, vencimento=None, valor=Decimal('100.00'), status=ContaReceber.Status.ABERTA, indice=1):
        return ContaReceber.objects.create(
            venda=self.venda,
            cliente=self.cliente,
            numero_parcela=indice,
            total_parcelas=10,
            data_vencimento=vencimento or timezone.localdate(),
            valor=valor,
            status=status,
        )

    def criar_conta_pagar(self, *, vencimento=None, valor=Decimal('80.00'), status=ContaPagar.Status.ABERTA, data_pagamento=None):
        return ContaPagar.objects.create(
            descricao=f'Despesa {ContaPagar.objects.count() + 1}',
            categoria=self.categoria,
            data_vencimento=vencimento or timezone.localdate(),
            data_pagamento=data_pagamento,
            valor=valor,
            valor_pago=valor if status == ContaPagar.Status.PAGA else Decimal('0.00'),
            status=status,
        )

    def criar_movimento(self, valor, forma=MovimentacaoCaixa.FormaPagamento.DINHEIRO, data=None):
        movimento = MovimentacaoCaixa.objects.create(
            caixa=self.caixa,
            tipo=MovimentacaoCaixa.Tipo.VENDA,
            descricao='Receita de teste',
            valor=valor,
            forma_pagamento=forma,
            usuario=self.user,
        )
        if data:
            MovimentacaoCaixa.objects.filter(pk=movimento.pk).update(data=data)
        return movimento

    def test_indicadores_mensais_calculam_receita_despesa_lucro_e_variacao(self):
        hoje = timezone.localdate()
        mes_anterior = (hoje.replace(day=1) - timedelta(days=1)).replace(day=10)
        self.criar_movimento(Decimal('300.00'))
        self.criar_movimento(
            Decimal('200.00'),
            data=timezone.now().replace(
                year=mes_anterior.year,
                month=mes_anterior.month,
                day=mes_anterior.day,
                hour=12,
                minute=0,
                second=0,
                microsecond=0,
            ),
        )
        self.criar_conta_pagar(
            valor=Decimal('80.00'),
            status=ContaPagar.Status.PAGA,
            data_pagamento=hoje,
        )

        contexto = buscar_dashboard_financeira(self.user, hoje=hoje)

        self.assertEqual(contexto['receitas_mes'], Decimal('300.00'))
        self.assertEqual(contexto['receitas_mes_anterior'], Decimal('200.00'))
        self.assertEqual(contexto['receitas_variacao'], Decimal('50.00'))
        self.assertEqual(contexto['despesas_mes'], Decimal('80.00'))
        self.assertEqual(contexto['lucro_estimado'], Decimal('220.00'))

    def test_saldo_disponivel_separa_caixa_e_fluxo_bancario(self):
        self.criar_movimento(Decimal('50.00'))
        self.criar_movimento(Decimal('200.00'), MovimentacaoCaixa.FormaPagamento.PIX)
        self.criar_conta_pagar(
            valor=Decimal('40.00'),
            status=ContaPagar.Status.PAGA,
            data_pagamento=timezone.localdate(),
        )
        ContaPagar.objects.filter(status=ContaPagar.Status.PAGA).update(
            forma_pagamento=ContaPagar.FormaPagamento.PIX
        )

        contexto = buscar_dashboard_financeira(self.user)

        self.assertEqual(contexto['saldo_caixa'], Decimal('150.00'))
        self.assertEqual(contexto['saldo_bancario'], Decimal('160.00'))
        self.assertEqual(contexto['saldo_disponivel'], Decimal('310.00'))

    def test_financeiro_imediato_e_alertas_usam_saldo_em_aberto(self):
        hoje = timezone.localdate()
        vencida = self.criar_conta_receber(
            vencimento=hoje - timedelta(days=2),
            valor=Decimal('100.00'),
            indice=1,
        )
        ContaReceber.objects.filter(pk=vencida.pk).update(valor_pago=Decimal('25.00'))
        self.criar_conta_receber(vencimento=hoje, valor=Decimal('50.00'), indice=2)
        self.criar_conta_pagar(vencimento=hoje - timedelta(days=1), valor=Decimal('80.00'))
        self.criar_conta_pagar(vencimento=hoje, valor=Decimal('30.00'))
        Produto.objects.create(
            nome='Produto baixo',
            unidade_medida='UN',
            preco_venda=Decimal('10.00'),
            estoque_atual=1,
            estoque_minimo=3,
        )

        contexto = buscar_dashboard_financeira(self.user, hoje=hoje)

        self.assertEqual(contexto['receber_atrasadas_total'], Decimal('75.00'))
        self.assertEqual(contexto['receber_hoje_total'], Decimal('50.00'))
        self.assertEqual(contexto['pagar_atrasadas_total'], Decimal('80.00'))
        self.assertEqual(contexto['pagar_hoje_total'], Decimal('30.00'))
        self.assertEqual(contexto['clientes_inadimplentes_qtd'], 1)
        self.assertEqual(contexto['estoque_baixo_qtd'], 1)
        self.assertTrue(contexto['tem_alertas_financeiros'])

    def test_sem_alertas_exibe_mensagem_padrao(self):
        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Não existem alertas financeiros.')

    def test_consultas_financeiras_permanecem_agregadas_e_sem_n_mais_um(self):
        for indice in range(1, 8):
            cliente = Cliente.objects.create(
                nome=f'Cliente {indice}',
                tipo_pessoa=Cliente.TipoPessoa.FISICA,
                cpf_cnpj=f'financeiro-{indice}',
            )
            venda = Venda.objects.create(cliente=cliente, usuario=self.user)
            ContaReceber.objects.create(
                venda=venda,
                cliente=cliente,
                numero_parcela=1,
                total_parcelas=1,
                data_vencimento=timezone.localdate() - timedelta(days=indice),
                valor=Decimal('10.00'),
            )

        with CaptureQueriesContext(connection) as consultas:
            contexto = buscar_dashboard_financeira(self.user)
            [conta.cliente.nome for conta in contexto['alertas_contas_vencidas']]

        self.assertLessEqual(len(consultas), 25)

    def test_vendedor_visualiza_apenas_contas_receber_do_proprio_escopo(self):
        vendedor = get_user_model().objects.create_user(username='vendedor-dashboard', password='senha')
        PerfilUsuario.objects.create(usuario=vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        venda_vendedor = Venda.objects.create(cliente=self.cliente, usuario=vendedor)
        ContaReceber.objects.create(
            venda=venda_vendedor,
            cliente=self.cliente,
            numero_parcela=1,
            total_parcelas=1,
            data_vencimento=timezone.localdate(),
            valor=Decimal('70.00'),
        )
        self.criar_conta_receber(valor=Decimal('90.00'), indice=3)
        self.client.logout()
        self.client.login(username='vendedor-dashboard', password='senha')

        response = self.client.get(reverse('dashboard'))

        self.assertFalse(response.context['dashboard_acesso_total'])
        self.assertTrue(response.context['dashboard_acesso_receber'])
        self.assertEqual(response.context['receber_hoje_total'], Decimal('70.00'))
        self.assertNotContains(response, 'Receitas do Mês')
        self.assertNotContains(response, 'Contas a Pagar Hoje')

    def test_estoquista_visualiza_somente_alerta_de_estoque(self):
        estoquista = get_user_model().objects.create_user(username='estoquista-dashboard', password='senha')
        PerfilUsuario.objects.create(usuario=estoquista, perfil=PerfilUsuario.Perfil.ESTOQUISTA)
        Produto.objects.create(
            nome='Item crítico',
            unidade_medida='UN',
            preco_venda=Decimal('10.00'),
            estoque_atual=0,
            estoque_minimo=2,
        )
        self.client.logout()
        self.client.login(username='estoquista-dashboard', password='senha')

        response = self.client.get(reverse('dashboard'))

        self.assertFalse(response.context['dashboard_acesso_total'])
        self.assertFalse(response.context['dashboard_acesso_receber'])
        self.assertTrue(response.context['dashboard_acesso_estoque'])
        self.assertContains(response, 'Item crítico')
        self.assertNotContains(response, 'Financeiro Imediato')


class DashboardExecutivaTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.gerente = User.objects.create_user(username='executivo-gerente', password='senha')
        PerfilUsuario.objects.create(usuario=self.gerente, perfil=PerfilUsuario.Perfil.GERENTE)
        self.vendedor = User.objects.create_user(
            username='executivo-vendedor',
            first_name='Vera',
            last_name='Silva',
            password='senha',
        )
        PerfilUsuario.objects.create(usuario=self.vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        self.cliente_a = Cliente.objects.create(
            nome='Cliente Executivo A',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='exec-a',
        )
        self.cliente_b = Cliente.objects.create(
            nome='Cliente Executivo B',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='exec-b',
        )
        self.produto_a = Produto.objects.create(
            nome='Produto Executivo A',
            unidade_medida='UN',
            preco_custo=Decimal('40.00'),
            preco_venda=Decimal('100.00'),
        )
        self.produto_b = Produto.objects.create(
            nome='Produto Executivo B',
            unidade_medida='UN',
            preco_custo=Decimal('20.00'),
            preco_venda=Decimal('50.00'),
        )
        self.categoria = CategoriaDespesa.objects.create(nome='Executiva')
        self.caixa = Caixa.objects.create(usuario_abertura=self.gerente, valor_inicial=Decimal('100.00'))

    def criar_venda(self, cliente, vendedor, produto, quantidade, valor_unitario):
        total = Decimal(valor_unitario) * quantidade
        venda = Venda.objects.create(
            cliente=cliente,
            usuario=vendedor,
            status=Venda.Status.FINALIZADA,
            subtotal=total,
            total=total,
        )
        ItemVenda.objects.create(
            venda=venda,
            produto=produto,
            quantidade=quantidade,
            valor_unitario=valor_unitario,
        )
        return venda

    def test_rankings_ticket_margem_e_vendedores(self):
        self.criar_venda(self.cliente_a, self.vendedor, self.produto_a, 2, Decimal('100.00'))
        self.criar_venda(self.cliente_b, self.gerente, self.produto_b, 1, Decimal('50.00'))

        contexto = buscar_dashboard_executiva(self.gerente)

        self.assertEqual(contexto['vendas_mes_total'], Decimal('250.00'))
        self.assertEqual(contexto['vendas_mes_quantidade'], 2)
        self.assertEqual(contexto['ticket_medio'], Decimal('125.00'))
        self.assertEqual(contexto['lucro_vendas_estimado'], Decimal('150.00'))
        self.assertEqual(contexto['margem_media'], Decimal('60.00'))
        self.assertEqual(contexto['top_clientes'][0]['cliente__nome'], 'Cliente Executivo A')
        self.assertEqual(contexto['top_produtos'][0]['produto__nome'], 'Produto Executivo A')
        self.assertEqual(contexto['top_vendedores'][0]['vendedor_nome'], 'Vera Silva')

    def test_inadimplencia_e_ranking_por_cliente(self):
        venda = self.criar_venda(
            self.cliente_a, self.vendedor, self.produto_a, 1, Decimal('100.00')
        )
        ContaReceber.objects.create(
            venda=venda,
            cliente=self.cliente_a,
            numero_parcela=1,
            total_parcelas=2,
            data_vencimento=timezone.localdate() - timedelta(days=12),
            valor=Decimal('100.00'),
            valor_pago=Decimal('20.00'),
        )
        ContaReceber.objects.create(
            venda=venda,
            cliente=self.cliente_a,
            numero_parcela=2,
            total_parcelas=2,
            data_vencimento=timezone.localdate() + timedelta(days=10),
            valor=Decimal('120.00'),
        )

        contexto = buscar_dashboard_executiva(self.gerente)

        self.assertEqual(contexto['inadimplencia_valor'], Decimal('80.00'))
        self.assertEqual(contexto['inadimplencia_percentual'], Decimal('40.00'))
        self.assertEqual(contexto['ranking_inadimplencia'][0]['valor_vencido'], Decimal('80.00'))
        self.assertEqual(contexto['ranking_inadimplencia'][0]['dias_atraso'], 12)

    def test_capital_giro_classifica_cobertura(self):
        ContaPagar.objects.create(
            descricao='Despesa futura executiva',
            categoria=self.categoria,
            data_vencimento=timezone.localdate() + timedelta(days=10),
            valor=Decimal('120.00'),
        )

        financeiro = buscar_dashboard_financeira(self.gerente)
        contexto = buscar_dashboard_executiva(
            self.gerente,
            saldo_disponivel=financeiro['saldo_disponivel'],
        )

        self.assertEqual(contexto['despesas_30_dias'], Decimal('120.00'))
        self.assertEqual(contexto['capital_giro'], Decimal('-20.00'))
        self.assertEqual(contexto['capital_giro_situacao'], 'ATENCAO')

    def test_vendedor_recebe_apenas_rankings_e_indicadores_proprios(self):
        self.criar_venda(self.cliente_a, self.vendedor, self.produto_a, 1, Decimal('100.00'))
        self.criar_venda(self.cliente_b, self.gerente, self.produto_b, 1, Decimal('50.00'))

        contexto = buscar_dashboard_executiva(self.vendedor)

        self.assertEqual(contexto['vendas_mes_total'], Decimal('100.00'))
        self.assertEqual(len(contexto['top_clientes']), 1)
        self.assertEqual(contexto['top_clientes'][0]['cliente__nome'], 'Cliente Executivo A')
        self.assertNotIn('top_vendedores', contexto)
        self.assertNotIn('capital_giro', contexto)

    def test_estoquista_nao_recebe_indicadores_executivos(self):
        estoquista = get_user_model().objects.create_user(username='executivo-estoquista')
        PerfilUsuario.objects.create(usuario=estoquista, perfil=PerfilUsuario.Perfil.ESTOQUISTA)

        self.assertEqual(
            buscar_dashboard_executiva(estoquista),
            {'dashboard_executiva_visivel': False},
        )

    def test_projecao_financeira_calcula_periodos_acumulados(self):
        venda = self.criar_venda(
            self.cliente_a, self.vendedor, self.produto_a, 1, Decimal('100.00')
        )
        ContaReceber.objects.create(
            venda=venda,
            cliente=self.cliente_a,
            numero_parcela=1,
            total_parcelas=1,
            data_vencimento=timezone.localdate() + timedelta(days=6),
            valor=Decimal('100.00'),
        )
        ContaPagar.objects.create(
            descricao='Pagar em quinze dias',
            categoria=self.categoria,
            data_vencimento=timezone.localdate() + timedelta(days=14),
            valor=Decimal('40.00'),
        )

        dados = grafico_projecao_financeira()

        self.assertEqual(dados['labels'], ['7 dias', '15 dias', '30 dias', '60 dias', '90 dias'])
        self.assertEqual(dados['receber'][0], 100.0)
        self.assertEqual(dados['pagar'][0], 0.0)
        self.assertEqual(dados['saldo'][1], 60.0)

    def test_servicos_executivos_carregam_em_menos_de_tres_segundos(self):
        for indice in range(30):
            self.criar_venda(
                self.cliente_a,
                self.vendedor,
                self.produto_a,
                1,
                Decimal('100.00'),
            )

        inicio = perf_counter()
        with CaptureQueriesContext(connection) as consultas:
            financeiro = buscar_dashboard_financeira(self.gerente)
            buscar_dashboard_executiva(
                self.gerente,
                saldo_disponivel=financeiro['saldo_disponivel'],
            )
        duracao = perf_counter() - inicio

        self.assertLess(duracao, 3)
        self.assertLessEqual(len(consultas), 40)


class DashboardGraficosApiTests(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.user = User.objects.create_user(username='graficos-admin', password='senha')
        PerfilUsuario.objects.create(usuario=self.user, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        self.client.login(username='graficos-admin', password='senha')
        self.cliente = Cliente.objects.create(
            nome='Cliente Gráficos',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='graficos-001',
        )
        self.caixa = Caixa.objects.create(usuario_abertura=self.user, valor_inicial=Decimal('100.00'))
        self.categoria = CategoriaDespesa.objects.create(nome='Gráficos')

    def movimento(self, valor, forma=MovimentacaoCaixa.FormaPagamento.DINHEIRO, venda=None, descricao='Receita'):
        return MovimentacaoCaixa.objects.create(
            caixa=self.caixa,
            tipo=MovimentacaoCaixa.Tipo.VENDA,
            descricao=descricao,
            valor=valor,
            forma_pagamento=forma,
            venda=venda,
            usuario=self.user,
        )

    def test_endpoint_fluxo_retorna_doze_meses_e_tres_series(self):
        self.movimento(Decimal('150.00'))
        ContaPagar.objects.create(
            descricao='Despesa do gráfico',
            categoria=self.categoria,
            data_vencimento=timezone.localdate(),
            data_pagamento=timezone.localdate(),
            valor=Decimal('40.00'),
            valor_pago=Decimal('40.00'),
            status=ContaPagar.Status.PAGA,
        )

        response = self.client.get(reverse('dashboard_api_fluxo_financeiro'))
        dados = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(dados['labels']), 12)
        self.assertEqual(dados['receitas'][-1], 150.0)
        self.assertEqual(dados['despesas'][-1], 40.0)
        self.assertEqual(dados['lucro'][-1], 110.0)

    def test_endpoint_formas_classifica_recebimento_de_parcela_como_crediario(self):
        venda = Venda.objects.create(
            cliente=self.cliente,
            usuario=self.user,
            forma_pagamento=Venda.FormaPagamento.CREDIARIO,
        )
        self.movimento(
            Decimal('90.00'),
            forma=MovimentacaoCaixa.FormaPagamento.PIX,
            venda=venda,
            descricao='Recebimento de parcela - Venda #1',
        )
        self.movimento(Decimal('30.00'), forma=MovimentacaoCaixa.FormaPagamento.PIX)

        response = self.client.get(reverse('dashboard_api_formas_pagamento'))
        dados = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(dados['labels'], ['PIX', 'Dinheiro', 'Cartão Débito', 'Cartão Crédito', 'Crediário'])
        self.assertEqual(dados['valores'][0], 30.0)
        self.assertEqual(dados['valores'][4], 90.0)

    def test_endpoint_contas_compara_saldos_dos_proximos_trinta_dias(self):
        venda = Venda.objects.create(cliente=self.cliente, usuario=self.user)
        ContaReceber.objects.create(
            venda=venda,
            cliente=self.cliente,
            numero_parcela=1,
            total_parcelas=1,
            data_vencimento=timezone.localdate() + timedelta(days=10),
            valor=Decimal('120.00'),
            valor_pago=Decimal('20.00'),
        )
        ContaPagar.objects.create(
            descricao='Conta futura',
            categoria=self.categoria,
            data_vencimento=timezone.localdate() + timedelta(days=20),
            valor=Decimal('80.00'),
        )

        response = self.client.get(reverse('dashboard_api_contas'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['valores'], [100.0, 80.0])

    def test_endpoint_caixa_respeita_periodos_validos_e_fallback(self):
        self.movimento(Decimal('50.00'))

        sete_dias = self.client.get(reverse('dashboard_api_caixa'), {'periodo': 7}).json()
        invalido = self.client.get(reverse('dashboard_api_caixa'), {'periodo': 99}).json()

        self.assertEqual(sete_dias['periodo'], 7)
        self.assertEqual(len(sete_dias['labels']), 7)
        self.assertEqual(sete_dias['valores'][-1], 150.0)
        self.assertEqual(invalido['periodo'], 30)

    def test_endpoint_projecao_retorna_cinco_horizontes(self):
        response = self.client.get(reverse('dashboard_api_projecao_financeira'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()['labels'],
            ['7 dias', '15 dias', '30 dias', '60 dias', '90 dias'],
        )

    def test_endpoints_exigem_perfil_gerencial(self):
        vendedor = get_user_model().objects.create_user(username='graficos-vendedor', password='senha')
        PerfilUsuario.objects.create(usuario=vendedor, perfil=PerfilUsuario.Perfil.VENDEDOR)
        self.client.logout()
        self.client.login(username='graficos-vendedor', password='senha')

        for nome in [
            'dashboard_api_fluxo_financeiro',
            'dashboard_api_formas_pagamento',
            'dashboard_api_contas',
            'dashboard_api_caixa',
            'dashboard_api_projecao_financeira',
        ]:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403)

    def test_resultado_do_endpoint_utiliza_cache(self):
        self.movimento(Decimal('25.00'))
        primeira = self.client.get(reverse('dashboard_api_fluxo_financeiro')).json()
        self.movimento(Decimal('75.00'))
        segunda = self.client.get(reverse('dashboard_api_fluxo_financeiro')).json()

        self.assertEqual(primeira, segunda)

    def test_template_carrega_chartjs_local_e_quatro_canvases(self):
        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'js/chart.umd.min.')
        for canvas_id in [
            'grafico-fluxo',
            'grafico-formas',
            'grafico-contas',
            'grafico-caixa',
            'grafico-projecao',
        ]:
            self.assertContains(response, f'id="{canvas_id}"')
