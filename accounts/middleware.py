from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from administracao.services import obter_tempo_logout_inatividade_minutos


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
    '/configuracoes/',
)

PRINT_EXCEPTIONS = (
    ('/vendas/', '/imprimir/'),
    ('/orcamentos/', '/imprimir/'),
    ('/ordens-servico/', '/imprimir/'),
)

ROLE_PERMISSIONS = {
    'Administrador': {'*'},
    'Gerente': {'dashboard', 'vendas', 'clientes', 'produtos', 'estoque', 'orcamentos', 'caixa', 'contas-receber', 'contas-pagar', 'ordens-servico', 'administracao', 'configuracoes'},
    'Vendedor': {'dashboard', 'clientes', 'vendas', 'orcamentos', 'caixa', 'contas-receber', 'ordens-servico'},
    'Estoquista': {'dashboard', 'produtos', 'fornecedores', 'estoque', 'ordens-servico'},
}


def is_internal_path(path):
    return any(path.startswith(prefix) for prefix in INTERNAL_PREFIXES)


def is_print_exception(path):
    return any(path.startswith(prefix) and path.endswith(suffix) for prefix, suffix in PRINT_EXCEPTIONS)


def module_from_path(path):
    if path.startswith('/dashboard/'):
        return 'dashboard'
    parts = [part for part in path.split('/') if part]
    return parts[0] if parts else ''


def user_allowed_modules(user):
    if user.is_superuser:
        return {'*'}
    modules = set()
    for group_name in user.groups.values_list('name', flat=True):
        modules.update(ROLE_PERMISSIONS.get(group_name, set()))
    return modules


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
            allowed = user_allowed_modules(request.user)
            if '*' not in allowed and modulo not in allowed:
                if path != reverse('dashboard'):
                    messages.error(request, 'Acesso inválido para o seu perfil de usuário.')
                    return redirect('dashboard')

        response = self.get_response(request)

        if request.user.is_authenticated and is_internal_path(path):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
