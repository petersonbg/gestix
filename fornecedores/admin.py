from django.contrib import admin

from .models import Fornecedor


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ('razao_social', 'nome_fantasia', 'cnpj', 'telefone', 'email', 'ativo')
    list_filter = ('ativo', 'estado')
    search_fields = ('razao_social', 'nome_fantasia', 'cnpj', 'email')
    readonly_fields = ('criado_em', 'atualizado_em')
