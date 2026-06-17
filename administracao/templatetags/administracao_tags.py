from django import template

<<<<<<< HEAD
from accounts.permissions import (
    perfil_atual,
    usuario_eh_admin,
    usuario_pode_acessar_modulo,
)
from accounts.models import PerfilUsuario
from relatorios.permissions import RELATORIOS_PERMISSOES

=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
register = template.Library()


@register.filter
<<<<<<< HEAD
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
=======
def pode_acessar_administracao(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Gerente']).exists()
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
