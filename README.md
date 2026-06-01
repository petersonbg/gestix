# GESTIX

Estrutura inicial do projeto **GESTIX**, preparada com Django, Django REST Framework e PostgreSQL.

## Módulos criados

- `accounts`
- `clientes`
- `fornecedores`
- `produtos`
- `estoque`
- `vendas`
- `orcamentos`
- `fiscal`
- `dashboard`

## Requisitos

- Python 3.12+
- PostgreSQL 14+
- `pip` e `venv`
- Docker e Docker Compose, para execução em containers

## Instalação

1. Crie e ative um ambiente virtual:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Instale as dependências:

   ```bash
   pip install -r requirements.txt
   ```

3. Crie o arquivo de variáveis de ambiente:

   ```bash
   cp .env.example .env
   ```

4. Ajuste as variáveis do PostgreSQL no arquivo `.env`:

   ```env
   POSTGRES_DB=gestix
   POSTGRES_USER=gestix
   POSTGRES_PASSWORD=gestix
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5432
   ```

5. Crie o banco no PostgreSQL, caso ainda não exista:

   ```bash
   createdb gestix
   ```

6. Execute as migrações iniciais:

   ```bash
   python manage.py migrate
   ```

7. Inicie o servidor de desenvolvimento:

   ```bash
   python manage.py runserver
   ```

8. Acesse a aplicação em <http://127.0.0.1:8000/>.




## Módulo clientes

O módulo `clientes` possui CRUD completo protegido por login em `/clientes/`. A listagem permite buscar por nome, CPF/CNPJ ou telefone.

Campos disponíveis no cadastro:

- nome, tipo de pessoa, CPF/CNPJ, telefone, email
- endereço, cidade, estado, observações
- status ativo, data de criação e data de atualização


## Módulo fornecedores

O módulo `fornecedores` possui CRUD completo protegido por login em `/fornecedores/`. A listagem permite buscar por razão social, nome fantasia ou CNPJ.

Campos disponíveis no cadastro:

- razão social, nome fantasia, CNPJ, inscrição estadual
- telefone, email, endereço, cidade, estado, observações
- status ativo, data de criação e data de atualização


## Módulo produtos

O módulo `produtos` possui CRUD completo protegido por login em `/produtos/`. A listagem permite buscar por nome, código interno ou código de barras.

Campos disponíveis no cadastro:

- nome, descrição, código interno, código de barras, categoria e unidade de medida
- preço de custo, preço de venda, estoque mínimo, fornecedor e NCM
- status ativo, data de criação e data de atualização

O preço de custo e o preço de venda não podem ser negativos, e o preço de venda deve ser maior ou igual ao preço de custo.


## Módulo estoque

O módulo `estoque` possui tela protegida por login em `/estoque/` para acompanhar saldos e acessar o histórico por produto. A movimentação manual fica em `/estoque/movimentar/`.

Funcionalidades disponíveis:

- movimentações de ENTRADA, SAIDA e AJUSTE
- atualização automática do saldo atual do produto
- histórico de movimentações por produto
- bloqueio de saída com quantidade maior que o estoque disponível

Em movimentações do tipo AJUSTE, a quantidade informada passa a ser o novo saldo atual do produto.


## Módulo vendas

O módulo `vendas` possui listagem em `/vendas/`, detalhe da venda e tela de cadastro em `/vendas/nova/` com múltiplos itens.

Funcionalidades disponíveis:

- venda com cliente, data, subtotal, desconto, total, status e usuário
- itens com produto, quantidade, valor unitário e total do item
- finalização de venda com baixa automática no estoque
- bloqueio de finalização quando algum produto não possui estoque suficiente

Vendas criadas como rascunho podem ser finalizadas pela tela de detalhes.




### Imprimindo recibo de venda

Após finalizar uma venda, acesse a tela de detalhes da venda e clique em **Imprimir Recibo**. O botão abre a URL `/vendas/<id>/imprimir/` em uma janela pop-up dedicada, sem menu lateral ou elementos administrativos; essa página é somente leitura, não altera dados da venda e não gera nova movimentação de estoque.

O layout de impressão foi otimizado para papel A5 em orientação paisagem, com dados da venda, cliente, vendedor, itens, resumo financeiro, botão **Imprimir** no pop-up e campo centralizado apenas para assinatura do cliente.

### Testando a venda dinâmica

Para testar a tela dinâmica de vendas:

1. Cadastre ou importe produtos com estoque disponível.
2. Acesse `/vendas/nova/`.
3. Digite no campo de pesquisa o nome, código interno ou código de barras do produto.
4. Clique em **Adicionar** para inserir o produto na tabela de itens.
5. Altere a quantidade e confira o recálculo automático de subtotal e total.
6. Tente adicionar produto sem estoque ou quantidade acima do saldo para validar os bloqueios.
7. Salve a venda como `Finalizada` para baixar o estoque automaticamente.

