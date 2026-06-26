from django.db import migrations


MODELOS_PADRAO = [
    {
        'nome': 'Cobrança',
        'tipo': 'COBRANCA',
        'mensagem': 'Olá, {cliente_nome}. Identificamos um valor em aberto de {valor} com vencimento em {vencimento}. Em caso de dúvidas, fale com {empresa_nome}: {empresa_contato}.',
    },
    {
        'nome': 'Aniversário',
        'tipo': 'ANIVERSARIO',
        'mensagem': 'Olá, {cliente_nome}. A equipe {empresa_nome} deseja um feliz aniversário e um excelente dia!',
    },
    {
        'nome': 'Orçamento',
        'tipo': 'ORCAMENTO',
        'mensagem': 'Olá, {cliente_nome}. Seu orçamento nº {numero_orcamento} está disponível. Qualquer dúvida, estamos à disposição. {empresa_nome} - {empresa_contato}.',
    },
    {
        'nome': 'Ordem de Serviço finalizada',
        'tipo': 'ORDEM_SERVICO',
        'mensagem': 'Olá, {cliente_nome}. Sua ordem de serviço nº {numero_os} foi finalizada em {data}. {empresa_nome} - {empresa_contato}.',
    },
    {
        'nome': 'Venda finalizada',
        'tipo': 'VENDA',
        'mensagem': 'Olá, {cliente_nome}. Sua venda nº {numero_venda} foi finalizada. Agradecemos a preferência. {empresa_nome} - {empresa_contato}.',
    },
]


def criar_modelos_padrao(apps, schema_editor):
    ModeloMensagemWhatsApp = apps.get_model('whatsapp', 'ModeloMensagemWhatsApp')
    for dados in MODELOS_PADRAO:
        ModeloMensagemWhatsApp.objects.get_or_create(
            nome=dados['nome'],
            defaults={
                'tipo': dados['tipo'],
                'mensagem': dados['mensagem'],
                'ativo': True,
            },
        )


def remover_modelos_padrao(apps, schema_editor):
    ModeloMensagemWhatsApp = apps.get_model('whatsapp', 'ModeloMensagemWhatsApp')
    ModeloMensagemWhatsApp.objects.filter(nome__in=[item['nome'] for item in MODELOS_PADRAO]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('whatsapp', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(criar_modelos_padrao, remover_modelos_padrao),
    ]