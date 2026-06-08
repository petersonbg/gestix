from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.utils import registrar_log

from .forms import ContaReceberRecebimentoForm
from .models import ContaReceber


def usuario_admin_ou_gerente(user):
    return user.is_superuser or user.groups.filter(name__in=['Administrador', 'Gerente']).exists()


class ContaReceberQuerysetMixin:
    def get_base_queryset(self):
        queryset = ContaReceber.objects.select_related('cliente', 'venda', 'venda__usuario', 'ordem_servico', 'ordem_servico__responsavel')
        if not usuario_admin_ou_gerente(self.request.user):
            queryset = queryset.filter(Q(venda__usuario=self.request.user) | Q(ordem_servico__responsavel=self.request.user))
        return queryset


class ContaReceberListView(LoginRequiredMixin, ContaReceberQuerysetMixin, ListView):
    model = ContaReceber
    template_name = 'contas_receber/list.html'
    context_object_name = 'contas'
    paginate_by = 20
    modo = ''

    def get_queryset(self):
        queryset = self.get_base_queryset()
        query = self.request.GET.get('cliente', '').strip()
        venda = self.request.GET.get('venda', '').strip()
        status = self.request.GET.get('status', '').strip()
        data_inicial = self.request.GET.get('data_inicial', '').strip()
        data_final = self.request.GET.get('data_final', '').strip()
        periodo = self.request.GET.get('periodo', '').strip() or self.modo
        hoje = timezone.localdate()

        if query:
            queryset = queryset.filter(
                Q(cliente__nome__icontains=query)
                | Q(cliente__cpf_cnpj__icontains=query)
                | Q(cliente__telefone__icontains=query)
            )
        if venda.isdigit():
            queryset = queryset.filter(venda_id=int(venda))
        if status in {ContaReceber.Status.ATRASADA, 'atrasadas'}:
            queryset = queryset.filter(
                Q(status=ContaReceber.Status.ATRASADA)
                | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
            )
        elif status:
            queryset = queryset.filter(status=status)
        if data_inicial:
            queryset = queryset.filter(data_vencimento__gte=data_inicial)
        if data_final:
            queryset = queryset.filter(data_vencimento__lte=data_final)
        if periodo in {'vencidas', 'atrasadas'}:
            queryset = queryset.filter(
                Q(status=ContaReceber.Status.ATRASADA)
                | Q(status=ContaReceber.Status.ABERTA, data_vencimento__lt=hoje)
            )
        elif periodo == 'hoje':
            queryset = queryset.filter(status=ContaReceber.Status.ABERTA, data_vencimento=hoje)
        elif periodo == 'a_vencer':
            queryset = queryset.filter(status=ContaReceber.Status.ABERTA, data_vencimento__gt=hoje)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filtros'] = self.request.GET
        context['status_choices'] = ContaReceber.Status.choices
        context['periodo'] = self.request.GET.get('periodo', '').strip() or self.modo
        return context


class ContaReceberDetailView(LoginRequiredMixin, ContaReceberQuerysetMixin, DetailView):
    model = ContaReceber
    template_name = 'contas_receber/detail.html'
    context_object_name = 'conta'

    def get_queryset(self):
        return self.get_base_queryset()


class ContaReceberReceberView(LoginRequiredMixin, ContaReceberQuerysetMixin, View):
    template_name = 'contas_receber/receber.html'
    success_url = reverse_lazy('contas_receber:list')

    def get_conta(self):
        return get_object_or_404(self.get_base_queryset(), pk=self.kwargs['pk'])

    def get(self, request, pk):
        conta = self.get_conta()
        form = ContaReceberRecebimentoForm(instance=conta, conta=conta)
        return render(request, self.template_name, {'conta': conta, 'form': form})

    def post(self, request, pk):
        conta = self.get_conta()
        form = ContaReceberRecebimentoForm(request.POST, instance=conta, conta=conta)
        if form.is_valid():
            try:
                conta.receber(
                    usuario=request.user,
                    valor_recebido=form.cleaned_data['valor_recebido'],
                    forma_recebimento=form.cleaned_data['forma_recebimento'],
                    data_pagamento=form.cleaned_data['data_pagamento'],
                    observacao=form.cleaned_data.get('observacao', ''),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Parcela recebida e lançada no caixa com sucesso.')
                registrar_log(
                    request.user,
                    'recebimento de parcela',
                    'contas_receber',
                    f'Parcela {conta.numero_parcela}/{conta.total_parcelas} de {conta.referencia} recebida.',
                    request=request,
                )
                return redirect(conta.get_absolute_url())
        return render(request, self.template_name, {'conta': conta, 'form': form})