## Módulo orçamentos

O módulo `orcamentos` possui listagem em `/orcamentos/`, detalhe, cadastro em `/orcamentos/novo/` com múltiplos produtos e template de impressão.

Funcionalidades disponíveis:

- orçamento com cliente, subtotal, desconto, total, status e usuário
- itens com produto, quantidade, valor unitário e total do item
- status Aberto, Aprovado, Rejeitado e Convertido
- conversão de orçamento em venda finalizada com baixa automática no estoque
- bloqueio da conversão quando algum produto não possui estoque suficiente

### Testando a tela dinâmica de orçamentos

Para testar o cadastro dinâmico de orçamentos:

1. Cadastre clientes e produtos ativos em `/clientes/` e `/produtos/`.
2. Acesse `/orcamentos/novo/`.
3. Pesquise produtos por nome, código interno ou código de barras.
4. Clique em **Adicionar** para inserir itens na tabela sem recarregar a página.
5. Altere quantidade e valor unitário para simular condições comerciais especiais; os subtotais, desconto e total final serão recalculados automaticamente.
6. Salve o orçamento e confira o detalhe em `/orcamentos/<id>/`.
7. Converta em venda quando necessário; a baixa de estoque acontece apenas nessa conversão e valida a disponibilidade atual dos produtos.

## Módulo fiscal

O módulo `fiscal` possui importação de XML de NF-e em `/fiscal/upload/`, listagem em `/fiscal/` e confirmação de entrada no estoque.

Funcionalidades disponíveis nesta etapa:

- leitura da chave de acesso, número, série, data de emissão, emitente, valor total e itens da NF-e
- verificação de duplicidade pela chave de acesso
- cadastro automático do fornecedor quando o CNPJ do emitente ainda não existir
- listagem dos produtos encontrados no XML
- vínculo de item do XML a produto existente ou criação de produto novo
- geração de entrada no estoque após confirmação

A integração com a SEFAZ não foi implementada nesta etapa.

## Autenticação e perfis de acesso

O módulo `accounts` usa a autenticação padrão do Django. A migração inicial do app cria os grupos de acesso:

- Administrador
- Gerente
- Vendedor
- Estoquista

Após executar as migrações, crie um superusuário e atribua usuários aos grupos pelo Django Admin:

```bash
python manage.py createsuperuser
```

As páginas internas começam em `/dashboard/`, exigem login e exibem o nome do usuário autenticado no topo.

## Executando com Docker

1. Crie o arquivo de variáveis de ambiente, se ainda não existir:

   ```bash
   cp .env.example .env
   ```

2. Suba os serviços `web` e `db` com Docker Compose:

   ```bash
   docker compose up --build
   ```

   O serviço `db` usa a imagem oficial `postgres:16-alpine` e o serviço `web` aplica as migrações antes de iniciar o servidor Django. No Docker Compose, o Django se conecta ao PostgreSQL usando `POSTGRES_HOST=db`.

3. Acesse a aplicação em <http://localhost:8000/>.

4. Para executar comandos Django dentro do container:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

5. Para parar os containers:

   ```bash
   docker compose down
   ```

6. Para remover também o volume do banco de dados local:

   ```bash
   docker compose down -v
   ```

### Atalhos para Windows

A pasta `scripts/windows/` possui arquivos `.bat` para facilitar o uso do GESTIX no Windows com Docker Desktop:

- `scripts/windows/iniciar_gestix.bat`: acessa automaticamente a pasta raiz do projeto, executa `docker compose up -d`, aguarda alguns segundos e abre <http://localhost:8000/> no navegador padrão.
- `scripts/windows/parar_gestix.bat`: acessa automaticamente a pasta raiz do projeto, executa `docker compose down` e informa que o sistema foi encerrado.
- `scripts/windows/backup_banco.bat`: cria backups PostgreSQL na pasta `backups/`.
- `scripts/windows/restaurar_banco.bat`: restaura um backup `.sql` informado pelo usuário.
- `scripts/windows/resetar_banco.bat`: recria o banco local após confirmação explícita.

Os arquivos `Iniciar_GESTIX.bat` e `Parar_GESTIX.bat` continuam disponíveis como atalhos compatíveis com a primeira rotina de Docker no Windows.

Como usar:

1. Instale e abra o Docker Desktop.
2. Aguarde o Docker Desktop finalizar a inicialização.
3. Dê duplo clique em `scripts/windows/iniciar_gestix.bat` para subir o sistema.
4. Dê duplo clique em `scripts/windows/parar_gestix.bat` quando quiser encerrar os containers.

