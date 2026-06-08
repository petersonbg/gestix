from django.urls import path

from .views import (
    FornecedorCreateView,
    FornecedorDeleteView,
    FornecedorDetailView,
    FornecedorListView,
    FornecedorUpdateView,
)

app_name = 'fornecedores'

urlpatterns = [
    path('', FornecedorListView.as_view(), name='list'),
    path('novo/', FornecedorCreateView.as_view(), name='create'),
    path('<int:pk>/', FornecedorDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', FornecedorUpdateView.as_view(), name='update'),
    path('<int:pk>/excluir/', FornecedorDeleteView.as_view(), name='delete'),
]
