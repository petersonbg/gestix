from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import ContaReceber


class ContaReceberRecebimentoForm(forms.ModelForm):
    valor_recebido = forms.DecimalField(
        label='Valor recebido',
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    )

    class Meta:
        model = ContaReceber
        fields = ['data_pagamento', 'forma_recebimento', 'valor_recebido', 'observacao']
        widgets = {
            'data_pagamento': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'forma_recebimento': forms.Select(attrs={'class': 'form-select'}),
            'observacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, conta=None, **kwargs):
        self.conta = conta or kwargs.get('instance')
        super().__init__(*args, **kwargs)
        self.fields['data_pagamento'].initial = timezone.localdate()
        self.fields['data_pagamento'].required = True
        self.fields['forma_recebimento'].required = True
        if self.conta:
            self.fields['valor_recebido'].initial = self.conta.saldo

    def clean_valor_recebido(self):
        valor_recebido = self.cleaned_data['valor_recebido']
        if self.conta and valor_recebido > self.conta.saldo:
            raise ValidationError('O valor recebido não pode ser maior que o saldo da parcela.')
        return valor_recebido
