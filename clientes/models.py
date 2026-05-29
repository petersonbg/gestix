from django.db import models
from django.urls import reverse


class Cliente(models.Model):
    class TipoPessoa(models.TextChoices):
        FISICA = 'fisica', 'Física'
        JURIDICA = 'juridica', 'Jurídica'

    nome = models.CharField(max_length=150)
    tipo_pessoa = models.CharField(max_length=10, choices=TipoPessoa.choices)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=20, unique=True)
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

    def get_absolute_url(self):
        return reverse('clientes:detail', kwargs={'pk': self.pk})
