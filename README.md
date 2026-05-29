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

## Estrutura inicial

- Configurações do projeto em `gestix/settings.py`.
- Rotas principais em `gestix/urls.py`.
- Templates globais em `templates/`.
- Arquivos estáticos globais em `static/`.
- Tela inicial simples em `templates/core/home.html` usando Bootstrap 5.

## Observações

Esta etapa cria apenas a base do projeto. Regras de negócio, modelos completos, APIs específicas e telas internas serão implementados nas próximas fases.
