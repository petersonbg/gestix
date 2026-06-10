@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."

cd /d "%PROJECT_ROOT%" || (
    echo Nao foi possivel acessar a pasta raiz do projeto GESTIX.
    pause
    exit /b 1
)

echo Encerrando o GESTIX com Docker Compose...
docker compose down
if errorlevel 1 (
    echo.
    echo Nao foi possivel encerrar o GESTIX. Verifique se o Docker Desktop esta aberto e tente novamente.
    pause
    exit /b 1
)

echo.
echo Sistema GESTIX encerrado com sucesso.
echo.
pause
