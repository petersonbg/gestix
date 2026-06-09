from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.http import JsonResponse
from django.views.decorators.http import require_POST


class GestixLoginView(LoginView):
    template_name = 'accounts/login.html'
    redirect_authenticated_user = True


class GestixLogoutView(LogoutView):
    pass


@login_required
@require_POST
def manter_sessao_ativa(request):
    """Confirma atividade do navegador; o middleware renova a expiração da sessão."""
    return JsonResponse({'ativa': True})
