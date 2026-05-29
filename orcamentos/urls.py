from django.urls import path

from .views import (
    OrcamentoConverterView,
    OrcamentoCreateView,
    OrcamentoDetailView,
    OrcamentoListView,
    OrcamentoPrintView,
)

app_name = 'orcamentos'

urlpatterns = [
    path('', OrcamentoListView.as_view(), name='list'),
    path('novo/', OrcamentoCreateView.as_view(), name='create'),
    path('<int:pk>/', OrcamentoDetailView.as_view(), name='detail'),
    path('<int:pk>/converter/', OrcamentoConverterView.as_view(), name='converter'),
    path('<int:pk>/imprimir/', OrcamentoPrintView.as_view(), name='print'),
]
