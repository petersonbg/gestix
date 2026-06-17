from django.contrib import admin

from .models import CategoriaDespesa, ContaPagar


@admin.register(CategoriaDespesa)
class CategoriaDespesaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativo', 'criado_em')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao')


@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'fornecedor', 'categoria', 'data_vencimento', 'valor', 'valor_pago', 'status')
    list_filter = ('status', 'categoria', 'fornecedor', 'data_vencimento')
    search_fields = ('descricao', 'fornecedor__razao_social', 'fornecedor__nome_fantasia')
    date_hierarchy = 'data_vencimento'
    readonly_fields = ('criado_em', 'atualizado_em')
