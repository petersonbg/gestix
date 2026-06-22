from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

CENTAVO = Decimal('0.01')


class CategoriaDespesa(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    descricao = models.TextField('descrição', blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'categoria de despesa'
        verbose_name_plural = 'categorias de despesa'

    def __str__(self):
        return self.nome


class ContaPagar(models.Model):
    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        PAGA = 'PAGA', 'Paga'
        ATRASADA = 'ATRASADA', 'Atrasada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class FormaPagamento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'PIX'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de débito'
        BOLETO = 'BOLETO', 'Boleto'
        TRANSFERENCIA = 'TRANSFERENCIA', 'Transferência'
        OUTROS = 'OUTROS', 'Outros'

    descricao = models.CharField('descrição', max_length=180)
    fornecedor = models.ForeignKey(
        'fornecedores.Fornecedor',
        on_delete=models.PROTECT,
        related_name='contas_pagar',
        blank=True,
        null=True,
    )
    categoria = models.ForeignKey(CategoriaDespesa, on_delete=models.PROTECT, related_name='contas_pagar')
    data_emissao = models.DateField('data de emissão', default=timezone.localdate)
    data_vencimento = models.DateField('data de vencimento')
    data_pagamento = models.DateField('data de pagamento', blank=True, null=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    valor_pago = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    observacao = models.TextField('observação', blank=True)
    usuario_criacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contas_pagar_criadas',
        blank=True,
        null=True,
    )
    usuario_pagamento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='contas_pagar_pagas',
        blank=True,
        null=True,
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data_vencimento', 'descricao']
        indexes = [
            models.Index(fields=['status', 'data_vencimento'], name='pagar_status_venc_idx'),
            models.Index(fields=['status', 'data_pagamento'], name='pagar_status_pag_idx'),
        ]
        verbose_name = 'conta a pagar'
        verbose_name_plural = 'contas a pagar'

    def __str__(self):
        return self.descricao

    @property
    def saldo(self):
        return max((self.valor or Decimal('0.00')) - (self.valor_pago or Decimal('0.00')), Decimal('0.00'))

    @property
    def status_exibicao(self):
        if self.status == self.Status.ABERTA and self.data_vencimento < timezone.localdate():
            return self.Status.ATRASADA
        return self.status

    @property
    def status_exibicao_label(self):
        return self.Status(self.status_exibicao).label

    @property
    def dias_atraso(self):
        if self.status_exibicao != self.Status.ATRASADA:
            return 0
        return max((timezone.localdate() - self.data_vencimento).days, 0)

    def clean(self):
        super().clean()
        if self.valor is not None and self.valor <= 0:
            raise ValidationError({'valor': 'O valor deve ser maior que zero.'})
        if self.valor_pago is not None and self.valor_pago < 0:
            raise ValidationError({'valor_pago': 'O valor pago não pode ser negativo.'})
        if self.valor is not None and self.valor_pago is not None and self.valor_pago > self.valor:
            raise ValidationError({'valor_pago': 'O valor pago não pode ser maior que o valor da conta.'})
        if self.status != self.Status.PAGA and self.data_pagamento:
            raise ValidationError({'data_pagamento': 'A data de pagamento só deve ser preenchida quando a conta estiver paga.'})
        if self.status == self.Status.PAGA and not self.data_pagamento:
            raise ValidationError({'data_pagamento': 'Informe a data de pagamento da conta paga.'})

    def pagar(self, *, usuario, valor_pago, forma_pagamento, data_pagamento=None, observacao=''):
        if self.status == self.Status.CANCELADA:
            raise ValidationError('Não é possível pagar conta cancelada.')
        if self.status == self.Status.PAGA:
            raise ValidationError('Esta conta já está paga.')
        if valor_pago is None or valor_pago <= 0:
            raise ValidationError({'valor_pago': 'Informe um valor pago maior que zero.'})
        if valor_pago > self.saldo:
            raise ValidationError({'valor_pago': 'O valor pago não pode ser maior que o valor em aberto.'})

        from caixa.models import Caixa, MovimentacaoCaixa

        with transaction.atomic():
            conta = ContaPagar.objects.select_for_update().get(pk=self.pk)
            if conta.status == ContaPagar.Status.CANCELADA:
                raise ValidationError('Não é possível pagar conta cancelada.')
            if conta.status == ContaPagar.Status.PAGA:
                raise ValidationError('Esta conta já está paga.')
            if valor_pago > conta.saldo:
                raise ValidationError({'valor_pago': 'O valor pago não pode ser maior que o valor em aberto.'})

            caixa = None
            if forma_pagamento == ContaPagar.FormaPagamento.DINHEIRO:
                caixa = Caixa.objects.select_for_update().filter(usuario_abertura=usuario, status=Caixa.Status.ABERTO).first()
                if not caixa:
                    raise ValidationError('É necessário abrir o caixa antes de pagar contas em dinheiro.')

            conta.valor_pago = (conta.valor_pago + valor_pago).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            conta.forma_pagamento = forma_pagamento
            conta.observacao = observacao or conta.observacao
            conta.usuario_pagamento = usuario
            if conta.valor_pago >= conta.valor:
                conta.valor_pago = conta.valor
                conta.status = ContaPagar.Status.PAGA
                conta.data_pagamento = data_pagamento or timezone.localdate()
            conta.full_clean()
            conta.save(update_fields=[
                'valor_pago',
                'forma_pagamento',
                'observacao',
                'usuario_pagamento',
                'status',
                'data_pagamento',
                'atualizado_em',
            ])

            if caixa:
                MovimentacaoCaixa.registrar(
                    caixa=caixa,
                    tipo=MovimentacaoCaixa.Tipo.SAIDA,
                    descricao=f'Pagamento de conta: {conta.descricao}',
                    valor=valor_pago,
                    forma_pagamento=MovimentacaoCaixa.FormaPagamento.DINHEIRO,
                    usuario=usuario,
                    observacao=observacao,
                )
            self.refresh_from_db()
            return conta

    def cancelar(self, observacao=''):
        if self.status == self.Status.PAGA:
            raise ValidationError('Conta paga não pode ser cancelada diretamente sem estorno.')
        if self.status == self.Status.CANCELADA:
            return
        self.status = self.Status.CANCELADA
        self.observacao = observacao or self.observacao
        self.save(update_fields=['status', 'observacao', 'atualizado_em'])

    def get_absolute_url(self):
        return reverse('contas_pagar:detail', kwargs={'pk': self.pk})
