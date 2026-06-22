import django.db.models.deletion
from django.db import migrations, models


def migrar_categorias_texto(apps, schema_editor):
    Produto = apps.get_model('produtos', 'Produto')
    CategoriaProduto = apps.get_model('administracao', 'CategoriaProduto')
    nomes = (
        Produto.objects.exclude(categoria_texto='')
        .values_list('categoria_texto', flat=True)
        .distinct()
    )
    categorias = {}
    for nome_original in nomes:
        nome = (nome_original or '').strip()
        if not nome:
            continue
        categoria = CategoriaProduto.objects.filter(nome__iexact=nome).first()
        if categoria is None:
            categoria = CategoriaProduto.objects.create(
                nome=nome, tipo='GERAL', ativo=True
            )
        categorias[nome_original] = categoria.pk
    for nome_original, categoria_id in categorias.items():
        Produto.objects.filter(categoria_texto=nome_original).update(categoria_id=categoria_id)


class Migration(migrations.Migration):
    dependencies = [
        ('administracao', '0005_categoriaproduto'),
        ('produtos', '0003_sequenciacodigoproduto_alter_produto_codigo_interno_and_more'),
    ]

    operations = [
        migrations.RenameField(
            model_name='produto',
            old_name='categoria',
            new_name='categoria_texto',
        ),
        migrations.AddField(
            model_name='produto',
            name='categoria',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='produtos',
                to='administracao.categoriaproduto',
            ),
        ),
        migrations.AddField(
            model_name='produto',
            name='chassi',
            field=models.CharField(
                blank=True,
                help_text='Disponível apenas para produtos da categoria Veículos.',
                max_length=50,
                null=True,
                verbose_name='Chassi',
            ),
        ),
        migrations.RunPython(migrar_categorias_texto, migrations.RunPython.noop),
        migrations.RemoveField(model_name='produto', name='categoria_texto'),
    ]

