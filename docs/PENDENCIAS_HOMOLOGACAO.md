# Pendências da Homologação do GESTIX

Data de atualização: **16/06/2026**

## Pendências abertas

| Prioridade | Módulo | Erro/risco encontrado | Sugestão de correção | Status |
|---|---|---|---|---|
| Alta | Segurança de produção | `manage.py check --deploy` ainda alerta HSTS, HTTPS redirect, cookies seguros e `SECRET_KEY` fraca/de exemplo | Definir `.env` de produção com `DEBUG=False`, `USE_HTTPS=True`, `SECRET_KEY` forte, TLS/proxy reverso e cookies seguros | Pendente |
| Alta | Backup e restauração | Restauração destrutiva não foi executada em banco descartável nesta rodada | Restaurar um `.dump` em base descartável e conferir contagens/totais antes da produção | Pendente |
| Média | Impressões | Recibo, OS e orçamento dependem de validação visual em navegador/impressora real | Gerar PDFs com dados reais, muitos itens, logos e assinaturas; validar Chrome/Edge | Pendente |
| Média | Compose de produção | `docker-compose.yml` usa `runserver` e bind mount, adequado para rede local/homologação, não para exposição pública | Criar compose/perfil de produção com WSGI/ASGI, imagem imutável e proxy reverso TLS | Pendente |
| Média | PostgreSQL exposto | Porta 5432 publicada no host | Em produção, remover publicação ou restringir por firewall/rede interna | Pendente |

## Correções aplicadas nesta rodada

| Prioridade | Módulo | Problema | Correção | Status |
|---|---|---|---|---|
| Alta | Código/documentação | Arquivos estavam com marcadores de conflito de merge | Removidos conflitos mantendo a linha funcional já homologada | Corrigido |
| Alta | Migrations | `makemigrations --check` indicou alterações de model sem migrations | Geradas e aplicadas migrations corretivas em `accounts`, `administracao`, `caixa`, `clientes`, `fornecedores` e `vendas` | Corrigido |
| Média | Codificação | Textos de interface/testes tinham mojibake em mensagens críticas | Normalizados textos afetados; testes focados e suíte completa aprovados | Corrigido |
| Alta | Qualidade | Suíte completa precisava ser reexecutada após resolução dos conflitos | `204 tests OK` em Docker/PostgreSQL | Corrigido |
| Média | Staticfiles | Necessário comprovar coleta de estáticos | `collectstatic --noinput` executado com sucesso | Corrigido |
| Média | Backup | Necessário comprovar geração/validade do dump | Backup gerado e validado com `pg_restore --list` | Corrigido |

## Evidências desta execução

| Ação | Resultado |
|---|---|
| Busca por marcadores de conflito | Sem ocorrências |
| `docker compose up -d --build` | OK |
| `docker compose exec web python manage.py check` | OK |
| `docker compose exec web python manage.py makemigrations --check` | OK, `No changes detected` |
| `docker compose exec web python manage.py migrate` | OK |
| `docker compose exec web python manage.py test` | OK, 204 testes |
| `docker compose exec web python manage.py collectstatic --noinput` | OK |
| `docker compose exec web python manage.py check --deploy` | 5 warnings de produção |
| `docker compose exec web python manage.py gerar_backup` | OK, `gestix_backup_20260616_220754.dump` |
| `pg_restore --list` | OK, dump custom PostgreSQL válido |

## Decisão de implantação

**Não liberar para produção pública ainda.**

O sistema está estabilizado na bateria automatizada de homologação em Docker/PostgreSQL, sem conflitos de merge e com backup válido. A liberação para produção depende das configurações seguras de ambiente, da restauração em banco descartável e da validação visual das impressões reais.
