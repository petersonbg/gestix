@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%" || exit /b 1

if not exist "launcher\dist\GESTIX.exe" (
    echo GESTIX.exe nao encontrado. Gerando launcher primeiro...
    call "launcher\build_launcher.bat"
    if errorlevel 1 exit /b 1
)

set "ISCC_EXE="
where ISCC.exe >nul 2>&1 && set "ISCC_EXE=ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles%\Inno Setup 7\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 7\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if "%ISCC_EXE%"=="" if exist "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"

if "%ISCC_EXE%"=="" (
    echo Inno Setup Compiler ^(ISCC.exe^) nao encontrado no PATH.
    echo Instale o Inno Setup e tente novamente.
    pause
    exit /b 1
)

echo Gerando instalador GESTIX_Instalador.exe...
"%ISCC_EXE%" "installer\gestix_installer.iss"
if errorlevel 1 (
    echo Falha ao gerar o instalador.
    pause
    exit /b 1
)

echo Instalador gerado em installer\Output\GESTIX_Instalador.exe
pause

endlocal
