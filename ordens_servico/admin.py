from django.contrib import admin

from .models import HistoricoOrdemServico, ItemProdutoOS, ItemServicoOS, OrdemServico, Servico


class ItemServicoInline(admin.TabularInline):
    model = ItemServicoOS
    extra = 0


class ItemProdutoInline(admin.TabularInline):
    model = ItemProdutoOS
    extra = 0


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ('numero', 'cliente', 'status', 'data_abertura', 'data_previsao', 'responsavel', 'total')
    list_filter = ('status', 'responsavel', 'data_abertura', 'data_previsao')
    search_fields = ('numero', 'cliente__nome', 'cliente__cpf_cnpj', 'descricao_problema')
    readonly_fields = ('numero', 'subtotal_servicos', 'subtotal_produtos', 'total', 'estoque_baixado')
    inlines = [ItemServicoInline, ItemProdutoInline]


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor_padrao', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao')


admin.site.register(ItemServicoOS)
admin.site.register(ItemProdutoOS)
admin.site.register(HistoricoOrdemServico)
