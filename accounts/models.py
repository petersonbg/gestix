from django.conf import settings
from django.db import models


class LogAtividade(models.Model):
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='logs_atividade',
        blank=True,
        null=True,
    )
    acao = models.CharField(max_length=80)
    modulo = models.CharField(max_length=80)
    descricao = models.TextField(blank=True)
    ip = models.GenericIPAddressField(blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'log de atividade'
        verbose_name_plural = 'logs de atividade'

    def __str__(self):
        usuario = self.usuario or 'Sistema'
        return f'{self.criado_em:%d/%m/%Y %H:%M} - {usuario} - {self.acao}'
