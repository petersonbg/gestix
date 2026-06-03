import calendar
from dataclasses import dataclass
from datetime import date

from django.utils import timezone

from clientes.models import Cliente


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
