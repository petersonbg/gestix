from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accounts.models import LogAtividade
from accounts.permissions import usuario_eh_admin, usuario_eh_gerente
from accounts.utils import registrar_log
from ordens_servico.models import Servico

from .forms import (
    BackupRestoreForm, CategoriaProdutoForm, ConfiguracaoSistemaAdministracaoForm,
    EmpresaForm, ServicoForm,
)
from .backup_services import (
    BackupError, backup_root, gerar_backup, limpar_temporario, restaurar_backup,
    salvar_upload_temporario,
)
from .models import BackupRegistro, CategoriaProduto, ConfiguracaoSistema, Empresa


def usuario_administrador(user):
    return getattr(user, 'is_authenticated', False) and usuario_eh_admin(user)


def usuario_gerente(user):
    return getattr(user, 'is_authenticated', False) and usuario_eh_gerente(user)


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


class AdministradorObrigatorioMixin(AdministracaoPermissaoMixin):
    def test_func(self):
        return usuario_administrador(self.request.user)


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
        context['categorias_produtos_total'] = CategoriaProduto.objects.count()
        context['categorias_produtos_ativas'] = CategoriaProduto.objects.filter(ativo=True).count()
        context['servicos_total'] = Servico.objects.count()
        context['servicos_ativos'] = Servico.objects.filter(ativo=True).count()
        context['backups_total'] = BackupRegistro.objects.count()
        context['ultimo_backup'] = BackupRegistro.objects.first()
        context['ultimo_log'] = LogAtividade.objects.select_related('usuario').first()
        return context


class BackupRestoreView(AdministradorObrigatorioMixin, TemplateView):
    template_name = 'administracao/backup/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = kwargs.get('form') or BackupRestoreForm()
        context['historico'] = BackupRegistro.objects.select_related('usuario')[:20]
        context['max_upload_mb'] = settings.BACKUP_MAX_UPLOAD_SIZE // (1024 * 1024)
        return context

    def post(self, request, *args, **kwargs):
        acao = request.POST.get('acao')
        if acao == 'gerar':
            try:
                registrar_log(request.user, 'BACKUP', 'administracao', 'Geração de backup iniciada.', request=request)
                caminho = gerar_backup(usuario=request.user)
            except (BackupError, OSError) as exc:
                registrar_log(request.user, 'ERRO', 'administracao', str(exc), request=request)
                messages.error(request, f'Erro ao gerar backup: {exc}')
            else:
                registrar_log(request.user, 'BACKUP', 'administracao', f'Backup {caminho.name} gerado.', request=request)
                messages.success(request, f'Backup gerado com sucesso: {caminho.name}')
            return redirect('administracao:backup')

        if acao == 'restaurar':
            form = BackupRestoreForm(request.POST, request.FILES)
            if not form.is_valid():
                messages.error(request, 'Revise o arquivo enviado para restauração.')
                return render(request, self.template_name, self.get_context_data(form=form))
            temporario = None
            try:
                registrar_log(request.user, 'RESTAURACAO', 'administracao', 'Restauração de backup iniciada.', request=request)
                temporario = salvar_upload_temporario(form.cleaned_data['arquivo_backup'])
                restaurar_backup(temporario, usuario=request.user)
            except Exception as exc:
                registrar_log(request.user, 'ERRO', 'administracao', str(exc), request=request)
                messages.error(request, f'Erro ao restaurar backup: {exc}')
            else:
                registrar_log(request.user, 'RESTAURACAO', 'administracao', 'Backup restaurado com sucesso.', request=request)
                messages.success(request, 'Backup restaurado com sucesso.')
            finally:
                if temporario:
                    limpar_temporario(temporario)
            return redirect('administracao:backup')

        messages.error(request, 'Ação inválida.')
        return redirect('administracao:backup')


