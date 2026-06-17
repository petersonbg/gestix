import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import close_old_connections
from django.utils import timezone

from .forms import EXTENSOES_BACKUP_PERMITIDAS
from .models import BackupRegistro


logger = logging.getLogger(__name__)


class BackupError(Exception):
    pass


def backup_root():
    raiz = Path(settings.BACKUP_ROOT).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    return raiz


def nome_backup(prefixo='gestix_backup'):
    return f'{prefixo}_{timezone.localtime().strftime("%Y%m%d_%H%M%S")}.dump'


def caminho_seguro_backup(nome_arquivo):
    nome = Path(nome_arquivo).name
    caminho = (backup_root() / nome).resolve()
    if backup_root() not in caminho.parents and caminho != backup_root():
        raise BackupError('Caminho de backup inválido.')
    return caminho


def _database_config():
    db = settings.DATABASES['default']
    return {
        'name': db.get('NAME') or os.getenv('DB_NAME', 'gestix'),
        'user': db.get('USER') or os.getenv('DB_USER', 'gestix'),
        'password': db.get('PASSWORD') or os.getenv('DB_PASSWORD', ''),
        'host': db.get('HOST') or os.getenv('DB_HOST', 'localhost'),
        'port': str(db.get('PORT') or os.getenv('DB_PORT', '5432')),
    }


def _env_postgres():
    config = _database_config()
    env = os.environ.copy()
    if config['password']:
        env['PGPASSWORD'] = str(config['password'])
    return config, env


def _executar(comando, *, env=None):
    logger.info('Executando comando de backup/restauração: %s', ' '.join(comando[:2]))
    resultado = subprocess.run(
        comando,
        env=env,
        capture_output=True,
        text=True,
        timeout=60 * 30,
        check=False,
    )
    if resultado.returncode != 0:
        mensagem = (resultado.stderr or resultado.stdout or 'Comando retornou erro.').strip()
        raise BackupError(mensagem[:1000])
    return resultado


def validar_arquivo_backup(caminho):
    caminho = Path(caminho)
    if caminho.suffix.lower() not in EXTENSOES_BACKUP_PERMITIDAS:
        raise ValidationError('Envie um arquivo .dump ou .backup.')
    if not caminho.exists() or not caminho.is_file():
        raise ValidationError('Arquivo de backup não encontrado.')
    if caminho.stat().st_size <= 0:
        raise ValidationError('Arquivo de backup vazio ou inválido.')
    if caminho.stat().st_size > settings.BACKUP_MAX_UPLOAD_SIZE:
        raise ValidationError('O arquivo deve ter no máximo 500 MB.')


def validar_formato_backup(caminho):
    _, env = _env_postgres()
    comando = [
        'pg_restore',
        '--list',
        str(caminho),
    ]
    _executar(comando, env=env)


def registrar_backup(*, tipo, caminho='', usuario=None, status, mensagem=''):
    caminho = Path(caminho) if caminho else None
    nome = caminho.name if caminho else ''
    tamanho = caminho.stat().st_size if caminho and caminho.exists() else 0
    arquivo_relativo = nome if caminho and caminho.exists() else ''
    return BackupRegistro.objects.create(
        tipo=tipo,
        arquivo=arquivo_relativo,
        nome_arquivo=nome,
        tamanho_arquivo=tamanho,
        usuario=usuario,
        status=status,
        mensagem=mensagem[:2000],
    )


def gerar_backup(*, usuario=None, prefixo='gestix_backup', registrar=True):
    caminho = caminho_seguro_backup(nome_backup(prefixo))
    config, env = _env_postgres()
    comando = [
        'pg_dump',
        '-h', config['host'],
        '-p', config['port'],
        '-U', config['user'],
        '-d', config['name'],
        '-Fc',
        '-f', str(caminho),
    ]
    try:
        logger.info('Backup iniciado para o banco %s.', config['name'])
        _executar(comando, env=env)
        logger.info('Backup concluído: %s.', caminho.name)
        if registrar:
            registrar_backup(
                tipo=BackupRegistro.Tipo.BACKUP,
                caminho=caminho,
                usuario=usuario,
                status=BackupRegistro.Status.SUCESSO,
                mensagem='Backup gerado com sucesso.',
            )
        return caminho
    except Exception as exc:
        logger.exception('Erro ao gerar backup.')
        if caminho.exists():
            caminho.unlink()
        if registrar:
            registrar_backup(
                tipo=BackupRegistro.Tipo.BACKUP,
                caminho=caminho,
                usuario=usuario,
                status=BackupRegistro.Status.ERRO,
                mensagem=str(exc),
            )
        raise


def salvar_upload_temporario(arquivo: UploadedFile):
    nome = Path(arquivo.name).name
    extensao = Path(nome).suffix.lower()
    if extensao not in EXTENSOES_BACKUP_PERMITIDAS:
        raise ValidationError('Envie um arquivo .dump ou .backup.')
    destino = Path(tempfile.mkdtemp(prefix='gestix_restore_')) / nome
    with destino.open('wb') as saida:
        for chunk in arquivo.chunks():
            saida.write(chunk)
    validar_arquivo_backup(destino)
    return destino


def restaurar_backup(caminho_arquivo, *, usuario=None, registrar=True, gerar_backup_seguranca=True):
    caminho = Path(caminho_arquivo).resolve()
    validar_arquivo_backup(caminho)
    backup_seguranca = None
    try:
        logger.info('Restauração iniciada a partir de %s.', caminho.name)
        validar_formato_backup(caminho)
        if gerar_backup_seguranca:
            backup_seguranca = gerar_backup(
                usuario=usuario,
                prefixo='gestix_backup_seguro_pre_restore',
                registrar=True,
            )

        config, env = _env_postgres()
        comando = [
            'pg_restore',
            '--clean',
            '--if-exists',
            '--no-owner',
            '-h', config['host'],
            '-p', config['port'],
            '-U', config['user'],
            '-d', config['name'],
            str(caminho),
        ]
        _executar(comando, env=env)
        close_old_connections()
        mensagem = 'Restauração concluída com sucesso.'
        if backup_seguranca:
            mensagem += f' Backup de segurança: {backup_seguranca.name}.'
        logger.info('Restauração concluída.')
        if registrar:
            registrar_backup(
                tipo=BackupRegistro.Tipo.RESTAURACAO,
                caminho=caminho,
                usuario=usuario,
                status=BackupRegistro.Status.SUCESSO,
                mensagem=mensagem,
            )
        return caminho
    except Exception as exc:
        logger.exception('Erro ao restaurar backup.')
        if registrar:
            registrar_backup(
                tipo=BackupRegistro.Tipo.RESTAURACAO,
                caminho=caminho,
                usuario=usuario,
                status=BackupRegistro.Status.ERRO,
                mensagem=str(exc),
            )
        raise


def limpar_temporario(caminho):
    caminho = Path(caminho)
    shutil.rmtree(caminho.parent, ignore_errors=True)

