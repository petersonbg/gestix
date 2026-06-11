from datetime import timedelta
from decimal import Decimal

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from administracao.models import Empresa
from caixa.models import Caixa, MovimentacaoCaixa
from clientes.models import Cliente
from contas_receber.models import ContaReceber
from estoque.models import MovimentacaoEstoque
from produtos.models import Produto

from .forms import OrdemServicoForm
from .models import HistoricoOrdemServico, ItemProdutoOS, ItemServicoOS, OrdemServico, Servico


class OrdemServicoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='gerente-os', password='senha')
        self.user.groups.add(Group.objects.get_or_create(name='Gerente')[0])
        self.client.login(username='gerente-os', password='senha')
        self.executor = get_user_model().objects.create_user(
            username='tecnico-os', first_name='Maria', last_name='Silva', password='senha'
        )
        self.inactive_executor = get_user_model().objects.create_user(
            username='tecnico-inativo', password='senha', is_active=False
        )
        self.cliente = Cliente.objects.create(nome='Cliente OS', tipo_pessoa='fisica', cpf_cnpj='12345678901', telefone='27999999999')
        self.servico = Servico.objects.create(nome='Manutenção', valor_padrao=Decimal('100.00'))
        self.produto = Produto.objects.create(nome='Peça A', codigo_interno='P-OS-1', unidade_medida='UN', preco_custo=Decimal('10.00'), preco_venda=Decimal('25.00'), estoque_atual=5)

    def criar_os(self, **kwargs):
        dados = {'cliente': self.cliente, 'responsavel': self.user, 'descricao_problema': 'Equipamento não liga.'}
        dados.update(kwargs)
        return OrdemServico.objects.create(**dados)

    def test_criar_os_gera_numero_e_cliente(self):
        ordem = self.criar_os()
        self.assertTrue(ordem.numero.startswith('OS-'))
        self.assertEqual(ordem.cliente, self.cliente)

    def test_adicionar_servico_produto_e_calcular_totais(self):
        ordem = self.criar_os(desconto=Decimal('10.00'))
        ItemServicoOS.objects.create(ordem_servico=ordem, servico=self.servico, quantidade=2, valor_unitario=Decimal('100.00'))
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.recalcular_totais()
        self.assertEqual(ordem.subtotal_servicos, Decimal('200.00'))
        self.assertEqual(ordem.subtotal_produtos, Decimal('50.00'))
        self.assertEqual(ordem.total, Decimal('240.00'))

    def test_criar_os_com_deslocamento_e_responsavel_execucao(self):
        ordem = self.criar_os(
            valor_deslocamento=Decimal('35.00'),
            responsavel_execucao=self.executor,
        )
        self.assertEqual(ordem.valor_deslocamento, Decimal('35.00'))
        self.assertEqual(ordem.responsavel_execucao, self.executor)
        self.assertEqual(ordem.nome_responsavel_execucao, 'Maria Silva')

    def test_total_inclui_valor_deslocamento(self):
        ordem = self.criar_os(valor_deslocamento=Decimal('30.00'), desconto=Decimal('10.00'))
        ItemServicoOS.objects.create(
            ordem_servico=ordem, servico=self.servico,
            quantidade=2, valor_unitario=Decimal('100.00'),
        )
        ItemProdutoOS.objects.create(
            ordem_servico=ordem, produto=self.produto,
            quantidade=2, valor_unitario=Decimal('25.00'),
        )
        ordem.recalcular_totais()
        self.assertEqual(ordem.total, Decimal('270.00'))

    def test_impede_deslocamento_negativo(self):
        ordem = OrdemServico(
            cliente=self.cliente, responsavel=self.user,
            descricao_problema='Equipamento não liga.',
            valor_deslocamento=Decimal('-0.01'),
        )
        with self.assertRaisesMessage(ValidationError, 'O valor do deslocamento não pode ser negativo.'):
            ordem.full_clean()

    def test_impede_responsavel_execucao_inativo(self):
        ordem = self.criar_os(responsavel_execucao=self.inactive_executor)
        with self.assertRaisesMessage(ValidationError, 'Selecione um usuário ativo'):
            ordem.full_clean()
        form = OrdemServicoForm()
        self.assertNotIn(self.inactive_executor, form.fields['responsavel_execucao'].queryset)

    def test_exibe_nome_completo_dos_responsaveis(self):
        self.user.first_name = 'João'
        self.user.last_name = 'Gestor'
        self.user.save(update_fields=['first_name', 'last_name'])
        ordem = self.criar_os(responsavel_execucao=self.executor)
        response = self.client.get(ordem.get_absolute_url())
        self.assertContains(response, 'João Gestor')
        self.assertContains(response, 'Maria Silva')

    def test_desconto_nao_pode_superar_subtotais_com_deslocamento(self):
        ordem = OrdemServico(
            cliente=self.cliente,
            descricao_problema='Equipamento não liga.',
            subtotal_servicos=Decimal('50.00'),
            subtotal_produtos=Decimal('20.00'),
            valor_deslocamento=Decimal('10.00'),
            desconto=Decimal('80.01'),
        )
        with self.assertRaisesMessage(ValidationError, 'O desconto não pode ser maior'):
            ordem.full_clean()

    def test_formulario_registra_historico_de_deslocamento_e_executor(self):
        response = self.client.post(reverse('ordens_servico:create'), {
            'cliente': self.cliente.pk,
            'data_previsao': '',
            'responsavel': self.user.pk,
            'responsavel_execucao': self.executor.pk,
            'descricao_problema': 'Equipamento não liga.',
            'diagnostico': '',
            'solucao': '',
            'observacoes': '',
            'valor_deslocamento': '20.00',
            'desconto': '0.00',
            'servicos-TOTAL_FORMS': '0',
            'servicos-INITIAL_FORMS': '0',
            'servicos-MIN_NUM_FORMS': '0',
            'servicos-MAX_NUM_FORMS': '1000',
            'produtos-TOTAL_FORMS': '0',
            'produtos-INITIAL_FORMS': '0',
            'produtos-MIN_NUM_FORMS': '0',
            'produtos-MAX_NUM_FORMS': '1000',
        })
        self.assertEqual(response.status_code, 302)
        ordem = OrdemServico.objects.latest('pk')
        self.assertEqual(ordem.total, Decimal('20.00'))
        self.assertTrue(ordem.historico.filter(acao='ALTERACAO_DESLOCAMENTO').exists())
        self.assertTrue(ordem.historico.filter(acao='ALTERACAO_EXECUTOR').exists())

    def test_concluir_com_estoque_baixa_produto_e_registra_historico(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.concluir(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 3)
        self.assertTrue(MovimentacaoEstoque.objects.filter(origem='ORDEM_SERVICO', quantidade=2).exists())
        ordem.refresh_from_db()
        self.assertIsNotNone(ordem.data_finalizacao)
        historico = HistoricoOrdemServico.objects.get(ordem_servico=ordem, acao='CONCLUSAO')
        self.assertEqual(historico.usuario, self.user)
        self.assertIn('Status alterado de Aberta para Concluída', historico.descricao)
        self.assertIn('OS finalizada em', historico.descricao)

    def test_os_finalizada_nao_pode_ser_editada_via_get(self):
        ordem = self.criar_os()
        ordem.concluir(self.user)
        response = self.client.get(reverse('ordens_servico:update', args=[ordem.pk]), follow=True)
        self.assertRedirects(response, ordem.get_absolute_url())
        self.assertContains(response, 'Esta ordem de serviço já foi finalizada e não pode ser editada.')

    def test_os_finalizada_nao_pode_ser_alterada_via_post(self):
        ordem = self.criar_os(descricao_problema='Descrição original')
        ordem.concluir(self.user)
        response = self.client.post(
            reverse('ordens_servico:update', args=[ordem.pk]),
            {'descricao_problema': 'Descrição adulterada'},
            follow=True,
        )
        self.assertRedirects(response, ordem.get_absolute_url())
        ordem.refresh_from_db()
        self.assertEqual(ordem.descricao_problema, 'Descrição original')
        self.assertContains(response, 'Esta ordem de serviço já foi finalizada e não pode ser editada.')

    def test_os_finalizada_nao_pode_retornar_a_status_editavel(self):
        ordem = self.criar_os()
        ordem.concluir(self.user)
        response = self.client.post(
            reverse('ordens_servico:status', args=[ordem.pk]),
            {'status': OrdemServico.Status.EM_ANDAMENTO},
            follow=True,
        )
        ordem.refresh_from_db()
        self.assertEqual(ordem.status, OrdemServico.Status.CONCLUIDA)
        self.assertContains(response, 'Esta ordem de serviço já foi finalizada e não pode ser editada.')

    def test_admin_torna_os_finalizada_somente_leitura(self):
        ordem = self.criar_os()
        ordem.concluir(self.user)
        model_admin = admin.site._registry[OrdemServico]
        readonly_fields = model_admin.get_readonly_fields(None, ordem)
        for field_name in ('status', 'data_abertura', 'data_finalizacao', 'responsavel', 'responsavel_execucao'):
            self.assertIn(field_name, readonly_fields)

    def test_detalhes_ocultam_edicao_e_exibem_data_finalizacao(self):
        ordem = self.criar_os()
        ordem.concluir(self.user)
        response = self.client.get(ordem.get_absolute_url())
        self.assertNotContains(response, reverse('ordens_servico:update', args=[ordem.pk]))
        self.assertContains(response, 'Data de finalização')
        self.assertContains(response, timezone.localtime(ordem.data_finalizacao).strftime('%d/%m/%Y %H:%M'))

    def test_impressao_exibe_data_finalizacao(self):
        ordem = self.criar_os()
        ordem.concluir(self.user)
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        self.assertContains(response, 'Finalização:')
        self.assertContains(response, timezone.localtime(ordem.data_finalizacao).strftime('%d/%m/%Y %H:%M'))

    def test_impressao_exibe_nao_finalizada_quando_aberta(self):
        ordem = self.criar_os()
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        self.assertContains(response, 'Não finalizada')

    def test_bloqueia_conclusao_sem_estoque(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=6, valor_unitario=Decimal('25.00'))
        with self.assertRaisesMessage(ValidationError, 'Estoque insuficiente'):
            ordem.concluir(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)

    def test_cancelar_os_nao_baixa_estoque(self):
        ordem = self.criar_os()
        ItemProdutoOS.objects.create(ordem_servico=ordem, produto=self.produto, quantidade=2, valor_unitario=Decimal('25.00'))
        ordem.cancelar(self.user)
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)
        self.assertEqual(ordem.status, OrdemServico.Status.CANCELADA)

    def test_imprimir_os(self):
        ordem = self.criar_os()
        ItemServicoOS.objects.create(
            ordem_servico=ordem,
            servico=self.servico,
            quantidade=1,
            valor_unitario=Decimal('100.00'),
        )
        ItemProdutoOS.objects.create(
            ordem_servico=ordem,
            produto=self.produto,
            quantidade=1,
            valor_unitario=Decimal('25.00'),
        )
        ordem.recalcular_totais()
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ORDEM DE SERVIÇO')
        self.assertContains(response, ordem.numero)
        self.assertContains(response, 'Assinatura do Responsável pela Execução')
        self.assertContains(response, 'Manutenção')
        self.assertContains(response, 'Peça A')

        ordem.responsavel_execucao = self.executor
        ordem.assinatura_responsavel_execucao = 'assinaturas_os/tecnico.png'
        ordem.valor_deslocamento = Decimal('25.00')
        ordem.save(update_fields=['responsavel_execucao', 'assinatura_responsavel_execucao', 'valor_deslocamento'])
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        self.assertContains(response, 'Maria Silva')
        self.assertContains(response, 'media/assinaturas_os/tecnico.png')
        self.assertContains(response, 'R$ 25,00')

        Empresa.objects.create(
            nome_fantasia='Assistência GESTIX', razao_social='Assistência Técnica GESTIX Ltda',
            cnpj='11.222.333/0001-44', inscricao_estadual='11223344',
            telefone='(27) 3222-1111', whatsapp='(27) 97777-6666',
            email='os@gestix.test', logradouro='Rua das Oficinas', numero='80',
            bairro='Industrial', cidade='Vila Velha', estado='ES', cep='29100-000',
        )
        response = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        for texto in ['Assistência GESTIX', '11.222.333/0001-44', '(27) 97777-6666',
                      'Rua das Oficinas, 80 - Industrial - Vila Velha/ES', 'Contato:']:
            self.assertContains(response, texto)
        for texto in ['Assistência Técnica GESTIX Ltda', '11223344', 'os@gestix.test', '(27) 3222-1111']:
            self.assertNotContains(response, texto)
        self.assertContains(response, 'size: 140mm 210mm')
        self.assertContains(response, 'margin: 5mm')
        self.assertContains(response, 'height: 200mm')
        self.assertContains(response, 'Assinatura do Cliente')
        self.assertContains(response, 'width: 130mm')
        self.assertContains(response, 'print-compact')
        self.assertContains(response, 'Descrição')

    def test_filtrar_por_status(self):
        self.criar_os(status=OrdemServico.Status.ABERTA)
        self.criar_os(status=OrdemServico.Status.EM_ANDAMENTO)
        response = self.client.get(reverse('ordens_servico:list'), {'status': OrdemServico.Status.EM_ANDAMENTO})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['ordens']), 1)


    def test_buscas_dinamicas_retornam_registros_ativos(self):
        for rota, termo in [('buscar_clientes', 'Cliente'), ('buscar_produtos', 'Peça'), ('buscar_servicos', 'Manutenção')]:
            response = self.client.get(reverse(f'ordens_servico:{rota}'), {'q': termo})
            self.assertEqual(response.status_code, 200)
            self.assertGreaterEqual(len(response.json()['resultados']), 1)

    def test_pagamento_a_vista_registra_entrada_no_caixa(self):
        ordem = self.criar_os(status=OrdemServico.Status.CONCLUIDA, total=Decimal('100.00'))
        Caixa.abrir(usuario=self.user, valor_inicial=Decimal('0.00'))
        ordem.registrar_pagamento(usuario=self.user, forma_pagamento=OrdemServico.FormaPagamento.PIX, valor=Decimal('100.00'))
        self.assertTrue(MovimentacaoCaixa.objects.filter(descricao=f'Recebimento da OS nº {ordem.numero}', valor=Decimal('100.00')).exists())
        ordem.refresh_from_db()
        self.assertEqual(ordem.valor_pago, Decimal('100.00'))

    def test_pagamento_crediario_gera_parcelas_com_arredondamento(self):
        ordem = self.criar_os(status=OrdemServico.Status.CONCLUIDA, total=Decimal('100.00'))
        ordem.registrar_pagamento(
            usuario=self.user,
            forma_pagamento=OrdemServico.FormaPagamento.CREDIARIO,
            valor=Decimal('100.00'),
            parcelas=3,
            primeiro_vencimento=timezone.localdate(),
            intervalo=30,
        )
        parcelas = list(ContaReceber.objects.filter(ordem_servico=ordem).order_by('numero_parcela'))
        self.assertEqual(len(parcelas), 3)
        self.assertEqual(sum((parcela.valor for parcela in parcelas), Decimal('0.00')), Decimal('100.00'))

    def test_dashboard_mostra_ordem_atrasada(self):
        self.criar_os(data_previsao=timezone.localdate() - timedelta(days=1))
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['os_atrasadas_qtd'], 1)


class ServicoDinamicoOSTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-servicos-dinamicos', password='senha', email='admin-os@example.com'
        )
        self.client.force_login(self.usuario)
        self.cliente = Cliente.objects.create(nome='Cliente Serviços', cpf_cnpj='12345678901')
        self.ativo = Servico.objects.create(
            nome='Alinhamento técnico', descricao='Ajuste e calibração',
            valor_padrao=Decimal('80.00'), ativo=True,
        )
        self.inativo = Servico.objects.create(
            nome='Serviço desativado', descricao='Não deve aparecer',
            valor_padrao=Decimal('10.00'), ativo=False,
        )

    def dados_os(self, **alteracoes):
        dados = {
            'cliente': self.cliente.pk,
            'data_previsao': '',
            'responsavel': self.usuario.pk,
            'responsavel_execucao': '',
            'descricao_problema': 'Necessita manutenção.',
            'diagnostico': '',
            'solucao': '',
            'observacoes': '',
            'valor_deslocamento': '20.00',
            'desconto': '10.00',
            'servicos-TOTAL_FORMS': '1',
            'servicos-INITIAL_FORMS': '0',
            'servicos-MIN_NUM_FORMS': '0',
            'servicos-MAX_NUM_FORMS': '1000',
            'servicos-0-servico': self.ativo.pk,
            'servicos-0-descricao': 'Alinhamento completo',
            'servicos-0-quantidade': '2',
            'servicos-0-valor_unitario': '75.00',
            'produtos-TOTAL_FORMS': '0',
            'produtos-INITIAL_FORMS': '0',
            'produtos-MIN_NUM_FORMS': '0',
            'produtos-MAX_NUM_FORMS': '1000',
        }
        dados.update(alteracoes)
        return dados

    def test_busca_retorna_somente_servicos_ativos_por_nome_ou_descricao(self):
        por_nome = self.client.get(reverse('ordens_servico:buscar_servicos'), {'q': 'Alinhamento'})
        por_descricao = self.client.get(reverse('ordens_servico:buscar_servicos'), {'q': 'calibração'})
        inativo = self.client.get(reverse('ordens_servico:buscar_servicos'), {'q': 'desativado'})

        self.assertEqual(por_nome.json()['resultados'][0]['id'], self.ativo.pk)
        self.assertEqual(por_descricao.json()['resultados'][0]['id'], self.ativo.pk)
        self.assertEqual(inativo.json()['resultados'], [])

    def test_cria_os_com_servico_dinamico_e_calcula_total(self):
        resposta = self.client.post(reverse('ordens_servico:create'), self.dados_os())
        self.assertEqual(resposta.status_code, 302)
        ordem = OrdemServico.objects.latest('pk')
        item = ordem.itens_servico.get()
        self.assertEqual(item.quantidade, 2)
        self.assertEqual(item.valor_unitario, Decimal('75.00'))
        self.assertEqual(item.subtotal, Decimal('150.00'))
        self.assertEqual(ordem.subtotal_servicos, Decimal('150.00'))
        self.assertEqual(ordem.total, Decimal('160.00'))

    def test_rejeita_quantidade_zero_e_valor_negativo(self):
        quantidade = self.client.post(
            reverse('ordens_servico:create'),
            self.dados_os(**{'servicos-0-quantidade': '0'}),
        )
        valor = self.client.post(
            reverse('ordens_servico:create'),
            self.dados_os(**{'servicos-0-valor_unitario': '-0.01'}),
        )
        self.assertEqual(quantidade.status_code, 200)
        self.assertIn('quantidade', quantidade.context['servicos_formset'].forms[0].errors)
        self.assertEqual(valor.status_code, 200)
        self.assertIn('valor_unitario', valor.context['servicos_formset'].forms[0].errors)
        self.assertFalse(OrdemServico.objects.exists())

    def test_servico_nao_movimenta_estoque(self):
        self.client.post(reverse('ordens_servico:create'), self.dados_os())
        ordem = OrdemServico.objects.latest('pk')
        ordem.concluir(self.usuario)
        self.assertFalse(MovimentacaoEstoque.objects.filter(origem='ORDEM_SERVICO').exists())

    def test_nova_os_exibe_controles_dinamicos_e_subtotais(self):
        resposta = self.client.get(reverse('ordens_servico:create'))
        self.assertContains(resposta, 'Pesquisar serviço')
        self.assertContains(resposta, reverse('ordens_servico:buscar_servicos'))
        self.assertContains(resposta, 'subtotal-servicos')
        self.assertContains(resposta, 'item-subtotal')
        self.assertContains(resposta, 'Serviços + produtos + deslocamento')

    def test_detalhe_e_impressao_exibem_servico_e_subtotal(self):
        self.client.post(reverse('ordens_servico:create'), self.dados_os())
        ordem = OrdemServico.objects.latest('pk')
        detalhe = self.client.get(ordem.get_absolute_url())
        impressao = self.client.get(reverse('ordens_servico:imprimir', args=[ordem.pk]))
        for resposta in (detalhe, impressao):
            self.assertContains(resposta, self.ativo.nome)
            self.assertContains(resposta, 'Alinhamento completo')
            self.assertContains(resposta, '150,00')


class ServicoCadastroViewsTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username='admin-cadastro-servicos', password='senha', email='servicos@example.com'
        )
        self.client.force_login(self.usuario)

    def test_cadastra_e_edita_servico(self):
        resposta = self.client.post(reverse('ordens_servico:servico_create'), {
            'nome': 'Instalação especializada', 'descricao': 'Instalação completa',
            'valor_padrao': '120.00', 'ativo': 'on',
        })
        self.assertRedirects(resposta, reverse('ordens_servico:servicos'))
        servico = Servico.objects.get(nome='Instalação especializada')
        resposta = self.client.post(reverse('ordens_servico:servico_update', args=[servico.pk]), {
            'nome': 'Instalação premium', 'descricao': 'Instalação completa',
            'valor_padrao': '150.00', 'ativo': 'on',
        })
        self.assertRedirects(resposta, reverse('ordens_servico:servicos'))
        servico.refresh_from_db()
        self.assertEqual(servico.nome, 'Instalação premium')
        self.assertEqual(servico.valor_padrao, Decimal('150.00'))
