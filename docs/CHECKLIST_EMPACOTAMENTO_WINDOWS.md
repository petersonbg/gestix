# Checklist de Empacotamento Windows do GESTIX

Use este checklist antes de entregar o instalador `GESTIX_Instalador.exe` a um cliente.

## Build

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| Dependencias Python instaladas | `pip install -r requirements.txt` conclui sem erro | Pendente |  |
| Staticfiles coletados | `python manage.py collectstatic --noinput` conclui sem erro | Pendente |  |
| Launcher gerado | `launcher\dist\GESTIX.exe` existe | Pendente |  |
| Instalador gerado | `installer\Output\GESTIX_Instalador.exe` existe | Pendente |  |
| Icone do aplicativo | `gestix.ico` aplicado quando disponivel | Pendente |  |

## Inicializacao

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| `config\.env` criado | Arquivo existe e contem `DEBUG=False`, `RUNNING_IN_DOCKER=False`, `SERVER_MODE=True` | Pendente |  |
| PostgreSQL ativo | `pg_isready` retorna conexao aceita | Pendente |  |
| Banco `gestix` existe | Usuario `gestix` conecta no banco `gestix` | Pendente |  |
| Migrations aplicadas | `python manage.py migrate --noinput` sem pendencias | Pendente |  |
| Launcher inicia Waitress | `GESTIX.exe` inicia sem abrir CMD | Pendente |  |
| Logs gerados | `logs\gestix_launcher.log` e `logs\gestix.log` recebem registros | Pendente |  |

## Acesso

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| Acesso local | `http://localhost:8000` abre o GESTIX | Pendente |  |
| IP detectado | `logs\launcher_diagnostico.txt` mostra `http://IP_DO_SERVIDOR:8000` | Pendente |  |
| Acesso em rede | Outro computador da rede acessa `http://IP_DO_SERVIDOR:8000` | Pendente |  |
| `ALLOWED_HOSTS` | Inclui `localhost`, `127.0.0.1` e IP do servidor | Pendente |  |
| `CSRF_TRUSTED_ORIGINS` | Inclui URLs locais e de rede com a porta usada | Pendente |  |

## Firewall

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| Regra porta 8000 | Regra `GESTIX - Rede Local` existe no perfil privado | Pendente |  |
| Criacao automatica | Launcher cria regra quando executado como administrador | Pendente |  |
| Sem permissao admin | Diagnostico registra alerta sem impedir acesso local | Pendente |  |

## Servico Windows

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| NSSM disponivel | `nssm.exe` esta no PATH ou em `tools\nssm\nssm.exe` | Pendente |  |
| Instalar servico | `scripts\windows\instalar_servico.bat` cria servico `GESTIX` | Pendente |  |
| Iniciar servico | `scripts\windows\iniciar_servico.bat` inicia o sistema | Pendente |  |
| Parar servico | `scripts\windows\parar_servico.bat` para o sistema | Pendente |  |
| Remover servico | `scripts\windows\remover_servico.bat` remove o servico | Pendente |  |
| Inicializacao com Windows | Servico configurado como automatico | Pendente |  |

## Funcionalidades Criticas

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| Login | Administrador acessa o sistema | Pendente |  |
| Permissoes | Perfis bloqueiam URLs e menus indevidos | Pendente |  |
| Backup | Backup gera arquivo em `backups\` | Pendente |  |
| Restauracao | Restauracao valida arquivo e registra historico | Pendente |  |
| Impressoes | Venda, orcamento e OS imprimem em formato homologado | Pendente |  |
| Logs de auditoria | Acoes importantes aparecem em Administracao -> Logs | Pendente |  |

## Pos-instalacao

| Item | Resultado esperado | Status | Observacoes |
| --- | --- | --- | --- |
| Diagnostico Windows | `python manage.py verificar_producao_windows` retorna sem ERRO | Pendente |  |
| Superusuario | Existe superusuario ativo | Pendente |  |
| Backup manual | `scripts\windows\backup_banco_sem_docker.bat` executa com sucesso | Pendente |  |
| Desinstalacao | Desinstalador remove atalhos e aplicacao sem apagar backup sem confirmacao externa | Pendente |  |

## Comandos de Build

```bat
build_launcher.bat
build_instalador.bat
```

Resultado esperado:

```text
launcher\dist\GESTIX.exe
installer\Output\GESTIX_Instalador.exe
```
