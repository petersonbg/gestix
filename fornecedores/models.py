from django.db import models
from django.urls import reverse


class Fornecedor(models.Model):
    razao_social = models.CharField('razão social', max_length=150)
    nome_fantasia = models.CharField(max_length=150, blank=True)
    cnpj = models.CharField('CNPJ', max_length=18, unique=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=30, blank=True)
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
        ordering = ['razao_social']
        verbose_name = 'fornecedor'
        verbose_name_plural = 'fornecedores'

    def __str__(self):
        return self.razao_social

    def get_absolute_url(self):
        return reverse('fornecedores:detail', kwargs={'pk': self.pk})
