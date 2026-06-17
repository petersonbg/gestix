from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from administracao.services import obter_tempo_logout_inatividade_minutos

<<<<<<< HEAD
from .permissions import (
    MENSAGEM_ACESSO_NEGADO,
    MENSAGEM_SEM_PERFIL,
    obter_perfil_usuario,
    usuario_pode_acessar_modulo,
)
from .utils import registrar_log

=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

ULTIMA_ATIVIDADE_SESSAO = 'gestix_ultima_atividade'


INTERNAL_PREFIXES = (
    '/dashboard/',
    '/administracao/',
    '/clientes/',
    '/fornecedores/',
    '/produtos/',
    '/estoque/',
    '/vendas/',
    '/caixa/',
    '/contas-receber/',
    '/contas-pagar/',
    '/ordens-servico/',
    '/orcamentos/',
    '/fiscal/',
<<<<<<< HEAD
    '/relatorios/',
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
    '/configuracoes/',
)

PRINT_EXCEPTIONS = (
    ('/vendas/', '/imprimir/'),
    ('/orcamentos/', '/imprimir/'),
    ('/ordens-servico/', '/imprimir/'),
)

<<<<<<< HEAD
=======
ROLE_PERMISSIONS = {
    'Administrador': {'*'},
    'Gerente': {'dashboard', 'vendas', 'clientes', 'produtos', 'estoque', 'orcamentos', 'caixa', 'contas-receber', 'contas-pagar', 'ordens-servico', 'administracao', 'configuracoes'},
    'Vendedor': {'dashboard', 'clientes', 'vendas', 'orcamentos', 'caixa', 'contas-receber', 'ordens-servico'},
    'Estoquista': {'dashboard', 'produtos', 'fornecedores', 'estoque', 'ordens-servico'},
}


>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
def is_internal_path(path):
    return any(path.startswith(prefix) for prefix in INTERNAL_PREFIXES)


def is_print_exception(path):
    return any(path.startswith(prefix) and path.endswith(suffix) for prefix, suffix in PRINT_EXCEPTIONS)


def module_from_path(path):
    if path.startswith('/dashboard/'):
        return 'dashboard'
<<<<<<< HEAD
    if path.startswith('/administracao/backup/'):
        return 'backup'
    if path.startswith('/administracao/logs/') or path.startswith('/administracao/logs-atividade/'):
        return 'logs'
    if path.startswith('/configuracoes/'):
        return 'administracao'
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
    parts = [part for part in path.split('/') if part]
    return parts[0] if parts else ''


<<<<<<< HEAD
def registrar_bloqueio(request, modulo, descricao):
    registrar_log(
        request.user,
        'ERRO',
        modulo or 'accounts',
        descricao,
        request=request,
    )
=======
def user_allowed_modules(user):
    if user.is_superuser:
        return {'*'}
    modules = set()
    for group_name in user.groups.values_list('name', flat=True):
        modules.update(ROLE_PERMISSIONS.get(group_name, set()))
    return modules
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


class InternalSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if request.user.is_authenticated:
            timeout_segundos = obter_tempo_logout_inatividade_minutos() * 60
            agora = timezone.now().timestamp()
            ultima_atividade = request.session.get(ULTIMA_ATIVIDADE_SESSAO)
            if ultima_atividade is not None and agora - ultima_atividade >= timeout_segundos:
                logout(request)
                messages.warning(request, 'Sua sessão expirou por inatividade. Faça login novamente.')
                return redirect(settings.LOGIN_URL)

            request.session[ULTIMA_ATIVIDADE_SESSAO] = agora
            request.session.set_expiry(timeout_segundos)

        if is_internal_path(path) and request.user.is_authenticated:
            modulo = module_from_path(path)
<<<<<<< HEAD
            perfil = obter_perfil_usuario(request.user)
            if not perfil:
                messages.error(request, MENSAGEM_SEM_PERFIL)
                registrar_bloqueio(request, modulo, MENSAGEM_SEM_PERFIL)
                return redirect('acesso_negado')
            if not usuario_pode_acessar_modulo(request.user, modulo) and path != reverse('dashboard'):
                messages.error(request, MENSAGEM_ACESSO_NEGADO)
                registrar_bloqueio(request, modulo, MENSAGEM_ACESSO_NEGADO)
                return redirect('acesso_negado')
=======
            allowed = user_allowed_modules(request.user)
            if '*' not in allowed and modulo not in allowed:
                if path != reverse('dashboard'):
                    messages.error(request, 'Acesso inválido para o seu perfil de usuário.')
                    return redirect('dashboard')
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

        response = self.get_response(request)

        if request.user.is_authenticated and is_internal_path(path):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
