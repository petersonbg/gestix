from django.contrib import admin

from .models import ItemNotaFiscalEntrada, NotaFiscalEntrada


class ItemNotaFiscalEntradaInline(admin.TabularInline):
    model = ItemNotaFiscalEntrada
    extra = 0
    readonly_fields = ('numero_item', 'codigo_produto', 'descricao', 'ncm', 'unidade_medida', 'quantidade', 'valor_unitario', 'valor_total')


@admin.register(NotaFiscalEntrada)
class NotaFiscalEntradaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'serie', 'chave_acesso', 'emitente_razao_social', 'valor_total', 'status', 'data_emissao')
    list_filter = ('status', 'data_emissao')
    search_fields = ('chave_acesso', 'numero', 'emitente_cnpj', 'emitente_razao_social')
    readonly_fields = ('criado_em', 'atualizado_em')
    inlines = [ItemNotaFiscalEntradaInline]
