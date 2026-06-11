from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

CENTAVO = Decimal('0.01')


class Servico(models.Model):
    nome = models.CharField(max_length=150)
    descricao = models.TextField('descrição', blank=True)
    valor_padrao = models.DecimalField('valor padrão', max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_padrao__gte=0),
                name='servico_valor_padrao_nao_negativo',
            ),
        ]
        verbose_name = 'serviço'
        verbose_name_plural = 'serviços'

    def __str__(self):
        return self.nome


class OrdemServico(models.Model):
    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        EM_ANDAMENTO = 'EM_ANDAMENTO', 'Em andamento'
        AGUARDANDO_PECA = 'AGUARDANDO_PECA', 'Aguardando peça'
        CONCLUIDA = 'CONCLUIDA', 'Concluída'
        CANCELADA = 'CANCELADA', 'Cancelada'
        ENTREGUE = 'ENTREGUE', 'Entregue'

    class FormaPagamento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'PIX'
        CARTAO_DEBITO = 'CARTAO_DEBITO', 'Cartão de débito'
        CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de crédito'
        BOLETO = 'BOLETO', 'Boleto'
        CREDIARIO = 'CREDIARIO', 'Crediário'
        OUTROS = 'OUTROS', 'Outros'

    numero = models.CharField(max_length=20, unique=True, blank=True)
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.PROTECT, related_name='ordens_servico')
    data_abertura = models.DateTimeField(default=timezone.now)
    data_previsao = models.DateField('data de previsão', blank=True, null=True)
    data_finalizacao = models.DateTimeField('Data de Finalização', blank=True, null=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ABERTA)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='ordens_servico_responsavel', blank=True, null=True)
    responsavel_execucao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='ordens_servico_executadas',
        verbose_name='Responsável pela Execução',
        blank=True,
        null=True,
    )
    assinatura_responsavel_execucao = models.ImageField(
        'Assinatura do Responsável pela Execução',
        upload_to='assinaturas_os/',
        blank=True,
        null=True,
    )
    descricao_problema = models.TextField('descrição do problema')
    diagnostico = models.TextField('diagnóstico', blank=True)
    solucao = models.TextField('solução', blank=True)
    observacoes = models.TextField('observações', blank=True)
    subtotal_servicos = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    subtotal_produtos = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    valor_deslocamento = models.DecimalField(
        'Valor do Deslocamento',
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
    )
    desconto = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    estoque_baixado = models.BooleanField(default=False, editable=False)
    forma_pagamento = models.CharField(max_length=20, choices=FormaPagamento.choices, blank=True)
    valor_pago = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data_abertura']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(valor_deslocamento__gte=0),
                name='os_valor_deslocamento_nao_negativo',
            ),
        ]
        verbose_name = 'ordem de serviço'
        verbose_name_plural = 'ordens de serviço'

    def __str__(self):
        return f'OS {self.numero}'

    def save(self, *args, **kwargs):
        if not self.numero:
            with transaction.atomic():
                ultima = OrdemServico.objects.select_for_update().order_by('-id').first()
                proximo = (ultima.id if ultima else 0) + 1
                self.numero = f'OS-{timezone.localdate():%Y}-{proximo:06d}'
                return super().save(*args, **kwargs)
        return super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        if self.valor_deslocamento is not None and self.valor_deslocamento < 0:
            raise ValidationError({'valor_deslocamento': 'O valor do deslocamento não pode ser negativo.'})
        if self.responsavel_execucao_id and not self.responsavel_execucao.is_active:
            raise ValidationError({'responsavel_execucao': 'Selecione um usuário ativo para executar a OS.'})
        if self.desconto is not None and self.desconto < 0:
            raise ValidationError({'desconto': 'O desconto não pode ser negativo.'})
        bruto = (self.subtotal_servicos or 0) + (self.subtotal_produtos or 0) + (self.valor_deslocamento or 0)
        if bruto > 0 and self.desconto is not None and self.desconto > bruto:
            raise ValidationError({'desconto': 'O desconto não pode ser maior que o total da OS.'})
        if self.valor_pago is not None and self.valor_pago > self.total:
            raise ValidationError({'valor_pago': 'O valor pago não pode ser maior que o total da OS.'})

    @staticmethod
    def nome_usuario(usuario):
        if not usuario:
            return 'Não informado'
        return usuario.get_full_name().strip() or usuario.get_username()

    @property
    def nome_responsavel(self):
        return self.nome_usuario(self.responsavel)

    @property
    def nome_responsavel_execucao(self):
        return self.nome_usuario(self.responsavel_execucao)

    @property
    def finalizada(self):
        return self.status in {self.Status.CONCLUIDA, self.Status.ENTREGUE}

    @property
    def saldo(self):
        return max(self.total - self.valor_pago, Decimal('0.00'))

    @property
    def atrasada(self):
        return bool(self.data_previsao and self.data_previsao < timezone.localdate() and self.status in {
            self.Status.ABERTA, self.Status.EM_ANDAMENTO, self.Status.AGUARDANDO_PECA
        })

    def recalcular_totais(self, salvar=True):
        self.subtotal_servicos = self.itens_servico.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        self.subtotal_produtos = self.itens_produto.aggregate(total=Sum('subtotal'))['total'] or Decimal('0.00')
        self.total = max(self.subtotal_servicos + self.subtotal_produtos + self.valor_deslocamento - self.desconto, Decimal('0.00')).quantize(CENTAVO)
        if salvar:
            self.save(update_fields=['subtotal_servicos', 'subtotal_produtos', 'total', 'atualizado_em'])
        return self.total

    def registrar_historico(self, usuario, acao, descricao=''):
        return HistoricoOrdemServico.objects.create(ordem_servico=self, usuario=usuario, acao=acao, descricao=descricao)

    def alterar_status(self, novo_status, usuario):
        if self.finalizada:
            if self.status == self.Status.CONCLUIDA and novo_status == self.Status.ENTREGUE:
                anterior = self.status
                self.status = novo_status
                self.save(update_fields=['status', 'atualizado_em'])
                self.registrar_historico(
                    usuario,
                    'MUDANCA_STATUS',
                    f'Status alterado de {self.Status(anterior).label} para {self.Status(novo_status).label}.',
                )
                return self
            raise ValidationError('Esta ordem de serviço já foi finalizada e não pode ser editada.')
        if novo_status == self.Status.CONCLUIDA:
            return self.concluir(usuario)
        if novo_status == self.Status.CANCELADA:
            return self.cancelar(usuario)
        if novo_status == self.Status.ENTREGUE:
            raise ValidationError('A ordem deve estar concluída antes da entrega.')
        anterior = self.status
        self.status = novo_status
        self.save(update_fields=['status', 'atualizado_em'])
        self.registrar_historico(
            usuario,
            'MUDANCA_STATUS',
            f'Status alterado de {self.Status(anterior).label} para {self.Status(novo_status).label}.',
        )
        return self

    def concluir(self, usuario):
        from estoque.models import MovimentacaoEstoque
        from produtos.models import Produto

        with transaction.atomic():
            ordem = OrdemServico.objects.select_for_update().get(pk=self.pk)
            if ordem.status == self.Status.CANCELADA:
                raise ValidationError('Ordem de serviço cancelada não pode ser concluída.')
            if ordem.finalizada:
                raise ValidationError('Esta ordem de serviço já foi finalizada e não pode ser editada.')
            itens = list(ordem.itens_produto.select_related('produto'))
            produtos = {
                produto.pk: produto
                for produto in Produto.objects.select_for_update().filter(pk__in=[item.produto_id for item in itens])
            }
            for item in itens:
                if item.quantidade > produtos[item.produto_id].estoque_atual:
                    raise ValidationError(f'Estoque insuficiente para o produto {item.produto.nome}.')
            if not ordem.estoque_baixado:
                for item in itens:
                    MovimentacaoEstoque.registrar(
                        produto=produtos[item.produto_id],
                        tipo_movimentacao=MovimentacaoEstoque.TipoMovimentacao.SAIDA,
                        quantidade=item.quantidade,
                        origem='ORDEM_SERVICO',
                        observacao=f'Saída referente à OS nº {ordem.numero}',
                        usuario=usuario,
                    )
                ordem.estoque_baixado = True
            status_anterior = ordem.status
            ordem.status = self.Status.CONCLUIDA
            ordem.data_finalizacao = timezone.now()
            ordem.save(update_fields=['status', 'data_finalizacao', 'estoque_baixado', 'atualizado_em'])
            data_local = timezone.localtime(ordem.data_finalizacao)
            ordem.registrar_historico(
                usuario,
                'CONCLUSAO',
                (
                    f'OS finalizada em {data_local:%d/%m/%Y %H:%M:%S} por '
                    f'{self.nome_usuario(usuario)}. Status alterado de '
                    f'{self.Status(status_anterior).label} para {self.Status.CONCLUIDA.label}. '
                    'Estoque baixado.'
                ),
            )
            self.refresh_from_db()
            return ordem

    def cancelar(self, usuario):
        if self.finalizada:
            raise ValidationError('Esta ordem de serviço já foi finalizada e não pode ser editada.')
        if self.estoque_baixado:
            raise ValidationError('A OS já baixou estoque. Faça o estorno antes de cancelar.')
        if self.status == self.Status.ENTREGUE:
            raise ValidationError('Ordem entregue não pode ser cancelada.')
        self.status = self.Status.CANCELADA
        self.save(update_fields=['status', 'atualizado_em'])
        self.registrar_historico(usuario, 'CANCELAMENTO', 'Ordem de serviço cancelada sem movimentar estoque.')
        return self

    def registrar_pagamento(self, *, usuario, forma_pagamento, valor, parcelas=1, primeiro_vencimento=None, intervalo=30):
        from caixa.models import Caixa, MovimentacaoCaixa
        from contas_receber.models import ContaReceber

        valor = Decimal(valor).quantize(CENTAVO, rounding=ROUND_HALF_UP)
        if self.status not in {self.Status.CONCLUIDA, self.Status.ENTREGUE}:
            raise ValidationError('Conclua a OS antes de registrar o pagamento.')
        if valor <= 0 or valor > self.saldo:
            raise ValidationError('O valor recebido deve ser maior que zero e não pode superar o saldo da OS.')
        with transaction.atomic():
            ordem = OrdemServico.objects.select_for_update().get(pk=self.pk)
            if forma_pagamento == self.FormaPagamento.CREDIARIO:
                if valor != ordem.saldo:
                    raise ValidationError('O crediário deve ser gerado para o saldo total da OS.')
                if not primeiro_vencimento:
                    raise ValidationError('Informe o primeiro vencimento do crediário.')
                ContaReceber.gerar_para_ordem_servico(ordem, parcelas, primeiro_vencimento, intervalo, valor)
            else:
                caixa = Caixa.objects.select_for_update().filter(usuario_abertura=usuario, status=Caixa.Status.ABERTO).first()
                if not caixa:
                    raise ValidationError('É necessário abrir o caixa antes de receber a ordem de serviço.')
                MovimentacaoCaixa.registrar(
                    caixa=caixa, tipo=MovimentacaoCaixa.Tipo.ENTRADA,
                    descricao=f'Recebimento da OS nº {ordem.numero}', valor=valor,
                    forma_pagamento=forma_pagamento, usuario=usuario,
                    observacao=f'Recebimento referente à OS nº {ordem.numero}',
                )
                ordem.valor_pago += valor
            ordem.forma_pagamento = forma_pagamento
            ordem.save(update_fields=['forma_pagamento', 'valor_pago', 'atualizado_em'])
            ordem.registrar_historico(usuario, 'PAGAMENTO', f'Pagamento registrado: {forma_pagamento} - R$ {valor}.')
            self.refresh_from_db()
            return ordem

    def get_absolute_url(self):
        return reverse('ordens_servico:detail', kwargs={'pk': self.pk})


