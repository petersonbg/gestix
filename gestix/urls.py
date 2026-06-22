"""URL configuration for the GESTIX project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.urls import re_path
from django.views.static import serve
from django.views.generic import TemplateView

from accounts.views import AcessoNegadoView, GestixLoginView, GestixLogoutView, manter_sessao_ativa
from dashboard.views import (
    DashboardHomeView,
    api_caixa,
    api_contas,
    api_fluxo_financeiro,
    api_formas_pagamento,
    api_projecao_financeira,
)

urlpatterns = [
    path('', TemplateView.as_view(template_name='core/home.html'), name='home'),
    path('accounts/login/', GestixLoginView.as_view(), name='login'),
    path('accounts/logout/', GestixLogoutView.as_view(), name='logout'),
    path('accounts/session/keepalive/', manter_sessao_ativa, name='session_keepalive'),
    path('acesso-negado/', AcessoNegadoView.as_view(), name='acesso_negado'),
    path('dashboard/', DashboardHomeView.as_view(), name='dashboard'),
    path('dashboard/api/fluxo-financeiro/', api_fluxo_financeiro, name='dashboard_api_fluxo_financeiro'),
    path('dashboard/api/formas-pagamento/', api_formas_pagamento, name='dashboard_api_formas_pagamento'),
    path('dashboard/api/contas/', api_contas, name='dashboard_api_contas'),
    path('dashboard/api/caixa/', api_caixa, name='dashboard_api_caixa'),
    path('dashboard/api/projecao-financeira/', api_projecao_financeira, name='dashboard_api_projecao_financeira'),
    path('configuracoes/', include('dashboard.urls')),
    path('administracao/', include('administracao.urls')),
    path('clientes/', include('clientes.urls')),
    path('fornecedores/', include('fornecedores.urls')),
    path('produtos/', include('produtos.urls')),
    path('estoque/', include('estoque.urls')),
    path('vendas/', include('vendas.urls')),
    path('caixa/', include('caixa.urls')),
    path('contas-receber/', include('contas_receber.urls')),
    path('contas-pagar/', include('contas_pagar.urls')),
    path('ordens-servico/', include('ordens_servico.urls')),
    path('orcamentos/', include('orcamentos.urls')),
    path('fiscal/', include('fiscal.urls')),
    path('relatorios/', include('relatorios.urls')),
    path('admin/', admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.SERVE_MEDIA_FILES:
    urlpatterns += [
        re_path(
            r'^media/(?P<path>.*)$',
            serve,
            {'document_root': settings.MEDIA_ROOT},
        ),
    ]
