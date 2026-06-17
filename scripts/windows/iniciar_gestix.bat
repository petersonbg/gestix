@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo Verificando Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo Docker Desktop nao parece estar aberto ou pronto para uso.
    echo Abra o Docker Desktop, aguarde a inicializacao completa e tente novamente.
    pause
    exit /b 1
)

echo Iniciando o GESTIX...
docker compose up -d
if errorlevel 1 (
    echo Nao foi possivel iniciar o GESTIX. Verifique as mensagens acima.
    pause
    exit /b 1
)

timeout /t 8 /nobreak >nul
start "" "http://localhost:8000"
echo GESTIX iniciado em http://localhost:8000
echo Outros dispositivos podem acessar http://IP-DO-SERVIDOR:8000
pause
