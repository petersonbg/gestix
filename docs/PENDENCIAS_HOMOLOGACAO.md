<<<<<<< HEAD
# Pendencias da Homologacao do GESTIX

Data: **15/06/2026**

## Pendencias abertas

| Prioridade | Modulo | Erro/risco encontrado | Sugestao de correcao | Status |
|---|---|---|---|---|
| Alta | Backup e Restauracao | A restauração destrutiva ainda não foi executada em banco descartável nesta homologação | Restaurar um `.dump` em base descartável e conferir contagens/totais antes de produção | Pendente |
| Alta | Seguranca | `manage.py check --deploy` gerou warnings por falta de configuracao de producao: HTTPS/HSTS, cookies seguros, `SECRET_KEY` forte e `DEBUG=False` | Definir `.env` de producao com `DEBUG=False`, `USE_HTTPS=True`, chave forte e proxy/TLS antes de exposicao externa | Pendente |
| Alta | Homologacao funcional | Fluxos de clientes, produtos, estoque, vendas, caixa, financeiro, OS e orcamentos ainda nao foram executados manualmente em navegador com massa de homologacao | Criar base de homologacao e percorrer o checklist por modulo | Pendente |
| Media | Impressao | Recibo, OS e orcamento dependem de validacao visual em PDF/impressora real | Gerar PDFs com dados reais, muitos itens e assinaturas/logos; validar Chrome/Edge | Pendente |
| Media | Permissoes | Matriz completa dos perfis Administrador, Gerente, Vendedor e Estoquista ainda depende de teste integrado | Validar acesso, botoes ocultos e POST direto para cada perfil | Pendente |
| Media | Compose de producao | `docker-compose.yml` usa `runserver` e bind mount do codigo, adequado para rede local/homologacao, nao para exposicao publica | Criar compose/perfil de producao com servidor WSGI/ASGI, imagem imutavel e proxy reverso | Pendente |
| Media | PostgreSQL exposto | Porta 5432 publicada no host | Em producao, remover publicacao ou restringir por firewall/rede interna | Pendente |

## Correcoes aplicadas nesta rodada

| Prioridade | Modulo | Problema | Correcao | Status |
|---|---|---|---|---|
| Alta | Clientes | CPF/CNPJ nao validava digitos verificadores no backend | Criado validador de CPF/CNPJ e integrado ao `Cliente.clean()` | Corrigido |
| Alta | Fornecedores | CNPJ nao validava digitos verificadores no backend | Integrado validador de CNPJ ao `Fornecedor.clean()` | Corrigido |
| Media | Testes | Nao havia cobertura especifica para CPF/CNPJ em clientes/fornecedores | Adicionados testes em `clientes/tests.py` e `fornecedores/tests.py` | Corrigido |
| Alta | Backup e Restauracao | Não existiam model, tela, comandos e template para backup/restauração | Implementados `BackupRegistro`, `/administracao/backup/`, download protegido, commands e testes | Corrigido |
| Media | Docker | `container_name` fixo colidia com containers de outro checkout (`gestix-main`) | Removidos `container_name` de `web` e `db`; compose agora cria `gestix-web-1` e `gestix-db-1` | Corrigido |
| Media | Vendas | Busca de cliente por telefone/documento tinha caso de teste ambiguo e ordenacao pouco explicita | Priorizadas correspondencias exatas, telefone, documento e nome; teste ajustado com fragmentos nao sobrepostos | Corrigido |
| Baixa | Staticfiles | Teste da home exigia `/static/css/home.css`, mas WhiteNoise gera nome com hash em producao | Teste atualizado para aceitar arquivo versionado | Corrigido |
| Baixa | Produtos | Testes de filtro nao atribuiam perfil permitido ao usuario, causando redirect de permissao | Usuario de teste recebeu grupo `Estoquista` | Corrigido |

## Evidencias desta execucao

