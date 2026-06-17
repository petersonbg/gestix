from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone


class Caixa(models.Model):
    class Status(models.TextChoices):
        ABERTO = 'ABERTO', 'Aberto'
        FECHADO = 'FECHADO', 'Fechado'

    usuario_abertura = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='caixas_abertos',
    )
    data_abertura = models.DateTimeField(auto_now_add=True)
    valor_inicial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.ABERTO)
    observacao_abertura = models.TextField('observação de abertura', blank=True)
    data_fechamento = models.DateTimeField(blank=True, null=True)
    usuario_fechamento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='caixas_fechados',
        blank=True,
        null=True,
    )
    valor_fechamento_informado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
        blank=True,
        null=True,
    )
    valor_fechamento_calculado = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    diferenca = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    observacao_fechamento = models.TextField('observação de fechamento', blank=True)

    class Meta:
        ordering = ['-data_abertura']
        verbose_name = 'caixa'
        verbose_name_plural = 'caixas'
        constraints = [
            models.UniqueConstraint(
                fields=['usuario_abertura'],
                condition=Q(status='ABERTO'),
                name='unique_caixa_aberto_por_usuario',
            )
        ]

    def __str__(self):
        return f'Caixa #{self.pk or "novo"} - {self.usuario_abertura} ({self.get_status_display()})'

    def clean(self):
        super().clean()
        if self.valor_inicial is not None and self.valor_inicial < 0:
            raise ValidationError({'valor_inicial': 'O valor inicial não pode ser negativo.'})
        if self.status == self.Status.ABERTO and self.usuario_abertura_id:
            aberto = Caixa.objects.filter(usuario_abertura=self.usuario_abertura, status=self.Status.ABERTO)
            if self.pk:
                aberto = aberto.exclude(pk=self.pk)
            if aberto.exists():
                raise ValidationError('Cada usuário só pode ter um caixa aberto por vez.')

    @classmethod
    def caixa_aberto_do_usuario(cls, usuario):
        return cls.objects.filter(usuario_abertura=usuario, status=cls.Status.ABERTO).first()

    @classmethod
    def abrir(cls, *, usuario, valor_inicial, observacao_abertura=''):
        if valor_inicial is None or valor_inicial < 0:
            raise ValidationError({'valor_inicial': 'O valor inicial não pode ser negativo.'})
        with transaction.atomic():
            if cls.objects.select_for_update().filter(usuario_abertura=usuario, status=cls.Status.ABERTO).exists():
                raise ValidationError('Cada usuário só pode ter um caixa aberto por vez.')
            caixa = cls.objects.create(
                usuario_abertura=usuario,
                valor_inicial=valor_inicial,
                observacao_abertura=observacao_abertura,
            )
            return caixa

    def totais_por_tipo(self):
        agregados = self.movimentacoes.values('tipo').annotate(total=Sum('valor'))
        totais = {tipo: Decimal('0.00') for tipo, _ in MovimentacaoCaixa.Tipo.choices}
        for item in agregados:
            totais[item['tipo']] = item['total'] or Decimal('0.00')
        return totais

    def saldo_calculado(self):
        totais = self.totais_por_tipo()
        entradas = totais[MovimentacaoCaixa.Tipo.ENTRADA] + totais[MovimentacaoCaixa.Tipo.SUPRIMENTO] + totais[MovimentacaoCaixa.Tipo.VENDA]
        saidas = totais[MovimentacaoCaixa.Tipo.SAIDA] + totais[MovimentacaoCaixa.Tipo.SANGRIA] + totais[MovimentacaoCaixa.Tipo.CANCELAMENTO]
        return self.valor_inicial + entradas - saidas

    def fechar(self, *, usuario, valor_fechamento_informado, observacao_fechamento=''):
        if valor_fechamento_informado is None or valor_fechamento_informado < 0:
            raise ValidationError({'valor_fechamento_informado': 'O valor contado não pode ser negativo.'})
        if self.status != self.Status.ABERTO:
            raise ValidationError('Não é possível fechar um caixa que já está fechado.')
        with transaction.atomic():
            caixa = Caixa.objects.select_for_update().get(pk=self.pk)
            if caixa.status != self.Status.ABERTO:
                raise ValidationError('Não é possível fechar um caixa que já está fechado.')
            calculado = caixa.saldo_calculado()
            caixa.valor_fechamento_calculado = calculado
            caixa.valor_fechamento_informado = valor_fechamento_informado
            caixa.diferenca = valor_fechamento_informado - calculado
            caixa.observacao_fechamento = observacao_fechamento
            caixa.usuario_fechamento = usuario
            caixa.data_fechamento = timezone.now()
            caixa.status = self.Status.FECHADO
            caixa.save(update_fields=[
                'valor_fechamento_calculado',
                'valor_fechamento_informado',
                'diferenca',
                'observacao_fechamento',
                'usuario_fechamento',
                'data_fechamento',
                'status',
            ])
            self.status = caixa.status
            self.valor_fechamento_calculado = caixa.valor_fechamento_calculado
            self.valor_fechamento_informado = caixa.valor_fechamento_informado
            self.diferenca = caixa.diferenca
            from accounts.utils import registrar_log

            registrar_log(
                usuario,
                'FECHAMENTO_CAIXA',
                'caixa',
                f'Caixa #{caixa.pk} fechado.',
                objeto=caixa,
            )
            return caixa

    def get_absolute_url(self):
        return reverse('caixa:atual')


