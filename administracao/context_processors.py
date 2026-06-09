from .services import obter_configuracao_sistema


def configuracao_sistema(request):
    """Disponibiliza as preferências globais nos templates internos."""
    if not request.user.is_authenticated:
        return {}
    return {'configuracao_global': obter_configuracao_sistema()}