| Acao | Resultado |
|---|---|
| Dependencias Python | Instaladas em `.venv` a partir de `requirements.txt` |
| `manage.py check` | OK, sem issues |
| `manage.py check --deploy` | 6 warnings de configuracao de producao |
| `docker compose up -d --build` | OK apos remover `container_name` fixo |
| `docker compose exec -T web python manage.py check` | OK, sem issues |
| `docker compose exec -T web python manage.py makemigrations --check` | OK, `No changes detected` |
| `docker compose exec -T web python manage.py migrate` | OK, `No migrations to apply` |
| `docker compose exec -T web python manage.py test` | OK, 173 testes aprovados |
| `docker compose exec -T web python manage.py collectstatic --noinput` | OK, 156 staticfiles e 409 pos-processados |
| `docker compose exec -T web python manage.py gerar_backup` | OK, arquivo `.dump` criado em `backups/` |
| `pg_restore --list backups/gestix_backup_20260616_180051.dump` | OK, formato custom PostgreSQL validado |
| `compileall` | OK para apps principais e arquivos alterados |
| Validacao direta CPF/CNPJ | OK |

## Decisao de implantacao

**Nao liberar para producao ainda.**

O sistema passou na bateria automatizada em Docker e recebeu correcoes pontuais de validacao, busca, permissao de teste e staticfiles. A homologacao ainda depende de validacao funcional manual por perfil, validacao visual das impressoes e implementacao/homologacao do modulo de backup e restauracao.
=======
# Pendências da Homologação do GESTIX

Data: **15/06/2026**

## Pendências abertas

| Prioridade | Módulo | Erro/risco encontrado | Sugestão de correção | Status |
|---|---|---|---|---|
| Alta | Qualidade | Não foi possível executar `manage.py check`, migrations e testes porque Django não está instalado e o download de dependências foi bloqueado pela rede do executor | Executar os comandos no container/CI com acesso às dependências antes de liberar a implantação | Pendente |
| Alta | Docker | Docker CLI não está disponível neste executor; build, healthcheck, volume e integração PostgreSQL não foram comprovados | Executar o roteiro Docker completo em Windows e Linux | Pendente |
| Alta | Segurança | `.env.example` contém credenciais demonstrativas e a aplicação possui fallback de chave secreta | Gerar `SECRET_KEY` forte e senhas exclusivas; nunca reutilizar valores de exemplo | Pendente |
| Alta | Servidor | Compose inicia o servidor de desenvolvimento do Django (`runserver`) | Antes de exposição pública, adotar servidor WSGI/ASGI de produção e proxy reverso TLS | Pendente |
| Média | Docker | PostgreSQL publica a porta 5432 no host | Remover a publicação em produção ou restringir por firewall | Pendente |
| Média | Docker | O código-fonte é montado em `/app`, adequado ao uso local, mas não a uma imagem imutável | Criar variante de compose para produção sem bind mount | Pendente |
| Média | Impressão | A validação visual A5 depende de navegador e impressora reais | Homologar Chrome, Edge e Firefox com os cenários de 20 itens | Pendente |
| Média | Permissões | Matriz completa dos quatro perfis ainda depende de teste integrado | Criar evidências por perfil e testar POST/URLs diretas | Pendente |
| Média | Windows | Backup e restauração foram corrigidos, mas não executados em Windows/Docker | Restaurar um backup em banco descartável e conferir contagens/totais | Pendente |

## Correções aplicadas nesta fase

| Prioridade | Módulo | Problema | Correção | Status |
|---|---|---|---|---|
| Alta | Administração | Validação de logo podia lançar erro de storage ao validar um `FieldFile` já persistido e indisponível | Tratamento seguro para arquivos já comprometidos no storage, preservando validação de novos uploads | Corrigido |
| Alta | Mídia/Docker | Logos e assinaturas não eram servidos com `DEBUG=False`; `MEDIA_URL` também não tinha barra inicial | URL normalizada e rota de mídia local controlada por `SERVE_MEDIA_FILES` | Corrigido |
| Média | Vendas | Busca parcial podia colocar outro cliente antes da correspondência exata | Correspondências exatas agora recebem prioridade | Corrigido |
| Alta | Backup | Aspas dos comandos `pg_dump`/`psql` nos scripts BAT impediam expansão correta das variáveis dentro do container | Comandos ajustados para expansão pelo shell do container | Corrigido |

## Decisão de implantação

**Não liberar para produção ainda.** A revisão estática e as correções acima avançam a estabilidade, mas a aprovação final depende da suíte Django, do PostgreSQL via Docker, dos testes funcionais por perfil, das impressões físicas/PDF e de um teste real de recuperação de backup.
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
