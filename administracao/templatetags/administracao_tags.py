from django import template

from accounts.permissions import (
    perfil_atual,
    usuario_eh_admin,
    usuario_pode_acessar_modulo,
)
from accounts.models import PerfilUsuario
from relatorios.permissions import RELATORIOS_PERMISSOES

register = template.Library()


@register.filter
def pode_acessar_modulo(user, modulo):
    return usuario_pode_acessar_modulo(user, modulo)


@register.filter
def pode_acessar_administracao(user):
    return usuario_pode_acessar_modulo(user, 'administracao')


@register.filter
def pode_administrar(user):
    return usuario_eh_admin(user)


@register.filter
def perfil_nome(user):
    perfil = perfil_atual(user)
    return dict(PerfilUsuario.Perfil.choices).get(perfil, 'Sem perfil')


@register.filter
def pode_acessar_relatorio(user, relatorio):
    return perfil_atual(user) in RELATORIOS_PERMISSOES.get(relatorio, set())
