from django.urls import path

from . import views


app_name = 'relatorios'

urlpatterns = [
    path('', views.RelatoriosHomeView.as_view(), name='home'),
    path('vendas/', views.VendasPeriodoView.as_view(), name='vendas'),
    path('estoque-baixo/', views.EstoqueBaixoView.as_view(), name='estoque_baixo'),
    path('contas-receber/', views.ContasReceberView.as_view(), name='contas_receber'),
    path('contas-pagar/', views.ContasPagarView.as_view(), name='contas_pagar'),
    path('caixa-diario/', views.CaixaDiarioView.as_view(), name='caixa_diario'),
]
