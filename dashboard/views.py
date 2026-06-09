from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView

from administracao.models import ConfiguracaoSistema
from .services import buscar_aniversariantes, buscar_contas_atrasadas_dashboard, buscar_contas_pagar_dashboard, buscar_ordens_servico_dashboard


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('acesso') == 'janela-invalida':
            messages.warning(request, 'Abra as telas internas pelo menu principal do GESTIX.')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuracao = ConfiguracaoSistema.get_solo()
        context['configuracao_sistema'] = configuracao
        context['aniversariantes'] = []
        if configuracao.notificacoes_aniversario_ativas:
            context['aniversariantes'] = buscar_aniversariantes(configuracao.dias_antecedencia_aniversario)
        context.update(buscar_contas_atrasadas_dashboard(self.request.user))
        context.update(buscar_contas_pagar_dashboard(self.request.user))
        context.update(buscar_ordens_servico_dashboard(self.request.user))
        return context
