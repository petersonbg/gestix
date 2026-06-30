from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.views.generic import TemplateView

from accounts.permissions import usuario_tem_perfil

from .services import (
    buscar_aniversariantes_configurados,
    buscar_dashboard_executiva,
    buscar_dashboard_financeira,
    grafico_contas_30_dias,
    grafico_evolucao_caixa,
    grafico_fluxo_financeiro,
    grafico_formas_pagamento,
    grafico_projecao_financeira,
)


class DashboardHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/home.html'

    def get(self, request, *args, **kwargs):
        if request.GET.get('acesso') == 'janela-invalida':
            messages.warning(request, 'Abra as telas internas pelo menu principal do AXIORA ERP.')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configuracao, aniversariantes = buscar_aniversariantes_configurados()
        context['configuracao_sistema'] = configuracao
        context['aniversariantes'] = aniversariantes
        financeiro = buscar_dashboard_financeira(self.request.user)
        context.update(financeiro)
        context.update(buscar_dashboard_executiva(
            self.request.user,
            saldo_disponivel=financeiro.get('saldo_disponivel'),
        ))
        return context


def _resposta_grafico(request, buscar_dados, **kwargs):
    if not usuario_tem_perfil(request.user, ['ADMINISTRADOR', 'GERENTE']):
        return JsonResponse({'detail': 'Acesso restrito à gestão.'}, status=403)
    return JsonResponse(buscar_dados(**kwargs))


@login_required
def api_fluxo_financeiro(request):
    return _resposta_grafico(request, grafico_fluxo_financeiro)


@login_required
def api_formas_pagamento(request):
    return _resposta_grafico(request, grafico_formas_pagamento)


@login_required
def api_contas(request):
    return _resposta_grafico(request, grafico_contas_30_dias)


@login_required
def api_caixa(request):
    try:
        periodo = int(request.GET.get('periodo', 30))
    except (TypeError, ValueError):
        periodo = 30
    return _resposta_grafico(request, grafico_evolucao_caixa, periodo=periodo)


@login_required
def api_projecao_financeira(request):
    return _resposta_grafico(request, grafico_projecao_financeira)
