<<<<<<< HEAD
# Checklist de Homologacao do GESTIX

Data de abertura: **15/06/2026**  
Responsavel tecnico: Codex  
Legenda: **Pendente** = depende de execucao/validacao; **OK** = verificado; **Corrigir** = falha confirmada.

> Esta fase estabiliza o sistema antes da implantacao. Nao criar modulos grandes durante a homologacao; corrigir apenas bugs, validacoes, seguranca, layout e ajustes de implantacao.

## 1. Estrutura geral

| Verificacao | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Apps instalados | Apps principais presentes em `INSTALLED_APPS` | OK | Revisado em `gestix/settings.py` |
| URLs | Rotas principais incluidas em `gestix/urls.py` | OK | Dashboard, administracao, clientes, produtos, estoque, vendas, caixa, financeiro, OS, orcamentos e fiscal |
| Templates | Estrutura de templates por modulo existente | OK | Revisao estatica concluida |
| Staticfiles | Assets em `static/` e `STATIC_ROOT` configurado | OK | `collectstatic --noinput` executado no container web |
| Migrations | Arquivos de migrations presentes por app | OK | `makemigrations --check`: No changes detected |
| `settings.py` | Configuracao externa por env, seguranca e PostgreSQL | OK | `check` aprovado; `check --deploy` gerou avisos esperados sem `.env` de producao |
| `docker-compose.yml` | Servicos `web` e `db` configurados | OK | Build executado; `db` healthy e `web` up |
| `.env.example` | Variaveis documentadas para rede local/Docker | OK | Usar segredos reais em producao |
| Backup e restauracao | Tela/comandos/volume persistente disponiveis | OK parcial | Tela, comandos, volume e backup real validados; restauração destrutiva deve ser homologada em banco descartável |

## 2. Verificacoes automatizadas

| Comando | Resultado esperado | Status | Evidencia |
|---|---|---|---|
| `.venv\Scripts\python.exe manage.py check` | Sem erros | OK | `System check identified no issues (0 silenced).` |
| `.venv\Scripts\python.exe manage.py check --deploy` | Sem alertas criticos apos env de producao | Corrigir | 6 warnings: HTTPS/HSTS/cookies seguros, `SECRET_KEY`, `DEBUG=True` sem `.env` |
| `docker compose exec -T web python manage.py makemigrations --check` | Sem migrations pendentes | OK | `No changes detected` |
| `docker compose exec -T web python manage.py migrate` | Migrations aplicadas | OK | `No migrations to apply` |
| `docker compose exec -T web python manage.py test` | Suite integral aprovada | OK | 173 testes executados com sucesso |
| `.venv\Scripts\python.exe -m compileall ...` | Fontes Python compilam | OK | Apps principais compilados |
| Validadores CPF/CNPJ | Algoritmos aceitam validos e recusam invalidos | OK | Validacao direta e testes Django aprovados |

## 3. Clientes

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Cadastrar cliente | Cliente salvo com dados obrigatorios | OK parcial | Testes de validacao passaram; fluxo visual pendente |
| Editar cliente | Dados atualizados sem perda | Pendente | |
| Buscar cliente | Busca por nome, CPF/CNPJ, IE e telefone | Pendente | Revisao estatica OK |
| Validar CPF/CNPJ | Digitos verificadores obrigatorios | OK | Bug corrigido em `Cliente.clean()`; suite verde |
| Inscricao estadual | Aceita numeros, pontos, barras, hifens ou ISENTO | Pendente | Revisao estatica OK; falta teste integrado |
| Data de nascimento | Nao aceita data futura | OK | Regra existente e teste adicionado |

## 4. Produtos

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Cadastrar produto | Produto salvo com preco e unidade | Pendente | |
| Codigo interno automatico | Sequencia `PROD000001` sem reutilizar exclusoes | Pendente | Revisao estatica OK |
| Preco de custo opcional | Vazio tratado como zero | Pendente | Revisao estatica OK |
| Categoria | Apenas categorias ativas no formulario | Pendente | |
| Chassi apenas para veiculos | Chassi limpo fora de categoria `VEICULOS` | Pendente | Revisao estatica OK |
| Filtro por categoria | Lista filtra corretamente | Pendente | Teste funcional necessario |
| Estoque minimo | Campo preservado e usado em alertas | Pendente | |

## 5. Fornecedores

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Cadastrar fornecedor | Fornecedor salvo com CNPJ valido | OK parcial | Validacao de CNPJ corrigida e testada; fluxo visual pendente |
| Editar fornecedor | Dados atualizados sem perda | Pendente | |
| Buscar fornecedor | Busca por razao social, fantasia, CNPJ e email | Pendente | Revisao estatica OK |

