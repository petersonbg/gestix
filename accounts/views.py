from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.views.decorators.http import require_POST
<<<<<<< HEAD
from django.views.generic import TemplateView
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


class GestixLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class GestixLogoutView(LogoutView):
    pass


<<<<<<< HEAD
class AcessoNegadoView(TemplateView):
    template_name = 'accounts/acesso_negado.html'


=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
@login_required
@require_POST
def manter_sessao_ativa(request):
    """Confirma atividade do navegador; o middleware renova a expiração da sessão."""
    return JsonResponse({'ativa': True})
