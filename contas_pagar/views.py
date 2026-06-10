from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from accounts.utils import registrar_log

from .forms import ContaPagarCancelamentoForm, ContaPagarForm, ContaPagarPagamentoForm
from .models import CategoriaDespesa, ContaPagar


def usuario_pode_acessar_contas_pagar(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['Administrador', 'Gerente']).exists()


class ContaPagarPermissaoMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        return usuario_pode_acessar_contas_pagar(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Acesso inválido para o módulo Contas a pagar.')
        return redirect('dashboard')


class ContaPagarQuerysetMixin:
    def get_base_queryset(self):
        return ContaPagar.objects.select_related('fornecedor', 'categoria', 'usuario_criacao', 'usuario_pagamento')


class ContaPagarListView(ContaPagarPermissaoMixin, ContaPagarQuerysetMixin, ListView):
    model = ContaPagar
    template_name = 'contas_pagar/list.html'
    context_object_name = 'contas'
    paginate_by = 20

    def get_queryset(self):
        queryset = self.get_base_queryset()
        fornecedor = self.request.GET.get('fornecedor', '').strip()
        categoria = self.request.GET.get('categoria', '').strip()
        status = self.request.GET.get('status', '').strip()
        data_inicial = self.request.GET.get('data_inicial', '').strip()
        data_final = self.request.GET.get('data_final', '').strip()
        periodo = self.request.GET.get('periodo', '').strip()
        hoje = timezone.localdate()

        if fornecedor:
            queryset = queryset.filter(
                Q(fornecedor__razao_social__icontains=fornecedor)
                | Q(fornecedor__nome_fantasia__icontains=fornecedor)
                | Q(fornecedor__cnpj__icontains=fornecedor)
            )
        if categoria:
            queryset = queryset.filter(categoria_id=categoria)
        if status in {ContaPagar.Status.ATRASADA, 'atrasadas'}:
            queryset = queryset.filter(
                Q(status=ContaPagar.Status.ATRASADA)
                | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
            )
        elif status:
            queryset = queryset.filter(status=status)
        if data_inicial:
            queryset = queryset.filter(data_vencimento__gte=data_inicial)
        if data_final:
            queryset = queryset.filter(data_vencimento__lte=data_final)
        if periodo in {'vencidas', 'atrasadas'}:
            queryset = queryset.filter(
                Q(status=ContaPagar.Status.ATRASADA)
                | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
            )
        elif periodo == 'hoje':
            queryset = queryset.filter(status=ContaPagar.Status.ABERTA, data_vencimento=hoje)
        elif periodo == 'a_vencer':
            queryset = queryset.filter(status=ContaPagar.Status.ABERTA, data_vencimento__gt=hoje)
        elif periodo == 'proximos_7':
            queryset = queryset.filter(status=ContaPagar.Status.ABERTA, data_vencimento__range=(hoje, hoje + timedelta(days=7)))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoje = timezone.localdate()
        mes_inicio = hoje.replace(day=1)
        proximos_7 = hoje + timedelta(days=7)
        context['filtros'] = self.request.GET
        context['status_choices'] = ContaPagar.Status.choices
        context['categorias'] = CategoriaDespesa.objects.filter(ativo=True)
        context['total_aberto'] = ContaPagar.objects.filter(status=ContaPagar.Status.ABERTA).aggregate(total=Sum('valor'))['total'] or 0
        context['total_pago_mes'] = ContaPagar.objects.filter(status=ContaPagar.Status.PAGA, data_pagamento__gte=mes_inicio, data_pagamento__lte=hoje).aggregate(total=Sum('valor_pago'))['total'] or 0
        context['total_atrasado'] = ContaPagar.objects.filter(
            Q(status=ContaPagar.Status.ATRASADA) | Q(status=ContaPagar.Status.ABERTA, data_vencimento__lt=hoje)
        ).aggregate(total=Sum('valor'))['total'] or 0
        context['total_proximos_7'] = ContaPagar.objects.filter(status=ContaPagar.Status.ABERTA, data_vencimento__range=(hoje, proximos_7)).aggregate(total=Sum('valor'))['total'] or 0
        return context


class ContaPagarCreateView(ContaPagarPermissaoMixin, CreateView):
    model = ContaPagar
    form_class = ContaPagarForm
    template_name = 'contas_pagar/form.html'
    success_url = reverse_lazy('contas_pagar:list')

    def form_valid(self, form):
        form.instance.usuario_criacao = self.request.user
        messages.success(self.request, 'Conta a pagar cadastrada com sucesso.')
        registrar_log(self.request.user, 'criação de conta a pagar', 'contas_pagar', f'Conta {form.instance.descricao} criada.', request=self.request)
        return super().form_valid(form)


class ContaPagarUpdateView(ContaPagarPermissaoMixin, ContaPagarQuerysetMixin, UpdateView):
    model = ContaPagar
    form_class = ContaPagarForm
    template_name = 'contas_pagar/form.html'

    def get_queryset(self):
        return self.get_base_queryset().exclude(status__in=[ContaPagar.Status.PAGA, ContaPagar.Status.CANCELADA])

    def form_valid(self, form):
        messages.success(self.request, 'Conta a pagar atualizada com sucesso.')
        return super().form_valid(form)


class ContaPagarDetailView(ContaPagarPermissaoMixin, ContaPagarQuerysetMixin, DetailView):
    model = ContaPagar
    template_name = 'contas_pagar/detail.html'
    context_object_name = 'conta'

    def get_queryset(self):
        return self.get_base_queryset()


class ContaPagarPagamentoView(ContaPagarPermissaoMixin, ContaPagarQuerysetMixin, View):
    template_name = 'contas_pagar/pagar.html'

    def get_conta(self):
        return get_object_or_404(self.get_base_queryset(), pk=self.kwargs['pk'])

    def get(self, request, pk):
        conta = self.get_conta()
        form = ContaPagarPagamentoForm(instance=conta, conta=conta)
        return render(request, self.template_name, {'conta': conta, 'form': form})

    def post(self, request, pk):
        conta = self.get_conta()
        form = ContaPagarPagamentoForm(request.POST, instance=conta, conta=conta)
        if form.is_valid():
            try:
                conta.pagar(
                    usuario=request.user,
                    valor_pago=form.cleaned_data['valor_pago_informado'],
                    forma_pagamento=form.cleaned_data['forma_pagamento'],
                    data_pagamento=form.cleaned_data['data_pagamento'],
                    observacao=form.cleaned_data.get('observacao', ''),
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Conta paga com sucesso.')
                registrar_log(request.user, 'pagamento de conta', 'contas_pagar', f'Conta #{conta.pk} paga.', request=request)
                return redirect(conta.get_absolute_url())
        return render(request, self.template_name, {'conta': conta, 'form': form})


class ContaPagarCancelamentoView(ContaPagarPermissaoMixin, ContaPagarQuerysetMixin, View):
    template_name = 'contas_pagar/cancelar.html'

    def get_conta(self):
        return get_object_or_404(self.get_base_queryset(), pk=self.kwargs['pk'])

    def get(self, request, pk):
        conta = self.get_conta()
        form = ContaPagarCancelamentoForm()
        return render(request, self.template_name, {'conta': conta, 'form': form})

    def post(self, request, pk):
        conta = self.get_conta()
        form = ContaPagarCancelamentoForm(request.POST)
        if form.is_valid():
            try:
                conta.cancelar(observacao=form.cleaned_data.get('observacao', ''))
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(request, 'Conta cancelada com sucesso.')
                registrar_log(request.user, 'cancelamento de conta', 'contas_pagar', f'Conta #{conta.pk} cancelada.', request=request)
                return redirect(conta.get_absolute_url())
        return render(request, self.template_name, {'conta': conta, 'form': form})
