"""Runtime network information shared by the launcher and Django views."""

import os
from dataclasses import dataclass

from .network_discovery import current_hostname, current_mdns_hostname, local_ip


DEFAULT_PORT = 8000


@dataclass(frozen=True)
class NetworkInfo:
    hostname: str
    mdns_hostname: str
    ip: str
    port: int

    @property
    def recommended_url(self):
        return f'http://{self.hostname}:{self.port}'

    @property
    def mdns_url(self):
        return f'http://{self.mdns_hostname}:{self.port}'

    @property
    def ip_url(self):
        return f'http://{self.ip}:{self.port}'


def server_port():
    raw_port = os.getenv('AXIORA_PORT') or os.getenv('GESTIX_PORT') or os.getenv('WEB_PORT') or DEFAULT_PORT
    try:
        port = int(raw_port)
    except (TypeError, ValueError):
        return DEFAULT_PORT
    return port if 1 <= port <= 65535 else DEFAULT_PORT


def get_network_info():
    return NetworkInfo(
        hostname=current_hostname(),
        mdns_hostname=current_mdns_hostname(),
        ip=local_ip(),
        port=server_port(),
    )


def required_hosts():
    info = get_network_info()
    return [info.hostname, info.mdns_hostname, 'localhost', '127.0.0.1']
