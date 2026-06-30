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

echo Iniciando AXIORA ERP com descoberta automatica em http://axiora.local:8000
python launcher\gestix_launcher.py --service

endlocal
