from decimal import Decimal

from django import forms

from .models import Caixa, MovimentacaoCaixa


class CaixaAberturaForm(forms.ModelForm):
    class Meta:
        model = Caixa
        fields = ['valor_inicial', 'observacao_abertura']
        widgets = {
            'valor_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacao_abertura': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class CaixaFechamentoForm(forms.ModelForm):
    def clean_valor_fechamento_informado(self):
        valor = self.cleaned_data.get('valor_fechamento_informado')
        if valor is None:
            raise forms.ValidationError('Informe o valor contado para fechar o caixa.')
        if valor < Decimal('0.00'):
            raise forms.ValidationError('O valor contado não pode ser negativo.')
        return valor

    class Meta:
        model = Caixa
        fields = ['valor_fechamento_informado', 'observacao_fechamento']
        widgets = {
            'valor_fechamento_informado': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'observacao_fechamento': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class MovimentacaoCaixaForm(forms.ModelForm):
    class Meta:
        model = MovimentacaoCaixa
        fields = ['descricao', 'valor', 'forma_pagamento', 'observacao']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_valor(self):
        valor = self.cleaned_data['valor']
        if valor <= Decimal('0.00'):
            raise forms.ValidationError('Informe um valor maior que zero.')
        return valor

