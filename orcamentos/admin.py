from django.contrib import admin

from .models import ItemOrcamento, Orcamento


class ItemOrcamentoInline(admin.TabularInline):
    model = ItemOrcamento
    extra = 0
    readonly_fields = ('total_item',)


@admin.register(Orcamento)
class OrcamentoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'data', 'subtotal', 'desconto', 'total', 'status', 'usuario', 'venda')
    list_filter = ('status', 'data')
    search_fields = ('cliente__nome', 'id')
    readonly_fields = ('subtotal', 'total', 'data', 'venda')
    inlines = [ItemOrcamentoInline]
