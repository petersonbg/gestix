from django.core.management.base import BaseCommand, CommandError

from administracao.backup_services import restaurar_backup


class Command(BaseCommand):
    help = 'Restaura um backup PostgreSQL do AXIORA ERP em formato .dump ou .backup.'

    def add_arguments(self, parser):
        parser.add_argument('caminho_do_arquivo')
        parser.add_argument(
            '--sem-backup-seguranca',
            action='store_true',
            help='Nao gera backup automatico antes de restaurar.',
        )

    def handle(self, *args, **options):
        try:
            restaurar_backup(
                options['caminho_do_arquivo'],
                gerar_backup_seguranca=not options['sem_backup_seguranca'],
            )
        except Exception as exc:
            raise CommandError(f'Erro ao restaurar backup: {exc}') from exc
        self.stdout.write(self.style.SUCCESS('Backup restaurado com sucesso.'))
