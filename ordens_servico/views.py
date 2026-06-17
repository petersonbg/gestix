from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, ListView

<<<<<<< HEAD
from accounts.permissions import usuario_tem_perfil
=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
from accounts.utils import registrar_log
from administracao.services import contexto_documento_impresso
from clientes.models import Cliente
from produtos.models import Produto

from .forms import (
    AlterarStatusForm, OrdemServicoForm, PagamentoOSForm, ProdutoFormSet,
    ServicoFormSet,
)
from .models import OrdemServico, Servico


MENSAGEM_OS_FINALIZADA = 'Esta ordem de serviço já foi finalizada e não pode ser editada.'


<<<<<<< HEAD
def pode_acessar(user):
    return usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE', 'VENDEDOR', 'ESTOQUISTA'])


def pode_editar(user):
    return usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE', 'VENDEDOR'])


def pode_gerenciar(user):
    return usuario_tem_perfil(user, ['ADMINISTRADOR', 'GERENTE'])
=======
def grupos_usuario(user):
    return set(user.groups.values_list('name', flat=True)) if user.is_authenticated else set()


def pode_acessar(user):
    return user.is_superuser or bool(grupos_usuario(user) & {'Administrador', 'Gerente', 'Vendedor', 'Estoquista'})


def pode_editar(user):
    return user.is_superuser or bool(grupos_usuario(user) & {'Administrador', 'Gerente', 'Vendedor'})


def pode_gerenciar(user):
    return user.is_superuser or bool(grupos_usuario(user) & {'Administrador', 'Gerente'})
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7


class OrdemServicoPermissaoMixin(LoginRequiredMixin, UserPassesTestMixin):
    permissao = staticmethod(pode_acessar)

    def test_func(self):
        return self.permissao(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, 'Você não possui permissão para esta ação em ordens de serviço.')
        return redirect('dashboard')


class OrdemServicoListView(OrdemServicoPermissaoMixin, ListView):
    model = OrdemServico
    template_name = 'ordens_servico/list.html'
    context_object_name = 'ordens'
    paginate_by = 20

    def get_queryset(self):
        qs = OrdemServico.objects.select_related('cliente', 'responsavel', 'responsavel_execucao')
        filtros = self.request.GET
        if filtros.get('cliente'):
            qs = qs.filter(Q(cliente__nome__icontains=filtros['cliente']) | Q(cliente__cpf_cnpj__icontains=filtros['cliente']))
        if filtros.get('status'):
            qs = qs.filter(status=filtros['status'])
        if filtros.get('responsavel'):
            qs = qs.filter(responsavel_id=filtros['responsavel'])
        if filtros.get('data_inicial'):
            qs = qs.filter(data_abertura__date__gte=filtros['data_inicial'])
        if filtros.get('data_final'):
            qs = qs.filter(data_abertura__date__lte=filtros['data_final'])
        if filtros.get('numero'):
            qs = qs.filter(numero__icontains=filtros['numero'])
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = OrdemServico.Status.choices
        context['filtros'] = self.request.GET
        context['pode_criar'] = pode_editar(self.request.user)
        return context


class OrdemServicoDetailView(OrdemServicoPermissaoMixin, DetailView):
    model = OrdemServico
    template_name = 'ordens_servico/detail.html'
    context_object_name = 'ordem'

    def get_queryset(self):
        return OrdemServico.objects.select_related('cliente', 'responsavel', 'responsavel_execucao').prefetch_related('itens_servico__servico', 'itens_produto__produto', 'historico__usuario')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_form'] = AlterarStatusForm(initial={'status': self.object.status})
        context['pagamento_form'] = PagamentoOSForm(initial={'valor': self.object.saldo})
        usuario_pode_editar = pode_editar(self.request.user)
        context['pode_editar'] = usuario_pode_editar and not self.object.finalizada
        context['pode_entregar'] = usuario_pode_editar and self.object.status == OrdemServico.Status.CONCLUIDA
        context['pode_registrar_pagamento'] = usuario_pode_editar
        context['pode_gerenciar'] = pode_gerenciar(self.request.user)
        return context


