"""The AresOS app helper (aresos-shell/1.0, OS-BASE.md Appendix B1/B2), package 24."""
import importlib.machinery
import json
import os
import pathlib
import socket
import stat
import struct
import sys
import tempfile
import threading
import types
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
HELPER = ROOT / 'os/config/usr/libexec/aresos-shell'
REGISTRY = ROOT / 'os/config/usr/share/aresos/apps'
loader = importlib.machinery.SourceFileLoader('aresos_shell', str(HELPER))
shell = types.ModuleType(loader.name)
sys.modules[loader.name] = shell
loader.exec_module(shell)
shell.LOG.disabled = True

NONCE = 'test-nonce-0123456789abcdef'
INSTANCE = 'desk-1'
ALL = ['list_apps', 'open_app', 'app_state', 'shell_focus', 'world_ready', 'heartbeat', 'windows']


class Conn:
    def __init__(self):
        self.sent = []
        self.closing = False

    def send(self, message):
        self.sent.append(json.loads(json.dumps(message)))

    def finish(self):
        self.closing = True

    def events(self, name=None):
        return [m for m in self.sent if 'event' in m and (name is None or m['event'] == name)]


class Proc:
    def __init__(self, code=None):
        self.code = code

    def poll(self):
        return self.code


class Base(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.journal = os.path.join(self.folder.name, 'journal.json')
        self.now = [100.0]
        self.popen = mock.Mock(side_effect=lambda *a, **k: Proc())
        self.active_units = set()
        self.windows = None
        self.activations = []

    def clock(self):
        return self.now[0]

    def launcher(self):
        run = mock.Mock(side_effect=lambda argv, **k: mock.Mock(returncode=0 if argv[-1] in self.active_units else 3))
        return shell.ScopeLauncher(popen=self.popen, run=run, environ={
            'HOME': '/var/home/ares', 'PATH': '/usr/bin', 'WAYLAND_DISPLAY': 'wayland-0',
            'ARESOS_LAUNCH_NONCE': NONCE, 'ARESOS_DESKTOP_INSTANCE': INSTANCE, 'NOTIFY_SOCKET': '/run/notify'})

    def helper(self, registry=REGISTRY, missing=('/usr/bin/google-chrome',), tracked=False):
        if tracked:
            self.windows = shell.Windows(clock=self.clock)
        return shell.Helper(str(registry), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                            windows=self.windows, activate=self.activate if tracked else None, clock=self.clock,
                            executable=lambda path: path not in missing)

    def activate(self, handle):
        self.activations.append(handle)
        return True

    def connect(self, helper, capabilities=ALL, requires=('list_apps', 'open_app')):
        conn = Conn()
        helper.connected(conn)
        reply = self.request(helper, conn, 'hello', 'h-1', major=1, minor=0, capabilities=list(capabilities),
                             requires=list(requires), instance=INSTANCE, nonce=NONCE)
        self.assertTrue(reply['ok'], reply)
        return conn

    @staticmethod
    def request(helper, conn, op, request_id='r-1', **fields):
        message = {'protocol': 'aresos-shell/1.0', 'id': request_id, 'op': op}
        message.update(fields)
        helper.receive(conn, json.dumps(message).encode() + b'\n')
        return conn.sent[-1]

    def write_registry(self, entries):
        folder = pathlib.Path(self.folder.name) / 'apps'
        folder.mkdir(exist_ok=True)
        for name, data in entries.items():
            (folder / name).write_text(data if isinstance(data, str) else json.dumps(data))
        return folder


def entry(app_id, **changes):
    data = {'schema': 1, 'id': app_id, 'name': app_id.title(), 'argv': ['/usr/bin/' + app_id],
            'working_directory': '~', 'window': {'app_ids': ['org.test.' + app_id], 'instance': 'multi'}}
    data.update(changes)
    return data


class RegistryTest(Base):
    def test_shipped_entries_are_reviewed_launch_definitions(self):
        apps, revision = shell.load_registry(str(REGISTRY))
        self.assertEqual(set(apps), {'terminal', 'notepad', 'browser'})
        self.assertRegex(revision, r'^[0-9a-f]{16}$')
        for path in REGISTRY.glob('*.json'):
            app = shell.parse_entry(json.loads(path.read_text()))
            self.assertEqual(path.stem, app.id)
            self.assertIsNone(app.invalid)
            self.assertTrue(app.argv[0].startswith('/usr/bin/'))
        self.assertEqual(apps['terminal'].argv, ('/usr/bin/foot', '--app-id=aresos.terminal'))
        self.assertEqual(apps['terminal'].app_ids, {'aresos.terminal'})
        # notepad keeps package 01's ID; on AresOS it is KWrite, already in the base image.
        self.assertEqual(apps['notepad'].argv, ('/usr/bin/kwrite',))
        self.assertEqual(apps['notepad'].app_ids, {'org.kde.kwrite'})
        image = (ROOT / 'os/manifest/ci/06c/image-full-1/packages.txt').read_text().splitlines()
        self.assertTrue(any(line.startswith('kwrite-26.') for line in image))
        self.assertTrue(any(line.startswith('foot-') for line in image))
        self.assertEqual(apps['browser'].argv, ('/usr/bin/google-chrome',))
        self.assertEqual(apps['browser'].instance, 'single')

    def test_browser_is_available_only_when_the_binary_exists(self):
        for missing, available in (((), True), (('/usr/bin/google-chrome',), False)):
            helper = self.helper(missing=missing)
            conn = self.connect(helper)
            reply = self.request(helper, conn, 'list_apps', 'l-1')
            rows = {row['id']: row for row in reply['apps']}
            self.assertEqual(rows['browser']['available'], available)
            self.assertEqual(rows['browser']['reason'], None if available else 'not_installed')
            self.assertTrue(rows['terminal']['available'] and rows['notepad']['available'])

    def test_list_apps_never_sends_commands(self):
        helper = self.helper()
        conn = self.connect(helper)
        reply = self.request(helper, conn, 'list_apps', 'l-1')
        self.assertEqual(reply['revision'], helper.revision)
        for row in reply['apps']:
            self.assertEqual(set(row), {'id', 'name', 'available', 'reason'})
        self.assertNotIn('/usr/bin', json.dumps(reply))

    def test_broken_entries_stay_visible_but_unavailable(self):
        folder = self.write_registry({
            'good.json': entry('good'),
            'typo.json': entry('typo', argvv=['/usr/bin/x']),
            'shell.json': entry('shell', argv='foot -e sh -c "rm -rf ~"'),
            'relative.json': entry('relative', argv=['foot']),
            'one.json': entry('twin'),
            'two.json': entry('twin', argv=['/usr/bin/other']),
            'clash-a.json': entry('clasha', window={'app_ids': ['org.test.same'], 'instance': 'multi'}),
            'clash-b.json': entry('clashb', window={'app_ids': ['org.test.same'], 'instance': 'multi'}),
            'desk.json': entry('desk', window={'app_ids': ['aresos-desktop'], 'instance': 'multi'}),
            'noid.json': {'schema': 1, 'argv': ['/usr/bin/x']},
            'garbage.json': '{not json',
            'nan.json': '{"schema": NaN}',
        })
        apps, _ = shell.load_registry(str(folder))
        self.assertEqual(set(apps), {'good', 'typo', 'shell', 'relative', 'twin', 'clasha', 'clashb', 'desk'})
        self.assertIsNone(apps['good'].invalid)
        for app_id in ('typo', 'shell', 'relative', 'desk'):
            self.assertEqual(apps[app_id].invalid, 'invalid_entry', app_id)
        self.assertEqual(apps['twin'].invalid, 'duplicate_entry')
        self.assertEqual(apps['clasha'].invalid, 'duplicate_window_identity')
        self.assertEqual(apps['clashb'].invalid, 'duplicate_window_identity')
        helper = self.helper(registry=folder, missing=())
        conn = self.connect(helper)
        rows = {row['id']: row for row in self.request(helper, conn, 'list_apps', 'l-1')['apps']}
        self.assertEqual(rows['shell'], {'id': 'shell', 'name': 'Shell', 'available': False, 'reason': 'invalid_entry'})
        reply = self.request(helper, conn, 'open_app', 'o-1', app_id='shell')
        self.assertEqual((reply['ok'], reply['error'], reply['reason']), (False, 'unavailable', 'invalid_entry'))
        self.popen.assert_not_called()

    def test_desktop_entries_split_exec_without_a_shell(self):
        folder = pathlib.Path(self.folder.name)
        cases = {
            'Exec=/usr/bin/kwrite %U': ['/usr/bin/kwrite'],
            'Exec="/opt/my app/run" --flag "a \\\\"quoted\\\\" word" %f 100%%': [
                '/opt/my app/run', '--flag', 'a "quoted" word', '100%'],
            'Exec=/usr/bin/tool %i %c %k': ['/usr/bin/tool', '--icon', 'tool-icon', 'Tool', None],
        }
        for line, expected in cases.items():
            path = folder / 'case.desktop'
            path.write_text(f'[Desktop Entry]\nType=Application\nName=Tool\nIcon=tool-icon\n{line}\n'
                            '[Desktop Action other]\nExec=/usr/bin/other\n')
            argv, directory = shell.desktop_exec(str(path))
            self.assertEqual(argv, [str(path) if part is None else part for part in expected], line)
            self.assertIsNone(directory)
        for line in ("Exec=sh -c 'echo hi'", 'Exec=/usr/bin/a;rm', 'Exec=/usr/bin/a $HOME', 'Exec="/usr/bin/a',
                     'Exec=/usr/bin/a %z', 'Exec=/usr/bin/a --name=%c'):
            path.write_text(f'[Desktop Entry]\nType=Application\n{line}\n')
            with self.subTest(line=line), self.assertRaises(ValueError):
                shell.desktop_exec(str(path))
        apps = folder / 'applications'
        apps.mkdir()
        (apps / 'org.test.editor.desktop').write_text('[Desktop Entry]\nType=Application\nExec=/usr/bin/editor %F\n'
                                                      'Path=/srv/notes\n')
        app = shell.App('editor', 'Editor', desktop_entry='org.test.editor.desktop',
                        app_ids=frozenset({'org.test.editor'}))
        self.assertEqual(shell.resolve(app, lambda p: True, (str(apps),)), (['/usr/bin/editor'], '/srv/notes', None))
        self.assertEqual(shell.resolve(app, lambda p: False, (str(apps),))[2], 'not_installed')
        missing = shell.App('gone', 'Gone', desktop_entry='org.test.gone.desktop')
        self.assertEqual(shell.resolve(missing, lambda p: True, (str(apps),)), (None, None, 'not_installed'))


class ProtocolTest(Base):
    def test_hello_negotiates_version_and_capabilities(self):
        helper = self.helper()
        conn = Conn()
        helper.connected(conn)
        reply = self.request(helper, conn, 'hello', 'h-1', major=1, minor=7, capabilities=ALL,
                             requires=['open_app'], instance=INSTANCE, nonce=NONCE, future_field={'x': 1})
        self.assertEqual(reply['protocol'], 'aresos-shell/1.0')
        self.assertEqual((reply['id'], reply['ok'], reply['major'], reply['minor']), ('h-1', True, 1, 0))
        # Without a compositor there is no window tracking, so no shell_focus.
        self.assertEqual(set(reply['capabilities']), {'list_apps', 'open_app', 'app_state', 'world_ready', 'heartbeat'})
        self.assertIs(helper.desktop, conn)
        again = self.request(helper, conn, 'hello', 'h-2', major=1, minor=0, instance=INSTANCE, nonce=NONCE)
        self.assertEqual(again['error'], 'invalid_state')

    def test_hello_refuses_wrong_nonce_instance_version_and_missing_capabilities(self):
        helper = self.helper()
        base = dict(major=1, minor=0, capabilities=ALL, requires=['open_app'], instance=INSTANCE, nonce=NONCE)
        for change, code in ((dict(nonce=NONCE[:-1] + 'X'), 'not_authorized'), (dict(nonce=None), 'not_authorized'),
                             (dict(instance='desk-2'), 'not_authorized'), (dict(major=2), 'incompatible_version'),
                             (dict(major='1'), 'malformed'), (dict(requires=['shell_focus']), 'incompatible_version')):
            conn = Conn()
            helper.connected(conn)
            reply = self.request(helper, conn, 'hello', 'h-1', **dict(base, **change))
            with self.subTest(change=change):
                self.assertEqual((reply['ok'], reply['error']), (False, code))
                self.assertTrue(conn.closing)
                self.assertFalse(conn.authenticated)
                self.assertNotIn(conn, [helper.desktop])
        self.assertEqual(reply['missing'], ['shell_focus'])
        conn = Conn()
        helper.connected(conn)
        reply = self.request(helper, conn, 'hello', 'h-1', protocol='aresos-shell/2.0', **base)
        self.assertEqual(reply['error'], 'incompatible_version')
        self.assertTrue(conn.closing)

    def test_operations_need_hello_and_guardian_operations_are_unknown(self):
        helper = self.helper()
        conn = Conn()
        helper.connected(conn)
        self.assertEqual(self.request(helper, conn, 'list_apps')['error'], 'hello_required')
        self.assertEqual(self.request(helper, conn, 'open_app', app_id='terminal')['error'], 'hello_required')
        self.popen.assert_not_called()
        conn = self.connect(helper)
        for op in ('request_power', 'prepare_stop', 'save_complete', 'exec', 'run_command'):
            reply = self.request(helper, conn, op, 'x-1', command=['/usr/bin/sh'])
            self.assertEqual((reply['ok'], reply['error']), (False, 'unknown_operation'))
        self.assertFalse(conn.closing)
        self.assertTrue(self.request(helper, conn, 'list_apps', 'l-1')['ok'])

    def test_malformed_input_is_rejected_without_crashing(self):
        helper = self.helper()
        conn = self.connect(helper)
        for raw in (b'{nope', b'\xff\xfe{}', b'[1,2]', b'"text"', b'{"op":"list_apps"}',
                    b'{"protocol":"aresos-shell/1.0","id":"bad id!","op":"list_apps"}',
                    b'{"protocol":"aresos-shell/1.0","id":"n-1","op":"list_apps","x":NaN}',
                    b'[' * 20000 + b']' * 20000):
            before = len(conn.sent)
            helper.receive(conn, raw + b'\n')
            with self.subTest(raw=raw[:40]):
                self.assertEqual(len(conn.sent), before + 1)
                self.assertEqual((conn.sent[-1]['ok'], conn.sent[-1]['error'], conn.sent[-1]['id']),
                                 (False, 'malformed', None))
        self.assertEqual(self.request(helper, conn, 'open_app', 'm-1', app_id=7)['error'], 'malformed')
        self.assertEqual(self.request(helper, conn, 'list_apps', 'v-1', protocol=None)['error'], 'incompatible_version')
        self.assertEqual(self.request(helper, conn, 'list_apps', 'v-2', protocol='aresos-shell/9.0')['error'],
                         'incompatible_version')
        self.assertFalse(conn.closing)
        self.assertTrue(self.request(helper, conn, 'list_apps', 'ok-1')['ok'])

    def test_oversized_messages_are_refused_and_close_the_connection(self):
        for raw in (b'x' * (shell.MAX_MESSAGE + 1), b'{"pad":"' + b'x' * shell.MAX_MESSAGE + b'"}\n'):
            helper = self.helper()
            conn = self.connect(helper)
            helper.receive(conn, raw)
            self.assertEqual(conn.sent[-1]['error'], 'message_too_large')
            self.assertTrue(conn.closing)
            self.assertEqual(len(conn.inbuf), 0)

    def test_split_and_batched_lines_are_framed(self):
        helper = self.helper()
        conn = self.connect(helper)
        line = json.dumps({'protocol': 'aresos-shell/1.0', 'id': 'l-1', 'op': 'list_apps'}).encode() + b'\n'
        helper.receive(conn, line[:10])
        self.assertEqual(len(conn.sent), 1)
        helper.receive(conn, line[10:] + line.replace(b'l-1', b'l-2'))
        self.assertEqual([m['id'] for m in conn.sent[1:]], ['l-1', 'l-2'])

    def test_world_ready_and_heartbeat_carry_instance_and_nonce(self):
        helper = self.helper()
        conn = self.connect(helper)
        world = {'id': 'AresOS', 'desktop': True}
        self.assertTrue(self.request(helper, conn, 'world_ready', 'w-1', instance=INSTANCE, nonce=NONCE,
                                     world=world)['ok'])
        self.assertEqual(helper.world, 'AresOS')
        self.assertEqual(self.request(helper, conn, 'world_ready', 'w-2', instance=INSTANCE, nonce=NONCE,
                                      world={'id': 'Survival', 'desktop': False})['error'], 'malformed')
        self.now[0] += 5
        self.assertTrue(self.request(helper, conn, 'heartbeat', 'b-1', instance=INSTANCE, nonce=NONCE,
                                     ready=True, world=world)['ok'])
        self.assertEqual(helper.last_heartbeat, 105.0)
        self.assertTrue(self.request(helper, conn, 'heartbeat', 'b-2', instance=INSTANCE, nonce=NONCE,
                                     ready=False)['ok'])
        self.assertIsNone(helper.world)
        reply = self.request(helper, conn, 'heartbeat', 'b-3', instance=INSTANCE, nonce='x' * 20, ready=True)
        self.assertEqual(reply['error'], 'not_authorized')
        self.assertTrue(conn.closing)

    def test_a_newer_authenticated_desktop_replaces_the_old_connection(self):
        helper = self.helper()
        first = self.connect(helper)
        second = self.connect(helper)
        self.assertTrue(first.closing)
        self.assertIs(helper.desktop, second)

    def test_unauthenticated_connections_time_out(self):
        helper = self.helper()
        conn = Conn()
        helper.connected(conn)
        self.now[0] += shell.HELLO_TIMEOUT + 1
        helper.tick()
        self.assertTrue(conn.closing)


class LaunchTest(Base):
    def test_open_app_starts_its_own_user_scope_without_the_launch_secrets(self):
        helper = self.helper()
        conn = self.connect(helper)
        reply = self.request(helper, conn, 'open_app', 'o-1', app_id='terminal')
        self.assertEqual((reply['ok'], reply['state'], reply['request_id'], reply['app_id']),
                         (True, 'starting', 'o-1', 'terminal'))
        self.assertRegex(reply['launch_id'], r'^[0-9a-f]{16}$')
        self.popen.assert_called_once()
        argv, options = self.popen.call_args.args[0], self.popen.call_args.kwargs
        self.assertEqual(argv, ['/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect', '--slice=app.slice',
                                f'--unit=app-aresos-terminal-{reply["launch_id"]}.scope',
                                '--description=AresOS app: Terminal', '--', '/usr/bin/foot', '--app-id=aresos.terminal'])
        self.assertEqual(options['cwd'], '/var/home/ares')
        self.assertTrue(options['start_new_session'])
        self.assertNotIn('ARESOS_LAUNCH_NONCE', options['env'])
        self.assertNotIn('ARESOS_DESKTOP_INSTANCE', options['env'])
        self.assertNotIn('NOTIFY_SOCKET', options['env'])
        self.assertEqual(options['env']['WAYLAND_DISPLAY'], 'wayland-0')
        self.assertNotIn('shell', options)

    def test_unit_names_escape_dashes(self):
        app = shell.App('my-app', 'My App', ('/usr/bin/x',))
        self.assertEqual(shell.ScopeLauncher.unit(app, 'ab12'), 'app-aresos-my\\x2dapp-ab12.scope')

    def test_duplicate_request_ids_return_the_same_result_and_launch_once(self):
        helper = self.helper()
        conn = self.connect(helper)
        first = self.request(helper, conn, 'open_app', 'o-1', app_id='notepad')
        again = self.request(helper, conn, 'open_app', 'o-1', app_id='notepad')
        self.assertEqual({k: v for k, v in first.items() if k != 'protocol'}, {k: v for k, v in again.items() if k != 'protocol'})
        self.assertEqual(self.popen.call_count, 1)
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-1', app_id='terminal')['error'], 'request_id_reused')
        self.assertEqual(self.popen.call_count, 1)
        # A new deliberate click gets a new request ID and a new launch.
        second = self.request(helper, conn, 'open_app', 'o-2', app_id='notepad')
        self.assertNotEqual(second['launch_id'], first['launch_id'])
        self.assertEqual(self.popen.call_count, 2)

    def test_unknown_and_unavailable_apps_fail_with_stable_errors(self):
        helper = self.helper()
        conn = self.connect(helper)
        unknown = self.request(helper, conn, 'open_app', 'o-1', app_id='spotify')
        self.assertEqual((unknown['ok'], unknown['state'], unknown['error'], unknown['launch_id']),
                         (False, 'failed', 'unknown_app', None))
        browser = self.request(helper, conn, 'open_app', 'o-2', app_id='browser')
        self.assertEqual((browser['error'], browser['reason']), ('unavailable', 'not_installed'))
        self.assertEqual(self.request(helper, conn, 'open_app', 'o-2', app_id='browser')['error'], 'unavailable')
        self.popen.assert_not_called()

    def test_spawn_failure_reports_launch_failed(self):
        helper = self.helper()
        conn = self.connect(helper)
        self.popen.side_effect = FileNotFoundError('systemd-run')
        reply = self.request(helper, conn, 'open_app', 'o-1', app_id='terminal')
        self.assertEqual((reply['ok'], reply['state'], reply['error']), (False, 'failed', 'launch_failed'))
        self.assertEqual(helper.journal.entries['o-1']['state'], 'failed')

    def test_journal_survives_a_restart_and_never_retries_a_launch(self):
        helper = self.helper()
        conn = self.connect(helper)
        first = self.request(helper, conn, 'open_app', 'o-1', app_id='terminal')
        if os.name == 'posix':
            self.assertEqual(stat.S_IMODE(os.stat(self.journal).st_mode), 0o600)
        restarted = self.helper()
        conn = self.connect(restarted)
        again = self.request(restarted, conn, 'open_app', 'o-1', app_id='terminal')
        self.assertEqual((again['launch_id'], again['state']), (first['launch_id'], 'starting'))
        self.assertEqual(self.popen.call_count, 1)

    def test_a_launch_interrupted_by_a_crash_is_reconciled_not_retried(self):
        units = {'o-dead': 'app-aresos-terminal-dead.scope', 'o-alive': 'app-aresos-notepad-alive.scope'}
        with open(self.journal, 'w') as handle:
            json.dump({'instance': INSTANCE, 'launches': {
                'o-dead': {'app_id': 'terminal', 'launch_id': 'dead', 'state': 'launching', 'unit': units['o-dead']},
                'o-alive': {'app_id': 'notepad', 'launch_id': 'alive', 'state': 'launching', 'unit': units['o-alive']},
            }}, handle)
        self.active_units = {units['o-alive']}
        helper = self.helper()
        conn = self.connect(helper)
        dead = self.request(helper, conn, 'open_app', 'o-dead', app_id='terminal')
        alive = self.request(helper, conn, 'open_app', 'o-alive', app_id='notepad')
        self.assertEqual((dead['state'], dead['error']), ('failed', 'launch_uncertain'))
        self.assertEqual((alive['state'], alive['launch_id']), ('starting', 'alive'))
        self.popen.assert_not_called()

    def test_journal_of_another_desktop_instance_is_ignored_and_bounded(self):
        with open(self.journal, 'w') as handle:
            json.dump({'instance': 'old-desk', 'launches': {'o-1': {'app_id': 'terminal', 'state': 'starting'}}}, handle)
        helper = self.helper()
        self.assertEqual(helper.journal.entries, {})
        conn = self.connect(helper)
        for number in range(shell.JOURNAL_LIMIT + 20):
            self.request(helper, conn, 'open_app', f'u-{number}', app_id='unknown')
        with open(self.journal) as handle:
            self.assertEqual(len(json.load(handle)['launches']), shell.JOURNAL_LIMIT)

    def test_without_window_tracking_exit_codes_are_reported(self):
        helper = self.helper()
        conn = self.connect(helper)
        processes = [Proc(), Proc()]
        self.popen.side_effect = lambda *a, **k: processes.pop(0)
        bad = self.request(helper, conn, 'open_app', 'o-1', app_id='terminal')
        good = self.request(helper, conn, 'open_app', 'o-2', app_id='notepad')
        helper.processes['o-1'].code = 1
        helper.processes['o-2'].code = 0
        helper.tick()
        states = conn.events('app_state')
        self.assertEqual([(e['request_id'], e['launch_id'], e['state'], e['error']) for e in states],
                         [('o-1', bad['launch_id'], 'failed', 'launch_failed')])
        self.assertEqual(helper.journal.entries['o-2']['state'], 'starting')
        self.assertEqual(good['state'], 'starting')
        self.assertEqual(conn.events('shell_focus'), [])


class WindowTest(Base):
    def setUp(self):
        super().setUp()
        self.helper_ = self.helper(missing=(), tracked=True)
        self.conn = self.connect(self.helper_)
        self.window(1, 'aresos-desktop', activated=True)

    def window(self, handle, app_id, activated=False, parent=0, batch=True):
        windows = self.windows
        windows.new(handle)
        windows.app_id(handle, app_id)
        windows.parent(handle, parent)
        windows.state(handle, activated)
        windows.done(handle)
        if activated:
            self.focus(handle, batch=False)
        if batch:
            self.helper_.windows_changed()

    def focus(self, handle, batch=True):
        for toplevel in list(self.windows.toplevels.values()):
            self.windows.state(toplevel.handle, toplevel.handle == handle)
            self.windows.done(toplevel.handle)
        if batch:
            self.helper_.windows_changed()

    def close(self, handle, batch=True):
        self.windows.gone(handle)
        if batch:
            self.helper_.windows_changed()

    def open(self, app_id, request_id):
        return self.request(self.helper_, self.conn, 'open_app', request_id, app_id=app_id)

    def focus_events(self):
        return [(e['focus'], e['reason'], e.get('app_id')) for e in self.conn.events('shell_focus')]

    def test_capabilities_include_window_tracking(self):
        self.assertIn('shell_focus', self.conn.sent[0]['capabilities'])
        self.assertIn('windows', self.conn.sent[0]['capabilities'])

    def test_new_window_confirms_launch_and_moves_the_shell_to_background(self):
        self.window(2, 'org.kde.kwrite')  # already open before the launch: never claimed
        self.now[0] += 1
        launch = self.open('notepad', 'o-1')
        self.assertEqual(launch['state'], 'starting')
        self.window(3, 'org.kde.kwrite', activated=True)
        states = [(e['request_id'], e['state']) for e in self.conn.events('app_state')]
        self.assertEqual(states, [('o-1', 'focused')])
        self.assertEqual(self.helper_.handles['o-1'], {3})
        self.assertEqual(self.focus_events(), [('background', 'app_activated', 'notepad')])
        again = self.open('notepad', 'o-1')
        self.assertEqual((again['state'], again['launch_id']), ('focused', launch['launch_id']))

    def test_no_matching_window_fails_the_launch_and_never_hangs(self):
        self.open('notepad', 'o-1')
        self.window(2, 'org.other.app', activated=True)
        self.now[0] += shell.WINDOW_TIMEOUT + 0.1
        self.helper_.tick()
        failed = self.conn.events('app_state')[-1]
        self.assertEqual((failed['request_id'], failed['state'], failed['error']), ('o-1', 'failed', 'no_window'))
        self.window(3, 'org.kde.kwrite')  # too late: the launch stays failed
        self.assertEqual(self.helper_.journal.entries['o-1']['state'], 'failed')

    def test_early_exit_fails_multi_instance_apps_but_single_instance_apps_wait(self):
        self.open('notepad', 'o-1')
        self.open('browser', 'o-2')
        self.helper_.processes['o-1'].code = 0
        self.helper_.processes['o-2'].code = 0
        self.helper_.tick()
        self.assertEqual(self.helper_.journal.entries['o-1']['error'], 'launch_failed')
        self.assertEqual(self.helper_.journal.entries['o-2']['state'], 'starting')
        self.window(2, 'google-chrome', activated=True)
        self.assertEqual(self.helper_.journal.entries['o-2']['state'], 'focused')

    def test_closing_the_foreground_apps_last_window_returns_to_the_desktop(self):
        self.open('notepad', 'o-1')
        self.window(2, 'org.kde.kwrite', activated=True)
        self.window(3, 'org.kde.kwrite', activated=True)  # the owner opened a second window
        self.close(3)
        self.assertEqual(self.activations, [])
        self.assertEqual(self.focus_events(), [('background', 'app_activated', 'notepad')])
        self.focus(2)
        self.close(2)
        self.assertEqual(self.activations, [1])
        last = self.conn.events('shell_focus')[-1]
        self.assertEqual((last['focus'], last['reason'], last['app_id'], last['activated']),
                         ('foreground', 'app_closed', 'notepad', True))
        self.assertEqual(self.conn.events('app_state')[-1]['state'], 'closed')
        self.focus(1)  # the compositor confirms; no second foreground event
        self.assertEqual(len(self.conn.events('shell_focus')), 2)

    def test_closing_a_background_app_never_emits_shell_focus(self):
        self.open('terminal', 'o-1')
        self.window(2, 'aresos.terminal', activated=True)
        self.open('notepad', 'o-2')
        self.window(3, 'org.kde.kwrite', activated=True)
        before = self.focus_events()
        self.close(2)
        self.assertEqual(self.focus_events(), before)
        self.assertEqual(self.activations, [])
        self.assertEqual(self.helper_.journal.entries['o-1']['state'], 'closed')
        self.assertEqual(self.helper_.journal.entries['o-2']['state'], 'focused')

    def test_dialogs_count_as_their_apps_windows(self):
        self.open('notepad', 'o-1')
        self.window(2, 'org.kde.kwrite', activated=True)
        self.window(3, '', parent=2, activated=True)  # e.g. a save dialog
        self.assertEqual(self.helper_.foreground_app, 'notepad')
        self.close(3)
        self.assertEqual(self.activations, [])
        self.focus(2)
        self.close(2)
        self.assertEqual(self.activations, [1])

    def test_close_and_next_activation_in_one_batch_still_returns_once(self):
        self.open('terminal', 'o-1')
        self.window(2, 'aresos.terminal')
        self.open('notepad', 'o-2')
        self.window(3, 'org.kde.kwrite', activated=True)
        # labwc may focus the next window before or after reporting the close.
        self.close(3, batch=False)
        self.focus(2, batch=False)
        self.helper_.windows_changed()
        self.assertEqual(self.activations, [1])
        self.assertEqual(self.focus_events(), [('background', 'app_activated', 'notepad'),
                                               ('foreground', 'app_closed', 'notepad')])

    def test_switching_to_the_desktop_and_unknown_windows(self):
        self.open('notepad', 'o-1')
        self.window(2, 'org.kde.kwrite', activated=True)
        self.focus(1)
        self.focus(1)
        self.window(4, 'org.unknown', activated=True)
        self.assertEqual(self.focus_events(), [('background', 'app_activated', 'notepad'),
                                               ('foreground', 'desktop_activated', None),
                                               ('background', 'other_window', None)])
        self.close(2)  # notepad was in the background
        self.assertEqual(len(self.focus_events()), 3)

    def test_without_a_desktop_window_the_return_is_reported_unactivated(self):
        self.close(1)
        self.open('notepad', 'o-1')
        self.window(2, 'org.kde.kwrite', activated=True)
        self.close(2)
        last = self.conn.events('shell_focus')[-1]
        self.assertEqual((last['focus'], last['activated']), ('foreground', False))

    def test_events_follow_the_capabilities_the_mod_declared(self):
        quiet = self.connect(self.helper_, capabilities=['list_apps', 'open_app'])
        self.assertIs(self.helper_.desktop, quiet)
        self.request(self.helper_, quiet, 'open_app', 'q-1', app_id='notepad')
        self.window(2, 'org.kde.kwrite', activated=True)
        self.assertEqual(quiet.events(), [])

    def test_a_restarted_helper_adopts_windows_for_launches_still_starting(self):
        self.open('notepad', 'o-1')
        restarted = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                                 windows=shell.Windows(clock=self.clock), activate=self.activate, clock=self.clock,
                                 executable=lambda path: True)
        windows = restarted.windows
        windows.new(9)
        windows.app_id(9, 'org.kde.kwrite')
        windows.state(9, True)
        windows.done(9)
        restarted.windows_changed()
        self.assertEqual(restarted.journal.entries['o-1']['state'], 'focused')
        self.assertEqual(self.popen.call_count, 1)


