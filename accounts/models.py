from django.conf import settings
from django.db import models


class PerfilUsuario(models.Model):
    class Perfil(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
        GERENTE = 'GERENTE', 'Gerente'
        VENDEDOR = 'VENDEDOR', 'Vendedor'
        ESTOQUISTA = 'ESTOQUISTA', 'Estoquista'

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil_usuario',
    )
    perfil = models.CharField(max_length=20, choices=Perfil.choices)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'perfil de usuário'
        verbose_name_plural = 'perfis de usuários'

    def __str__(self):
        return f'{self.usuario} - {self.get_perfil_display()}'


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
    acao = models.CharField(max_length=30, choices=Acao.choices)
    modulo = models.CharField(max_length=80)
    descricao = models.TextField(blank=True)
    objeto_tipo = models.CharField(max_length=120, blank=True)
    objeto_id = models.CharField(max_length=64, blank=True)
    ip_usuario = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        indexes = [
            models.Index(fields=['-criado_em']),
            models.Index(fields=['usuario']),
            models.Index(fields=['acao']),
            models.Index(fields=['modulo']),
        ]
        verbose_name = 'log de atividade'
        verbose_name_plural = 'logs de atividade'

    def __str__(self):
        usuario = self.usuario or 'Sistema'
        return f'{self.criado_em:%d/%m/%Y %H:%M} - {usuario} - {self.acao}'

    @property
    def ip(self):
        return self.ip_usuario
