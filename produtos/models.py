import re
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse


class SequenciaCodigoProduto(models.Model):
    """Mantém a numeração de produtos mesmo após exclusões físicas."""

    chave = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    ultimo_numero = models.PositiveBigIntegerField(default=0)

    class Meta:
        verbose_name = 'sequência de código de produto'
        verbose_name_plural = 'sequências de códigos de produtos'


class Produto(models.Model):
    PREFIXO_CODIGO_INTERNO = 'PROD'
    DIGITOS_CODIGO_INTERNO = 6
    PADRAO_CODIGO_INTERNO = re.compile(r'^PROD(?P<numero>\d+)$')

    nome = models.CharField(max_length=150)
    descricao = models.TextField('descrição', blank=True)
    codigo_interno = models.CharField('código interno', max_length=50, unique=True, blank=True)
    codigo_barras = models.CharField('código de barras', max_length=50, blank=True, null=True, unique=True)
    categoria = models.ForeignKey(
        'administracao.CategoriaProduto',
        on_delete=models.PROTECT,
        related_name='produtos',
        blank=True,
        null=True,
    )
    chassi = models.CharField(
        'Chassi',
        max_length=50,
        blank=True,
        null=True,
        help_text='Disponível apenas para produtos da categoria Veículos.',
    )
    unidade_medida = models.CharField('unidade de medida', max_length=20)
    preco_custo = models.DecimalField(
        'preço de custo',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        null=True,
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

    @classmethod
    def _maior_numero_existente(cls):
        maior_numero = 0
        for codigo in cls.objects.filter(
            codigo_interno__startswith=cls.PREFIXO_CODIGO_INTERNO
        ).values_list('codigo_interno', flat=True):
            correspondencia = cls.PADRAO_CODIGO_INTERNO.fullmatch(codigo or '')
            if correspondencia:
                maior_numero = max(maior_numero, int(correspondencia.group('numero')))
        return maior_numero

    @classmethod
    def gerar_codigo_interno(cls):
        """Reserva e retorna o próximo código, sem reutilizar números excluídos."""
        with transaction.atomic():
            sequencia, criada = (
                SequenciaCodigoProduto.objects.select_for_update().get_or_create(chave=1)
            )
            if criada:
                sequencia.ultimo_numero = cls._maior_numero_existente()
            sequencia.ultimo_numero += 1
            sequencia.save(update_fields=['ultimo_numero'])
            return (
                f'{cls.PREFIXO_CODIGO_INTERNO}'
                f'{sequencia.ultimo_numero:0{cls.DIGITOS_CODIGO_INTERNO}d}'
            )

    @classmethod
    def _sincronizar_sequencia(cls, codigo):
        correspondencia = cls.PADRAO_CODIGO_INTERNO.fullmatch(codigo or '')
        if not correspondencia:
            return

        numero = int(correspondencia.group('numero'))
        with transaction.atomic():
            sequencia, _ = (
                SequenciaCodigoProduto.objects.select_for_update().get_or_create(chave=1)
            )
            if numero > sequencia.ultimo_numero:
                sequencia.ultimo_numero = numero
                sequencia.save(update_fields=['ultimo_numero'])

    def save(self, *args, **kwargs):
        limpar_chassi = not self.categoria_id or self.categoria.tipo != 'VEICULOS'
        if limpar_chassi:
            self.chassi = None
            if kwargs.get('update_fields') is not None:
                kwargs['update_fields'] = set(kwargs['update_fields']) | {'chassi'}

        codigo_informado = (self.codigo_interno or '').strip()
        codigo_gerado = not codigo_informado
        if codigo_gerado:
            self.codigo_interno = self.gerar_codigo_interno()
        else:
            self.codigo_interno = codigo_informado
            self._sincronizar_sequencia(self.codigo_interno)

        if codigo_gerado and kwargs.get('update_fields') is not None:
            kwargs['update_fields'] = set(kwargs['update_fields']) | {'codigo_interno'}
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.categoria_id and self.categoria.tipo != 'VEICULOS':
            self.chassi = None
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
