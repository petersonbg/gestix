@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

cd /d "%PROJECT_ROOT%" || (
    echo Nao foi possivel acessar a pasta raiz do projeto GESTIX.
    pause
    exit /b 1
)

echo Verificando se o Docker Desktop esta em execucao...
docker info >nul 2>&1
if errorlevel 1 (
    echo.
    echo Docker Desktop nao parece estar aberto ou pronto para uso.
    echo Abra o Docker Desktop, aguarde ele iniciar completamente e execute este arquivo novamente.
    echo.
    pause
    exit /b 1
)

echo.
echo Iniciando o GESTIX com Docker Compose...
docker compose up -d
if errorlevel 1 (
    echo.
    echo Nao foi possivel iniciar o GESTIX. Verifique as mensagens acima e tente novamente.
    pause
    exit /b 1
)

echo.
echo Aguardando o servidor iniciar...
timeout /t 8 /nobreak >nul

echo Abrindo o GESTIX no navegador...
start "" "http://localhost:8000"

echo.
echo GESTIX iniciado com sucesso em http://localhost:8000
echo Outros dispositivos podem acessar http://IP-DO-SERVIDOR:8000
echo.
pause
