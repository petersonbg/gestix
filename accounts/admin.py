from django.contrib import admin

from .models import LogAtividade, PerfilUsuario, SessaoUsuario
from .permissions import usuario_eh_admin


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'perfil', 'ativo', 'criado_em', 'atualizado_em')
    list_filter = ('perfil', 'ativo')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'usuario__email')
    readonly_fields = ('criado_em', 'atualizado_em')

    @staticmethod
    def pode_gerenciar(request):
        return request.user.is_superuser or usuario_eh_admin(request.user)

    def has_view_permission(self, request, obj=None):
        return self.pode_gerenciar(request)

    def has_add_permission(self, request):
        return self.pode_gerenciar(request)

    def has_change_permission(self, request, obj=None):
        return self.pode_gerenciar(request)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'usuario', 'acao', 'modulo', 'objeto_tipo', 'objeto_id', 'ip_usuario')
    list_filter = ('acao', 'modulo', 'criado_em')
    search_fields = (
        'usuario__username', 'usuario__first_name', 'usuario__last_name',
        'acao', 'modulo', 'descricao', 'objeto_tipo', 'objeto_id', 'ip_usuario',
    )
    readonly_fields = (
        'usuario', 'acao', 'modulo', 'descricao', 'objeto_tipo', 'objeto_id',
        'ip_usuario', 'user_agent', 'criado_em',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SessaoUsuario)
class SessaoUsuarioAdmin(admin.ModelAdmin):
    list_display = (
        'usuario', 'session_key', 'ip_usuario', 'user_agent_resumido',
        'data_login', 'ultimo_acesso', 'ativa',
    )
    list_filter = ('ativa', 'data_login', 'ultimo_acesso')
    search_fields = (
        'usuario__username', 'usuario__first_name', 'usuario__last_name',
        'session_key', 'ip_usuario', 'user_agent',
    )
    readonly_fields = (
        'usuario', 'session_key', 'ip_usuario', 'user_agent',
        'data_login', 'ultimo_acesso', 'ativa',
    )

    @admin.display(description='User agent')
    def user_agent_resumido(self, obj):
        return obj.user_agent[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
