from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import FormView, ListView, UpdateView

from accounts.models import PerfilUsuario
from accounts.permissions import PerfilRequiredMixin, perfil_required, usuario_tem_perfil
from administracao.models import Empresa
from clientes.models import Cliente

from .forms import ConfiguracaoWhatsAppForm, EnviarMensagemWhatsAppForm, ModeloMensagemWhatsAppForm
from .models import ConfiguracaoWhatsApp, FilaMensagemWhatsApp, MensagemWhatsApp, ModeloMensagemWhatsApp
from .services import (
    ORIGEM_LOG_DESCRICAO,
    ORIGEM_TIPO_MODELO,
    contexto_whatsapp,
    gerar_link_whatsapp,
    registrar_log_whatsapp,
    renderizar_modelo,
    resolver_origem_whatsapp,
    validar_telefone,
)


PERFIS_CONFIGURAR = (PerfilUsuario.Perfil.ADMINISTRADOR, PerfilUsuario.Perfil.GERENTE)
PERFIS_ENVIAR = (
    PerfilUsuario.Perfil.ADMINISTRADOR,
    PerfilUsuario.Perfil.GERENTE,
    PerfilUsuario.Perfil.VENDEDOR,
)


class WhatsAppContextMixin:
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pode_configurar_whatsapp'] = usuario_tem_perfil(self.request.user, PERFIS_CONFIGURAR)
        context['pode_enviar_whatsapp'] = usuario_tem_perfil(self.request.user, PERFIS_ENVIAR)
        return context


class ConfiguracaoWhatsAppView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, UpdateView):
    model = ConfiguracaoWhatsApp
    form_class = ConfiguracaoWhatsAppForm
    template_name = 'whatsapp/configuracao.html'
    success_url = reverse_lazy('whatsapp:configuracao')
    perfis_permitidos = PERFIS_CONFIGURAR

    def get_object(self, queryset=None):
        obj = ConfiguracaoWhatsApp.objects.order_by('-ativo', '-atualizado_em').first()
        if obj:
            return obj
        return ConfiguracaoWhatsApp()

    def form_valid(self, form):
        messages.success(self.request, 'Configuração do WhatsApp salva com sucesso.')
        return super().form_valid(form)


class ModeloMensagemListView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, ListView):
    model = ModeloMensagemWhatsApp
    template_name = 'whatsapp/modelos/lista.html'
    context_object_name = 'modelos'
    paginate_by = 10
    perfis_permitidos = PERFIS_ENVIAR

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q', '').strip()
        if query:
            queryset = queryset.filter(Q(nome__icontains=query) | Q(mensagem__icontains=query))
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '').strip()
        return context


class ModeloMensagemCreateView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, FormView):
    form_class = ModeloMensagemWhatsAppForm
    template_name = 'whatsapp/modelos/form.html'
    success_url = reverse_lazy('whatsapp:modelos')
    perfis_permitidos = PERFIS_CONFIGURAR

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Modelo de mensagem criado com sucesso.')
        return super().form_valid(form)


class ModeloMensagemUpdateView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, UpdateView):
    model = ModeloMensagemWhatsApp
    form_class = ModeloMensagemWhatsAppForm
    template_name = 'whatsapp/modelos/form.html'
    success_url = reverse_lazy('whatsapp:modelos')
    perfis_permitidos = PERFIS_CONFIGURAR

    def form_valid(self, form):
        messages.success(self.request, 'Modelo de mensagem atualizado com sucesso.')
        return super().form_valid(form)


