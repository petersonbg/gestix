from django.urls import path

from .views import NFeUploadView, NotaFiscalEntradaConfirmView, NotaFiscalEntradaDetailView, NotaFiscalEntradaListView

app_name = 'fiscal'

urlpatterns = [
    path('', NotaFiscalEntradaListView.as_view(), name='list'),
    path('upload/', NFeUploadView.as_view(), name='upload'),
    path('<int:pk>/', NotaFiscalEntradaDetailView.as_view(), name='detail'),
    path('<int:pk>/confirmar/', NotaFiscalEntradaConfirmView.as_view(), name='confirmar'),
]