class FakeCompositor:
    """Speaks just enough Wayland to drive ForeignToplevels."""
    MANAGER_NAME, SEAT_NAME = 7, 8
    TOPLEVEL = 0xff000000

    def __init__(self, sock):
        self.sock = sock
        self.buffer = b''
        self.requests = []

    @staticmethod
    def message(object_id, opcode, payload=b''):
        return struct.pack('=II', object_id, ((8 + len(payload)) << 16) | opcode) + payload

    def read(self):
        while len(self.buffer) < 8 or len(self.buffer) < struct.unpack_from('=II', self.buffer)[1] >> 16:
            self.buffer += self.sock.recv(65536)
        object_id, word = struct.unpack_from('=II', self.buffer)
        size = word >> 16
        payload, self.buffer = self.buffer[8:size], self.buffer[size:]
        self.requests.append((object_id, word & 0xffff, payload))
        return object_id, word & 0xffff, payload

    def serve(self, toplevels):
        string = shell.ForeignToplevels.string
        object_id, opcode, payload = self.read()
        assert (object_id, opcode) == (1, 1)
        registry = struct.unpack('=I', payload)[0]
        _, _, payload = self.read()
        callback = struct.unpack('=I', payload)[0]
        self.sock.sendall(self.message(registry, 0, struct.pack('=I', 3) + string('wl_compositor') + struct.pack('=I', 6))
                          + self.message(registry, 0, struct.pack('=I', self.MANAGER_NAME)
                                         + string(shell.ForeignToplevels.MANAGER) + struct.pack('=I', 3))
                          + self.message(registry, 0, struct.pack('=I', self.SEAT_NAME) + string('wl_seat')
                                         + struct.pack('=I', 9))
                          + self.message(callback, 0, struct.pack('=I', 0)))
        binds = [self.read(), self.read()]
        manager = struct.unpack_from('=I', binds[0][2], len(binds[0][2]) - 4)[0]
        _, _, payload = self.read()
        callback = struct.unpack('=I', payload)[0]
        events = b''
        for index, (app_id, activated) in enumerate(toplevels):
            handle = self.TOPLEVEL + index
            states = struct.pack('=I', 2) if activated else b''
            events += (self.message(manager, 0, struct.pack('=I', handle))
                       + self.message(handle, 0, string('Title'))
                       + self.message(handle, 1, string(app_id))
                       + self.message(handle, 4, struct.pack('=I', len(states)) + states)
                       + self.message(handle, 7, struct.pack('=I', 0))
                       + self.message(handle, 5))
        self.sock.sendall(events + self.message(callback, 0, struct.pack('=I', 0)))
        return binds


