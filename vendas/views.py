from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView

from accounts.utils import registrar_log
from administracao.services import contexto_documento_impresso
from clientes.models import Cliente
from produtos.models import Produto

from .forms import ItemVendaFormSet, VendaCancelamentoForm, VendaForm
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


class ClienteBuscaView(LoginRequiredMixin, View):
    def get(self, request):
        query = request.GET.get('q', '').strip()
        clientes = Cliente.objects.filter(ativo=True)
        if len(query) >= 2:
            clientes = clientes.filter(
                Q(nome__icontains=query)
                | Q(cpf_cnpj__icontains=query)
                | Q(telefone__icontains=query)
            ).annotate(
                prioridade_busca=Case(
                    When(nome__iexact=query, then=Value(0)),
                    When(cpf_cnpj__exact=query, then=Value(0)),
                    When(telefone__exact=query, then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by('prioridade_busca', 'nome')
        else:
            clientes = clientes.none()

        data = [
            {
                'id': cliente.pk,
                'nome': cliente.nome,
                'cpf_cnpj': cliente.cpf_cnpj or '',
                'telefone': cliente.telefone or '',
                'email': cliente.email or '',
                'endereco': cliente.endereco or '',
                'inscricao_estadual': cliente.inscricao_estadual or '',
            }
            for cliente in clientes[:10]
        ]
        return JsonResponse({'results': data})


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
        status = self.request.GET.get('status', 'ativas')
        if status == 'canceladas':
            queryset = queryset.filter(status=Venda.Status.CANCELADA)
        elif status != 'todas':
            queryset = queryset.exclude(status=Venda.Status.CANCELADA)
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
        context['status_filtro'] = self.request.GET.get('status', 'ativas')
        return context


class VendaDetailView(LoginRequiredMixin, DetailView):
    model = Venda
    template_name = 'vendas/venda_detail.html'
    context_object_name = 'venda'

    def get_queryset(self):
        return super().get_queryset().select_related('cliente', 'usuario').prefetch_related('itens__produto')


class VendaCreateView(LoginRequiredMixin, View):
    template_name = 'vendas/venda_form.html'

    def get_selected_cliente(self, form):
        cliente = form.cleaned_data.get('cliente') if hasattr(form, 'cleaned_data') else None
        if cliente:
            return cliente
        cliente_id = form.data.get('cliente') if form.is_bound else form.initial.get('cliente')
        if cliente_id:
            return Cliente.objects.filter(pk=cliente_id, ativo=True).first()
        return None

    def get_context_data(self, form, formset, **extra):
        context = {
            'form': form,
            'formset': formset,
            'selected_cliente': self.get_selected_cliente(form),
        }
        context.update(extra)
        return context

    def get(self, request):
        form = VendaForm(initial={'status': Venda.Status.RASCUNHO})
        formset = ItemVendaFormSet()
        return render(request, self.template_name, self.get_context_data(form, formset))

    def post(self, request):
        form = VendaForm(request.POST)
        form_is_valid = form.is_valid()
        venda = form.save(commit=False) if form_is_valid else Venda()
        venda.usuario = request.user
        formset = ItemVendaFormSet(request.POST, instance=venda)

        if form_is_valid and formset.is_valid():
            venda.status = Venda.Status.RASCUNHO
            venda.save()
            formset.instance = venda
            formset.save()
            venda.recalcular_totais()
            messages.success(request, 'Venda salva como rascunho. Finalize-a para movimentar estoque e financeiro.')
            registrar_log(
                request.user,
                'criação de venda',
                'vendas',
                f'Venda #{venda.pk} criada como rascunho.',
                request=request,
            )
            return redirect(venda.get_absolute_url())

        return render(request, self.template_name, self.get_context_data(form, formset))


class VendaUpdateView(VendaCreateView):
    def obter_venda(self, pk):
        return get_object_or_404(Venda.objects.prefetch_related('itens'), pk=pk)

    def get(self, request, pk):
        venda = self.obter_venda(pk)
        if venda.status != Venda.Status.RASCUNHO:
            messages.error(request, 'Somente vendas em rascunho podem ser editadas.')
            return redirect(venda.get_absolute_url())
        form = VendaForm(instance=venda)
        formset = ItemVendaFormSet(instance=venda)
        return render(request, self.template_name, self.get_context_data(form, formset, venda=venda, is_editing=True))

    def post(self, request, pk):
        venda = self.obter_venda(pk)
        if venda.status != Venda.Status.RASCUNHO:
            messages.error(request, 'Somente vendas em rascunho podem ser editadas.')
            return redirect(venda.get_absolute_url())

        form = VendaForm(request.POST, instance=venda)
        formset = ItemVendaFormSet(request.POST, instance=venda)
        if form.is_valid() and formset.is_valid():
            venda = form.save(commit=False)
            venda.status = Venda.Status.RASCUNHO
            venda.save()
            formset.save()
            venda.recalcular_totais()
            messages.success(request, 'Rascunho da venda atualizado com sucesso.')
            registrar_log(request.user, 'edição de venda', 'vendas', f'Venda #{venda.pk} atualizada.', request=request)
            return redirect(venda.get_absolute_url())

        return render(request, self.template_name, self.get_context_data(form, formset, venda=venda, is_editing=True))


class VendaCancelarView(LoginRequiredMixin, View):
    template_name = 'vendas/venda_cancelar.html'

    def get_venda(self, pk):
        return get_object_or_404(Venda.objects.select_related('cliente'), pk=pk)

    def get(self, request, pk):
        venda = self.get_venda(pk)
        if venda.status != Venda.Status.RASCUNHO:
            messages.error(request, 'Somente vendas em rascunho podem ser canceladas.')
            return redirect(venda.get_absolute_url())
        return render(request, self.template_name, {'venda': venda, 'form': VendaCancelamentoForm()})

    def post(self, request, pk):
        venda = self.get_venda(pk)
        form = VendaCancelamentoForm(request.POST)
        if venda.status != Venda.Status.RASCUNHO:
            messages.error(request, 'Somente vendas em rascunho podem ser canceladas.')
            return redirect(venda.get_absolute_url())
        if form.is_valid():
            motivo = form.cleaned_data['motivo']
            try:
                venda.cancelar(usuario=request.user, motivo=motivo)
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                registrar_log(
                    request.user,
                    'cancelamento de venda',
                    'vendas',
                    f'Venda #{venda.pk} cancelada. Motivo: {motivo}',
                    request=request,
                )
                messages.success(request, 'Venda em rascunho cancelada sem movimentar estoque ou financeiro.')
                return redirect(venda.get_absolute_url())
        return render(request, self.template_name, {'venda': venda, 'form': form})


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
        return super().get_queryset().select_related('cliente', 'usuario').prefetch_related('itens__produto', 'contas_receber')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(contexto_documento_impresso())
        context['vendedor_nome'] = formatar_nome_vendedor(self.object.usuario)
        return context
