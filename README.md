# GESTIX

Estrutura inicial do projeto **GESTIX**, preparada com Django, Django REST Framework e PostgreSQL.

## Módulos criados

- `accounts`
- `clientes`
- `fornecedores`
- `produtos`
- `estoque`
- `vendas`
- `caixa`
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

6. Execute as migrações iniciais e colete os arquivos estáticos:

   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   ```

7. Inicie o servidor de desenvolvimento:

   ```bash
   python manage.py runserver 0.0.0.0:8000
   ```

8. Acesse a aplicação em <http://127.0.0.1:8000/>.




## Como acessar o GESTIX pela rede

O GESTIX pode ser acessado por computadores, tablets e celulares conectados à **mesma rede local** do servidor. Esta configuração não deve ser usada para publicar o sistema diretamente na internet.

### 1. Descobrir o IP do servidor

No computador Windows que executa o GESTIX, abra o Prompt de Comando e execute:

```bat
ipconfig
```

Procure o endereço **IPv4** da placa de rede em uso. No Linux, utilize:

```bash
hostname -I
```

Nos exemplos abaixo o servidor usa `192.168.1.50`. Substitua esse endereço pelo IP real do servidor, preferencialmente configurando uma reserva de IP no roteador para evitar mudanças.

### 2. Configurar o arquivo `.env`

```env
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.50:8000
USE_HTTPS=False
GESTIX_NETWORK_URL=http://192.168.1.50:8000
```

Reinicie o container web após alterar o arquivo:

```bash
docker compose up -d --force-recreate web
```

O Docker publica a porta `8000` do container e inicia o Django em `0.0.0.0:8000`, permitindo conexões vindas da rede local.

### 3. Liberar a porta 8000 no firewall

No Windows, execute o PowerShell ou Prompt de Comando **como Administrador**:

```bat
netsh advfirewall firewall add rule name="GESTIX - Rede Local" dir=in action=allow protocol=TCP localport=8000 profile=private
```

Confirme também que a conexão do Windows está marcada como **Rede privada**. No Linux com UFW:

```bash
sudo ufw allow from 192.168.1.0/24 to any port 8000 proto tcp
```

Ajuste `192.168.1.0/24` para a faixa da rede local. Não crie redirecionamento da porta 8000 no roteador e não use perfil público no firewall.

### 4. Acessar de outro dispositivo

Com o servidor e o Docker em execução, abra no navegador de outro dispositivo conectado à mesma rede:

```text
http://IP-DO-SERVIDOR:8000
```

Exemplo:

```text
http://192.168.1.50:8000
```

O launcher e os atalhos continuam abrindo `http://localhost:8000` no próprio servidor. A mensagem do launcher também informa o endereço configurado para os demais dispositivos da rede.

### 5. Diagnóstico rápido

- Confirme que os dispositivos estão na mesma rede e não em uma rede de convidados isolada.
- Execute `docker compose ps` e confirme que o serviço `web` publica `0.0.0.0:8000->8000/tcp`.
- Teste no servidor primeiro com `http://localhost:8000`.
- Depois teste em outro dispositivo com o IP do servidor.
- Se o IP mudar, atualize `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` e `GESTIX_NETWORK_URL` no `.env` e reinicie o serviço web.

## Arquivos estáticos e Django Admin

O projeto usa **WhiteNoise** para servir os arquivos reunidos em `staticfiles`, inclusive com `DEBUG=False`. O container web executa automaticamente `collectstatic` depois das migrações e antes de iniciar o servidor. O bind mount do código-fonte em `docker-compose.yml` não monta um volume vazio sobre `/app/staticfiles`; a pasta é recriada no próprio container a cada inicialização.

Para atualizar os estáticos em um container já iniciado:

```bash
docker compose exec web python manage.py collectstatic --noinput
docker compose restart web
```

Depois, confirme no navegador que `/static/admin/css/base.css` retorna HTTP 200. Para diagnóstico pelo terminal:

```bash
curl -I http://localhost:8000/static/admin/css/base.css
```

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

