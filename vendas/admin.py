from django.contrib import admin

from .models import ItemVenda, Venda


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 0
    readonly_fields = ('total_item',)


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'data', 'subtotal', 'desconto', 'total', 'status', 'usuario')
    list_filter = ('status', 'data')
    search_fields = ('cliente__nome', 'id')
    readonly_fields = ('subtotal', 'total', 'data')
    inlines = [ItemVendaInline]
