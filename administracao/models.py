from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.urls import reverse

from .validators import validador_logo_impressao, validador_logo_sistema


validador_cor_hexadecimal = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message='Informe uma cor hexadecimal no formato #RRGGBB.',
)


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

    logo = models.FileField(
        'logo do sistema',
        upload_to='empresa/logos/',
        blank=True,
        validators=[validador_logo_sistema],
        help_text='Recomendado: PNG transparente 512x512',
    )
    logo_impressao = models.FileField(
        'logo para impressão',
        upload_to='empresa/logos/impressao/',
        blank=True,
        validators=[validador_logo_impressao],
        help_text='Recomendado: PNG ou SVG horizontal 1200x400',
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

    @property
    def possui_dados_cadastrais(self):
        return any([
            self.razao_social,
            self.nome_fantasia,
            self.cnpj,
            self.inscricao_estadual,
            self.telefone,
            self.celular,
            self.whatsapp,
            self.email,
            self.logradouro,
            self.cidade,
        ])

    @property
    def endereco_completo(self):
        endereco = self.logradouro
        if endereco and self.numero:
            endereco = f'{endereco}, {self.numero}'
        elif self.numero:
            endereco = self.numero
        partes = [endereco, self.complemento, self.bairro]
        cidade_estado = ' - '.join(parte for parte in [self.cidade, self.estado] if parte)
        if cidade_estado:
            partes.append(cidade_estado)
        if self.cep:
            partes.append(f'CEP {self.cep}')
        return ', '.join(parte for parte in partes if parte)

    @property
    def telefone_whatsapp(self):
        contatos = []
        telefone = self.telefone or self.celular
        if telefone:
            contatos.append(telefone)
        if self.whatsapp and self.whatsapp != telefone:
            contatos.append(f'WhatsApp: {self.whatsapp}')
        return ' | '.join(contatos)

    @property
    def logo_para_impressao_url(self):
        arquivo = self.logo_impressao or self.logo
        return arquivo.url if arquivo else ''


class ConfiguracaoSistema(models.Model):
    notificacoes_aniversario_ativas = models.BooleanField(
        'ativar notificações de aniversário',
        default=True,
    )
    dias_antecedencia_aniversario = models.PositiveIntegerField(
        'dias de antecedência para aviso',
        default=0,
        help_text='0 = avisar somente no dia; 7 = avisar com uma semana de antecedência.',
    )
    tempo_logout_inatividade = models.PositiveIntegerField(
        'tempo para logout por inatividade (minutos)',
        default=15,
        help_text='Tempo em minutos antes de encerrar automaticamente uma sessão inativa.',
    )
    mostrar_logo_impressoes = models.BooleanField('mostrar logo nas impressões', default=True)
    mostrar_assinatura_cliente = models.BooleanField('mostrar assinatura do cliente', default=True)
    mensagem_rodape_documentos = models.CharField(
        'mensagem de rodapé dos documentos',
        max_length=255,
        default='Documento gerado pelo sistema GESTIX.',
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'configuração do sistema'
        verbose_name_plural = 'configuração do sistema'
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name='configuracao_sistema_registro_unico'),
        ]

    def __str__(self):
        return 'Configurações do Sistema'

    def clean(self):
        super().clean()
        if self.pk not in (None, 1):
            raise ValidationError('O sistema permite apenas um registro de configuração.')
        if self.tempo_logout_inatividade < 1:
            raise ValidationError({'tempo_logout_inatividade': 'O tempo de inatividade deve ser de pelo menos 1 minuto.'})

    def save(self, *args, **kwargs):
        if self.pk is None:
            self.pk = 1
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError('A configuração do sistema não pode ser excluída; edite o registro existente.')

    @classmethod
    def get_solo(cls):
        configuracao, _ = cls.objects.get_or_create(pk=1)
        return configuracao
