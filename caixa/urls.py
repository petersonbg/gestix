from django.urls import path

from .views import (
    CaixaAtualView,
    CaixaHistoricoView,
    CaixaIndexView,
    CaixaAbrirView,
    CaixaFecharView,
    CaixaMovimentacaoView,
)

app_name = 'caixa'

urlpatterns = [
    path('', CaixaIndexView.as_view(), name='index'),
    path('abrir/', CaixaAbrirView.as_view(), name='abrir'),
    path('atual/', CaixaAtualView.as_view(), name='atual'),
    path('suprimento/', CaixaMovimentacaoView.as_view(tipo='SUPRIMENTO'), name='suprimento'),
    path('sangria/', CaixaMovimentacaoView.as_view(tipo='SANGRIA'), name='sangria'),
    path('saida/', CaixaMovimentacaoView.as_view(tipo='SAIDA'), name='saida'),
    path('fechar/', CaixaFecharView.as_view(), name='fechar'),
    path('historico/', CaixaHistoricoView.as_view(), name='historico'),
]
