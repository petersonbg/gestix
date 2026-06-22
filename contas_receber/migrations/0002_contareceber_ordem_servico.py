import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('contas_receber', '0001_initial'), ('ordens_servico', '0001_initial')]
    operations = [
        migrations.AlterField(
            model_name='contareceber', name='venda',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contas_receber', to='vendas.venda'),
        ),
        migrations.AddField(
            model_name='contareceber', name='ordem_servico',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='contas_receber', to='ordens_servico.ordemservico'),
        ),
        migrations.RemoveConstraint(model_name='contareceber', name='unique_parcela_por_venda'),
        migrations.AddConstraint(model_name='contareceber', constraint=models.UniqueConstraint(condition=models.Q(('venda__isnull', False)), fields=('venda', 'numero_parcela'), name='unique_parcela_por_venda')),
        migrations.AddConstraint(model_name='contareceber', constraint=models.UniqueConstraint(condition=models.Q(('ordem_servico__isnull', False)), fields=('ordem_servico', 'numero_parcela'), name='unique_parcela_por_os')),
    ]
