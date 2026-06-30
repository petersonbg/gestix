@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

set "NSSM=%PROJECT_ROOT%\tools\nssm\nssm.exe"
if not exist "%NSSM%" set "NSSM=nssm"

"%NSSM%" version >nul 2>&1
if errorlevel 1 (
    echo NSSM nao encontrado.
    echo Instale o NSSM no PATH ou coloque nssm.exe em tools\nssm\nssm.exe.
    pause
    exit /b 1
)

if not exist "AxioraERP.exe" (
    echo AxioraERP.exe nao encontrado na pasta do sistema.
    echo Gere o launcher com build_launcher.bat antes de instalar o servico.
    pause
    exit /b 1
)

"%NSSM%" install AxioraERP "%PROJECT_ROOT%\AxioraERP.exe" --service
"%NSSM%" set AxioraERP AppDirectory "%PROJECT_ROOT%"
"%NSSM%" set AxioraERP DisplayName "AXIORA ERP"
"%NSSM%" set AxioraERP Description "Sistema AXIORA ERP em Waitress para rede local"
"%NSSM%" set AxioraERP Start SERVICE_AUTO_START
"%NSSM%" set AxioraERP AppStdout "%PROJECT_ROOT%\logs\axiora_service_stdout.log"
"%NSSM%" set AxioraERP AppStderr "%PROJECT_ROOT%\logs\axiora_service_stderr.log"
"%NSSM%" set AxioraERP AppRotateFiles 1
"%NSSM%" set AxioraERP AppRotateOnline 1
"%NSSM%" set AxioraERP AppRotateBytes 5242880

echo Servico AXIORA ERP instalado.
pause

endlocal
