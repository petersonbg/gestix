from django.db import models
from django.core.validators import MinValueValidator


class ConfiguracaoSistema(models.Model):
    notificacoes_aniversario_ativas = models.BooleanField(
        'ativar notificações de aniversário',
        default=True,
    )
    dias_antecedencia_aniversario = models.PositiveIntegerField(
        'dias de antecedência para aviso',
        default=0,
        validators=[MinValueValidator(0)],
        help_text='0 = avisar somente no dia; 7 = avisar com uma semana de antecedência.',
    )
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuração do sistema'
        verbose_name_plural = 'configurações do sistema'

    def __str__(self):
        return 'Configurações do Sistema'

    @classmethod
    def get_solo(cls):
        configuracao, _ = cls.objects.get_or_create(pk=1)
        return configuracao
