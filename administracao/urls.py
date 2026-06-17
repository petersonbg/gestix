from django.urls import path

from .views import (
    AdministracaoHomeView,
<<<<<<< HEAD
    BackupDownloadView,
    BackupRestoreView,
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
    CategoriaProdutoCreateView,
    CategoriaProdutoDetailView,
    CategoriaProdutoListView,
    CategoriaProdutoUpdateView,
    ConfiguracaoSistemaView,
    EmpresaDetailView,
    EmpresaUpdateView,
    LogsAtividadeView,
<<<<<<< HEAD
    LogAtividadeDetailView,
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
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
<<<<<<< HEAD
    path('backup/', BackupRestoreView.as_view(), name='backup'),
    path('backup/<int:pk>/download/', BackupDownloadView.as_view(), name='backup_download'),
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
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
<<<<<<< HEAD
    path('logs/', LogsAtividadeView.as_view(), name='logs_atividade'),
    path('logs/<int:pk>/', LogAtividadeDetailView.as_view(), name='log_detalhe'),
    path('logs-atividade/', LogsAtividadeView.as_view(), name='logs_atividade_legacy'),
=======
    path('logs-atividade/', LogsAtividadeView.as_view(), name='logs_atividade'),
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
]
