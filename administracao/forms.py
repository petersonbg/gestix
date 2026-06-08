from django import forms

from dashboard.models import ConfiguracaoSistema

from .models import Empresa


class BootstrapModelFormMixin:
    def aplicar_bootstrap(self):
        for field in self.fields.values():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.setdefault('class', 'form-check-input')
            else:
                field.widget.attrs.setdefault('class', 'form-control')

    def definir_somente_leitura(self):
        for field in self.fields.values():
            field.disabled = True


class EmpresaForm(BootstrapModelFormMixin, forms.ModelForm):
    class Meta:
        model = Empresa
        fields = [
            'razao_social', 'nome_fantasia', 'cnpj', 'inscricao_estadual', 'inscricao_municipal',
            'cep', 'logradouro', 'numero', 'complemento', 'bairro', 'cidade', 'estado',
            'telefone', 'celular', 'whatsapp', 'email', 'site',
            'logo', 'logo_impressao', 'cor_primaria', 'cor_secundaria',
            'responsavel', 'observacoes',
        ]
        widgets = {
            'estado': forms.TextInput(attrs={'maxlength': 2, 'style': 'text-transform: uppercase'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color'}),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()

    def clean_estado(self):
        return self.cleaned_data.get('estado', '').strip().upper()


class ConfiguracaoSistemaAdministracaoForm(BootstrapModelFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracaoSistema
        fields = ['notificacoes_aniversario_ativas', 'dias_antecedencia_aniversario']
        widgets = {
            'notificacoes_aniversario_ativas': forms.CheckboxInput(),
            'dias_antecedencia_aniversario': forms.NumberInput(attrs={'min': 0}),
        }

    def __init__(self, *args, somente_leitura=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()
        if somente_leitura:
            self.definir_somente_leitura()
