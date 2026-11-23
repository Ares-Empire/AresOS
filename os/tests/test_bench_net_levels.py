import http.client
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
BENCH = ROOT / 'os/ci/bench'
sys.path.insert(0, str(BENCH))
from fake_net import NAMESPACE_ENV, REPLY, Stubs, listening, offline_namespace
from network import HOST, STUB_PORT, Level, level, offline_desk_command, qemu_nic, require_loopback
from script import parse


def isolated_desk_probe(outside_port, folder):
    require_loopback()
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    assert os.getuid() != 0 and status['NoNewPrivs'].strip() == '1'
    assert all(int(status[key].strip(), 16) == 0 for key in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb'))
    stub = Stubs(folder, STUB_PORT)
    context = ssl.create_default_context(cafile=stub.ca)

    def fetch(path, tls=context):
        with socket.create_connection(('127.0.0.1', stub.port), timeout=2) as connection:
            with tls.wrap_socket(connection, server_hostname=HOST) as wrapped:
                wrapped.sendall(f'GET {path} HTTP/1.0\r\nHost: {HOST}\r\n\r\n'.encode())
                with http.client.HTTPResponse(wrapped) as response:
                    response.begin()
                    return response.status, response.read()

    try:
        stub.up()
        assert fetch('/') == (200, REPLY)
        curl = subprocess.run(['curl', '--disable', '--noproxy', '*', '--silent', '--fail', '--max-time', '3',
                               '--cacert', stub.ca, '--resolve', f'{HOST}:{stub.port}:127.0.0.1',
                               f'https://{HOST}:{stub.port}/'], capture_output=True, check=True, timeout=5)
        assert curl.stdout == REPLY
        assert fetch('/wrong') == (503, b'wrong fixture\n')
        assert fetch('/slow') == (200, REPLY)
        try:
            fetch('/', ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT))
        except ssl.SSLCertVerificationError:
            pass
        else:
            raise AssertionError('Fixture certificate was trusted without its CA')
        stub.down()
        for port in (stub.port, outside_port):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=1):
                    raise AssertionError('Unexpected listener response')
            except ConnectionRefusedError:
                pass
        stub.up()
        assert fetch('/') == (200, REPLY)
    finally:
        stub.down()


class BenchNetworkLevelsTest(unittest.TestCase):
    def test_level_and_net_steps(self):
        self.assertEqual(parse(b'{"steps":[{"kind":"status"}]}'), (Level.NONE, [{'kind': 'status'}]))
        for value in Level:
            self.assertIs(level(value.value), value)
            chosen, _ = parse(json.dumps({'network': value, 'steps': [{'kind': 'status'}]}).encode())
            self.assertEqual(chosen, value)
        for value in (None, True, ['fake'], {}, 'bridge', 'FAKE'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                level(value)
        self.assertEqual(parse((ROOT / 'reviews/334c-bench-network/bench/fake-network.json').read_bytes())[0], Level.FAKE)
        for value, state in (('none', 'up'), ('internet', 'down'), ('fake', None), ('fake', 'toggle')):
            with self.subTest(value=value, state=state), self.assertRaises(ValueError):
                parse(json.dumps({'network': value, 'steps': [{'kind': 'net', 'state': state}]}).encode())

    def test_offline_launch_options_and_guest_nic(self):
        image = 'sha256:' + 'a' * 64
        for network in (Level.NONE, Level.FAKE):
            argv = offline_desk_command(network, image, ['/usr/bin/python3', '-I'])
            self.assertIn('--network=none', argv)
            self.assertIn('--pull=never', argv)
            self.assertIn('--dns=none', argv)
            self.assertIn('--hosts-file=none', argv)
            self.assertIn('--cap-drop=all', argv)
            self.assertIn('65534:65534', argv)
            self.assertIn('--http-proxy=false', argv)
            self.assertIn('--read-only', argv)
            self.assertEqual('--add-host' in argv, network == Level.FAKE)
            self.assertFalse(any(arg.startswith(('--publish', '--volume', '--device', '--privileged')) for arg in argv))
        with self.assertRaises(ValueError):
            offline_desk_command(Level.INTERNET, image, ['/usr/bin/true'])
        with self.assertRaises(ValueError):
            offline_desk_command(Level.FAKE, '--network=host', ['/usr/bin/true'])
        self.assertEqual(qemu_nic(Level.NONE), ['-nic', 'none'])
        self.assertEqual(qemu_nic(Level.FAKE), ['-nic', 'user,model=virtio-net-pci,id=bench-nic,ipv6=off,ipv4=on'])

    def test_loopback_check_refuses_an_extra_interface(self):
        with patch('network.if_nameindex', return_value=[(1, 'lo'), (2, 'eth0')]):
            with self.assertRaises(ValueError):
                require_loopback()

    def test_loopback_stub_and_outside_listener(self):
        with listening() as outside, tempfile.TemporaryDirectory(dir=ROOT) as folder:
            with socket.create_connection(('127.0.0.1', outside.server_port), timeout=2) as positive:
                positive.sendall(b'GET / HTTP/1.0\r\n\r\n')
                with http.client.HTTPResponse(positive) as response:
                    response.begin()
                    self.assertEqual((response.status, response.read()), (200, REPLY))
            command = offline_namespace([sys.executable, '-B', __file__, str(outside.server_port), folder])
            result = subprocess.run(command, env=NAMESPACE_ENV, timeout=25, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(outside.connections, 1)


if __name__ == '__main__':
    isolated_desk_probe(int(sys.argv[1]), Path(sys.argv[2]))
