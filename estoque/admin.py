from django.contrib import admin

from .models import MovimentacaoEstoque


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ('produto', 'tipo_movimentacao', 'quantidade', 'origem', 'usuario', 'data')
    list_filter = ('tipo_movimentacao', 'data')
    search_fields = ('produto__nome', 'produto__codigo_interno', 'origem', 'observacao')
    readonly_fields = ('data',)
