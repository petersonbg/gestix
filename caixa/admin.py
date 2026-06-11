from django.contrib import admin

from .models import Caixa, MovimentacaoCaixa


@admin.register(Caixa)
class CaixaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'usuario_abertura',
        'data_abertura',
        'status',
        'valor_inicial',
        'valor_fechamento_calculado',
        'diferenca',
    )
    list_filter = ('status', 'usuario_abertura', 'data_abertura')
    search_fields = ('usuario_abertura__username', 'usuario_abertura__first_name', 'usuario_abertura__last_name')
    readonly_fields = ('data_abertura', 'data_fechamento', 'valor_fechamento_calculado', 'diferenca')


@admin.register(MovimentacaoCaixa)
class MovimentacaoCaixaAdmin(admin.ModelAdmin):
    list_display = ('id', 'caixa', 'tipo', 'descricao', 'valor', 'forma_pagamento', 'usuario', 'data')
    list_filter = ('tipo', 'forma_pagamento', 'usuario', 'data')
    search_fields = ('descricao', 'usuario__username', 'venda__id')
    readonly_fields = ('data',)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def has_delete_permission(self, request, obj=None):
        return False
