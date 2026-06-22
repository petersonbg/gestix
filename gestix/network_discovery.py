"""Local-network discovery for GESTIX servers."""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import secrets
import signal
import socket
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    from zeroconf import IPVersion, ServiceInfo, Zeroconf
except ImportError:  # pragma: no cover - handled with a clear runtime error
    IPVersion = ServiceInfo = Zeroconf = None


SERVICE_TYPE = '_gestix._tcp.local.'
SERVICE_NAME = f'GESTIX.{SERVICE_TYPE}'
DISCOVERY_PORT = 37020
PROTOCOL_VERSION = 1
QUERY_KIND = 'gestix-discover'
RESPONSE_KIND = 'gestix-server'
DEFAULT_CACHE_PATH = Path('config') / 'discovered_server.json'
LOGGER = logging.getLogger('GESTIX.discovery')


@dataclass(frozen=True)
class ServerAddress:
    hostname: str
    machine_name: str
    ip: str
    port: int
    source: str
    discovered_at: float

    @property
    def url(self):
        return f'http://{self.hostname}:{self.port}'

    @property
    def ip_url(self):
        return f'http://{self.ip}:{self.port}'


def current_machine_name():
    return platform.node() or socket.gethostname() or 'GESTIX'


def current_hostname():
    return current_machine_name().split('.', 1)[0].strip() or 'GESTIX'


def current_mdns_hostname():
    return f'{current_hostname()}.local'


HOSTNAME = current_hostname()


def local_ip():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(('192.0.2.1', 9))
            address = sock.getsockname()[0]
            if address and not address.startswith('127.'):
                return address
    except OSError:
        pass

    try:
        for item in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            address = item[4][0]
            if address and not address.startswith(('127.', '169.254.')):
                return address
    except OSError:
        pass
    return '127.0.0.1'


def _encode(payload):
    return json.dumps(payload, separators=(',', ':'), sort_keys=True).encode('utf-8')