class EnviarMensagemWhatsAppView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, FormView):
    form_class = EnviarMensagemWhatsAppForm
    template_name = 'whatsapp/enviar.html'
    perfis_permitidos = PERFIS_ENVIAR

    def _dados_origem(self):
        origem = self.request.GET.get('origem')
        objeto_id = self.request.GET.get('id')
        if not origem or not objeto_id:
            return None
        return resolver_origem_whatsapp(origem, objeto_id)

    def get_initial(self):
        initial = super().get_initial()
        dados = self._dados_origem()
        if dados:
            initial.update({
                'cliente': dados['cliente'],
                'telefone': dados['telefone'],
                'modelo': dados['modelo'],
                'mensagem': dados['mensagem'],
            })
            if dados['erro_telefone']:
                messages.error(self.request, dados['erro_telefone'])
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dados_origem_whatsapp'] = self._dados_origem()
        return context

    def form_valid(self, form):
        cliente = form.cleaned_data['cliente']
        modelo = form.cleaned_data.get('modelo')
        telefone = form.cleaned_data['telefone']
        mensagem = form.cleaned_data['mensagem']
        link = gerar_link_whatsapp(telefone, mensagem)
        tipo = modelo.tipo if modelo else 'AVULSA'

        registro = MensagemWhatsApp.objects.create(
            cliente=cliente,
            telefone=telefone,
            tipo=tipo,
            mensagem=mensagem,
            modo_envio=ConfiguracaoWhatsApp.ModoEnvio.WHATSAPP_WEB,
            status=MensagemWhatsApp.Status.ENVIADA,
            usuario=self.request.user,
            data_envio=timezone.now(),
        )
        origem = self.request.POST.get('origem_whatsapp') or self.request.GET.get('origem') or 'cliente'
        if origem not in ORIGEM_TIPO_MODELO:
            origem = 'cliente'
        descricao = ORIGEM_LOG_DESCRICAO.get(origem, 'mensagem enviada')
        registrar_log_whatsapp(
            self.request.user,
            origem,
            f'{descricao}: WhatsApp Web para {cliente.nome}.',
            request=self.request,
        )
        messages.success(self.request, 'Tentativa registrada. O WhatsApp Web será aberto em uma nova aba.')
        context = self.get_context_data(
            form=form,
            abrir_link_whatsapp=link,
            mensagem_registrada=registro,
        )
        return self.render_to_response(context)


class HistoricoEnviosView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, ListView):
    model = MensagemWhatsApp
    template_name = 'whatsapp/historico.html'
    context_object_name = 'mensagens'
    paginate_by = 20
    perfis_permitidos = PERFIS_ENVIAR

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'usuario')
        if usuario_tem_perfil(self.request.user, [PerfilUsuario.Perfil.VENDEDOR]):
            queryset = queryset.filter(usuario=self.request.user)
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = MensagemWhatsApp.Status.choices
        context['status_selecionado'] = self.request.GET.get('status', '').strip()
        return context


class FilaMensagemView(LoginRequiredMixin, PerfilRequiredMixin, WhatsAppContextMixin, ListView):
    model = FilaMensagemWhatsApp
    template_name = 'whatsapp/fila.html'
    context_object_name = 'itens_fila'
    paginate_by = 20
    perfis_permitidos = PERFIS_ENVIAR

    def get_queryset(self):
        queryset = super().get_queryset().select_related('cliente', 'usuario_criacao')
        if usuario_tem_perfil(self.request.user, [PerfilUsuario.Perfil.VENDEDOR]):
            queryset = queryset.filter(usuario_criacao=self.request.user)
        status = self.request.GET.get('status', '').strip()
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = FilaMensagemWhatsApp.Status.choices
        context['status_selecionado'] = self.request.GET.get('status', '').strip()
        return context


@login_required
@perfil_required(PERFIS_ENVIAR)
def preview_modelo(request):
    cliente_id = request.GET.get('cliente')
    modelo_id = request.GET.get('modelo')
    cliente = get_object_or_404(Cliente, pk=cliente_id, ativo=True)
    modelo = get_object_or_404(ModeloMensagemWhatsApp, pk=modelo_id, ativo=True)
    empresa = Empresa.get_solo()
    telefone = cliente.telefone or ''
    telefone_valido = ''
    erro_telefone = ''
    if telefone:
        try:
            telefone_valido = validar_telefone(telefone)
        except ValueError as exc:
            erro_telefone = str(exc)
    contexto = contexto_whatsapp(cliente=cliente, empresa=empresa)
    return JsonResponse({
        'cliente_nome': cliente.nome,
        'telefone': telefone_valido or telefone,
        'telefone_valido': bool(telefone_valido),
        'erro_telefone': erro_telefone,
        'tipo': modelo.tipo,
        'mensagem': renderizar_modelo(modelo, contexto),
    })


def whatsapp_home(request):
    return redirect('whatsapp:configuracao')