from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from .models import ItemProdutoOS, ItemServicoOS, OrdemServico


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ['cliente', 'data_previsao', 'responsavel', 'descricao_problema', 'diagnostico', 'solucao', 'observacoes', 'desconto']
        widgets = {
            'cliente': forms.HiddenInput(),
            'data_previsao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'descricao_problema': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'solucao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'desconto': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
        }

    def clean_cliente(self):
        cliente = self.cleaned_data.get('cliente')
        if not cliente or not cliente.ativo:
            raise forms.ValidationError('Selecione um cliente ativo para a ordem de serviço.')
        return cliente


class ItemServicoOSForm(forms.ModelForm):
    class Meta:
        model = ItemServicoOS
        fields = ['servico', 'descricao', 'quantidade', 'valor_unitario']
        widgets = {
            'servico': forms.HiddenInput(), 'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control item-quantidade', 'min': 1}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control item-valor', 'min': 0, 'step': '0.01'}),
        }


class ItemProdutoOSForm(forms.ModelForm):
    class Meta:
        model = ItemProdutoOS
        fields = ['produto', 'quantidade', 'valor_unitario']
        widgets = {
            'produto': forms.HiddenInput(),
            'quantidade': forms.NumberInput(attrs={'class': 'form-control item-quantidade', 'min': 1}),
            'valor_unitario': forms.NumberInput(attrs={'class': 'form-control item-valor', 'min': 0, 'step': '0.01'}),
        }


ServicoFormSet = inlineformset_factory(OrdemServico, ItemServicoOS, form=ItemServicoOSForm, extra=0, can_delete=True)
ProdutoFormSet = inlineformset_factory(OrdemServico, ItemProdutoOS, form=ItemProdutoOSForm, extra=0, can_delete=True)


class AlterarStatusForm(forms.Form):
    status = forms.ChoiceField(choices=OrdemServico.Status.choices, widget=forms.Select(attrs={'class': 'form-select'}))


class PagamentoOSForm(forms.Form):
    forma_pagamento = forms.ChoiceField(choices=OrdemServico.FormaPagamento.choices, widget=forms.Select(attrs={'class': 'form-select'}))
    valor = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'), widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}))
    parcelas = forms.IntegerField(min_value=1, initial=1, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))
    primeiro_vencimento = forms.DateField(required=False, widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    intervalo = forms.IntegerField(min_value=1, initial=30, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))

    def clean(self):
        dados = super().clean()
        if dados.get('forma_pagamento') == OrdemServico.FormaPagamento.CREDIARIO and not dados.get('primeiro_vencimento'):
            self.add_error('primeiro_vencimento', 'Informe o primeiro vencimento do crediário.')
        return dados
