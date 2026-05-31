from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from xml.etree import ElementTree as ET

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from estoque.models import MovimentacaoEstoque
from fornecedores.models import Fornecedor
from produtos.models import Produto

from .models import ItemNotaFiscalEntrada, NotaFiscalEntrada


@dataclass
class NFeItemData:
    numero_item: int
    codigo_produto: str
    descricao: str
    ncm: str
    unidade_medida: str
    quantidade: int
    valor_unitario: Decimal
    valor_total: Decimal


@dataclass
class NFeData:
    chave_acesso: str
    numero: str
    serie: str
    data_emissao: datetime
    emitente_cnpj: str
    emitente_razao_social: str
    valor_total: Decimal
    itens: list[NFeItemData]


def _strip_namespace(element):
    for node in element.iter():
        if '}' in node.tag:
            node.tag = node.tag.split('}', 1)[1]
    return element


def _text(parent, path, default=''):
    found = parent.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _decimal(value, default='0.00'):
    return Decimal(value or default).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def _quantity(value):
    quantity = Decimal(value or '0')
    if quantity < 0:
        raise ValidationError('Quantidade de item inválida no XML.')
    return int(quantity.to_integral_value(rounding=ROUND_HALF_UP))


def parse_nfe_xml(xml_file):
    try:
        tree = ET.parse(xml_file)
    except ET.ParseError as exc:
        raise ValidationError('Arquivo XML inválido.') from exc

    root = _strip_namespace(tree.getroot())
    inf_nfe = root.find('.//infNFe')
    if inf_nfe is None:
        raise ValidationError('XML não contém dados de NF-e.')

    chave_acesso = (inf_nfe.attrib.get('Id') or '').replace('NFe', '').strip()
    if not chave_acesso:
        chave_acesso = _text(root, './/protNFe/infProt/chNFe')
    if len(chave_acesso) != 44:
        raise ValidationError('Chave de acesso da NF-e não encontrada ou inválida.')

    ide = inf_nfe.find('ide')
    emit = inf_nfe.find('emit')
    total = inf_nfe.find('total/ICMSTot')
    if ide is None or emit is None or total is None:
        raise ValidationError('XML de NF-e incompleto.')

    data_emissao_raw = _text(ide, 'dhEmi') or _text(ide, 'dEmi')
    try:
        data_emissao = datetime.fromisoformat(data_emissao_raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValidationError('Data de emissão inválida no XML.') from exc
    if timezone.is_naive(data_emissao):
        data_emissao = timezone.make_aware(data_emissao)

    itens = []
    for det in inf_nfe.findall('det'):
        prod = det.find('prod')
        if prod is None:
            continue
        itens.append(
            NFeItemData(
                numero_item=int(det.attrib.get('nItem') or len(itens) + 1),
                codigo_produto=_text(prod, 'cProd'),
                descricao=_text(prod, 'xProd'),
                ncm=_text(prod, 'NCM'),
                unidade_medida=_text(prod, 'uCom') or 'UN',
                quantidade=_quantity(_text(prod, 'qCom')),
                valor_unitario=_decimal(_text(prod, 'vUnCom')),
                valor_total=_decimal(_text(prod, 'vProd')),
            )
        )

    if not itens:
        raise ValidationError('Nenhum item de produto foi encontrado no XML.')

    return NFeData(
        chave_acesso=chave_acesso,
        numero=_text(ide, 'nNF'),
        serie=_text(ide, 'serie'),
        data_emissao=data_emissao,
        emitente_cnpj=_text(emit, 'CNPJ'),
        emitente_razao_social=_text(emit, 'xNome'),
        valor_total=_decimal(_text(total, 'vNF')),
        itens=itens,
    )


@transaction.atomic
def importar_nfe(xml_file):
    data = parse_nfe_xml(xml_file)
    if NotaFiscalEntrada.objects.filter(chave_acesso=data.chave_acesso).exists():
        raise ValidationError('Esta NF-e já foi importada.')

    fornecedor, _created = Fornecedor.objects.get_or_create(
        cnpj=data.emitente_cnpj,
        defaults={
            'razao_social': data.emitente_razao_social,
            'nome_fantasia': data.emitente_razao_social,
        },
    )

    nota = NotaFiscalEntrada.objects.create(
        chave_acesso=data.chave_acesso,
        numero=data.numero,
        serie=data.serie,
        data_emissao=data.data_emissao,
        emitente_cnpj=data.emitente_cnpj,
        emitente_razao_social=data.emitente_razao_social,
        valor_total=data.valor_total,
        fornecedor=fornecedor,
    )
    for item in data.itens:
        ItemNotaFiscalEntrada.objects.create(nota=nota, **item.__dict__)
    return nota


@transaction.atomic
def confirmar_nota(nota, item_bindings, usuario=None):
    nota = NotaFiscalEntrada.objects.select_for_update().get(pk=nota.pk)
    if nota.status == NotaFiscalEntrada.Status.CONFIRMADA:
        return nota

    for item in nota.itens.select_for_update():
        binding = item_bindings.get(item.pk, {})
        produto = binding.get('produto')
        if produto is None:
            codigo_interno = binding.get('codigo_interno') or item.codigo_produto or f'NFE-{nota.numero}-{item.numero_item}'
            produto = Produto.objects.create(
                nome=item.descricao,
                descricao=f'Produto criado a partir da NF-e {nota.numero}/{nota.serie}.',
                codigo_interno=codigo_interno,
                codigo_barras=None,
                categoria='Importado NF-e',
                unidade_medida=item.unidade_medida or 'UN',
                preco_custo=item.valor_unitario,
                preco_venda=item.valor_unitario,
                fornecedor=nota.fornecedor,
                ncm=item.ncm,
            )
        item.produto = produto
        item.save(update_fields=['produto'])
        MovimentacaoEstoque.registrar(
            produto=produto,
            tipo_movimentacao=MovimentacaoEstoque.TipoMovimentacao.ENTRADA,
            quantidade=item.quantidade,
            origem=f'NF-e {nota.numero}/{nota.serie}',
            observacao=f'Entrada gerada pela importação da chave {nota.chave_acesso}.',
            usuario=usuario,
        )

    nota.status = NotaFiscalEntrada.Status.CONFIRMADA
    nota.save(update_fields=['status', 'atualizado_em'])
    return nota