class ItemServicoOS(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='itens_servico')
    servico = models.ForeignKey(Servico, on_delete=models.PROTECT, related_name='itens_os')
    descricao = models.CharField(max_length=255, blank=True)
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)

    class Meta:
        verbose_name = 'item de serviço da OS'
        verbose_name_plural = 'itens de serviço da OS'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantidade__gt=0),
                name='item_servico_os_quantidade_positiva',
            ),
            models.CheckConstraint(
                condition=models.Q(valor_unitario__gte=0),
                name='item_servico_os_valor_nao_negativo',
            ),
        ]

    def clean(self):
        super().clean()
        if self.quantidade is None or self.quantidade <= 0:
            raise ValidationError({'quantidade': 'A quantidade deve ser maior que zero.'})
        if self.valor_unitario is None or self.valor_unitario < 0:
            raise ValidationError({'valor_unitario': 'O valor unitário não pode ser negativo.'})

    def save(self, *args, **kwargs):
        self.subtotal = (Decimal(self.quantidade) * self.valor_unitario).quantize(CENTAVO)
        if not self.descricao:
            self.descricao = self.servico.nome
        return super().save(*args, **kwargs)


class ItemProdutoOS(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='itens_produto')
    produto = models.ForeignKey('produtos.Produto', on_delete=models.PROTECT, related_name='itens_ordem_servico')
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    valor_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'), editable=False)

    def save(self, *args, **kwargs):
        self.subtotal = (Decimal(self.quantidade) * self.valor_unitario).quantize(CENTAVO)
        return super().save(*args, **kwargs)


class HistoricoOrdemServico(models.Model):
    ordem_servico = models.ForeignKey(OrdemServico, on_delete=models.CASCADE, related_name='historico')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    acao = models.CharField(max_length=40)
    descricao = models.TextField('descrição', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'histórico da ordem de serviço'
        verbose_name_plural = 'históricos das ordens de serviço'