class OrdemServicoFormView(OrdemServicoPermissaoMixin, View):
    permissao = staticmethod(pode_editar)
    template_name = 'ordens_servico/form.html'
    instance = None

    def get_instance(self):
        return self.instance

    @staticmethod
    def contexto_formulario(form, servicos_formset, produtos_formset, ordem):
        return {
            'form': form,
            'servicos_formset': servicos_formset,
            'produtos_formset': produtos_formset,
            'servicos_ativos': Servico.objects.filter(ativo=True).order_by('nome'),
            'ordem': ordem,
        }

    def get(self, request, *args, **kwargs):
        ordem = self.get_instance()
        return render(
            request,
            self.template_name,
            self.contexto_formulario(
                OrdemServicoForm(instance=ordem),
                ServicoFormSet(instance=ordem, prefix='servicos'),
                ProdutoFormSet(instance=ordem, prefix='produtos'),
                ordem,
            ),
        )

    def post(self, request, *args, **kwargs):
        ordem = self.get_instance() or OrdemServico()
        if ordem.pk:
            ordem.refresh_from_db(fields=['status'])
            if ordem.finalizada:
                messages.error(request, MENSAGEM_OS_FINALIZADA)
                return redirect(ordem)
        dados_anteriores = {
            'valor_deslocamento': ordem.valor_deslocamento if ordem.pk else 0,
            'responsavel_execucao_id': ordem.responsavel_execucao_id if ordem.pk else None,
            'responsavel_execucao_nome': ordem.nome_responsavel_execucao if ordem.pk else 'Não informado',
            'assinatura': ordem.assinatura_responsavel_execucao.name if ordem.pk and ordem.assinatura_responsavel_execucao else '',
        }
        form = OrdemServicoForm(request.POST, request.FILES, instance=ordem)
        servicos_formset = ServicoFormSet(request.POST, instance=ordem, prefix='servicos')
        produtos_formset = ProdutoFormSet(request.POST, instance=ordem, prefix='produtos')
        if form.is_valid() and servicos_formset.is_valid() and produtos_formset.is_valid():
            subtotal_servicos = sum((item.get('quantidade', 0) * item.get('valor_unitario', 0)) for item in servicos_formset.cleaned_data if item and not item.get('DELETE'))
            subtotal_produtos = sum((item.get('quantidade', 0) * item.get('valor_unitario', 0)) for item in produtos_formset.cleaned_data if item and not item.get('DELETE'))
            valor_deslocamento = form.cleaned_data.get('valor_deslocamento', 0) or 0
            if form.cleaned_data.get('desconto', 0) > subtotal_servicos + subtotal_produtos + valor_deslocamento:
                form.add_error('desconto', 'O desconto não pode ser maior que o total da OS.')
                return render(
                    request, self.template_name,
                    self.contexto_formulario(form, servicos_formset, produtos_formset, ordem),
                )
            with transaction.atomic():
                nova = not ordem.pk
                ordem = form.save()
                servicos_formset.instance = ordem
                produtos_formset.instance = ordem
                servicos_formset.save()
                produtos_formset.save()
                ordem.recalcular_totais()
                ordem.registrar_historico(request.user, 'CRIACAO' if nova else 'EDICAO', 'Ordem de serviço criada.' if nova else 'Ordem de serviço editada.')
                if dados_anteriores['valor_deslocamento'] != ordem.valor_deslocamento:
                    ordem.registrar_historico(
                        request.user,
                        'ALTERACAO_DESLOCAMENTO',
                        f"Valor do deslocamento alterado de R$ {dados_anteriores['valor_deslocamento']} para R$ {ordem.valor_deslocamento}.",
                    )
                if dados_anteriores['responsavel_execucao_id'] != ordem.responsavel_execucao_id:
                    ordem.registrar_historico(
                        request.user,
                        'ALTERACAO_EXECUTOR',
                        f"Responsável pela execução alterado de {dados_anteriores['responsavel_execucao_nome']} para {ordem.nome_responsavel_execucao}.",
                    )
                assinatura_atual = ordem.assinatura_responsavel_execucao.name if ordem.assinatura_responsavel_execucao else ''
                if dados_anteriores['assinatura'] != assinatura_atual:
                    ordem.registrar_historico(
                        request.user,
                        'ALTERACAO_ASSINATURA_EXECUTOR',
                        'Assinatura do responsável pela execução incluída ou alterada.' if assinatura_atual else 'Assinatura do responsável pela execução removida.',
                    )
                registrar_log(request.user, 'criação de OS' if nova else 'edição de OS', 'ordens_servico', f'OS {ordem.numero}.', request=request)
            messages.success(request, 'Ordem de serviço salva com sucesso.')
            return redirect(ordem)
        return render(
            request, self.template_name,
            self.contexto_formulario(form, servicos_formset, produtos_formset, ordem),
        )


class OrdemServicoCreateView(OrdemServicoFormView):
    pass


class OrdemServicoUpdateView(OrdemServicoFormView):
    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(OrdemServico, pk=kwargs['pk'])
        if self.instance.finalizada:
            messages.error(request, MENSAGEM_OS_FINALIZADA)
            return redirect(self.instance)
        return super().dispatch(request, *args, **kwargs)


