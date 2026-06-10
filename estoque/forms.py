from django import forms

from produtos.models import Produto

from .models import MovimentacaoEstoque


class MovimentacaoEstoqueForm(forms.Form):
    produto = forms.ModelChoiceField(
        queryset=Produto.objects.filter(ativo=True).order_by('nome'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Produto',
    )
    tipo_movimentacao = forms.ChoiceField(
        choices=MovimentacaoEstoque.TipoMovimentacao.choices,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tipo de movimentação',
    )
    quantidade = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
        label='Quantidade',
    )
    origem = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex.: compra, venda, inventário'}),
        label='Origem',
    )
    observacao = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
        label='Observação',
    )

    def clean(self):
        cleaned_data = super().clean()
        produto = cleaned_data.get('produto')
        tipo_movimentacao = cleaned_data.get('tipo_movimentacao')
        quantidade = cleaned_data.get('quantidade')

        if tipo_movimentacao in {
            MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
            MovimentacaoEstoque.TipoMovimentacao.SAIDA,
        } and quantidade == 0:
            self.add_error('quantidade', 'A quantidade deve ser maior que zero para entradas e saídas.')

        if (
            produto
            and tipo_movimentacao == MovimentacaoEstoque.TipoMovimentacao.SAIDA
            and quantidade is not None
            and quantidade > produto.estoque_atual
        ):
            self.add_error('quantidade', 'A saída não pode ser maior que o estoque disponível.')

        return cleaned_data