1. Cadastre clientes ativos e produtos com estoque disponível.
2. Acesse `/vendas/nova/`.
3. No bloco **Cliente da venda**, pesquise clientes por nome, CPF/CNPJ ou telefone. A busca usa o endpoint interno `/vendas/clientes/buscar/`, exige login, retorna somente clientes ativos e limita os resultados a 10 registros.
4. Clique em **Selecionar** para preencher o cliente da venda; o sistema grava o ID em um campo oculto, exibe os dados básicos e permite trocar o cliente antes de salvar.
5. Digite no campo de pesquisa o nome, código interno ou código de barras do produto.
6. Clique em **Adicionar** para inserir o produto na tabela de itens.
7. Altere a quantidade e confira o recálculo automático de subtotal e total.
8. Tente adicionar produto sem estoque ou quantidade acima do saldo para validar os bloqueios.
9. Abra o caixa em `/caixa/abrir/` antes de finalizar a venda.
10. Salve a venda como `Finalizada` para baixar o estoque e registrar o recebimento automaticamente no caixa.

## Módulo caixa

O módulo `caixa` controla o caixa diário em `/caixa/`, exigindo login e respeitando os perfis de acesso. Administradores e gerentes podem consultar todos os caixas no histórico, vendedores operam apenas o próprio caixa e estoquistas não possuem acesso ao módulo.

Funcionalidades disponíveis:

- abertura de caixa em `/caixa/abrir/` com valor inicial;
- tela de caixa atual em `/caixa/atual/` com resumo financeiro, saldo calculado e movimentações;
- lançamento de suprimento em `/caixa/suprimento/`;
- lançamento de sangria em `/caixa/sangria/`;
- lançamento de saída manual em `/caixa/saida/`;
- fechamento em `/caixa/fechar/`, informando o valor contado para cálculo da diferença;
- histórico em `/caixa/historico/` com filtros por data, usuário e status.

Regras importantes:

- cada usuário pode ter apenas um caixa aberto por vez;
- vendas finalizadas exigem caixa aberto para o usuário logado;
- ao finalizar uma venda, o sistema cria automaticamente uma movimentação do tipo `VENDA` no caixa com o valor total e a forma de pagamento;
- movimentações não podem ser negativas e não podem ser lançadas em caixa fechado;
- sangria e saída reduzem o saldo calculado, enquanto suprimento e venda aumentam o saldo.

Fluxo sugerido:

1. Acesse `/caixa/abrir/` e informe o valor inicial.
2. Registre vendas normalmente; ao finalizar, elas entram automaticamente no caixa.
3. Use `/caixa/sangria/` para registrar retiradas de dinheiro e `/caixa/suprimento/` para adicionar reforço de caixa.
4. Ao final do expediente, acesse `/caixa/fechar/`, confira o saldo calculado e informe o valor contado.
5. Consulte caixas anteriores em `/caixa/historico/`.

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
3. No bloco **Cliente do orçamento**, pesquise clientes por nome, CPF/CNPJ ou telefone. A busca usa o endpoint interno `/orcamentos/clientes/buscar/`, exige login, retorna somente clientes ativos e limita os resultados a 10 registros.
4. Clique em **Selecionar** para preencher o cliente no orçamento. O sistema grava o ID do cliente em um campo oculto, exibe o cliente selecionado e permite trocar/limpar a seleção antes de salvar.
5. Pesquise produtos por nome, código interno ou código de barras.
6. Clique em **Adicionar** para inserir itens na tabela sem recarregar a página.
7. Altere quantidade e valor unitário para simular condições comerciais especiais; os subtotais, desconto e total final serão recalculados automaticamente.
8. Salve o orçamento e confira o detalhe em `/orcamentos/<id>/`.
9. Clique em **Imprimir Orçamento** para abrir o pop-up em `/orcamentos/<id>/imprimir/`; a impressão exibe a seção **Dados do Cliente** com nome, CPF/CNPJ, endereço, telefone, e-mail e inscrição estadual, além da validade de 30 dias.
10. Converta em venda quando necessário; a baixa de estoque acontece apenas nessa conversão e valida a disponibilidade atual dos produtos.


## Notificações de aniversário de clientes

O dashboard pode exibir aniversariantes usando o campo `data_nascimento` do cadastro de clientes. Clientes inativos ou sem data de nascimento não geram notificações.

