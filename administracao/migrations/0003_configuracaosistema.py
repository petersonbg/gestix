from django.db import migrations, models


def copiar_configuracao_dashboard(apps, schema_editor):
    ConfiguracaoAntiga = apps.get_model('dashboard', 'ConfiguracaoSistema')
    ConfiguracaoNova = apps.get_model('administracao', 'ConfiguracaoSistema')
    antiga = ConfiguracaoAntiga.objects.order_by('pk').first()
    valores = {}
    if antiga:
        valores = {
            'notificacoes_aniversario_ativas': antiga.notificacoes_aniversario_ativas,
            'dias_antecedencia_aniversario': antiga.dias_antecedencia_aniversario,
        }
    ConfiguracaoNova.objects.update_or_create(pk=1, defaults=valores)


def restaurar_configuracao_dashboard(apps, schema_editor):
    ConfiguracaoAntiga = apps.get_model('dashboard', 'ConfiguracaoSistema')
    ConfiguracaoNova = apps.get_model('administracao', 'ConfiguracaoSistema')
    nova = ConfiguracaoNova.objects.order_by('pk').first()
    if nova:
        ConfiguracaoAntiga.objects.update_or_create(
            pk=1,
            defaults={
                'notificacoes_aniversario_ativas': nova.notificacoes_aniversario_ativas,
                'dias_antecedencia_aniversario': nova.dias_antecedencia_aniversario,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ('administracao', '0002_empresa_dados_completos'),
        ('dashboard', '0001_configuracaosistema'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConfiguracaoSistema',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notificacoes_aniversario_ativas', models.BooleanField(default=True, verbose_name='ativar notificações de aniversário')),
                ('dias_antecedencia_aniversario', models.PositiveIntegerField(default=0, help_text='0 = avisar somente no dia; 7 = avisar com uma semana de antecedência.', verbose_name='dias de antecedência para aviso')),
                ('tempo_logout_inatividade', models.PositiveIntegerField(default=15, help_text='Tempo em minutos antes de encerrar automaticamente uma sessão inativa.', verbose_name='tempo para logout por inatividade (minutos)')),
                ('mostrar_logo_impressoes', models.BooleanField(default=True, verbose_name='mostrar logo nas impressões')),
                ('mostrar_assinatura_cliente', models.BooleanField(default=True, verbose_name='mostrar assinatura do cliente')),
                ('mensagem_rodape_documentos', models.CharField(default='Documento gerado pelo sistema GESTIX.', max_length=255, verbose_name='mensagem de rodapé dos documentos')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'configuração do sistema',
                'verbose_name_plural': 'configuração do sistema',
            },
        ),
        migrations.AddConstraint(
            model_name='configuracaosistema',
            constraint=models.CheckConstraint(condition=models.Q(('id', 1)), name='configuracao_sistema_registro_unico'),
        ),
        migrations.RunPython(copiar_configuracao_dashboard, restaurar_configuracao_dashboard),
    ]