class MovimentacaoCaixa(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'
        SANGRIA = 'SANGRIA', 'Sangria'
        SUPRIMENTO = 'SUPRIMENTO', 'Suprimento'
        VENDA = 'VENDA', 'Venda'
        CANCELAMENTO = 'CANCELAMENTO', 'Cancelamento'

    class FormaPagamento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'PIX'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de débito'
        BOLETO = 'BOLETO', 'Boleto'
        OUTROS = 'OUTROS', 'Outros'

    caixa = models.ForeignKey(Caixa, on_delete=models.PROTECT, related_name='movimentacoes')
    tipo = models.CharField(max_length=12, choices=Tipo.choices)
    descricao = models.CharField(max_length=150)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, default=FormaPagamento.DINHEIRO)
    venda = models.ForeignKey('vendas.Venda', on_delete=models.PROTECT, related_name='movimentacoes_caixa', blank=True, null=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='movimentacoes_caixa')
    data = models.DateTimeField(auto_now_add=True)
    observacao = models.TextField('observação', blank=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'movimentação de caixa'
        verbose_name_plural = 'movimentações de caixa'

    def __str__(self):
        return f'{self.get_tipo_display()} - R$ {self.valor}'

    def clean(self):
        super().clean()
        if self.valor is not None and self.valor < 0:
            raise ValidationError({'valor': 'O valor não pode ser negativo.'})
        if self.caixa_id and self.caixa.status != Caixa.Status.ABERTO:
            raise ValidationError('Movimentações só podem ser lançadas em caixa aberto.')

    @classmethod
    def registrar(cls, *, caixa, tipo, descricao, valor, usuario, forma_pagamento=None, venda=None, observacao=''):
        if caixa.status != Caixa.Status.ABERTO:
            raise ValidationError('Movimentações só podem ser lançadas em caixa aberto.')
        if valor is None or valor < 0:
            raise ValidationError({'valor': 'O valor não pode ser negativo.'})
        movimentacao = cls(
            caixa=caixa,
            tipo=tipo,
            descricao=descricao,
            valor=valor,
            forma_pagamento=forma_pagamento or cls.FormaPagamento.DINHEIRO,
            venda=venda,
            usuario=usuario,
            observacao=observacao,
        )
        movimentacao.full_clean()
        movimentacao.save()
        return movimentacao

