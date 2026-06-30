@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

if exist "AxioraERP.exe" (
    "AxioraERP.exe" --stop
) else (
    if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
    python "launcher\gestix_launcher.py" --stop
)

endlocal
