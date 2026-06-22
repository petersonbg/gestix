from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

from clientes.models import Cliente
from fornecedores.models import Fornecedor
from produtos.models import Produto

from .utils import registrar_log
from .session_services import encerrar_sessao_atual, registrar_sessao_login


@receiver(user_logged_in, dispatch_uid='accounts_registrar_sessao_login')
def controlar_sessao_login(sender, request, user, **kwargs):
    if request is not None:
        registrar_sessao_login(request, user)


@receiver(user_logged_in, dispatch_uid='accounts_registrar_log_login')
def registrar_login(sender, request, user, **kwargs):
    registrar_log(user, 'LOGIN', 'accounts', 'Usuário autenticado no sistema.', request=request)


@receiver(user_logged_out, dispatch_uid='accounts_encerrar_sessao_logout')
def encerrar_registro_sessao(sender, request, user, **kwargs):
    if request is not None:
        encerrar_sessao_atual(request, user)


@receiver(user_logged_out, dispatch_uid='accounts_registrar_log_logout')
def registrar_logout(sender, request, user, **kwargs):
    registrar_log(user, 'LOGOUT', 'accounts', 'Usuário encerrou a sessão.', request=request)


def registrar_exclusao(sender, instance, **kwargs):
    registrar_log(
        None,
        'EXCLUSAO',
        sender._meta.app_label,
        f'{sender._meta.verbose_name.title()} removido: {instance}.',
        objeto=instance,
    )


for modelo in (Cliente, Fornecedor, Produto):
    post_delete.connect(registrar_exclusao, sender=modelo, dispatch_uid=f'accounts_log_delete_{modelo.__name__}')
