from django.contrib import admin

from .models import LogAtividade


@admin.register(LogAtividade)
class LogAtividadeAdmin(admin.ModelAdmin):
    list_display = ('criado_em', 'usuario', 'acao', 'modulo', 'ip')
    list_filter = ('acao', 'modulo', 'criado_em')
    search_fields = ('usuario__username', 'usuario__first_name', 'usuario__last_name', 'acao', 'modulo', 'descricao', 'ip')
    readonly_fields = ('usuario', 'acao', 'modulo', 'descricao', 'ip', 'criado_em')
