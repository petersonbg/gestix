from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='ConfiguracaoSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notificacoes_aniversario_ativas', models.BooleanField(default=True, verbose_name='ativar notificações de aniversário')),
                ('dias_antecedencia_aniversario', models.PositiveIntegerField(default=0, help_text='0 = avisar somente no dia; 7 = avisar com uma semana de antecedência.', validators=[django.core.validators.MinValueValidator(0)], verbose_name='dias de antecedência para aviso')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'configuração do sistema',
                'verbose_name_plural': 'configurações do sistema',
            },
        ),
    ]
