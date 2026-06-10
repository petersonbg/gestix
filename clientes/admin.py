from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo_pessoa', 'cpf_cnpj', 'inscricao_estadual', 'data_nascimento', 'telefone', 'email', 'ativo')
    list_filter = ('tipo_pessoa', 'ativo', 'estado')
    search_fields = ('nome', 'cpf_cnpj', 'inscricao_estadual', 'telefone', 'email')
    readonly_fields = ('criado_em', 'atualizado_em')
