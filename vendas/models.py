from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse

from clientes.models import Cliente
from estoque.models import MovimentacaoEstoque
from produtos.models import Produto


class Venda(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = 'RASCUNHO', 'Rascunho'
        FINALIZADA = 'FINALIZADA', 'Finalizada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class FormaPagamento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'PIX'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de débito'
        BOLETO = 'BOLETO', 'Boleto'
        OUTROS = 'OUTROS', 'Outros'

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='vendas')
    data = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    desconto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RASCUNHO)
    forma_pagamento = models.CharField(
        'forma de pagamento',
        max_length=20,
        choices=FormaPagamento.choices,
        default=FormaPagamento.DINHEIRO,
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='vendas',
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ['-data']
        verbose_name = 'venda'
        verbose_name_plural = 'vendas'

    def __str__(self):
        return f'Venda #{self.pk or "nova"} - {self.cliente}'

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

    def finalizar(self, usuario=None):
        if self.status == self.Status.FINALIZADA:
            return
        if self.status == self.Status.CANCELADA:
            raise ValidationError('Venda cancelada não pode ser finalizada.')

        with transaction.atomic():
            venda = Venda.objects.select_for_update().get(pk=self.pk)
            if venda.status == self.Status.FINALIZADA:
                return
            if venda.status == self.Status.CANCELADA:
                raise ValidationError('Venda cancelada não pode ser finalizada.')

            itens = list(venda.itens.select_related('produto'))
            if not itens:
                raise ValidationError('Inclua ao menos um item para finalizar a venda.')

            from caixa.models import Caixa, MovimentacaoCaixa

            caixa = Caixa.objects.select_for_update().filter(
                usuario_abertura=usuario or venda.usuario,
                status=Caixa.Status.ABERTO,
            ).first()
            if not caixa:
                raise ValidationError('É necessário abrir o caixa antes de finalizar vendas.')

            produto_ids = [item.produto_id for item in itens]
            produtos = Produto.objects.select_for_update().filter(pk__in=produto_ids)
            saldos = {produto.pk: produto.estoque_atual for produto in produtos}

            quantidades_por_produto = {}
            produto_por_id = {}
            for item in itens:
                quantidades_por_produto[item.produto_id] = quantidades_por_produto.get(item.produto_id, 0) + item.quantidade
                produto_por_id[item.produto_id] = item.produto

            for produto_id, quantidade_total in quantidades_por_produto.items():
                if quantidade_total > saldos[produto_id]:
                    raise ValidationError(
                        f'Estoque insuficiente para {produto_por_id[produto_id].nome}. Disponível: {saldos[produto_id]}.'
                    )

            venda.recalcular_totais(save=False)
            if venda.desconto > venda.subtotal:
                raise ValidationError('O desconto não pode ser maior que o subtotal.')
            venda.status = self.Status.FINALIZADA
            venda.save(update_fields=['subtotal', 'total', 'status'])

            for item in itens:
                MovimentacaoEstoque.registrar(
                    produto=item.produto,
                    tipo_movimentacao=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                    quantidade=item.quantidade,
                    origem=f'Venda #{venda.pk}',
                    observacao='Saída gerada automaticamente ao finalizar venda.',
                    usuario=usuario or venda.usuario,
                )

            MovimentacaoCaixa.registrar(
                caixa=caixa,
                tipo=MovimentacaoCaixa.Tipo.VENDA,
                descricao=f'Venda #{venda.pk}',
                valor=venda.total,
                forma_pagamento=venda.forma_pagamento,
                venda=venda,
                usuario=usuario or venda.usuario,
                observacao='Recebimento registrado automaticamente ao finalizar venda.',
            )

            self.status = venda.status
            self.subtotal = venda.subtotal
            self.total = venda.total
            self.forma_pagamento = venda.forma_pagamento

    def get_absolute_url(self):
        return reverse('vendas:detail', kwargs={'pk': self.pk})


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='itens')
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name='itens_venda')
    quantidade = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    valor_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    total_item = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        verbose_name = 'item de venda'
        verbose_name_plural = 'itens de venda'

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