class Wrapped:
    """A connected socket pair end that pretends to connect to the compositor's path."""

    def __init__(self, sock):
        self.sock = sock
        self.path = None

    def connect(self, path):
        self.path = path

    def __getattr__(self, name):
        return getattr(self.sock, name)


class WaylandTest(unittest.TestCase):
    def test_connect_binds_the_manager_and_seat_and_reads_toplevels(self):
        client_end, server_end = socket.socketpair()
        self.addCleanup(client_end.close)
        self.addCleanup(server_end.close)
        compositor = FakeCompositor(server_end)
        result = {}
        thread = threading.Thread(target=lambda: result.update(binds=compositor.serve(
            [('aresos-desktop', True), ('org.kde.kwrite', False)])))
        thread.start()
        windows = shell.Windows()
        wrapped = Wrapped(client_end)
        with mock.patch.object(shell.socket, 'socket', return_value=wrapped), \
                mock.patch.object(shell.socket, 'AF_UNIX', getattr(socket, 'AF_UNIX', 1), create=True):
            client = shell.ForeignToplevels.connect(windows, {'WAYLAND_DISPLAY': 'wayland-1',
                                                             'XDG_RUNTIME_DIR': '/run/user/1001'})
        thread.join(5)
        self.assertEqual(wrapped.path, '/run/user/1001/wayland-1')
        binds = result['binds']
        self.assertIn(shell.ForeignToplevels.MANAGER.encode(), binds[0][2])
        self.assertEqual(struct.unpack_from('=I', binds[0][2])[0], FakeCompositor.MANAGER_NAME)
        self.assertEqual(struct.unpack_from('=I', binds[0][2], len(binds[0][2]) - 8)[0], 3)
        self.assertIn(b'wl_seat', binds[1][2])
        opened, closed = windows.take()
        self.assertEqual([(t.app_id, t.activated) for t in opened], [('aresos-desktop', True), ('org.kde.kwrite', False)])
        self.assertEqual(windows.active().owner, shell.Windows.SHELL)
        self.assertTrue(client.activate(FakeCompositor.TOPLEVEL))
        self.assertEqual(compositor.read(), (FakeCompositor.TOPLEVEL, 4, struct.pack('=I', client.seat)))
        self.assertFalse(client.activate(12345))
        client.feed(FakeCompositor.message(FakeCompositor.TOPLEVEL + 1, 6))
        self.assertEqual([t.app_id for t in windows.take()[1]], ['org.kde.kwrite'])
        self.assertEqual(compositor.read(), (FakeCompositor.TOPLEVEL + 1, 7, b''))
        with self.assertRaises(shell.WaylandError):
            client.feed(FakeCompositor.message(1, 0, struct.pack('=II', 1, 3) + shell.ForeignToplevels.string('boom')))

    def test_a_compositor_without_the_protocol_is_refused(self):
        windows = shell.Windows()
        client_end, server_end = socket.socketpair()
        self.addCleanup(server_end.close)
        client = shell.ForeignToplevels(client_end, windows)
        client.feed(FakeCompositor.message(client.registry, 0, struct.pack('=I', 3)
                                           + shell.ForeignToplevels.string('wl_compositor') + struct.pack('=I', 6)))
        self.assertFalse(client.bind())
        client_end.close()
        with self.assertRaises(shell.WaylandError):
            shell.ForeignToplevels.connect(windows, {})

    def test_split_messages_are_reassembled(self):
        windows = shell.Windows()
        client_end, server_end = socket.socketpair()
        self.addCleanup(client_end.close)
        self.addCleanup(server_end.close)
        client = shell.ForeignToplevels(client_end, windows)
        client.kinds[50] = 'manager'
        data = FakeCompositor.message(50, 0, struct.pack('=I', 0xff000009))
        client.feed(data[:5])
        self.assertEqual(windows.toplevels, {})
        client.feed(data[5:])
        self.assertIn(0xff000009, windows.toplevels)
        with self.assertRaises(shell.WaylandError):
            client.feed(struct.pack('=II', 50, (4 << 16)))


