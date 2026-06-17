from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='DadosEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('razao_social', models.CharField(blank=True, max_length=180, verbose_name='razão social')),
                ('nome_fantasia', models.CharField(blank=True, max_length=180)),
                ('cnpj', models.CharField(blank=True, max_length=18, verbose_name='CNPJ')),
                ('inscricao_estadual', models.CharField(blank=True, max_length=30, verbose_name='inscrição estadual')),
                ('telefone', models.CharField(blank=True, max_length=20)),
                ('email', models.EmailField(blank=True, max_length=254)),
                ('endereco', models.CharField(blank=True, max_length=255, verbose_name='endereço')),
                ('cidade', models.CharField(blank=True, max_length=100)),
                ('estado', models.CharField(blank=True, max_length=2)),
                ('cep', models.CharField(blank=True, max_length=10, verbose_name='CEP')),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'dados da empresa', 'verbose_name_plural': 'dados da empresa'},
        ),
    ]

