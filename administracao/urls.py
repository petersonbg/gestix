from django.urls import path

from .views import (
    AdministracaoHomeView,
    CategoriaProdutoCreateView,
    CategoriaProdutoDetailView,
    CategoriaProdutoListView,
    CategoriaProdutoUpdateView,
    ConfiguracaoSistemaView,
    EmpresaDetailView,
    EmpresaUpdateView,
    LogsAtividadeView,
    UsuariosPermissoesView,
)

app_name = 'administracao'

urlpatterns = [
    path('', AdministracaoHomeView.as_view(), name='home'),
    path('categorias-produtos/', CategoriaProdutoListView.as_view(), name='categorias_produtos'),
    path('categorias-produtos/nova/', CategoriaProdutoCreateView.as_view(), name='categoria_produto_criar'),
    path('categorias-produtos/<int:pk>/', CategoriaProdutoDetailView.as_view(), name='categoria_produto_detalhe'),
    path('categorias-produtos/<int:pk>/editar/', CategoriaProdutoUpdateView.as_view(), name='categoria_produto_editar'),
    path('dados-empresa/', EmpresaDetailView.as_view(), name='dados_empresa'),
    path('dados-empresa/editar/', EmpresaUpdateView.as_view(), name='dados_empresa_editar'),
    path('configuracoes-sistema/', ConfiguracaoSistemaView.as_view(), name='configuracoes_sistema'),
    path('usuarios-permissoes/', UsuariosPermissoesView.as_view(), name='usuarios_permissoes'),
    path('logs-atividade/', LogsAtividadeView.as_view(), name='logs_atividade'),
]
