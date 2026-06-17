<<<<<<< HEAD
import logging

from .models import LogAtividade


logger = logging.getLogger(__name__)


ACAO_ALIASES = {
    'login': LogAtividade.Acao.LOGIN,
    'logout': LogAtividade.Acao.LOGOUT,
    'criação': LogAtividade.Acao.CRIACAO,
    'criacao': LogAtividade.Acao.CRIACAO,
    'edição': LogAtividade.Acao.EDICAO,
    'edicao': LogAtividade.Acao.EDICAO,
    'exclusão': LogAtividade.Acao.EXCLUSAO,
    'exclusao': LogAtividade.Acao.EXCLUSAO,
    'cancelamento': LogAtividade.Acao.CANCELAMENTO,
    'finalização': LogAtividade.Acao.FINALIZACAO,
    'finalizacao': LogAtividade.Acao.FINALIZACAO,
    'impressão': LogAtividade.Acao.IMPRESSAO,
    'impressao': LogAtividade.Acao.IMPRESSAO,
    'backup': LogAtividade.Acao.BACKUP,
    'restauração': LogAtividade.Acao.RESTAURACAO,
    'restauracao': LogAtividade.Acao.RESTAURACAO,
    'pagamento': LogAtividade.Acao.PAGAMENTO,
    'recebimento': LogAtividade.Acao.RECEBIMENTO,
    'movimentação': LogAtividade.Acao.MOVIMENTACAO_ESTOQUE,
    'movimentacao': LogAtividade.Acao.MOVIMENTACAO_ESTOQUE,
    'abertura': LogAtividade.Acao.ABERTURA_CAIXA,
    'fechamento': LogAtividade.Acao.FECHAMENTO_CAIXA,
    'erro': LogAtividade.Acao.ERRO,
}


=======
from .models import LogAtividade


>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
def obter_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR') if request else ''
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR') if request else None


<<<<<<< HEAD
def obter_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')[:1000] if request else ''


def normalizar_acao(acao):
    valor = str(acao or '').strip()
    if valor in LogAtividade.Acao.values:
        return valor
    valor_normalizado = valor.lower()
    for chave, acao_padrao in ACAO_ALIASES.items():
        if chave in valor_normalizado:
            return acao_padrao
    return LogAtividade.Acao.ERRO if valor_normalizado else LogAtividade.Acao.ERRO


def dados_objeto(objeto):
    if not objeto:
        return '', ''
    meta = getattr(objeto, '_meta', None)
    tipo = f'{meta.app_label}.{meta.model_name}' if meta else objeto.__class__.__name__
    objeto_id = getattr(objeto, 'pk', None)
    return tipo[:120], str(objeto_id or '')[:64]


def registrar_log(usuario, acao, modulo, descricao='', objeto=None, request=None):
    try:
        objeto_tipo, objeto_id = dados_objeto(objeto)
        LogAtividade.objects.create(
            usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
            acao=normalizar_acao(acao),
            modulo=(modulo or '')[:80],
            descricao=descricao or '',
            objeto_tipo=objeto_tipo,
            objeto_id=objeto_id,
            ip_usuario=obter_ip(request),
            user_agent=obter_user_agent(request),
        )
    except Exception:
        logger.exception('Falha ao registrar log de atividade.')
=======
def registrar_log(usuario, acao, modulo, descricao='', request=None):
    LogAtividade.objects.create(
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        acao=acao,
        modulo=modulo,
        descricao=descricao,
        ip=obter_ip(request),
    )
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
