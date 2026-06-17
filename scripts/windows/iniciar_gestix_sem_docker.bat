@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

set "DJANGO_SETTINGS_MODULE=gestix.settings"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

if not exist "config\.env" (
    echo Arquivo config\.env nao encontrado.
    echo Copie config\.env.example para config\.env e ajuste as credenciais antes de iniciar.
    pause
    exit /b 1
)

if not exist "logs" mkdir "logs"
if not exist "backups" mkdir "backups"
if not exist "media" mkdir "media"
if not exist "staticfiles" mkdir "staticfiles"
if not exist "config" mkdir "config"

echo Aplicando migrations...
python manage.py migrate
if errorlevel 1 (
    echo Falha ao aplicar migrations. Verifique logs\errors.log.
    pause
    exit /b 1
)

echo Coletando arquivos estaticos...
python manage.py collectstatic --noinput
if errorlevel 1 (
    echo Falha ao coletar arquivos estaticos. Verifique logs\errors.log.
    pause
    exit /b 1
)

echo Verificando ambiente de producao Windows...
python manage.py verificar_producao_windows --sem-cor
if errorlevel 1 (
    echo A verificacao encontrou erros. Consulte logs\diagnostico.txt.
    pause
    exit /b 1
)

echo Iniciando GESTIX com Waitress em http://localhost:8000
echo Para acessar na rede local, use http://IP-DO-SERVIDOR:8000
waitress-serve --listen=0.0.0.0:8000 gestix.wsgi:application

endlocal
