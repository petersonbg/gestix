from django.db import migrations, models


def normalizar_acoes_existentes(apps, schema_editor):
    LogAtividade = apps.get_model('accounts', 'LogAtividade')
    aliases = (
        ('login', 'LOGIN'), ('logout', 'LOGOUT'), ('criação', 'CRIACAO'),
        ('edição', 'EDICAO'), ('exclusão', 'EXCLUSAO'),
        ('cancelamento', 'CANCELAMENTO'), ('finalização', 'FINALIZACAO'),
        ('impressão', 'IMPRESSAO'), ('backup', 'BACKUP'),
        ('restauração', 'RESTAURACAO'), ('pagamento', 'PAGAMENTO'),
        ('recebimento', 'RECEBIMENTO'), ('movimentação', 'MOVIMENTACAO_ESTOQUE'),
        ('abertura de caixa', 'ABERTURA_CAIXA'),
        ('fechamento de caixa', 'FECHAMENTO_CAIXA'), ('erro', 'ERRO'),
    )
    for log in LogAtividade.objects.all().only('pk', 'acao').iterator():
        valor = (log.acao or '').casefold()
        novo_valor = next((choice for trecho, choice in aliases if trecho in valor), 'EDICAO')
        LogAtividade.objects.filter(pk=log.pk).update(acao=novo_valor)


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_logatividade'),
    ]

    operations = [
        migrations.RenameField(
            model_name='logatividade',
            old_name='ip',
            new_name='ip_usuario',
        ),
        migrations.RunPython(normalizar_acoes_existentes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='logatividade',
            name='acao',
            field=models.CharField(
                choices=[
                    ('LOGIN', 'Login'), ('LOGOUT', 'Logout'), ('CRIACAO', 'Criação'),
                    ('EDICAO', 'Edição'), ('EXCLUSAO', 'Exclusão'),
                    ('CANCELAMENTO', 'Cancelamento'), ('FINALIZACAO', 'Finalização'),
                    ('IMPRESSAO', 'Impressão'), ('BACKUP', 'Backup'),
                    ('RESTAURACAO', 'Restauração'), ('PAGAMENTO', 'Pagamento'),
                    ('RECEBIMENTO', 'Recebimento'),
                    ('MOVIMENTACAO_ESTOQUE', 'Movimentação de estoque'),
                    ('ABERTURA_CAIXA', 'Abertura de caixa'),
                    ('FECHAMENTO_CAIXA', 'Fechamento de caixa'), ('ERRO', 'Erro'),
                ],
                db_index=True,
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name='logatividade',
            name='modulo',
            field=models.CharField(db_index=True, max_length=80),
        ),
        migrations.AlterField(
            model_name='logatividade',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='objeto_id',
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='objeto_tipo',
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name='logatividade',
            name='user_agent',
            field=models.CharField(blank=True, max_length=500),
        ),
    ]
