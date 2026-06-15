from django.contrib import admin

from .models import LogAtividade


@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'usuario', 'acao', 'modulo', 'ip_usuario', 'objeto_tipo', 'objeto_id')
    list_filter = ('acao', 'modulo', 'criado_em')
    search_fields = (
        'usuario__username', 'usuario__first_name', 'usuario__last_name',
        'acao', 'modulo', 'descricao', 'ip_usuario', 'objeto_tipo', 'objeto_id',
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
