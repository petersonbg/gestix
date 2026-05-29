from django.urls import path

from .views import VendaCreateView, VendaDetailView, VendaFinalizarView, VendaListView

app_name = 'vendas'

urlpatterns = [
    path('', VendaListView.as_view(), name='list'),
    path('nova/', VendaCreateView.as_view(), name='create'),
    path('<int:pk>/', VendaDetailView.as_view(), name='detail'),
    path('<int:pk>/finalizar/', VendaFinalizarView.as_view(), name='finalizar'),
]
