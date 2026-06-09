from .models import ConfiguracaoSistema, Empresa


def contexto_documento_impresso():
    """Retorna a identidade da empresa e preferências comuns às impressões."""
    configuracao = ConfiguracaoSistema.get_solo()
    empresa = Empresa.objects.order_by('pk').first()
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
