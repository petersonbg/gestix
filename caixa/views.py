from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render
from django.utils.dateparse import parse_date
from django.views import View
from django.views.generic import ListView

from accounts.utils import registrar_log

from .forms import CaixaAberturaForm, CaixaFechamentoForm, MovimentacaoCaixaForm
from .models import Caixa, MovimentacaoCaixa


TIPO_CONFIG = {
    MovimentacaoCaixa.Tipo.SUPRIMENTO: {
        'titulo': 'Lançar suprimento',
        'descricao': 'Suprimento de caixa',
        'sucesso': 'Suprimento lançado com sucesso.',
    },
    MovimentacaoCaixa.Tipo.SANGRIA: {
        'titulo': 'Lançar sangria',
        'descricao': 'Sangria de caixa',
        'sucesso': 'Sangria lançada com sucesso.',
    },
    MovimentacaoCaixa.Tipo.SAIDA: {
        'titulo': 'Lançar saída manual',
        'descricao': 'Saída manual de caixa',
        'sucesso': 'Saída manual lançada com sucesso.',
    },
}


def usuario_admin_ou_gerente(user):
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Gerente']).exists()


def caixa_aberto_ou_redirect(request):
    caixa = Caixa.caixa_aberto_do_usuario(request.user)
    if not caixa:
        messages.warning(request, 'Abra o caixa antes de registrar movimentações.')
    return caixa


def resumo_caixa(caixa):
    totais = caixa.totais_por_tipo()
    total_vendas = totais[MovimentacaoCaixa.Tipo.VENDA]
    total_entradas = totais[MovimentacaoCaixa.Tipo.ENTRADA]
    total_saidas = totais[MovimentacaoCaixa.Tipo.SAIDA]
    total_sangrias = totais[MovimentacaoCaixa.Tipo.SANGRIA]
    total_suprimentos = totais[MovimentacaoCaixa.Tipo.SUPRIMENTO]
    total_cancelamentos = totais[MovimentacaoCaixa.Tipo.CANCELAMENTO]
    saldo = caixa.valor_inicial + total_vendas + total_entradas + total_suprimentos - total_saidas - total_sangrias - total_cancelamentos
    return {
        'total_vendas': total_vendas,
        'total_entradas': total_entradas,
        'total_saidas': total_saidas,
        'total_sangrias': total_sangrias,
        'total_suprimentos': total_suprimentos,
        'total_cancelamentos': total_cancelamentos,
        'saldo_calculado': saldo,
    }


class CaixaIndexView(LoginRequiredMixin, View):
    def get(self, request):
        if Caixa.caixa_aberto_do_usuario(request.user):
            return redirect('caixa:atual')
        return redirect('caixa:abrir')


