from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from administracao.models import CategoriaProduto

from .forms import ProdutoForm
from .models import Produto


class ProdutoListView(LoginRequiredMixin, ListView):
    model = Produto
    template_name = 'produtos/produto_list.html'
    context_object_name = 'produtos'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('fornecedor', 'categoria')
        query = self.request.GET.get('q', '').strip()
        categoria = self.request.GET.get('categoria', '').strip()
        if categoria.isdigit():
            queryset = queryset.filter(categoria_id=categoria)
        if query:
            queryset = queryset.filter(
                Q(nome__icontains=query)
                | Q(codigo_interno__icontains=query)
                | Q(codigo_barras__icontains=query)
                | Q(chassi__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        context['categoria_selecionada'] = self.request.GET.get('categoria', '').strip()
        context['categorias'] = CategoriaProduto.objects.filter(ativo=True).order_by('nome')
        return context


class ProdutoDetailView(LoginRequiredMixin, DetailView):
    model = Produto
    template_name = 'produtos/produto_detail.html'
    context_object_name = 'produto'

    def get_queryset(self):
        return super().get_queryset().select_related('fornecedor', 'categoria')


class ProdutoCreateView(LoginRequiredMixin, CreateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'produtos/produto_form.html'


class ProdutoUpdateView(LoginRequiredMixin, UpdateView):
    model = Produto
    form_class = ProdutoForm
    template_name = 'produtos/produto_form.html'


class ProdutoDeleteView(LoginRequiredMixin, DeleteView):
    model = Produto
    template_name = 'produtos/produto_confirm_delete.html'
    context_object_name = 'produto'
    success_url = reverse_lazy('produtos:list')
