@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."
cd /d "%SCRIPT_DIR%" || exit /b 1

echo Verificando PyInstaller...
set "PYTHON_EXE="
if exist "%PROJECT_ROOT%\.venv\Scripts\python.exe" set "PYTHON_EXE=%PROJECT_ROOT%\.venv\Scripts\python.exe"
if "%PYTHON_EXE%"=="" where py >nul 2>&1 && set "PYTHON_EXE=py"
if "%PYTHON_EXE%"=="" where python >nul 2>&1 && set "PYTHON_EXE=python"

if "%PYTHON_EXE%"=="" (
    echo Python nao encontrado. Instale Python 3.12+ ou crie .venv na raiz do projeto.
    pause
    exit /b 1
)

"%PYTHON_EXE%" -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    "%PYTHON_EXE%" -m pip install pyinstaller
    if errorlevel 1 (
        echo Nao foi possivel instalar o PyInstaller.
        pause
        exit /b 1
    )
)

set "ICON_OPTION="
if exist "%SCRIPT_DIR%gestix.ico" (
    set "ICON_OPTION=--icon %SCRIPT_DIR%gestix.ico"
) else (
    if exist "%PROJECT_ROOT%\gestix.ico" set "ICON_OPTION=--icon %PROJECT_ROOT%\gestix.ico"
)

echo Gerando GESTIX.exe...
"%PYTHON_EXE%" -m PyInstaller --onefile --noconsole --paths "%PROJECT_ROOT%" --collect-all zeroconf --name GESTIX %ICON_OPTION% gestix_launcher.py
if errorlevel 1 (
    echo Falha ao gerar o executavel GESTIX.exe.
    pause
    exit /b 1
)

echo.
echo Executavel gerado em dist\GESTIX.exe
echo.
pause
