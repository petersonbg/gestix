from datetime import date, timedelta

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from clientes.models import Cliente
from contas_receber.models import ContaReceber
from vendas.models import Venda

from administracao.models import ConfiguracaoSistema
from accounts.models import PerfilUsuario
from .services import buscar_aniversariantes, buscar_aniversariantes_configurados


class AniversariantesServiceTests(TestCase):
    def criar_cliente(self, nome, data_nascimento=None, ativo=True):
        return Cliente.objects.create(
            nome=nome,
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj=f'{nome}-cpf',
            data_nascimento=data_nascimento,
            ativo=ativo,
        )

    def test_cliente_sem_data_nao_gera_notificacao(self):
        self.criar_cliente('Sem Data')
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_cliente_inativo_nao_gera_notificacao(self):
        self.criar_cliente('Inativo', date(1990, 6, 1), ativo=False)
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_aniversario_no_dia_atual(self):
        cliente = self.criar_cliente('Hoje', date(1990, 6, 1))
        resultado = buscar_aniversariantes(0, hoje=date(2026, 6, 1))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 0)
        self.assertEqual(resultado[0].idade, 36)

    def test_aniversario_dentro_do_periodo_de_antecedencia(self):
        cliente = self.criar_cliente('Em Breve', date(1990, 6, 10))
        resultado = buscar_aniversariantes(15, hoje=date(2026, 6, 1))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 9)

    def test_aniversario_fora_do_periodo(self):
        self.criar_cliente('Fora', date(1990, 6, 20))
        self.assertEqual(buscar_aniversariantes(7, hoje=date(2026, 6, 1)), [])

    def test_aniversario_na_virada_do_ano(self):
        cliente = self.criar_cliente('Virada', date(1990, 1, 2))
        resultado = buscar_aniversariantes(7, hoje=date(2026, 12, 28))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].dias_restantes, 5)
        self.assertEqual(resultado[0].data_aniversario_no_ano, date(2027, 1, 2))

    def test_aniversario_29_fevereiro_em_ano_nao_bissexto(self):
        cliente = self.criar_cliente('Bissexto', date(1992, 2, 29))
        resultado = buscar_aniversariantes(0, hoje=date(2027, 2, 28))
        self.assertEqual(resultado[0].cliente, cliente)
        self.assertEqual(resultado[0].data_aniversario_no_ano, date(2027, 2, 28))


class DashboardAniversariantesTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='admin', password='senha')
        PerfilUsuario.objects.create(usuario=self.user, perfil=PerfilUsuario.Perfil.ADMINISTRADOR)
        self.client.login(username='admin', password='senha')

    def test_notificacoes_ativadas_no_dashboard(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = True
        configuracao.dias_antecedencia_aniversario = 7
        configuracao.save()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Aniversariantes')

    def test_notificacoes_desativadas_no_dashboard(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = False
        configuracao.dias_antecedencia_aniversario = 7
        configuracao.save()
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Notificações de aniversário desativadas.')
        self.assertEqual(response.context['aniversariantes'], [])

    def test_configuracao_padrao_e_criada_automaticamente(self):
        ConfiguracaoSistema.objects.all().delete()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        configuracao = ConfiguracaoSistema.objects.get(pk=1)
        self.assertTrue(configuracao.notificacoes_aniversario_ativas)
        self.assertEqual(configuracao.dias_antecedencia_aniversario, 0)
        self.assertEqual(response.context['configuracao_sistema'], configuracao)

    @patch('dashboard.services.buscar_aniversariantes')
    def test_servico_usa_dias_de_antecedencia_configurados(self, buscar_mock):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = True
        configuracao.dias_antecedencia_aniversario = 12
        configuracao.save()
        buscar_mock.return_value = []
        hoje = date(2026, 6, 1)

        configuracao_retornada, aniversariantes = buscar_aniversariantes_configurados(hoje=hoje)

        self.assertEqual(configuracao_retornada, configuracao)
        self.assertEqual(aniversariantes, [])
        buscar_mock.assert_called_once_with(12, hoje=hoje)

    @patch('dashboard.services.buscar_aniversariantes')
    def test_servico_nao_busca_clientes_quando_notificacoes_estao_desativadas(self, buscar_mock):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.notificacoes_aniversario_ativas = False
        configuracao.dias_antecedencia_aniversario = 30
        configuracao.save()

        configuracao_retornada, aniversariantes = buscar_aniversariantes_configurados()

        self.assertEqual(configuracao_retornada, configuracao)
        self.assertEqual(aniversariantes, [])
        buscar_mock.assert_not_called()


class DashboardContasAtrasadasTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='gerente', password='senha')
        self.user.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        self.client.login(username='gerente', password='senha')
        self.cliente = Cliente.objects.create(
            nome='Cliente Atraso',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='atraso-001',
        )
        self.venda = Venda.objects.create(cliente=self.cliente, usuario=self.user)

    def criar_conta(self, *, dias_vencida=1, valor=Decimal('100.00'), status=ContaReceber.Status.ABERTA, indice=1):
        return ContaReceber.objects.create(
            venda=self.venda,
            cliente=self.cliente,
            numero_parcela=indice,
            total_parcelas=10,
            data_vencimento=timezone.localdate() - timedelta(days=dias_vencida),
            valor=valor,
            status=status,
        )

    def test_conta_aberta_vencida_aparece_no_dashboard(self):
        self.criar_conta(dias_vencida=3, valor=Decimal('120.00'))

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'Contas a receber atrasadas')
        self.assertContains(response, 'Cliente Atraso')
        self.assertEqual(response.context['contas_atrasadas_qtd'], 1)

    def test_conta_paga_vencida_nao_aparece(self):
        self.criar_conta(dias_vencida=3, status=ContaReceber.Status.PAGA)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['contas_atrasadas_qtd'], 0)
        self.assertContains(response, 'Nenhuma conta a receber atrasada.')

    def test_conta_cancelada_vencida_nao_aparece(self):
        self.criar_conta(dias_vencida=3, status=ContaReceber.Status.CANCELADA)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['contas_atrasadas_qtd'], 0)
        self.assertContains(response, 'Nenhuma conta a receber atrasada.')

    def test_valor_total_atrasado_eh_calculado_corretamente(self):
        self.criar_conta(dias_vencida=5, valor=Decimal('100.00'), indice=1)
        self.criar_conta(dias_vencida=2, valor=Decimal('50.50'), indice=2)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['contas_atrasadas_total'], Decimal('150.50'))

    def test_lista_limita_a_cinco_registros_mais_antigos(self):
        for indice in range(1, 8):
            self.criar_conta(dias_vencida=indice, valor=Decimal('10.00'), indice=indice)

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.context['contas_atrasadas_qtd'], 7)
        self.assertEqual(len(response.context['contas_atrasadas_lista']), 5)
        self.assertEqual(response.context['contas_atrasadas_lista'][0].data_vencimento, timezone.localdate() - timedelta(days=7))

    def test_usuario_sem_permissao_nao_visualiza_notificacao(self):
        User = get_user_model()
        estoquista = User.objects.create_user(username='estoquista', password='senha')
        estoquista.groups.add(Group.objects.get_or_create(name='Estoquista')[0])
        self.criar_conta(dias_vencida=3)
        self.client.logout()
        self.client.login(username='estoquista', password='senha')

        response = self.client.get(reverse('dashboard'))

        self.assertFalse(response.context['pode_visualizar_contas_atrasadas'])
        self.assertNotContains(response, 'Contas a receber atrasadas')