Se o Docker Desktop não estiver aberto, o script de inicialização exibirá uma mensagem amigável solicitando que ele seja iniciado antes de tentar novamente.


## Empacotamento e instalação no Windows

O projeto possui uma estrutura para distribuição em máquinas Windows usando PyInstaller e Inno Setup:

- `launcher/gestix_launcher.py`: launcher gráfico que valida o Docker Desktop, executa `docker compose up -d`, aguarda a inicialização e abre <http://localhost:8000>.
- `launcher/build_launcher.bat`: gera `launcher/dist/GESTIX.exe` com PyInstaller usando `--onefile --noconsole`; se existir `launcher/gestix.ico`, o ícone será aplicado ao executável.
- `installer/gestix_installer.iss`: script do Inno Setup para gerar o instalador `.exe` com diretório padrão `C:\GESTIX`, atalhos no desktop/menu iniciar e verificação de Docker Desktop instalado.
- `scripts/windows/`: scripts para iniciar, parar, resetar banco, gerar backup e restaurar backup.
- `docs/INSTALACAO_WINDOWS.md`: guia operacional para instalação, abertura, parada, backup, restauração e desinstalação no Windows.

Fluxo recomendado para gerar o instalador:

1. Em uma máquina Windows com Python, execute `launcher/build_launcher.bat` para gerar `launcher/dist/GESTIX.exe`.
2. Instale o Inno Setup.
3. Abra `installer/gestix_installer.iss` no Inno Setup Compiler.
4. Compile o instalador.
5. Distribua o `.exe` gerado para instalação no Windows.

Após instalado, o usuário final deve abrir o Docker Desktop e clicar no atalho **GESTIX** na área de trabalho. O sistema será iniciado sem necessidade de digitar comandos no terminal.

## Estrutura inicial

- Configurações do projeto em `gestix/settings.py`.
- Rotas principais em `gestix/urls.py`.
- Templates globais em `templates/`.
- Arquivos estáticos globais em `static/`.
- Tela inicial simples em `templates/core/home.html` usando Bootstrap 5.

## Observações

Esta etapa cria apenas a base do projeto. Regras de negócio, modelos completos, APIs específicas e telas internas serão implementados nas próximas fases.

## Segurança da aplicação

O GESTIX possui uma camada inicial de segurança para reduzir uso indevido das telas internas:

- todas as páginas internas usam autenticação do Django com `LoginRequiredMixin` ou views protegidas;
- APIs internas do Django REST Framework exigem usuário autenticado por padrão;
- sessões expiram após 15 minutos (`SESSION_COOKIE_AGE = 900`), são salvas a cada requisição e encerram ao fechar o navegador;
- a interface monitora clique, digitação, rolagem, toque e movimento do mouse, exibindo aviso no último minuto antes do logout automático por inatividade;
- cookies de sessão e CSRF são `HttpOnly` e `SameSite=Lax`; em produção (`DEBUG=False`) ficam preparados para `Secure=True`;
- `X_FRAME_OPTIONS = "DENY"`, proteção contra MIME sniffing, política de referer `same-origin` e HSTS em produção estão configurados;
- páginas internas autenticadas recebem cabeçalhos `Cache-Control`, `Pragma` e `Expires` para evitar cache e impedir visualização indevida após logout;
- telas internas comuns devem ser abertas pelo fluxo principal do sistema. O JavaScript global `static/js/security-navigation.js` bloqueia botão direito, Ctrl/Cmd+clique, Shift+clique e botão do meio em links internos; aberturas diretas indevidas redirecionam para o dashboard com aviso;
- as exceções autorizadas para pop-up são a impressão de recibo de venda e a impressão de orçamento;
- o controle por perfil segue os grupos `Administrador`, `Gerente`, `Vendedor` e `Estoquista` criados pela migration de `accounts`;
- usuários sem perfil definido são redirecionados ao dashboard ao tentar acessar módulos operacionais;
- ações relevantes são registradas no modelo `LogAtividade`, incluindo login, logout, criação/finalização de venda, criação/conversão de orçamento, movimentação manual de estoque e exclusões básicas de cadastros.

Perfis de acesso previstos:

- **Administrador**: acesso total.
- **Gerente**: dashboard, vendas, clientes, produtos, estoque e orçamentos.
- **Vendedor**: dashboard, clientes, vendas e orçamentos.
- **Estoquista**: dashboard, produtos, fornecedores e estoque.

> Observação: regras críticas continuam validadas no backend. A finalização de vendas e a conversão de orçamentos em vendas revalidam estoque antes de movimentar saldo.
