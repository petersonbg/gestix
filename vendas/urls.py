from django.urls import path

from .views import ClienteBuscaView, ProdutoBuscaView, VendaCreateView, VendaDetailView, VendaFinalizarView, VendaListView, VendaPrintView

app_name = 'vendas'

urlpatterns = [
    path('', VendaListView.as_view(), name='list'),
    path('nova/', VendaCreateView.as_view(), name='create'),
    path('buscar-produtos/', ProdutoBuscaView.as_view(), name='buscar_produtos'),
    path('clientes/buscar/', ClienteBuscaView.as_view(), name='buscar_clientes'),
    path('<int:pk>/', VendaDetailView.as_view(), name='detail'),
    path('<int:pk>/finalizar/', VendaFinalizarView.as_view(), name='finalizar'),
    path('<int:pk>/imprimir/', VendaPrintView.as_view(), name='imprimir'),
]
