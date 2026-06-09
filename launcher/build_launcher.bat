@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b 1

echo Verificando PyInstaller...
py -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    py -m pip install pyinstaller
    if errorlevel 1 (
        echo Nao foi possivel instalar o PyInstaller.
        pause
        exit /b 1
    )
)

set "ICON_OPTION="
if exist "gestix.ico" set "ICON_OPTION=--icon gestix.ico"

echo Gerando GESTIX.exe...
pyinstaller --onefile --noconsole --name GESTIX %ICON_OPTION% gestix_launcher.py
if errorlevel 1 (
    echo Falha ao gerar o executavel GESTIX.exe.
    pause
    exit /b 1
)

echo.
echo Executavel gerado em dist\GESTIX.exe
echo.
pause
