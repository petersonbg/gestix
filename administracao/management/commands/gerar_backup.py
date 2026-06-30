from django.core.management.base import BaseCommand, CommandError

from administracao.backup_services import gerar_backup


class Command(BaseCommand):
    help = 'Gera um backup PostgreSQL do banco AXIORA ERP em formato custom.'

    def handle(self, *args, **options):
        try:
            caminho = gerar_backup()
        except Exception as exc:
            raise CommandError(f'Erro ao gerar backup: {exc}') from exc
        self.stdout.write(self.style.SUCCESS(f'Backup gerado: {caminho.name}'))
