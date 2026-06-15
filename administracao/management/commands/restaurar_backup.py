from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from administracao.backup_service import ErroBackup, restaurar_backup


class Command(BaseCommand):
    help = 'Valida e restaura um backup PostgreSQL, gerando antes um backup de segurança.'

    def add_arguments(self, parser):
        parser.add_argument('caminho_do_arquivo')
        parser.add_argument(
            '--confirmar',
            action='store_true',
            help='Confirma que a restauração substituirá os dados atuais.',
        )

    def handle(self, *args, **options):
        if not options['confirmar']:
            raise CommandError('Use --confirmar para autorizar explicitamente a restauração.')
        caminho = Path(options['caminho_do_arquivo']).expanduser().resolve()
        try:
            registro = restaurar_backup(caminho)
        except ErroBackup as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(registro.mensagem))
