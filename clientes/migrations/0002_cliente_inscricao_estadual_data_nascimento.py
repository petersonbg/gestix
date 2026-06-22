from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='inscricao_estadual',
            field=models.CharField(blank=True, max_length=30, null=True, verbose_name='inscrição estadual'),
        ),
        migrations.AddField(
            model_name='cliente',
            name='data_nascimento',
            field=models.DateField(blank=True, null=True, verbose_name='data de nascimento'),
        ),
    ]

