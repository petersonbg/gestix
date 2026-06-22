from django import forms

from produtos.models import Produto


class NFeUploadForm(forms.Form):
    arquivo_xml = forms.FileField(
        label='Arquivo XML da NF-e',
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.xml,text/xml,application/xml'}),
    )

    def clean_arquivo_xml(self):
        arquivo = self.cleaned_data['arquivo_xml']
        if not arquivo.name.lower().endswith('.xml'):
            raise forms.ValidationError('Envie um arquivo XML válido.')
        return arquivo


class ConfirmarNotaFiscalForm(forms.Form):
    def __init__(self, *args, nota, **kwargs):
        super().__init__(*args, **kwargs)
        self.nota = nota
        produtos = Produto.objects.filter(ativo=True).order_by('nome')
        for item in nota.itens.all():
            self.fields[f'produto_{item.pk}'] = forms.ModelChoiceField(
                queryset=produtos,
                required=False,
                label='Produto existente',
                widget=forms.Select(attrs={'class': 'form-select'}),
            )
            self.fields[f'criar_{item.pk}'] = forms.BooleanField(
                required=False,
                label='Criar produto novo',
                widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            )
            self.fields[f'codigo_interno_{item.pk}'] = forms.CharField(
                required=False,
                initial=item.codigo_produto or f'NFE-{nota.numero}-{item.numero_item}',
                label='Código interno do novo produto',
                widget=forms.TextInput(attrs={'class': 'form-control'}),
            )

    def clean(self):
        cleaned_data = super().clean()
        for item in self.nota.itens.all():
            produto = cleaned_data.get(f'produto_{item.pk}')
            criar = cleaned_data.get(f'criar_{item.pk}')
            codigo_interno = cleaned_data.get(f'codigo_interno_{item.pk}')
            if not produto and not criar:
                self.add_error(f'produto_{item.pk}', 'Selecione um produto existente ou marque para criar um novo.')
            if criar and not codigo_interno:
                self.add_error(f'codigo_interno_{item.pk}', 'Informe o código interno do novo produto.')
            if criar and codigo_interno and Produto.objects.filter(codigo_interno=codigo_interno).exists():
                self.add_error(f'codigo_interno_{item.pk}', 'Já existe um produto com este código interno.')
        return cleaned_data

    def get_item_bindings(self):
        bindings = {}
        for item in self.nota.itens.all():
            produto = self.cleaned_data.get(f'produto_{item.pk}')
            bindings[item.pk] = {
                'produto': produto,
                'codigo_interno': self.cleaned_data.get(f'codigo_interno_{item.pk}'),
            }
        return bindings

