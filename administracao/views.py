from pathlib import Path

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.models import Group
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from accounts.models import LogAtividade
from accounts.utils import registrar_log
from ordens_servico.models import Servico

from .backup_service import (
    ErroBackup, gerar_backup, restaurar_backup, salvar_upload_temporario,
)
from .forms import (
    CategoriaProdutoForm, ConfiguracaoSistemaAdministracaoForm, EmpresaForm,
    RestaurarBackupForm, ServicoForm,
)
from .models import BackupRegistro, CategoriaProduto, ConfiguracaoSistema, Empresa


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
        context['categorias_produtos_total'] = CategoriaProduto.objects.count()
        context['categorias_produtos_ativas'] = CategoriaProduto.objects.filter(ativo=True).count()
        context['servicos_total'] = Servico.objects.count()
        context['servicos_ativos'] = Servico.objects.filter(ativo=True).count()
        context['ultimo_log'] = LogAtividade.objects.select_related('usuario').first()
        return context


class BackupView(AdministracaoPermissaoMixin, TemplateView):
    template_name = 'administracao/backup/index.html'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_restauracao'] = kwargs.get('form_restauracao') or RestaurarBackupForm()
        context['registros'] = BackupRegistro.objects.select_related('usuario')[:50]
        return context


@login_required
@require_POST
def gerar_backup_view(request):
    if not usuario_administrador(request.user):
        messages.error(request, 'Apenas administradores podem gerar backups.')
        return redirect('dashboard')
    try:
        registro = gerar_backup(usuario=request.user)
        registrar_log(
            request.user, 'BACKUP', 'administracao',
            f'Backup {registro.nome_arquivo} gerado com sucesso.',
            objeto=registro, request=request,
        )
        messages.success(request, 'Backup gerado com sucesso.')
    except ErroBackup as exc:
        registrar_log(
            request.user, 'ERRO', 'administracao', str(exc), request=request,
        )
        messages.error(request, f'Não foi possível gerar o backup: {exc}')
    return redirect('administracao:backup')


@login_required
@require_POST
def restaurar_backup_view(request):
    if not usuario_administrador(request.user):
        messages.error(request, 'Apenas administradores podem restaurar backups.')
        return redirect('dashboard')

    form = RestaurarBackupForm(request.POST, request.FILES)
    if not form.is_valid():
        view = BackupView()
        view.setup(request)
        return view.render_to_response(
            view.get_context_data(form_restauracao=form),
            status=400,
        )

    arquivo = form.cleaned_data['arquivo']
    temporario = None
    registrar_log(
        request.user, 'RESTAURACAO', 'administracao',
        f'Restauração iniciada com o arquivo {Path(arquivo.name).name}.', request=request,
    )
    try:
        temporario = salvar_upload_temporario(arquivo)
        registro = restaurar_backup(
            temporario,
            usuario=request.user,
            nome_arquivo=arquivo.name,
        )
        registrar_log(
            request.user, 'RESTAURACAO', 'administracao',
            registro.mensagem, objeto=registro, request=request,
        )
        messages.success(request, 'Restauração concluída com sucesso.')
    except ErroBackup as exc:
        nome_arquivo = Path(arquivo.name).name
        if not BackupRegistro.objects.filter(
            tipo=BackupRegistro.Tipo.RESTAURACAO,
            nome_arquivo=nome_arquivo,
            usuario=request.user,
            status=BackupRegistro.Status.ERRO,
        ).exists():
            BackupRegistro.objects.create(
                tipo=BackupRegistro.Tipo.RESTAURACAO,
                nome_arquivo=nome_arquivo,
                tamanho_arquivo=arquivo.size,
                usuario=request.user,
                status=BackupRegistro.Status.ERRO,
                mensagem=str(exc),
            )
        registrar_log(
            request.user, 'ERRO', 'administracao', str(exc), request=request,
        )
        messages.error(request, f'Não foi possível restaurar o backup: {exc}')
    finally:
        if temporario:
            temporario.unlink(missing_ok=True)
    return redirect('administracao:backup')


