import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.core.cache import cache
from django.db.models import (
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Min,
    OuterRef,
    Q,
    Subquery,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, TruncDate, TruncMonth
from django.utils import timezone

from administracao.services import obter_configuracao_sistema
from accounts.permissions import usuario_pode_acessar_modulo, usuario_tem_perfil
from caixa.models import Caixa, MovimentacaoCaixa
from clientes.models import Cliente
from contas_pagar.models import ContaPagar
from contas_receber.models import ContaReceber
from produtos.models import Produto
from vendas.models import ItemVenda, Venda

from .cache import chave_cache_dashboard


ZERO = Decimal('0.00')
GRAFICOS_CACHE_TIMEOUT = 300
MESES_ABREVIADOS = (
    'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
    'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez',
)


@dataclass(frozen=True)
class Aniversariante:
    cliente: Cliente
    data_aniversario_no_ano: date
    dias_restantes: int
    idade: int


def data_aniversario_para_ano(data_nascimento, ano):
    if data_nascimento.month == 2 and data_nascimento.day == 29 and not calendar.isleap(ano):
        return date(ano, 2, 28)
    return date(ano, data_nascimento.month, data_nascimento.day)


def proximo_aniversario(data_nascimento, hoje):
    aniversario = data_aniversario_para_ano(data_nascimento, hoje.year)
    if aniversario < hoje:
        aniversario = data_aniversario_para_ano(data_nascimento, hoje.year + 1)
    return aniversario


def buscar_aniversariantes(dias_antecedencia, hoje=None):
    hoje = hoje or timezone.localdate()
    aniversariantes = []
    clientes = Cliente.objects.filter(ativo=True, data_nascimento__isnull=False).order_by('nome')

    for cliente in clientes:
        aniversario = proximo_aniversario(cliente.data_nascimento, hoje)
        dias_restantes = (aniversario - hoje).days
        if 0 <= dias_restantes <= dias_antecedencia:
            aniversariantes.append(
                Aniversariante(
                    cliente=cliente,
                    data_aniversario_no_ano=aniversario,
                    dias_restantes=dias_restantes,
                    idade=aniversario.year - cliente.data_nascimento.year,
                )
            )

    return sorted(aniversariantes, key=lambda item: (item.dias_restantes, item.cliente.nome))


def buscar_aniversariantes_configurados(hoje=None):
    """Aplica a configuração global antes de consultar aniversariantes."""
    configuracao = obter_configuracao_sistema()
    if not configuracao.notificacoes_aniversario_ativas:
        return configuracao, []

    aniversariantes = buscar_aniversariantes(
        configuracao.dias_antecedencia_aniversario,
        hoje=hoje,
    )
    return configuracao, aniversariantes


def _inicio_mes_anterior(inicio_mes):
    return (inicio_mes - timedelta(days=1)).replace(day=1)


def _total(queryset, campo='valor'):
    return queryset.aggregate(total=Sum(campo))['total'] or ZERO


def _percentual_variacao(atual, anterior):
    if anterior == 0:
        return Decimal('100.00') if atual > 0 else ZERO
    return ((atual - anterior) / anterior * 100).quantize(Decimal('0.01'))


def _saldo_query(queryset):
    saldo = ExpressionWrapper(
        F('valor') - F('valor_pago'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    return queryset.aggregate(total=Sum(saldo))['total'] or ZERO


def _escopo_contas_receber(user):
    queryset = ContaReceber.objects.select_related('cliente', 'venda', 'ordem_servico')
    if usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE']):
        return queryset
    if usuario_tem_perfil(user, ['VENDEDOR']):
        return queryset.filter(Q(venda__usuario=user) | Q(ordem_servico__responsavel=user))
    return queryset.none()


def _saldo_caixa_atual():
    caixa_mais_recente = (
        Caixa.objects
        .filter(usuario_abertura_id=OuterRef('usuario_abertura_id'))
        .order_by('-data_abertura', '-pk')
        .values('pk')[:1]
    )
    caixas_atuais = Caixa.objects.filter(pk=Subquery(caixa_mais_recente))
    saldo_base = caixas_atuais.aggregate(
        total=Sum(
            Case(
                When(status=Caixa.Status.ABERTO, then=F('valor_inicial')),
                default=Coalesce(
                    F('valor_fechamento_informado'),
                    F('valor_fechamento_calculado'),
                    Value(ZERO),
                ),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
    )['total'] or ZERO
    movimentos_abertos = MovimentacaoCaixa.objects.filter(
        caixa__in=caixas_atuais.filter(status=Caixa.Status.ABERTO),
        forma_pagamento=MovimentacaoCaixa.FormaPagamento.DINHEIRO,
    )
    entradas = _total(movimentos_abertos.filter(
        tipo__in=[
            MovimentacaoCaixa.Tipo.ENTRADA,
            MovimentacaoCaixa.Tipo.SUPRIMENTO,
            MovimentacaoCaixa.Tipo.VENDA,
        ]
    ))
    saidas = _total(movimentos_abertos.filter(
        tipo__in=[
            MovimentacaoCaixa.Tipo.SAIDA,
            MovimentacaoCaixa.Tipo.SANGRIA,
            MovimentacaoCaixa.Tipo.CANCELAMENTO,
        ]
    ))
    return saldo_base + entradas - saidas

def buscar_dashboard_financeira(user, hoje=None, limite_alertas=5):
    hoje = hoje or timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    inicio_mes_anterior = _inicio_mes_anterior(inicio_mes)
    fim_mes_anterior = inicio_mes - timedelta(days=1)
    acesso_total = usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE'])
    acesso_receber = acesso_total or usuario_tem_perfil(user, ['VENDEDOR'])
    acesso_estoque = acesso_total or usuario_tem_perfil(user, ['ESTOQUISTA'])
    contexto = {
        'dashboard_acesso_total': acesso_total,
        'dashboard_acesso_receber': acesso_receber,
        'dashboard_acesso_estoque': acesso_estoque,
    }

    if acesso_total:
        receitas_base = MovimentacaoCaixa.objects.filter(
            tipo__in=[MovimentacaoCaixa.Tipo.VENDA, MovimentacaoCaixa.Tipo.ENTRADA],
        )
        receitas_mes = _total(receitas_base.filter(data__date__range=(inicio_mes, hoje)))
        receitas_mes_anterior = _total(
            receitas_base.filter(data__date__range=(inicio_mes_anterior, fim_mes_anterior))
        )
        despesas_mes = _total(
            ContaPagar.objects.filter(
                status=ContaPagar.Status.PAGA,
                data_pagamento__range=(inicio_mes, hoje),
            ),
            'valor_pago',
        )
        despesas_mes_anterior = _total(
            ContaPagar.objects.filter(
                status=ContaPagar.Status.PAGA,
                data_pagamento__range=(inicio_mes_anterior, fim_mes_anterior),
            ),
            'valor_pago',
        )
        saldo_caixa = _saldo_caixa_atual()

        formas_bancarias = [
            forma for forma, _ in MovimentacaoCaixa.FormaPagamento.choices
            if forma != MovimentacaoCaixa.FormaPagamento.DINHEIRO
        ]
        entradas_bancarias = _total(receitas_base.filter(forma_pagamento__in=formas_bancarias))
        saidas_bancarias = _total(
            ContaPagar.objects.filter(status=ContaPagar.Status.PAGA).exclude(
                forma_pagamento=ContaPagar.FormaPagamento.DINHEIRO,
            ),
            'valor_pago',
        )
        saldo_bancario = entradas_bancarias - saidas_bancarias
        contexto.update({
            'receitas_mes': receitas_mes,
            'receitas_mes_anterior': receitas_mes_anterior,
            'receitas_variacao': _percentual_variacao(receitas_mes, receitas_mes_anterior),
            'despesas_mes': despesas_mes,
            'despesas_mes_anterior': despesas_mes_anterior,
            'despesas_variacao': _percentual_variacao(despesas_mes, despesas_mes_anterior),
            'lucro_estimado': receitas_mes - despesas_mes,
            'saldo_caixa': saldo_caixa,
            'saldo_bancario': saldo_bancario,
            'saldo_disponivel': saldo_caixa + saldo_bancario,
        })

    contas_receber = _escopo_contas_receber(user)
    receber_hoje = contas_receber.filter(status=ContaReceber.Status.ABERTA, data_vencimento=hoje)
    receber_atrasadas = contas_receber.filter(
        Q(status=ContaReceber.Status.ATRASADA)
        | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
    )
    if acesso_total:
        pagar_base = ContaPagar.objects.select_related('fornecedor', 'categoria')
        pagar_hoje = pagar_base.filter(status=ContaPagar.Status.ABERTA, data_vencimento=hoje)
        pagar_atrasadas = pagar_base.filter(
            Q(status=ContaPagar.Status.ATRASADA)
            | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
        )
    else:
        pagar_hoje = ContaPagar.objects.none()
        pagar_atrasadas = ContaPagar.objects.none()
    produtos_baixos = (
        Produto.objects.select_related('categoria', 'fornecedor')
        .filter(ativo=True, estoque_atual__lte=F('estoque_minimo'))
        .order_by('estoque_atual', 'nome')
        if acesso_estoque else Produto.objects.none()
    )

    contexto.update({
        'receber_hoje_qtd': receber_hoje.count() if acesso_receber else 0,
        'receber_hoje_total': _saldo_query(receber_hoje) if acesso_receber else ZERO,
        'receber_atrasadas_qtd': receber_atrasadas.count() if acesso_receber else 0,
        'receber_atrasadas_total': _saldo_query(receber_atrasadas) if acesso_receber else ZERO,
        'pagar_hoje_qtd': pagar_hoje.count() if acesso_total else 0,
        'pagar_hoje_total': _saldo_query(pagar_hoje) if acesso_total else ZERO,
        'pagar_atrasadas_qtd': pagar_atrasadas.count() if acesso_total else 0,
        'pagar_atrasadas_total': _saldo_query(pagar_atrasadas) if acesso_total else ZERO,
        'clientes_inadimplentes_qtd': (
            receber_atrasadas.aggregate(total=Count('cliente', distinct=True))['total'] or 0
        ) if acesso_receber else 0,
        'estoque_baixo_qtd': produtos_baixos.count() if acesso_estoque else 0,
        'alertas_contas_vencidas': list(
            receber_atrasadas.order_by('data_vencimento', 'numero_parcela')[:limite_alertas]
        ) if acesso_receber else [],
        'alertas_contas_hoje': list(
            receber_hoje.order_by('cliente__nome', 'numero_parcela')[:limite_alertas]
        ) if acesso_receber else [],
        'alertas_pagar_vencidas': list(
            pagar_atrasadas.order_by('data_vencimento', 'descricao')[:limite_alertas]
        ) if acesso_total else [],
        'alertas_pagar_hoje': list(
            pagar_hoje.order_by('descricao')[:limite_alertas]
        ) if acesso_total else [],
        'alertas_estoque_baixo': list(produtos_baixos[:limite_alertas]) if acesso_estoque else [],
    })
    contexto['alertas_contas_vencidas_qtd'] = (
        contexto['receber_atrasadas_qtd'] + contexto['pagar_atrasadas_qtd']
    )
    contexto['alertas_vencendo_hoje_qtd'] = (
        contexto['receber_hoje_qtd'] + contexto['pagar_hoje_qtd']
    )
    contexto.update({
        'pode_visualizar_contas_atrasadas': acesso_receber,
        'contas_atrasadas_qtd': contexto['receber_atrasadas_qtd'],
        'contas_atrasadas_total': contexto['receber_atrasadas_total'],
        'contas_atrasadas_lista': contexto['alertas_contas_vencidas'],
        'pode_visualizar_contas_pagar': acesso_total,
        'contas_pagar_atrasadas_qtd': contexto['pagar_atrasadas_qtd'],
        'contas_pagar_atrasadas_total': contexto['pagar_atrasadas_total'],
        'contas_pagar_atrasadas_lista': contexto['alertas_pagar_vencidas'],
        'contas_pagar_hoje_qtd': contexto['pagar_hoje_qtd'],
        'contas_pagar_hoje_total': contexto['pagar_hoje_total'],
        'contas_pagar_hoje_lista': contexto['alertas_pagar_hoje'],
    })
    contexto['tem_alertas_financeiros'] = any([
        contexto['alertas_contas_vencidas_qtd'],
        contexto['alertas_vencendo_hoje_qtd'],
        contexto['estoque_baixo_qtd'],
    ])
    return contexto


def _percentual_razao(numerador, denominador):
    if not denominador:
        return ZERO
    return (numerador / denominador * 100).quantize(Decimal('0.01'))


def buscar_dashboard_executiva(user, hoje=None, saldo_disponivel=None):
    hoje = hoje or timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    acesso_total = usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE'])
    acesso_vendedor = usuario_tem_perfil(user, ['VENDEDOR'])
    if not (acesso_total or acesso_vendedor):
        return {'dashboard_executiva_visivel': False}

    if acesso_total and saldo_disponivel is None:
        saldo_disponivel = buscar_dashboard_financeira(user, hoje=hoje)['saldo_disponivel']
    saldo_chave = saldo_disponivel if acesso_total else 'vendedor'
    chave = chave_cache_dashboard(
        f'dashboard:executiva:{user.pk}:{int(acesso_total)}:{hoje:%Y-%m-%d}:{saldo_chave}'
    )
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    vendas = Venda.objects.filter(
        status=Venda.Status.FINALIZADA,
        data__date__range=(inicio_mes, hoje),
    )
    if acesso_vendedor and not acesso_total:
        vendas = vendas.filter(usuario=user)

    resumo_vendas = vendas.aggregate(total=Sum('total'), quantidade=Count('pk'))
    total_vendas = resumo_vendas['total'] or ZERO
    quantidade_vendas = resumo_vendas['quantidade'] or 0
    ticket_medio = total_vendas / quantidade_vendas if quantidade_vendas else ZERO

    custo_expr = ExpressionWrapper(
        F('quantidade') * F('produto__preco_custo'),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    itens = ItemVenda.objects.filter(venda__in=vendas)
    custo_total = itens.aggregate(total=Sum(custo_expr))['total'] or ZERO
    lucro_vendas = total_vendas - custo_total
    margem_media = _percentual_razao(lucro_vendas, total_vendas)

    contas_receber = _escopo_contas_receber(user).exclude(status=ContaReceber.Status.CANCELADA)
    saldo_receber = _saldo_query(contas_receber.exclude(status=ContaReceber.Status.PAGA))
    contas_atrasadas = contas_receber.filter(
        Q(status=ContaReceber.Status.ATRASADA)
        | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
    )
    saldo_atrasado = _saldo_query(contas_atrasadas)
    inadimplencia = _percentual_razao(saldo_atrasado, saldo_receber)

    top_clientes = list(
        vendas.values('cliente_id', 'cliente__nome')
        .annotate(valor_comprado=Sum('total'), quantidade_compras=Count('pk'))
        .order_by('-valor_comprado', 'cliente__nome')[:10]
    )
    faturamento_liquido = Case(
        When(
            venda__subtotal__gt=0,
            then=ExpressionWrapper(
                F('total_item') * F('venda__total') / F('venda__subtotal'),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
        ),
        default=Value(ZERO),
        output_field=DecimalField(max_digits=14, decimal_places=2),
    )
    top_produtos = list(
        itens.values('produto_id', 'produto__nome')
        .annotate(
            quantidade_vendida=Sum('quantidade'),
            faturamento=Sum(faturamento_liquido),
        )
        .order_by('-faturamento', 'produto__nome')[:10]
    )

    contexto = {
        'dashboard_executiva_visivel': True,
        'vendas_mes_total': total_vendas,
        'vendas_mes_quantidade': quantidade_vendas,
        'ticket_medio': ticket_medio,
        'lucro_vendas_estimado': lucro_vendas,
        'margem_media': margem_media,
        'inadimplencia_percentual': inadimplencia,
        'inadimplencia_valor': saldo_atrasado,
        'top_clientes': top_clientes,
        'top_produtos': top_produtos,
    }

    if acesso_total:
        top_vendedores_bruto = list(
            vendas.exclude(usuario__isnull=True)
            .values('usuario_id', 'usuario__username', 'usuario__first_name', 'usuario__last_name')
            .annotate(total_vendido=Sum('total'), quantidade_vendas=Count('pk'))
            .order_by('-total_vendido', 'usuario__username')[:10]
        )
        for item in top_vendedores_bruto:
            nome = f"{item['usuario__first_name']} {item['usuario__last_name']}".strip()
            item['vendedor_nome'] = nome or item['usuario__username']

        fim_30 = hoje + timedelta(days=29)
        despesas_30_dias = _saldo_query(ContaPagar.objects.filter(
            status__in=[ContaPagar.Status.ABERTA, ContaPagar.Status.ATRASADA],
            data_vencimento__range=(hoje, fim_30),
        ))
        capital_giro = saldo_disponivel - despesas_30_dias
        cobertura = saldo_disponivel / despesas_30_dias if despesas_30_dias else None
        if saldo_disponivel < 0:
            situacao = 'CRITICO'
            situacao_label = 'Crítico'
            situacao_cor = 'danger'
        elif cobertura is None or cobertura >= 1:
            situacao = 'SAUDAVEL'
            situacao_label = 'Saudável'
            situacao_cor = 'success'
        elif cobertura >= Decimal('0.50'):
            situacao = 'ATENCAO'
            situacao_label = 'Atenção'
            situacao_cor = 'warning'
        else:
            situacao = 'CRITICO'
            situacao_label = 'Crítico'
            situacao_cor = 'danger'
        ranking_inadimplencia = list(
            contas_atrasadas.values('cliente_id', 'cliente__nome')
            .annotate(
                valor_vencido=Sum(
                    ExpressionWrapper(
                        F('valor') - F('valor_pago'),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ),
                vencimento_mais_antigo=Min('data_vencimento'),
            )
            .order_by('-valor_vencido', 'cliente__nome')[:10]
        )
        for item in ranking_inadimplencia:
            item['dias_atraso'] = (hoje - item['vencimento_mais_antigo']).days
        contexto.update({
            'top_vendedores': top_vendedores_bruto,
            'despesas_30_dias': despesas_30_dias,
            'capital_giro': capital_giro,
            'capital_giro_situacao': situacao,
            'capital_giro_label': situacao_label,
            'capital_giro_cor': situacao_cor,
            'ranking_inadimplencia': ranking_inadimplencia,
        })

    cache.set(chave, contexto, GRAFICOS_CACHE_TIMEOUT)
    return contexto


def grafico_projecao_financeira(hoje=None):
    hoje = hoje or timezone.localdate()
    periodos = [7, 15, 30, 60, 90]
    chave = chave_cache_dashboard(f'dashboard:grafico:projecao:{hoje:%Y-%m-%d}')
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    receber_base = ContaReceber.objects.filter(
        status__in=[ContaReceber.Status.ABERTA, ContaReceber.Status.ATRASADA],
    )
    pagar_base = ContaPagar.objects.filter(
        status__in=[ContaPagar.Status.ABERTA, ContaPagar.Status.ATRASADA],
    )
    saldo_expr = ExpressionWrapper(
        F('valor') - F('valor_pago'),
        output_field=DecimalField(max_digits=12, decimal_places=2),
    )
    filtros = {
        f'periodo_{dias}': Sum(
            saldo_expr,
            filter=Q(data_vencimento__lte=hoje + timedelta(days=dias - 1)),
        )
        for dias in periodos
    }
    totais_receber = receber_base.aggregate(**filtros)
    totais_pagar = pagar_base.aggregate(**filtros)
    receber_decimais = [totais_receber[f'periodo_{dias}'] or ZERO for dias in periodos]
    pagar_decimais = [totais_pagar[f'periodo_{dias}'] or ZERO for dias in periodos]
    dados = {
        'labels': [f'{dias} dias' for dias in periodos],
        'receber': [_decimal_float(valor) for valor in receber_decimais],
        'pagar': [_decimal_float(valor) for valor in pagar_decimais],
        'saldo': [
            _decimal_float(valor_receber - valor_pagar)
            for valor_receber, valor_pagar in zip(receber_decimais, pagar_decimais)
        ],
    }
    cache.set(chave, dados, GRAFICOS_CACHE_TIMEOUT)
    return dados


def _meses_ate(hoje, quantidade):
    meses = []
    for deslocamento in range(quantidade - 1, -1, -1):
        indice = hoje.year * 12 + hoje.month - 1 - deslocamento
        meses.append(date(indice // 12, indice % 12 + 1, 1))
    return meses


def _decimal_float(valor):
    return float(valor or ZERO)


def _data_mes(valor):
    return valor.date() if hasattr(valor, 'date') else valor


def grafico_fluxo_financeiro(hoje=None):
    hoje = hoje or timezone.localdate()
    chave = chave_cache_dashboard(f'dashboard:grafico:fluxo:{hoje:%Y-%m}')
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    meses = _meses_ate(hoje, 12)
    inicio = meses[0]
    receitas_qs = (
        MovimentacaoCaixa.objects
        .filter(
            tipo__in=[MovimentacaoCaixa.Tipo.VENDA, MovimentacaoCaixa.Tipo.ENTRADA],
            data__date__range=(inicio, hoje),
        )
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(total=Sum('valor'))
    )
    despesas_qs = (
        ContaPagar.objects
        .filter(
            status=ContaPagar.Status.PAGA,
            data_pagamento__range=(inicio, hoje),
        )
        .annotate(mes=TruncMonth('data_pagamento'))
        .values('mes')
        .annotate(total=Sum('valor_pago'))
    )
    receitas_por_mes = {_data_mes(item['mes']): item['total'] for item in receitas_qs}
    despesas_por_mes = {_data_mes(item['mes']): item['total'] for item in despesas_qs}
    receitas = [receitas_por_mes.get(mes, ZERO) for mes in meses]
    despesas = [despesas_por_mes.get(mes, ZERO) for mes in meses]
    dados = {
        'labels': [f'{MESES_ABREVIADOS[mes.month - 1]}/{str(mes.year)[2:]}' for mes in meses],
        'receitas': [_decimal_float(valor) for valor in receitas],
        'despesas': [_decimal_float(valor) for valor in despesas],
        'lucro': [_decimal_float(receita - despesa) for receita, despesa in zip(receitas, despesas)],
    }
    cache.set(chave, dados, GRAFICOS_CACHE_TIMEOUT)
    return dados


def grafico_formas_pagamento(hoje=None):
    hoje = hoje or timezone.localdate()
    inicio = _meses_ate(hoje, 12)[0]
    chave = chave_cache_dashboard(f'dashboard:grafico:formas:{hoje:%Y-%m}')
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    receitas = MovimentacaoCaixa.objects.filter(
        tipo__in=[MovimentacaoCaixa.Tipo.VENDA, MovimentacaoCaixa.Tipo.ENTRADA],
        data__date__range=(inicio, hoje),
    )
    filtro_crediario = (
        Q(venda__forma_pagamento=Venda.FormaPagamento.CREDIARIO)
        | Q(descricao__istartswith='Recebimento de parcela')
    )
    total_crediario = _total(receitas.filter(filtro_crediario))
    por_forma = {
        item['forma_pagamento']: item['total']
        for item in (
            receitas.exclude(filtro_crediario)
            .filter(forma_pagamento__in=[
                MovimentacaoCaixa.FormaPagamento.PIX,
                MovimentacaoCaixa.FormaPagamento.DINHEIRO,
                MovimentacaoCaixa.FormaPagamento.CARTAO_DEBITO,
                MovimentacaoCaixa.FormaPagamento.CARTAO_CREDITO,
            ])
            .values('forma_pagamento')
            .annotate(total=Sum('valor'))
        )
    }
    dados = {
        'labels': ['PIX', 'Dinheiro', 'Cartão Débito', 'Cartão Crédito', 'Crediário'],
        'valores': [
            _decimal_float(por_forma.get(MovimentacaoCaixa.FormaPagamento.PIX, ZERO)),
            _decimal_float(por_forma.get(MovimentacaoCaixa.FormaPagamento.DINHEIRO, ZERO)),
            _decimal_float(por_forma.get(MovimentacaoCaixa.FormaPagamento.CARTAO_DEBITO, ZERO)),
            _decimal_float(por_forma.get(MovimentacaoCaixa.FormaPagamento.CARTAO_CREDITO, ZERO)),
            _decimal_float(total_crediario),
        ],
        'periodo': 'Últimos 12 meses',
    }
    cache.set(chave, dados, GRAFICOS_CACHE_TIMEOUT)
    return dados


def grafico_contas_30_dias(hoje=None):
    hoje = hoje or timezone.localdate()
    fim = hoje + timedelta(days=29)
    chave = chave_cache_dashboard(f'dashboard:grafico:contas:{hoje:%Y-%m-%d}')
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    receber = _saldo_query(ContaReceber.objects.filter(
        status__in=[ContaReceber.Status.ABERTA, ContaReceber.Status.ATRASADA],
        data_vencimento__range=(hoje, fim),
    ))
    pagar = _saldo_query(ContaPagar.objects.filter(
        status__in=[ContaPagar.Status.ABERTA, ContaPagar.Status.ATRASADA],
        data_vencimento__range=(hoje, fim),
    ))
    dados = {
        'labels': ['Receber', 'Pagar'],
        'valores': [_decimal_float(receber), _decimal_float(pagar)],
        'inicio': hoje.isoformat(),
        'fim': fim.isoformat(),
    }
    cache.set(chave, dados, GRAFICOS_CACHE_TIMEOUT)
    return dados


def grafico_evolucao_caixa(periodo=30, hoje=None):
    hoje = hoje or timezone.localdate()
    periodo = periodo if periodo in {1, 7, 15, 30} else 30
    inicio = hoje - timedelta(days=periodo - 1)
    chave = chave_cache_dashboard(f'dashboard:grafico:caixa:{periodo}:{hoje:%Y-%m-%d}')
    armazenado = cache.get(chave)
    if armazenado is not None:
        return armazenado

    movimentos = MovimentacaoCaixa.objects.filter(
        forma_pagamento=MovimentacaoCaixa.FormaPagamento.DINHEIRO,
    ).annotate(
        valor_assinado=Case(
            When(
                tipo__in=[
                    MovimentacaoCaixa.Tipo.ENTRADA,
                    MovimentacaoCaixa.Tipo.SUPRIMENTO,
                    MovimentacaoCaixa.Tipo.VENDA,
                ],
                then=F('valor'),
            ),
            default=-F('valor'),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
    )
    saldo = _total(Caixa.objects.filter(data_abertura__date__lt=inicio), 'valor_inicial')
    saldo += movimentos.filter(data__date__lt=inicio).aggregate(
        total=Sum('valor_assinado')
    )['total'] or ZERO
    caixas_diarios = {
        item['dia']: item['total'] or ZERO
        for item in (
            Caixa.objects.filter(data_abertura__date__range=(inicio, hoje))
            .annotate(dia=TruncDate('data_abertura'))
            .values('dia')
            .annotate(total=Sum('valor_inicial'))
        )
    }
    movimentos_diarios = {
        item['dia']: item['total'] or ZERO
        for item in (
            movimentos.filter(data__date__range=(inicio, hoje))
            .annotate(dia=TruncDate('data'))
            .values('dia')
            .annotate(total=Sum('valor_assinado'))
        )
    }
    labels = []
    valores = []
    for deslocamento in range(periodo):
        dia = inicio + timedelta(days=deslocamento)
        saldo += caixas_diarios.get(dia, ZERO) + movimentos_diarios.get(dia, ZERO)
        labels.append(dia.strftime('%d/%m'))
        valores.append(_decimal_float(saldo))
    dados = {'labels': labels, 'valores': valores, 'periodo': periodo}
    cache.set(chave, dados, GRAFICOS_CACHE_TIMEOUT)
    return dados


def queryset_contas_atrasadas(hoje=None):
    hoje = hoje or timezone.localdate()
    return ContaReceber.objects.select_related('cliente', 'venda', 'ordem_servico').filter(
        Q(status=ContaReceber.Status.ATRASADA)
        | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
    )


def usuario_pode_visualizar_contas_receber(user):
    return usuario_pode_acessar_modulo(user, 'contas-receber')


def buscar_contas_atrasadas_dashboard(user, hoje=None, limite=5):
    if not usuario_pode_visualizar_contas_receber(user):
        return {
            'contas_atrasadas_qtd': 0,
            'contas_atrasadas_total': 0,
            'contas_atrasadas_lista': [],
            'pode_visualizar_contas_atrasadas': False,
        }

    hoje = hoje or timezone.localdate()
    queryset = queryset_contas_atrasadas(hoje=hoje)
    if not usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE']):
        queryset = queryset.filter(Q(venda__usuario=user) | Q(ordem_servico__responsavel=user))

    return {
        'contas_atrasadas_qtd': queryset.count(),
        'contas_atrasadas_total': queryset.aggregate(total=Sum('valor'))['total'] or 0,
        'contas_atrasadas_lista': list(queryset.order_by('data_vencimento', 'numero_parcela')[:limite]),
        'pode_visualizar_contas_atrasadas': True,
    }


def queryset_contas_pagar_atrasadas(hoje=None):
    from contas_pagar.models import ContaPagar

    hoje = hoje or timezone.localdate()
    return ContaPagar.objects.select_related('fornecedor', 'categoria').filter(
        Q(status=ContaPagar.Status.ATRASADA)
        | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
    )


def usuario_pode_visualizar_contas_pagar(user):
    return usuario_pode_acessar_modulo(user, 'contas-pagar')


def buscar_contas_pagar_dashboard(user, hoje=None, limite=5):
    from datetime import timedelta
    from contas_pagar.models import ContaPagar

    if not usuario_pode_visualizar_contas_pagar(user):
        return {
            'pode_visualizar_contas_pagar': False,
            'contas_pagar_atrasadas_qtd': 0,
            'contas_pagar_atrasadas_total': 0,
            'contas_pagar_atrasadas_lista': [],
            'contas_pagar_hoje_qtd': 0,
            'contas_pagar_hoje_total': 0,
            'contas_pagar_hoje_lista': [],
            'contas_pagar_7_dias_qtd': 0,
            'contas_pagar_7_dias_total': 0,
            'contas_pagar_7_dias_lista': [],
        }

    hoje = hoje or timezone.localdate()
    em_7_dias = hoje + timedelta(days=7)
    atrasadas = queryset_contas_pagar_atrasadas(hoje=hoje)
    hoje_qs = ContaPagar.objects.select_related('fornecedor', 'categoria').filter(status=ContaPagar.Status.ABERTA, data_vencimento=hoje)
    proximas = ContaPagar.objects.select_related('fornecedor', 'categoria').filter(status=ContaPagar.Status.ABERTA, data_vencimento__gt=hoje, data_vencimento__lte=em_7_dias)

    return {
        'pode_visualizar_contas_pagar': True,
        'contas_pagar_atrasadas_qtd': atrasadas.count(),
        'contas_pagar_atrasadas_total': atrasadas.aggregate(total=Sum('valor'))['total'] or 0,
        'contas_pagar_atrasadas_lista': list(atrasadas.order_by('data_vencimento', 'descricao')[:limite]),
        'contas_pagar_hoje_qtd': hoje_qs.count(),
        'contas_pagar_hoje_total': hoje_qs.aggregate(total=Sum('valor'))['total'] or 0,
        'contas_pagar_hoje_lista': list(hoje_qs.order_by('data_vencimento', 'descricao')[:limite]),
        'contas_pagar_7_dias_qtd': proximas.count(),
        'contas_pagar_7_dias_total': proximas.aggregate(total=Sum('valor'))['total'] or 0,
        'contas_pagar_7_dias_lista': list(proximas.order_by('data_vencimento', 'descricao')[:limite]),
    }


def buscar_ordens_servico_dashboard(user, hoje=None, limite=5):
    from ordens_servico.models import OrdemServico

    if not usuario_pode_acessar_modulo(user, 'ordens-servico'):
        return {'pode_visualizar_ordens_servico': False}
    hoje = hoje or timezone.localdate()
    base = OrdemServico.objects.select_related('cliente', 'responsavel')
    abertas = base.filter(status=OrdemServico.Status.ABERTA)
    andamento = base.filter(status=OrdemServico.Status.EM_ANDAMENTO)
    aguardando = base.filter(status=OrdemServico.Status.AGUARDANDO_PECA)
    concluidas = base.filter(status=OrdemServico.Status.CONCLUIDA)
    atrasadas = base.filter(
        status__in=[OrdemServico.Status.ABERTA, OrdemServico.Status.EM_ANDAMENTO, OrdemServico.Status.AGUARDANDO_PECA],
        data_previsao__lt=hoje,
    ).order_by('data_previsao')
    return {
        'pode_visualizar_ordens_servico': True,
        'os_abertas_qtd': abertas.count(),
        'os_andamento_qtd': andamento.count(),
        'os_aguardando_peca_qtd': aguardando.count(),
        'os_concluidas_entrega_qtd': concluidas.count(),
        'os_atrasadas_qtd': atrasadas.count(),
        'os_atrasadas_lista': list(atrasadas[:limite]),
    }
