from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ('total_item',)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'data', 'forma_pagamento', 'subtotal', 'desconto', 'total', 'status', 'usuario')
    list_filter = ('status', 'forma_pagamento', 'data')
    search_fields = ('cliente__nome', 'id')
    readonly_fields = ('subtotal', 'total', 'data', 'cancelada_em', 'usuario_cancelamento', 'motivo_cancelamento')
    inlines = [ItemVendaInline]
