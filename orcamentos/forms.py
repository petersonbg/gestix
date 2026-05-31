from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import ItemOrcamento, Orcamento


class OrcamentoForm(forms.ModelForm):
    class Meta:
        model = Orcamento
        fields = ['cliente', 'desconto', 'status']
        widgets = {
            'cliente': forms.Select(attrs={'class': 'form-select'}),
            'desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }


class ItemOrcamentoForm(forms.ModelForm):
    class Meta:
        model = ItemOrcamento
        fields = ['produto', 'quantidade', 'valor_unitario']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


class BaseItemOrcamentoFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return

        itens_validos = []
        subtotal = Decimal('0.00')
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get('DELETE'):
                continue
            produto = form.cleaned_data.get('produto')
            quantidade = form.cleaned_data.get('quantidade')
            valor_unitario = form.cleaned_data.get('valor_unitario')
            if produto and quantidade and valor_unitario is not None:
                itens_validos.append(form)
                subtotal += quantidade * valor_unitario

        if not itens_validos:
            raise forms.ValidationError('Inclua ao menos um item no orçamento.')

        desconto = self.instance.desconto or Decimal('0.00')
        if desconto > subtotal:
            raise forms.ValidationError('O desconto não pode ser maior que o subtotal dos itens.')


ItemOrcamentoFormSet = inlineformset_factory(
    Orcamento,
    ItemOrcamento,
    form=ItemOrcamentoForm,
    formset=BaseItemOrcamentoFormSet,
    extra=5,
    can_delete=False,
)
