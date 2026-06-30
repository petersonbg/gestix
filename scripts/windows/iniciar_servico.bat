@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

set "NSSM=%PROJECT_ROOT%\tools\nssm\nssm.exe"
if not exist "%NSSM%" set "NSSM=nssm"

"%NSSM%" start AxioraERP
if errorlevel 1 (
    echo Nao foi possivel iniciar o servico AXIORA ERP.
    pause
    exit /b 1
)

echo Servico AXIORA ERP iniciado.
pause

endlocal
