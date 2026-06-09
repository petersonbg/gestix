# Generated manually for GESTIX caixa integration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendas', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='venda',
            name='forma_pagamento',
            field=models.CharField(
                choices=[
                    ('DINHEIRO', 'Dinheiro'),
                    ('PIX', 'PIX'),
                    ('CARTAO_CREDITO', 'Cartão de crédito'),
                    ('CARTAO_DEBITO', 'Cartão de débito'),
                    ('BOLETO', 'Boleto'),
                    ('OUTROS', 'Outros'),
                ],
                default='DINHEIRO',
                max_length=20,
                verbose_name='forma de pagamento',
            ),
        ),
    ]
