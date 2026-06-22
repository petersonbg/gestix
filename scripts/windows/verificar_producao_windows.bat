@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

set "DJANGO_SETTINGS_MODULE=gestix.settings"

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

python manage.py verificar_producao_windows --sem-cor
if errorlevel 1 (
    echo Verificacao concluida com erros. Consulte logs\diagnostico.txt.
    pause
    exit /b 1
)

echo Verificacao concluida. Consulte logs\diagnostico.txt para detalhes.
pause

endlocal
