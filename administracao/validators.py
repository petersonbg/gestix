from pathlib import Path
from xml.etree import ElementTree

from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible
from PIL import Image, UnidentifiedImageError


@deconstructible
class ValidadorLogotipo:
    """Valida extensão, tamanho e integridade de logotipos raster ou SVG."""

    def __init__(self, extensoes_permitidas, tamanho_maximo_mb):
        self.extensoes_permitidas = tuple(
            extensao.lower().lstrip('.') for extensao in extensoes_permitidas
        )
        self.tamanho_maximo_mb = tamanho_maximo_mb
        self.tamanho_maximo_bytes = tamanho_maximo_mb * 1024 * 1024

    def __call__(self, arquivo):
        extensao = Path(arquivo.name or '').suffix.lower().lstrip('.')
        if extensao not in self.extensoes_permitidas:
            formatos = ', '.join(extensao.upper() for extensao in self.extensoes_permitidas)
            raise ValidationError(
                f'Formato não permitido. Envie um arquivo nos formatos: {formatos}.',
                code='extensao_invalida',
            )

        tamanho = getattr(arquivo, 'size', None)
        if tamanho is not None and tamanho > self.tamanho_maximo_bytes:
            raise ValidationError(
                f'O arquivo deve ter no máximo {self.tamanho_maximo_mb} MB.',
                code='arquivo_muito_grande',
            )

        if extensao == 'svg':
            self._validar_svg(arquivo)
        else:
            self._validar_raster(arquivo)

    @staticmethod
    def _posicao_atual(arquivo):
        try:
            return arquivo.tell()
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _restaurar_posicao(arquivo, posicao):
        try:
            arquivo.seek(0 if posicao is None else posicao)
        except (AttributeError, OSError):
            pass

    def _validar_raster(self, arquivo):
        posicao = self._posicao_atual(arquivo)
        try:
            arquivo.seek(0)
            with Image.open(arquivo) as imagem:
                formato_esperado = (
                    'JPEG'
                    if Path(arquivo.name).suffix.lower() in {'.jpg', '.jpeg'}
                    else 'PNG'
                )
                if imagem.format != formato_esperado:
                    raise ValueError
                imagem.verify()
        except (AttributeError, OSError, SyntaxError, ValueError, UnidentifiedImageError):
            raise ValidationError(
                'O arquivo de imagem está corrompido ou não é uma imagem válida.',
                code='imagem_corrompida',
            )
        finally:
            self._restaurar_posicao(arquivo, posicao)

    def _validar_svg(self, arquivo):
        posicao = self._posicao_atual(arquivo)
        try:
            arquivo.seek(0)
            conteudo = arquivo.read()
            if isinstance(conteudo, str):
                conteudo = conteudo.encode('utf-8')
            conteudo_maiusculo = conteudo.upper()
            if b'<!DOCTYPE' in conteudo_maiusculo or b'<!ENTITY' in conteudo_maiusculo:
                raise ValueError
            raiz = ElementTree.fromstring(conteudo)
            nome_tag = raiz.tag.rsplit('}', 1)[-1].lower()
            if nome_tag != 'svg':
                raise ValueError
        except (AttributeError, ElementTree.ParseError, OSError, TypeError, UnicodeError, ValueError):
            raise ValidationError(
                'O arquivo SVG está corrompido ou não é um SVG válido.',
                code='svg_corrompido',
            )
        finally:
            self._restaurar_posicao(arquivo, posicao)


validador_logo_sistema = ValidadorLogotipo(
    extensoes_permitidas=('png', 'jpg', 'jpeg', 'svg'),
    tamanho_maximo_mb=2,
)
validador_logo_impressao = ValidadorLogotipo(
    extensoes_permitidas=('png', 'svg'),
    tamanho_maximo_mb=5,
)
