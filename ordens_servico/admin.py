from django.contrib import admin

from .models import HistoricoOrdemServico, ItemProdutoOS, ItemServicoOS, OrdemServico, Servico


class ItemOSInlineProtegidoMixin:
    def has_add_permission(self, request, obj=None):
        if obj and obj.finalizada:
            return False
        return super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.finalizada:
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.finalizada:
            return False
        return super().has_delete_permission(request, obj)


class ItemServicoInline(ItemOSInlineProtegidoMixin, admin.TabularInline):
    model = ItemServicoOS
    extra = 0


class ItemProdutoInline(ItemOSInlineProtegidoMixin, admin.TabularInline):
    model = ItemProdutoOS
    extra = 0


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = (
        'numero', 'cliente', 'status', 'data_abertura', 'data_finalizacao',
        'responsavel_nome', 'executor_nome', 'valor_deslocamento', 'total',
    )
    list_filter = ('status', 'responsavel', 'responsavel_execucao', 'data_abertura', 'data_finalizacao')
    search_fields = ('numero', 'cliente__nome', 'cliente__cpf_cnpj', 'descricao_problema')
    readonly_fields = ('numero', 'subtotal_servicos', 'subtotal_produtos', 'total', 'estoque_baixado')
    inlines = [ItemServicoInline, ItemProdutoInline]

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.finalizada:
            return tuple(field.name for field in self.model._meta.fields)
        return super().get_readonly_fields(request, obj)

    def has_change_permission(self, request, obj=None):
        if obj and obj.finalizada and request.method == 'POST':
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.finalizada:
            return False
        return super().has_delete_permission(request, obj)

    @admin.display(description='Responsável', ordering='responsavel__first_name')
    def responsavel_nome(self, obj):
        return obj.nome_responsavel

    @admin.display(description='Responsável pela execução', ordering='responsavel_execucao__first_name')
    def executor_nome(self, obj):
        return obj.nome_responsavel_execucao


@admin.register(Servico)
class ServicoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'valor_padrao', 'ativo', 'atualizado_em')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao')
    readonly_fields = ('criado_em', 'atualizado_em')

    @staticmethod
    def usuario_administrador(request):
        return request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()

    def has_view_permission(self, request, obj=None):
        return self.usuario_administrador(request) or request.user.groups.filter(name='Gerente').exists()

    def has_add_permission(self, request):
        return self.usuario_administrador(request)

    def has_change_permission(self, request, obj=None):
        return self.usuario_administrador(request)

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(ItemServicoOS)
admin.site.register(ItemProdutoOS)
admin.site.register(HistoricoOrdemServico)