## 6. Estoque

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Entrada manual | Incrementa saldo e registra historico | Pendente | |
| Saida manual | Reduz saldo e registra historico | Pendente | |
| Ajuste | Define saldo final informado | Pendente | |
| Historico | Movimentacoes ordenadas por data | Pendente | |
| Saida maior que estoque | Bloqueada no backend | Pendente | Revisao estatica OK em `MovimentacaoEstoque.registrar()` |

## 7. Vendas

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Pesquisar cliente | Retorna clientes ativos e prioriza correspondencia exata | OK parcial | Teste automatizado aprovado; fluxo visual pendente |
| Adicionar produtos | Itens validos e totais corretos | Pendente | |
| Finalizar venda | Baixa estoque e registra caixa/financeiro | Pendente | |
| Cancelar venda nao finalizada | Cancela apenas rascunho | Pendente | Revisao estatica OK |
| Impedir venda sem estoque | Bloqueio no backend | Pendente | Revisao estatica OK |
| Crediario | Gera parcelas e entrada quando aplicavel | Pendente | |
| Recibo | 14 cm x 21 cm, retrato, legivel | Pendente | Validar no navegador/impressora |

## 8. Caixa

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Abrir caixa | Um caixa aberto por usuario | Pendente | Revisao estatica OK |
| Venda no caixa | Movimento automatico registrado | Pendente | |
| Suprimento | Entrada manual positiva | Pendente | |
| Sangria | Saida manual positiva | Pendente | |
| Saida manual | Saida registrada em caixa aberto | Pendente | |
| Fechamento | Calcula saldo e diferenca | Pendente | |

## 9. Orcamentos

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Pesquisar cliente | Clientes ativos retornados | Pendente | |
| Adicionar produtos | Totais corretos | Pendente | |
| Imprimir orcamento | A5 retrato e conteudo legivel | Pendente | |
| Frase de validade | "Orcamento valido por 30 dias" presente | Pendente | Validar visualmente |
| Converter em venda | Venda criada sem duplicidades | Pendente | |

## 10. Ordens de Servico

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Cadastrar OS | Cliente e dados obrigatorios salvos | Pendente | |
| Selecionar servico via dropdown | Somente servicos ativos | Pendente | Revisao estatica OK |
| Adicionar produtos | Total e estoque consistentes | Pendente | |
| Deslocamento | Soma no total | Pendente | |
| Responsavel e executor | Dados preservados | Pendente | |
| Assinatura | Upload/exibicao correta | Pendente | |
| Data de finalizacao | Gravada ao concluir | Pendente | |
| Bloquear edicao apos finalizar | Bloqueio no backend | Pendente | Revisao estatica OK |
| Imprimir OS | A5 retrato, assinaturas otimizadas | Pendente | Validar visualmente |

## 11. Contas a Receber

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Gerar parcelas no crediario | Parcelas criadas com arredondamento correto | Pendente | |
| Receber parcela | Baixa e movimento de caixa | Pendente | |
| Bloquear recebimento sem caixa | Obrigatorio quando aplicavel | Pendente | Revisao estatica OK |
| Atrasadas no dashboard | Valores corretos no painel | Pendente | |

## 12. Contas a Pagar

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Cadastrar conta | Conta aberta salva | Pendente | |
| Pagar conta | Baixa e caixa quando dinheiro | Pendente | Revisao estatica OK |
| Cancelar conta | Bloqueia conta paga | Pendente | Revisao estatica OK |
| Alertas no dashboard | Vencimentos exibidos | Pendente | |

## 13. Administracao

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Dados da empresa | Cadastro unico editavel por admin | Pendente | |
| Categorias de produtos | CRUD restrito a admin | Pendente | Revisao estatica OK |
| Servicos | CRUD restrito a admin | Pendente | Revisao estatica OK |
| Configuracoes do sistema | Admin edita, gerente visualiza | Pendente | Revisao estatica OK |
| Notificacoes de aniversario | Configuracao aplicada no dashboard | Pendente | |
| Tempo de logout | Sessao expira por inatividade | Pendente | Middleware revisado |
| Usuarios e permissoes | Admin/Gerente visualizam, admin edita | Pendente | |

## 14. Impressoes

| Documento | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Recibo de venda | 140 mm x 210 mm, retrato | Pendente | CSS `@page` revisado |
| Ordem de servico | 140 mm x 210 mm, retrato | Pendente | CSS compartilhado revisado |
| Orcamento | 140 mm x 210 mm, retrato | Pendente | CSS compartilhado revisado |
| Cabecalho | Endereco em uma linha e contato visivel | Pendente | Validar com dados reais |
| Assinaturas | Area compacta sem cortar conteudo essencial | Pendente | Validar com assinatura real |

