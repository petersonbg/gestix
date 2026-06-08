from django.urls import path
from django.views.generic import RedirectView

app_name = 'configuracoes'

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='administracao:configuracoes_sistema', permanent=False), name='sistema'),
]
