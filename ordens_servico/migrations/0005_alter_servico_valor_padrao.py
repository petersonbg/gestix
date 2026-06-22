from decimal import Decimal

from django.db import migrations, models
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):
    dependencies = [
        ('ordens_servico', '0004_servico_item_servico_constraints'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servico',
            name='valor_padrao',
            field=models.DecimalField(
                'valor padrão',
                max_digits=12,
                decimal_places=2,
                default=Decimal('0.00'),
                validators=[MinValueValidator(Decimal('0.00'))],
            ),
        ),
    ]

