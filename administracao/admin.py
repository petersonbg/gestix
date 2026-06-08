from django.contrib import admin

from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Dados gerais', {'fields': ('razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual', 'inscricao_municipal')}),
        ('Endereço', {'fields': ('cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado')}),
        ('Contato', {'fields': ('telefone', 'celular', 'whatsapp', 'email', 'site')}),
        ('Identidade visual', {'fields': ('logo', 'logo_impressao', 'cor_primaria', 'cor_secundaria')}),
        ('Outros', {'fields': ('responsavel', 'observacoes', 'criado_em', 'atualizado_em')}),
    )
    readonly_fields = ('criado_em', 'atualizado_em')

    def has_add_permission(self, request):
        return not Empresa.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
