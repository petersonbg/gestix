from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, FormView, ListView

from accounts.utils import registrar_log
from produtos.models import Produto

from .forms import MovimentacaoEstoqueForm
from .models import MovimentacaoEstoque


class EstoqueProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'estoque/produto_estoque_list.html'
    context_object_name = 'produtos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('fornecedor').order_by('nome')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(nome__icontains=query) | Q(codigo_interno__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class MovimentacaoEstoqueCreateView(LoginRequiredMixin, FormView):
    template_name = 'estoque/movimentacao_form.html'
    form_class = MovimentacaoEstoqueForm
    success_url = reverse_lazy('estoque:list')

    def form_valid(self, form):
        try:
            movimentacao = MovimentacaoEstoque.registrar(
                produto=form.cleaned_data['produto'],
                tipo_movimentacao=form.cleaned_data['tipo_movimentacao'],
                quantidade=form.cleaned_data['quantidade'],
                origem=form.cleaned_data['origem'],
                observacao=form.cleaned_data['observacao'],
                usuario=self.request.user,
            )
        except ValidationError as exc:
            if hasattr(exc, 'message_dict'):
                for field, errors in exc.message_dict.items():
                    form.add_error(field if field in form.fields else None, errors)
            else:
                form.add_error(None, exc)
            return self.form_invalid(form)

        messages.success(self.request, 'Movimentação registrada e saldo atualizado com sucesso.')
        registrar_log(
            self.request.user,
            'movimentação manual de estoque',
            'estoque',
            f'Movimentação #{movimentacao.pk} registrada para o produto {movimentacao.produto}.',
            request=self.request,
        )
        return redirect('estoque:produto_historico', produto_pk=movimentacao.produto_id)


class ProdutoHistoricoEstoqueView(LoginRequiredMixin, DetailView):
    model = Produto
    template_name = 'estoque/produto_historico.html'
    context_object_name = 'produto'
    pk_url_kwarg = 'produto_pk'

    def get_queryset(self):
        return super().get_queryset().select_related('fornecedor')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movimentacoes'] = self.object.movimentacoes_estoque.select_related('usuario')
        return context

