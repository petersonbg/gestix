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
