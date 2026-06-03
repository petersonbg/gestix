from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente

from .models import ConfiguracaoSistema
from .services import buscar_aniversariantes


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
        self.client.login(username='admin', password='senha')

    def test_notificacoes_ativadas_no_dashboard(self):
        ConfiguracaoSistema.objects.create(notificacoes_aniversario_ativas=True, dias_antecedencia_aniversario=7)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Aniversariantes')

    def test_notificacoes_desativadas_no_dashboard(self):
        ConfiguracaoSistema.objects.create(notificacoes_aniversario_ativas=False, dias_antecedencia_aniversario=7)
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Notificações de aniversário desativadas.')
        self.assertEqual(response.context['aniversariantes'], [])
