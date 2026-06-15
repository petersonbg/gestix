@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

if not exist "backups" mkdir "backups"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set "STAMP=%%i"
set "BACKUP_FILE=backups\gestix_%STAMP%.sql"

echo Gerando backup em %BACKUP_FILE%...
docker compose exec -T db sh -c "pg_dump -U $POSTGRES_USER $POSTGRES_DB" > "%BACKUP_FILE%"
if errorlevel 1 (
    echo Nao foi possivel gerar o backup. Verifique se os containers estao em execucao.
    if exist "%BACKUP_FILE%" del "%BACKUP_FILE%"
    pause
    exit /b 1
)

echo Backup criado com sucesso: %BACKUP_FILE%
pause
