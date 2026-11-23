import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
from egress import ENDPOINTS, ENTRIES, PASTA, SETTINGS, Policy, code_version, record_matches, record_pass
from fake_net import NAMESPACE_ENV
from laptop import Busy
from laptop_cli import Bench
from network import require_loopback
from store import GB, DiskSpace, Store

KEY = b'\x01' * 32
VERSION = 'a' * 64
FACTS = dict(addresses=['192.0.2.2', '2001:db8::1'], routes=['198.51.100.0/24', '44.0.0.0/24', '2001:db8::/64'],
             reflected=['45.0.0.9'], resolver='46.0.0.53', identity=b'synthetic link')
BLOCKED = ('192.0.2.2', '44.0.0.8', '45.0.0.9')
ALLOWED = '46.0.0.8'


def policy(**changes):
    return Policy.build(**(FACTS | changes))


def proof():
    return {entry: dict.fromkeys(ENDPOINTS + SETTINGS, True) for entry in ENTRIES}


def policy_fixture():
    require_loopback()
    # Create both ends in private namespaces. Neither namespace has a link to the host.
    command = ['unshare', '--net', '--', sys.executable, '-B', __file__, '--listen']
    with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True) as peer:
        try:
            assert peer.stdout.readline() == 'ready\n'
            ip('link', 'add', 'bench-edge', 'type', 'veth', 'peer', 'name', 'bench-peer', 'netns', str(peer.pid))
            ip('address', 'add', '100.64.0.1/30', 'dev', 'bench-edge')
            ip('link', 'set', 'bench-edge', 'up')
            ip('route', 'add', 'default', 'via', '100.64.0.2')
            peer.stdin.write('configure\n')
            peer.stdin.flush()
            ports = json.loads(peer.stdout.readline())
            for address, port in zip((*BLOCKED, ALLOWED), ports, strict=True):
                with socket.create_connection((address, port), timeout=1):
                    pass
            peer.stdin.write('baseline\n')
            peer.stdin.flush()
            assert peer.stdout.readline() == 'listening\n'
            subprocess.run(['nft', '-f', '-'], input=policy().rules(), text=True, check=True)
            subprocess.run(['setpriv', '--no-new-privs', '--inh-caps=-all', '--ambient-caps=-all',
                            '--bounding-set=-all', '--', sys.executable, '-B', __file__, '--probe',
                            *map(str, ports)], check=True, timeout=8)
            peer.stdin.write('verify\n')
            peer.stdin.flush()
            assert peer.wait(timeout=3) == 0
        finally:
            if peer.poll() is None:
                peer.terminate()


def ip(*args):
    subprocess.run(['ip', *args], check=True, timeout=3)


def listeners():
    require_loopback()
    print('ready', flush=True)
    assert input() == 'configure'
    ip('link', 'set', 'lo', 'up')
    ip('address', 'add', '100.64.0.2/30', 'dev', 'bench-peer')
    ip('link', 'set', 'bench-peer', 'up')
    sockets = []
    try:
        for address in (*BLOCKED, ALLOWED):
            ip('address', 'add', f'{address}/32', 'dev', 'lo')
            listener = socket.socket()
            sockets.append(listener)
            listener.bind((address, 0))
            listener.listen(1)
            listener.settimeout(1)
        print(json.dumps([listener.getsockname()[1] for listener in sockets]), flush=True)
        assert input() == 'baseline'
        for listener in sockets:
            listener.accept()[0].close()
        print('listening', flush=True)
        assert input() == 'verify'
        for listener in sockets[:-1]:
            listener.setblocking(False)
            try:
                connection, _ = listener.accept()
            except BlockingIOError:
                continue
            connection.close()
            raise AssertionError('Blocked fixture listener received a connection')
        sockets[-1].settimeout(1)
        sockets[-1].accept()[0].close()
    finally:
        for listener in sockets:
            listener.close()


def policy_probe(ports):
    assert os.getuid() != 0
    status = dict(line.split(':', 1) for line in Path('/proc/self/status').read_text().splitlines())
    assert all(int(status[key].strip(), 16) == 0 for key in ('CapEff', 'CapPrm', 'CapInh', 'CapBnd', 'CapAmb'))
    for address, port in zip((*BLOCKED, ALLOWED), map(int, ports), strict=True):
        try:
            with socket.create_connection((address, port), timeout=0.5):
                assert address == ALLOWED
        except TimeoutError:
            assert address != ALLOWED


