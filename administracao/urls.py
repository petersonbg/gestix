from django.urls import path

from .views import (
    AdministracaoHomeView,
    BackupDownloadView,
    BackupRestoreView,
    CategoriaProdutoCreateView,
    CategoriaProdutoDetailView,
    CategoriaProdutoListView,
    CategoriaProdutoUpdateView,
    ConfiguracaoSistemaView,
    EmpresaDetailView,
    EmpresaUpdateView,
    LogsAtividadeView,
    LogAtividadeDetailView,
    ServicoCreateView,
    ServicoDetailView,
    ServicoListView,
    ServicoUpdateView,
    servico_alterar_ativo,
    UsuariosPermissoesView,
)

app_name = 'administracao'

urlpatterns = [
    path('', AdministracaoHomeView.as_view(), name='home'),
    path('backup/', BackupRestoreView.as_view(), name='backup'),
    path('backup/<int:pk>/download/', BackupDownloadView.as_view(), name='backup_download'),
    path('servicos/', ServicoListView.as_view(), name='servicos'),
    path('servicos/novo/', ServicoCreateView.as_view(), name='servico_criar'),
    path('servicos/<int:pk>/', ServicoDetailView.as_view(), name='servico_detalhe'),
    path('servicos/<int:pk>/editar/', ServicoUpdateView.as_view(), name='servico_editar'),
    path('servicos/<int:pk>/inativar/', servico_alterar_ativo, name='servico_alterar_ativo'),
    path('categorias-produtos/', CategoriaProdutoListView.as_view(), name='categorias_produtos'),
    path('categorias-produtos/nova/', CategoriaProdutoCreateView.as_view(), name='categoria_produto_criar'),
    path('categorias-produtos/<int:pk>/', CategoriaProdutoDetailView.as_view(), name='categoria_produto_detalhe'),
    path('categorias-produtos/<int:pk>/editar/', CategoriaProdutoUpdateView.as_view(), name='categoria_produto_editar'),
    path('dados-empresa/', EmpresaDetailView.as_view(), name='dados_empresa'),
    path('dados-empresa/editar/', EmpresaUpdateView.as_view(), name='dados_empresa_editar'),
    path('configuracoes-sistema/', ConfiguracaoSistemaView.as_view(), name='configuracoes_sistema'),
    path('usuarios-permissoes/', UsuariosPermissoesView.as_view(), name='usuarios_permissoes'),
    path('logs/', LogsAtividadeView.as_view(), name='logs_atividade'),
    path('logs/<int:pk>/', LogAtividadeDetailView.as_view(), name='log_detalhe'),
    path('logs-atividade/', LogsAtividadeView.as_view(), name='logs_atividade_legacy'),
]
