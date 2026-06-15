from django.conf import settings
from django.db import models


class LogAtividade(models.Model):
    class Acao(models.TextChoices):
        LOGIN = 'LOGIN', 'Login'
        LOGOUT = 'LOGOUT', 'Logout'
        CRIACAO = 'CRIACAO', 'Criação'
        EDICAO = 'EDICAO', 'Edição'
        EXCLUSAO = 'EXCLUSAO', 'Exclusão'
        CANCELAMENTO = 'CANCELAMENTO', 'Cancelamento'
        FINALIZACAO = 'FINALIZACAO', 'Finalização'
        IMPRESSAO = 'IMPRESSAO', 'Impressão'
        BACKUP = 'BACKUP', 'Backup'
        RESTAURACAO = 'RESTAURACAO', 'Restauração'
        PAGAMENTO = 'PAGAMENTO', 'Pagamento'
        RECEBIMENTO = 'RECEBIMENTO', 'Recebimento'
        MOVIMENTACAO_ESTOQUE = 'MOVIMENTACAO_ESTOQUE', 'Movimentação de estoque'
        ABERTURA_CAIXA = 'ABERTURA_CAIXA', 'Abertura de caixa'
        FECHAMENTO_CAIXA = 'FECHAMENTO_CAIXA', 'Fechamento de caixa'
        ERRO = 'ERRO', 'Erro'

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='logs_atividade',
        blank=True,
        null=True,
    )
    acao = models.CharField(max_length=30, choices=Acao.choices, db_index=True)
    modulo = models.CharField(max_length=80, db_index=True)
    descricao = models.TextField(blank=True)
    objeto_tipo = models.CharField(max_length=150, blank=True)
    objeto_id = models.CharField(max_length=100, blank=True)
    ip_usuario = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'log de atividade'
        verbose_name_plural = 'logs de atividade'

    def __str__(self):
        usuario = self.usuario or 'Sistema'
        return f'{self.criado_em:%d/%m/%Y %H:%M} - {usuario} - {self.acao}'

    @property
    def ip(self):
        return self.ip_usuario
