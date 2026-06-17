# Generated manually for GESTIX caixa module

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('vendas', '0002_venda_forma_pagamento'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Caixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_abertura', models.DateTimeField(auto_now_add=True)),
                ('valor_inicial', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('status', models.CharField(choices=[('ABERTO', 'Aberto'), ('FECHADO', 'Fechado')], default='ABERTO', max_length=8)),
                ('observacao_abertura', models.TextField(blank=True, verbose_name='observação de abertura')),
                ('data_fechamento', models.DateTimeField(blank=True, null=True)),
                ('valor_fechamento_informado', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('valor_fechamento_calculado', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('diferenca', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('observacao_fechamento', models.TextField(blank=True, verbose_name='observação de fechamento')),
                ('usuario_abertura', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='caixas_abertos', to=settings.AUTH_USER_MODEL)),
                ('usuario_fechamento', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='caixas_fechados', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'caixa',
                'verbose_name_plural': 'caixas',
                'ordering': ['-data_abertura'],
            },
        ),
        migrations.CreateModel(
            name='MovimentacaoCaixa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('ENTRADA', 'Entrada'), ('SAIDA', 'Saída'), ('SANGRIA', 'Sangria'), ('SUPRIMENTO', 'Suprimento'), ('VENDA', 'Venda'), ('CANCELAMENTO', 'Cancelamento')], max_length=12)),
                ('descricao', models.CharField(max_length=150)),
                ('valor', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('forma_pagamento', models.CharField(choices=[('DINHEIRO', 'Dinheiro'), ('PIX', 'PIX'), ('CARTAO_CREDITO', 'Cartão de crédito'), ('CARTAO_DEBITO', 'Cartão de débito'), ('BOLETO', 'Boleto'), ('OUTROS', 'Outros')], default='DINHEIRO', max_length=20)),
                ('data', models.DateTimeField(auto_now_add=True)),
                ('observacao', models.TextField(blank=True, verbose_name='observação')),
                ('caixa', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes', to='caixa.caixa')),
                ('usuario', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes_caixa', to=settings.AUTH_USER_MODEL)),
                ('venda', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='movimentacoes_caixa', to='vendas.venda')),
            ],
            options={
                'verbose_name': 'movimentação de caixa',
                'verbose_name_plural': 'movimentações de caixa',
                'ordering': ['-data'],
            },
        ),
        migrations.AddConstraint(
            model_name='caixa',
            constraint=models.UniqueConstraint(condition=models.Q(status='ABERTO'), fields=('usuario_abertura',), name='unique_caixa_aberto_por_usuario'),
        ),
    ]

