from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from administracao.services import obter_tempo_logout_inatividade_minutos

from .permissions import (
    MENSAGEM_ACESSO_NEGADO,
    MENSAGEM_SEM_PERFIL,
    obter_perfil_usuario,
    usuario_pode_acessar_modulo,
)
from .models import SessaoUsuario
from .session_services import MENSAGEM_SESSAO_SUBSTITUIDA, atualizar_ultimo_acesso
from .utils import registrar_log


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
    '/relatorios/',
    '/configuracoes/',
)

PRINT_EXCEPTIONS = (
    ('/vendas/', '/imprimir/'),
    ('/orcamentos/', '/imprimir/'),
    ('/ordens-servico/', '/imprimir/'),
)

def is_internal_path(path):
    return any(path.startswith(prefix) for prefix in INTERNAL_PREFIXES)


def is_print_exception(path):
    return any(path.startswith(prefix) and path.endswith(suffix) for prefix, suffix in PRINT_EXCEPTIONS)


def module_from_path(path):
    if path.startswith('/dashboard/'):
        return 'dashboard'
    if path.startswith('/administracao/backup/'):
        return 'backup'
    if path.startswith('/administracao/logs/') or path.startswith('/administracao/logs-atividade/'):
        return 'logs'
    if path.startswith('/configuracoes/'):
        return 'administracao'
    parts = [part for part in path.split('/') if part]
    return parts[0] if parts else ''


def registrar_bloqueio(request, modulo, descricao):
    registrar_log(
        request.user,
        'ERRO',
        modulo or 'accounts',
        descricao,
        request=request,
    )


class SingleSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        session_key = request.session.session_key

        if request.user.is_authenticated:
            sessao = (
                SessaoUsuario.objects.filter(
                    usuario=request.user,
                    session_key=session_key,
                    ativa=True,
                )
                .only('pk')
                .first()
            )
            if not sessao:
                registrar_log(
                    request.user,
                    'LOGOUT',
                    'accounts',
                    'Logout porque o usuário entrou em outro dispositivo.',
                    request=request,
                )
                logout(request)
                messages.warning(request, MENSAGEM_SESSAO_SUBSTITUIDA)
                return redirect(settings.LOGIN_URL)
            atualizar_ultimo_acesso(sessao.pk)
        elif request.path != reverse('login'):
            cookie_key = request.COOKIES.get(settings.SESSION_COOKIE_NAME)
            sessao_antiga = (
                SessaoUsuario.objects.select_related('usuario')
                .filter(session_key=cookie_key, ativa=False)
                .first()
                if cookie_key
                else None
            )
            if sessao_antiga:
                registrar_log(
                    sessao_antiga.usuario,
                    'LOGOUT',
                    'accounts',
                    'Logout porque o usuário entrou em outro dispositivo.',
                    request=request,
                )
                request.session.flush()
                messages.warning(request, MENSAGEM_SESSAO_SUBSTITUIDA)
                return redirect(settings.LOGIN_URL)

        return self.get_response(request)


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
            perfil = obter_perfil_usuario(request.user)
            if not perfil:
                messages.error(request, MENSAGEM_SEM_PERFIL)
                registrar_bloqueio(request, modulo, MENSAGEM_SEM_PERFIL)
                return redirect('acesso_negado')
            if not usuario_pode_acessar_modulo(request.user, modulo) and path != reverse('dashboard'):
                messages.error(request, MENSAGEM_ACESSO_NEGADO)
                registrar_bloqueio(request, modulo, MENSAGEM_ACESSO_NEGADO)
                return redirect('acesso_negado')

        response = self.get_response(request)

        if request.user.is_authenticated and is_internal_path(path):
            response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response
