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

if not exist "GESTIX.exe" (
    echo GESTIX.exe nao encontrado na pasta do sistema.
    echo Gere o launcher com build_launcher.bat antes de instalar o servico.
    pause
    exit /b 1
)

"%NSSM%" install GESTIX "%PROJECT_ROOT%\GESTIX.exe" --service
"%NSSM%" set GESTIX AppDirectory "%PROJECT_ROOT%"
"%NSSM%" set GESTIX DisplayName "GESTIX"
"%NSSM%" set GESTIX Description "Sistema GESTIX em Waitress para rede local"
"%NSSM%" set GESTIX Start SERVICE_AUTO_START
"%NSSM%" set GESTIX AppStdout "%PROJECT_ROOT%\logs\gestix_service_stdout.log"
"%NSSM%" set GESTIX AppStderr "%PROJECT_ROOT%\logs\gestix_service_stderr.log"
"%NSSM%" set GESTIX AppRotateFiles 1
"%NSSM%" set GESTIX AppRotateOnline 1
"%NSSM%" set GESTIX AppRotateBytes 5242880

echo Servico GESTIX instalado.
pause

endlocal
