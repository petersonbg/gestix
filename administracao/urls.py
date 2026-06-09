from django.urls import path

from .views import (
    AdministracaoHomeView,
    ConfiguracaoSistemaView,
    EmpresaDetailView,
    EmpresaUpdateView,
    LogsAtividadeView,
    UsuariosPermissoesView,
)

app_name = 'administracao'

urlpatterns = [
    path('', AdministracaoHomeView.as_view(), name='home'),
    path('dados-empresa/', EmpresaDetailView.as_view(), name='dados_empresa'),
    path('dados-empresa/editar/', EmpresaUpdateView.as_view(), name='dados_empresa_editar'),
    path('configuracoes-sistema/', ConfiguracaoSistemaView.as_view(), name='configuracoes_sistema'),
    path('usuarios-permissoes/', UsuariosPermissoesView.as_view(), name='usuarios_permissoes'),
    path('logs-atividade/', LogsAtividadeView.as_view(), name='logs_atividade'),
]
