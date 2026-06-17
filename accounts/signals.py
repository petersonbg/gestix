from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_delete
from django.dispatch import receiver

from clientes.models import Cliente
from fornecedores.models import Fornecedor
from produtos.models import Produto

from .utils import registrar_log


@receiver(user_logged_in)
def registrar_login(sender, request, user, **kwargs):
<<<<<<< HEAD
    registrar_log(user, 'LOGIN', 'accounts', 'Usuário autenticado no sistema.', request=request)
=======
    registrar_log(user, 'login', 'accounts', 'Usuário autenticado no sistema.', request=request)
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


@receiver(user_logged_out)
def registrar_logout(sender, request, user, **kwargs):
<<<<<<< HEAD
    registrar_log(user, 'LOGOUT', 'accounts', 'Usuário encerrou a sessão.', request=request)
=======
    registrar_log(user, 'logout', 'accounts', 'Usuário encerrou a sessão.', request=request)
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


def registrar_exclusao(sender, instance, **kwargs):
    registrar_log(
        None,
<<<<<<< HEAD
        'EXCLUSAO',
        sender._meta.app_label,
        f'{sender._meta.verbose_name.title()} removido: {instance}.',
        objeto=instance,
=======
        'exclusão de registro',
        sender._meta.app_label,
        f'{sender._meta.verbose_name.title()} removido: {instance}.',
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
    )


for modelo in (Cliente, Fornecedor, Produto):
    post_delete.connect(registrar_exclusao, sender=modelo, dispatch_uid=f'accounts_log_delete_{modelo.__name__}')
