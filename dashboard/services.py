import calendar
from dataclasses import dataclass
from datetime import date

from django.db.models import Q, Sum
from django.utils import timezone

from administracao.services import obter_configuracao_sistema
from accounts.permissions import usuario_pode_acessar_modulo, usuario_tem_perfil
from clientes.models import Cliente
from contas_receber.models import ContaReceber


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

