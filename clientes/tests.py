from datetime import timedelta

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import Cliente


class ClienteValidacaoTests(TestCase):
    def test_cliente_aceita_cpf_valido(self):
        cliente = Cliente(
            nome='Maria Silva',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='529.982.247-25',
        )

        cliente.full_clean()

    def test_cliente_rejeita_cpf_invalido(self):
        cliente = Cliente(
            nome='Maria Silva',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='111.111.111-11',
        )

        with self.assertRaisesMessage(ValidationError, 'Informe um CPF valido.'):
            cliente.full_clean()

    def test_cliente_aceita_cnpj_valido(self):
        cliente = Cliente(
            nome='Empresa Teste',
            tipo_pessoa=Cliente.TipoPessoa.JURIDICA,
            cpf_cnpj='11.222.333/0001-81',
        )

        cliente.full_clean()

    def test_cliente_rejeita_cnpj_invalido(self):
        cliente = Cliente(
            nome='Empresa Teste',
            tipo_pessoa=Cliente.TipoPessoa.JURIDICA,
            cpf_cnpj='11.222.333/0001-00',
        )

        with self.assertRaisesMessage(ValidationError, 'Informe um CNPJ valido.'):
            cliente.full_clean()

    def test_cliente_rejeita_data_nascimento_futura(self):
        cliente = Cliente(
            nome='Maria Silva',
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj='52998224725',
            data_nascimento=timezone.localdate() + timedelta(days=1),
        )

        with self.assertRaisesMessage(ValidationError, 'A data de nascimento'):
            cliente.full_clean()
