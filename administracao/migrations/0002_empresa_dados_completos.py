import django.core.validators
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('administracao', '0001_initial')]

    operations = [
        migrations.RenameModel(old_name='DadosEmpresa', new_name='Empresa'),
        migrations.RenameField(model_name='empresa', old_name='endereco', new_name='logradouro'),
        migrations.AlterField(model_name='empresa', name='logradouro', field=models.CharField(blank=True, max_length=255)),
        migrations.AlterModelOptions(
            name='empresa',
            options={'verbose_name': 'empresa', 'verbose_name_plural': 'empresa'},
        ),
        migrations.AddField(model_name='empresa', name='inscricao_municipal', field=models.CharField(blank=True, max_length=30, verbose_name='inscrição municipal')),
        migrations.AddField(model_name='empresa', name='numero', field=models.CharField(blank=True, max_length=20, verbose_name='número')),
        migrations.AddField(model_name='empresa', name='complemento', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='empresa', name='bairro', field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name='empresa', name='celular', field=models.CharField(blank=True, max_length=20)),
        migrations.AddField(model_name='empresa', name='whatsapp', field=models.CharField(blank=True, max_length=20, verbose_name='WhatsApp')),
        migrations.AddField(model_name='empresa', name='site', field=models.URLField(blank=True)),
        migrations.AddField(
            model_name='empresa',
            name='logo',
            field=models.FileField(blank=True, upload_to='empresa/logos/', validators=[django.core.validators.FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp', 'svg'])]),
        ),
        migrations.AddField(
            model_name='empresa',
            name='logo_impressao',
            field=models.FileField(blank=True, upload_to='empresa/logos/impressao/', validators=[django.core.validators.FileExtensionValidator(['png', 'jpg', 'jpeg', 'webp', 'svg'])], verbose_name='logo para impressão'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='cor_primaria',
            field=models.CharField(default='#0D6EFD', max_length=7, validators=[django.core.validators.RegexValidator(message='Informe uma cor hexadecimal no formato #RRGGBB.', regex='^#[0-9A-Fa-f]{6}$')], verbose_name='cor primária'),
        ),
        migrations.AddField(
            model_name='empresa',
            name='cor_secundaria',
            field=models.CharField(default='#6C757D', max_length=7, validators=[django.core.validators.RegexValidator(message='Informe uma cor hexadecimal no formato #RRGGBB.', regex='^#[0-9A-Fa-f]{6}$')], verbose_name='cor secundária'),
        ),
        migrations.AddField(model_name='empresa', name='responsavel', field=models.CharField(blank=True, max_length=150, verbose_name='responsável')),
        migrations.AddField(model_name='empresa', name='observacoes', field=models.TextField(blank=True, verbose_name='observações')),
        migrations.AddField(
            model_name='empresa',
            name='criado_em',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddConstraint(
            model_name='empresa',
            constraint=models.CheckConstraint(condition=models.Q(('id', 1)), name='empresa_registro_unico'),
        ),
    ]
