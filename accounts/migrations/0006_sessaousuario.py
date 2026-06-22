import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_alter_perfilusuario_options_alter_logatividade_acao'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SessaoUsuario',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(max_length=40, unique=True, verbose_name='chave da sessão')),
                ('ip_usuario', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP')),
                ('user_agent', models.TextField(blank=True)),
                ('data_login', models.DateTimeField(auto_now_add=True)),
                ('ultimo_acesso', models.DateTimeField(default=django.utils.timezone.now)),
                ('ativa', models.BooleanField(default=True)),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sessoes_gestix', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'sessão de usuário',
                'verbose_name_plural': 'sessões de usuários',
                'ordering': ['-data_login'],
                'indexes': [
                    models.Index(fields=['usuario', 'ativa'], name='accounts_se_usuario_610e01_idx'),
                    models.Index(fields=['ultimo_acesso'], name='accounts_se_ultimo__e4eace_idx'),
                ],
                'constraints': [
                    models.UniqueConstraint(condition=models.Q(('ativa', True)), fields=('usuario',), name='accounts_uma_sessao_ativa_por_usuario'),
                ],
            },
        ),
    ]
