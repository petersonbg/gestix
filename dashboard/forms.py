from django import forms

from .models import ConfiguracaoSistema


class ConfiguracaoSistemaForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoSistema
        fields = ['notificacoes_aniversario_ativas', 'dias_antecedencia_aniversario']
        widgets = {
            'notificacoes_aniversario_ativas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'dias_antecedencia_aniversario': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        }
