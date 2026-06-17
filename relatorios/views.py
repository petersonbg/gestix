import csv
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.generic import TemplateView

from accounts.permissions import perfil_atual
from accounts.utils import registrar_log
from administracao.models import CategoriaProduto
from administracao.services import contexto_documento_impresso
from caixa.models import Caixa, MovimentacaoCaixa
from clientes.models import Cliente
from contas_pagar.models import CategoriaDespesa, ContaPagar
from contas_receber.models import ContaReceber
from fornecedores.models import Fornecedor
from produtos.models import Produto
from vendas.models import Venda

from .permissions import RELATORIOS_PERMISSOES

DECIMAL_ZERO = Decimal('0.00')


def decimal_agregado(valor):
    return valor or DECIMAL_ZERO


def data_get(request, nome):
    return parse_date(request.GET.get(nome, '') or '')


def get_id(request, nome):
    valor = (request.GET.get(nome) or '').strip()
    return int(valor) if valor.isdigit() else None


def escrever_csv(response, cabecalho, linhas):
    writer = csv.writer(response, delimiter=';')
    writer.writerow(cabecalho)
    for linha in linhas:
        writer.writerow(linha)


class RelatorioPermissaoMixin(LoginRequiredMixin, UserPassesTestMixin):
    relatorio = ''

    def test_func(self):
        perfil = perfil_atual(self.request.user)
        return perfil in RELATORIOS_PERMISSOES.get(self.relatorio, set())

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Você não possui permissão para acessar este recurso.')
        registrar_log(
            self.request.user,
            'ERRO',
            'relatorios',
            f'Tentativa de acesso indevido ao relatório {self.relatorio}.',
            request=self.request,
        )
        return redirect('acesso_negado')

    def registrar_emissao(self, descricao):
        registrar_log(
            self.request.user,
            'IMPRESSAO',
            'relatorios',
            descricao,
            request=self.request,
        )

    def dispatch(self, request, *args, **kwargs):
        self.formato = request.GET.get('formato', '')
        self.imprimir = request.GET.get('imprimir') == '1'
        return super().dispatch(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        if self.formato == 'csv':
            self.registrar_emissao(f'Exportação CSV do relatório {self.relatorio}.')
            return self.render_csv(context)
        if self.imprimir:
            self.registrar_emissao(f'Impressão do relatório {self.relatorio}.')
            context['modo_impressao'] = True
            self.template_name = 'relatorios/impressao.html'
        else:
            self.registrar_emissao(f'Emissão do relatório {self.relatorio}.')
        return super().render_to_response(context, **response_kwargs)

    def base_context(self, titulo):
        contexto = contexto_documento_impresso()
        contexto.update({
            'titulo_relatorio': titulo,
            'relatorio_slug': self.relatorio,
            'emitido_em': timezone.now(),
            'emitido_por': self.request.user,
            'querystring': self.request.GET.urlencode(),
        })
        return contexto


class RelatoriosHomeView(LoginRequiredMixin, TemplateView):
    template_name = 'relatorios/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        perfil = perfil_atual(self.request.user)
        context['relatorios_disponiveis'] = [
            item for item in [
                ('Vendas por Período', 'relatorios:vendas', 'vendas'),
                ('Estoque Baixo', 'relatorios:estoque_baixo', 'estoque_baixo'),
                ('Contas a Receber', 'relatorios:contas_receber', 'contas_receber'),
                ('Contas a Pagar', 'relatorios:contas_pagar', 'contas_pagar'),
                ('Caixa Diário', 'relatorios:caixa_diario', 'caixa_diario'),
            ]
            if perfil in RELATORIOS_PERMISSOES[item[2]]
        ]
        return context


class VendasPeriodoView(RelatorioPermissaoMixin, TemplateView):
    relatorio = 'vendas'
    template_name = 'relatorios/vendas.html'

    def get_queryset(self):
        qs = Venda.objects.select_related('cliente', 'usuario').order_by('-data')
        inicial = data_get(self.request, 'data_inicial')
        final = data_get(self.request, 'data_final')
        cliente_id = get_id(self.request, 'cliente')
        vendedor_id = get_id(self.request, 'vendedor')
        forma = self.request.GET.get('forma_pagamento', '')
        status = self.request.GET.get('status', '')
        incluir_canceladas = self.request.GET.get('incluir_canceladas') == 'on'
        if inicial:
            qs = qs.filter(data__date__gte=inicial)
        if final:
            qs = qs.filter(data__date__lte=final)
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if vendedor_id:
            qs = qs.filter(usuario_id=vendedor_id)
        if forma:
            qs = qs.filter(forma_pagamento=forma)
        if status:
            qs = qs.filter(status=status)
        elif incluir_canceladas:
            qs = qs.filter(status__in=[Venda.Status.FINALIZADA, Venda.Status.CANCELADA])
        else:
            qs = qs.filter(status=Venda.Status.FINALIZADA)
        return qs

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        agregados = qs.aggregate(
            quantidade=Count('pk'),
            subtotal=Coalesce(Sum('subtotal'), DECIMAL_ZERO),
            desconto=Coalesce(Sum('desconto'), DECIMAL_ZERO),
            total=Coalesce(Sum('total'), DECIMAL_ZERO),
        )
        por_forma = qs.values('forma_pagamento').annotate(total=Coalesce(Sum('total'), DECIMAL_ZERO)).order_by('forma_pagamento')
        context = super().get_context_data(**kwargs)
        context.update(self.base_context('Vendas por Período'))
        context.update({
            'vendas': qs,
            'resumo': agregados,
            'total_por_forma': [(Venda.FormaPagamento(item['forma_pagamento']).label, item['total']) for item in por_forma],
            'clientes': Cliente.objects.order_by('nome'),
            'vendedores': get_user_model().objects.order_by('username'),
            'formas_pagamento': Venda.FormaPagamento.choices,
            'status_choices': Venda.Status.choices,
        })
        return context

    def render_csv(self, context):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_vendas.csv"'
        escrever_csv(response, ['Numero', 'Data', 'Cliente', 'Vendedor', 'Forma', 'Subtotal', 'Desconto', 'Total', 'Status'], [
            [v.pk, v.data.strftime('%d/%m/%Y %H:%M'), v.cliente, v.usuario or '', v.get_forma_pagamento_display(), v.subtotal, v.desconto, v.total, v.get_status_display()]
            for v in context['vendas']
        ])
        return response


class EstoqueBaixoView(RelatorioPermissaoMixin, TemplateView):
    relatorio = 'estoque_baixo'
    template_name = 'relatorios/estoque_baixo.html'

    def get_queryset(self):
        qs = Produto.objects.select_related('categoria', 'fornecedor').filter(estoque_atual__lte=F('estoque_minimo')).order_by('nome')
        categoria_id = get_id(self.request, 'categoria')
        fornecedor_id = get_id(self.request, 'fornecedor')
        ativo = self.request.GET.get('ativo', '')
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        if fornecedor_id:
            qs = qs.filter(fornecedor_id=fornecedor_id)
        if ativo in {'true', 'false'}:
            qs = qs.filter(ativo=ativo == 'true')
        return qs

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        total_falta = sum(max((p.estoque_minimo or 0) - (p.estoque_atual or 0), 0) for p in qs)
        valor_reposicao = sum((p.preco_custo or DECIMAL_ZERO) * max((p.estoque_minimo or 0) - (p.estoque_atual or 0), 0) for p in qs)
        context = super().get_context_data(**kwargs)
        context.update(self.base_context('Estoque Baixo'))
        context.update({
            'produtos': qs,
            'resumo': {'quantidade': qs.count(), 'total_falta': total_falta, 'valor_reposicao': valor_reposicao},
            'categorias': CategoriaProduto.objects.order_by('nome'),
            'fornecedores': Fornecedor.objects.order_by('razao_social'),
        })
        return context

    def render_csv(self, context):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_estoque_baixo.csv"'
        escrever_csv(response, ['Codigo', 'Produto', 'Categoria', 'Fornecedor', 'Estoque atual', 'Estoque minimo', 'Unidade', 'Status'], [
            [p.codigo_interno, p.nome, p.categoria or '', p.fornecedor or '', p.estoque_atual, p.estoque_minimo, p.unidade_medida, 'Ativo' if p.ativo else 'Inativo']
            for p in context['produtos']
        ])
        return response


class ContasReceberView(RelatorioPermissaoMixin, TemplateView):
    relatorio = 'contas_receber'
    template_name = 'relatorios/contas_receber.html'

    def get_queryset(self):
        hoje = timezone.localdate()
        qs = ContaReceber.objects.select_related('cliente', 'venda').order_by('data_vencimento', 'numero_parcela')
        inicial = data_get(self.request, 'data_inicial')
        final = data_get(self.request, 'data_final')
        cliente_id = get_id(self.request, 'cliente')
        status = self.request.GET.get('status', '')
        vencimento = self.request.GET.get('vencimento', '')
        if inicial:
            qs = qs.filter(data_vencimento__gte=inicial)
        if final:
            qs = qs.filter(data_vencimento__lte=final)
        if cliente_id:
            qs = qs.filter(cliente_id=cliente_id)
        if status:
            qs = qs.filter(status=status)
        if vencimento == 'vencidas':
            qs = qs.filter(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
        elif vencimento == 'hoje':
            qs = qs.filter(data_vencimento=hoje)
        elif vencimento == 'a_vencer':
            qs = qs.filter(status=ContaReceber.Status.ABERTA, data_vencimento__gt=hoje)
        return qs

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        hoje = timezone.localdate()
        context = super().get_context_data(**kwargs)
        context.update(self.base_context('Contas a Receber'))
        context.update({
            'contas': qs,
            'resumo': {
                'aberto': decimal_agregado(qs.filter(status=ContaReceber.Status.ABERTA).aggregate(total=Sum('valor'))['total']),
                'recebido': decimal_agregado(qs.filter(status=ContaReceber.Status.PAGA).aggregate(total=Sum('valor_pago'))['total']),
                'atrasado': decimal_agregado(qs.filter(Q(status=ContaReceber.Status.ATRASADA) | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)).aggregate(total=Sum('valor'))['total']),
                'parcelas_atrasadas': qs.filter(Q(status=ContaReceber.Status.ATRASADA) | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)).count(),
            },
            'clientes': Cliente.objects.order_by('nome'),
            'status_choices': ContaReceber.Status.choices,
        })
        return context

    def render_csv(self, context):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_contas_receber.csv"'
        escrever_csv(response, ['Cliente', 'Venda', 'Parcela', 'Vencimento', 'Pagamento', 'Valor', 'Valor pago', 'Status'], [
            [c.cliente, c.venda_id or '', f'{c.numero_parcela}/{c.total_parcelas}', c.data_vencimento, c.data_pagamento or '', c.valor, c.valor_pago, c.status_exibicao_label]
            for c in context['contas']
        ])
        return response