class CaixaAbrirView(LoginRequiredMixin, View):
    template_name = 'caixa/abrir.html'

    def get(self, request):
        caixa = Caixa.caixa_aberto_do_usuario(request.user)
        if caixa:
            messages.info(request, 'Você já possui um caixa aberto.')
            return redirect('caixa:atual')
        return render(request, self.template_name, {'form': CaixaAberturaForm()})

    def post(self, request):
        if Caixa.caixa_aberto_do_usuario(request.user):
            messages.error(request, 'Cada usuário só pode ter um caixa aberto por vez.')
            return redirect('caixa:atual')

        form = CaixaAberturaForm(request.POST)
        if form.is_valid():
            try:
                caixa = Caixa.abrir(
                    usuario=request.user,
                    valor_inicial=form.cleaned_data['valor_inicial'],
                    observacao_abertura=form.cleaned_data.get('observacao_abertura', ''),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Caixa aberto com sucesso.')
<<<<<<< HEAD
                registrar_log(request.user, 'abertura de caixa', 'caixa', f'Caixa #{caixa.pk} aberto.', objeto=caixa, request=request)
=======
                registrar_log(request.user, 'abertura de caixa', 'caixa', f'Caixa #{caixa.pk} aberto.', request=request)
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
                return redirect('caixa:atual')

        return render(request, self.template_name, {'form': form})


class CaixaAtualView(LoginRequiredMixin, View):
    template_name = 'caixa/atual.html'

    def get(self, request):
        caixa = caixa_aberto_ou_redirect(request)
        if not caixa:
            return redirect('caixa:abrir')
        movimentacoes = caixa.movimentacoes.select_related('usuario', 'venda')
        context = {'caixa': caixa, 'movimentacoes': movimentacoes, **resumo_caixa(caixa)}
        return render(request, self.template_name, context)


class CaixaMovimentacaoView(LoginRequiredMixin, View):
    template_name = 'caixa/movimentacao_form.html'
    tipo = None

    def dispatch(self, request, *args, **kwargs):
        self.config = TIPO_CONFIG[self.tipo]
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        caixa = caixa_aberto_ou_redirect(request)
        if not caixa:
            return redirect('caixa:abrir')
        form = MovimentacaoCaixaForm(initial={'descricao': self.config['descricao']})
        return render(request, self.template_name, {'form': form, 'caixa': caixa, 'titulo': self.config['titulo']})

    def post(self, request):
        caixa = caixa_aberto_ou_redirect(request)
        if not caixa:
            return redirect('caixa:abrir')
        form = MovimentacaoCaixaForm(request.POST)
        if form.is_valid():
            try:
                movimentacao = MovimentacaoCaixa.registrar(
                    caixa=caixa,
                    tipo=self.tipo,
                    descricao=form.cleaned_data['descricao'],
                    valor=form.cleaned_data['valor'],
                    forma_pagamento=form.cleaned_data['forma_pagamento'],
                    usuario=request.user,
                    observacao=form.cleaned_data.get('observacao', ''),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, self.config['sucesso'])
<<<<<<< HEAD
                registrar_log(request.user, self.config['titulo'].lower(), 'caixa', f'Movimentação #{movimentacao.pk} lançada.', objeto=movimentacao, request=request)
=======
                registrar_log(request.user, self.config['titulo'].lower(), 'caixa', f'Movimentação #{movimentacao.pk} lançada.', request=request)
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
                return redirect('caixa:atual')
        return render(request, self.template_name, {'form': form, 'caixa': caixa, 'titulo': self.config['titulo']})


class CaixaFecharView(LoginRequiredMixin, View):
    template_name = 'caixa/fechar.html'

    def get(self, request):
        caixa = caixa_aberto_ou_redirect(request)
        if not caixa:
            return redirect('caixa:abrir')
        saldo = caixa.saldo_calculado()
        form = CaixaFechamentoForm(initial={'valor_fechamento_informado': saldo})
        return render(request, self.template_name, {'form': form, 'caixa': caixa, 'saldo_calculado': saldo})

    def post(self, request):
        caixa = caixa_aberto_ou_redirect(request)
        if not caixa:
            return redirect('caixa:abrir')
        form = CaixaFechamentoForm(request.POST, instance=caixa)
        saldo = caixa.saldo_calculado()
        if form.is_valid():
            try:
                caixa = caixa.fechar(
                    usuario=request.user,
                    valor_fechamento_informado=form.cleaned_data['valor_fechamento_informado'],
                    observacao_fechamento=form.cleaned_data.get('observacao_fechamento', ''),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Caixa fechado com sucesso.')
<<<<<<< HEAD
                registrar_log(request.user, 'fechamento de caixa', 'caixa', f'Caixa #{caixa.pk} fechado.', objeto=caixa, request=request)
=======
                registrar_log(request.user, 'fechamento de caixa', 'caixa', f'Caixa #{caixa.pk} fechado.', request=request)
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
                return redirect('caixa:historico')
        return render(request, self.template_name, {'form': form, 'caixa': caixa, 'saldo_calculado': saldo})


class CaixaHistoricoView(LoginRequiredMixin, ListView):
    model = Caixa
    template_name = 'caixa/historico.html'
    context_object_name = 'caixas'
    paginate_by = 15

    def get_queryset(self):
        queryset = Caixa.objects.select_related('usuario_abertura', 'usuario_fechamento')
        if not usuario_admin_ou_gerente(self.request.user):
            queryset = queryset.filter(usuario_abertura=self.request.user)

        data_inicial = parse_date(self.request.GET.get('data_inicial', '') or '')
        data_final = parse_date(self.request.GET.get('data_final', '') or '')
        status = self.request.GET.get('status', '').strip()
        usuario_id = self.request.GET.get('usuario', '').strip()

        if data_inicial:
            queryset = queryset.filter(data_abertura__date__gte=data_inicial)
        if data_final:
            queryset = queryset.filter(data_abertura__date__lte=data_final)
        if status in Caixa.Status.values:
            queryset = queryset.filter(status=status)
        if usuario_id and usuario_admin_ou_gerente(self.request.user):
            queryset = queryset.filter(usuario_abertura_id=usuario_id)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        User = get_user_model()
        context['filtros'] = self.request.GET
        context['status_choices'] = Caixa.Status.choices
        context['usuarios'] = User.objects.order_by('username') if usuario_admin_ou_gerente(self.request.user) else []
        context['pode_filtrar_usuario'] = usuario_admin_ou_gerente(self.request.user)
        return context
