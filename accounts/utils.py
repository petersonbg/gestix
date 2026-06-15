from .models import LogAtividade


def obter_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') if request else ''
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') if request else None


ALIASES_ACAO = {
    'login': LogAtividade.Acao.LOGIN,
    'logout': LogAtividade.Acao.LOGOUT,
    'criação': LogAtividade.Acao.CRIACAO,
    'edição': LogAtividade.Acao.EDICAO,
    'exclusão': LogAtividade.Acao.EXCLUSAO,
    'cancelamento': LogAtividade.Acao.CANCELAMENTO,
    'finalização': LogAtividade.Acao.FINALIZACAO,
    'impressão': LogAtividade.Acao.IMPRESSAO,
    'backup': LogAtividade.Acao.BACKUP,
    'restauração': LogAtividade.Acao.RESTAURACAO,
    'pagamento': LogAtividade.Acao.PAGAMENTO,
    'recebimento': LogAtividade.Acao.RECEBIMENTO,
    'movimentação': LogAtividade.Acao.MOVIMENTACAO_ESTOQUE,
    'abertura de caixa': LogAtividade.Acao.ABERTURA_CAIXA,
    'fechamento de caixa': LogAtividade.Acao.FECHAMENTO_CAIXA,
    'erro': LogAtividade.Acao.ERRO,
}


def normalizar_acao(acao):
    valor = str(acao or '').strip()
    if valor in LogAtividade.Acao.values:
        return valor
    valor_normalizado = valor.casefold()
    for trecho, escolha in ALIASES_ACAO.items():
        if trecho in valor_normalizado:
            return escolha
    return LogAtividade.Acao.EDICAO


def registrar_log(usuario, acao, modulo, descricao='', objeto=None, request=None):
    """Registra auditoria sem interromper o fluxo principal em caso de falha."""
    try:
        objeto_tipo = ''
        objeto_id = ''
        if objeto is not None:
            meta = getattr(objeto, '_meta', None)
            objeto_tipo = (
                f'{meta.app_label}.{meta.model_name}' if meta else objeto.__class__.__name__
            )
            objeto_id = str(getattr(objeto, 'pk', '') or '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request else ''
        return LogAtividade.objects.create(
            usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
            acao=normalizar_acao(acao),
            modulo=str(modulo or '')[:80],
            descricao=str(descricao or ''),
            objeto_tipo=objeto_tipo,
            objeto_id=objeto_id,
            ip_usuario=obter_ip(request),
            user_agent=user_agent,
        )
    except Exception:
        return None
