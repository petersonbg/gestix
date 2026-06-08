from django.urls import path

from .views import AdministracaoHomeView, ConfiguracaoSistemaView, DadosEmpresaView

app_name = 'administracao'

urlpatterns = [
    path('', AdministracaoHomeView.as_view(), name='home'),
    path('dados-empresa/', DadosEmpresaView.as_view(), name='dados_empresa'),
    path('configuracoes-sistema/', ConfiguracaoSistemaView.as_view(), name='configuracoes_sistema'),
]
