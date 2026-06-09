from django.urls import path

from . import views

app_name = 'contas_pagar'

urlpatterns = [
    path('', views.ContaPagarListView.as_view(), name='list'),
    path('nova/', views.ContaPagarCreateView.as_view(), name='create'),
    path('<int:pk>/', views.ContaPagarDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.ContaPagarUpdateView.as_view(), name='update'),
    path('<int:pk>/pagar/', views.ContaPagarPagamentoView.as_view(), name='pagar'),
    path('<int:pk>/cancelar/', views.ContaPagarCancelamentoView.as_view(), name='cancelar'),
]
