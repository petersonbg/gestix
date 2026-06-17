# Permissoes do GESTIX

Este documento descreve a infraestrutura de perfis criada no app `accounts` e a aplicacao das permissoes nos modulos internos.

## Perfis

O model `PerfilUsuario` vincula um usuario Django a exatamente um perfil ativo:

| Perfil | Uso previsto |
|---|---|
| `ADMINISTRADOR` | Administracao completa do sistema |
| `GERENTE` | Operacao gerencial, operacional e financeira |
| `VENDEDOR` | Rotinas comerciais e atendimento |
| `ESTOQUISTA` | Rotinas de produtos, fornecedores, estoque e consulta de OS |

Usuarios sem `PerfilUsuario` ativo sao redirecionados para `/acesso-negado/`.

## Helpers

Disponiveis em `accounts.permissions`:

```python
usuario_eh_admin(user)
usuario_eh_gerente(user)
usuario_eh_vendedor(user)
usuario_eh_estoquista(user)
usuario_tem_perfil(user, ["ADMINISTRADOR", "GERENTE"])
usuario_pode_acessar_modulo(user, "vendas")
```

Os helpers retornam `False` para usuarios anonimos, usuarios sem perfil ou perfis inativos. Superusuarios sao tratados como administradores. Os grupos legados do Django (`Administrador`, `Gerente`, `Vendedor`, `Estoquista`) ainda sao aceitos como fallback para compatibilidade, mas o cadastro recomendado e o `PerfilUsuario`.

## Decorator e mixin

Use `perfil_required` em function based views:

```python
from accounts.permissions import perfil_required


@perfil_required(["ADMINISTRADOR"])
def minha_view(request):
    ...
```

Use `PerfilRequiredMixin` em class based views:

```python
from accounts.permissions import PerfilRequiredMixin


class MinhaView(PerfilRequiredMixin, TemplateView):
    perfis_permitidos = ["ADMINISTRADOR", "GERENTE"]
    template_name = "minha_tela.html"
```

## Aplicacao por modulo

O middleware interno valida as URLs dos modulos protegidos mesmo quando o usuario digita o endereco manualmente. O menu lateral e os atalhos do dashboard usam os mesmos helpers para exibir apenas os modulos permitidos.

| Modulo | Administrador | Gerente | Vendedor | Estoquista |
|---|---:|---:|---:|---:|
| Dashboard | Sim | Sim | Sim | Sim |
| Clientes | Sim | Sim | Sim | Nao |
| Produtos | Sim | Sim | Nao | Sim |
| Fornecedores | Sim | Sim | Nao | Sim |
| Estoque | Sim | Sim | Nao | Sim |
| Vendas | Sim | Sim | Sim | Nao |
| Orcamentos | Sim | Sim | Sim | Nao |
| Caixa | Sim | Sim | Sim | Nao |
| Contas a receber | Sim | Sim | Nao | Nao |
| Contas a pagar | Sim | Sim | Nao | Nao |
| Ordens de servico | Sim | Sim | Sim | Somente consulta |
| Administracao | Sim | Sim | Nao | Nao |
| Backup e restauracao | Sim | Nao | Nao | Nao |
| Logs de atividade | Sim | Nao | Nao | Nao |

## Acesso negado e logs

A rota global `/acesso-negado/` exibe a mensagem de permissao negada. Quando o usuario autenticado nao possui perfil definido, a infraestrutura adiciona a mensagem especifica de usuario sem perfil.

Tentativas indevidas e usuarios sem perfil geram log com acao `ERRO`, modulo relacionado, IP e user-agent capturados a partir do request. A falha ao registrar log nao deve interromper o fluxo principal.

## Admin Django

`PerfilUsuario` esta registrado no Django Admin. Apenas superusuarios ou usuarios com perfil `ADMINISTRADOR` podem visualizar, criar ou editar perfis. Exclusao fica restrita ao superusuario.
