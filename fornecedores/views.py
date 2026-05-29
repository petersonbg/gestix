from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import FornecedorForm
from .models import Fornecedor


class FornecedorListView(LoginRequiredMixin, ListView):
    model = Fornecedor
    template_name = 'fornecedores/fornecedor_list.html'
    context_object_name = 'fornecedores'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(razao_social__icontains=query)
                | Q(nome_fantasia__icontains=query)
                | Q(cnpj__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class FornecedorDetailView(LoginRequiredMixin, DetailView):
    model = Fornecedor
    template_name = 'fornecedores/fornecedor_detail.html'
    context_object_name = 'fornecedor'


class FornecedorCreateView(LoginRequiredMixin, CreateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'fornecedores/fornecedor_form.html'


class FornecedorUpdateView(LoginRequiredMixin, UpdateView):
    model = Fornecedor
    form_class = FornecedorForm
    template_name = 'fornecedores/fornecedor_form.html'


class FornecedorDeleteView(LoginRequiredMixin, DeleteView):
    model = Fornecedor
    template_name = 'fornecedores/fornecedor_confirm_delete.html'
    context_object_name = 'fornecedor'
    success_url = reverse_lazy('fornecedores:list')
