import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox

APP_URL = 'http://localhost:8000'
STARTUP_DELAY_SECONDS = 8


def base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0


def run_command(command, cwd):
    return subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags(),
        check=False,
    )


def show_error(message):
    messagebox.showerror('GESTIX', message)


def show_info(message):
    messagebox.showinfo('GESTIX', message)


def main():
    install_dir = base_dir()
    compose_file = install_dir / 'docker-compose.yml'
    if not compose_file.exists():
        show_error('Nao foi possivel encontrar o docker-compose.yml na pasta de instalacao do GESTIX.')
        return 1

    docker_check = run_command(['docker', 'info'], install_dir)
    if docker_check.returncode != 0:
        show_error(
            'O Docker Desktop nao parece estar aberto ou pronto para uso.\n\n'
            'Abra o Docker Desktop, aguarde a inicializacao completa e tente abrir o GESTIX novamente.'
        )
        return 1

    start_result = run_command(['docker', 'compose', 'up', '-d'], install_dir)
    if start_result.returncode != 0:
        show_error(
            'Nao foi possivel iniciar os servicos do GESTIX.\n\n'
            'Verifique se o Docker Desktop esta em execucao e tente novamente.'
        )
        return 1

    time.sleep(STARTUP_DELAY_SECONDS)
    webbrowser.open(APP_URL)
    show_info(f'GESTIX iniciado com sucesso.\n\nAcesse: {APP_URL}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
