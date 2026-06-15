import administracao.storage
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('administracao', '0005_categoriaproduto'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BackupRegistro',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('BACKUP', 'Backup'), ('RESTAURACAO', 'Restauração')], max_length=12)),
                ('arquivo', models.FileField(blank=True, storage=administracao.storage.armazenamento_backups, upload_to='')),
                ('nome_arquivo', models.CharField(max_length=255)),
                ('tamanho_arquivo', models.BigIntegerField(default=0)),
                ('status', models.CharField(choices=[('SUCESSO', 'Sucesso'), ('ERRO', 'Erro')], max_length=10)),
                ('mensagem', models.TextField(blank=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='backups_registrados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'registro de backup',
                'verbose_name_plural': 'registros de backup',
                'ordering': ['-criado_em'],
            },
        ),
    ]