Para configurar:

1. Acesse **Configurações** no menu lateral ou `/configuracoes/`.
2. Marque ou desmarque **Ativar notificações de aniversário**.
3. Informe **Dias de antecedência para aviso**:
   - `0`: mostra apenas aniversários do dia.
   - `1`: mostra aniversários de hoje e amanhã.
   - `7`: mostra aniversários da semana.
4. Salve as configurações.

Apenas usuários do perfil **Administrador** podem alterar essas opções. Usuários **Gerente** podem visualizar a tela de configurações, enquanto **Vendedor** e **Estoquista** não possuem acesso.

A regra para clientes nascidos em 29/02 considera 28/02 em anos não bissextos.

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

<<<<<<< HEAD
## Backup e Restauração

O GESTIX possui uma tela administrativa em **Administração > Backup e Restauração** (`/administracao/backup/`).

- Apenas usuários Administradores podem acessar, gerar, restaurar e baixar backups.
- Os arquivos são salvos em `backups/`, fora de `static/` e `media/`, e não têm URL pública.
- O formato gerado é o custom format do PostgreSQL (`pg_dump -Fc`) com nome `gestix_backup_YYYYMMDD_HHMMSS.dump`.
- A restauração aceita somente `.dump` e `.backup`, com limite padrão de 500 MB.
- Antes de restaurar, o sistema gera um backup automático de segurança do banco atual.

Pela interface:

1. Acesse **Administração > Backup e Restauração**.
2. Clique em **Gerar Backup** para criar um arquivo novo.
3. Use **Baixar Backup** no histórico para salvar uma cópia local.
4. Para restaurar, envie um arquivo `.dump` ou `.backup`, marque a confirmação explícita e clique em **Restaurar Backup**.

Pelo terminal:

```bash
python manage.py gerar_backup
python manage.py restaurar_backup caminho_do_arquivo.dump
```

No Docker, os comandos podem ser executados dentro do container web:

```bash
docker compose exec web python manage.py gerar_backup
docker compose exec web python manage.py restaurar_backup backups/gestix_backup_DATA.dump
```

Backup manual do banco no Docker:

```bash
docker compose exec -T db pg_dump -U gestix -d gestix -Fc > backups/gestix_backup_DATA.dump
```

Restauração é uma operação destrutiva: ela substitui os dados atuais. Em produção, faça a restauração preferencialmente em janela de manutenção, por comando administrativo ou fila de tarefas, e valide primeiro em uma base descartável.

=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
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
<<<<<<< HEAD
- ações relevantes são registradas no modelo `LogAtividade`, incluindo login, logout, criação/finalização/cancelamento/impressão de venda, criação/conversão de orçamento, movimentações de estoque, abertura/fechamento de caixa, pagamentos, recebimentos, OS, backup/restauração e exclusões básicas de cadastros.
=======
- ações relevantes são registradas no modelo `LogAtividade`, incluindo login, logout, criação/finalização de venda, criação/conversão de orçamento, movimentação manual de estoque e exclusões básicas de cadastros.
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

Perfis de acesso previstos:

- **Administrador**: acesso total.
- **Gerente**: dashboard, vendas, clientes, produtos, estoque e orçamentos.
- **Vendedor**: dashboard, clientes, vendas e orçamentos.
- **Estoquista**: dashboard, produtos, fornecedores e estoque.

> Observação: regras críticas continuam validadas no backend. A finalização de vendas e a conversão de orçamentos em vendas revalidam estoque antes de movimentar saldo.

## Vendas no crediário e contas a receber

O módulo de vendas permite selecionar a forma de pagamento **Crediário** para finalizar a venda, baixar o estoque normalmente e gerar parcelas em **Contas a receber**.

Fluxo de uso:

1. Abra o caixa se houver entrada/sinal ou se for receber parcelas no momento.
2. Acesse **Vendas > Nova venda**.
3. Pesquise e selecione um cliente ativo. Vendas no crediário não devem ser feitas para cliente genérico/consumidor final.
4. Adicione os produtos normalmente.
5. Selecione a forma de pagamento **Crediário**.
6. Informe:
   - quantidade de parcelas;
   - data do primeiro vencimento;
   - intervalo entre parcelas, por padrão 30 dias;
   - valor de entrada/sinal, se existir;
   - observações do crediário, se necessário.
