from django.db import models
from django.urls import reverse


class DadosEmpresa(models.Model):
    razao_social = models.CharField('razão social', max_length=180, blank=True)
    nome_fantasia = models.CharField(max_length=180, blank=True)
    cnpj = models.CharField('CNPJ', max_length=18, blank=True)
    inscricao_estadual = models.CharField('inscrição estadual', max_length=30, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    endereco = models.CharField('endereço', max_length=255, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=2, blank=True)
    cep = models.CharField('CEP', max_length=10, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'dados da empresa'
        verbose_name_plural = 'dados da empresa'

    def __str__(self):
        return self.nome_fantasia or self.razao_social or 'Dados da Empresa'

    @classmethod
    def get_solo(cls):
        empresa, _ = cls.objects.get_or_create(pk=1)
        return empresa

    def get_absolute_url(self):
        return reverse('administracao:dados_empresa')
