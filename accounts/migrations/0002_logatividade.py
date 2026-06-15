from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0001_create_access_profiles'),
    ]

    operations = [
        migrations.CreateModel(
            name='LogAtividade',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=80)),
                ('modulo', models.CharField(max_length=80)),
                ('descricao', models.TextField(blank=True)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='logs_atividade', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'log de atividade',
                'verbose_name_plural': 'logs de atividade',
                'ordering': ['-criado_em'],
            },
        ),
    ]