7. Finalize a venda.

Regras principais:

- Sem entrada, a venda no crediário não lança valor no caixa no momento da finalização.
- Com entrada, o caixa registra apenas o valor da entrada com a descrição da venda no crediário.
- O restante é dividido automaticamente em parcelas no módulo **Contas a receber**.
- Diferenças de centavos por arredondamento são ajustadas na última parcela.
- Para receber uma parcela, acesse **Contas a receber**, clique em **Receber** e confirme o pagamento com caixa aberto.
- Se não houver caixa aberto ao receber parcela, o sistema bloqueia o recebimento com a mensagem: “É necessário abrir o caixa antes de receber parcelas.”
- Parcelas abertas vencidas aparecem como **Atrasada** na listagem.
- Ao imprimir o recibo de uma venda no crediário, o documento exibe entrada, quantidade de parcelas e lista de vencimentos/valores.

URLs úteis:

- `/contas-receber/`: listagem e filtros de parcelas.
- `/contas-receber/vencidas/`: parcelas abertas vencidas.
- `/contas-receber/hoje/`: parcelas abertas que vencem no dia.
- `/contas-receber/<id>/receber/`: recebimento de uma parcela.

## Contas a pagar

O módulo **Contas a pagar** permite registrar despesas da empresa, acompanhar vencimentos e baixar pagamentos.

Fluxo básico:

1. Acesse **Contas a pagar > Nova conta**.
2. Informe descrição, fornecedor opcional, categoria, data de emissão, vencimento, valor e observação.
3. Use a listagem em `/contas-pagar/` para filtrar por fornecedor, categoria, status, vencidas, vencem hoje, a vencer e próximos 7 dias.
4. Clique em **Pagar** para registrar data de pagamento, valor pago, forma de pagamento e observação.
5. Pagamentos em **dinheiro** exigem caixa aberto para o usuário e registram uma `MovimentacaoCaixa` do tipo **SAIDA** com a descrição `Pagamento de conta: [descrição]`.
6. Pagamentos por PIX, cartão, boleto, transferência ou outros são registrados no financeiro sem exigir caixa aberto.
7. Contas abertas vencidas aparecem dinamicamente como **Atrasadas**. Contas pagas ou canceladas não entram nos alertas de atraso.
8. Contas abertas podem ser canceladas; contas pagas não devem ser canceladas diretamente sem estorno.

O dashboard exibe, para Administrador e Gerente, cards de **Contas a pagar atrasadas**, **Contas a pagar hoje** e **Próximos 7 dias**, com quantidade, valor total e lista resumida das 5 contas mais relevantes.

## Ordens de serviço

O módulo **Ordens de serviço** centraliza atendimentos técnicos, serviços executados, produtos/peças utilizados, conclusão, pagamento e entrega.

Fluxo recomendado:

1. Acesse **Ordens de serviço > Nova OS** e pesquise um cliente ativo por nome, CPF/CNPJ ou telefone.
2. Informe o problema relatado, previsão, responsável e observações.
3. Pesquise e adicione serviços e produtos/peças. O estoque é apenas consultado nesta etapa e não é baixado na abertura.
4. Salve a OS e utilize a tela de detalhes para registrar diagnóstico, solução e acompanhar o histórico.
5. Ao concluir, o backend revalida o estoque e cria uma saída com origem `ORDEM_SERVICO` para cada peça utilizada. A conclusão é bloqueada se faltar estoque.
6. Depois da conclusão, registre o pagamento. Pagamentos à vista exigem caixa aberto e geram entrada; no crediário, o sistema gera parcelas em **Contas a receber**.
7. Marque a OS concluída como entregue. Depois da entrega, somente administradores podem alterá-la.
8. Use **Imprimir OS** para abrir o documento A4 em uma janela autorizada de impressão.

Perfis: Administrador e Gerente gerenciam todo o fluxo; Vendedor pode criar, visualizar, entregar e receber; Estoquista pode visualizar as ordens e peças necessárias. O dashboard resume OS abertas, em andamento, aguardando peça, concluídas aguardando entrega e atrasadas pela previsão.

