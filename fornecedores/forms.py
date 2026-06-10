from django import forms

from .models import Fornecedor


class FornecedorForm(forms.ModelForm):
    class Meta:
        model = Fornecedor
        fields = [
            'razao_social',
            'nome_fantasia',
            'cnpj',
            'inscricao_estadual',
            'telefone',
            'email',
            'endereco',
            'cidade',
            'estado',
            'observacoes',
            'ativo',
        ]
        widgets = {
            'razao_social': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Razão social'}),
            'nome_fantasia': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome fantasia'}),
            'cnpj': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '00.000.000/0000-00'}),
            'inscricao_estadual': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Inscrição estadual'}),
            'telefone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '(00) 00000-0000'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@exemplo.com'}),
            'endereco': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Rua, número e complemento'}),
            'cidade': forms.TextInput(attrs={'class': 'form-control'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '2', 'placeholder': 'UF'}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
