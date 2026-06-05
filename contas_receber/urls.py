from django.urls import path

from . import views

app_name = 'contas_receber'

urlpatterns = [
    path('', views.ContaReceberListView.as_view(), name='list'),
    path('vencidas/', views.ContaReceberListView.as_view(modo='vencidas'), name='vencidas'),
    path('atrasadas/', views.ContaReceberListView.as_view(modo='atrasadas'), name='atrasadas'),
    path('hoje/', views.ContaReceberListView.as_view(modo='hoje'), name='hoje'),
    path('<int:pk>/', views.ContaReceberDetailView.as_view(), name='detail'),
    path('<int:pk>/receber/', views.ContaReceberReceberView.as_view(), name='receber'),
]
