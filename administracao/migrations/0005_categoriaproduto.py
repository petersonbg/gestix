from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('administracao', '0004_alter_empresa_logo_alter_empresa_logo_impressao')]

    operations = [
        migrations.CreateModel(
            name='CategoriaProduto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('descricao', models.TextField(blank=True, verbose_name='descrição')),
                ('tipo', models.CharField(choices=[('GERAL', 'Geral'), ('VEICULOS', 'Veículos')], default='GERAL', max_length=10)),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'categoria de produto',
                'verbose_name_plural': 'categorias de produtos',
                'ordering': ['nome'],
            },
        ),
    ]

