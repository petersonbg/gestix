from django.urls import path

from .views import AdministracaoHomeView, ConfiguracaoSistemaView, EmpresaDetailView, EmpresaUpdateView

app_name = 'administracao'

urlpatterns = [
    path('', AdministracaoHomeView.as_view(), name='home'),
    path('dados-empresa/', EmpresaDetailView.as_view(), name='dados_empresa'),
    path('dados-empresa/editar/', EmpresaUpdateView.as_view(), name='dados_empresa_editar'),
    path('configuracoes-sistema/', ConfiguracaoSistemaView.as_view(), name='configuracoes_sistema'),
]
