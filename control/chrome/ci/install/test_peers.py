"""The proof's socket observation follows 18e's atomic listener publication.

Extract only the functions under test: importing proof.py itself is rightly
refused outside its GitHub container. No Chrome or service is started here.
"""
import ast
import os
from pathlib import Path
import shutil
import socket
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[4]
PROOF = ROOT / 'control/chrome/ci/install/proof.py'


def functions(path, names, namespace):
    tree = ast.parse(path.read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in nodes} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class Peers(unittest.TestCase):
    def peers(self):
        return functions(PROOF, ['service_peers'], {'subprocess': subprocess})['service_peers']

    def test_exact_server_endpoint_and_established_state_at_both_bind_names(self):
        rows = [
            'u_str ESTAB 0 0 /run/aresos-tools/.chrome.sock.new 10 * 11',
            'u_str ESTAB 0 0 /run/aresos-tools/chrome.sock 12 * 13',
            'u_str LISTEN 0 16 /run/aresos-tools/.chrome.sock.new 10 * 0',
            'u_str ESTAB 0 0 /run/aresos-tools/chrome.sock.other 14 * 15',
            'u_str ESTAB 0 0 /run/aresos-tools/.chrome.sock.new-other 16 * 17',
            'u_str ESTAB 0 0 * 11 /run/aresos-tools/.chrome.sock.new 10',
            'u_dgr ESTAB 0 0 /run/aresos-tools/.chrome.sock.new 18 * 19',
        ]
        peers = self.peers()
        with patch('subprocess.run', return_value=SimpleNamespace(stdout='\n'.join(rows))) as run:
            self.assertEqual(peers(), rows[:2])
            run.assert_called_once_with(['ss', '-x', '-a', '-n'], capture_output=True, text=True, check=True)
        with patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['ss'])):
            with self.assertRaises(subprocess.CalledProcessError):
                peers()

    @unittest.skipUnless(shutil.which('ss'), 'needs ss for the kernel observation')
    def test_real_renamed_listener_zero_one_two_and_disconnected_peers(self):
        scratch = ROOT / '.work/18c-b-chrome'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as directory:
            folder = Path(directory)
            daemon = functions(ROOT / 'control/aresos_control/daemon.py', ['replaceable', 'listen'],
                               {'os': os, 'stat': stat, 'socket': socket, 'SOCKET_MODES': {'chrome': 0o666}})
            peers = self.peers()
            with daemon['listen'](folder, 'chrome') as listener:
                self.assertEqual(listener.getsockname(), str(folder / '.chrome.sock.new'))
                self.assertTrue((folder / 'chrome.sock').is_socket())
                self.assertFalse((folder / '.chrome.sock.new').exists())
                self.assertEqual(peers(folder), [])
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as first:
                    first.connect(str(folder / 'chrome.sock'))
                    accepted, _ = listener.accept()
                    with accepted:
                        self.assertEqual(len(peers(folder)), 1)
                        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as second:
                            second.connect(str(folder / 'chrome.sock'))
                            another, _ = listener.accept()
                            with another:
                                self.assertEqual(len(peers(folder)), 2)
                self.assertEqual(peers(folder), [])

    def test_an_unasked_ordinary_extension_case_is_a_failure(self):
        class Failure(Exception):
            pass

        class CdpError(Exception):
            pass

        ordinary = functions(PROOF, ['case_ordinary'], {
            'Failure': Failure, 'cdp': SimpleNamespace(Error=CdpError), 'log': lambda *args: None,
            'LOADING': '--enable-unsafe-extension-debugging', 'ORDINARY': Path('/synthetic'),
        })['case_ordinary']
        for error in (CdpError('cannot load'), Failure('page not found'), KeyError('id')):
            p = Mock()
            p.bundles = {'a': {'id': 'a' * 32}}
            p.extensions_page.side_effect = error
            with self.assertRaisesRegex(Failure, 'must allow the hand-loaded extension to be asked'):
                ordinary(p)


if __name__ == '__main__':
    unittest.main()
