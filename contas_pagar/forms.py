from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ContaPagar


class ContaPagarForm(forms.ModelForm):
    class Meta:
        model = ContaPagar
        fields = ['descricao', 'fornecedor', 'categoria', 'data_emissao', 'data_vencimento', 'valor', 'observacao']
        widgets = {
            'descricao': forms.TextInput(attrs={'class': 'form-control'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'data_emissao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'data_vencimento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'valor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


class ContaPagarPagamentoForm(forms.ModelForm):
    valor_pago_informado = forms.DecimalField(
        label='Valor pago',
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    )

    class Meta:
        model = ContaPagar
        fields = ['data_pagamento', 'forma_pagamento', 'valor_pago_informado', 'observacao']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'forma_pagamento': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, conta=None, **kwargs):
        self.conta = conta or kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['data_pagamento'].initial = timezone.localdate()
        self.fields['data_pagamento'].required = True
        self.fields['forma_pagamento'].required = True
        if self.conta:
            self.fields['valor_pago_informado'].initial = self.conta.saldo

    def clean_valor_pago_informado(self):
        valor_pago = self.cleaned_data['valor_pago_informado']
        if self.conta and valor_pago > self.conta.saldo:
            raise ValidationError('O valor pago não pode ser maior que o valor em aberto.')
        return valor_pago


class ContaPagarCancelamentoForm(forms.Form):
    observacao = forms.CharField(
        label='Observação do cancelamento',
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
    )
