from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView, UpdateView

from dashboard.models import ConfiguracaoSistema

from .forms import ConfiguracaoSistemaAdministracaoForm, DadosEmpresaForm
from .models import DadosEmpresa


def usuario_administrador(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Administrador').exists())


def usuario_gerente(user):
    return user.is_authenticated and user.groups.filter(name='Gerente').exists()


def usuario_pode_visualizar_administracao(user):
    return usuario_administrador(user) or usuario_gerente(user)


class AdministracaoPermissaoMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return usuario_pode_visualizar_administracao(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Você não possui permissão para acessar a Administração.')
        return redirect('dashboard')


class AdministracaoHomeView(AdministracaoPermissaoMixin, TemplateView):
    template_name = 'administracao/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        context['empresa'] = DadosEmpresa.get_solo()
        context['configuracao'] = ConfiguracaoSistema.get_solo()
        return context


class AdministracaoUpdateMixin(AdministracaoPermissaoMixin, UpdateView):
    def pode_editar(self):
        return usuario_administrador(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['somente_leitura'] = not self.pode_editar()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = self.pode_editar()
        return context

    def post(self, request, *args, **kwargs):
        if not self.pode_editar():
            messages.error(request, 'Apenas administradores podem alterar estas configurações.')
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)


class DadosEmpresaView(AdministracaoUpdateMixin):
    model = DadosEmpresa
    form_class = DadosEmpresaForm
    template_name = 'administracao/dados_empresa.html'
    context_object_name = 'empresa'
    success_url = reverse_lazy('administracao:dados_empresa')

    def get_object(self, queryset=None):
        return DadosEmpresa.get_solo()

    def form_valid(self, form):
        messages.success(self.request, 'Dados da empresa atualizados com sucesso.')
        return super().form_valid(form)


class ConfiguracaoSistemaView(AdministracaoUpdateMixin):
    model = ConfiguracaoSistema
    form_class = ConfiguracaoSistemaAdministracaoForm
    template_name = 'administracao/configuracoes_sistema.html'
    context_object_name = 'configuracao'
    success_url = reverse_lazy('administracao:configuracoes_sistema')

    def get_object(self, queryset=None):
        return ConfiguracaoSistema.get_solo()

    def form_valid(self, form):
        messages.success(self.request, 'Configurações do sistema atualizadas com sucesso.')
        return super().form_valid(form)
