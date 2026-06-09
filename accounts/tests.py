from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracao.models import ConfiguracaoSistema

from .middleware import ULTIMA_ATIVIDADE_SESSAO


class LogoutInatividadeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-timeout',
            password='senha',
            email='timeout@gestix.test',
        )
        self.client.login(username='admin-timeout', password='senha')

    def definir_ultima_atividade(self, instante):
        session = self.client.session
        session[ULTIMA_ATIVIDADE_SESSAO] = instante.timestamp()
        session.save()

    def test_backend_aplica_tempo_configurado_em_minutos(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 30
        configuracao.save()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertIn(ULTIMA_ATIVIDADE_SESSAO, self.client.session)
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 1798)
        self.assertLessEqual(self.client.session.get_expiry_age(), 1800)

    def test_sessao_expirada_redireciona_para_login(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 1
        configuracao.save()
        self.definir_ultima_atividade(timezone.now() - timedelta(seconds=61))

        response = self.client.get(reverse('dashboard'))

        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sem_configuracao_cria_padrao_de_quinze_minutos(self):
        ConfiguracaoSistema.objects.all().delete()

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        configuracao = ConfiguracaoSistema.objects.get(pk=1)
        self.assertEqual(configuracao.tempo_logout_inatividade, 15)
        self.assertGreaterEqual(self.client.session.get_expiry_age(), 898)
        self.assertLessEqual(self.client.session.get_expiry_age(), 900)

    def test_javascript_recebe_tempo_configurado(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 27
        configuracao.save()

        response = self.client.get(reverse('dashboard'))

        self.assertContains(response, 'const timeoutMinutes = Number(27);')
        self.assertContains(response, reverse('session_keepalive'))
        self.assertContains(response, "window.location.replace(loginPath)")

    def test_keepalive_exige_login_e_renova_atividade(self):
        configuracao = ConfiguracaoSistema.get_solo()
        configuracao.tempo_logout_inatividade = 15
        configuracao.save()
        instante_antigo = timezone.now() - timedelta(minutes=5)
        self.definir_ultima_atividade(instante_antigo)

        response = self.client.post(reverse('session_keepalive'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'ativa': True})
        self.assertGreater(self.client.session[ULTIMA_ATIVIDADE_SESSAO], instante_antigo.timestamp())

        self.client.logout()
        response = self.client.post(reverse('session_keepalive'))
        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('session_keepalive')}",
            fetch_redirect_response=False,
        )