@login_required
def baixar_backup_view(request, pk):
    if not usuario_administrador(request.user):
        messages.error(request, 'Apenas administradores podem baixar backups.')
        return redirect('dashboard')
    registro = get_object_or_404(
        BackupRegistro,
        pk=pk,
        tipo=BackupRegistro.Tipo.BACKUP,
        status=BackupRegistro.Status.SUCESSO,
    )
    if not registro.arquivo:
        raise Http404('Arquivo de backup indisponível.')
    try:
        arquivo = registro.arquivo.open('rb')
    except (FileNotFoundError, OSError):
        raise Http404('Arquivo de backup indisponível.')
    registrar_log(
        request.user, 'BACKUP', 'administracao',
        f'Backup {registro.nome_arquivo} baixado.', objeto=registro, request=request,
    )
    return FileResponse(
        arquivo,
        as_attachment=True,
        filename=Path(registro.nome_arquivo).name,
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

    def get_queryset(self):
        queryset = LogAtividade.objects.select_related('usuario').all()
        usuario = self.request.GET.get('usuario', '').strip()
        acao = self.request.GET.get('acao', '').strip()
        modulo = self.request.GET.get('modulo', '').strip()
        data_inicial = self.request.GET.get('data_inicial', '').strip()
        data_final = self.request.GET.get('data_final', '').strip()
        texto = self.request.GET.get('texto', '').strip()
        if usuario:
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
            queryset = queryset.filter(descricao__icontains=texto)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['usuarios'] = get_user_model().objects.filter(
            logs_atividade__isnull=False
        ).distinct().order_by('username')
        context['acoes'] = LogAtividade.Acao.choices
        context['modulos'] = LogAtividade.objects.order_by('modulo').values_list(
            'modulo', flat=True
        ).distinct()
        context['filtros'] = self.request.GET
        return context


class LogAtividadeDetailView(AdministracaoPermissaoMixin, DetailView):
    model = LogAtividade
    template_name = 'administracao/logs/detalhe.html'
    context_object_name = 'log'


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
        response = super().form_valid(form)
        registrar_log(self.request.user, 'EDICAO', 'administracao', 'Dados da empresa atualizados.', objeto=self.object, request=self.request)
        return response


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
        response = super().form_valid(form)
        registrar_log(self.request.user, 'EDICAO', 'administracao', 'Configurações do sistema atualizadas.', objeto=self.object, request=self.request)
        return response


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
        response = super().form_valid(form)
        registrar_log(self.request.user, 'CRIACAO', 'administracao', f'Categoria {self.object.nome} criada.', objeto=self.object, request=self.request)
        return response


class CategoriaProdutoUpdateView(AdministracaoPermissaoMixin, UpdateView):
    model = CategoriaProduto
    form_class = CategoriaProdutoForm
    template_name = 'administracao/categorias_produtos/form.html'
    context_object_name = 'categoria'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Categoria de produto atualizada com sucesso.')
        response = super().form_valid(form)
        registrar_log(self.request.user, 'EDICAO', 'administracao', f'Categoria {self.object.nome} atualizada.', objeto=self.object, request=self.request)
        return response


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
        response = super().form_valid(form)
        registrar_log(self.request.user, 'CRIACAO', 'administracao', f'Serviço {self.object.nome} criado.', objeto=self.object, request=self.request)
        return response


class ServicoUpdateView(AdministracaoPermissaoMixin, UpdateView):
    model = Servico
    form_class = ServicoForm
    template_name = 'administracao/servicos/form.html'
    context_object_name = 'servico'

    def test_func(self):
        return usuario_administrador(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Serviço atualizado com sucesso.')
        response = super().form_valid(form)
        registrar_log(self.request.user, 'EDICAO', 'administracao', f'Serviço {self.object.nome} atualizado.', objeto=self.object, request=self.request)
        return response


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