def _decode(data):
    try:
        payload = json.loads(data.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def make_query(nonce=None):
    return {
        'kind': QUERY_KIND,
        'version': PROTOCOL_VERSION,
        'nonce': nonce or secrets.token_hex(12),
    }


def make_response(query, ip, port, machine_name=None):
    hostname = current_hostname()
    return {
        'kind': RESPONSE_KIND,
        'version': PROTOCOL_VERSION,
        'nonce': query['nonce'],
        'hostname': hostname,
        'mdns_hostname': f'{hostname}.local',
        'machine_name': machine_name or current_machine_name(),
        'ip': ip,
        'port': int(port),
    }


def _valid_query(payload):
    return (
        payload
        and payload.get('kind') == QUERY_KIND
        and payload.get('version') == PROTOCOL_VERSION
        and isinstance(payload.get('nonce'), str)
        and bool(payload['nonce'])
    )


def _server_from_response(payload, nonce, sender_ip):
    if not payload or payload.get('kind') != RESPONSE_KIND:
        return None
    if payload.get('version') != PROTOCOL_VERSION or payload.get('nonce') != nonce:
        return None
    try:
        port = int(payload['port'])
    except (KeyError, TypeError, ValueError):
        return None
    if not 1 <= port <= 65535:
        return None
    return ServerAddress(
        hostname=str(payload.get('hostname') or HOSTNAME).rstrip('.'),
        machine_name=str(payload.get('machine_name') or 'GESTIX'),
        ip=sender_ip,
        port=port,
        source='udp',
        discovered_at=time.time(),
    )


class UdpDiscoveryResponder:
    def __init__(self, ip, http_port, discovery_port=DISCOVERY_PORT):
        self.ip = ip
        self.http_port = int(http_port)
        self.discovery_port = int(discovery_port)
        self._stop_event = threading.Event()
        self._socket = None

    def serve_forever(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            self._socket = sock
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(('', self.discovery_port))
            sock.settimeout(0.5)
            LOGGER.info('Fallback UDP ativo na porta %s.', self.discovery_port)
            while not self._stop_event.is_set():
                try:
                    data, sender = sock.recvfrom(4096)
                except socket.timeout:
                    continue
                except OSError:
                    break
                query = _decode(data)
                if not _valid_query(query):
                    continue
                response = make_response(query, self.ip, self.http_port)
                try:
                    sock.sendto(_encode(response), sender)
                except OSError:
                    LOGGER.exception('Falha ao responder descoberta UDP para %s.', sender)

    def stop(self):
        self._stop_event.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass


class MdnsAdvertisement:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = int(port)
        self.zeroconf = None
        self.info = None

    def start(self):
        if Zeroconf is None:
            raise RuntimeError('A dependencia zeroconf nao esta instalada.')
        mdns_hostname = current_mdns_hostname()
        self.zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
        self.info = ServiceInfo(
            SERVICE_TYPE,
            SERVICE_NAME,
            addresses=[socket.inet_aton(self.ip)],
            port=self.port,
            properties={
                b'app': b'GESTIX',
                b'version': str(PROTOCOL_VERSION).encode('ascii'),
                b'machine': current_machine_name().encode('utf-8'),
            },
            server=f'{mdns_hostname}.',
        )
        self.zeroconf.register_service(self.info, allow_name_change=False)
        LOGGER.info('mDNS ativo: %s -> %s:%s.', mdns_hostname, self.ip, self.port)

    def stop(self):
        if self.zeroconf is None:
            return
        try:
            if self.info is not None:
                self.zeroconf.unregister_service(self.info)
        finally:
            self.zeroconf.close()
            self.zeroconf = None


def discover_mdns(timeout=2.5):
    if Zeroconf is None:
        LOGGER.warning('mDNS indisponivel: dependencia zeroconf nao instalada.')
        return None
    zeroconf = Zeroconf(ip_version=IPVersion.V4Only)
    try:
        info = zeroconf.get_service_info(
            SERVICE_TYPE,
            SERVICE_NAME,
            timeout=max(1, int(timeout * 1000)),
        )
        if not info or not info.addresses:
            return None
        addresses = info.parsed_scoped_addresses(IPVersion.V4Only)
        if not addresses:
            return None
        machine = info.properties.get(b'machine', b'GESTIX').decode('utf-8', errors='replace')
        return ServerAddress(
            hostname=machine,
            machine_name=machine,
            ip=addresses[0],
            port=info.port,
            source='mdns',
            discovered_at=time.time(),
        )
    finally:
        zeroconf.close()


def discover_udp(timeout=3.0, discovery_port=DISCOVERY_PORT):
    query = make_query()
    payload = _encode(query)
    deadline = time.monotonic() + timeout
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(('', 0))
        sock.settimeout(min(0.5, timeout))
        for target in ('255.255.255.255', '<broadcast>'):
            try:
                sock.sendto(payload, (target, discovery_port))
            except OSError:
                LOGGER.debug('Broadcast indisponivel em %s.', target, exc_info=True)
        while time.monotonic() < deadline:
            try:
                data, sender = sock.recvfrom(4096)
            except socket.timeout:
                continue
            server = _server_from_response(_decode(data), query['nonce'], sender[0])
            if server:
                return server
    return None


def discover_server(mdns_timeout=2.5, udp_timeout=3.0):
    server = discover_mdns(timeout=mdns_timeout)
    return server or discover_udp(timeout=udp_timeout)


def save_server(server, path=DEFAULT_CACHE_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f'{path.suffix}.tmp')
    temporary.write_text(json.dumps(asdict(server), indent=2), encoding='utf-8')
    os.replace(temporary, path)
    return path


def load_saved_server(path=DEFAULT_CACHE_PATH):
    path = Path(path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        return ServerAddress(
            hostname=str(payload['hostname']),
            machine_name=str(payload['machine_name']),
            ip=str(payload['ip']),
            port=int(payload['port']),
            source=str(payload.get('source') or 'cache'),
            discovered_at=float(payload['discovered_at']),
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        LOGGER.warning('Cache de descoberta invalido em %s.', path)
        return None


def serve(ip, port, discovery_port=DISCOVERY_PORT):
    advertisement = MdnsAdvertisement(ip, port)
    responder = UdpDiscoveryResponder(ip, port, discovery_port)
    responder_thread = threading.Thread(target=responder.serve_forever, name='gestix-udp', daemon=True)
    stop_event = threading.Event()

    def request_stop(_signum=None, _frame=None):
        stop_event.set()

    signal.signal(signal.SIGINT, request_stop)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, request_stop)

    advertisement.start()
    responder_thread.start()
    try:
        while not stop_event.wait(1):
            pass
    finally:
        responder.stop()
        advertisement.stop()
        responder_thread.join(timeout=2)


def parse_args():
    parser = argparse.ArgumentParser(description='Descoberta local do servidor GESTIX.')
    subparsers = parser.add_subparsers(dest='command', required=True)

    server = subparsers.add_parser('serve', help='Anuncia este servidor na rede local.')
    server.add_argument('--ip', default=local_ip())
    server.add_argument('--port', type=int, required=True)
    server.add_argument('--discovery-port', type=int, default=DISCOVERY_PORT)

    client = subparsers.add_parser('discover', help='Localiza um servidor GESTIX.')
    client.add_argument('--cache', type=Path, default=DEFAULT_CACHE_PATH)
    return parser.parse_args()


def main():
    logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    args = parse_args()
    if args.command == 'serve':
        serve(args.ip, args.port, args.discovery_port)
        return 0

    server = discover_server()
    if not server:
        LOGGER.error('Nenhum servidor GESTIX foi encontrado na rede local.')
        return 1
    save_server(server, args.cache)
    print(server.ip_url)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
