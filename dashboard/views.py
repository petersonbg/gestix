from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from .forms import ConfiguracaoSistemaForm
from .models import ConfiguracaoSistema
from .services import buscar_aniversariantes


def usuario_em_grupo(user, nome_grupo):
    return user.is_authenticated and user.groups.filter(name=nome_grupo).exists()


def usuario_administrador(user):
    return user.is_superuser or usuario_em_grupo(user, 'Administrador')


def usuario_gerente(user):
    return usuario_em_grupo(user, 'Gerente')


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
        return context


class ConfiguracaoSistemaView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = ConfiguracaoSistema
    form_class = ConfiguracaoSistemaForm
    template_name = 'dashboard/configuracao_sistema.html'
    context_object_name = 'configuracao'
    success_url = reverse_lazy('configuracoes:sistema')

    def test_func(self):
        return usuario_administrador(self.request.user) or usuario_gerente(self.request.user)

    def get_object(self, queryset=None):
        return ConfiguracaoSistema.get_solo()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        if not usuario_administrador(request.user):
            messages.error(request, 'Apenas administradores podem alterar as configurações do sistema.')
            return redirect('configuracoes:sistema')
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Configurações do sistema atualizadas com sucesso.')
        return super().form_valid(form)
