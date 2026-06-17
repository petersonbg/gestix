from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_logatividade'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameField(
            model_name='logatividade',
            old_name='ip',
            new_name='ip_usuario',
        ),
        migrations.AlterField(
            model_name='logatividade',
            name='acao',
            field=models.CharField(
                choices=[
                    ('LOGIN', 'Login'),
                    ('LOGOUT', 'Logout'),
                    ('CRIACAO', 'Criação'),
                    ('EDICAO', 'Edição'),
                    ('EXCLUSAO', 'Exclusão'),
                    ('CANCELAMENTO', 'Cancelamento'),
                    ('FINALIZACAO', 'Finalização'),
                    ('IMPRESSAO', 'Impressão'),
                    ('BACKUP', 'Backup'),
                    ('RESTAURACAO', 'Restauração'),
                    ('PAGAMENTO', 'Pagamento'),
                    ('RECEBIMENTO', 'Recebimento'),
                    ('MOVIMENTACAO_ESTOQUE', 'Movimentação de estoque'),
                    ('ABERTURA_CAIXA', 'Abertura de caixa'),
                    ('FECHAMENTO_CAIXA', 'Fechamento de caixa'),
                    ('ERRO', 'Erro'),
                ],
                max_length=30,
            ),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='objeto_tipo',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='objeto_id',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='user_agent',
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name='logatividade',
            index=models.Index(fields=['-criado_em'], name='accounts_lo_criado__1f6b20_idx'),
        ),
        migrations.AddIndex(
            model_name='logatividade',
            index=models.Index(fields=['usuario'], name='accounts_lo_usuario_d072a8_idx'),
        ),
        migrations.AddIndex(
            model_name='logatividade',
            index=models.Index(fields=['acao'], name='accounts_lo_acao_0dc8fd_idx'),
        ),
        migrations.AddIndex(
            model_name='logatividade',
            index=models.Index(fields=['modulo'], name='accounts_lo_modulo_e4a9e9_idx'),
        ),
    ]
