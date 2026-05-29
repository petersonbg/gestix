from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from clientes.models import Cliente
from produtos.models import Produto
from vendas.models import ItemVenda, Venda


class Orcamento(models.Model):
    class Status(models.TextChoices):
        ABERTO = 'ABERTO', 'Aberto'
        APROVADO = 'APROVADO', 'Aprovado'
        REJEITADO = 'REJEITADO', 'Rejeitado'
        CONVERTIDO = 'CONVERTIDO', 'Convertido'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='orcamentos')
    data = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ABERTO)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='orcamentos',
        blank=True,
        null=True,
    )
    venda = models.OneToOneField(
        Venda,
        on_delete=models.SET_NULL,
        related_name='orcamento_origem',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-data']
        verbose_name = 'orçamento'
        verbose_name_plural = 'orçamentos'

    def __str__(self):
        return f'Orçamento #{self.pk or "novo"} - {self.cliente}'

    def clean(self):
        super().clean()
        if self.desconto < 0:
            raise ValidationError({'desconto': 'O desconto não pode ser negativo.'})
        if self.subtotal and self.desconto > self.subtotal:
            raise ValidationError({'desconto': 'O desconto não pode ser maior que o subtotal.'})

    def recalcular_totais(self, save=True):
        subtotal = sum((item.total_item for item in self.itens.all()), Decimal('0.00'))
        self.subtotal = subtotal
        self.total = max(subtotal - self.desconto, Decimal('0.00'))
        if save:
            self.save(update_fields=['subtotal', 'total'])
        return self.total

    def converter_em_venda(self, usuario=None):
        if self.status == self.Status.CONVERTIDO and self.venda_id:
            return self.venda
        if self.status == self.Status.REJEITADO:
            raise ValidationError('Orçamento rejeitado não pode ser convertido em venda.')

        with transaction.atomic():
            orcamento = Orcamento.objects.select_for_update().get(pk=self.pk)
            if orcamento.status == self.Status.CONVERTIDO and orcamento.venda_id:
                return orcamento.venda
            if orcamento.status == self.Status.REJEITADO:
                raise ValidationError('Orçamento rejeitado não pode ser convertido em venda.')

            itens = list(orcamento.itens.select_related('produto'))
            if not itens:
                raise ValidationError('Inclua ao menos um item para converter o orçamento.')

            orcamento.recalcular_totais(save=False)
            if orcamento.desconto > orcamento.subtotal:
                raise ValidationError('O desconto não pode ser maior que o subtotal.')

            venda = Venda.objects.create(
                cliente=orcamento.cliente,
                desconto=orcamento.desconto,
                status=Venda.Status.RASCUNHO,
                usuario=usuario or orcamento.usuario,
            )
            for item in itens:
                ItemVenda.objects.create(
                    venda=venda,
                    produto=item.produto,
                    quantidade=item.quantidade,
                    valor_unitario=item.valor_unitario,
                )
            venda.recalcular_totais()
            venda.finalizar(usuario=usuario or orcamento.usuario)

            orcamento.status = self.Status.CONVERTIDO
            orcamento.venda = venda
            orcamento.subtotal = venda.subtotal
            orcamento.total = venda.total
            orcamento.save(update_fields=['status', 'venda', 'subtotal', 'total'])

            self.status = orcamento.status
            self.venda = venda
            self.subtotal = orcamento.subtotal
            self.total = orcamento.total
            return venda

    def get_absolute_url(self):
        return reverse('orcamentos:detail', kwargs={'pk': self.pk})


class ItemOrcamento(models.Model):
    orcamento = models.ForeignKey(Orcamento, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_orcamento')
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    valor_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total_item = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'item de orçamento'
        verbose_name_plural = 'itens de orçamento'

    def __str__(self):
        return f'{self.produto} x {self.quantidade}'

    def clean(self):
        super().clean()
        if self.quantidade <= 0:
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero.'})
        if self.valor_unitario < 0:
            raise ValidationError({'valor_unitario': 'O valor unitário não pode ser negativo.'})

    def save(self, *args, **kwargs):
        self.total_item = self.quantidade * self.valor_unitario
        super().save(*args, **kwargs)
