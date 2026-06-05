"""URL configuration for the GESTIX project."""
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

from accounts.views import GestixLoginView, GestixLogoutView
from dashboard.views import DashboardHomeView

urlpatterns = [
    path('', TemplateView.as_view(template_name='core/home.html'), name='home'),
    path('accounts/login/', GestixLoginView.as_view(), name='login'),
    path('accounts/logout/', GestixLogoutView.as_view(), name='logout'),
    path('dashboard/', DashboardHomeView.as_view(), name='dashboard'),
    path('configuracoes/', include('dashboard.urls')),
    path('clientes/', include('clientes.urls')),
    path('fornecedores/', include('fornecedores.urls')),
    path('produtos/', include('produtos.urls')),
    path('estoque/', include('estoque.urls')),
    path('vendas/', include('vendas.urls')),
    path('caixa/', include('caixa.urls')),
    path('contas-receber/', include('contas_receber.urls')),
    path('contas-pagar/', include('contas_pagar.urls')),
    path('orcamentos/', include('orcamentos.urls')),
    path('fiscal/', include('fiscal.urls')),
    path('admin/', admin.site.urls),
]
