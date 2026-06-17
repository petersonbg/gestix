@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo ATENCAO: esta acao apagara todos os dados do banco local do GESTIX.
set /p CONFIRMA="Digite APAGAR para confirmar: "
if /i not "%CONFIRMA%"=="APAGAR" (
    echo Operacao cancelada.
    pause
    exit /b 0
)

echo Removendo containers e volume do banco...
docker compose down -v
if errorlevel 1 goto erro

echo Subindo containers novamente...
docker compose up -d
if errorlevel 1 goto erro

echo Aguardando inicializacao...
timeout /t 12 /nobreak >nul

echo Executando migrations...
docker compose exec web python manage.py migrate
if errorlevel 1 goto erro

echo.
echo Banco resetado com sucesso. Todos os dados anteriores foram apagados.
pause
exit /b 0

:erro
echo.
echo Nao foi possivel resetar o banco. Verifique se o Docker Desktop esta aberto.
pause
exit /b 1
