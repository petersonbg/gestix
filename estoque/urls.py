from django.urls import path

from .views import EstoqueProdutoListView, MovimentacaoEstoqueCreateView, ProdutoHistoricoEstoqueView

app_name = 'estoque'

urlpatterns = [
    path('', EstoqueProdutoListView.as_view(), name='list'),
    path('movimentar/', MovimentacaoEstoqueCreateView.as_view(), name='movimentar'),
    path('produtos/<int:produto_pk>/historico/', ProdutoHistoricoEstoqueView.as_view(), name='produto_historico'),
]
