from django.contrib import admin

from .forms import ConfiguracaoWhatsAppForm
from .models import ConfiguracaoWhatsApp, FilaMensagemWhatsApp, MensagemWhatsApp, ModeloMensagemWhatsApp


@admin.register(ConfiguracaoWhatsApp)
class ConfiguracaoWhatsAppAdmin(admin.ModelAdmin):
    form = ConfiguracaoWhatsAppForm
    list_display = ('modo_envio', 'provedor_api', 'numero_remetente', 'ativo', 'enviar_automaticamente', 'atualizado_em')
    list_filter = ('modo_envio', 'provedor_api', 'ativo', 'enviar_automaticamente')
    search_fields = ('numero_remetente', 'api_url')
    readonly_fields = ('criado_em', 'atualizado_em')



@admin.register(ModeloMensagemWhatsApp)
class ModeloMensagemWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'ativo', 'atualizado_em')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome', 'mensagem')
    readonly_fields = ('criado_em', 'atualizado_em')


@admin.register(MensagemWhatsApp)
class MensagemWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('telefone', 'cliente', 'tipo', 'modo_envio', 'status', 'usuario', 'data_envio', 'criado_em')
    list_filter = ('tipo', 'modo_envio', 'status', 'criado_em')
    search_fields = ('telefone', 'mensagem', 'cliente__nome', 'usuario__username')
    readonly_fields = ('criado_em',)
    autocomplete_fields = ('cliente', 'usuario')


@admin.register(FilaMensagemWhatsApp)
class FilaMensagemWhatsAppAdmin(admin.ModelAdmin):
    list_display = ('telefone', 'cliente', 'tipo', 'status', 'tentativas', 'agendada_para', 'usuario_criacao', 'criado_em')
    list_filter = ('tipo', 'status', 'agendada_para', 'criado_em')
    search_fields = ('telefone', 'mensagem', 'cliente__nome', 'usuario_criacao__username')
    readonly_fields = ('criado_em', 'atualizado_em')
    autocomplete_fields = ('cliente', 'usuario_criacao')