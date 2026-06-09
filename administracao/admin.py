from django.contrib import admin

from .models import ConfiguracaoSistema, Empresa


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
