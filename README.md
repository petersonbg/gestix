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

## Estrutura inicial

- Configurações do projeto em `gestix/settings.py`.
- Rotas principais em `gestix/urls.py`.
- Templates globais em `templates/`.
- Arquivos estáticos globais em `static/`.
- Tela inicial simples em `templates/core/home.html` usando Bootstrap 5.

## Observações

Esta etapa cria apenas a base do projeto. Regras de negócio, modelos completos, APIs específicas e telas internas serão implementados nas próximas fases.
