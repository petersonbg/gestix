from django.urls import path

from .views import (
    ProdutoCreateView,
    ProdutoDeleteView,
    ProdutoDetailView,
    ProdutoListView,
    ProdutoUpdateView,
)

app_name = 'produtos'

urlpatterns = [
    path('', ProdutoListView.as_view(), name='list'),
    path('novo/', ProdutoCreateView.as_view(), name='create'),
    path('<int:pk>/', ProdutoDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', ProdutoUpdateView.as_view(), name='update'),
    path('<int:pk>/excluir/', ProdutoDeleteView.as_view(), name='delete'),
]
