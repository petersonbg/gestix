import os
import subprocess
from pathlib import Path

from django.conf import settings
from django.db import connection
from django.utils import timezone

from accounts.utils import registrar_log

from .models import BackupRegistro


class ErroBackup(RuntimeError):
    pass


def _configuracao_banco():
    banco = settings.DATABASES['default']
    if banco.get('ENGINE') != 'django.db.backends.postgresql':
        raise ErroBackup('Backup e restauração estão disponíveis apenas para PostgreSQL.')
    return {
        'nome': banco.get('NAME') or '',
        'usuario': banco.get('USER') or '',
        'senha': banco.get('PASSWORD') or '',
        'host': banco.get('HOST') or '',
        'porta': str(banco.get('PORT') or ''),
    }


def _ambiente_postgres():
    ambiente = os.environ.copy()
    senha = _configuracao_banco()['senha']
    if senha:
        ambiente['PGPASSWORD'] = senha
    return ambiente


def _argumentos_conexao():
    banco = _configuracao_banco()
    if not banco['nome'] or not banco['usuario']:
        raise ErroBackup('Configuração do PostgreSQL incompleta para backup/restauração.')
    argumentos = ['-U', banco['usuario'], '-d', banco['nome']]
    if banco['host']:
        argumentos.extend(['-h', banco['host']])
    if banco['porta']:
        argumentos.extend(['-p', banco['porta']])
    return argumentos


def _executar(comando):
    try:
        return subprocess.run(
            comando,
            check=True,
            capture_output=True,
            env=_ambiente_postgres(),
        )
    except FileNotFoundError as exc:
        raise ErroBackup(
            f'Utilitário PostgreSQL não encontrado: {comando[0]}.'
        ) from exc
    except subprocess.CalledProcessError as exc:
        detalhe = (exc.stderr or exc.stdout or b'').decode('utf-8', errors='replace').strip()
        raise ErroBackup(detalhe or 'O utilitário PostgreSQL retornou erro.') from exc


def _modo_execucao():
    return 'Docker' if getattr(settings, 'RUNNING_IN_DOCKER', False) else 'local'


def _caminho_seguro(nome_arquivo):
    raiz = Path(settings.BACKUP_ROOT).resolve()
    raiz.mkdir(parents=True, exist_ok=True)
    nome_seguro = Path(nome_arquivo).name
    if nome_seguro != nome_arquivo or not nome_seguro:
        raise ErroBackup('Nome de arquivo de backup inválido.')
    caminho = (raiz / nome_seguro).resolve()
    if caminho.parent != raiz:
        raise ErroBackup('Caminho de backup inválido.')
    return caminho


def gerar_backup(usuario=None, prefixo='gestix_backup'):
    nome = f'{prefixo}_{timezone.localtime():%Y%m%d_%H%M%S}.dump'
    caminho = _caminho_seguro(nome)
    registro = BackupRegistro.objects.create(
        tipo=BackupRegistro.Tipo.BACKUP,
        nome_arquivo=nome,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        status=BackupRegistro.Status.ERRO,
        mensagem=f'Geração do backup iniciada em ambiente {_modo_execucao()}.',
    )
    try:
        _executar(['pg_dump', *_argumentos_conexao(), '-Fc', '-f', str(caminho)])
        tamanho = caminho.stat().st_size
        if tamanho <= 0:
            raise ErroBackup('O arquivo de backup foi gerado vazio.')
        registro.arquivo.name = nome
        registro.tamanho_arquivo = tamanho
        registro.status = BackupRegistro.Status.SUCESSO
        registro.mensagem = f'Backup gerado com sucesso em ambiente {_modo_execucao()}.'
        registro.save()
        registrar_log(
            usuario, 'BACKUP', 'administracao',
            f'Backup {registro.nome_arquivo} gerado com sucesso.', objeto=registro,
        )
        return registro
    except Exception as exc:
        caminho.unlink(missing_ok=True)
        registro.mensagem = str(exc)
        registro.save(update_fields=['mensagem'])
        registrar_log(
            usuario, 'ERRO', 'administracao',
            f'Erro ao gerar backup {registro.nome_arquivo}: {exc}', objeto=registro,
        )
        if isinstance(exc, ErroBackup):
            raise
        raise ErroBackup(str(exc)) from exc


