from django.urls import path
from . import views

app_name = 'ordens_servico'
urlpatterns = [
    path('', views.OrdemServicoListView.as_view(), name='list'),
    path('nova/', views.OrdemServicoCreateView.as_view(), name='create'),
    path('servicos/', views.ServicoListView.as_view(), name='servicos'),
    path('servicos/novo/', views.ServicoCreateView.as_view(), name='servico_create'),
    path('servicos/<int:pk>/editar/', views.ServicoUpdateView.as_view(), name='servico_update'),
    path('clientes/buscar/', views.buscar_clientes, name='buscar_clientes'),
    path('produtos/buscar/', views.buscar_produtos, name='buscar_produtos'),
    path('servicos/buscar/', views.buscar_servicos, name='buscar_servicos'),
    path('<int:pk>/', views.OrdemServicoDetailView.as_view(), name='detail'),
    path('<int:pk>/editar/', views.OrdemServicoUpdateView.as_view(), name='update'),
    path('<int:pk>/status/', views.alterar_status, name='status'),
    path('<int:pk>/concluir/', views.concluir, name='concluir'),
    path('<int:pk>/cancelar/', views.cancelar, name='cancelar'),
    path('<int:pk>/entregar/', views.entregar, name='entregar'),
    path('<int:pk>/pagamento/', views.registrar_pagamento, name='pagamento'),
    path('<int:pk>/imprimir/', views.imprimir, name='imprimir'),
]
