from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect

from .models import PerfilUsuario
from .utils import registrar_log


MENSAGEM_SEM_PERFIL = 'Seu usuário ainda não possui perfil definido.'
MENSAGEM_ACESSO_NEGADO = 'Você não possui permissão para acessar este recurso.'


def normalizar_perfis(perfis):
    return {str(perfil).upper() for perfil in perfis}


GRUPO_PARA_PERFIL = {
    'Administrador': PerfilUsuario.Perfil.ADMINISTRADOR,
    'Gerente': PerfilUsuario.Perfil.GERENTE,
    'Vendedor': PerfilUsuario.Perfil.VENDEDOR,
    'Estoquista': PerfilUsuario.Perfil.ESTOQUISTA,
}

PERFIL_MODULOS = {
    PerfilUsuario.Perfil.ADMINISTRADOR: {'*'},
    PerfilUsuario.Perfil.GERENTE: {
        'dashboard', 'clientes', 'fornecedores', 'produtos', 'estoque',
        'vendas', 'orcamentos', 'caixa', 'contas-receber', 'contas-pagar',
        'ordens-servico', 'administracao', 'fiscal', 'relatorios',
    },
    PerfilUsuario.Perfil.VENDEDOR: {
        'dashboard', 'clientes', 'produtos', 'vendas', 'orcamentos', 'caixa',
        'contas-receber', 'ordens-servico', 'relatorios',
    },
    PerfilUsuario.Perfil.ESTOQUISTA: {
        'dashboard', 'produtos', 'fornecedores', 'estoque', 'ordens-servico',
        'relatorios',
    },
}


def obter_perfil_usuario(user):
    if not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'is_superuser', False):
        return type(
            'PerfilSuperuser',
            (),
            {'perfil': PerfilUsuario.Perfil.ADMINISTRADOR, 'ativo': True},
        )()
    try:
        perfil = user.perfil_usuario
    except PerfilUsuario.DoesNotExist:
        for grupo in user.groups.values_list('name', flat=True):
            perfil_legado = GRUPO_PARA_PERFIL.get(grupo)
            if perfil_legado:
                return type('PerfilLegado', (), {'perfil': perfil_legado, 'ativo': True})()
        return None
    return perfil if perfil.ativo else None


def perfil_atual(user):
    if getattr(user, 'is_superuser', False):
        return PerfilUsuario.Perfil.ADMINISTRADOR
    perfil = obter_perfil_usuario(user)
    return perfil.perfil if perfil else None


def modulos_permitidos(user):
    perfil = perfil_atual(user)
    if not perfil:
        return set()
    return PERFIL_MODULOS.get(perfil, set())


def usuario_pode_acessar_modulo(user, modulo):
    permitidos = modulos_permitidos(user)
    return '*' in permitidos or modulo in permitidos


def usuario_tem_perfil(user, perfis):
    if getattr(user, 'is_superuser', False):
        return True
    perfil = obter_perfil_usuario(user)
    return bool(perfil and perfil.perfil in normalizar_perfis(perfis))


def usuario_eh_admin(user):
    return usuario_tem_perfil(user, [PerfilUsuario.Perfil.ADMINISTRADOR])


def usuario_eh_gerente(user):
    return usuario_tem_perfil(user, [PerfilUsuario.Perfil.GERENTE])


def usuario_eh_vendedor(user):
    return usuario_tem_perfil(user, [PerfilUsuario.Perfil.VENDEDOR])


def usuario_eh_estoquista(user):
    return usuario_tem_perfil(user, [PerfilUsuario.Perfil.ESTOQUISTA])


def _registrar_bloqueio(request, descricao):
    registrar_log(
        request.user,
        'ERRO',
        'accounts',
        descricao,
        request=request,
    )


def _negar_acesso(request, mensagem):
    messages.error(request, mensagem)
    _registrar_bloqueio(request, mensagem)
    return redirect('acesso_negado')


def validar_perfil_request(request, perfis):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    perfil = obter_perfil_usuario(request.user)
    if not perfil:
        return _negar_acesso(request, MENSAGEM_SEM_PERFIL)
    if perfil.perfil not in normalizar_perfis(perfis):
        return _negar_acesso(request, MENSAGEM_ACESSO_NEGADO)
    return None


def perfil_required(perfis):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            resposta = validar_perfil_request(request, perfis)
            if resposta is not None:
                return resposta
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class PerfilRequiredMixin:
    perfis_permitidos = ()

    def dispatch(self, request, *args, **kwargs):
        resposta = validar_perfil_request(request, self.perfis_permitidos)
        if resposta is not None:
            return resposta
        return super().dispatch(request, *args, **kwargs)
