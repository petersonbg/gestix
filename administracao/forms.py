from django import forms
<<<<<<< HEAD
from django.conf import settings
from django.core.exceptions import ValidationError
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

from ordens_servico.models import Servico

from .models import CategoriaProduto, ConfiguracaoSistema, Empresa


<<<<<<< HEAD
EXTENSOES_BACKUP_PERMITIDAS = {'.dump', '.backup'}


class BackupRestoreForm(forms.Form):
    arquivo_backup = forms.FileField(
        label='Arquivo de backup',
        required=True,
        widget=forms.ClearableFileInput(attrs={
            'class': 'form-control',
            'accept': '.dump,.backup',
        }),
    )
    confirmar_restauracao = forms.BooleanField(
        label='A restauração substituirá os dados atuais do sistema. Deseja continuar?',
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
    )

    def clean_arquivo_backup(self):
        arquivo = self.cleaned_data['arquivo_backup']
        nome = arquivo.name or ''
        extensao = f'.{nome.rsplit(".", 1)[-1].lower()}' if '.' in nome else ''
        if extensao not in EXTENSOES_BACKUP_PERMITIDAS:
            raise ValidationError('Envie um arquivo .dump ou .backup.')
        if arquivo.size > settings.BACKUP_MAX_UPLOAD_SIZE:
            raise ValidationError('O arquivo deve ter no máximo 500 MB.')
        return arquivo


=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
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
        labels = {
            'logo': 'Logo do Sistema',
            'logo_impressao': 'Logo de Impressão',
        }
        widgets = {
            'estado': forms.TextInput(attrs={'maxlength': 2, 'style': 'text-transform: uppercase'}),
            'cor_primaria': forms.TextInput(attrs={'type': 'color'}),
            'cor_secundaria': forms.TextInput(attrs={'type': 'color'}),
            'observacoes': forms.Textarea(attrs={'rows': 4}),
            'logo': forms.ClearableFileInput(attrs={'accept': '.png,.jpg,.jpeg,.svg'}),
            'logo_impressao': forms.ClearableFileInput(attrs={'accept': '.png,.svg'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()

    def clean_estado(self):
        return self.cleaned_data.get('estado', '').strip().upper()


class CategoriaProdutoForm(BootstrapModelFormMixin, forms.ModelForm):
    class Meta:
        model = CategoriaProduto
        fields = ['nome', 'descricao', 'tipo', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'tipo': forms.Select(),
            'ativo': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()


class ServicoForm(BootstrapModelFormMixin, forms.ModelForm):
    class Meta:
        model = Servico
        fields = ['nome', 'descricao', 'valor_padrao', 'ativo']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'valor_padrao': forms.NumberInput(attrs={'min': 0, 'step': '0.01'}),
            'ativo': forms.CheckboxInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()

class ConfiguracaoSistemaAdministracaoForm(BootstrapModelFormMixin, forms.ModelForm):
    class Meta:
        model = ConfiguracaoSistema
        fields = [
            'notificacoes_aniversario_ativas',
            'dias_antecedencia_aniversario',
            'tempo_logout_inatividade',
            'mostrar_logo_impressoes',
            'mostrar_assinatura_cliente',
            'mensagem_rodape_documentos',
        ]
        widgets = {
            'notificacoes_aniversario_ativas': forms.CheckboxInput(),
            'dias_antecedencia_aniversario': forms.NumberInput(attrs={'min': 0}),
            'tempo_logout_inatividade': forms.NumberInput(attrs={'min': 1}),
        }

    def __init__(self, *args, somente_leitura=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.aplicar_bootstrap()
        if somente_leitura:
            self.definir_somente_leitura()
