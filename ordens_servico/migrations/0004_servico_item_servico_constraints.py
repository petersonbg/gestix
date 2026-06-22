from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('ordens_servico', '0003_data_finalizacao_verbose'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='itemservicoos',
            options={
                'verbose_name': 'item de serviço da OS',
                'verbose_name_plural': 'itens de serviço da OS',
            },
        ),
        migrations.AddConstraint(
            model_name='servico',
            constraint=models.CheckConstraint(
                condition=models.Q(valor_padrao__gte=0),
                name='servico_valor_padrao_nao_negativo',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemservicoos',
            constraint=models.CheckConstraint(
                condition=models.Q(quantidade__gt=0),
                name='item_servico_os_quantidade_positiva',
            ),
        ),
        migrations.AddConstraint(
            model_name='itemservicoos',
            constraint=models.CheckConstraint(
                condition=models.Q(valor_unitario__gte=0),
                name='item_servico_os_valor_nao_negativo',
            ),
        ),
    ]