## 15. Permissoes e seguranca

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| Administrador | Acesso total permitido | Pendente | Requer teste por usuario real |
| Gerente | Acesso gerencial sem edicoes restritas | Pendente | |
| Vendedor | Sem administracao/produtos/estoque indevidos | Pendente | |
| Estoquista | Estoque/produtos/fornecedores/OS conforme matriz | Pendente | |
| Botoes ocultos | UI respeita perfil | Pendente | |
| Validacao backend | POST direto bloqueado conforme perfil | Pendente | |
| Login obrigatorio | Rotas internas protegidas | Pendente | |
| CSRF | POST protegido | Pendente | Middleware presente |
| Cache apos logout | Paginas privadas sem cache | Pendente | Middleware revisado |
| Venda/OS finalizada | Edicao bloqueada no backend | Pendente | Revisao estatica OK |
| Estoque backend | Saida concorrente protegida | Pendente | `select_for_update()` revisado |

## 16. Docker, persistencia e recuperacao

| Cenario | Resultado esperado | Status | Observacoes |
|---|---|---|---|
| `docker compose up -d --build` | Containers `web` e `db` saudaveis | OK | Conflito de `container_name` corrigido; ambiente subiu |
| Container web | Django inicializa, migrations e staticfiles | OK | `gestix-web-1` up; comandos executados |
| Container db | PostgreSQL 16 saudavel | OK | `gestix-db-1` healthy |
| Volumes persistentes | Banco preservado em `postgres_data` | OK parcial | Volume criado; teste de reinicio/restauracao ainda pendente |
| Backup do banco | Arquivo gerado em pasta protegida | OK | `gerar_backup` criou `.dump` validado com `pg_restore --list` |
| Restauracao do banco | Restauracao em banco descartavel comprovada | Pendente | Implementada; executar prova destrutiva somente em banco descartável |

## 17. Criterios de aceite

A implantacao so deve ser autorizada quando:

1. `check`, `makemigrations --check`, `migrate` e `test` estiverem OK em PostgreSQL.
2. Nao houver pendencia critica ou alta aberta.
3. Docker subir com `web` e `db` saudaveis.
4. Backup e restauracao forem comprovados em banco descartavel.
5. Os quatro perfis forem testados no frontend e por POST/URL direta.
6. Recibo, OS e orcamento forem aprovados em PDF/impressao real.
7. `DEBUG=False`, `SECRET_KEY` forte, cookies seguros e HTTPS/proxy estiverem definidos para producao.
=======
# Checklist de Homologação do GESTIX

Data de abertura: **15/06/2026**  
Legenda: **Pendente** = depende de execução/validação; **OK** = verificado; **Corrigir** = falha confirmada.

> Este documento registra a fase de homologação. Marque o status somente após executar o cenário em ambiente equivalente ao de implantação e preencha evidências nas observações.

## 1. Estrutura e ambiente

| Verificação | Resultado esperado | Status | Observações |
|---|---|---|---|
| Apps instalados | Todos os módulos em `INSTALLED_APPS` | OK | Revisão estática concluída |
| URLs | Rotas principais e admin carregadas | OK | Revisão estática concluída |
| Templates | Templates referenciados existem | OK | Estrutura revisada |
| Staticfiles | `collectstatic` sem erro e assets acessíveis | Pendente | Django/dependências indisponíveis no executor |
| Migrations | Sem alterações de model pendentes | Pendente | Executar `makemigrations --check` |
| Settings e `.env` | Configuração externa, hosts, CSRF e mídia coerentes | OK | URL de mídia e modo LAN revisados |
| Docker Compose | Web/DB saudáveis e volume persistente | Pendente | Docker indisponível no executor |

## 2. Verificações automatizadas obrigatórias

| Comando | Resultado esperado | Status | Observações |
|---|---|---|---|
| `python manage.py check` | Sem erros | Pendente | Django não instalado; instalação bloqueada pela rede |
| `python manage.py makemigrations --check` | “No changes detected” | Pendente | Mesma limitação |
| `python manage.py migrate` | Todas as migrations aplicadas | Pendente | Requer PostgreSQL/Django |
| `python manage.py test` | Suíte integral aprovada | Pendente | Requer dependências |
| `python -m compileall ...` | Fontes Python compilam | OK | Executado na homologação |

## 3. Checklist funcional por módulo

### Clientes

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/editar/buscar | Persistência e busca corretas | Pendente | |
| CPF/CNPJ | Formato e regra de negócio validados | Pendente | |
| Inscrição estadual/data de nascimento | Campos preservados | Pendente | |

