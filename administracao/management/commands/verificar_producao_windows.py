import logging
import shutil
import socket
import subprocess
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


logger = logging.getLogger(__name__)


class Resultado:
    OK = 'OK'
    ALERTA = 'ALERTA'
    ERRO = 'ERRO'


class Command(BaseCommand):
    help = 'Verifica se o AXIORA ERP esta pronto para producao local em Windows sem Docker.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--sem-cor',
            action='store_true',
            help='Mantem a saida sem estilos de cor.',
        )

    def handle(self, *args, **options):
        self.sem_cor = options['sem_cor']
        resultados = []
        logger.info('Verificacao de producao Windows iniciada.')

        self.garantir_arquivos_log()
        resultados.extend(self.verificar_configuracoes())
        resultados.extend(self.verificar_postgresql())
        resultados.extend(self.verificar_migrations())
        resultados.extend(self.verificar_diretorios())
        resultados.extend(self.verificar_staticfiles())
        resultados.extend(self.verificar_superusuario())

        self.gerar_diagnostico(resultados)
        self.exibir_resultados(resultados)

        erros = [item for item in resultados if item[0] == Resultado.ERRO]
        alertas = [item for item in resultados if item[0] == Resultado.ALERTA]
        if erros:
            logger.error('Verificacao de producao Windows concluida com erros.')
            raise SystemExit(1)
        if alertas:
            logger.warning('Verificacao de producao Windows concluida com alertas.')
        else:
            logger.info('Verificacao de producao Windows concluida com sucesso.')

    def item(self, status, titulo, detalhe=''):
        return status, titulo, detalhe

    def garantir_arquivos_log(self):
        Path(settings.LOG_DIR).mkdir(parents=True, exist_ok=True)
        for nome in ('gestix.log', 'errors.log'):
            caminho = Path(settings.LOG_DIR) / nome
            caminho.touch(exist_ok=True)

    def verificar_configuracoes(self):
        resultados = []
        if settings.DEBUG:
            resultados.append(self.item(Resultado.ERRO, 'DEBUG', 'DEBUG deve estar False em producao.'))
        else:
            resultados.append(self.item(Resultado.OK, 'DEBUG', 'DEBUG=False.'))

        if settings.RUNNING_IN_DOCKER:
            resultados.append(self.item(Resultado.ALERTA, 'RUNNING_IN_DOCKER', 'Esperado False para producao Windows sem Docker.'))
        else:
            resultados.append(self.item(Resultado.OK, 'RUNNING_IN_DOCKER', 'False.'))

        if not getattr(settings, 'SERVER_MODE', False):
            resultados.append(self.item(Resultado.ALERTA, 'SERVER_MODE', 'Recomendado SERVER_MODE=True em producao local.'))
        else:
            resultados.append(self.item(Resultado.OK, 'SERVER_MODE', 'True.'))

        if len(settings.SECRET_KEY) < 50 or settings.SECRET_KEY in {'change-me-in-production', 'alterar-esta-chave'}:
            resultados.append(self.item(Resultado.ERRO, 'SECRET_KEY', 'Configure uma SECRET_KEY longa e exclusiva em config/.env.'))
        else:
            resultados.append(self.item(Resultado.OK, 'SECRET_KEY', 'Configurada.'))

        if not settings.ALLOWED_HOSTS:
            resultados.append(self.item(Resultado.ERRO, 'ALLOWED_HOSTS', 'Configure hosts permitidos em config/.env.'))
        else:
            resultados.append(self.item(Resultado.OK, 'ALLOWED_HOSTS', ', '.join(settings.ALLOWED_HOSTS)))
        return resultados

    def verificar_postgresql(self):
        resultados = []
        psql = shutil.which('psql')
        pg_isready = shutil.which('pg_isready')
        resultados.append(self.item(Resultado.OK if psql else Resultado.ALERTA, 'PostgreSQL client', psql or 'psql nao encontrado no PATH.'))

        db = settings.DATABASES['default']
        if pg_isready:
            comando = [
                pg_isready,
                '-h', str(db.get('HOST') or 'localhost'),
                '-p', str(db.get('PORT') or '5432'),
                '-d', str(db.get('NAME')),
                '-U', str(db.get('USER')),
            ]
            processo = subprocess.run(comando, capture_output=True, text=True, check=False)
            status = Resultado.OK if processo.returncode == 0 else Resultado.ERRO
            resultados.append(self.item(status, 'Servico PostgreSQL', (processo.stdout or processo.stderr).strip()))
        else:
            resultados.append(self.item(Resultado.ALERTA, 'Servico PostgreSQL', 'pg_isready nao encontrado; validando pela conexao Django.'))

        try:
            connection.ensure_connection()
            with connection.cursor() as cursor:
                cursor.execute('select current_database(), current_user')
                database, user = cursor.fetchone()
            resultados.append(self.item(Resultado.OK, 'Conexao com banco', f'Banco={database}; usuario={user}.'))
        except Exception as exc:
            logger.exception('Falha na conexao com o banco PostgreSQL.')
            resultados.append(self.item(Resultado.ERRO, 'Conexao com banco', str(exc)))
        return resultados

    def verificar_migrations(self):
        try:
            executor = MigrationExecutor(connection)
            pendentes = executor.migration_plan(executor.loader.graph.leaf_nodes())
            if pendentes:
                return [self.item(Resultado.ERRO, 'Migrations', f'{len(pendentes)} migration(s) pendente(s).')]
            return [self.item(Resultado.OK, 'Migrations', 'Todas aplicadas.')]
        except Exception as exc:
            logger.exception('Falha ao verificar migrations.')
            return [self.item(Resultado.ERRO, 'Migrations', str(exc))]

    def verificar_diretorios(self):
        diretorios = {
            'logs': Path(settings.LOG_DIR),
            'backups': Path(settings.BACKUP_ROOT),
            'media': Path(settings.MEDIA_ROOT),
            'staticfiles': Path(settings.STATIC_ROOT),
            'config': Path(settings.BASE_DIR) / 'config',
        }
        resultados = []
        for nome, caminho in diretorios.items():
            try:
                caminho.mkdir(parents=True, exist_ok=True)
                teste = caminho / '.gestix_write_test'
                teste.write_text('ok', encoding='utf-8')
                teste.unlink()
                resultados.append(self.item(Resultado.OK, f'Diretorio {nome}', str(caminho)))
            except Exception as exc:
                logger.exception('Falha de permissao no diretorio %s.', caminho)
                resultados.append(self.item(Resultado.ERRO, f'Diretorio {nome}', str(exc)))
        return resultados

    def verificar_staticfiles(self):
        static_root = Path(settings.STATIC_ROOT)
        if not static_root.exists():
            return [self.item(Resultado.ERRO, 'Staticfiles', f'{static_root} nao existe. Execute collectstatic.')]
        arquivos = [item for item in static_root.rglob('*') if item.is_file()]
        if not arquivos:
            return [self.item(Resultado.ALERTA, 'Staticfiles', 'Diretorio vazio. Execute collectstatic.')]
        return [self.item(Resultado.OK, 'Staticfiles', f'{len(arquivos)} arquivo(s) encontrados.')]

    def verificar_superusuario(self):
        try:
            existe = get_user_model().objects.filter(is_superuser=True, is_active=True).exists()
            if existe:
                return [self.item(Resultado.OK, 'Superusuario', 'Existe ao menos um superusuario ativo.')]
            return [self.item(Resultado.ALERTA, 'Superusuario', 'Crie um superusuario com createsuperuser.')]
        except Exception as exc:
            return [self.item(Resultado.ERRO, 'Superusuario', str(exc))]

    def ip_local(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(('8.8.8.8', 80))
                return sock.getsockname()[0]
        except Exception:
            try:
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                return 'indisponivel'

    def gerar_diagnostico(self, resultados):
        caminho = Path(settings.LOG_DIR) / 'diagnostico.txt'
        linhas = [
            'DIAGNOSTICO AXIORA ERP - PRODUCAO WINDOWS',
            f'IP local: {self.ip_local()}',
            f'DEBUG: {settings.DEBUG}',
            f'RUNNING_IN_DOCKER: {settings.RUNNING_IN_DOCKER}',
            f'SERVER_MODE: {getattr(settings, "SERVER_MODE", False)}',
            f'ALLOWED_HOSTS: {", ".join(settings.ALLOWED_HOSTS)}',
            f'DATABASE: {settings.DATABASES["default"].get("NAME")}@{settings.DATABASES["default"].get("HOST")}:{settings.DATABASES["default"].get("PORT")}',
            '',
            'RESULTADOS:',
        ]
        linhas.extend(f'[{status}] {titulo}: {detalhe}' for status, titulo, detalhe in resultados)
        caminho.write_text('\n'.join(linhas) + '\n', encoding='utf-8')

    def exibir_resultados(self, resultados):
        for status, titulo, detalhe in resultados:
            mensagem = f'[{status}] {titulo}: {detalhe}'
            if self.sem_cor:
                self.stdout.write(mensagem)
            elif status == Resultado.OK:
                self.stdout.write(self.style.SUCCESS(mensagem))
            elif status == Resultado.ALERTA:
                self.stdout.write(self.style.WARNING(mensagem))
            else:
                self.stdout.write(self.style.ERROR(mensagem))
        self.stdout.write(f'Diagnostico: {Path(settings.LOG_DIR) / "diagnostico.txt"}')
