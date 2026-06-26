import ipaddress
from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse


HOSTS_API_BLOQUEADOS = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}


def validar_api_url_externa(api_url):
    partes = urlparse(api_url or '')
    hostname = (partes.hostname or '').strip().lower()
    if partes.scheme not in {'http', 'https'} or not partes.netloc or not hostname:
        raise ValidationError('Informe uma URL HTTP/HTTPS válida para a API.')
    if hostname in HOSTS_API_BLOQUEADOS or hostname.endswith('.local'):
        raise ValidationError('A URL da API não pode apontar para localhost ou rede local.')
    try:
        endereco = ipaddress.ip_address(hostname)
    except ValueError:
        return
    if any([
        endereco.is_loopback,
        endereco.is_private,
        endereco.is_link_local,
        endereco.is_multicast,
        endereco.is_reserved,
        endereco.is_unspecified,
    ]):
        raise ValidationError('A URL da API deve apontar para um provedor externo válido.')


class TipoMensagemWhatsApp(models.TextChoices):
    COBRANCA = 'COBRANCA', 'Cobrança'
    ANIVERSARIO = 'ANIVERSARIO', 'Aniversário'
    ORCAMENTO = 'ORCAMENTO', 'Orçamento'
    ORDEM_SERVICO = 'ORDEM_SERVICO', 'Ordem de Serviço'
    VENDA = 'VENDA', 'Venda'
    AVULSA = 'AVULSA', 'Avulsa'


class ConfiguracaoWhatsApp(models.Model):
    class ModoEnvio(models.TextChoices):
        WHATSAPP_WEB = 'WHATSAPP_WEB', 'WhatsApp Web'
        API = 'API', 'API'

    class ProvedorAPI(models.TextChoices):
        ZERNIO = 'ZERNIO', 'Zernio'
        META = 'META', 'Meta'
        OUTRO = 'OUTRO', 'Outro'

    modo_envio = models.CharField(max_length=20, choices=ModoEnvio.choices, default=ModoEnvio.WHATSAPP_WEB)
    provedor_api = models.CharField(max_length=20, choices=ProvedorAPI.choices, default=ProvedorAPI.OUTRO)
    api_url = models.URLField('URL da API', blank=True)
    api_token = models.CharField('token da API', max_length=500, blank=True)
    numero_remetente = models.CharField('número remetente', max_length=20, blank=True)
    ativo = models.BooleanField(default=True)
    enviar_automaticamente = models.BooleanField('enviar automaticamente', default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-ativo', '-atualizado_em']
        verbose_name = 'configuração do WhatsApp'
        verbose_name_plural = 'configurações do WhatsApp'
        constraints = [
            models.UniqueConstraint(
                fields=['ativo'],
                condition=Q(ativo=True),
                name='whatsapp_apenas_uma_configuracao_ativa',
            ),
        ]

    def __str__(self):
        status = 'ativa' if self.ativo else 'inativa'
        return f'{self.get_modo_envio_display()} ({status})'

    def clean(self):
        super().clean()
        if self.modo_envio == self.ModoEnvio.API:
            erros = {}
            if not self.api_url:
                erros['api_url'] = 'Informe a URL da API para o modo API.'
            if not self.api_token:
                erros['api_token'] = 'Informe o token da API para o modo API.'
            if self.api_url:
                try:
                    validar_api_url_externa(self.api_url)
                except ValidationError as exc:
                    erros['api_url'] = exc.messages[0]
            if erros:
                raise ValidationError(erros)


class ModeloMensagemWhatsApp(models.Model):
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TipoMensagemWhatsApp.choices)
    mensagem = models.TextField()
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'modelo de mensagem WhatsApp'
        verbose_name_plural = 'modelos de mensagem WhatsApp'
        indexes = [models.Index(fields=['tipo', 'ativo'])]

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        from .services import variaveis_nao_permitidas

        variaveis = variaveis_nao_permitidas(self.mensagem)
        if variaveis:
            raise ValidationError({
                'mensagem': f"Variáveis não permitidas: {', '.join('{' + item + '}' for item in variaveis)}."
            })

    def get_absolute_url(self):
        return reverse('whatsapp:modelos')


class MensagemWhatsApp(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ENVIADA = 'ENVIADA', 'Enviada'
        ERRO = 'ERRO', 'Erro'
        CANCELADA = 'CANCELADA', 'Cancelada'

    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.SET_NULL, blank=True, null=True)
    telefone = models.CharField(max_length=20)
    tipo = models.CharField(max_length=20, choices=TipoMensagemWhatsApp.choices)
    mensagem = models.TextField()
    modo_envio = models.CharField(max_length=20, choices=ConfiguracaoWhatsApp.ModoEnvio.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    resposta_api = models.TextField('resposta da API', blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, blank=True, null=True)
    data_envio = models.DateTimeField('data de envio', blank=True, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']
        verbose_name = 'mensagem WhatsApp'
        verbose_name_plural = 'mensagens WhatsApp'
        indexes = [
            models.Index(fields=['status', 'criado_em']),
            models.Index(fields=['tipo', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} - {self.telefone}'


class FilaMensagemWhatsApp(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        PROCESSANDO = 'PROCESSANDO', 'Processando'
        ENVIADA = 'ENVIADA', 'Enviada'
        ERRO = 'ERRO', 'Erro'
        CANCELADA = 'CANCELADA', 'Cancelada'

    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.SET_NULL, blank=True, null=True)
    telefone = models.CharField(max_length=20)
    tipo = models.CharField(max_length=20, choices=TipoMensagemWhatsApp.choices)
    mensagem = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDENTE)
    tentativas = models.PositiveSmallIntegerField(default=0)
    erro = models.TextField(blank=True)
    agendada_para = models.DateTimeField(blank=True, null=True)
    usuario_criacao = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        verbose_name='usuário de criação',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['agendada_para', '-criado_em']
        verbose_name = 'fila de mensagem WhatsApp'
        verbose_name_plural = 'fila de mensagens WhatsApp'
        indexes = [
            models.Index(fields=['status', 'agendada_para']),
            models.Index(fields=['tipo', 'criado_em']),
        ]

    def __str__(self):
        return f'{self.get_status_display()} - {self.telefone}'