### Produtos

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastro e código automático | Código único sequencial | Pendente | |
| Preço de custo opcional | Vazio tratado como zero | Pendente | |
| Categoria e filtro | Apenas categorias válidas; filtro combinável | Pendente | |
| Chassi | Persistido somente para veículos | Pendente | |
| Estoque mínimo | Alerta/campo consistente | Pendente | |

### Fornecedores

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/editar/buscar | Fluxos sem perda de dados | Pendente | |

### Estoque

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Entrada/saída/ajuste | Saldo e histórico consistentes | Pendente | |
| Saída acima do saldo | Operação recusada no backend | Pendente | |

### Vendas

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Pesquisar cliente/produto | Resultados relevantes e ativos | Pendente | Correspondência exata de cliente priorizada |
| Finalizar/cancelar rascunho | Estados e integrações consistentes | Pendente | |
| Venda sem estoque | Recusada no backend | Pendente | |
| Crediário | Parcelas geradas corretamente | Pendente | |
| Recibo | A5 14×21 cm retrato, legível | Pendente | Validar Chrome, Edge e Firefox |

### Caixa

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Abrir/suprimento/sangria/saída | Movimentos e saldo corretos | Pendente | |
| Venda e fechamento | Valores e diferença corretos | Pendente | |

### Orçamentos

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cliente e produtos | Inclusão e totais corretos | Pendente | |
| Impressão | A5 e frase “ORÇAMENTO VÁLIDO POR 30 DIAS” | Pendente | |
| Converter em venda | Dados transferidos sem duplicação | Pendente | |

### Ordens de Serviço

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastro/cliente/serviço dropdown | Somente serviços ativos | Pendente | |
| Produtos/deslocamento/desconto | Total correto e estoque íntegro | Pendente | |
| Responsáveis, assinatura e conclusão | Dados exibidos e edição final bloqueada | Pendente | |
| Impressão | A5, assinaturas compactas e conteúdo íntegro | Pendente | |

### Contas a Receber

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Parcelas/recebimento | Baixa e caixa consistentes | Pendente | |
| Caixa obrigatório | Recebimento bloqueado quando aplicável | Pendente | |
| Atrasos no dashboard | Valores e datas corretos | Pendente | |

### Contas a Pagar

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Cadastrar/pagar/cancelar | Estado e caixa consistentes | Pendente | |
| Alertas no dashboard | Vencimentos corretos | Pendente | |

### Administração

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Dados da empresa/logotipos | Upload válido e mídia acessível | Pendente | Validador não falha em arquivo já persistido |
| Categorias/serviços | CRUD conforme perfil | Pendente | |
| Configurações | Aniversários e logout aplicados | Pendente | |

## 4. Impressões

| Documento | Resultado esperado | Status | Observações |
|---|---|---|---|
| Recibo de venda | 140×210 mm, retrato, assinatura centralizada | Pendente | Testar até 20 itens |
| Ordem de serviço | 140×210 mm, assinaturas lado a lado | Pendente | Testar serviços e produtos |
| Orçamento | 140×210 mm, validade e totais legíveis | Pendente | Testar até 20 itens |
| Cabeçalho | Endereço em uma linha e contato visível | Pendente | |

## 5. Permissões e segurança

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| Administrador/Gerente/Vendedor/Estoquista | Acesso e botões conforme perfil | Pendente | Validar também POST direto |
| Login/CSRF | Rotas protegidas e POST com CSRF | Pendente | Middleware presente; requer teste integrado |
| Logout por inatividade/cache | Sessão encerrada e páginas privadas não reutilizadas | Pendente | |
| Venda/OS finalizada | Edição bloqueada no backend | Pendente | |
| Estoque | Validação concorrente no backend | Pendente | |

## 6. Docker, persistência e recuperação

| Cenário | Resultado esperado | Status | Observações |
|---|---|---|---|
| `docker compose up -d --build` | Web e DB saudáveis | Pendente | Docker indisponível neste executor |
| Migrate/collectstatic | Inicialização sem erro | Pendente | |
| Reinício | Banco preservado no volume | Pendente | |
| Backup/restauração | SQL gerado e restaurado em banco de teste | Pendente | Scripts corrigidos; validar em Windows |
| Mídia | Logos/assinaturas acessíveis com DEBUG=False | Pendente | `SERVE_MEDIA_FILES=True` para rede local |

## 7. Critérios de aceite

A implantação somente deve ser autorizada quando:

1. todos os comandos obrigatórios estiverem **OK**;
2. não houver pendência de prioridade crítica ou alta;
3. backup e restauração forem comprovados em banco descartável;
4. os quatro perfis forem testados no frontend e por requisição direta;
5. as três impressões forem aprovadas nos navegadores-alvo;
6. segredos, senha do banco, hosts e HTTPS estiverem configurados para o ambiente real.
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
