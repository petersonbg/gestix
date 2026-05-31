import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.utils import registrar_log
from produtos.models import Produto

from .forms import ItemVendaFormSet, VendaForm
from .models import Venda


def formatar_nome_vendedor(usuario):
    if not usuario:
        return '-'

    nomes = [parte for parte in usuario.get_full_name().split() if parte]
    if len(nomes) >= 2:
        return f'{nomes[0]} {nomes[-1]}'
    if len(nomes) == 1:
        return nomes[0]
    return usuario.get_username() or '-'


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


class VendaListView(LoginRequiredMixin, ListView):
    model = Venda
    template_name = 'vendas/venda_list.html'
    context_object_name = 'vendas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'usuario')
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


class VendaDetailView(LoginRequiredMixin, DetailView):
    model = Venda
    template_name = 'vendas/venda_detail.html'
    context_object_name = 'venda'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'usuario').prefetch_related('itens__produto')


class VendaCreateView(LoginRequiredMixin, View):
    template_name = 'vendas/venda_form.html'

    def get(self, request):
        form = VendaForm(initial={'status': Venda.Status.RASCUNHO})
        formset = ItemVendaFormSet()
        return render(request, self.template_name, {'form': form, 'formset': formset})

    def post(self, request):
        form = VendaForm(request.POST)
        venda = form.save(commit=False) if form.is_valid() else Venda()
        venda.usuario = request.user
        formset = ItemVendaFormSet(request.POST, instance=venda)

        if form.is_valid() and formset.is_valid():
            status_solicitado = venda.status
            if status_solicitado == Venda.Status.FINALIZADA:
                venda.status = Venda.Status.RASCUNHO
            venda.save()
            formset.instance = venda
            formset.save()
            venda.recalcular_totais()

            if status_solicitado == Venda.Status.FINALIZADA:
                try:
                    venda.finalizar(usuario=request.user)
                except ValidationError as exc:
                    form.add_error(None, exc)
                    return render(request, self.template_name, {'form': form, 'formset': formset})
                messages.success(request, 'Venda registrada, finalizada e estoque atualizado com sucesso.')
                registrar_log(request.user, 'criação de venda', 'vendas', f'Venda #{venda.pk} criada e finalizada.', request=request)
            else:
                venda.status = status_solicitado
                venda.save(update_fields=['status'])
                messages.success(request, 'Venda registrada com sucesso.')
                registrar_log(request.user, 'criação de venda', 'vendas', f'Venda #{venda.pk} criada como {venda.get_status_display()}.', request=request)

            return redirect(venda.get_absolute_url())

        return render(request, self.template_name, {'form': form, 'formset': formset})


class VendaFinalizarView(LoginRequiredMixin, View):
    success_url = reverse_lazy('vendas:list')

    def post(self, request, pk):
        venda = get_object_or_404(Venda, pk=pk)
        try:
            venda.finalizar(usuario=request.user)
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, 'message') else exc.messages[0])
        else:
            messages.success(request, 'Venda finalizada e estoque atualizado com sucesso.')
            registrar_log(request.user, 'finalização de venda', 'vendas', f'Venda #{venda.pk} finalizada com baixa de estoque.', request=request)
        return redirect(venda.get_absolute_url())


class VendaPrintView(LoginRequiredMixin, DetailView):
    model = Venda
    template_name = 'vendas/imprimir_recibo.html'
    context_object_name = 'venda'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'usuario').prefetch_related('itens__produto')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['logo_url'] = os.getenv('GESTIX_LOGO_URL', '').strip()
        context['vendedor_nome'] = formatar_nome_vendedor(self.object.usuario)
        return context
