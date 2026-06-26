from django import forms

from .models import ConfiguracaoWhatsApp, MensagemWhatsApp, ModeloMensagemWhatsApp
from .services import TelefoneWhatsAppInvalido, validar_telefone


class ConfiguracaoWhatsAppForm(forms.ModelForm):
    api_token = forms.CharField(
        label='Token da API',
        required=False,
        widget=forms.PasswordInput(
            attrs={'class': 'form-control', 'autocomplete': 'new-password'},
            render_value=False,
        ),
        help_text='Deixe em branco para manter o token já cadastrado.',
    )

    class Meta:
        model = ConfiguracaoWhatsApp
        fields = [
            'modo_envio',
            'provedor_api',
            'api_url',
            'api_token',
            'numero_remetente',
            'ativo',
            'enviar_automaticamente',
        ]
        widgets = {
            'modo_envio': forms.Select(attrs={'class': 'form-select'}),
            'provedor_api': forms.Select(attrs={'class': 'form-select'}),
            'api_url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://api.exemplo.com'}),
            'numero_remetente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5500000000000'}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'enviar_automaticamente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.api_token:
            self.fields['api_token'].widget.attrs['placeholder'] = 'Token já cadastrado'

    def clean_api_token(self):
        token = self.cleaned_data.get('api_token')
        if not token and self.instance and self.instance.pk:
            return self.instance.api_token
        return token


class ModeloMensagemWhatsAppForm(forms.ModelForm):
    class Meta:
        model = ModeloMensagemWhatsApp
        fields = ['nome', 'tipo', 'mensagem', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'mensagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'ativo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class EnviarMensagemWhatsAppForm(forms.Form):
    cliente = forms.ModelChoiceField(
        queryset=None,
        required=True,
        label='Cliente',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    telefone = forms.CharField(
        label='Telefone',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '5500000000000'}),
    )
    modelo = forms.ModelChoiceField(
        queryset=None,
        required=False,
        label='Modelo de mensagem',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    mensagem = forms.CharField(
        label='Mensagem',
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 7}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['cliente'].queryset = self._cliente_queryset()
        self.fields['modelo'].queryset = ModeloMensagemWhatsApp.objects.filter(ativo=True).order_by('nome')

    def _cliente_queryset(self):
        from clientes.models import Cliente

        return Cliente.objects.filter(ativo=True).order_by('nome')

    def clean_telefone(self):
        telefone = self.cleaned_data.get('telefone')
        try:
            return validar_telefone(telefone)
        except TelefoneWhatsAppInvalido as exc:
            raise forms.ValidationError(str(exc)) from exc