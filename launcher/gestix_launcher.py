import argparse
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from logging.handlers import RotatingFileHandler
from pathlib import Path

try:
    from tkinter import messagebox
except ImportError:
    messagebox = None

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gestix.network_discovery import (
    DISCOVERY_PORT,
    HOSTNAME,
    current_machine_name,
    current_mdns_hostname,
    discover_server,
    save_server,
    serve,
)

APP_NAME = 'AXIORA ERP'
DEFAULT_PORT = 8000
MAX_PORT_ATTEMPTS = 20
FIREWALL_RULE_NAME = 'AXIORA ERP - Rede Local'
DISCOVERY_FIREWALL_RULE_NAME = 'AXIORA ERP - Descoberta Local'
MDNS_FIREWALL_RULE_NAME = 'AXIORA ERP - mDNS'
PID_FILE_NAME = 'axiora_waitress.pid'
DISCOVERY_PID_FILE_NAME = 'axiora_discovery.pid'
APP_URL = 'http://localhost:8000'


def base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


INSTALL_DIR = base_dir()
LOG_DIR = INSTALL_DIR / 'logs'
BACKUP_DIR = INSTALL_DIR / 'backups'
MEDIA_DIR = INSTALL_DIR / 'media'
STATIC_DIR = INSTALL_DIR / 'staticfiles'
CONFIG_DIR = INSTALL_DIR / 'config'
PID_FILE = LOG_DIR / PID_FILE_NAME
DISCOVERY_PID_FILE = LOG_DIR / DISCOVERY_PID_FILE_NAME
DISCOVERED_SERVER_FILE = CONFIG_DIR / 'discovered_server.json'


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform.startswith('win') else 0


def ensure_directories():
    for path in (LOG_DIR, BACKUP_DIR, MEDIA_DIR, STATIC_DIR, CONFIG_DIR):
        path.mkdir(parents=True, exist_ok=True)


