from django.db.utils import OperationalError, ProgrammingError

from .models import ConfiguracaoSistema, Empresa


TEMPO_LOGOUT_PADRAO_MINUTOS = 15


def obter_configuracao_sistema():
    """Obtém o singleton ou usa os padrões enquanto as migrations não foram aplicadas."""
    try:
        return ConfiguracaoSistema.get_solo()
    except (OperationalError, ProgrammingError):
        return ConfiguracaoSistema()


def obter_tempo_logout_inatividade_minutos():
    configuracao = obter_configuracao_sistema()
    return configuracao.tempo_logout_inatividade or TEMPO_LOGOUT_PADRAO_MINUTOS


def formatar_endereco_empresa(empresa):
    """Formata o endereço da empresa em uma linha, omitindo campos vazios."""
    if not empresa:
        return ''

    logradouro_numero = ', '.join(
        parte.strip() for parte in [empresa.logradouro, empresa.numero] if parte and parte.strip()
    )
    cidade_uf = '/'.join(
        parte.strip() for parte in [empresa.cidade, empresa.estado] if parte and parte.strip()
    )
    bairro = (empresa.bairro or '').strip()
    return ' - '.join(parte for parte in [logradouro_numero, bairro, cidade_uf] if parte)


def formatar_contato_empresa(empresa):
    """Retorna o contato preferencial da empresa: WhatsApp, telefone ou celular."""
    if not empresa:
        return ''
    return next(
        (contato.strip() for contato in [empresa.whatsapp, empresa.telefone, empresa.celular] if contato and contato.strip()),
        '',
    )


def contexto_documento_impresso():
    """Retorna a identidade da empresa e preferências comuns às impressões."""
    configuracao = obter_configuracao_sistema()
    try:
        empresa = Empresa.objects.order_by('pk').first()
    except (OperationalError, ProgrammingError):
        empresa = None
    if empresa and not empresa.possui_dados_cadastrais:
        empresa = None

    logo_empresa_url = ''
    if empresa and configuracao.mostrar_logo_impressoes:
        logo_empresa_url = empresa.logo_para_impressao_url

    return {
        'empresa': empresa,
        'configuracao_sistema': configuracao,
        'logo_empresa_url': logo_empresa_url,
        'endereco_empresa_formatado': formatar_endereco_empresa(empresa),
        'contato_empresa_formatado': formatar_contato_empresa(empresa),
    }

