from django.urls import path

from .views import ConfiguracaoSistemaView

app_name = 'configuracoes'

urlpatterns = [
    path('', ConfiguracaoSistemaView.as_view(), name='sistema'),
]
