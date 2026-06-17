from django.contrib import admin

<<<<<<< HEAD
from .models import LogAtividade, PerfilUsuario
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
=======
from .models import LogAtividade
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
<<<<<<< HEAD
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
=======
    list_display = ('criado_em', 'usuario', 'acao', 'modulo', 'ip')
    list_filter = ('acao', 'modulo', 'criado_em')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'acao', 'modulo', 'descricao', 'ip')
    readonly_fields = ('usuario', 'acao', 'modulo', 'descricao', 'ip', 'criado_em')
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
