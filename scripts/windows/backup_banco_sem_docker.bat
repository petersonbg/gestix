@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"

python manage.py gerar_backup
if errorlevel 1 (
    echo Nao foi possivel gerar o backup. Consulte logs\errors.log.
    pause
    exit /b 1
)

echo Backup gerado com sucesso.
pause

endlocal
