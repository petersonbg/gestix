@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

set "NSSM=%PROJECT_ROOT%\tools\nssm\nssm.exe"
if not exist "%NSSM%" set "NSSM=nssm"

"%NSSM%" stop GESTIX >nul 2>&1
"%NSSM%" remove GESTIX confirm
if errorlevel 1 (
    echo Nao foi possivel remover o servico GESTIX.
    pause
    exit /b 1
)

echo Servico GESTIX removido.
pause

endlocal