class ContasPagarView(RelatorioPermissaoMixin, TemplateView):
    relatorio = 'contas_pagar'
    template_name = 'relatorios/contas_pagar.html'

    def get_queryset(self):
        hoje = timezone.localdate()
        qs = ContaPagar.objects.select_related('fornecedor', 'categoria').order_by('data_vencimento', 'descricao')
        inicial = data_get(self.request, 'data_inicial')
        final = data_get(self.request, 'data_final')
        fornecedor_id = get_id(self.request, 'fornecedor')
        categoria_id = get_id(self.request, 'categoria')
        status = self.request.GET.get('status', '')
        vencimento = self.request.GET.get('vencimento', '')
        if inicial:
            qs = qs.filter(data_vencimento__gte=inicial)
        if final:
            qs = qs.filter(data_vencimento__lte=final)
        if fornecedor_id:
            qs = qs.filter(fornecedor_id=fornecedor_id)
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
        if status:
            qs = qs.filter(status=status)
        if vencimento == 'vencidas':
            qs = qs.filter(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
        elif vencimento == 'hoje':
            qs = qs.filter(data_vencimento=hoje)
        elif vencimento == 'a_vencer':
            qs = qs.filter(status=ContaPagar.Status.ABERTA, data_vencimento__gt=hoje)
        return qs

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        hoje = timezone.localdate()
        sete_dias = hoje + timedelta(days=7)
        context = super().get_context_data(**kwargs)
        context.update(self.base_context('Contas a Pagar'))
        context.update({
            'contas': qs,
            'resumo': {
                'aberto': decimal_agregado(qs.filter(status=ContaPagar.Status.ABERTA).aggregate(total=Sum('valor'))['total']),
                'pago': decimal_agregado(qs.filter(status=ContaPagar.Status.PAGA).aggregate(total=Sum('valor_pago'))['total']),
                'atrasado': decimal_agregado(qs.filter(Q(status=ContaPagar.Status.ATRASADA) | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)).aggregate(total=Sum('valor'))['total']),
                'proximos_7': qs.filter(status=ContaPagar.Status.ABERTA, data_vencimento__gte=hoje, data_vencimento__lte=sete_dias).count(),
            },
            'fornecedores': Fornecedor.objects.order_by('razao_social'),
            'categorias': CategoriaDespesa.objects.order_by('nome'),
            'status_choices': ContaPagar.Status.choices,
        })
        return context

    def render_csv(self, context):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_contas_pagar.csv"'
        escrever_csv(response, ['Descricao', 'Fornecedor', 'Categoria', 'Vencimento', 'Pagamento', 'Valor', 'Valor pago', 'Status'], [
            [c.descricao, c.fornecedor or '', c.categoria, c.data_vencimento, c.data_pagamento or '', c.valor, c.valor_pago, c.status_exibicao_label]
            for c in context['contas']
        ])
        return response


