from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from administracao.models import Empresa
from clientes.models import Cliente
from produtos.models import Produto

from .models import ItemOrcamento, Orcamento


class ClienteBuscaOrcamentoTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username='admin', password='senha', email='admin@example.com')
        self.client.login(username='admin', password='senha')

    def criar_cliente(self, nome, cpf_cnpj, telefone='11999990000', ativo=True):
        return Cliente.objects.create(
            nome=nome,
            tipo_pessoa=Cliente.TipoPessoa.FISICA,
            cpf_cnpj=cpf_cnpj,
            telefone=telefone,
            email=f'{nome.lower().replace(" ", ".")}@example.com',
            endereco='Rua Central, 100',
            inscricao_estadual='ISENTO',
            ativo=ativo,
        )

    def test_busca_exige_login(self):
        self.client.logout()
        response = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': 'Ma'})
        self.assertEqual(response.status_code, 302)

    def test_busca_retorna_vazio_para_consulta_curta(self):
        self.criar_cliente('Maria Silva', '11122233344')
        response = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': 'M'})
        self.assertEqual(response.json()['results'], [])

    def test_busca_retorna_apenas_clientes_ativos_com_campos_necessarios(self):
        cliente = self.criar_cliente('Maria Silva', '11122233344', telefone='1133334444')
        self.criar_cliente('Maria Inativa', '99988877766', ativo=False)

        response = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': 'Maria'})

        self.assertEqual(response.status_code, 200)
        results = response.json()['results']
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], cliente.pk)
        self.assertEqual(results[0]['nome'], 'Maria Silva')
        self.assertEqual(results[0]['cpf_cnpj'], '11122233344')
        self.assertEqual(results[0]['telefone'], '1133334444')
        self.assertEqual(results[0]['email'], cliente.email)
        self.assertEqual(results[0]['endereco'], 'Rua Central, 100')
        self.assertEqual(results[0]['inscricao_estadual'], 'ISENTO')

    def test_busca_por_cpf_cnpj_e_telefone(self):
        por_documento = self.criar_cliente('Cliente Documento', '12345678901', telefone='1100000000')
        por_telefone = self.criar_cliente('Cliente Telefone', '22233344455', telefone='11987654321')

        response_documento = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': '678901'})
        response_telefone = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': '987654'})

        self.assertEqual(response_documento.json()['results'][0]['id'], por_documento.pk)
        self.assertEqual(response_telefone.json()['results'][0]['id'], por_telefone.pk)

    def test_busca_limita_resultado_a_dez_clientes(self):
        for indice in range(12):
            self.criar_cliente(f'Cliente Limite {indice:02d}', f'900000000{indice:02d}')

        response = self.client.get(reverse('orcamentos:buscar_clientes'), {'q': 'Cliente Limite'})

        self.assertEqual(len(response.json()['results']), 10)

    def test_impressao_exibe_dados_completos_do_cliente(self):
        cliente = self.criar_cliente('Cliente Impressão', '44455566677', telefone='1144445555')
        produto = Produto.objects.create(
            nome='Produto Teste',
            codigo_interno='P001',
            unidade_medida='UN',
            preco_custo=Decimal('5.00'),
            preco_venda=Decimal('10.00'),
        )
        orcamento = Orcamento.objects.create(cliente=cliente, usuario=self.user)
        ItemOrcamento.objects.create(orcamento=orcamento, produto=produto, quantidade=2, valor_unitario=Decimal('10.00'))
        orcamento.recalcular_totais()

        response = self.client.get(reverse('orcamentos:imprimir_orcamento', kwargs={'pk': orcamento.pk}))

        self.assertContains(response, 'Dados do Cliente', html=False)
        self.assertContains(response, 'Cliente Impressão')
        self.assertContains(response, '44455566677')
        self.assertContains(response, 'Rua Central, 100')
        self.assertContains(response, 'cliente.impressão@example.com')
        self.assertContains(response, 'ISENTO')
        self.assertContains(response, 'Orçamento válido por 30 dias')

        Empresa.objects.create(
            nome_fantasia='Empresa Orçamentos', razao_social='Empresa Orçamentos Ltda',
            cnpj='98.765.432/0001-10', inscricao_estadual='987654321',
            telefone='(11) 3333-2222', whatsapp='(11) 98888-7777',
            email='orcamentos@empresa.test', logradouro='Rua Comercial', numero='45',
            bairro='Centro', cidade='São Paulo', estado='SP', cep='01000-000',
        )
        response = self.client.get(reverse('orcamentos:imprimir_orcamento', kwargs={'pk': orcamento.pk}))
        for texto in ['Empresa Orçamentos', 'Empresa Orçamentos Ltda', '98.765.432/0001-10',
                      '987654321', '(11) 3333-2222', '(11) 98888-7777',
                      'orcamentos@empresa.test', 'Rua Comercial, 45', 'São Paulo - SP']:
            self.assertContains(response, texto)
        self.assertContains(response, 'size: A4 portrait')
        self.assertContains(response, 'Orçamento válido por 30 dias')
