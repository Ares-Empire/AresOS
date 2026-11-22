"""Pairing a Mac through the guarded Deskflow launcher (brief 321, step 3 review, finding 3).

A stand-in plays deskflow-core: it opens the core's IPC socket in the TMPDIR it is given, answers a hello the way
Deskflow 1.27 does (its own version on a mismatch, then the messages it queued), reports peers' fingerprints as
the real core does for every TLS peer, and writes down what the running server trusts. Qt Test answers the real
offscreen pairing prompt. The real openssl makes the certificate.
"""
import json
import fcntl
import io
import os
from pathlib import Path
import runpy
import signal
import stat
import tempfile
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox

CONFIG = Path(__file__).resolve().parents[1] / 'config'
LAUNCHER = CONFIG / 'usr/libexec/aresos-deskflow'
LOGIN = CONFIG / 'usr/libexec/aresos-deskflow-login'
MAC = 'AB' * 32
STRANGER = 'CD' * 32
OLD = 'v2:sha256:' + 'ef' * 32

CORE = r'''#!/usr/bin/python3 -I
import json, os, socket, sys, time
from pathlib import Path
plan = json.loads(Path(os.environ['STANDIN_PLAN']).read_text())
profile = Path(os.environ['XDG_CONFIG_HOME']) / 'Deskflow'
trusted = profile / 'tls/trusted-clients'
report = {'argv': sys.argv[1:], 'tmpdir': os.environ['TMPDIR'], 'config': os.environ['XDG_CONFIG_HOME'],
          'platform': os.environ.get('QT_QPA_PLATFORM'), 'display': os.environ.get('DISPLAY'),
          'settings': (profile / 'Deskflow.conf').read_text(),
          'certificate': (profile / 'tls/deskflow.pem').exists(),
          'trust_at_start': trusted.read_text() if trusted.exists() else None, 'client': False}
server = socket.socket(socket.AF_UNIX)
server.bind(os.path.join(os.environ['TMPDIR'], 'deskflow-core'))
server.listen(1)
server.settimeout(plan['accept_within'])
try:
    conn, _ = server.accept()
except TimeoutError:
    conn = None
if conn is not None:
    report['client'] = True
    reader = conn.makefile('r')
    version = '1.27.0+'
    while True:
        line = reader.readline().strip()
        if not line:
            break
        if line == f'hello={version}':
            conn.sendall(f'hello={version}\n'.encode())
            break
        conn.sendall(f'versionMismatch={version}\n'.encode())
    for message in ['connectionState=Listening'] + [f'peerFingerprint={peer}' for peer in plan['peers']]:
        try:
            conn.sendall((message + '\n').encode())
        except OSError:
            break  # the launcher is done with the channel once the owner accepted a Mac
        time.sleep(0.05)
    deadline = time.monotonic() + 5
    while plan['wait_for_trust'] and not trusted.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    conn.close()
report['trust_at_end'] = trusted.read_text() if trusted.exists() else None
Path(os.environ['STANDIN_REPORT']).write_text(json.dumps(report))
'''

class PairingTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root / 'run'
        self.runtime.mkdir(mode=0o700)
        self.source = self.root / 'config/Deskflow'
        self.source.mkdir(parents=True)
        # Whatever the user's settings say, the launch makes TLS and the peer check effective.
        (self.source / 'Deskflow.conf').write_text('[security]\ntlsEnabled=false\ncheckPeerFingerprints=false\n'
                                                  '[log]\ntoFile=true\n')
        self.core = self.root / 'deskflow-core'
        self.core.write_text(CORE)
        self.core.chmod(0o755)
        self.plan, self.report = self.root / 'plan.json', self.root / 'report.json'
        self.asked = []
        self.launcher = runpy.run_path(str(LAUNCHER))
        self.enterContext(patch.dict(os.environ, {
            'XDG_CONFIG_HOME': str(self.root / 'config'), 'XDG_RUNTIME_DIR': str(self.runtime),
            'STANDIN_PLAN': str(self.plan), 'STANDIN_REPORT': str(self.report),
            'XDG_CACHE_HOME': str(self.root / 'cache'), 'XDG_DATA_HOME': str(self.root / 'data'),
            'QT_QPA_PLATFORM': 'offscreen', 'DISPLAY': ':9'}))
        self.app = QApplication.instance() or QApplication([])
        previous = signal.getsignal(signal.SIGTERM)
        self.addCleanup(signal.signal, signal.SIGTERM, previous)

    def launch(self, argv=(), peers=(), accept=(), reject=(), wait_for_trust=False, accept_within=10.0):
        self.plan.write_text(json.dumps(dict(peers=list(peers), wait_for_trust=wait_for_trust,
                                             accept_within=accept_within)))

        def prompt(peer, own):
            def answer():
                box = QApplication.activeModalWidget()
                if not isinstance(box, QMessageBox):
                    self.app.closeAllWindows()
                    return
                self.asked.append(box.text())
                if peer in accept or peer in reject:
                    label = 'It matches' if peer in accept else "It doesn't match"
                    button = next(button for button in box.buttons() if button.text().replace('&', '') == label)
                    QTest.mouseClick(button, Qt.MouseButton.LeftButton)
                else:
                    focus = self.app.focusWidget()
                    QTest.keyClick(focus if focus and box.isAncestorOf(focus) else box, Qt.Key.Key_Return)

            QTimer.singleShot(0, answer)
            return self.launcher['ask'](peer, own)

        code = self.launcher['main'](list(argv), core=str(self.core), prompt=prompt, sharing_on=lambda: True)
        self.assertEqual(code, 0)
        return json.loads(self.report.read_text())

    def saved(self):
        trusted = self.source / 'tls/trusted-clients'
        return trusted.read_text() if trusted.exists() else None

    def test_an_empty_profile_pairs_only_the_mac_the_owner_confirms(self):
        report = self.launch(peers=[MAC, MAC, STRANGER], accept=[MAC], wait_for_trust=True)
        mac_line = f'v2:sha256:{MAC.lower()}\n'
        self.assertEqual(self.saved(), mac_line, 'the one fingerprint the owner confirmed, and nothing else')
        self.assertEqual(stat.S_IMODE((self.source / 'tls/trusted-clients').stat().st_mode), 0o600)
        self.assertEqual(report['trust_at_start'], None, 'the server trusted nobody before the owner answered')
        self.assertEqual(report['trust_at_end'], mac_line, "the running server trusts it too: the Mac's next try gets in")
        # Asked once: not again for the same Mac, and not at all for the stranger after the Mac was accepted.
        questions = self.asked
        self.assertEqual(len(questions), 1)
        text = questions[0]
        self.assertIn(self.launcher['columns'](MAC), text)
        self.assertNotIn(self.launcher['columns'](STRANGER), text)
        # A profile that never ran Deskflow's window gets a server certificate, and the dialog shows its
        # fingerprint for the Mac to check.
        certificate = self.source / 'tls/deskflow.pem'
        self.assertEqual(stat.S_IMODE(certificate.stat().st_mode), 0o600)
        pem = certificate.read_text()
        self.assertIn('PRIVATE KEY-----', pem)
        self.assertIn('BEGIN CERTIFICATE-----', pem)
        own = self.launcher['own_fingerprint'](certificate)
        self.assertRegex(own, r'^[0-9A-F]{64}$')
        self.assertIn("This laptop's fingerprint", text)
        self.assertIn(self.launcher['columns'](own), text)
        self.assertTrue(report['certificate'])
        # TLS and the peer check on in the copy the core ran with; its IPC socket in that private folder;
        # Wayland only.
        self.assertEqual(report['argv'], ['server'])
        self.assertIn('tlsEnabled=true', report['settings'])
        self.assertIn('checkPeerFingerprints=true', report['settings'])
        self.assertIn('toFile=false', report['settings'])
        self.assertEqual(report['tmpdir'], report['config'])
        self.assertEqual(Path(report['tmpdir']).parent, self.runtime)
        self.assertEqual((report['platform'], report['display']), ('wayland', None))
        self.assertTrue(report['client'])

    def test_nothing_is_trusted_unless_the_owner_confirms(self):
        # Default Enter rejects the first peer and explicitly clicking reject
        # rejects the second. A retry of the first peer cannot get another prompt.
        report = self.launch(peers=[MAC, STRANGER, MAC, 'not-a-fingerprint'], reject=[STRANGER])
        self.assertIsNone(self.saved())
        self.assertIsNone(report['trust_at_end'])
        texts = self.asked
        self.assertEqual(len(texts), 2, 'each peer asked about once')
        self.assertIn(self.launcher['columns'](MAC), texts[0])
        self.assertIn(self.launcher['columns'](STRANGER), texts[1])

    def test_enroll_replaces_the_saved_mac_only_when_the_owner_confirms(self):
        (self.source / 'tls').mkdir()
        (self.source / 'tls/trusted-clients').write_text(OLD + '\n')
        report = self.launch(['--enroll'], peers=[STRANGER], accept=[])
        self.assertEqual(self.saved(), OLD + '\n', 'refused: the saved Mac stays')
        self.assertIsNone(report['trust_at_start'], 'while pairing the server trusts nobody, not even the saved Mac')
        report = self.launch(['--enroll'], peers=[MAC], accept=[MAC], wait_for_trust=True)
        self.assertEqual(self.saved(), f'v2:sha256:{MAC.lower()}\n')
        self.assertEqual(report['trust_at_end'], f'v2:sha256:{MAC.lower()}\n')

    def test_a_paired_mac_starts_the_server_without_asking(self):
        (self.source / 'tls').mkdir()
        (self.source / 'tls/trusted-clients').write_text(OLD + '\n')
        report = self.launch(peers=[MAC], accept=[MAC], accept_within=1.0)
        self.assertFalse(report['client'], 'no pairing channel is opened')
        self.assertEqual(report['trust_at_start'], OLD + '\n')
        self.assertEqual(self.asked, [])
        self.assertEqual(self.saved(), OLD + '\n')

    def test_a_trust_list_with_two_entries_is_refused_and_points_to_enroll(self):
        (self.source / 'tls').mkdir()
        (self.source / 'tls/trusted-clients').write_text(f'{OLD}\nv2:sha256:{MAC.lower()}\n')
        with self.assertRaisesRegex(ValueError, '--enroll'):
            self.launch(peers=[], accept_within=1.0)
        self.assertFalse(self.report.exists(), 'the core was never started')

    def test_a_core_without_its_pairing_channel_is_stopped(self):
        pid_file = self.root / 'core.pid'
        self.core.write_text('#!/usr/bin/python3 -I\nimport os, time\n'
                             f'open({str(pid_file)!r}, "w").write(str(os.getpid()))\ntime.sleep(60)\n')
        with self.assertRaisesRegex(OSError, 'pairing channel'):
            self.launcher['main']([], core=str(self.core), pairing_within=1.0, sharing_on=lambda: True)
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pid_file.read_text()), 0)
        self.assertIsNone(self.saved())

    def test_off_stops_a_core_even_if_the_portal_cannot_close_it(self):
        (self.source / 'tls').mkdir()
        (self.source / 'tls/trusted-clients').write_text(OLD + '\n')
        ready = self.root / 'started'
        self.core.write_text('#!/usr/bin/python3 -I\nimport os, time\n'
                             f'open({str(ready)!r}, "w").write(str(os.getpid()))\ntime.sleep(10)\n')
        self.launcher['main']([], core=str(self.core), sharing_on=lambda: not ready.exists())
        with self.assertRaises(ProcessLookupError):
            os.kill(int(ready.read_text()), 0)

    def test_a_second_guarded_launch_does_not_replace_the_running_profile(self):
        with (self.runtime / 'aresos-deskflow.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual(self.launcher['main']([], core=str(self.core), sharing_on=lambda: True), 0)
            with self.assertRaisesRegex(ValueError, 'already running'):
                self.launcher['main'](['--enroll'], core=str(self.core), sharing_on=lambda: True)
        self.assertFalse(self.report.exists())

    def test_crossing_coordinates_do_not_leave_the_guard(self):
        source = io.BytesIO(b'[2026-11-22T12:00:00] INFO: switch from "laptop" to "mac" at -18,479\n'
                            b'INFO: accepted secure socket\nINFO: jump from "mac" to "laptop" at 221,444\n')
        output = io.BytesIO()
        self.launcher['relay_core_output'](source, output)
        self.assertEqual(output.getvalue(), b'[2026-11-22T12:00:00] INFO: switch from "laptop" to "mac"\n'
                                           b'INFO: accepted secure socket\nINFO: jump from "mac" to "laptop"\n')

class LoginTest(unittest.TestCase):
    def test_off_does_not_even_load_the_hub_catalogue(self):
        login = runpy.run_path(str(LOGIN))
        with patch('runpy.run_path', return_value={'sharing_on': lambda: False}) as load:
            login['main']()
        load.assert_called_once_with('/usr/libexec/aresos-input-sharing-set')

    def test_on_uses_the_hub_scope_and_exact_guarded_executable(self):
        login = runpy.run_path(str(LOGIN))
        app = Mock(source='image', argv=login['GUARDED'])
        launcher = Mock()
        launcher.command.return_value = ['/usr/bin/systemd-run', '--scope', *app.argv]
        launcher.working_directory.return_value = '/fixture'
        shell = {'REGISTRY': '/registry', 'load_catalogue': Mock(return_value=({login['APP_ID']: app}, None)),
                 'resolve': Mock(return_value=(list(app.argv), '~', None)),
                 'ScopeLauncher': Mock(return_value=launcher)}
        with (patch('runpy.run_path', side_effect=({'sharing_on': lambda: True}, shell)),
              patch('os.chdir') as chdir, patch('os.execve') as execve):
            login['main']()
        self.assertEqual(launcher.command.call_args.args[:2], (app, list(app.argv)))
        self.assertRegex(launcher.command.call_args.args[2], r'^[0-9a-f]{16}$')
        chdir.assert_called_once_with('/fixture')
        execve.assert_called_once_with('/usr/bin/systemd-run', launcher.command.return_value,
                                        launcher.environment.return_value)

    def test_enrollment_requires_the_same_sharing_gate(self):
        login = runpy.run_path(str(LOGIN))
        with patch('runpy.run_path', return_value={'sharing_on': lambda: False}) as load:
            login['main'](['--enroll'])
        load.assert_called_once_with('/usr/libexec/aresos-input-sharing-set')


if __name__ == '__main__':
    unittest.main()
