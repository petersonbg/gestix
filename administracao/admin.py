from django.contrib import admin

<<<<<<< HEAD
from .models import BackupRegistro, CategoriaProduto, ConfiguracaoSistema, Empresa
=======
from .models import CategoriaProduto, ConfiguracaoSistema, Empresa
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


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


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Notificações', {'fields': ('notificacoes_aniversario_ativas', 'dias_antecedencia_aniversario')}),
        ('Sessão', {'fields': ('tempo_logout_inatividade',)}),
        ('Documentos e impressões', {'fields': ('mostrar_logo_impressoes', 'mostrar_assinatura_cliente', 'mensagem_rodape_documentos')}),
        ('Controle', {'fields': ('criado_em', 'atualizado_em')}),
    )
    readonly_fields = ('criado_em', 'atualizado_em')

    @staticmethod
    def usuario_administrador(request):
        return request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()

    def has_view_permission(self, request, obj=None):
        return self.usuario_administrador(request) or request.user.groups.filter(name='Gerente').exists()

    def has_add_permission(self, request):
        return self.usuario_administrador(request) and not ConfiguracaoSistema.objects.exists()

    def has_change_permission(self, request, obj=None):
        return self.usuario_administrador(request)

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CategoriaProduto)
class CategoriaProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'ativo', 'atualizado_em')
    list_filter = ('tipo', 'ativo')
    search_fields = ('nome', 'descricao')
    readonly_fields = ('criado_em', 'atualizado_em')

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(
            name__in=('Administrador', 'Gerente')
        ).exists()

    def has_add_permission(self, request):
        return request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_add_permission(request)
<<<<<<< HEAD


@admin.register(BackupRegistro)
class BackupRegistroAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'nome_arquivo', 'tamanho_arquivo', 'usuario', 'status', 'criado_em')
    list_filter = ('tipo', 'status', 'criado_em')
    search_fields = ('nome_arquivo', 'mensagem', 'usuario__username')
    readonly_fields = (
        'tipo', 'arquivo', 'nome_arquivo', 'tamanho_arquivo', 'usuario',
        'status', 'mensagem', 'criado_em',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser or request.user.groups.filter(name='Administrador').exists()
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
