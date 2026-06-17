# Instalacao em Producao Windows sem Docker

Este guia prepara o GESTIX para rodar em um computador Windows usando PostgreSQL local e Waitress. Nao use `runserver` em producao.

## Requisitos

- Windows 10 ou superior.
- Python 3.12 ou superior.
- PostgreSQL 14 ou superior.
- Acesso de administrador para liberar firewall, se outros computadores acessarem pela rede.

## 1. Preparar Python

Na pasta do projeto:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

O pacote `waitress` esta nas dependencias e sera usado para iniciar a aplicacao.

## 2. Configurar PostgreSQL local

Crie o usuario e banco do GESTIX no PostgreSQL:

```bat
createuser -U postgres gestix
createdb -U postgres -O gestix gestix
psql -U postgres -c "ALTER USER gestix WITH PASSWORD 'troque-esta-senha';"
```

Confirme que os comandos `psql` e `pg_isready` estao no `PATH` do Windows. Se nao estiverem, adicione a pasta `bin` do PostgreSQL, por exemplo:

```text
C:\Program Files\PostgreSQL\16\bin
```

## 3. Criar config/.env

Copie o exemplo:

```bat
copy config\.env.example config\.env
```

Edite `config\.env`:

```env
DEBUG=False
RUNNING_IN_DOCKER=False
SERVER_MODE=True
SECRET_KEY=gere-uma-chave-longa-aleatoria-com-mais-de-50-caracteres
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.50:8000
DB_NAME=gestix
DB_USER=gestix
DB_PASSWORD=troque-esta-senha
DB_HOST=localhost
DB_PORT=5432
USE_HTTPS=False
SERVE_MEDIA_FILES=True
BACKUP_ROOT=backups
LOG_DIR=logs
```

Troque `192.168.1.50` pelo IP fixo ou reservado do computador servidor. Nunca exponha esse servidor diretamente na internet sem HTTPS, proxy reverso e revisao de seguranca.

## 4. Preparar pastas, banco e arquivos estaticos

As pastas abaixo sao criadas automaticamente pelo sistema quando necessario:

- `logs/`
- `backups/`
- `media/`
- `staticfiles/`
- `config/`

Execute:

```bat
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py verificar_producao_windows
```

O verificador retorna `OK`, `ALERTA` ou `ERRO` e gera:

```text
logs\diagnostico.txt
```

Os logs principais ficam em:

```text
logs\gestix.log
logs\errors.log
```

## 5. Iniciar com Waitress

Com o ambiente virtual ativado:

```bat
waitress-serve --listen=0.0.0.0:8000 gestix.wsgi:application
```

Tambem existe o atalho:

```bat
scripts\windows\iniciar_gestix_sem_docker.bat
```

Ele aplica migrations, executa `collectstatic`, roda o verificador e inicia o Waitress.

## 5.1. Iniciar pelo GESTIX.exe

Quando o launcher for gerado com PyInstaller, o sistema tambem pode ser iniciado por:

```bat
GESTIX.exe
```

O launcher:

- valida PostgreSQL;
- aplica migrations;
- executa `collectstatic`;
- verifica a porta 8000 e usa a proxima porta livre se necessario;
- tenta criar a regra de firewall `GESTIX - Rede Local`;
- inicia o Waitress sem abrir prompt;
- grava diagnostico em `logs\launcher_diagnostico.txt`;
- abre o navegador no endereco local.

Para encerrar o processo iniciado pelo launcher:

```bat
GESTIX.exe --stop
```

Para modo servico, use:

```bat
GESTIX.exe --service
```

## 6. Acesso local e pela rede

No proprio servidor:

```text
http://localhost:8000
```

Em outro dispositivo da mesma rede:

```text
http://IP-DO-SERVIDOR:8000
```

Se necessario, libere a porta no Firewall do Windows:

```bat
netsh advfirewall firewall add rule name="GESTIX - Rede Local" dir=in action=allow protocol=TCP localport=8000 profile=private
```

## 7. Backup e restauracao

Pela interface:

- Acesse `Administracao -> Backup e Restauracao`.
- Use `Gerar Backup` para criar arquivos em `backups/`.
- Use `Restaurar Backup` apenas apos confirmar que o arquivo esta correto.

Pelo terminal:

```bat
python manage.py gerar_backup
python manage.py restaurar_backup caminho_do_arquivo.dump
```

A restauracao substitui os dados atuais. Antes de restaurar em producao, gere uma copia de seguranca e garanta que nenhum usuario esteja usando o sistema.

## 8. Diagnostico rapido

Para verificar o ambiente sem iniciar o servidor:

```bat
scripts\windows\verificar_producao_windows.bat
```

Corrija qualquer item marcado como `ERRO` antes da implantacao. Itens `ALERTA` devem ser avaliados, mas nem sempre bloqueiam a execucao.

## 9. Empacotamento

Gere o launcher:

```bat
build_launcher.bat
```

Gere o instalador com Inno Setup:

```bat
build_instalador.bat
```

Resultado esperado:

```text
installer\Output\GESTIX_Instalador.exe
```

Para instalar como servico automatico do Windows, disponibilize o NSSM no `PATH` ou em:

```text
tools\nssm\nssm.exe
```

Depois execute como administrador:

```bat
scripts\windows\instalar_servico.bat
scripts\windows\iniciar_servico.bat
```
