from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('acesso') == 'janela-invalida':
            messages.warning(request, 'Abra as telas internas pelo menu principal do GESTIX.')
        return super().get(request, *args, **kwargs)
