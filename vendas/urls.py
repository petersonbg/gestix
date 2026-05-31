from django.urls import path

from .views import ProdutoBuscaView, VendaCreateView, VendaDetailView, VendaFinalizarView, VendaListView

app_name = 'vendas'

urlpatterns = [
    path('', VendaListView.as_view(), name='list'),
    path('nova/', VendaCreateView.as_view(), name='create'),
    path('buscar-produtos/', ProdutoBuscaView.as_view(), name='buscar_produtos'),
    path('<int:pk>/', VendaDetailView.as_view(), name='detail'),
    path('<int:pk>/finalizar/', VendaFinalizarView.as_view(), name='finalizar'),
]
