from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.utils import registrar_log
from produtos.models import Produto

from .forms import ItemOrcamentoFormSet, OrcamentoForm
from .models import Orcamento


class ProdutoBuscaView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        produtos = Produto.objects.filter(ativo=True)
        if query:
            produtos = produtos.filter(
                Q(nome__icontains=query)
                | Q(codigo_interno__icontains=query)
                | Q(codigo_barras__icontains=query)
            )
        else:
            produtos = produtos.none()

        data = [
            {
                'id': produto.pk,
                'nome': produto.nome,
                'codigo_interno': produto.codigo_interno,
                'codigo_barras': produto.codigo_barras or '',
                'preco_venda': str(produto.preco_venda),
                'estoque_atual': produto.estoque_atual,
            }
            for produto in produtos.order_by('nome')[:10]
        ]
        return JsonResponse({'results': data})


class OrcamentoListView(LoginRequiredMixin, ListView):
    model = Orcamento
    template_name = 'orcamentos/orcamento_list.html'
    context_object_name = 'orcamentos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'usuario', 'venda')
        query = self.request.GET.get('q', '').strip()
        if query:
            filters = Q(cliente__nome__icontains=query)
            if query.isdigit():
                filters |= Q(id=int(query))
            queryset = queryset.filter(filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class OrcamentoDetailView(LoginRequiredMixin, DetailView):
    model = Orcamento
    template_name = 'orcamentos/orcamento_detail.html'
    context_object_name = 'orcamento'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'usuario', 'venda').prefetch_related('itens__produto')


class OrcamentoPrintView(LoginRequiredMixin, DetailView):
    model = Orcamento
    template_name = 'orcamentos/imprimir_orcamento.html'
    context_object_name = 'orcamento'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'usuario').prefetch_related('itens__produto')


class OrcamentoCreateView(LoginRequiredMixin, View):
    template_name = 'orcamentos/orcamento_form.html'

    def get(self, request):
        form = OrcamentoForm(initial={'status': Orcamento.Status.ABERTO})
        formset = ItemOrcamentoFormSet()
        return render(request, self.template_name, {'form': form, 'formset': formset})

    def post(self, request):
        form = OrcamentoForm(request.POST)
        orcamento = form.save(commit=False) if form.is_valid() else Orcamento()
        orcamento.usuario = request.user
        formset = ItemOrcamentoFormSet(request.POST, instance=orcamento)

        if form.is_valid() and formset.is_valid():
            orcamento.save()
            formset.instance = orcamento
            formset.save()
            orcamento.recalcular_totais()
            messages.success(request, 'Orçamento registrado com sucesso.')
            registrar_log(request.user, 'criação de orçamento', 'orcamentos', f'Orçamento #{orcamento.pk} criado.', request=request)
            return redirect(orcamento.get_absolute_url())

        return render(request, self.template_name, {'form': form, 'formset': formset})


class OrcamentoConverterView(LoginRequiredMixin, View):
    def post(self, request, pk):
        orcamento = get_object_or_404(Orcamento, pk=pk)
        try:
            venda = orcamento.converter_em_venda(usuario=request.user)
        except ValidationError as exc:
            message = exc.message if hasattr(exc, 'message') else exc.messages[0]
            messages.error(request, message)
            return redirect(orcamento.get_absolute_url())

        messages.success(request, f'Orçamento convertido na venda #{venda.pk} e estoque atualizado com sucesso.')
        registrar_log(request.user, 'conversão de orçamento em venda', 'orcamentos', f'Orçamento #{orcamento.pk} convertido na venda #{venda.pk}.', request=request)
        return redirect(venda.get_absolute_url())
