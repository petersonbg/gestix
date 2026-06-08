from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, RegexValidator
from django.db import models
from django.urls import reverse


validador_cor_hexadecimal = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Informe uma cor hexadecimal no formato #RRGGBB.',
)
validador_imagem = FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp', 'svg'])


class Empresa(models.Model):
    razao_social = models.CharField('razão social', max_length=180, blank=True)
    nome_fantasia = models.CharField(max_length=180, blank=True)
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=30, blank=True)
    inscricao_municipal = models.CharField('inscrição municipal', max_length=30, blank=True)

    cep = models.CharField('CEP', max_length=10, blank=True)
    logradouro = models.CharField(max_length=255, blank=True)
    numero = models.CharField('número', max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)

    telefone = models.CharField(max_length=20, blank=True)
    celular = models.CharField(max_length=20, blank=True)
    whatsapp = models.CharField('WhatsApp', max_length=20, blank=True)
    email = models.EmailField(blank=True)
    site = models.URLField(blank=True)

    logo = models.FileField(upload_to='empresa/logos/', blank=True, validators=[validador_imagem])
    logo_impressao = models.FileField(
        'logo para impressão',
        upload_to='empresa/logos/impressao/',
        blank=True,
        validators=[validador_imagem],
    )
    cor_primaria = models.CharField(
        'cor primária', max_length=7, default='#0D6EFD', validators=[validador_cor_hexadecimal]
    )
    cor_secundaria = models.CharField(
        'cor secundária', max_length=7, default='#6C757D', validators=[validador_cor_hexadecimal]
    )

    responsavel = models.CharField('responsável', max_length=150, blank=True)
    observacoes = models.TextField('observações', blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'empresa'
        verbose_name_plural = 'empresa'
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name='empresa_registro_unico'),
        ]

    def __str__(self):
        return self.nome_fantasia or self.razao_social or 'Dados da Empresa'

    def clean(self):
        super().clean()
        if self.pk not in (None, 1):
            raise ValidationError('O sistema permite apenas um cadastro de empresa.')

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('O cadastro da empresa não pode ser excluído; edite os dados existentes.')

    @classmethod
    def get_solo(cls):
        empresa, _ = cls.objects.get_or_create(pk=1)
        return empresa

    def get_absolute_url(self):
        return reverse('administracao:dados_empresa')
