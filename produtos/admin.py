from django.contrib import admin

from .models import Produto


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'codigo_interno', 'codigo_barras', 'categoria', 'preco_venda', 'estoque_atual', 'fornecedor', 'ativo')
    list_filter = ('ativo', 'categoria', 'fornecedor')
    search_fields = ('nome', 'codigo_interno', 'codigo_barras', 'categoria')
    readonly_fields = ('codigo_interno', 'criado_em', 'atualizado_em')
