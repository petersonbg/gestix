from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from .models import SessaoUsuario
from .utils import obter_ip, obter_user_agent, registrar_log


MENSAGEM_SESSAO_SUBSTITUIDA = (
    'Sua sessão foi encerrada porque este usuário entrou em outro dispositivo.'
)


def garantir_session_key(request):
    if not request.session.session_key:
        request.session.save()
    return request.session.session_key


@transaction.atomic
def registrar_sessao_login(request, user):
    session_key = garantir_session_key(request)
    get_user_model().objects.select_for_update().get(pk=user.pk)

    anteriores = list(
        SessaoUsuario.objects.select_for_update()
        .filter(usuario=user, ativa=True)
        .exclude(session_key=session_key)
    )
    chaves_anteriores = [sessao.session_key for sessao in anteriores]
    if chaves_anteriores:
        Session.objects.filter(session_key__in=chaves_anteriores).delete()
        SessaoUsuario.objects.filter(pk__in=[sessao.pk for sessao in anteriores]).update(
            ativa=False,
            ultimo_acesso=timezone.now(),
        )
        registrar_log(
            user,
            'LOGOUT',
            'accounts',
            f'{len(anteriores)} sessão(ões) anterior(es) encerrada(s) por novo login.',
            request=request,
        )

    sessao, _ = SessaoUsuario.objects.update_or_create(
        session_key=session_key,
        defaults={
            'usuario': user,
            'ip_usuario': obter_ip(request),
            'user_agent': obter_user_agent(request),
            'ultimo_acesso': timezone.now(),
            'ativa': True,
        },
    )
    return sessao


def encerrar_sessao_atual(request, user=None):
    session_key = request.session.session_key
    if not session_key:
        return 0
    filtros = {'session_key': session_key, 'ativa': True}
    if user and getattr(user, 'is_authenticated', False):
        filtros['usuario'] = user
    return SessaoUsuario.objects.filter(**filtros).update(
        ativa=False,
        ultimo_acesso=timezone.now(),
    )


def atualizar_ultimo_acesso(sessao_id):
    SessaoUsuario.objects.filter(pk=sessao_id, ativa=True).update(ultimo_acesso=timezone.now())