def _json_permitido(request):
    if not pode_acessar(request.user):
        return JsonResponse({'resultados': []}, status=403)
    return None


@login_required
@require_http_methods(['GET'])
def buscar_clientes(request):
    negado = _json_permitido(request)
    if negado:
        return negado
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': []})
    clientes = Cliente.objects.filter(ativo=True).filter(Q(nome__icontains=q) | Q(cpf_cnpj__icontains=q) | Q(telefone__icontains=q))[:10]
    return JsonResponse({'resultados': [{'id': c.pk, 'nome': c.nome, 'cpf_cnpj': c.cpf_cnpj or '', 'telefone': c.telefone or '', 'email': c.email or '', 'endereco': c.endereco or '', 'inscricao_estadual': c.inscricao_estadual or ''} for c in clientes]})


@login_required
@require_http_methods(['GET'])
def buscar_produtos(request):
    negado = _json_permitido(request)
    if negado:
        return negado
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'resultados': []})
    produtos = Produto.objects.filter(ativo=True).filter(Q(nome__icontains=q) | Q(codigo_interno__icontains=q) | Q(codigo_barras__icontains=q))[:10]
    return JsonResponse({'resultados': [{'id': p.pk, 'nome': p.nome, 'codigo_interno': p.codigo_interno, 'preco_venda': str(p.preco_venda), 'estoque_atual': p.estoque_atual} for p in produtos]})



def _ordem_acao(request, pk, permissao=pode_editar):
    ordem = get_object_or_404(OrdemServico, pk=pk)
    if not permissao(request.user):
        messages.error(request, 'Você não possui permissão para esta ação.')
        return ordem, redirect('dashboard')
    return ordem, None


@login_required
@require_http_methods(['POST'])
def alterar_status(request, pk):
    ordem, resposta = _ordem_acao(request, pk, pode_gerenciar)
    if resposta:
        return resposta
    form = AlterarStatusForm(request.POST)
    if form.is_valid():
        try:
            ordem.alterar_status(form.cleaned_data['status'], request.user)
            messages.success(request, 'Status atualizado com sucesso.')
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
    return redirect(ordem)


@login_required
@require_http_methods(['POST'])
def concluir(request, pk):
    ordem, resposta = _ordem_acao(request, pk, pode_gerenciar)
    if resposta:
        return resposta
    try:
        ordem.concluir(request.user)
        messages.success(request, 'Ordem de serviço concluída e estoque atualizado.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect(ordem)


@login_required
@require_http_methods(['POST'])
def cancelar(request, pk):
    ordem, resposta = _ordem_acao(request, pk, pode_gerenciar)
    if resposta:
        return resposta
    try:
        ordem.cancelar(request.user)
        messages.success(request, 'Ordem de serviço cancelada.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect(ordem)


@login_required
@require_http_methods(['POST'])
def entregar(request, pk):
    ordem, resposta = _ordem_acao(request, pk, pode_editar)
    if resposta:
        return resposta
    try:
        ordem.alterar_status(OrdemServico.Status.ENTREGUE, request.user)
        ordem.registrar_historico(request.user, 'ENTREGA', 'Ordem de serviço entregue ao cliente.')
        messages.success(request, 'Ordem de serviço marcada como entregue.')
    except ValidationError as exc:
        messages.error(request, '; '.join(exc.messages))
    return redirect(ordem)


@login_required
@require_http_methods(['POST'])
def registrar_pagamento(request, pk):
    ordem, resposta = _ordem_acao(request, pk, pode_editar)
    if resposta:
        return resposta
    form = PagamentoOSForm(request.POST)
    if form.is_valid():
        try:
            ordem.registrar_pagamento(usuario=request.user, **form.cleaned_data)
            messages.success(request, 'Pagamento da ordem de serviço registrado.')
        except ValidationError as exc:
            messages.error(request, '; '.join(exc.messages))
    else:
        messages.error(request, 'Revise os dados do pagamento.')
    return redirect(ordem)


@login_required
@require_http_methods(['GET'])
def imprimir(request, pk):
    ordem = get_object_or_404(OrdemServico.objects.select_related('cliente', 'responsavel', 'responsavel_execucao').prefetch_related('itens_servico__servico', 'itens_produto__produto'), pk=pk)
    if not pode_acessar(request.user):
        messages.error(request, 'Você não possui permissão para imprimir esta OS.')
        return redirect('dashboard')
    ordem.registrar_historico(request.user, 'IMPRESSAO', 'Ordem de serviço impressa.')
    context = {'ordem': ordem}
    context.update(contexto_documento_impresso())
    return render(request, 'ordens_servico/imprimir.html', context)