class CaixaDiarioView(RelatorioPermissaoMixin, TemplateView):
    relatorio = 'caixa_diario'
    template_name = 'relatorios/caixa_diario.html'

    def get_queryset(self):
        data = data_get(self.request, 'data') or timezone.localdate()
        qs = Caixa.objects.select_related('usuario_abertura', 'usuario_fechamento').prefetch_related('movimentacoes').filter(data_abertura__date=data)
        usuario_id = get_id(self.request, 'usuario')
        status = self.request.GET.get('status', '')
        if usuario_id:
            qs = qs.filter(usuario_abertura_id=usuario_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by('-data_abertura')

    def totais_caixa(self, caixa):
        totais = caixa.totais_por_tipo()
        por_forma = {
            item['forma_pagamento']: item['total'] or DECIMAL_ZERO
            for item in caixa.movimentacoes.filter(tipo=MovimentacaoCaixa.Tipo.VENDA).values('forma_pagamento').annotate(total=Sum('valor'))
        }
        return {
            'vendas': totais[MovimentacaoCaixa.Tipo.VENDA],
            'suprimentos': totais[MovimentacaoCaixa.Tipo.SUPRIMENTO],
            'sangrias': totais[MovimentacaoCaixa.Tipo.SANGRIA],
            'saidas': totais[MovimentacaoCaixa.Tipo.SAIDA],
            'saldo': caixa.saldo_calculado(),
            'dinheiro': por_forma.get(MovimentacaoCaixa.FormaPagamento.DINHEIRO, DECIMAL_ZERO),
            'pix': por_forma.get(MovimentacaoCaixa.FormaPagamento.PIX, DECIMAL_ZERO),
            'cartao': por_forma.get(MovimentacaoCaixa.FormaPagamento.CARTAO_CREDITO, DECIMAL_ZERO) + por_forma.get(MovimentacaoCaixa.FormaPagamento.CARTAO_DEBITO, DECIMAL_ZERO),
        }

    def get_context_data(self, **kwargs):
        qs = self.get_queryset()
        linhas = [(caixa, self.totais_caixa(caixa)) for caixa in qs]
        context = super().get_context_data(**kwargs)
        context.update(self.base_context('Caixa Diário'))
        context.update({
            'caixas': linhas,
            'resumo': {
                'abertos': qs.filter(status=Caixa.Status.ABERTO).count(),
                'fechados': qs.filter(status=Caixa.Status.FECHADO).count(),
                'vendido': sum(t['vendas'] for _, t in linhas),
                'dinheiro': sum(t['dinheiro'] for _, t in linhas),
                'pix': sum(t['pix'] for _, t in linhas),
                'cartao': sum(t['cartao'] for _, t in linhas),
                'diferenca': sum(c.diferenca or DECIMAL_ZERO for c, _ in linhas),
            },
            'usuarios': get_user_model().objects.order_by('username'),
            'status_choices': Caixa.Status.choices,
        })
        return context

    def render_csv(self, context):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="relatorio_caixa_diario.csv"'
        escrever_csv(response, ['Usuario', 'Abertura', 'Fechamento', 'Inicial', 'Vendas', 'Suprimentos', 'Sangrias', 'Saidas', 'Saldo', 'Informado', 'Diferenca', 'Status'], [
            [c.usuario_abertura, c.data_abertura, c.data_fechamento or '', c.valor_inicial, t['vendas'], t['suprimentos'], t['sangrias'], t['saidas'], t['saldo'], c.valor_fechamento_informado or '', c.diferenca, c.get_status_display()]
            for c, t in context['caixas']
        ])
        return response
