from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from accounts.models import LogAtividade

from .forms import ConfiguracaoSistemaAdministracaoForm, EmpresaForm
from .models import ConfiguracaoSistema, Empresa


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
        context['empresa'] = Empresa.get_solo()
        context['configuracao'] = ConfiguracaoSistema.get_solo()
        context['usuarios_total'] = get_user_model().objects.count()
        context['usuarios_ativos'] = get_user_model().objects.filter(is_active=True).count()
        context['grupos_total'] = Group.objects.count()
        context['logs_total'] = LogAtividade.objects.count()
        context['ultimo_log'] = LogAtividade.objects.select_related('usuario').first()
        return context


class UsuariosPermissoesView(AdministracaoPermissaoMixin, ListView):
    template_name = 'administracao/usuarios_permissoes.html'
    context_object_name = 'usuarios'
    paginate_by = 25

    def get_queryset(self):
        return get_user_model().objects.prefetch_related('groups').order_by('username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['grupos'] = Group.objects.order_by('name')
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class LogsAtividadeView(AdministracaoPermissaoMixin, ListView):
    template_name = 'administracao/logs_atividade.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        return LogAtividade.objects.select_related('usuario').all()


class EmpresaDetailView(AdministracaoPermissaoMixin, DetailView):
    model = Empresa
    template_name = 'administracao/dados_empresa.html'
    context_object_name = 'empresa'

    def get_object(self, queryset=None):
        return Empresa.get_solo()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class EmpresaUpdateView(AdministracaoPermissaoMixin, UpdateView):
    model = Empresa
    form_class = EmpresaForm
    template_name = 'administracao/dados_empresa_form.html'
    context_object_name = 'empresa'
    success_url = reverse_lazy('administracao:dados_empresa')

    def test_func(self):
        return usuario_administrador(self.request.user)

    def get_object(self, queryset=None):
        return Empresa.get_solo()

    def form_valid(self, form):
        messages.success(self.request, 'Dados da empresa atualizados com sucesso.')
        return super().form_valid(form)


class ConfiguracaoSistemaView(AdministracaoPermissaoMixin, UpdateView):
    model = ConfiguracaoSistema
    form_class = ConfiguracaoSistemaAdministracaoForm
    template_name = 'administracao/configuracoes_sistema.html'
    context_object_name = 'configuracao'
    success_url = reverse_lazy('administracao:configuracoes_sistema')

    def pode_editar(self):
        return usuario_administrador(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['somente_leitura'] = not self.pode_editar()
        return kwargs

    def get_object(self, queryset=None):
        return ConfiguracaoSistema.get_solo()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = self.pode_editar()
        return context

    def post(self, request, *args, **kwargs):
        if not self.pode_editar():
            messages.error(request, 'Apenas administradores podem alterar estas configurações.')
            return redirect(self.success_url)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Configurações do sistema atualizadas com sucesso.')
        return super().form_valid(form)