## Administração

O menu **Administração** centraliza configurações gerais do GESTIX e fica disponível somente para os perfis **Administrador** e **Gerente**:

<<<<<<< HEAD
A tela inicial apresenta cards responsivos para **Dados da Empresa**, **Configurações do Sistema**, **Usuários e Permissões**, **Backup e Restauração** e **Logs de Atividade**, com resumos e acesso às respectivas consultas.
=======
A tela inicial apresenta cards responsivos para **Dados da Empresa**, **Configurações do Sistema**, **Usuários e Permissões** e **Logs de Atividade**, com resumos e acesso às respectivas consultas.
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7

- **Dados da Empresa**: cadastro único com razão social, nome fantasia, CNPJ, inscrições estadual e municipal, endereço completo, contatos, logos, cores institucionais, responsável e observações. Administradores podem editar em `/administracao/dados-empresa/editar/`; Gerentes acessam somente a visualização.
  Esses dados alimentam automaticamente os cabeçalhos do recibo de venda, orçamento e ordem de serviço; quando não há cadastro, os documentos exibem somente a marca GESTIX. A logo obedece à opção **Mostrar logo nas impressões**.
- **Configurações do Sistema**: cadastro único de preferências compartilhadas, incluindo notificações de aniversário, tempo de logout por inatividade, exibição de logo e assinatura nas impressões e mensagem padrão do rodapé dos documentos.
  O tempo de logout é aplicado tanto pelo backend quanto pelo temporizador do navegador; atividades no navegador renovam a sessão por um endpoint autenticado e, ao expirar, o usuário retorna à tela de login. Na ausência de configuração, o padrão é 15 minutos.

Administradores podem visualizar e alterar os dados. Gerentes possuem acesso somente para consulta, com os campos desabilitados no formulário. Vendedores, Estoquistas e usuários sem perfil não acessam o módulo. A URL anterior `/configuracoes/` é mantida por compatibilidade e redireciona para a nova área administrativa.

<<<<<<< HEAD
### Logs e auditoria

Os logs ficam em **Administração > Logs de Atividade** (`/administracao/logs/`).

- Administradores visualizam todos os registros; Gerentes também podem consultar; Vendedores e Estoquistas não acessam a tela.
- A listagem possui filtros por usuário, ação, módulo, data inicial, data final e texto na descrição.
- A tabela exibe data/hora, usuário, ação, módulo, descrição e IP, sempre com os registros mais recentes primeiro.
- O detalhe do log (`/administracao/logs/<id>/`) mostra também `user_agent`, `objeto_tipo` e `objeto_id`.
- Os logs são somente leitura na interface comum. No Django Admin, apenas superusuários podem excluir registros.
- A função utilitária `registrar_log(usuario, acao, modulo, descricao, objeto=None, request=None)` captura usuário, IP, user-agent e objeto relacionado sem interromper o fluxo principal se houver falha no registro.
- Não registre senhas, dados de cartão, tokens ou outros dados sensíveis em `descricao`.

=======
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
### Diagnóstico da rota inicial

A rota `/` não depende de registros de `Empresa` ou `ConfiguracaoSistema` para ser renderizada. Se as migrations de administração ainda estiverem sendo aplicadas, as preferências usam temporariamente os valores padrão e voltam a persistir pelo singleton assim que o banco estiver disponível. O WhiteNoise continua sendo usado nos containers instalados pelo `requirements.txt`; em um ambiente Python incompleto, o projeto usa o armazenamento estático padrão do Django para que a página inicial não falhe com erro 500.

### Cancelamento de vendas em rascunho

Vendas novas são sempre salvas como **RASCUNHO** e somente movimentam estoque, caixa ou contas a receber quando finalizadas. Enquanto estiver em rascunho, a venda pode ser editada ou cancelada mediante motivo obrigatório. O cancelamento registra usuário, data/hora e motivo no histórico de atividades, bloqueia novas alterações e não realiza qualquer baixa ou lançamento financeiro. Vendas finalizadas não podem usar esse cancelamento simples.
