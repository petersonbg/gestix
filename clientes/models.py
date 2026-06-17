import re

from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .validators import validar_cpf_ou_cnpj


class Cliente(models.Model):
    class TipoPessoa(models.TextChoices):
        FISICA = 'fisica', 'Física'
        JURIDICA = 'juridica', 'Jurídica'

    nome = models.CharField(max_length=150)
    tipo_pessoa = models.CharField(max_length=10, choices=TipoPessoa.choices)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=20, unique=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=30, blank=True, null=True)
    data_nascimento = models.DateField('data de nascimento', blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    observacoes = models.TextField('observações', blank=True)
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'cliente'
        verbose_name_plural = 'clientes'

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        if self.data_nascimento and self.data_nascimento > timezone.localdate():
            raise ValidationError({'data_nascimento': 'A data de nascimento não pode ser futura.'})

        try:
            validar_cpf_ou_cnpj(self.cpf_cnpj, self.tipo_pessoa)
        except ValidationError as exc:
            raise ValidationError({'cpf_cnpj': exc.messages}) from exc

        if self.inscricao_estadual:
            inscricao = self.inscricao_estadual.strip()
            if inscricao.upper() != 'ISENTO' and not re.fullmatch(r'[0-9./-]+', inscricao):
                raise ValidationError({
                    'inscricao_estadual': 'Informe números, pontos, barras, hífens ou o texto ISENTO.'
                })

    def get_absolute_url(self):
        return reverse('clientes:detail', kwargs={'pk': self.pk})
