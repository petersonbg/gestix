from django.urls import path

from .views import (
    ClienteBuscaView,
    OrcamentoConverterView,
    OrcamentoCreateView,
    OrcamentoDetailView,
    OrcamentoListView,
    OrcamentoPrintView,
    ProdutoBuscaView,
)

app_name = 'orcamentos'

urlpatterns = [
    path('', OrcamentoListView.as_view(), name='list'),
    path('novo/', OrcamentoCreateView.as_view(), name='create'),
    path('buscar-produtos/', ProdutoBuscaView.as_view(), name='buscar_produtos'),
    path('clientes/buscar/', ClienteBuscaView.as_view(), name='buscar_clientes'),
    path('<int:pk>/', OrcamentoDetailView.as_view(), name='detail'),
    path('<int:pk>/converter/', OrcamentoConverterView.as_view(), name='converter'),
    path('<int:pk>/imprimir/', OrcamentoPrintView.as_view(), name='imprimir_orcamento'),
    path('<int:pk>/imprimir/', OrcamentoPrintView.as_view(), name='print'),
]
