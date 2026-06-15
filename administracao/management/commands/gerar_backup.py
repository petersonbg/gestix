from django.core.management.base import BaseCommand, CommandError

from administracao.backup_service import ErroBackup, gerar_backup


class Command(BaseCommand):
    help = 'Gera um backup PostgreSQL no formato custom e registra a operação.'

    def handle(self, *args, **options):
        try:
            registro = gerar_backup()
        except ErroBackup as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(registro.nome_arquivo))
