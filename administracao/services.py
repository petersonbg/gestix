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
    }