class BenchEgressTest(unittest.TestCase):
    def test_policy_is_outbound_only_and_blocks_public_home_routes(self):
        rules = policy().rules()
        for item in ('192.0.2.0/24', '198.51.100.0/24', '44.0.0.0/24', '45.0.0.9/32', '100.64.0.0/10'):
            self.assertIn(item, rules)
        self.assertIn('meta nfproto ipv4 ct state established,related accept', rules)
        self.assertEqual(rules.count('policy drop;'), 3)
        self.assertLess(rules.index('ip daddr @denied drop'), rules.index('46.0.0.53'))
        self.assertLess(rules.index('th dport 53 drop'), rules.index('meta nfproto ipv4 meta l4proto'))
        self.assertIn('--no-map-gw', PASTA)
        for flag in ('-t', '-u', '-T', '-U'):
            self.assertEqual(PASTA[PASTA.index(flag) + 1], 'none')

    def test_missing_observations_and_contradictions_fail_closed(self):
        for changes in ({'addresses': []}, {'routes': []}, {'reflected': []}, {'identity': b''},
                        {'routes': ['0.0.0.0/0']}, {'reflected': ['127.0.0.1']},
                        {'resolver': '192.0.2.2'}, {'routes': ['sensitive-invalid-value']}):
            with self.subTest(changes=changes), self.assertRaisesRegex(
                    Busy, '^laptop egress topology cannot be verified$'):
                policy(**changes)

    def test_each_laptop_entry_is_refused_before_preparation(self):
        bench = Bench(Mock(), Mock())
        for entry in ENTRIES:
            with self.subTest(entry=entry), self.assertRaisesRegex(Busy, 'hosted only'):
                bench.run(entry, {}, Mock(), network='internet')
        bench.store.phase.assert_not_called()
        bench.inputs.require.assert_not_called()

    def test_pass_requires_every_endpoint_and_setting_on_each_entry(self):
        for entry in ENTRIES:
            for name in ENDPOINTS + SETTINGS:
                facts = proof()
                facts[entry][name] = False
                with self.subTest(entry=entry, fact=name), self.assertRaises(Busy):
                    record_pass(KEY, VERSION, policy(), facts)
        facts = proof()
        del facts['exec']
        with self.assertRaises(Busy):
            record_pass(KEY, VERSION, policy(), facts)

    def test_record_binds_version_and_network_without_storing_observations(self):
        good = record_pass(KEY, VERSION, policy(), proof())
        decoded = json.loads(good)
        self.assertEqual(set(decoded), {'schema', 'version', 'binding'})
        for observation in ('192.0.2.2', '44.0.0.0', '45.0.0.9', 'synthetic link', '46.0.0.53'):
            self.assertNotIn(observation.encode(), good)
        self.assertTrue(record_matches(good, KEY, VERSION, policy()))
        self.assertTrue(record_matches(good, KEY, VERSION, policy(addresses=FACTS['addresses'][::-1])))
        self.assertFalse(record_matches(good, KEY, 'b' * 64, policy()))
        self.assertFalse(record_matches(good, b'\x02' * 32, VERSION, policy()))
        for changes in ({'addresses': ['192.0.2.3']}, {'routes': ['192.0.2.0/25']},
                        {'reflected': ['45.0.0.10']}, {'identity': b'other link'}, {'resolver': '46.0.0.52'}):
            self.assertFalse(record_matches(good, KEY, VERSION, policy(**changes)))
        for bad in (None, b'', b'[]', b'x' * 257, good + b'\n', good.replace(b'"schema":1', b'"schema":true')):
            self.assertFalse(record_matches(bad, KEY, VERSION, policy()))

    def test_store_round_trip_and_cleanup(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder, patch('store.code_version', return_value=VERSION):
            root = Path(folder)
            shelf = Store(root / 'store', root, root / 'lock', disk_space=lambda _: DiskSpace('fixture', 100 * GB, 4096))
            self.assertFalse(shelf.egress_matches(policy()))
            shelf.save_egress(policy(), proof())
            self.assertTrue(shelf.egress_matches(policy()))
            self.assertFalse(shelf.egress_matches(policy(identity=b'other network')))
            with patch('store.code_version', return_value='b' * 64):
                self.assertFalse(shelf.egress_matches(policy()))
            record = root / 'store/egress/record.json'
            record.chmod(0o644)
            self.assertFalse(shelf.egress_matches(policy()))
            shelf.save_egress(policy(identity=b'other network'), proof())
            self.assertFalse(shelf.egress_matches(policy()))
            self.assertTrue(shelf.egress_matches(policy(identity=b'other network')))
            shelf.clean()
            self.assertFalse(shelf.egress_matches(policy(identity=b'other network')))

    def test_code_version_changes_with_source_contents(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            source = Path(folder) / 'launcher.py'
            source.write_text('first\n')
            first = code_version(Path(folder))
            source.write_text('second\n')
            self.assertNotEqual(first, code_version(Path(folder)))

    def test_firewall_keeps_controlled_network_listeners_out_of_reach(self):
        command = ['unshare', '--user', '--map-current-user', '--keep-caps', '--net', '--',
                   'bash', '-ec', 'ip link set lo up; exec "$@"', 'bench', sys.executable, '-B', __file__,
                   '--policy']
        result = subprocess.run(command, env=NAMESPACE_ENV, timeout=15, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    if sys.argv[1:] == ['--policy']:
        policy_fixture()
    elif sys.argv[1:] == ['--listen']:
        listeners()
    elif sys.argv[1:2] == ['--probe']:
        policy_probe(sys.argv[2:])
