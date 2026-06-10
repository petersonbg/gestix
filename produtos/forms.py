from decimal import Decimal

from django import forms

from .models import Produto


class ProdutoForm(forms.ModelForm):
    class Meta:
        model = Produto
        fields = [
            'nome',
            'descricao',
            'codigo_interno',
            'codigo_barras',
            'categoria',
            'unidade_medida',
            'preco_custo',
            'preco_venda',
            'estoque_minimo',
            'fornecedor',
            'ncm',
            'ativo',
        ]
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nome do produto'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'codigo_interno': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Gerado automaticamente'}),
            'codigo_barras': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código de barras'}),
            'categoria': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Categoria'}),
            'unidade_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UN, KG, CX...'}),
            'preco_custo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'preco_venda': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'estoque_minimo': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'fornecedor': forms.Select(attrs={'class': 'form-select'}),
            'ncm': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'NCM'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        codigo = self.fields['codigo_interno']
        codigo.required = False
        codigo.disabled = True
        codigo.help_text = 'Gerado automaticamente ao salvar.'
        self.fields['preco_custo'].required = False

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('codigo_barras'):
            cleaned_data['codigo_barras'] = None
        preco_custo = cleaned_data.get('preco_custo')
        if preco_custo is None:
            preco_custo = Decimal('0.00')
            cleaned_data['preco_custo'] = preco_custo
        preco_venda = cleaned_data.get('preco_venda')
        if preco_custo is not None and preco_venda is not None and preco_venda < preco_custo:
            self.add_error('preco_venda', 'O preço de venda deve ser maior ou igual ao preço de custo.')
        return cleaned_data
