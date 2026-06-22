import socket
import tempfile
import threading
import time
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from gestix.network_discovery import (
    HOSTNAME,
    ServerAddress,
    UdpDiscoveryResponder,
    _decode,
    _encode,
    _server_from_response,
    discover_server,
    current_hostname,
    current_mdns_hostname,
    load_saved_server,
    make_query,
    save_server,
)


class NetworkDiscoveryTests(TestCase):
    def test_hostnames_are_derived_from_machine_name(self):
        with patch('gestix.network_discovery.current_machine_name', return_value='SERVIDOR-LOJA.exemplo'):
            self.assertEqual(current_hostname(), 'SERVIDOR-LOJA')
            self.assertEqual(current_mdns_hostname(), 'SERVIDOR-LOJA.local')

    def test_udp_responder_answers_valid_query(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.bind(('127.0.0.1', 0))
            discovery_port = probe.getsockname()[1]

        responder = UdpDiscoveryResponder('192.168.1.25', 8000, discovery_port)
        thread = threading.Thread(target=responder.serve_forever, daemon=True)
        thread.start()
        time.sleep(0.05)

        query = make_query('test-nonce')
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(2)
                client.sendto(_encode(query), ('127.0.0.1', discovery_port))
                data, sender = client.recvfrom(4096)
            server = _server_from_response(_decode(data), query['nonce'], sender[0])
        finally:
            responder.stop()
            thread.join(timeout=2)

        self.assertIsNotNone(server)
        self.assertEqual(server.hostname, HOSTNAME)
        self.assertEqual(server.port, 8000)
        self.assertEqual(server.source, 'udp')

    def test_discovery_uses_udp_when_mdns_fails(self):
        udp_server = ServerAddress(HOSTNAME, 'SERVIDOR', '10.0.0.8', 8000, 'udp', time.time())

        with (
            patch('gestix.network_discovery.discover_mdns', return_value=None) as mdns,
            patch('gestix.network_discovery.discover_udp', return_value=udp_server) as udp,
        ):
            found = discover_server()

        self.assertEqual(found, udp_server)
        mdns.assert_called_once()
        udp.assert_called_once()

    def test_discovery_stops_after_mdns_success(self):
        mdns_server = ServerAddress(HOSTNAME, 'SERVIDOR', '10.0.0.9', 8000, 'mdns', time.time())

        with (
            patch('gestix.network_discovery.discover_mdns', return_value=mdns_server),
            patch('gestix.network_discovery.discover_udp') as udp,
        ):
            found = discover_server()

        self.assertEqual(found, mdns_server)
        udp.assert_not_called()

    def test_server_address_is_saved_and_loaded(self):
        server = ServerAddress(HOSTNAME, 'SERVIDOR', '192.168.0.15', 8010, 'mdns', time.time())
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'server.json'
            save_server(server, cache)
            loaded = load_saved_server(cache)

        self.assertEqual(loaded, server)
        self.assertEqual(loaded.ip_url, 'http://192.168.0.15:8010')
