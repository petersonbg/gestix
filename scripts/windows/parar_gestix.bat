@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo Parando o AXIORA ERP...
docker compose down
if errorlevel 1 (
    echo Nao foi possivel parar o AXIORA ERP. Verifique se o Docker Desktop esta aberto.
    pause
    exit /b 1
)

echo Containers do AXIORA ERP encerrados.
pause
