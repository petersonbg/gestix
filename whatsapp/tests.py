import sys
from types import SimpleNamespace
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.urls import reverse

from accounts.models import LogAtividade, PerfilUsuario
from clientes.models import Cliente
from contas_receber.models import ContaReceber
from orcamentos.models import Orcamento
from ordens_servico.models import OrdemServico
from vendas.models import Venda

from .models import ConfiguracaoWhatsApp, FilaMensagemWhatsApp, MensagemWhatsApp, ModeloMensagemWhatsApp
from .services import (
    ZernioProvider,
    gerar_link_whatsapp,
    limpar_telefone,
    processar_fila_whatsapp,
    renderizar_modelo,
    validar_telefone,
)


def requests_fake(post):
    return SimpleNamespace(
        post=post,
        Timeout=TimeoutError,
        RequestException=Exception,
    )


class WhatsAppServicesTests(TestCase):
    def test_limpa_valida_e_gera_link_whatsapp(self):
        self.assertEqual(limpar_telefone('(11) 99999-8888'), '5511999998888')
        self.assertEqual(validar_telefone('11 99999-8888'), '5511999998888')
        self.assertEqual(
            gerar_link_whatsapp('(11) 99999-8888', 'Olá cliente'),
            'https://wa.me/5511999998888?text=Ol%C3%A1%20cliente',
        )

    def test_renderiza_apenas_variaveis_permitidas(self):
        modelo = type('Modelo', (), {'mensagem': 'Olá {cliente_nome}, {empresa_nome} em {data}.'})()
        mensagem = renderizar_modelo(modelo, {
            'cliente_nome': 'Ana',
            'empresa_nome': 'AXIORA ERP',
            'data': '26/06/2026',
        })
        self.assertEqual(mensagem, 'Olá Ana, AXIORA ERP em 26/06/2026.')

    def test_modelo_bloqueia_variavel_nao_permitida(self):
        modelo = ModeloMensagemWhatsApp(nome='Teste', tipo='AVULSA', mensagem='Olá {cliente_nome} {senha}')
        with self.assertRaises(ValidationError) as contexto:
            modelo.full_clean()
        self.assertIn('mensagem', contexto.exception.message_dict)
        self.assertIn('{senha}', contexto.exception.message_dict['mensagem'][0])


class WhatsAppManualEnvioTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(username='gerente-whatsapp', password='senha')
        PerfilUsuario.objects.create(usuario=cls.usuario, perfil=PerfilUsuario.Perfil.GERENTE)
        cls.cliente = Cliente.objects.create(
            nome='Cliente WhatsApp',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='123.456.789-09',
            telefone='(11) 99999-8888',
        )

    def setUp(self):
        self.client.login(username='gerente-whatsapp', password='senha')

    def test_migration_cria_modelos_padrao(self):
        nomes = set(ModeloMensagemWhatsApp.objects.values_list('nome', flat=True))
        self.assertIn('Cobrança', nomes)
        self.assertIn('Aniversário', nomes)
        self.assertIn('Orçamento', nomes)
        self.assertIn('Ordem de Serviço finalizada', nomes)
        self.assertIn('Venda finalizada', nomes)

    def test_preview_renderiza_modelo_com_cliente_e_empresa(self):
        modelo = ModeloMensagemWhatsApp.objects.get(nome='Aniversário')
        response = self.client.get(reverse('whatsapp:preview_modelo'), {
            'cliente': self.cliente.pk,
            'modelo': modelo.pk,
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['telefone'], '5511999998888')
        self.assertIn('Cliente WhatsApp', data['mensagem'])

    def test_envio_manual_registra_historico_e_abre_whatsapp_web(self):
        modelo = ModeloMensagemWhatsApp.objects.get(nome='Aniversário')
        response = self.client.post(reverse('whatsapp:enviar'), {
            'cliente': self.cliente.pk,
            'telefone': '(11) 99999-8888',
            'modelo': modelo.pk,
            'mensagem': 'Olá Cliente WhatsApp',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'https://wa.me/5511999998888')
        mensagem = MensagemWhatsApp.objects.get()
        self.assertEqual(mensagem.cliente, self.cliente)
        self.assertEqual(mensagem.telefone, '5511999998888')
        self.assertEqual(mensagem.tipo, modelo.tipo)
        self.assertEqual(mensagem.modo_envio, ConfiguracaoWhatsApp.ModoEnvio.WHATSAPP_WEB)
        self.assertEqual(mensagem.status, MensagemWhatsApp.Status.ENVIADA)
        self.assertEqual(mensagem.usuario, self.usuario)
        self.assertIsNotNone(mensagem.data_envio)
        self.assertTrue(LogAtividade.objects.filter(modulo='whatsapp', descricao__icontains='mensagem enviada').exists())


class WhatsAppApiProviderTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(username='api-whatsapp', password='senha')
        cls.cliente = Cliente.objects.create(
            nome='Cliente API',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='987.654.321-00',
            telefone='(21) 98888-7777',
        )

    def setUp(self):
        self.configuracao = ConfiguracaoWhatsApp.objects.create(
            modo_envio=ConfiguracaoWhatsApp.ModoEnvio.API,
            provedor_api=ConfiguracaoWhatsApp.ProvedorAPI.ZERNIO,
            api_url='https://api.example.test/send',
            api_token='token-super-secreto',
            numero_remetente='5511999990000',
            ativo=True,
        )

    def test_configuracao_api_bloqueia_url_local(self):
        configuracao = ConfiguracaoWhatsApp(
            modo_envio=ConfiguracaoWhatsApp.ModoEnvio.API,
            provedor_api=ConfiguracaoWhatsApp.ProvedorAPI.OUTRO,
            api_url='http://127.0.0.1:8000/send',
            api_token='token-super-secreto',
            ativo=False,
        )
        with self.assertRaises(ValidationError) as contexto:
            configuracao.full_clean()
        self.assertIn('api_url', contexto.exception.message_dict)

    def test_zernio_provider_envia_payload_generico_e_registra_historico(self):
        post = Mock()
        response = Mock(status_code=200, text='')
        response.json.return_value = {'id': 'abc123'}
        post.return_value = response

        with patch.dict(sys.modules, {'requests': requests_fake(post)}):
            resultado = ZernioProvider(self.configuracao).send_message(
                '(21) 98888-7777',
                'Mensagem API',
                contexto={'cliente': self.cliente, 'usuario': self.usuario, 'tipo': 'COBRANCA'},
            )

        self.assertTrue(resultado.sucesso)
        post.assert_called_once()
        _, kwargs = post.call_args
        self.assertEqual(kwargs['json'], {
            'telefone': '5521988887777',
            'mensagem': 'Mensagem API',
            'numero_remetente': '5511999990000',
        })
        self.assertNotIn('token-super-secreto', resultado.resposta_api)
        historico = MensagemWhatsApp.objects.get()
        self.assertEqual(historico.status, MensagemWhatsApp.Status.ENVIADA)
        self.assertEqual(historico.modo_envio, ConfiguracaoWhatsApp.ModoEnvio.API)
        self.assertEqual(historico.cliente, self.cliente)
        self.assertEqual(historico.usuario, self.usuario)
        self.assertIsNotNone(historico.data_envio)

    def test_api_trata_erro_de_autenticacao_sem_expor_token(self):
        post = Mock()
        response = Mock(status_code=401, text='token-super-secreto inválido')
        response.json.side_effect = ValueError('json inválido')
        post.return_value = response

        with patch.dict(sys.modules, {'requests': requests_fake(post)}):
            resultado = ZernioProvider(self.configuracao).send_message('21 98888-7777', 'Mensagem API')

        self.assertFalse(resultado.sucesso)
        self.assertEqual(resultado.status, MensagemWhatsApp.Status.ERRO)
        self.assertIn('autenticação', resultado.erro)
        historico = MensagemWhatsApp.objects.get()
        self.assertNotIn('token-super-secreto', historico.resposta_api)
        self.assertIn('[removido]', historico.resposta_api)

    def test_processar_fila_envia_pendentes_e_atualiza_item(self):
        post = Mock()
        response = Mock(status_code=200, text='')
        response.json.return_value = {'ok': True}
        post.return_value = response
        item = FilaMensagemWhatsApp.objects.create(
            cliente=self.cliente,
            telefone='21 98888-7777',
            tipo='AVULSA',
            mensagem='Mensagem da fila',
            usuario_criacao=self.usuario,
        )

        with patch.dict(sys.modules, {'requests': requests_fake(post)}):
            resultado = processar_fila_whatsapp()

        item.refresh_from_db()
        self.assertEqual(resultado, {'processadas': 1, 'enviadas': 1, 'erros': 0})
        self.assertEqual(item.status, FilaMensagemWhatsApp.Status.ENVIADA)
        self.assertEqual(item.tentativas, 1)
        self.assertEqual(item.erro, '')
        self.assertEqual(MensagemWhatsApp.objects.count(), 1)

    def test_processar_fila_ignora_item_agendado_para_o_futuro(self):
        item = FilaMensagemWhatsApp.objects.create(
            cliente=self.cliente,
            telefone='21 98888-7777',
            tipo='AVULSA',
            mensagem='Mensagem futura',
            usuario_criacao=self.usuario,
            agendada_para=timezone.now() + timedelta(days=1),
        )

        resultado = processar_fila_whatsapp()

        item.refresh_from_db()
        self.assertEqual(resultado, {'processadas': 0, 'enviadas': 0, 'erros': 0})
        self.assertEqual(item.status, FilaMensagemWhatsApp.Status.PENDENTE)
        self.assertEqual(item.tentativas, 0)
        self.assertEqual(MensagemWhatsApp.objects.count(), 0)

    def test_management_command_processa_fila(self):
        post = Mock()
        response = Mock(status_code=200, text='')
        response.json.return_value = {'ok': True}
        post.return_value = response
        FilaMensagemWhatsApp.objects.create(
            cliente=self.cliente,
            telefone='21 98888-7777',
            tipo='AVULSA',
            mensagem='Mensagem da fila',
            usuario_criacao=self.usuario,
        )

        with patch.dict(sys.modules, {'requests': requests_fake(post)}):
            call_command('processar_fila_whatsapp')

        self.assertEqual(FilaMensagemWhatsApp.objects.get().status, FilaMensagemWhatsApp.Status.ENVIADA)

class WhatsAppIntegracoesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user(username='integracao-whatsapp', password='senha')
        PerfilUsuario.objects.create(usuario=cls.usuario, perfil=PerfilUsuario.Perfil.GERENTE)
        cls.cliente = Cliente.objects.create(
            nome='Cliente Integracao',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='111.444.777-35',
            telefone='(31) 99999-0000',
            data_nascimento=date(1990, 6, 26),
        )
        cls.cliente_sem_telefone = Cliente.objects.create(
            nome='Cliente Sem Telefone',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='123.123.123-87',
            telefone='',
        )
        cls.venda = Venda.objects.create(
            cliente=cls.cliente,
            usuario=cls.usuario,
            total=Decimal('150.00'),
            status=Venda.Status.FINALIZADA,
        )
        cls.conta = ContaReceber.objects.create(
            venda=cls.venda,
            cliente=cls.cliente,
            numero_parcela=1,
            total_parcelas=1,
            data_vencimento=date(2026, 7, 10),
            valor=Decimal('150.00'),
        )
        cls.orcamento = Orcamento.objects.create(cliente=cls.cliente, usuario=cls.usuario, total=Decimal('200.00'))
        cls.ordem = OrdemServico.objects.create(
            cliente=cls.cliente,
            responsavel=cls.usuario,
            descricao_problema='Manutenção preventiva',
        )

    def setUp(self):
        self.client.login(username='integracao-whatsapp', password='senha')

    def test_botao_em_cliente(self):
        response = self.client.get(reverse('clientes:detail', kwargs={'pk': self.cliente.pk}))
        self.assertContains(response, 'Enviar WhatsApp')
        self.assertContains(response, f'?origem=cliente&id={self.cliente.pk}')

    def test_cobranca_com_variaveis(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'cobranca', 'id': self.conta.pk})
        self.assertContains(response, 'Cliente Integracao')
        self.assertContains(response, 'R$ 150,00')
        self.assertContains(response, '10/07/2026')

    def test_aniversario_com_variaveis(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'aniversario', 'id': self.cliente.pk})
        self.assertContains(response, 'Cliente Integracao')
        self.assertContains(response, 'feliz aniversário')

    def test_orcamento_com_variaveis(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'orcamento', 'id': self.orcamento.pk})
        self.assertContains(response, 'Cliente Integracao')
        self.assertContains(response, f'orçamento nº {self.orcamento.pk}')

    def test_os_com_variaveis(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'ordem_servico', 'id': self.ordem.pk})
        self.assertContains(response, 'Cliente Integracao')
        self.assertContains(response, self.ordem.numero)

    def test_venda_com_variaveis(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'venda', 'id': self.venda.pk})
        self.assertContains(response, 'Cliente Integracao')
        self.assertContains(response, f'venda nº {self.venda.pk}')

    def test_origem_invalida_retorna_404(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'invalida', 'id': self.cliente.pk})
        self.assertEqual(response.status_code, 404)

    def test_bloqueio_sem_telefone(self):
        response = self.client.get(reverse('whatsapp:enviar'), {'origem': 'cliente', 'id': self.cliente_sem_telefone.pk})
        self.assertContains(response, 'Cliente sem telefone cadastrado.')
        post = self.client.post(reverse('whatsapp:enviar'), {
            'cliente': self.cliente_sem_telefone.pk,
            'telefone': '',
            'mensagem': 'Teste sem telefone',
        })
        self.assertEqual(post.status_code, 200)
        self.assertContains(post, 'Este campo é obrigatório.')
        self.assertFalse(MensagemWhatsApp.objects.filter(cliente=self.cliente_sem_telefone).exists())