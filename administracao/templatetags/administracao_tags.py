from django import template

register = template.Library()


@register.filter
def pode_acessar_administracao(user):
    if not getattr(user, 'is_authenticated', False):
        return False
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Gerente']).exists()
