from django.contrib import admin

from .models import ContaReceber


@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = (
        'cliente',
        'origem',
        'parcela',
        'data_vencimento',
        'valor',
        'valor_pago',
        'status',
    )
    list_filter = ('status', 'forma_recebimento', 'data_vencimento', 'cliente')
    search_fields = ('cliente__nome', 'cliente__cpf_cnpj', 'venda__id', 'ordem_servico__numero')
    date_hierarchy = 'data_vencimento'
    readonly_fields = ('criado_em', 'atualizado_em')

    @admin.display(description='origem')
    def origem(self, obj):
        return obj.referencia

    def parcela(self, obj):
        return f'{obj.numero_parcela}/{obj.total_parcelas}'

    parcela.short_description = 'parcela'
