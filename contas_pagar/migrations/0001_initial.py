# Generated manually for GESTIX contas_pagar module.

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


CATEGORIAS_INICIAIS = [
    'Energia',
    'Ãgua',
    'Internet',
    'Aluguel',
    'Fornecedor',
    'Funcionários',
    'Impostos',
    'Manutenção',
    'Outros',
]


def criar_categorias(apps, schema_editor):
    categoria_model = apps.get_model('contas_pagar', 'CategoriaDespesa')
    for nome in CATEGORIAS_INICIAIS:
        categoria_model.objects.get_or_create(nome=nome, defaults={'ativo': True})


def remover_categorias(apps, schema_editor):
    categoria_model = apps.get_model('contas_pagar', 'CategoriaDespesa')
    categoria_model.objects.filter(nome__in=CATEGORIAS_INICIAIS).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('fornecedores', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaDespesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, unique=True)),
                ('descricao', models.TextField(blank=True, verbose_name='descrição')),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'categoria de despesa',
                'verbose_name_plural': 'categorias de despesa',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='ContaPagar',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=180, verbose_name='descrição')),
                ('data_emissao', models.DateField(default=django.utils.timezone.localdate, verbose_name='data de emissão')),
                ('data_vencimento', models.DateField(verbose_name='data de vencimento')),
                ('data_pagamento', models.DateField(blank=True, null=True, verbose_name='data de pagamento')),
                ('valor', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('valor_pago', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('forma_pagamento', models.CharField(blank=True, choices=[('DINHEIRO', 'Dinheiro'), ('PIX', 'PIX'), ('CARTAO_CREDITO', 'Cartão de crédito'), ('CARTAO_DEBITO', 'Cartão de débito'), ('BOLETO', 'Boleto'), ('TRANSFERENCIA', 'Transferência'), ('OUTROS', 'Outros')], max_length=20)),
                ('status', models.CharField(choices=[('ABERTA', 'Aberta'), ('PAGA', 'Paga'), ('ATRASADA', 'Atrasada'), ('CANCELADA', 'Cancelada')], default='ABERTA', max_length=10)),
                ('observacao', models.TextField(blank=True, verbose_name='observação')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('categoria', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contas_pagar', to='contas_pagar.categoriadespesa')),
                ('fornecedor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contas_pagar', to='fornecedores.fornecedor')),
                ('usuario_criacao', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contas_pagar_criadas', to=settings.AUTH_USER_MODEL)),
                ('usuario_pagamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contas_pagar_pagas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'conta a pagar',
                'verbose_name_plural': 'contas a pagar',
                'ordering': ['data_vencimento', 'descricao'],
            },
        ),
        migrations.RunPython(criar_categorias, remover_categorias),
    ]

