from django.contrib import admin

from .models import ConfiguracaoSistema


@admin.register(ConfiguracaoSistema)
class ConfiguracaoSistemaAdmin(admin.ModelAdmin):
    list_display = ('notificacoes_aniversario_ativas', 'dias_antecedencia_aniversario', 'atualizado_em')
    readonly_fields = ('atualizado_em',)

    def has_add_permission(self, request):
        return not ConfiguracaoSistema.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
