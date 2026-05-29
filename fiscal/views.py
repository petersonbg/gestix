from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from .forms import ConfirmarNotaFiscalForm, NFeUploadForm
from .models import NotaFiscalEntrada
from .services import confirmar_nota, importar_nfe


class NotaFiscalEntradaListView(LoginRequiredMixin, ListView):
    model = NotaFiscalEntrada
    template_name = 'fiscal/nota_list.html'
    context_object_name = 'notas'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('fornecedor')
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(
                Q(chave_acesso__icontains=query)
                | Q(numero__icontains=query)
                | Q(emitente_razao_social__icontains=query)
                | Q(emitente_cnpj__icontains=query)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class NotaFiscalEntradaDetailView(LoginRequiredMixin, DetailView):
    model = NotaFiscalEntrada
    template_name = 'fiscal/nota_detail.html'
    context_object_name = 'nota'

    def get_queryset(self):
        return super().get_queryset().select_related('fornecedor').prefetch_related('itens__produto')


class NFeUploadView(LoginRequiredMixin, View):
    template_name = 'fiscal/upload.html'

    def get(self, request):
        return render(request, self.template_name, {'form': NFeUploadForm()})

    def post(self, request):
        form = NFeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                nota = importar_nfe(form.cleaned_data['arquivo_xml'])
            except ValidationError as exc:
                form.add_error('arquivo_xml', exc.message if hasattr(exc, 'message') else exc.messages[0])
            else:
                messages.success(request, 'NF-e importada com sucesso. Revise os itens para confirmar a entrada no estoque.')
                return redirect(nota.get_absolute_url())
        return render(request, self.template_name, {'form': form})


class NotaFiscalEntradaConfirmView(LoginRequiredMixin, View):
    template_name = 'fiscal/confirmar.html'

    def get(self, request, pk):
        nota = get_object_or_404(NotaFiscalEntrada.objects.prefetch_related('itens'), pk=pk)
        form = ConfirmarNotaFiscalForm(nota=nota)
        return render(request, self.template_name, {'nota': nota, 'form': form})

    def post(self, request, pk):
        nota = get_object_or_404(NotaFiscalEntrada.objects.prefetch_related('itens'), pk=pk)
        form = ConfirmarNotaFiscalForm(request.POST, nota=nota)
        if form.is_valid():
            try:
                confirmar_nota(nota, form.get_item_bindings(), usuario=request.user)
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, 'message') else exc.messages[0])
            else:
                messages.success(request, 'Entrada no estoque gerada com sucesso.')
                return redirect(nota.get_absolute_url())
        return render(request, self.template_name, {'nota': nota, 'form': form})
