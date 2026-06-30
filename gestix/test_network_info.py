from unittest import TestCase
from unittest.mock import patch

from gestix.network_info import get_network_info, required_hosts, server_port


class NetworkInfoTests(TestCase):
    def test_network_info_builds_browser_urls_from_hostname(self):
        with (
            patch('gestix.network_info.current_hostname', return_value='SERVIDOR'),
            patch('gestix.network_info.current_mdns_hostname', return_value='SERVIDOR.local'),
            patch('gestix.network_info.local_ip', return_value='192.168.1.20'),
            patch.dict('os.environ', {'AXIORA_PORT': '8012'}),
        ):
            info = get_network_info()

        self.assertEqual(info.recommended_url, 'http://SERVIDOR:8012')
        self.assertEqual(info.mdns_url, 'http://SERVIDOR.local:8012')
        self.assertEqual(info.ip, '192.168.1.20')

    def test_required_hosts_include_machine_and_local_alias(self):
        with (
            patch('gestix.network_info.current_hostname', return_value='SERVIDOR'),
            patch('gestix.network_info.current_mdns_hostname', return_value='SERVIDOR.local'),
        ):
            hosts = required_hosts()

        self.assertEqual(hosts, ['SERVIDOR', 'SERVIDOR.local', 'localhost', '127.0.0.1'])

    def test_invalid_port_uses_default(self):
        with patch.dict('os.environ', {'AXIORA_PORT': 'invalida'}):
            self.assertEqual(server_port(), 8000)
