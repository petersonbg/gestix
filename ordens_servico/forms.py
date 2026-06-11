from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.forms import inlineformset_factory

from .models import ItemProdutoOS, ItemServicoOS, OrdemServico, Servico


class ServicoForm(forms.ModelForm):
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'valor_padrao', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'descricao': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'valor_padrao': forms.NumberInput(
                attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}
            ),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UsuarioAtivoChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, usuario):
        return usuario.get_full_name().strip() or usuario.get_username()


class OrdemServicoForm(forms.ModelForm):
    responsavel = UsuarioAtivoChoiceField(
        label='Responsável pela abertura/gerenciamento',
        queryset=get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    responsavel_execucao = UsuarioAtivoChoiceField(
        label='Responsável pela Execução',
        queryset=get_user_model().objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = OrdemServico
        fields = ['cliente', 'data_previsao', 'responsavel', 'responsavel_execucao', 'assinatura_responsavel_execucao', 'descricao_problema', 'diagnostico', 'solucao', 'observacoes', 'valor_deslocamento', 'desconto']
        widgets = {
            'cliente': forms.HiddenInput(),
            'data_previsao': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'responsavel': forms.Select(attrs={'class': 'form-select'}),
            'responsavel_execucao': forms.Select(attrs={'class': 'form-select'}),
            'assinatura_responsavel_execucao': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'descricao_problema': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'diagnostico': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'solucao': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'observacoes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'valor_deslocamento': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
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
