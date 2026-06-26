from django.core.management.base import BaseCommand

from whatsapp.services import processar_fila_whatsapp


class Command(BaseCommand):
    help = 'Processa manualmente mensagens pendentes da fila de WhatsApp via API configurada.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limite',
            type=int,
            default=None,
            help='Quantidade máxima de mensagens pendentes a processar.',
        )

    def handle(self, *args, **options):
        resultado = processar_fila_whatsapp(limite=options.get('limite'))
        self.stdout.write(self.style.SUCCESS(
            'Fila WhatsApp processada: '
            f"{resultado['processadas']} processadas, "
            f"{resultado['enviadas']} enviadas, "
            f"{resultado['erros']} com erro."
        ))