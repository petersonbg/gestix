from django.contrib import admin

from .models import DadosEmpresa


@admin.register(DadosEmpresa)
class DadosEmpresaAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Identificação', {'fields': ('razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual')}),
        ('Contato e endereço', {'fields': ('telefone', 'email', 'endereco', 'cidade', 'estado', 'cep')}),
        ('Controle', {'fields': ('atualizado_em',)}),
    )
    readonly_fields = ('atualizado_em',)

    def has_add_permission(self, request):
        return not DadosEmpresa.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
