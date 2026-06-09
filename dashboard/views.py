from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from .services import (
    buscar_aniversariantes_configurados,
    buscar_contas_atrasadas_dashboard,
    buscar_contas_pagar_dashboard,
    buscar_ordens_servico_dashboard,
)


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('acesso') == 'janela-invalida':
            messages.warning(request, 'Abra as telas internas pelo menu principal do GESTIX.')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuracao, aniversariantes = buscar_aniversariantes_configurados()
        context['configuracao_sistema'] = configuracao
        context['aniversariantes'] = aniversariantes
        context.update(buscar_contas_atrasadas_dashboard(self.request.user))
        context.update(buscar_contas_pagar_dashboard(self.request.user))
        context.update(buscar_ordens_servico_dashboard(self.request.user))
        return context
