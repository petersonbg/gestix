import calendar
from dataclasses import dataclass
from datetime import date

from django.db.models import Q, Sum
from django.utils import timezone

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


def queryset_contas_atrasadas(hoje=None):
    hoje = hoje or timezone.localdate()
    return ContaReceber.objects.select_related('cliente', 'venda').filter(
        Q(status=ContaReceber.Status.ATRASADA)
        | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
    )


def usuario_pode_visualizar_contas_receber(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administrador', 'Gerente', 'Vendedor']).exists()


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
    if not (user.is_superuser or user.groups.filter(name__in=['Administrador', 'Gerente']).exists()):
        queryset = queryset.filter(venda__usuario=user)

    return {
        'contas_atrasadas_qtd': queryset.count(),
        'contas_atrasadas_total': queryset.aggregate(total=Sum('valor'))['total'] or 0,
        'contas_atrasadas_lista': list(queryset.order_by('data_vencimento', 'numero_parcela')[:limite]),
        'pode_visualizar_contas_atrasadas': True,
    }
