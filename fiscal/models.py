from django.db import models
from django.urls import reverse

from fornecedores.models import Fornecedor
from produtos.models import Produto


class NotaFiscalEntrada(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        CONFIRMADA = 'CONFIRMADA', 'Confirmada'

    chave_acesso = models.CharField('chave de acesso', max_length=44, unique=True)
    numero = models.CharField('número', max_length=20)
    serie = models.CharField('série', max_length=10)
    data_emissao = models.DateTimeField('data de emissão')
    emitente_cnpj = models.CharField('CNPJ do emitente', max_length=18)
    emitente_razao_social = models.CharField('razão social do emitente', max_length=150)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.PROTECT, related_name='notas_fiscais_entrada')
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_emissao']
        verbose_name = 'nota fiscal de entrada'
        verbose_name_plural = 'notas fiscais de entrada'

    def __str__(self):
        return f'NF-e {self.numero}/{self.serie} - {self.emitente_razao_social}'

    def get_absolute_url(self):
        return reverse('fiscal:detail', kwargs={'pk': self.pk})


class ItemNotaFiscalEntrada(models.Model):
    nota = models.ForeignKey(NotaFiscalEntrada, on_delete=models.CASCADE, related_name='itens')
    numero_item = models.PositiveIntegerField()
    codigo_produto = models.CharField('código do produto no XML', max_length=60, blank=True)
    descricao = models.CharField('descrição', max_length=255)
    ncm = models.CharField('NCM', max_length=20, blank=True)
    unidade_medida = models.CharField('unidade de medida', max_length=20, blank=True)
    quantidade = models.PositiveIntegerField()
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_nfe_entrada', blank=True, null=True)

    class Meta:
        ordering = ['numero_item']
        verbose_name = 'item de nota fiscal de entrada'
        verbose_name_plural = 'itens de nota fiscal de entrada'
        unique_together = ('nota', 'numero_item')

    def __str__(self):
        return f'{self.numero_item} - {self.descricao}'
