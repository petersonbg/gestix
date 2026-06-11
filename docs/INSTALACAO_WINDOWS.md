# Instalação do GESTIX no Windows

Este guia explica como instalar e operar o GESTIX em uma máquina Windows usando o instalador gerado pelo Inno Setup.

## Pré-requisitos

- Windows 10 ou superior.
- Docker Desktop instalado.
- Docker Desktop aberto e completamente inicializado antes de iniciar o GESTIX.

> O instalador do GESTIX verifica se o Docker Desktop está instalado, mas não instala o Docker automaticamente nesta etapa.

## Como instalar

1. Gere o executável `GESTIX.exe` do launcher executando `launcher/build_launcher.bat` em uma máquina com Python.
2. Compile o instalador `installer/gestix_installer.iss` usando o Inno Setup.
3. Execute o instalador `.exe` gerado.
4. Mantenha o diretório padrão `C:\GESTIX` ou escolha outro diretório de instalação.
5. Finalize a instalação.

## Como abrir o sistema

1. Abra o Docker Desktop.
2. Aguarde o Docker Desktop informar que está pronto.
3. Clique no atalho **GESTIX** na área de trabalho ou no menu iniciar.
4. O launcher iniciará os containers com `docker compose up -d` e abrirá <http://localhost:8000> no navegador.

Caso o Docker Desktop não esteja aberto, o GESTIX exibirá uma mensagem solicitando que ele seja iniciado antes de tentar novamente.

## Como parar o sistema

Use uma das opções abaixo:

- Pelo menu iniciar, clique em **Parar GESTIX**.
- Ou execute `C:\GESTIX\scripts\windows\parar_gestix.bat`.

Esse script executa `docker compose down` e encerra os containers do sistema.

## Como fazer backup do banco

1. Garanta que o Docker Desktop esteja aberto e que os containers do GESTIX estejam em execução.
2. Execute `C:\GESTIX\scripts\windows\backup_banco.bat`.
3. O backup será salvo na pasta `C:\GESTIX\backups\` com data e hora no nome do arquivo.

O backup é gerado com `pg_dump` dentro do container PostgreSQL.

## Como restaurar backup

1. Copie o arquivo `.sql` para a pasta `C:\GESTIX\backups\`, se ele ainda não estiver lá.
2. Execute `C:\GESTIX\scripts\windows\restaurar_banco.bat`.
3. Informe o caminho do arquivo, por exemplo: `backups\gestix_20260101_120000.sql`.
4. Confirme a restauração digitando `RESTAURAR`.

> Atenção: a restauração pode sobrescrever dados atuais, dependendo do conteúdo do arquivo SQL restaurado.

## Como resetar o banco local

Execute `C:\GESTIX\scripts\windows\resetar_banco.bat` e confirme digitando `APAGAR`.

Esse procedimento executa `docker compose down -v`, recria os containers e roda as migrations. Todos os dados locais serão apagados.

## Como desinstalar

1. Abra o menu iniciar.
2. Clique em **Desinstalar GESTIX**.
3. Siga as instruções do desinstalador.

Se desejar apagar também os dados locais do PostgreSQL, execute `scripts\windows\resetar_banco.bat` antes da desinstalação ou remova manualmente os volumes Docker associados ao projeto.

## Problemas comuns

### Docker Desktop não está aberto

Abra o Docker Desktop, aguarde a inicialização completa e clique novamente no atalho **GESTIX**.

### A página não abriu automaticamente

Acesse manualmente <http://localhost:8000> no navegador.

### Porta 8000 em uso

Feche outro serviço que esteja usando a porta 8000 ou ajuste o mapeamento de porta no `docker-compose.yml`.

## Acesso pela rede local

Para acessar o GESTIX a partir de outros computadores, tablets ou celulares da mesma rede:

1. Descubra o IPv4 do servidor executando `ipconfig` no Prompt de Comando.
2. Atualize o `.env`, substituindo `192.168.1.50` pelo IP real:

   ```env
   ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.50
   CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,http://192.168.1.50:8000
   USE_HTTPS=False
   GESTIX_NETWORK_URL=http://192.168.1.50:8000
   ```

3. Em um terminal executado como Administrador, libere apenas a porta TCP 8000 no perfil privado do Windows:

   ```bat
   netsh advfirewall firewall add rule name="GESTIX - Rede Local" dir=in action=allow protocol=TCP localport=8000 profile=private
   ```

4. Recrie o serviço web com `docker compose up -d --force-recreate web`.
5. Em outro dispositivo da mesma rede, acesse `http://IP-DO-SERVIDOR:8000`.

O launcher continua abrindo `http://localhost:8000` no servidor. Não encaminhe a porta 8000 no roteador e não exponha esta instalação diretamente à internet.
