from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse

from produtos.models import Produto


class MovimentacaoEstoque(models.Model):
    class TipoMovimentacao(models.TextChoices):
        ENTRADA = 'ENTRADA', 'Entrada'
        SAIDA = 'SAIDA', 'Saída'
        AJUSTE = 'AJUSTE', 'Ajuste'

    produto = models.ForeignKey(
        Produto,
        on_delete=models.PROTECT,
        related_name='movimentacoes_estoque',
    )
    tipo_movimentacao = models.CharField(
        'tipo de movimentação',
        max_length=10,
        choices=TipoMovimentacao.choices,
    )
    quantidade = models.PositiveIntegerField()
    origem = models.CharField(max_length=100, blank=True)
    observacao = models.TextField('observação', blank=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='movimentacoes_estoque',
        blank=True,
        null=True,
    )
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-data']
        verbose_name = 'movimentação de estoque'
        verbose_name_plural = 'movimentações de estoque'

    def __str__(self):
        return f'{self.get_tipo_movimentacao_display()} - {self.produto} ({self.quantidade})'

    def clean(self):
        super().clean()
        if (
            self.quantidade is not None
            and self.tipo_movimentacao in {self.TipoMovimentacao.ENTRADA, self.TipoMovimentacao.SAIDA}
            and self.quantidade <= 0
        ):
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero para entradas e saídas.'})

    @classmethod
    def registrar(cls, *, produto, tipo_movimentacao, quantidade, origem='', observacao='', usuario=None):
        if quantidade is None or quantidade < 0:
            raise ValidationError({'quantidade': 'A quantidade não pode ser negativa.'})
        if tipo_movimentacao in {cls.TipoMovimentacao.ENTRADA, cls.TipoMovimentacao.SAIDA} and quantidade <= 0:
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero para entradas e saídas.'})

        with transaction.atomic():
            produto_atualizado = Produto.objects.select_for_update().get(pk=produto.pk)

            if tipo_movimentacao == cls.TipoMovimentacao.ENTRADA:
                novo_saldo = produto_atualizado.estoque_atual + quantidade
            elif tipo_movimentacao == cls.TipoMovimentacao.SAIDA:
                if quantidade > produto_atualizado.estoque_atual:
                    raise ValidationError({'quantidade': 'A saída não pode ser maior que o estoque disponível.'})
                novo_saldo = produto_atualizado.estoque_atual - quantidade
            elif tipo_movimentacao == cls.TipoMovimentacao.AJUSTE:
                novo_saldo = quantidade
            else:
                raise ValidationError({'tipo_movimentacao': 'Tipo de movimentação inválido.'})

            movimentacao = cls.objects.create(
                produto=produto_atualizado,
                tipo_movimentacao=tipo_movimentacao,
                quantidade=quantidade,
                origem=origem,
                observacao=observacao,
                usuario=usuario,
            )
            produto_atualizado.estoque_atual = novo_saldo
            produto_atualizado.save(update_fields=['estoque_atual', 'atualizado_em'])
            movimentacao.produto = produto_atualizado
            return movimentacao

    def get_absolute_url(self):
        return reverse('estoque:produto_historico', kwargs={'produto_pk': self.produto_id})
