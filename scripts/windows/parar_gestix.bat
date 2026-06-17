<<<<<<< HEAD
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo Parando o GESTIX...
docker compose down
if errorlevel 1 (
    echo Nao foi possivel parar o GESTIX. Verifique se o Docker Desktop esta aberto.
    pause
    exit /b 1
)

echo Containers do GESTIX encerrados.
pause
=======
@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\.."
cd /d "%PROJECT_ROOT%" || exit /b 1

echo Parando o GESTIX...
docker compose down
if errorlevel 1 (
    echo Nao foi possivel parar o GESTIX. Verifique se o Docker Desktop esta aberto.
    pause
    exit /b 1
)

echo Containers do GESTIX encerrados.
pause
>>>>>>> 027f04bc6b4f2b33d16a13e0d7c9548c220798f7