def validar_arquivo_backup(caminho):
    caminho = Path(caminho).resolve()
    if caminho.suffix.lower() not in {'.dump', '.backup'}:
        raise ErroBackup('Formato inválido. Envie um arquivo .dump ou .backup.')
    if not caminho.is_file() or caminho.stat().st_size <= 0:
        raise ErroBackup('Arquivo de backup inválido ou vazio.')
    _executar(['pg_restore', '--list', str(caminho)])


def restaurar_backup(caminho, usuario=None, nome_arquivo=None):
    caminho = Path(caminho).resolve()
    nome_exibicao = Path(nome_arquivo or caminho.name).name
    try:
        validar_arquivo_backup(caminho)
    except Exception as exc:
        tamanho = caminho.stat().st_size if caminho.exists() and caminho.is_file() else 0
        registro = BackupRegistro.objects.create(
            tipo=BackupRegistro.Tipo.RESTAURACAO,
            nome_arquivo=nome_exibicao,
            tamanho_arquivo=tamanho,
            usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
            status=BackupRegistro.Status.ERRO,
            mensagem=str(exc),
        )
        registrar_log(
            usuario, 'ERRO', 'administracao',
            f'Erro ao validar backup para restauração {nome_exibicao}: {exc}',
            objeto=registro,
        )
        if isinstance(exc, ErroBackup):
            raise
        raise ErroBackup(str(exc)) from exc
    seguranca = gerar_backup(usuario=usuario, prefixo='gestix_pre_restauracao')
    registro = BackupRegistro.objects.create(
        tipo=BackupRegistro.Tipo.RESTAURACAO,
        nome_arquivo=nome_exibicao,
        tamanho_arquivo=caminho.stat().st_size,
        usuario=usuario if getattr(usuario, 'is_authenticated', False) else None,
        status=BackupRegistro.Status.ERRO,
        mensagem=f'Restauração iniciada. Backup de segurança: {seguranca.nome_arquivo}.',
    )
    registrar_log(
        usuario, 'RESTAURACAO', 'administracao',
        f'Restauração iniciada para {registro.nome_arquivo}. Backup de segurança: {seguranca.nome_arquivo}.',
        objeto=registro,
    )
    try:
        connection.close()
        _executar([
            'pg_restore',
            *_argumentos_conexao(),
            '--clean',
            '--if-exists',
            '--no-owner',
            '--no-privileges',
            str(caminho),
        ])
        registro.status = BackupRegistro.Status.SUCESSO
        registro.mensagem = (
            f'Restauração concluída. Backup de segurança: {seguranca.nome_arquivo}.'
        )
        registro.save(update_fields=['status', 'mensagem'])
        registrar_log(
            usuario, 'RESTAURACAO', 'administracao', registro.mensagem, objeto=registro,
        )
        return registro
    except Exception as exc:
        registro.mensagem = (
            f'Falha na restauração: {exc}. '
            f'Backup de segurança disponível: {seguranca.nome_arquivo}.'
        )
        registro.save(update_fields=['mensagem'])
        registrar_log(
            usuario, 'ERRO', 'administracao', registro.mensagem, objeto=registro,
        )
        if isinstance(exc, ErroBackup):
            raise
        raise ErroBackup(str(exc)) from exc


def salvar_upload_temporario(arquivo):
    nome = Path(arquivo.name).name
    caminho = _caminho_seguro(f'temporario_{timezone.now():%Y%m%d%H%M%S%f}_{nome}')
    with caminho.open('wb') as destino:
        for bloco in arquivo.chunks():
            destino.write(bloco)
    return caminho
