from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ('administracao', '0003_configuracaosistema'),
        ('dashboard', '0001_configuracaosistema'),
    ]

    operations = [
        migrations.DeleteModel(name='ConfiguracaoSistema'),
    ]
