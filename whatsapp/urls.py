from django.urls import path

from .views import (
    ConfiguracaoWhatsAppView,
    EnviarMensagemWhatsAppView,
    FilaMensagemView,
    HistoricoEnviosView,
    ModeloMensagemCreateView,
    ModeloMensagemListView,
    ModeloMensagemUpdateView,
    preview_modelo,
    whatsapp_home,
)

app_name = 'whatsapp'

urlpatterns = [
    path('', whatsapp_home, name='home'),
    path('configuracoes/', ConfiguracaoWhatsAppView.as_view(), name='configuracao'),
    path('modelos/', ModeloMensagemListView.as_view(), name='modelos'),
    path('modelos/novo/', ModeloMensagemCreateView.as_view(), name='modelo_create'),
    path('modelos/<int:pk>/editar/', ModeloMensagemUpdateView.as_view(), name='modelo_update'),
    path('enviar/', EnviarMensagemWhatsAppView.as_view(), name='enviar'),
    path('preview-modelo/', preview_modelo, name='preview_modelo'),
    path('historico/', HistoricoEnviosView.as_view(), name='historico'),
    path('fila/', FilaMensagemView.as_view(), name='fila'),
]