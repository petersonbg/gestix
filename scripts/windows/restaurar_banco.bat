@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

if not exist "backups" mkdir "backups"
echo Informe o caminho do arquivo de backup .sql.
echo Exemplo: backups\gestix_20260101_120000.sql
set /p BACKUP_FILE="Arquivo: "

if not exist "%BACKUP_FILE%" (
    echo Arquivo de backup nao encontrado.
    pause
    exit /b 1
)

echo ATENCAO: a restauracao pode sobrescrever dados atuais.
set /p CONFIRMA="Digite RESTAURAR para confirmar: "
if /i not "%CONFIRMA%"=="RESTAURAR" (
    echo Operacao cancelada.
    pause
    exit /b 0
)

echo Garantindo que os containers estejam em execucao...
docker compose up -d db
if errorlevel 1 goto erro
timeout /t 8 /nobreak >nul

echo Restaurando backup...
type "%BACKUP_FILE%" | docker compose exec -T db sh -c "psql -U $POSTGRES_USER $POSTGRES_DB"
if errorlevel 1 goto erro

echo Backup restaurado com sucesso.
pause
exit /b 0

:erro
echo.
echo Nao foi possivel restaurar o backup. Verifique o Docker Desktop e o arquivo informado.
pause
exit /b 1
