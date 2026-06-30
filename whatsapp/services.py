import json
import re
from dataclasses import dataclass
from urllib.parse import quote

from django.utils import timezone

VARIAVEIS_PERMITIDAS = {
    'cliente_nome',
    'empresa_nome',
    'empresa_contato',
    'valor',
    'vencimento',
    'numero_venda',
    'numero_orcamento',
    'numero_os',
    'data',
}
PADRAO_VARIAVEL = re.compile(r'{([a-zA-Z_][a-zA-Z0-9_]*)}')


def variaveis_nao_permitidas(mensagem):
    return sorted({
        variavel
        for variavel in PADRAO_VARIAVEL.findall(mensagem or '')
        if variavel not in VARIAVEIS_PERMITIDAS
    })


class TelefoneWhatsAppInvalido(ValueError):
    pass


class ConfiguracaoWhatsAppInvalida(ValueError):
    pass


@dataclass
class ResultadoEnvioWhatsApp:
    sucesso: bool
    status: str
    telefone: str
    resposta_api: str = ''
    erro: str = ''
    mensagem_historico: object = None
    link: str = ''


def limpar_telefone(telefone):
    somente_digitos = re.sub(r'\D+', '', telefone or '')
    while somente_digitos.startswith('0'):
        somente_digitos = somente_digitos[1:]
    if somente_digitos and not somente_digitos.startswith('55'):
        somente_digitos = f'55{somente_digitos}'
    return somente_digitos


def validar_telefone(telefone):
    telefone_limpo = limpar_telefone(telefone)
    if len(telefone_limpo) < 12:
        raise TelefoneWhatsAppInvalido('Informe um telefone válido com DDD.')
    if len(telefone_limpo) > 15:
        raise TelefoneWhatsAppInvalido('O telefone informado possui dígitos demais.')
    return telefone_limpo


def gerar_link_whatsapp(telefone, mensagem):
    telefone_limpo = validar_telefone(telefone)
    return f'https://wa.me/{telefone_limpo}?text={quote(mensagem or "")}'


def renderizar_modelo(modelo, contexto):
    contexto_seguro = {chave: str(contexto.get(chave, '') or '') for chave in VARIAVEIS_PERMITIDAS}
    mensagem = modelo.mensagem if hasattr(modelo, 'mensagem') else str(modelo or '')
    for chave, valor in contexto_seguro.items():
        mensagem = mensagem.replace('{' + chave + '}', valor)
    return mensagem


def contexto_whatsapp(cliente=None, empresa=None, **extras):
    empresa_nome = ''
    empresa_contato = ''
    if empresa:
        empresa_nome = empresa.nome_fantasia or empresa.razao_social or 'AXIORA ERP'
        empresa_contato = empresa.whatsapp or empresa.telefone or empresa.celular or empresa.email or ''
    contexto = {
        'cliente_nome': getattr(cliente, 'nome', '') if cliente else '',
        'empresa_nome': empresa_nome,
        'empresa_contato': empresa_contato,
        'valor': '',
        'vencimento': '',
        'numero_venda': '',
        'numero_orcamento': '',
        'numero_os': '',
        'data': timezone.localdate().strftime('%d/%m/%Y'),
    }
    contexto.update({chave: valor for chave, valor in extras.items() if chave in VARIAVEIS_PERMITIDAS})
    return contexto


def _limitar_texto(texto, limite=4000):
    texto = str(texto or '')
    return texto[:limite]


def _sanitizar_resposta(valor, token=''):
    if isinstance(valor, (dict, list)):
        texto = json.dumps(valor, ensure_ascii=False)
    else:
        texto = str(valor or '')
    if token:
        texto = texto.replace(token, '[removido]')
    return _limitar_texto(texto)


class WhatsAppProvider:
    def __init__(self, configuracao=None):
        self.configuracao = configuracao

    def send_message(self, telefone, mensagem, contexto=None):
        raise NotImplementedError('Provider deve implementar send_message().')


class WhatsAppWebProvider(WhatsAppProvider):
    def send_message(self, telefone, mensagem, contexto=None):
        telefone_limpo = validar_telefone(telefone)
        return ResultadoEnvioWhatsApp(
            sucesso=True,
            status='PENDENTE',
            telefone=telefone_limpo,
            link=gerar_link_whatsapp(telefone_limpo, mensagem),
        )