class BackupDownloadView(AdministradorObrigatorioMixin, TemplateView):
    def get(self, request, pk):
        registro = get_object_or_404(
            BackupRegistro,
            pk=pk,
            tipo=BackupRegistro.Tipo.BACKUP,
            status=BackupRegistro.Status.SUCESSO,
        )
        nome = registro.nome_arquivo or registro.arquivo
        caminho = (backup_root() / nome).resolve()
        if backup_root() not in caminho.parents or not caminho.exists():
            raise Http404('Backup não encontrado.')
        return FileResponse(
            caminho.open('rb'),
            as_attachment=True,
            filename=caminho.name,
            content_type='application/octet-stream',
        )


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
    template_name = 'administracao/logs/lista.html'
    context_object_name = 'logs'
    paginate_by = 50

    def test_func(self):
        return usuario_administrador(self.request.user)

    def get_queryset(self):
        queryset = LogAtividade.objects.select_related('usuario').all()
        usuario = self.request.GET.get('usuario', '').strip()
        acao = self.request.GET.get('acao', '').strip()
        modulo = self.request.GET.get('modulo', '').strip()
        data_inicial = parse_date(self.request.GET.get('data_inicial', '') or '')
        data_final = parse_date(self.request.GET.get('data_final', '') or '')
        texto = self.request.GET.get('q', '').strip()

        if usuario.isdigit():
            queryset = queryset.filter(usuario_id=usuario)
        if acao:
            queryset = queryset.filter(acao=acao)
        if modulo:
            queryset = queryset.filter(modulo=modulo)
        if data_inicial:
            queryset = queryset.filter(criado_em__date__gte=data_inicial)
        if data_final:
            queryset = queryset.filter(criado_em__date__lte=data_final)
        if texto:
            queryset = queryset.filter(
                Q(descricao__icontains=texto)
                | Q(objeto_tipo__icontains=texto)
                | Q(objeto_id__icontains=texto)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['usuarios'] = User.objects.order_by('username')
        context['acoes'] = LogAtividade.Acao.choices
        context['modulos'] = (
            LogAtividade.objects.exclude(modulo='')
            .values_list('modulo', flat=True)
            .distinct()
            .order_by('modulo')
        )
        context['filtros'] = self.request.GET
        return context


class LogAtividadeDetailView(AdministracaoPermissaoMixin, DetailView):
    model = LogAtividade
    template_name = 'administracao/logs/detalhe.html'
    context_object_name = 'log'

    def test_func(self):
        return usuario_administrador(self.request.user)


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


class CategoriaProdutoListView(AdministracaoPermissaoMixin, ListView):
    model = CategoriaProduto
    template_name = 'administracao/categorias_produtos/lista.html'
    context_object_name = 'categorias'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class CategoriaProdutoDetailView(AdministracaoPermissaoMixin, DetailView):
    model = CategoriaProduto
    template_name = 'administracao/categorias_produtos/detalhe.html'
    context_object_name = 'categoria'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class CategoriaProdutoCreateView(AdministracaoPermissaoMixin, CreateView):
    model = CategoriaProduto
    form_class = CategoriaProdutoForm
    template_name = 'administracao/categorias_produtos/form.html'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria de produto criada com sucesso.')
        return super().form_valid(form)


class CategoriaProdutoUpdateView(AdministracaoPermissaoMixin, UpdateView):
    model = CategoriaProduto
    form_class = CategoriaProdutoForm
    template_name = 'administracao/categorias_produtos/form.html'
    context_object_name = 'categoria'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria de produto atualizada com sucesso.')
        return super().form_valid(form)


class ServicoListView(AdministracaoPermissaoMixin, ListView):
    model = Servico
    template_name = 'administracao/servicos/lista.html'
    context_object_name = 'servicos'
    paginate_by = 25

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(nome__icontains=query) | Q(descricao__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class ServicoDetailView(AdministracaoPermissaoMixin, DetailView):
    model = Servico
    template_name = 'administracao/servicos/detalhe.html'
    context_object_name = 'servico'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_editar'] = usuario_administrador(self.request.user)
        return context


class ServicoCreateView(AdministracaoPermissaoMixin, CreateView):
    model = Servico
    form_class = ServicoForm
    template_name = 'administracao/servicos/form.html'
    success_url = reverse_lazy('administracao:servicos')

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Serviço cadastrado com sucesso.')
        return super().form_valid(form)


class ServicoUpdateView(AdministracaoPermissaoMixin, UpdateView):
    model = Servico
    form_class = ServicoForm
    template_name = 'administracao/servicos/form.html'
    context_object_name = 'servico'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Serviço atualizado com sucesso.')
        return super().form_valid(form)


@login_required
@require_POST
def servico_alterar_ativo(request, pk):
    if not usuario_administrador(request.user):
        messages.error(request, 'Apenas administradores podem ativar ou inativar serviços.')
        return redirect('administracao:servicos')
    servico = get_object_or_404(Servico, pk=pk)
    servico.ativo = not servico.ativo
    servico.save(update_fields=['ativo', 'atualizado_em'])
    messages.success(
        request,
        f'Serviço {"ativado" if servico.ativo else "inativado"} com sucesso.',
    )
    return redirect(servico.get_absolute_url())
