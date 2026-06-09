from .models import LogAtividade


def obter_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') if request else ''
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') if request else None


def registrar_log(usuario, acao, modulo, descricao='', request=None):
    LogAtividade.objects.create(
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        acao=acao,
        modulo=modulo,
        descricao=descricao,
        ip=obter_ip(request),
    )