class ApiWhatsAppProvider(WhatsAppProvider):
    timeout = 15

    def __init__(self, configuracao):
        super().__init__(configuracao)
        self._validar_configuracao()

    def _validar_configuracao(self):
        if not self.configuracao:
            raise ConfiguracaoWhatsAppInvalida('Nenhuma configuração de WhatsApp ativa foi encontrada.')
        if not self.configuracao.api_url:
            raise ConfiguracaoWhatsAppInvalida('Informe a URL da API nas configurações do WhatsApp.')
        if not self.configuracao.api_token:
            raise ConfiguracaoWhatsAppInvalida('Informe o token da API nas configurações do WhatsApp.')

    def montar_payload(self, telefone, mensagem, contexto=None):
        return {
            'telefone': telefone,
            'mensagem': mensagem,
            'numero_remetente': self.configuracao.numero_remetente or '',
        }

    def montar_headers(self):
        return {
            'Authorization': f'Bearer {self.configuracao.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }

    def send_message(self, telefone, mensagem, contexto=None):
        from .models import ConfiguracaoWhatsApp, MensagemWhatsApp

        contexto = contexto or {}
        telefone_limpo = validar_telefone(telefone)
        resposta_api = ''
        erro = ''
        sucesso = False
        status = MensagemWhatsApp.Status.ERRO

        try:
            import requests
        except ImportError:
            erro = 'Biblioteca requests não está instalada.'
        else:
            try:
                response = requests.post(
                    self.configuracao.api_url,
                    json=self.montar_payload(telefone_limpo, mensagem, contexto),
                    headers=self.montar_headers(),
                    timeout=self.timeout,
                )
                resposta_api = self._serializar_resposta(response)
                if response.status_code in (401, 403):
                    erro = 'Erro de autenticação na API do WhatsApp.'
                elif 200 <= response.status_code < 300:
                    sucesso = True
                    status = MensagemWhatsApp.Status.ENVIADA
                else:
                    erro = f'API retornou status HTTP {response.status_code}.'
            except requests.Timeout:
                erro = 'Tempo limite excedido ao chamar a API do WhatsApp.'
            except requests.RequestException as exc:
                erro = f'Erro ao chamar a API do WhatsApp: {exc.__class__.__name__}.'
            except ValueError as exc:
                erro = str(exc)

        if erro and not resposta_api:
            resposta_api = erro

        historico = MensagemWhatsApp.objects.create(
            cliente=contexto.get('cliente'),
            telefone=telefone_limpo,
            tipo=contexto.get('tipo') or 'AVULSA',
            mensagem=mensagem,
            modo_envio=ConfiguracaoWhatsApp.ModoEnvio.API,
            status=status,
            resposta_api=_sanitizar_resposta(resposta_api, self.configuracao.api_token),
            usuario=contexto.get('usuario'),
            data_envio=timezone.now() if sucesso else None,
        )
        origem = contexto.get('origem') or _origem_por_tipo(contexto.get('tipo'))
        descricao = ORIGEM_LOG_DESCRICAO.get(origem, 'mensagem enviada')
        alvo = getattr(contexto.get('cliente'), 'nome', '') or telefone_limpo
        registrar_log_whatsapp(
            contexto.get('usuario'),
            origem,
            f'{descricao}: WhatsApp API para {alvo}.',
            erro=not sucesso,
        )
        return ResultadoEnvioWhatsApp(
            sucesso=sucesso,
            status=status,
            telefone=telefone_limpo,
            resposta_api=historico.resposta_api,
            erro=erro,
            mensagem_historico=historico,
        )

    def _serializar_resposta(self, response):
        try:
            conteudo = response.json()
        except ValueError:
            conteudo = response.text or f'HTTP {response.status_code}'
        return _sanitizar_resposta({
            'status_code': response.status_code,
            'body': conteudo,
        }, self.configuracao.api_token)


class ZernioProvider(ApiWhatsAppProvider):
    pass


class MetaProvider(ApiWhatsAppProvider):
    pass


class OutroProvider(ApiWhatsAppProvider):
    pass


def obter_provider(configuracao=None):
    from .models import ConfiguracaoWhatsApp

    configuracao = configuracao or ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
    if not configuracao or configuracao.modo_envio == ConfiguracaoWhatsApp.ModoEnvio.WHATSAPP_WEB:
        return WhatsAppWebProvider(configuracao)
    provedores = {
        ConfiguracaoWhatsApp.ProvedorAPI.ZERNIO: ZernioProvider,
        ConfiguracaoWhatsApp.ProvedorAPI.META: MetaProvider,
        ConfiguracaoWhatsApp.ProvedorAPI.OUTRO: OutroProvider,
    }
    return provedores.get(configuracao.provedor_api, OutroProvider)(configuracao)


def enviar_mensagem_api(telefone, mensagem, contexto=None, configuracao=None):
    from .models import ConfiguracaoWhatsApp

    configuracao = configuracao or ConfiguracaoWhatsApp.objects.filter(ativo=True).first()
    if not configuracao:
        raise ConfiguracaoWhatsAppInvalida('Nenhuma configuração de WhatsApp ativa foi encontrada.')
    if configuracao.modo_envio != ConfiguracaoWhatsApp.ModoEnvio.API:
        raise ConfiguracaoWhatsAppInvalida('A configuração ativa não está em modo API.')
    return obter_provider(configuracao).send_message(telefone, mensagem, contexto or {})


def processar_fila_whatsapp(limite=None):
    from django.db.models import F, Q

    from .models import FilaMensagemWhatsApp

    agora = timezone.now()
    queryset = FilaMensagemWhatsApp.objects.select_related('cliente', 'usuario_criacao').filter(
        Q(agendada_para__isnull=True) | Q(agendada_para__lte=agora),
        status=FilaMensagemWhatsApp.Status.PENDENTE,
    ).order_by('agendada_para', 'criado_em')
    if limite:
        queryset = queryset[:limite]

    resultado = {'processadas': 0, 'enviadas': 0, 'erros': 0}
    for item in queryset:
        atualizado = FilaMensagemWhatsApp.objects.filter(
            pk=item.pk,
            status=FilaMensagemWhatsApp.Status.PENDENTE,
        ).update(
            status=FilaMensagemWhatsApp.Status.PROCESSANDO,
            tentativas=F('tentativas') + 1,
            erro='',
            atualizado_em=timezone.now(),
        )
        if not atualizado:
            continue
        item.refresh_from_db(fields=['status', 'tentativas', 'erro', 'atualizado_em'])

        try:
            envio = enviar_mensagem_api(
                item.telefone,
                item.mensagem,
                contexto={
                    'cliente': item.cliente,
                    'usuario': item.usuario_criacao,
                    'tipo': item.tipo,
                    'origem': _origem_por_tipo(item.tipo),
                },
            )
        except (ConfiguracaoWhatsAppInvalida, TelefoneWhatsAppInvalido) as exc:
            item.status = FilaMensagemWhatsApp.Status.ERRO
            item.erro = _limitar_texto(str(exc), 1000)
            resultado['erros'] += 1
        else:
            if envio.sucesso:
                item.status = FilaMensagemWhatsApp.Status.ENVIADA
                item.erro = ''
                resultado['enviadas'] += 1
            else:
                item.status = FilaMensagemWhatsApp.Status.ERRO
                item.erro = _limitar_texto(envio.erro or envio.resposta_api, 1000)
                resultado['erros'] += 1
        item.save(update_fields=['status', 'erro', 'atualizado_em'])
        resultado['processadas'] += 1
    return resultado
ORIGEM_TIPO_MODELO = {
    'cliente': 'AVULSA',
    'cobranca': 'COBRANCA',
    'aniversario': 'ANIVERSARIO',
    'orcamento': 'ORCAMENTO',
    'ordem_servico': 'ORDEM_SERVICO',
    'venda': 'VENDA',
}

ORIGEM_LOG_DESCRICAO = {
    'cliente': 'mensagem enviada',
    'cobranca': 'envio de cobrança',
    'aniversario': 'envio de aniversário',
    'orcamento': 'envio de orçamento',
    'ordem_servico': 'envio de OS',
    'venda': 'envio de venda',
}


def _origem_por_tipo(tipo):
    for origem, tipo_origem in ORIGEM_TIPO_MODELO.items():
        if tipo_origem == tipo:
            return origem
    return 'cliente'


def obter_modelo_padrao(tipo):
    from .models import ModeloMensagemWhatsApp

    return ModeloMensagemWhatsApp.objects.filter(tipo=tipo, ativo=True).order_by('nome').first()


def _formatar_moeda(valor):
    if valor in (None, ''):
        return ''
    return f'R$ {valor:.2f}'.replace('.', ',')


def _formatar_data(valor):
    return valor.strftime('%d/%m/%Y') if valor else ''


def resolver_origem_whatsapp(origem, objeto_id):
    from django.http import Http404
    from django.shortcuts import get_object_or_404

    from administracao.models import Empresa
    from clientes.models import Cliente
    from contas_receber.models import ContaReceber
    from orcamentos.models import Orcamento
    from ordens_servico.models import OrdemServico
    from vendas.models import Venda

    origem = origem or 'cliente'
    if origem not in ORIGEM_TIPO_MODELO:
        raise Http404('Origem de WhatsApp inválida.')
    tipo = ORIGEM_TIPO_MODELO[origem]
    empresa = Empresa.get_solo()
    objeto = None
    extras = {}

    if origem == 'cobranca':
        objeto = get_object_or_404(ContaReceber.objects.select_related('cliente'), pk=objeto_id)
        cliente = objeto.cliente
        extras = {
            'valor': _formatar_moeda(objeto.saldo),
            'vencimento': _formatar_data(objeto.data_vencimento),
        }
    elif origem == 'orcamento':
        objeto = get_object_or_404(Orcamento.objects.select_related('cliente'), pk=objeto_id)
        cliente = objeto.cliente
        extras = {'numero_orcamento': str(objeto.pk)}
    elif origem == 'ordem_servico':
        objeto = get_object_or_404(OrdemServico.objects.select_related('cliente'), pk=objeto_id)
        cliente = objeto.cliente
        extras = {'numero_os': objeto.numero}
    elif origem == 'venda':
        objeto = get_object_or_404(Venda.objects.select_related('cliente'), pk=objeto_id)
        cliente = objeto.cliente
        extras = {'numero_venda': str(objeto.pk)}
    else:
        cliente = get_object_or_404(Cliente, pk=objeto_id)
        origem = 'aniversario' if origem == 'aniversario' else 'cliente'
        tipo = ORIGEM_TIPO_MODELO.get(origem, 'AVULSA')

    modelo = obter_modelo_padrao(tipo) if tipo != 'AVULSA' else None
    contexto = contexto_whatsapp(cliente=cliente, empresa=empresa, **extras)
    mensagem = renderizar_modelo(modelo, contexto) if modelo else ''
    telefone = cliente.telefone or ''
    telefone_valido = ''
    erro_telefone = ''
    if telefone:
        try:
            telefone_valido = validar_telefone(telefone)
        except TelefoneWhatsAppInvalido as exc:
            erro_telefone = str(exc)
    else:
        erro_telefone = 'Cliente sem telefone cadastrado.'

    return {
        'origem': origem,
        'tipo': tipo,
        'cliente': cliente,
        'objeto': objeto,
        'modelo': modelo,
        'contexto': contexto,
        'mensagem': mensagem,
        'telefone': telefone_valido or telefone,
        'telefone_valido': bool(telefone_valido),
        'erro_telefone': erro_telefone,
        'log_descricao': ORIGEM_LOG_DESCRICAO.get(origem, 'mensagem enviada'),
    }


def url_envio_whatsapp(origem, objeto_id):
    from django.urls import reverse
    from urllib.parse import urlencode

    return f"{reverse('whatsapp:enviar')}?{urlencode({'origem': origem, 'id': objeto_id})}"


def registrar_log_whatsapp(usuario, origem, descricao, request=None, erro=False):
    try:
        from accounts.utils import registrar_log
    except Exception:
        return
    acao = 'erro' if erro else 'edicao'
    registrar_log(usuario, acao, 'whatsapp', descricao, request=request)