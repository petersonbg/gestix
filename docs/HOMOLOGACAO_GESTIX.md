# Checklist de Homologação do GESTIX

Data de atualização: **16/06/2026**  
Responsável técnico: Codex  
Legenda: **Pendente** = depende de execução/validação; **OK** = verificado; **Corrigir** = falha confirmada.

> Esta fase estabiliza o sistema antes da implantação. Não criar módulos grandes durante a homologação; corrigir apenas bugs, validações, segurança, layout e ajustes de implantação.

## 1. Estrutura Geral

| Verificação | Resultado esperado | Status | Observações |
|---|---|---|---|
| Conflitos de merge | Nenhum marcador de conflito | OK | Conflitos removidos em código e documentação |
| Apps instalados | Apps principais presentes em `INSTALLED_APPS` | OK | Inclui `relatorios`, backup, logs e perfis |
| URLs | Rotas principais incluídas em `gestix/urls.py` | OK | Módulos internos, admin e relatórios carregados |
| Templates | Templates referenciados existem | OK | Renderização coberta pela suíte |
| Staticfiles | `collectstatic --noinput` sem erro | OK | 156 arquivos sem alteração, 409 pós-processados |
| Migrations | Sem alterações pendentes | OK | Migrations corretivas geradas/aplicadas; `makemigrations --check` limpo |
| `settings.py` | Configuração externa por env | OK parcial | `check` OK; `check --deploy` mantém avisos de produção |
| `docker-compose.yml` | Serviços `web` e `db` sobem | OK | `docker compose up -d --build` executado com sucesso |
| Backup | Arquivo `.dump` em formato custom PostgreSQL | OK | `gestix_backup_20260616_220754.dump` validado com `pg_restore --list` |
| Restauração | Restaurar em banco descartável | Pendente | Não executar restauração destrutiva no banco de homologação atual |

## 2. Verificações Automatizadas

| Comando | Resultado esperado | Status | Evidência |
|---|---|---|---|
| `docker compose up -d --build` | Containers sobem | OK | `gestix-db-1` healthy e `gestix-web-1` started |
| `docker compose exec web python manage.py check` | Sem erros | OK | `System check identified no issues` |
| `docker compose exec web python manage.py makemigrations --check` | Sem migrations pendentes | OK | `No changes detected` |
| `docker compose exec web python manage.py migrate` | Migrations aplicadas | OK | Migrations corretivas aplicadas |
| `docker compose exec web python manage.py test` | Suíte integral aprovada | OK | 204 testes executados com sucesso |
| `docker compose exec web python manage.py collectstatic --noinput` | Staticfiles processados | OK | 409 pós-processados |
| `docker compose exec web python manage.py check --deploy` | Sem alertas para produção | Corrigir | 5 warnings: HSTS/HTTPS/cookies seguros/SECRET_KEY |
| `docker compose exec web python manage.py gerar_backup` | Backup gerado | OK | `gestix_backup_20260616_220754.dump` |
| `pg_restore --list` no backup | Dump custom válido | OK | TOC lido, formato `CUSTOM`, PostgreSQL 16 |

## 3. Fluxos Funcionais Automatizados

| Módulo | Cenários cobertos pela suíte | Status | Observações |
|---|---|---|---|
| Clientes | Cadastro, edição, busca, CPF/CNPJ, IE e nascimento | OK | Cobertura automatizada existente |
| Produtos | Cadastro, código interno, custo opcional, categoria, chassi, filtro e estoque mínimo | OK | Cobertura automatizada existente |
| Fornecedores | Cadastro, edição, busca e CNPJ | OK | Cobertura automatizada existente |
| Estoque | Entrada, saída, ajuste, histórico e bloqueio sem saldo | OK | Cobertura automatizada/model tests |
| Vendas | Busca, itens, finalização, cancelamento, sem estoque, crediário e recibo | OK | Cobertura automatizada; impressão visual ainda pendente |
| Caixa | Abertura, movimentos, venda e fechamento | OK | Cobertura automatizada |
| Orçamentos | Cliente/produtos, impressão, validade e conversão | OK | Cobertura automatizada; validação visual ainda pendente |
| Ordens de Serviço | Cadastro, serviços, produtos, deslocamento, responsáveis, assinatura, conclusão e bloqueio | OK | Cobertura automatizada; validação visual ainda pendente |
| Contas a Receber | Parcelas, recebimento, bloqueio sem caixa e dashboard | OK | Cobertura automatizada |
| Contas a Pagar | Cadastro, pagamento, cancelamento e alertas | OK | Cobertura automatizada |
| Administração | Empresa, categorias, serviços, configurações, aniversário, logout e permissões | OK | Cobertura automatizada |
| Backup/Restauração | Tela, comando, registro, download protegido e validações | OK parcial | Restauração destrutiva deve ser feita em base descartável |
| Logs/Auditoria | Registro e tela protegida | OK | Cobertura automatizada |
| Relatórios | Permissões, filtros, totais, CSV e impressão | OK | 7 testes específicos; incluído na suíte de 204 testes |

## 4. Permissões e Segurança

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Administrador | Acesso total | OK | Testes de perfil e menus |
| Gerente | Operacional completo, sem backup/logs | OK | Testes de perfil e URL direta |
| Vendedor | Clientes, vendas, orçamentos, caixa e OS | OK | Bloqueio em contas/produtos validado |
| Estoquista | Produtos, fornecedores, estoque e OS consulta | OK | Bloqueio em vendas validado |
| Usuário sem perfil | Acesso bloqueado | OK | Redireciona para `/acesso-negado/` |
| Botões/menus | UI respeita perfil | OK | Sidebar/dashboard cobertos por testes |
| Backend | URL manual bloqueada | OK | Middleware e views cobertos |
| Login obrigatório | Rotas internas protegidas | OK | Testes existentes |
| Cache após logout/inatividade | No-store e timeout | OK | Middleware coberto |
| Produção HTTPS | Cookies seguros, HSTS, redirect SSL e segredo forte | Corrigir | Configurar `.env`/proxy antes de produção |

## 5. Impressões

| Documento | Resultado esperado | Status | Observações |
|---|---|---|---|
| Recibo de venda | 140 mm x 210 mm, retrato | OK parcial | Template/testes OK; validar PDF/impressora real |
| Ordem de serviço | 140 mm x 210 mm, retrato | OK parcial | Template/testes OK; validar PDF/impressora real |
| Orçamento | 140 mm x 210 mm, retrato e validade | OK parcial | Template/testes OK; validar PDF/impressora real |
| Relatórios | A4 retrato | OK | Template de impressão e testes OK |

## 6. Critérios de Aceite

1. `check`, `makemigrations --check`, `migrate`, `collectstatic` e `test` estão **OK** em Docker/PostgreSQL.
2. Não há conflito de merge aberto.
3. Backup foi gerado e validado como dump custom PostgreSQL.
4. A matriz de permissões está validada por testes automatizados.
5. Antes de produção ainda falta configurar variáveis seguras e HTTPS.
6. Antes de produção ainda falta validar restauração em banco descartável.
7. Antes de produção ainda falta aprovação visual de recibo, OS e orçamento em navegador/impressora real.