@unittest.skipUnless(sys.platform.startswith('linux'), 'needs Linux Unix sockets and SO_PEERCRED')
class ServerTest(Base):
    def server(self, path):
        helper = self.helper()
        server = shell.Server(path, helper)
        self.addCleanup(server.close)
        return server

    def line(self, client, message):
        client.sendall(json.dumps(dict({'protocol': 'aresos-shell/1.0'}, **message)).encode() + b'\n')

    def receive(self, server, client):
        data = b''
        while not data.endswith(b'\n'):
            server.step(0.05)
            try:
                data += client.recv(65536, socket.MSG_DONTWAIT)
            except BlockingIOError:
                pass
        return json.loads(data)

    def test_private_socket_same_user_hello_and_list(self):
        path = os.path.join(self.folder.name, 'aresos', 'shell.sock')
        server = self.server(path)
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(path)).st_mode), 0o700)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(client.close)
        client.connect(path)
        self.line(client, {'id': 'h-1', 'op': 'hello', 'major': 1, 'minor': 0, 'capabilities': ALL,
                           'instance': INSTANCE, 'nonce': NONCE})
        self.assertTrue(self.receive(server, client)['ok'])
        self.line(client, {'id': 'l-1', 'op': 'list_apps'})
        self.assertEqual({row['id'] for row in self.receive(server, client)['apps']}, {'terminal', 'notepad', 'browser'})
        with self.assertRaises(SystemExit):
            shell.Server(path, self.helper())

    def test_other_users_are_refused_and_stale_sockets_replaced(self):
        path = os.path.join(self.folder.name, 'aresos', 'shell.sock')
        os.makedirs(os.path.dirname(path), mode=0o700)
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale.bind(path)
        stale.close()
        server = self.server(path)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.addCleanup(client.close)
        with mock.patch.object(shell, 'peer_uid', return_value=os.getuid() + 1):
            client.connect(path)
            server.step(0.2)
        self.assertEqual(server.peers, {})
        client.settimeout(2)
        self.assertEqual(client.recv(10), b'')


if __name__ == '__main__':
    unittest.main()
