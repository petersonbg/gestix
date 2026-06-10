from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

from clientes.models import Cliente
from fornecedores.models import Fornecedor
from produtos.models import Produto

from .utils import registrar_log


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
    registrar_log(user, 'login', 'accounts', 'Usuário autenticado no sistema.', request=request)


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
    registrar_log(user, 'logout', 'accounts', 'Usuário encerrou a sessão.', request=request)


def registrar_exclusao(sender, instance, **kwargs):
    registrar_log(
        None,
        'exclusão de registro',
        sender._meta.app_label,
        f'{sender._meta.verbose_name.title()} removido: {instance}.',
    )


for modelo in (Cliente, Fornecedor, Produto):
    post_delete.connect(registrar_exclusao, sender=modelo, dispatch_uid=f'accounts_log_delete_{modelo.__name__}')
