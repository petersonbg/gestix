from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from clientes.models import Cliente

from .forms import VendaForm
from .models import Venda


class ClienteBuscaVendaTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username='admin', password='senha', email='admin@example.com')
        self.client.login(username='admin', password='senha')

    def criar_cliente(self, nome, cpf_cnpj, telefone='27999999999', ativo=True):
        return Cliente.objects.create(
            nome=nome,
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            email=f'{nome.lower().replace(" ", ".")}@example.com',
            endereco='Rua das Vendas, 10',
            inscricao_estadual='ISENTO',
            ativo=ativo,
        )

    def test_busca_clientes_exige_login(self):
        self.client.logout()
        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'Jo'})
        self.assertEqual(response.status_code, 302)

    def test_busca_clientes_retorna_vazio_para_consulta_curta(self):
        self.criar_cliente('João da Silva', '12345678900')
        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'J'})
        self.assertEqual(response.json()['results'], [])

    def test_busca_clientes_por_nome_cpf_cnpj_e_telefone(self):
        cliente_nome = self.criar_cliente('João da Silva', '12345678900', telefone='2711111111')
        cliente_cpf = self.criar_cliente('Maria Documento', '98765432100', telefone='2722222222')
        cliente_telefone = self.criar_cliente('Pedro Telefone', '11122233344', telefone='27987654321')

        por_nome = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'João'}).json()['results']
        por_cpf = self.client.get(reverse('vendas:buscar_clientes'), {'q': '654321'}).json()['results']
        por_telefone = self.client.get(reverse('vendas:buscar_clientes'), {'q': '987654'}).json()['results']

        self.assertEqual(por_nome[0]['id'], cliente_nome.pk)
        self.assertEqual(por_cpf[0]['id'], cliente_cpf.pk)
        self.assertEqual(por_telefone[0]['id'], cliente_telefone.pk)

    def test_busca_clientes_exibe_campos_e_limita_dez_ativos(self):
        cliente = self.criar_cliente('Cliente Ativo', '22233344455', telefone='2733333333')
        self.criar_cliente('Cliente Inativo', '99988877766', ativo=False)
        for indice in range(11):
            self.criar_cliente(f'Cliente Limite {indice:02d}', f'800000000{indice:02d}')

        response = self.client.get(reverse('vendas:buscar_clientes'), {'q': 'Cliente'})

        results = response.json()['results']
        self.assertEqual(len(results), 10)
        ids = [item['id'] for item in results]
        self.assertIn(cliente.pk, ids)
        self.assertNotIn(Cliente.objects.get(nome='Cliente Inativo').pk, ids)
        primeiro = results[0]
        self.assertIn('nome', primeiro)
        self.assertIn('cpf_cnpj', primeiro)
        self.assertIn('telefone', primeiro)
        self.assertIn('email', primeiro)

    def test_formulario_venda_sem_cliente_exibe_mensagem_amigavel(self):
        form = VendaForm(data={
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.DINHEIRO,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Selecione um cliente para continuar.', form.errors['cliente'])

    def test_formulario_venda_rejeita_cliente_inativo(self):
        cliente = self.criar_cliente('Cliente Inativo Form', '55566677788', ativo=False)
        form = VendaForm(data={
            'cliente': cliente.pk,
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.PIX,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertFalse(form.is_valid())
        self.assertIn('Selecione um cliente ativo para continuar.', form.errors['cliente'])

    def test_formulario_venda_com_cliente_valido(self):
        cliente = self.criar_cliente('Cliente Valido', '44455566677')
        form = VendaForm(data={
            'cliente': cliente.pk,
            'desconto': Decimal('0.00'),
            'forma_pagamento': Venda.FormaPagamento.PIX,
            'status': Venda.Status.RASCUNHO,
        })

        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['cliente'], cliente)

    def test_recibo_exibe_dados_completos_do_cliente(self):
        cliente = self.criar_cliente('Cliente Recibo', '77788899900', telefone='2744445555')
        venda = Venda.objects.create(
            cliente=cliente,
            usuario=self.user,
            subtotal=Decimal('10.00'),
            total=Decimal('10.00'),
            forma_pagamento=Venda.FormaPagamento.DINHEIRO,
        )

        response = self.client.get(reverse('vendas:imprimir', kwargs={'pk': venda.pk}))

        self.assertContains(response, 'Dados do Cliente', html=False)
        self.assertContains(response, 'Cliente Recibo')
        self.assertContains(response, '77788899900')
        self.assertContains(response, '2744445555')
        self.assertContains(response, 'cliente.recibo@example.com')
        self.assertContains(response, 'Rua das Vendas, 10')
        self.assertContains(response, 'ISENTO')
