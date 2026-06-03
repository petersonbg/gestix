from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone


CENTAVO = Decimal('0.01')


class ContaReceber(models.Model):
    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        PAGA = 'PAGA', 'Paga'
        ATRASADA = 'ATRASADA', 'Atrasada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class FormaRecebimento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'PIX'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de débito'
        BOLETO = 'BOLETO', 'Boleto'
        OUTROS = 'OUTROS', 'Outros'

    venda = models.ForeignKey('vendas.Venda', on_delete=models.PROTECT, related_name='contas_receber')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='contas_receber')
    numero_parcela = models.PositiveIntegerField()
    total_parcelas = models.PositiveIntegerField()
    data_emissao = models.DateField(default=timezone.localdate)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(blank=True, null=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    forma_recebimento = models.CharField(max_length=20, choices=FormaRecebimento.choices, blank=True)
    observacao = models.TextField('observação', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['data_vencimento', 'numero_parcela']
        verbose_name = 'conta a receber'
        verbose_name_plural = 'contas a receber'
        constraints = [
            models.UniqueConstraint(fields=['venda', 'numero_parcela'], name='unique_parcela_por_venda')
        ]

    def __str__(self):
        return f'Venda #{self.venda_id} - Parcela {self.numero_parcela}/{self.total_parcelas}'

    @property
    def saldo(self):
        return max(self.valor - self.valor_pago, Decimal('0.00'))

    @property
    def status_exibicao(self):
        if self.status == self.Status.ABERTA and self.data_vencimento < timezone.localdate():
            return self.Status.ATRASADA
        return self.status

    @property
    def status_exibicao_label(self):
        return self.Status(self.status_exibicao).label

    def clean(self):
        super().clean()
        if self.valor is not None and self.valor < 0:
            raise ValidationError({'valor': 'O valor da parcela não pode ser negativo.'})
        if self.valor_pago is not None and self.valor_pago < 0:
            raise ValidationError({'valor_pago': 'O valor pago não pode ser negativo.'})
        if self.valor is not None and self.valor_pago is not None and self.valor_pago > self.valor:
            raise ValidationError({'valor_pago': 'O valor recebido não pode ser maior que o valor da parcela.'})

    @classmethod
    def gerar_para_venda(cls, venda):
        if venda.forma_pagamento != venda.FormaPagamento.CREDIARIO:
            return []
        if cls.objects.filter(venda=venda).exists():
            return list(cls.objects.filter(venda=venda))

        total_parcelas = venda.quantidade_parcelas
        valor_a_parcelar = (venda.total - venda.valor_entrada).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if valor_a_parcelar <= 0:
            return []

        valor_base = (valor_a_parcelar / total_parcelas).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        parcelas = []
        acumulado = Decimal('0.00')
        for numero in range(1, total_parcelas + 1):
            valor = valor_base if numero < total_parcelas else (valor_a_parcelar - acumulado).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            acumulado += valor
            parcelas.append(cls(
                venda=venda,
                cliente=venda.cliente,
                numero_parcela=numero,
                total_parcelas=total_parcelas,
                data_emissao=timezone.localdate(),
                data_vencimento=venda.data_primeiro_vencimento + timedelta(days=venda.intervalo_parcelas * (numero - 1)),
                valor=valor,
                observacao=venda.observacoes_crediario,
            ))
        return cls.objects.bulk_create(parcelas)

    def receber(self, *, usuario, valor_recebido, forma_recebimento, data_pagamento=None, observacao=''):
        if self.status == self.Status.CANCELADA:
            raise ValidationError('Não é possível receber parcela cancelada.')
        if self.status == self.Status.PAGA:
            raise ValidationError('Esta parcela já está paga.')
        if valor_recebido is None or valor_recebido <= 0:
            raise ValidationError({'valor_pago': 'Informe um valor recebido maior que zero.'})
        if valor_recebido > self.saldo:
            raise ValidationError({'valor_pago': 'O valor recebido não pode ser maior que o saldo da parcela.'})

        from caixa.models import Caixa, MovimentacaoCaixa

        with transaction.atomic():
            conta = ContaReceber.objects.select_for_update().get(pk=self.pk)
            if conta.status == ContaReceber.Status.CANCELADA:
                raise ValidationError('Não é possível receber parcela cancelada.')
            if conta.status == ContaReceber.Status.PAGA:
                raise ValidationError('Esta parcela já está paga.')
            if valor_recebido > conta.saldo:
                raise ValidationError({'valor_pago': 'O valor recebido não pode ser maior que o saldo da parcela.'})
            caixa = Caixa.objects.select_for_update().filter(usuario_abertura=usuario, status=Caixa.Status.ABERTO).first()
            if not caixa:
                raise ValidationError('É necessário abrir o caixa antes de receber parcelas.')

            conta.valor_pago = (conta.valor_pago + valor_recebido).quantize(CENTAVO, rounding=ROUND_HALF_UP)
            conta.forma_recebimento = forma_recebimento
            conta.observacao = observacao
            if conta.valor_pago >= conta.valor:
                conta.valor_pago = conta.valor
                conta.status = ContaReceber.Status.PAGA
                conta.data_pagamento = data_pagamento or timezone.localdate()
            conta.full_clean()
            conta.save(update_fields=['valor_pago', 'forma_recebimento', 'observacao', 'status', 'data_pagamento', 'atualizado_em'])

            MovimentacaoCaixa.registrar(
                caixa=caixa,
                tipo=MovimentacaoCaixa.Tipo.ENTRADA,
                descricao=f'Recebimento de parcela - Venda nº {conta.venda_id} ({conta.numero_parcela}/{conta.total_parcelas})',
                valor=valor_recebido,
                forma_pagamento=forma_recebimento,
                usuario=usuario,
                venda=conta.venda,
                observacao=observacao,
            )
            self.refresh_from_db()
            return conta

    def cancelar(self, observacao=''):
        if self.status == self.Status.PAGA:
            raise ValidationError('Não é possível cancelar parcela já paga sem procedimento específico.')
        self.status = self.Status.CANCELADA
        self.observacao = observacao or self.observacao
        self.save(update_fields=['status', 'observacao', 'atualizado_em'])

    def get_absolute_url(self):
        return reverse('contas_receber:detail', kwargs={'pk': self.pk})
