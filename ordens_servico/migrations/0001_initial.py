from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


SERVICOS_INICIAIS = ['Manutenção', 'Revisão', 'Instalação', 'Troca de peça', 'Diagnóstico técnico']


def criar_servicos_iniciais(apps, schema_editor):
    Servico = apps.get_model('ordens_servico', 'Servico')
    for nome in SERVICOS_INICIAIS:
        Servico.objects.get_or_create(nome=nome, defaults={'valor_padrao': Decimal('0.00'), 'ativo': True})


def remover_servicos_iniciais(apps, schema_editor):
    apps.get_model('ordens_servico', 'Servico').objects.filter(nome__in=SERVICOS_INICIAIS).delete()


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('clientes', '0002_cliente_inscricao_estadual_data_nascimento'),
        ('produtos', '0002_produto_estoque_atual'),
    ]
    operations = [
        migrations.CreateModel(
            name='Servico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150)),
                ('descricao', models.TextField(blank=True, verbose_name='descrição')),
                ('valor_padrao', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))], verbose_name='valor padrão')),
                ('ativo', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={'verbose_name': 'serviço', 'verbose_name_plural': 'serviços', 'ordering': ['nome']},
        ),
        migrations.CreateModel(
            name='OrdemServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(blank=True, max_length=20, unique=True)),
                ('data_abertura', models.DateTimeField(default=django.utils.timezone.now)),
                ('data_previsao', models.DateField(blank=True, null=True, verbose_name='data de previsão')),
                ('data_finalizacao', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('ABERTA', 'Aberta'), ('EM_ANDAMENTO', 'Em andamento'), ('AGUARDANDO_PECA', 'Aguardando peça'), ('CONCLUIDA', 'Concluída'), ('CANCELADA', 'Cancelada'), ('ENTREGUE', 'Entregue')], default='ABERTA', max_length=20)),
                ('descricao_problema', models.TextField(verbose_name='descrição do problema')),
                ('diagnostico', models.TextField(blank=True, verbose_name='diagnóstico')),
                ('solucao', models.TextField(blank=True, verbose_name='solução')),
                ('observacoes', models.TextField(blank=True, verbose_name='observações')),
                ('subtotal_servicos', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('subtotal_produtos', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('desconto', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('total', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12)),
                ('estoque_baixado', models.BooleanField(default=False, editable=False)),
                ('forma_pagamento', models.CharField(blank=True, choices=[('DINHEIRO', 'Dinheiro'), ('PIX', 'PIX'), ('CARTAO_DEBITO', 'Cartão de débito'), ('CARTAO_CREDITO', 'Cartão de crédito'), ('BOLETO', 'Boleto'), ('CREDIARIO', 'Crediário'), ('OUTROS', 'Outros')], max_length=20)),
                ('valor_pago', models.DecimalField(decimal_places=2, default=Decimal('0.00'), max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='ordens_servico', to='clientes.cliente')),
                ('responsavel', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ordens_servico_responsavel', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'ordem de serviço', 'verbose_name_plural': 'ordens de serviço', 'ordering': ['-data_abertura']},
        ),
        migrations.CreateModel(
            name='ItemServicoOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(blank=True, max_length=255)),
                ('quantidade', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), editable=False, max_digits=12)),
                ('ordem_servico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens_servico', to='ordens_servico.ordemservico')),
                ('servico', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='itens_os', to='ordens_servico.servico')),
            ],
        ),
        migrations.CreateModel(
            name='ItemProdutoOS',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('valor_unitario', models.DecimalField(decimal_places=2, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00'))])),
                ('subtotal', models.DecimalField(decimal_places=2, default=Decimal('0.00'), editable=False, max_digits=12)),
                ('ordem_servico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens_produto', to='ordens_servico.ordemservico')),
                ('produto', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='itens_ordem_servico', to='produtos.produto')),
            ],
        ),
        migrations.CreateModel(
            name='HistoricoOrdemServico',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('acao', models.CharField(max_length=40)),
                ('descricao', models.TextField(blank=True, verbose_name='descrição')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('ordem_servico', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='historico', to='ordens_servico.ordemservico')),
                ('usuario', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'histórico da ordem de serviço', 'verbose_name_plural': 'históricos das ordens de serviço', 'ordering': ['-criado_em']},
        ),
        migrations.RunPython(criar_servicos_iniciais, remover_servicos_iniciais),
    ]
