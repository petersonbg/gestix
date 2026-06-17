from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone

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
        CREDIARIO = 'CREDIARIO', 'Crediário'
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
    quantidade_parcelas = models.PositiveIntegerField(
        'quantidade de parcelas',
        default=1,
        validators=[MinValueValidator(1)],
    )
    data_primeiro_vencimento = models.DateField('data do primeiro vencimento', blank=True, null=True)
    intervalo_parcelas = models.PositiveIntegerField(
        'intervalo entre parcelas',
        default=30,
        validators=[MinValueValidator(1)],
    )
    valor_entrada = models.DecimalField(
        'valor de entrada/sinal',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    observacoes_crediario = models.TextField('observações do crediário', blank=True)
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
    cancelada_em = models.DateTimeField('cancelada em', blank=True, null=True)
    usuario_cancelamento = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='vendas_canceladas',
        blank=True,
        null=True,
    )
    motivo_cancelamento = models.TextField('motivo do cancelamento', blank=True)

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
        if self.valor_entrada is not None and self.valor_entrada < 0:
            raise ValidationError({'valor_entrada': 'O valor de entrada não pode ser negativo.'})
        if self.total and self.valor_entrada and self.valor_entrada > self.total:
            raise ValidationError({'valor_entrada': 'O valor de entrada não pode ser maior que o total da venda.'})
        if self.forma_pagamento == self.FormaPagamento.CREDIARIO:
            if not self.cliente_id:
                raise ValidationError({'cliente': 'Selecione um cliente válido para venda no crediário.'})
            cliente = Cliente.objects.filter(pk=self.cliente_id).first() if self.cliente_id else None
            if self.cliente_id and not cliente:
                raise ValidationError({'cliente': 'Selecione um cliente válido para venda no crediário.'})
            if cliente and not cliente.ativo:
                raise ValidationError({'cliente': 'Selecione um cliente ativo para venda no crediário.'})
            nome_cliente = (cliente.nome if cliente else '').strip().lower()
            nomes_genericos = {'consumidor final', 'cliente generico', 'cliente genérico', 'consumidor'}
            if nome_cliente in nomes_genericos:
                raise ValidationError({'cliente': 'Venda no crediário não pode ser feita para cliente genérico/consumidor final.'})
            if not self.data_primeiro_vencimento:
                raise ValidationError({'data_primeiro_vencimento': 'Informe a data do primeiro vencimento.'})
            if not self.quantidade_parcelas or self.quantidade_parcelas < 1:
                raise ValidationError({'quantidade_parcelas': 'Informe ao menos uma parcela.'})
            if not self.intervalo_parcelas or self.intervalo_parcelas < 1:
                raise ValidationError({'intervalo_parcelas': 'O intervalo entre parcelas deve ser maior que zero.'})

    def save(self, *args, **kwargs):
        if self.pk and Venda.objects.filter(pk=self.pk, status=self.Status.CANCELADA).exists():
            raise ValidationError('Venda cancelada não pode ser alterada.')
        return super().save(*args, **kwargs)

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
            venda = Venda.objects.select_for_update(of=('self',)).select_related('cliente').get(pk=self.pk)
            if venda.status == self.Status.FINALIZADA:
                return
            if venda.status == self.Status.CANCELADA:
                raise ValidationError('Venda cancelada não pode ser finalizada.')

            itens = list(venda.itens.select_related('produto'))
            if not itens:
                raise ValidationError('Inclua ao menos um item para finalizar a venda.')

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
            venda.full_clean()

            from caixa.models import Caixa, MovimentacaoCaixa

            usuario_movimento = usuario or venda.usuario
            exige_caixa_imediato = venda.forma_pagamento != self.FormaPagamento.CREDIARIO or venda.valor_entrada > 0
            caixa = None
            if exige_caixa_imediato:
                caixa = Caixa.objects.select_for_update().filter(
                    usuario_abertura=usuario_movimento,
                    status=Caixa.Status.ABERTO,
                ).first()
                if not caixa:
                    raise ValidationError('É necessário abrir o caixa antes de finalizar vendas.')

            venda.status = self.Status.FINALIZADA
            venda.save(update_fields=['subtotal', 'total', 'status'])

            for item in itens:
                MovimentacaoEstoque.registrar(
                    produto=item.produto,
                    tipo_movimentacao=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                    quantidade=item.quantidade,
                    origem=f'Venda #{venda.pk}',
                    observacao='Saída gerada automaticamente ao finalizar venda.',
                    usuario=usuario_movimento,
                )

            if venda.forma_pagamento == self.FormaPagamento.CREDIARIO:
                from contas_receber.models import ContaReceber

                ContaReceber.gerar_para_venda(venda)
                if venda.valor_entrada > 0:
                    MovimentacaoCaixa.registrar(
                        caixa=caixa,
                        tipo=MovimentacaoCaixa.Tipo.ENTRADA,
                        descricao=f'Entrada de venda no crediário - Venda nº {venda.pk}',
                        valor=venda.valor_entrada,
                        forma_pagamento=MovimentacaoCaixa.FormaPagamento.DINHEIRO,
                        venda=venda,
                        usuario=usuario_movimento,
                        observacao='Entrada/sinal registrado automaticamente ao finalizar venda no crediário.',
                    )
            else:
                MovimentacaoCaixa.registrar(
                    caixa=caixa,
                    tipo=MovimentacaoCaixa.Tipo.VENDA,
                    descricao=f'Venda #{venda.pk}',
                    valor=venda.total,
                    forma_pagamento=venda.forma_pagamento,
                    venda=venda,
                    usuario=usuario_movimento,
                    observacao='Recebimento registrado automaticamente ao finalizar venda.',
                )

            self.status = venda.status
            self.subtotal = venda.subtotal
            self.total = venda.total
            self.forma_pagamento = venda.forma_pagamento
<<<<<<< HEAD
            from accounts.utils import registrar_log

            registrar_log(
                usuario_movimento,
                'FINALIZACAO',
                'vendas',
                f'Venda #{venda.pk} finalizada.',
                objeto=venda,
            )
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

    def cancelar(self, usuario, motivo):
        motivo = (motivo or '').strip()
        if not motivo:
            raise ValidationError({'motivo_cancelamento': 'Informe o motivo do cancelamento.'})
        if not self.pk:
            raise ValidationError('Salve a venda antes de cancelá-la.')

        with transaction.atomic():
            venda = Venda.objects.select_for_update().get(pk=self.pk)
            if venda.status == self.Status.FINALIZADA:
                raise ValidationError('Venda finalizada não pode ser cancelada por esta operação.')
            if venda.status == self.Status.CANCELADA:
                raise ValidationError('Venda já está cancelada.')
            if venda.status != self.Status.RASCUNHO:
                raise ValidationError('Somente vendas em rascunho podem ser canceladas.')

            venda.status = self.Status.CANCELADA
            venda.cancelada_em = timezone.now()
            venda.usuario_cancelamento = usuario
            venda.motivo_cancelamento = motivo
            venda.save(update_fields=[
                'status',
                'cancelada_em',
                'usuario_cancelamento',
                'motivo_cancelamento',
            ])

            self.status = venda.status
            self.cancelada_em = venda.cancelada_em
            self.usuario_cancelamento = venda.usuario_cancelamento
            self.motivo_cancelamento = venda.motivo_cancelamento

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
