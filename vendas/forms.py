from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from clientes.models import Cliente

from .models import ItemVenda, Venda


class VendaForm(forms.ModelForm):
    cliente = forms.ModelChoiceField(
        queryset=Cliente.objects.filter(ativo=True),
        error_messages={
            'required': 'Selecione um cliente para continuar.',
            'invalid_choice': 'Selecione um cliente ativo para continuar.',
        },
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in ['quantidade_parcelas', 'data_primeiro_vencimento', 'intervalo_parcelas', 'valor_entrada', 'observacoes_crediario']:
            self.fields[field_name].required = False

    class Meta:
        model = Venda
        fields = [
            'cliente',
            'desconto',
            'forma_pagamento',
            'quantidade_parcelas',
            'data_primeiro_vencimento',
            'intervalo_parcelas',
            'valor_entrada',
            'observacoes_crediario',
        ]
        widgets = {
            'desconto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'quantidade_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'data_primeiro_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'intervalo_parcelas': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor_entrada': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacoes_crediario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['quantidade_parcelas'] = cleaned_data.get('quantidade_parcelas') or 1
        cleaned_data['intervalo_parcelas'] = cleaned_data.get('intervalo_parcelas') or 30
        cleaned_data['valor_entrada'] = cleaned_data.get('valor_entrada') or Decimal('0.00')
        if cleaned_data.get('forma_pagamento') == Venda.FormaPagamento.CREDIARIO:
            if not cleaned_data.get('cliente'):
                self.add_error('cliente', 'Selecione um cliente válido para venda no crediário.')
            if not cleaned_data.get('data_primeiro_vencimento'):
                self.add_error('data_primeiro_vencimento', 'Informe a data do primeiro vencimento.')
            if (cleaned_data.get('quantidade_parcelas') or 0) < 1:
                self.add_error('quantidade_parcelas', 'Informe ao menos uma parcela.')
            if (cleaned_data.get('intervalo_parcelas') or 0) < 1:
                self.add_error('intervalo_parcelas', 'O intervalo entre parcelas deve ser maior que zero.')
        return cleaned_data


class ItemVendaForm(forms.ModelForm):
    class Meta:
        model = ItemVenda
        fields = ['produto', 'quantidade', 'valor_unitario']
        widgets = {
            'produto': forms.Select(attrs={'class': 'form-select'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }


class BaseItemVendaFormSet(BaseInlineFormSet):
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
            raise forms.ValidationError('Inclua ao menos um item na venda.')

        desconto = self.instance.desconto or Decimal('0.00')
        if desconto > subtotal:
            raise forms.ValidationError('O desconto não pode ser maior que o subtotal dos itens.')

        quantidades_por_produto = {}
        formularios_por_produto = {}
        for form in itens_validos:
            produto = form.cleaned_data['produto']
            quantidade = form.cleaned_data['quantidade']
            quantidades_por_produto[produto.pk] = quantidades_por_produto.get(produto.pk, 0) + quantidade
            formularios_por_produto.setdefault(produto.pk, []).append(form)

        for produto_id, quantidade_total in quantidades_por_produto.items():
            produto = formularios_por_produto[produto_id][0].cleaned_data['produto']
            if quantidade_total > produto.estoque_atual:
                for form in formularios_por_produto[produto_id]:
                    form.add_error(
                        'quantidade',
                        f'Estoque insuficiente. Disponível: {produto.estoque_atual}.',
                    )


ItemVendaFormSet = inlineformset_factory(
    Venda,
    ItemVenda,
    form=ItemVendaForm,
    formset=BaseItemVendaFormSet,
    extra=5,
    can_delete=False,
)


class VendaCancelamentoForm(forms.Form):
    motivo = forms.CharField(
        label='Motivo do cancelamento',
        min_length=3,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 4,
            'placeholder': 'Informe por que esta venda em rascunho está sendo cancelada.',
        }),
    )
