from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse


class Produto(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField('descrição', blank=True)
    codigo_interno = models.CharField('código interno', max_length=50, unique=True)
    codigo_barras = models.CharField('código de barras', max_length=50, blank=True, null=True, unique=True)
    categoria = models.CharField(max_length=100, blank=True)
    unidade_medida = models.CharField('unidade de medida', max_length=20)
    preco_custo = models.DecimalField(
        'preço de custo',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    preco_venda = models.DecimalField(
        'preço de venda',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    estoque_minimo = models.PositiveIntegerField('estoque mínimo', default=0)
    estoque_atual = models.PositiveIntegerField('estoque atual', default=0)
    fornecedor = models.ForeignKey(
        'fornecedores.Fornecedor',
        on_delete=models.PROTECT,
        related_name='produtos',
        blank=True,
        null=True,
    )
    ncm = models.CharField('NCM', max_length=20, blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'produto'
        verbose_name_plural = 'produtos'

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if self.preco_custo is not None and self.preco_custo < Decimal('0.00'):
            raise ValidationError({'preco_custo': 'O preço de custo não pode ser negativo.'})
        if self.preco_venda is not None and self.preco_venda < Decimal('0.00'):
            raise ValidationError({'preco_venda': 'O preço de venda não pode ser negativo.'})
        if (
            self.preco_custo is not None
            and self.preco_venda is not None
            and self.preco_venda < self.preco_custo
        ):
            raise ValidationError({'preco_venda': 'O preço de venda deve ser maior ou igual ao preço de custo.'})

    def get_absolute_url(self):
        return reverse('produtos:detail', kwargs={'pk': self.pk})