def setup_logging():
    ensure_directories()
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    for name, level in (('axiora_launcher.log', logging.INFO), ('axiora_launcher_errors.log', logging.ERROR)):
        handler = RotatingFileHandler(LOG_DIR / name, maxBytes=5 * 1024 * 1024, backupCount=5, encoding='utf-8')
        handler.setLevel(level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger


LOGGER = setup_logging()


def read_env_file(path):
    values = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def load_environment(port, ip_address):
    env = os.environ.copy()
    for env_file in (INSTALL_DIR / '.env', CONFIG_DIR / '.env'):
        env.update(read_env_file(env_file))

    env.setdefault('DEBUG', 'False')
    env.setdefault('SERVER_MODE', 'True')
    env.setdefault('RUNNING_IN_DOCKER', 'False')
    env.setdefault('SERVE_MEDIA_FILES', 'True')
    env.setdefault('BACKUP_ROOT', str(BACKUP_DIR))
    env.setdefault('LOG_DIR', str(LOG_DIR))

    hosts = split_csv(env.get('ALLOWED_HOSTS', ''))
    mdns_hostname = current_mdns_hostname()
    for host in ('localhost', '127.0.0.1', HOSTNAME, mdns_hostname, ip_address):
        if host and host not in hosts:
            hosts.append(host)
    env['ALLOWED_HOSTS'] = ','.join(hosts)

    origins = split_csv(env.get('CSRF_TRUSTED_ORIGINS', ''))
    for host in ('localhost', '127.0.0.1', HOSTNAME, mdns_hostname, ip_address):
        origin = f'http://{host}:{port}'
        if host and origin not in origins:
            origins.append(origin)
    env['CSRF_TRUSTED_ORIGINS'] = ','.join(origins)
    env['AXIORA_NETWORK_URL'] = f'http://{HOSTNAME}:{port}'
    env['AXIORA_MDNS_URL'] = f'http://{mdns_hostname}:{port}'
    env['AXIORA_NETWORK_IP_URL'] = f'http://{ip_address}:{port}'
    env['AXIORA_PORT'] = str(port)
    # Compatibilidade com instalações antigas que ainda leem GESTIX_*.
    env.setdefault('GESTIX_NETWORK_URL', env['AXIORA_NETWORK_URL'])
    env.setdefault('GESTIX_MDNS_URL', env['AXIORA_MDNS_URL'])
    env.setdefault('GESTIX_NETWORK_IP_URL', env['AXIORA_NETWORK_IP_URL'])
    env.setdefault('GESTIX_PORT', env['AXIORA_PORT'])
    return env


def split_csv(value):
    return [item.strip() for item in value.split(',') if item.strip()]


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('8.8.8.8', 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'


def port_is_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(1)
        return sock.connect_ex(('127.0.0.1', port)) != 0


def wait_for_http(url, timeout=45):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


def choose_port(preferred):
    for offset in range(MAX_PORT_ATTEMPTS):
        port = preferred + offset
        if port_is_free(port):
            return port
    raise RuntimeError(f'Nenhuma porta livre encontrada entre {preferred} e {preferred + MAX_PORT_ATTEMPTS - 1}.')


def find_python():
    candidates = [
        INSTALL_DIR / '.venv' / 'Scripts' / 'python.exe',
        INSTALL_DIR / 'venv' / 'Scripts' / 'python.exe',
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    if not getattr(sys, 'frozen', False):
        return sys.executable
    for executable in ('python.exe', 'python', 'py.exe', 'py'):
        found = shutil.which(executable)
        if found:
            return found
    raise RuntimeError('Python nao encontrado. Instale Python 3.12+ ou crie o ambiente .venv na pasta do AXIORA ERP.')


def find_waitress_command(python_exe):
    candidates = [
        INSTALL_DIR / '.venv' / 'Scripts' / 'waitress-serve.exe',
        INSTALL_DIR / 'venv' / 'Scripts' / 'waitress-serve.exe',
    ]
    for candidate in candidates:
        if candidate.exists():
            return [str(candidate)]
    found = shutil.which('waitress-serve')
    if found:
        return [found]
    return [python_exe, '-m', 'waitress']


def run(command, env, check_title):
    LOGGER.info('Executando: %s', ' '.join(map(str, command)))
    result = subprocess.run(
        command,
        cwd=INSTALL_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags(),
        check=False,
    )
    if result.stdout:
        LOGGER.info('%s stdout: %s', check_title, result.stdout.strip())
    if result.stderr:
        LOGGER.warning('%s stderr: %s', check_title, result.stderr.strip())
    if result.returncode != 0:
        raise RuntimeError(f'{check_title} falhou. Consulte logs/axiora_launcher_errors.log.')
    return result


def check_postgresql(env):
    pg_isready = shutil.which('pg_isready')
    if pg_isready:
        command = [
            pg_isready,
            '-h', env.get('DB_HOST') or env.get('POSTGRES_HOST') or 'localhost',
            '-p', env.get('DB_PORT') or env.get('POSTGRES_PORT') or '5432',
            '-d', env.get('DB_NAME') or env.get('POSTGRES_DB') or 'gestix',
            '-U', env.get('DB_USER') or env.get('POSTGRES_USER') or 'gestix',
        ]
        result = subprocess.run(command, env=env, capture_output=True, text=True, creationflags=creation_flags(), check=False)
        LOGGER.info('pg_isready: %s %s', result.stdout.strip(), result.stderr.strip())
        if result.returncode != 0:
            raise RuntimeError('PostgreSQL nao esta pronto. Verifique servico, banco, usuario e senha.')
    else:
        LOGGER.warning('pg_isready nao encontrado; validacao sera feita pelos comandos Django.')


def ensure_firewall_rule(name, protocol, port):
    if not sys.platform.startswith('win'):
        return True
    show = subprocess.run(
        ['netsh', 'advfirewall', 'firewall', 'show', 'rule', f'name={name}'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags(),
        check=False,
    )
    if show.returncode == 0 and str(port) in show.stdout and protocol.upper() in show.stdout.upper():
        LOGGER.info('Regra de firewall %s ja existe para %s/%s.', name, protocol, port)
        return True

    add = subprocess.run(
        [
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name={name}',
            'dir=in',
            'action=allow',
            f'protocol={protocol}',
            f'localport={port}',
            'profile=private',
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags(),
        check=False,
    )
    if add.returncode == 0:
        LOGGER.info('Regra de firewall criada: %s %s/%s.', name, protocol, port)
        return True
    LOGGER.warning('Nao foi possivel criar regra de firewall: %s %s', add.stdout.strip(), add.stderr.strip())
    return False


def verify_firewall(port):
    return {
        'http': ensure_firewall_rule(FIREWALL_RULE_NAME, 'TCP', port),
        'discovery': ensure_firewall_rule(DISCOVERY_FIREWALL_RULE_NAME, 'UDP', DISCOVERY_PORT),
        'mdns': ensure_firewall_rule(MDNS_FIREWALL_RULE_NAME, 'UDP', 5353),
    }


def write_diagnostic(port, ip_address, firewall_status):
    mdns_hostname = current_mdns_hostname()
    diagnostic = LOG_DIR / 'launcher_diagnostico.txt'
    diagnostic.write_text(
        '\n'.join(
            [
                'DIAGNOSTICO LAUNCHER AXIORA ERP',
                f'Pasta: {INSTALL_DIR}',
                f'Nome da maquina: {current_machine_name()}',
                f'Hostname: {HOSTNAME}',
                f'Hostname mDNS: {mdns_hostname}',
                f'IP atual: {ip_address}',
                f'Porta utilizada: {port}',
                f'URL local: http://localhost:{port}',
                f'URL recomendada: http://{HOSTNAME}:{port}',
                f'URL mDNS: http://{mdns_hostname}:{port}',
                f'URL rede: http://{ip_address}:{port}',
                f'Firewall TCP {port}: {"OK" if firewall_status["http"] else "ALERTA"}',
                f'Firewall UDP {DISCOVERY_PORT}: {"OK" if firewall_status["discovery"] else "ALERTA"}',
                f'Firewall mDNS UDP 5353: {"OK" if firewall_status["mdns"] else "ALERTA"}',
                f'PID file: {PID_FILE}',
                f'PID descoberta: {DISCOVERY_PID_FILE}',
                '',
            ]
        ),
        encoding='utf-8',
    )


def process_is_running(pid):
    if not pid:
        return False
    if sys.platform.startswith('win'):
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creation_flags(),
            check=False,
        )
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_pid_file(pid_file):
    if not pid_file.exists():
        return False
    try:
        pid = int(pid_file.read_text(encoding='utf-8').strip())
    except ValueError:
        pid_file.unlink(missing_ok=True)
        return False
    if not process_is_running(pid):
        pid_file.unlink(missing_ok=True)
        return False

    command = ['taskkill', '/PID', str(pid), '/T', '/F'] if sys.platform.startswith('win') else ['kill', str(pid)]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags(), check=False)
    LOGGER.info('Parada do processo %s retornou %s.', pid, result.returncode)
    pid_file.unlink(missing_ok=True)
    return result.returncode == 0


def stop_existing():
    discovery_stopped = stop_pid_file(DISCOVERY_PID_FILE)
    waitress_stopped = stop_pid_file(PID_FILE)
    if not discovery_stopped and not waitress_stopped:
        LOGGER.info('Nenhum processo do AXIORA ERP encontrado.')
    return discovery_stopped or waitress_stopped


def start_waitress(port, env):
    python_exe = find_python()
    waitress_command = find_waitress_command(python_exe)
    command = waitress_command + [f'--listen=0.0.0.0:{port}', 'gestix.wsgi:application']
    stdout = open(LOG_DIR / 'waitress_stdout.log', 'a', encoding='utf-8')
    stderr = open(LOG_DIR / 'waitress_stderr.log', 'a', encoding='utf-8')
    process = subprocess.Popen(
        command,
        cwd=INSTALL_DIR,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creation_flags(),
    )
    PID_FILE.write_text(str(process.pid), encoding='utf-8')
    LOGGER.info('Waitress iniciado na porta %s com PID %s.', port, process.pid)
    return process


def start_discovery_server(port, ip_address, env):
    stop_pid_file(DISCOVERY_PID_FILE)
    if getattr(sys, 'frozen', False):
        command = [
            sys.executable,
            '--discovery-server',
            '--ip',
            ip_address,
            '--port',
            str(port),
        ]
    else:
        command = [
            find_python(),
            '-m',
            'gestix.network_discovery',
            'serve',
            '--ip',
            ip_address,
            '--port',
            str(port),
        ]
    stdout = open(LOG_DIR / 'discovery_stdout.log', 'a', encoding='utf-8')
    stderr = open(LOG_DIR / 'discovery_stderr.log', 'a', encoding='utf-8')
    process = subprocess.Popen(
        command,
        cwd=INSTALL_DIR,
        env=env,
        stdout=stdout,
        stderr=stderr,
        creationflags=creation_flags(),
    )
    DISCOVERY_PID_FILE.write_text(str(process.pid), encoding='utf-8')
    time.sleep(0.5)
    if process.poll() is not None:
        DISCOVERY_PID_FILE.unlink(missing_ok=True)
        raise RuntimeError('O servico de descoberta nao iniciou. Consulte logs/discovery_stderr.log.')
    LOGGER.info('Descoberta local iniciada com PID %s.', process.pid)
    return process


def prepare_application(env):
    python_exe = find_python()
    check_postgresql(env)
    run([python_exe, 'manage.py', 'migrate', '--noinput'], env, 'Migrations')
    run([python_exe, 'manage.py', 'collectstatic', '--noinput'], env, 'Collectstatic')
    run([python_exe, 'manage.py', 'verificar_producao_windows', '--sem-cor'], env, 'Verificacao de producao')


def show_error(message):
    LOGGER.error(message)
    if messagebox is not None:
        try:
            messagebox.showerror(APP_NAME, message)
            return
        except Exception:
            LOGGER.warning('Interface grafica indisponivel.', exc_info=True)
    print(f'{APP_NAME}: {message}', file=sys.stderr)


def show_info(message):
    LOGGER.info(message.replace('\n', ' | '))
    if messagebox is not None:
        try:
            messagebox.showinfo(APP_NAME, message)
            return
        except Exception:
            LOGGER.warning('Interface grafica indisponivel.', exc_info=True)
    print(message)


def run_launcher(service=False, open_browser=True, preferred_port=DEFAULT_PORT):
    ensure_directories()
    ip_address = local_ip()
    port = choose_port(preferred_port)
    env = load_environment(port, ip_address)
    firewall_status = verify_firewall(port)
    write_diagnostic(port, ip_address, firewall_status)
    prepare_application(env)

    local_url = f'http://localhost:{port}'
    hostname_url = f'http://{HOSTNAME}:{port}'
    mdns_url = f'http://{current_mdns_hostname()}:{port}'
    network_url = f'http://{ip_address}:{port}'
    process = start_waitress(port, env)
    if not wait_for_http(local_url):
        raise RuntimeError('Waitress iniciou, mas o AXIORA ERP nao respondeu dentro do tempo esperado.')
    discovery_process = start_discovery_server(port, ip_address, env)

    if open_browser:
        webbrowser.open(local_url)
    if service:
        LOGGER.info('Launcher em modo servico. URL rede: %s', network_url)
        try:
            process.wait()
        finally:
            stop_pid_file(DISCOVERY_PID_FILE)
            PID_FILE.unlink(missing_ok=True)
    else:
        show_info(
            f'AXIORA ERP iniciado com sucesso.\n\n'
            f'Nome da maquina: {current_machine_name()}\n'
            f'Hostname: {HOSTNAME}\n'
            f'IP atual: {ip_address}\n\n'
            f'Neste servidor: {local_url}\n'
            f'Endereco de acesso na rede: {hostname_url}\n'
            f'Alternativa mDNS: {mdns_url}\n'
            f'Endereco alternativo: {network_url}\n\n'
            f'Diagnostico: logs\\launcher_diagnostico.txt'
        )
    if discovery_process.poll() is not None:
        raise RuntimeError('O servico de descoberta foi encerrado inesperadamente.')
    return 0


def run_client(open_browser=True):
    ensure_directories()
    server = discover_server()
    if not server:
        raise RuntimeError('Nenhum servidor AXIORA ERP foi encontrado na rede local.')
    save_server(server, DISCOVERED_SERVER_FILE)
    if open_browser:
        webbrowser.open(server.ip_url)
    show_info(
        f'Servidor AXIORA ERP encontrado.\n\n'
        f'Nome da maquina: {server.machine_name}\n'
        f'Hostname: {server.hostname}\n'
        f'IP atual: {server.ip}\n'
        f'Endereco: {server.ip_url}\n'
        f'Descoberta: {server.source.upper()}'
    )
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description='Launcher multiplataforma do AXIORA ERP.')
    parser.add_argument('--service', action='store_true', help='Executa sem interface e mantem o processo ativo.')
    parser.add_argument('--client', action='store_true', help='Localiza e abre um servidor AXIORA ERP da rede local.')
    parser.add_argument('--discovery-server', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--ip', help=argparse.SUPPRESS)
    parser.add_argument('--no-browser', action='store_true', help='Nao abre navegador apos iniciar.')
    parser.add_argument('--stop', action='store_true', help='Encerra o Waitress iniciado pelo launcher.')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help='Porta preferencial. Padrao: 8000.')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        if args.discovery_server:
            serve(args.ip or local_ip(), args.port)
            return 0
        if args.stop:
            stopped = stop_existing()
            if not args.service:
                show_info('AXIORA ERP encerrado.' if stopped else 'Nenhum processo do AXIORA ERP encontrado.')
            return 0
        if args.client:
            return run_client(open_browser=not args.no_browser)
        return run_launcher(service=args.service, open_browser=not args.no_browser and not args.service, preferred_port=args.port)
    except Exception as exc:
        LOGGER.exception('Falha no launcher.')
        if args.service:
            return 1
        show_error(str(exc))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
