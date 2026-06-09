from .models import ConfiguracaoSistema


def configuracao_sistema(request):
    """Disponibiliza as preferências globais nos templates internos."""
    if not request.user.is_authenticated:
        return {}
    return {'configuracao_global': ConfiguracaoSistema.get_solo()}
