from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Fornecedor


class FornecedorValidacaoTests(TestCase):
    def test_fornecedor_aceita_cnpj_valido(self):
        fornecedor = Fornecedor(
            razao_social='Fornecedor Teste',
            cnpj='11.222.333/0001-81',
        )

        fornecedor.full_clean()

    def test_fornecedor_rejeita_cnpj_invalido(self):
        fornecedor = Fornecedor(
            razao_social='Fornecedor Teste',
            cnpj='11.222.333/0001-00',
        )

        with self.assertRaisesMessage(ValidationError, 'Informe um CNPJ valido.'):
            fornecedor.full_clean()
