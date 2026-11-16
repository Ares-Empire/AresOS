"""Package 18c, B2: the pieces of the Control VM test that run without a VM (os/ci/control/, the checks.py hook)."""
import ast
import gzip
import importlib.util
import io
import json
import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTROL_CI = ROOT / 'os/ci/control'


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def layer(home):
    """actions.py and sessions.py as the guest loads them, with a stand-in for the account `ares` (home, this user)."""
    owner = mock.Mock(pw_dir=str(home), pw_uid=os.getuid(), pw_gid=os.getgid())
    paths = [str(ROOT / 'os/ci'), str(ROOT / 'control/boundary'), str(CONTROL_CI)]
    with mock.patch('pwd.getpwnam', return_value=owner), mock.patch.object(sys, 'path', paths + sys.path):
        return (load(CONTROL_CI / 'actions.py', f'control_actions_{id(home)}'),
                load(CONTROL_CI / 'sessions.py', f'control_sessions_{id(home)}'))


class LayerHookTest(unittest.TestCase):
    """Agreed change 8: checks.py loads a later layer's actions from actions.d and keeps its own first."""

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        for name in ('overlay/checks.py', 'channel.py'):
            shutil.copy(ROOT / 'os/ci' / name, self.folder)
        (self.folder / 'actions.d').mkdir()
        sys.path.insert(0, str(self.folder))
        self.addCleanup(sys.path.remove, str(self.folder))

    def checks(self):
        return load(self.folder / 'checks.py', f'checks_{id(self)}')

    def test_a_layer_action_answers_and_an_unknown_one_still_fails(self):
        (self.folder / 'actions.d/control.py').write_text(
            'ACTIONS = {"control-echo": lambda request: dict(returncode=0, echo=request["value"])}\n')
        checks = self.checks()
        self.assertEqual(checks.check('control-echo', {'value': 7}), {'returncode': 0, 'echo': 7})
        with self.assertRaisesRegex(ValueError, 'Unknown check: control-other'):
            checks.check('control-other', {})

    def test_without_a_layer_nothing_is_added(self):
        with self.assertRaisesRegex(ValueError, 'Unknown check: control-files'):
            self.checks().check('control-files', {})

    def test_two_layer_files_cannot_claim_the_same_action(self):
        for name in ('a', 'b'):
            (self.folder / f'actions.d/{name}.py').write_text('ACTIONS = {"same": lambda request: {}}\n')
        with self.assertRaisesRegex(AssertionError, 'repeats an action'):
            self.checks().check('same', {})

    def test_the_control_layer_installs_its_actions_where_the_hook_looks(self):
        containerfile = (CONTROL_CI / 'Containerfile').read_text()
        self.assertIn('FROM localhost/aresos:vm\n', containerfile)
        self.assertIn('COPY os/ci/control/actions.py /usr/libexec/aresos-ci/actions.d/control.py\n', containerfile)
        self.assertNotIn('tls.key', containerfile)
        tree = ast.parse((CONTROL_CI / 'actions.py').read_text())
        actions = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                       and [target.id for target in node.targets] == ['ACTIONS'])
        names = [key.value for key in actions.keys]
        runner = load(CONTROL_CI / 'control_vm.py', 'control_vm_for_test')
        self.assertEqual([action for action, _ in runner.CHECKS], names)
        lines = [line for _, line in runner.CHECKS]
        self.assertEqual(len(set(lines)), len(lines))
        self.assertTrue(all(re.fullmatch('CONTROL_[A-Z_]+', line) for line in lines))


class RunnerInputsTest(unittest.TestCase):
    def test_the_install_step_is_the_readmes_block_word_for_word(self):
        runner = load(CONTROL_CI / 'control_vm.py', 'control_vm_for_readme')
        readme = (ROOT / 'control/README.md').read_text()
        step = runner.install_step(readme)
        self.assertIn('```sh\n' + step + '\n```', readme)
        self.assertTrue(step.startswith("python3 - <<'INSTALL'\n") and step.endswith('\nINSTALL'))
        self.assertIn("'/usr/share/aresos/control/user-mcp.json'", step)
        with self.assertRaises(AssertionError):
            runner.install_step(readme + '\n```sh\n' + step + '\n```\n')

    def test_the_fixtures_are_the_mail_suites_images_and_one_password_line(self):
        run = (ROOT / 'control/ci/mail/run.sh').read_text()
        for pattern in (r'greenmail/standalone:[^ @]+@sha256:[0-9a-f]{64}', r'dovecot/dovecot:[^ @]+@sha256:[0-9a-f]{64}'):
            self.assertEqual(len(re.findall(pattern, run)), 1, pattern)
        conf = (ROOT / 'control/ci/mail/dovecot.conf').read_text().splitlines()
        self.assertEqual(conf.count('  args = password=pass'), 1)
        script = (CONTROL_CI / 'runner.sh').read_text()
        # The names image-checks.sh's negative check knows (step 1, PLAN-GAP 3).
        scan = (ROOT / 'os/ci/image-checks.sh').read_text()
        self.assertIn("names='greenmail dovecot'", script)
        self.assertIn("printf '10.0.2.2 greenmail dovecot\\n'", scan)
        self.assertIn("-subj '/CN=mail-fixture.invalid'", script)
        self.assertIn('${RUNNER_TEMP:-/tmp}/aresos-control-fixtures', script)
        self.assertEqual([arg for arg in re.findall(r' -p (\S+)', script) if not arg.startswith('"$')], ['127.0.0.1:3465:3465', '127.0.0.1:3993:3993',
                                                           '127.0.0.1:993:993'])


class OwnServerTest(unittest.TestCase):
    def test_it_speaks_mcp_over_stdio(self):
        own = load(CONTROL_CI / 'own-mcp.py', 'own_mcp')
        hello = own.answer({'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                            'params': {'protocolVersion': '2025-03-26'}})
        self.assertEqual(hello['result']['protocolVersion'], '2025-03-26')
        self.assertIsNone(own.answer({'jsonrpc': '2.0', 'method': 'notifications/initialized'}))
        self.assertEqual([tool['name'] for tool in own.answer({'id': 2, 'method': 'tools/list'})['result']['tools']],
                         ['note'])
        called = own.answer({'id': 3, 'method': 'tools/call', 'params': {'name': 'note', 'arguments': {'word': 'x'}}})
        self.assertEqual(called['result']['content'], [{'type': 'text', 'text': 'OWN_NOTE x'}])
        self.assertEqual(own.answer({'id': 4, 'method': 'resources/list'})['error']['code'], -32601)


class SessionPiecesTest(unittest.TestCase):
    """Step 2b: his own hooks, the layer's copies of B1's driver and model double, Mail's runner-side fixture."""

    def test_his_hooks_log_every_event_and_only_the_permission_hook_approves(self):
        hook = load(CONTROL_CI / 'own-hook.py', 'own_hook')
        with tempfile.TemporaryDirectory() as folder:
            log = pathlib.Path(folder, 'hooks.jsonl')
            outputs = {}
            for event in ('Stop', 'UserPromptSubmit', 'PermissionRequest'):
                with mock.patch('sys.stdin', new=__import__('io').StringIO(json.dumps({'hook_event_name': event}))), \
                        mock.patch('sys.stdout', new=__import__('io').StringIO()) as out:
                    hook.main(event, str(log))
                outputs[event] = out.getvalue()
            lines = [json.loads(line) for line in log.read_text().splitlines()]
        self.assertEqual([line['event'] for line in lines], ['Stop', 'UserPromptSubmit', 'PermissionRequest'])
        self.assertEqual(outputs['Stop'] + outputs['UserPromptSubmit'], '')
        self.assertEqual(json.loads(outputs['PermissionRequest'])['hookSpecificOutput']['decision'],
                         {'behavior': 'allow'})

    def test_the_layer_carries_the_session_pieces_unchanged(self):
        containerfile = (CONTROL_CI / 'Containerfile').read_text()
        for source in ('os/ci/control/sessions.py', 'os/ci/control/own-hook.py', 'control/boundary/interactive_driver.py',
                       'control/boundary/interactive_model.py', 'control/ci/image/mail_flows.py'):
            self.assertIn(source, containerfile)
            self.assertTrue((ROOT / source).is_file(), source)
        sessions = ast.parse((CONTROL_CI / 'sessions.py').read_text())
        imported = {(node.module, alias.name) for node in ast.walk(sessions) if isinstance(node, ast.ImportFrom)
                    for alias in node.names}
        self.assertEqual(imported, {('interactive_driver', 'Terminal'), ('interactive_driver', 'options'),
                                    ('interactive_model', 'Model'), ('interactive_model', 'texts')})
        actions = (CONTROL_CI / 'actions.py').read_text()
        self.assertIn("'/run/systemd/system/aresos-toold.service.d/aresos-ci-fail.conf'", actions)

    def test_the_seeded_attachment_is_binary_and_named(self):
        fixture = load(ROOT / 'control/ci/image/mail_fixture.py', 'mail_fixture_for_test')
        mail = fixture.message('attachment')
        parts = list(mail.iter_attachments())
        self.assertEqual([part.get_filename() for part in parts], [fixture.ATTACHMENT_NAME])
        self.assertEqual(parts[0].get_payload(decode=True), fixture.attachment_bytes())
        self.assertEqual(len(set(fixture.attachment_bytes())), 256)
        self.assertTrue(mail['Message-ID'].endswith('@mail.invalid>'))
        flows = (ROOT / 'control/ci/image/mail_flows.py').read_text()
        for name in ('USERNAME', 'ADDRESS'):
            self.assertIn(f"{name} = {getattr(fixture, name)!r}", flows)


class EvidencePackingTest(unittest.TestCase):
    """Run 43568250360: check 9's transcripts tar went over the cap and its exception lost the whole record."""

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.actions, self.sessions = layer(self.folder / 'home')

    def test_a_continuation_tail_is_the_newest_user_text(self):
        messages = [{'role': 'user', 'content': 'ORDINARY_OWNER_TURN_04'},
                    {'role': 'assistant', 'content': [{'type': 'text', 'text': 'INTERACTIVE_DONE_4'}]},
                    {'role': 'user', 'content': [{'type': 'text', 'text': 'Stop hook feedback:\n[cmd]: AresOS tools '
                                                  'are not running. If you prepared'}]}]
        tail = self.sessions.last_user_text(messages)
        self.assertIn('AresOS tools are not running', tail)
        self.assertNotIn('TURN_04', tail)
        self.assertEqual(self.sessions.last_user_text([{'role': 'user', 'content': 'x\n  y'}]), 'x y')
        # A session's last turn keeps the long quiet window: nothing after it would see a late continuation.
        self.assertLess(self.sessions.SETTLE_NEXT, self.sessions.SETTLE)

    def case(self, name, size):
        folder = self.folder / name
        (folder / 'screens').mkdir(parents=True)
        (folder / 'screens/001-settled-1.txt').write_text('screen')
        (folder / 'screens/002-wait-1.txt').write_bytes(os.urandom(size))
        return folder

    def test_a_tar_that_does_not_fit_is_left_out_and_named_never_raised(self):
        files, errors = {}, []
        sizes = self.actions.packed(files, {'small.tar.gz': self.case('small', 1000),
                                            'missing.tar.gz': self.folder / 'missing',
                                            'huge.tar.gz': self.case('huge', 0)}, errors)
        self.assertEqual(sorted(files), ['huge.tar.gz', 'small.tar.gz'])
        self.assertEqual(errors, [])
        (self.folder / 'huge/transcript.jsonl').write_bytes(os.urandom(1_200_000))
        files, errors = {}, []
        sizes = self.actions.packed(files, {'small.tar.gz': self.case('small2', 1000),
                                            'huge.tar.gz': self.folder / 'huge'}, errors)
        self.assertEqual(list(files), ['small.tar.gz'])
        self.assertIsNone(sizes['huge.tar.gz'])
        self.assertIn('evidence huge.tar.gz left out', errors[0])

    def test_the_intermediate_screens_go_first_and_the_budget_holds(self):
        files, errors = {}, []
        mock.patch.object(self.actions, 'TARS_BUDGET', 1_500_000).start()
        self.addCleanup(mock.patch.stopall)
        sizes = self.actions.packed(files, {f'{n}.tar.gz': self.case(f'case{n}', 900_000) for n in range(3)}, errors)
        # The first fits whole; what is left of the budget then takes the others only without their intermediate
        # screens, and nothing is left out.
        self.assertEqual(len(files), 3)
        self.assertGreater(sizes['0.tar.gz'], 900_000)
        self.assertTrue(sizes['1.tar.gz'] < 10_000 and sizes['2.tar.gz'] < 10_000, sizes)
        self.assertEqual(errors, [])

    def test_a_turn_sees_only_its_own_lines_on_screen(self):
        # Run 43572578699: the screens of turn 3 still showed turn 2's reminder above turn 3's prompt.
        earlier = ['❯ TURN_2', '● Ran 1 stop hook', '⎿ Stop hook error: AresOS held/unfinished work']
        screens = self.folder / 'screens'
        screens.mkdir()
        for number, name, lines in ((5, 'settled-2', earlier), (6, 'owner-prompt', earlier),
                                    (7, 'wait-prompt-or-done-3', earlier + ['❯ TURN_3', '✶ (running Stop hook)']),
                                    (8, 'settled-3', ['● INTERACTIVE_DONE_3', '⎿ AresOS scrolled into view'])):
            (screens / f'{number:03d}-{name}.txt').write_text('\n'.join(lines))
        self.assertEqual(self.sessions.ours_on_screen(screens, 5, 8, 'TURN_3'),
                         ['✶ (running Stop hook)', '⎿ AresOS scrolled into view'])
        self.assertEqual(self.sessions.ours_on_screen(screens, 4, 5, 'TURN_2'), earlier[1:])

    def test_the_tools_offered_are_counted_per_server(self):
        # Run 43669126392: the first request went out before our servers connected.
        tools = [{'name': 'Bash'}, {'name': 'Read'}, {'name': 'mcp__notes__note'}, {'name': 'mcp__chrome__tabs'},
                 {'name': 'mcp__chrome__read'}]
        self.assertEqual(self.sessions.tools_per_server(tools), {'built-in': 2, 'notes': 1, 'chrome': 2})

    def test_only_the_transcripts_a_case_wrote_are_copied(self):
        source = self.folder / 'projects/work'
        source.mkdir(parents=True)
        (source / 'old.jsonl').write_text('{"check": 6}\n')
        (source / 'kept.jsonl').write_text('{"check": 7}\n')
        mock.patch.object(self.sessions, 'TRANSCRIPTS', self.folder / 'projects').start()
        self.addCleanup(mock.patch.stopall)
        before = self.sessions.transcript_files()
        (source / 'new.jsonl').write_text('{"check": 9}\n')
        with open(source / 'old.jsonl', 'a') as stream:
            stream.write('{"check": 9}\n')
        copied = self.sessions.transcripts(self.folder / 'out', before)
        self.assertEqual([row['name'] for row in copied], ['work/new.jsonl', 'work/old.jsonl'])
        self.assertFalse((self.folder / 'out/work/kept.jsonl').exists())


class ServiceModesTest(unittest.TestCase):
    """Check 2 expects the socket folder's and sockets' modes the merged daemon.py sets, read from daemon.py itself
    (step 2a assumed chrome.sock 0600; PR #27 made it 0666)."""

    def constant(self, name):
        tree = ast.parse((CONTROL_CI / 'actions.py').read_text())
        return next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == [name])

    def test_the_socket_modes_are_the_ones_daemon_py_sets(self):
        tree = ast.parse((ROOT / 'control/aresos_control/daemon.py').read_text())
        daemon = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Daemon')
        init = next(node for node in daemon.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        loop = next(node for node in ast.walk(init) if isinstance(node, ast.For) and ast.unparse(node.target) == 'kind')
        chmod = [node for node in ast.walk(loop) if isinstance(node, ast.Call) and ast.unparse(node.func) == 'os.chmod']
        self.assertEqual(len(chmod), 1)
        expression = chmod[0].args[1]
        # Only the loop's kind decides the mode: a constant, or a choice between constants by kind.
        self.assertEqual({node.id for node in ast.walk(expression) if isinstance(node, ast.Name)}, {'kind'})
        mode = compile(ast.Expression(expression), 'daemon.py', 'eval')
        sockets = {f'{kind}.sock': eval(mode, {'__builtins__': {}}, {'kind': kind})
                   for kind in ast.literal_eval(loop.iter)}
        self.assertEqual(sockets, self.constant('SOCKET_MODES'))
        folder = [keyword.value for node in ast.walk(init) if isinstance(node, ast.Call)
                  and ast.unparse(node.func) == 'directory.mkdir' for keyword in node.keywords if keyword.arg == 'mode']
        self.assertEqual([ast.literal_eval(value) for value in folder], [self.constant('SOCKET_FOLDER_MODE')])
        self.assertEqual(sockets, {'act.sock': 0o666, 'admin.sock': 0o600, 'chrome.sock': 0o666})


class ServiceFixesTest(unittest.TestCase):
    """What the VM pass expects from 18e (PR #69), read from the sources that make it, so a change there fails here
    until the check follows."""

    def constant(self, name):
        tree = ast.parse((CONTROL_CI / 'actions.py').read_text())
        return next(ast.literal_eval(node.value) for node in tree.body
                    if isinstance(node, ast.Assign) and [ast.unparse(t) for t in node.targets] == [name])

    def test_check_2_pins_the_units_start_limit(self):
        unit = (ROOT / 'control/packaging/aresos-toold.service').read_text().splitlines()
        section = unit[unit.index('[Unit]'):unit.index('[Service]')]
        sandbox = self.constant('SANDBOX')
        self.assertIn(f"StartLimitIntervalSec={sandbox['StartLimitIntervalUSec'].removesuffix('s')}", section)
        self.assertIn(f"StartLimitBurst={sandbox['StartLimitBurst']}", section)

    def test_the_admin_hint_and_the_refusal_are_the_services_texts(self):
        sys.path.insert(0, str(ROOT / 'control'))
        self.addCleanup(sys.path.remove, str(ROOT / 'control'))
        from aresos_control.common import Refused
        from aresos_control.files import FilePolicy
        build = (ROOT / 'os/build.sh').read_text()
        folders = ast.literal_eval(re.search(r'^FOLDERS = (.+)$', build, re.M)[1])
        policy = FilePolicy('/var/home/ares', [f'/var/home/ares/{name}' for name in folders])
        with self.assertRaises(Refused) as refusal:
            policy.locate('/var/home/ares/outside-ci.bin')
        self.assertEqual((refusal.exception.code, str(refusal.exception)), ('file_refused', self.constant('OUTSIDE_REFUSAL')))
        cli = (ROOT / 'control/aresos_control/cli.py').read_text()
        self.assertIn('"Admin commands need sudo: run sudo aresos admin " + " ".join(command) + " (same options)."', cli)
        self.assertEqual(self.constant('ADMIN_HINT'), 'Admin commands need sudo: run sudo aresos admin '
                         + ' '.join(['testapp', 'fixture_configure']) + ' (same options).')

    def test_check_6_lets_the_unit_fail_by_its_start_limit(self):
        actions = (CONTROL_CI / 'actions.py').read_text()
        drop_in = re.search(r"DROP_IN\.write_text\((.+?)\)\n", actions, re.S)[1]
        self.assertIn('ExecStartPre=/usr/bin/false', drop_in)
        self.assertNotIn('Restart=', drop_in)

    def test_check_6s_turns_are_found_by_unique_prompts(self):
        tree = ast.parse((CONTROL_CI / 'actions.py').read_text())
        turns = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                     and [ast.unparse(t) for t in node.targets] == ['ORDINARY_TURNS'])
        rows = [[ast.unparse(item) for item in row.elts] for row in turns.elts]
        prompts = [f'ORDINARY_OWNER_TURN_{number:02}' for number in range(1, len(rows) + 1)]
        self.assertTrue(all(a == b or a not in b for a in prompts for b in prompts))
        self.assertIn('ORDINARY_OWNER_TURN_{number:02}', (CONTROL_CI / 'actions.py').read_text())
        notices = [row[3] for row in rows]
        self.assertEqual(notices.count('1'), 2)
        # A session's done markers (INTERACTIVE_DONE_<n>) stay unique while it has fewer than ten turns.
        sessions = [row[0] for row in rows]
        self.assertLess(max(sessions.count(name) for name in set(sessions)), 10)


class FixRoundOneTest(unittest.TestCase):
    """Fix round 1 (REVIEW-A1 #1, #5, #7, #9; SECURITY-REVIEW-A1 F1): what the VM pass now requires, without a VM."""

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.actions, self.sessions = layer(self.folder / 'home')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'reads /proc')
    def test_check_2_sees_a_listening_socket_and_an_unconnected_udp_one(self):
        # REVIEW-A1 #7: the unit allows AF_INET/AF_INET6; check 2 requires that the service holds no listener.
        import socket
        before, _ = self.actions.listening_sockets([os.getpid()])
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as tcp, \
                socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp, \
                socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as connected, \
                socket.socket(socket.AF_INET, socket.SOCK_STREAM) as unbound:
            tcp.bind(('127.0.0.1', 0))
            tcp.listen(1)
            udp.bind(('127.0.0.1', 0))
            connected.connect(('127.0.0.1', udp.getsockname()[1]))
            found, held = self.actions.listening_sockets([os.getpid()])
            new = [item for item in found if item not in before]
            ports = {(item['kind'], int(item['local'].rsplit(':', 1)[1], 16)) for item in new}
            self.assertEqual(ports, {('tcp', tcp.getsockname()[1]), ('udp', udp.getsockname()[1])})
            self.assertGreaterEqual(held, 4)
        self.assertEqual(self.actions.listening_sockets([os.getpid()])[0], before)
        with self.assertRaises(OSError):
            self.actions.listening_sockets([2 ** 22 + 1])  # no such process: an error, never "no listener"
        source = (CONTROL_CI / 'actions.py').read_text()
        service = source[source.index('def service(request):'):source.index('# Step 2b')]
        self.assertIn("network = network_listeners(properties['ControlGroup'])", service)
        self.assertIn("'-l', '-n', '-t', '-u', '-p'", source)

    def test_check_6_runs_four_sessions_and_leaves_held_work_beside_a_fresh_one(self):
        # SECURITY-REVIEW-A1 F1: a No leaves the send reserved; a fresh session that never used the tools follows.
        turns = self.actions.ORDINARY_TURNS
        self.assertTrue(all(len(row) == 5 for row in turns))
        self.assertEqual([row[0] for row in turns if row[0] in ('held-work', 'fresh-beside-held')],
                         ['held-work', 'fresh-beside-held'])
        self.assertEqual([row[-2:] for row in turns[-2:]], [(0, 'No'), (0, None)])
        self.assertEqual([row[2] for row in turns[-2:]], [self.actions.PREPARED, self.actions.NOTE])
        # Only our ask gets an answer; his own tool and testapp's list never ask.
        self.assertTrue(all((row[4] is not None) == (row[2] == self.actions.PREPARED) for row in turns))
        self.assertEqual(sorted({row[0] for row in turns}),
                         ['failed-fresh-session', 'fresh-beside-held', 'held-work', 'used-later'])
        source = (CONTROL_CI / 'actions.py').read_text()
        self.assertIn("('held-work', clean_baseline, None), ('fresh-beside-held', note_held, None)", source)
        # The driver's resume prompt after a No belongs to the turn it resumes (his hooks' lines per turn).
        self.assertIn('RESUME', (CONTROL_CI / 'sessions.py').read_text())
        self.assertIn("sessions.RESUME not in line['input'].get('prompt', '')", source)
        self.assertNotIn('INTERACTIVE_RESUME_CURRENT_TURN', source)

    def test_the_held_work_is_released_as_check_9_releases_its_cases(self):
        calls = []

        def cli(user, *argv, value=None):
            calls.append(argv)
            if argv == ('testapp', 'operation_status'):
                return {'returncode': 0, 'json': {'ok': True, 'data': {'operation': {'state': 'reserved'}}}}
            if argv == ('testapp', 'operation_cancel'):
                return {'returncode': 0, 'json': {'ok': True, 'data': {'operation': {'state': 'failed'}}}}
            if argv == ('testapp', 'notice_ack'):
                return {'returncode': 0, 'json': {'ok': True, 'data': {}}}
            pending = 1 if ('testapp', 'notice_ack') not in calls else 0
            return {'returncode': 0, 'json': {'ok': True, 'data': {'total': pending}}}
        with mock.patch.object(self.actions, 'cli', side_effect=cli):
            released = self.actions.release_held('op-1')
        self.assertEqual(released, {'state': 'reserved', 'cancelled': 'failed', 'notice_ack': {'ok': True, 'data': {}},
                                    'pending_after': 0})
        self.assertIn('released = release_held(op_id)', (CONTROL_CI / 'actions.py').read_text())

    def test_the_desktop_comes_up_again_as_at_boot_with_the_service_failed(self):
        # REVIEW-A1 #1 (agreed change 6). greetd runs its auto-login once per boot, recorded in its runfile, so the
        # check removes it before greetd starts again; the session is then required by the CI layer's own checks.
        config = (ROOT / 'os/config/etc/greetd/config.toml').read_text()
        self.assertIn('[initial_session]\ncommand = "/usr/bin/aresos-session"\nuser = "ares"', config)
        self.assertNotIn('runfile', config)  # greetd's default, which the check names
        self.assertEqual(self.actions.GREETD_RUNFILE, pathlib.Path('/run/greetd.run'))
        source = (CONTROL_CI / 'actions.py').read_text()
        restart = source[source.index('def desktop_with_service_failed('):source.index('def ordinary(request):')]
        order = [restart.index(text) for text in (
            "'systemctl', 'stop', 'greetd.service'", "'loginctl', 'terminate-user', 'ares'",
            'GREETD_RUNFILE.unlink(', "'systemctl', 'start', 'greetd.service'", 'checks.wait_session()',
            'checks.desktop_session()')]
        self.assertEqual(order, sorted(order))
        checks = ast.parse((ROOT / 'os/ci/overlay/checks.py').read_text())
        defined = {node.name for node in checks.body if isinstance(node, ast.FunctionDef)}
        self.assertLessEqual({'wait_session', 'desktop_session'}, defined)
        # Armed first, then the desktop, then the fresh session (agreed change 6: "armed before a fresh session").
        arm = source[source.index('    def arm_failure(first):'):source.index('    def clean_baseline(first):')]
        self.assertLess(arm.index('wait_failed()'), arm.index('desktop_with_service_failed('))

    def test_the_static_checks_cover_the_runner_and_the_mail_flows(self):
        # REVIEW-A1 #9: a typo in these showed only in a 50-minute control run.
        for script in sorted(CONTROL_CI.glob('*.sh')):
            result = subprocess.run(['bash', '-n', str(script)], capture_output=True, text=True, timeout=60)
            self.assertEqual(result.returncode, 0, (script.name, result.stderr))
        sources = sorted([*CONTROL_CI.glob('*.py'), *(ROOT / 'control/ci/image').glob('*.py')])
        self.assertIn(ROOT / 'control/ci/image/mail_flows.py', sources)
        self.assertIn(CONTROL_CI / 'runner.sh', list(CONTROL_CI.glob('*.sh')))
        for source in sources:
            py_compile.compile(str(source), cfile=str(self.folder / 'compiled.pyc'), doraise=True)


class EvidenceScanTest(unittest.TestCase):
    """REVIEW-A1 #5: the password checks read inside the evidence's archives; only GreenMail's log is redacted."""
    SECRET = b'0123456789abcdef0123456789abcdef'

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.scan = load(CONTROL_CI / 'evidence_scan.py', 'evidence_scan_for_test')
        self.evidence = self.folder / 'evidence'
        (self.evidence / 'control/ordinary').mkdir(parents=True)
        (self.evidence / 'control/fixtures').mkdir(parents=True)
        (self.evidence / 'control/clean.json').write_text('{"password_sha256": "x"}')

    def tar(self, path, members, compress='gz'):
        with tarfile.open(path, f'w:{compress}' if compress else 'w') as archive:
            for name, data in members.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))

    def test_a_password_inside_a_tar_gz_is_found_and_named_by_its_member(self):
        self.tar(self.evidence / 'control/ordinary/used-later.tar.gz',
                 {'used-later/screens/001.txt': b'nothing', 'used-later/model/requests.json': b'[' + self.SECRET + b']'})
        self.tar(self.evidence / 'control/ordinary/clean.tar.gz', {'clean/screens/001.txt': b'nothing'})
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['holding'], ['control/ordinary/used-later.tar.gz'])
        self.assertIn('control/ordinary/used-later.tar.gz!gunzip!used-later/model/requests.json', found['hits'])
        self.assertEqual(found['files'], 3)
        # A raw byte search over the archive, as before this round, cannot see it.
        self.assertNotIn(self.SECRET, (self.evidence / 'control/ordinary/used-later.tar.gz').read_bytes())

    def test_plain_tars_gzip_files_and_archives_in_archives_are_read(self):
        inner = self.folder / 'inner.tar.gz'
        self.tar(inner, {'deep.txt': self.SECRET})
        self.tar(self.evidence / 'control/outer.tar', {'inner.tar.gz': inner.read_bytes()}, compress=None)
        (self.evidence / 'control/log.gz').write_bytes(gzip.compress(b'x' + self.SECRET))
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['holding'], ['control/log.gz', 'control/outer.tar'])
        self.assertIn('control/outer.tar!inner.tar.gz!gunzip!deep.txt', found['hits'])

    def test_an_archive_that_cannot_be_read_counts_as_holding_it(self):
        (self.evidence / 'control/broken.tar.gz').write_bytes(gzip.compress(os.urandom(4096))[:-100])
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['holding'], ['control/broken.tar.gz'])
        self.assertEqual(found['hits'], [])
        self.assertIn('control/broken.tar.gz: gzip', found['unreadable'][0])

    def test_the_runner_redacts_greenmail_only_and_fails_on_dovecot(self):
        password = self.folder / 'password'
        password.write_bytes(self.SECRET)
        fixtures = self.evidence / 'control/fixtures'
        (fixtures / 'greenmail.txt').write_bytes(b'Created user login ci-owner with password ' + self.SECRET + b'\n')
        (fixtures / 'dovecot.txt').write_bytes(b'auth ok\n')
        with mock.patch('builtins.print') as printed:
            code = self.scan.main(['--redact', str(fixtures / 'greenmail.txt'), '--remove', str(password),
                                   str(self.evidence)])
        report = json.loads(printed.call_args.args[0])
        self.assertEqual((code, report['redacted'], report['holding']), (0, {'greenmail.txt': 1}, []))
        self.assertIn(b'[fixture password redacted]', (fixtures / 'greenmail.txt').read_bytes())
        # Dovecot's log is never redacted: one occurrence fails the step and the file goes.
        (fixtures / 'dovecot.txt').write_bytes(b'auth: ' + self.SECRET + b'\n')
        with mock.patch('builtins.print') as printed:
            code = self.scan.main(['--redact', str(fixtures / 'greenmail.txt'), '--remove', str(password),
                                   str(self.evidence)])
        report = json.loads(printed.call_args.args[0])
        self.assertEqual((code, report['removed']), (1, ['control/fixtures/dovecot.txt']))
        self.assertFalse((fixtures / 'dovecot.txt').exists())
        self.assertNotIn(self.SECRET.decode(), printed.call_args.args[0])

    def test_runner_and_control_vm_use_the_scanner_and_redact_only_greenmail(self):
        runner = (CONTROL_CI / 'runner.sh').read_text()
        stop = runner[runner.index('    stop)'):]
        self.assertIn('evidence_scan.py --redact "$evidence/greenmail.txt" --remove', stop)
        self.assertNotIn('dovecot.txt', stop)
        self.assertNotIn('grep -rlF', stop)
        control_vm = (CONTROL_CI / 'control_vm.py').read_text()
        self.assertIn('evidence_scan.scan(evidence, mail_fixture.password().encode())', control_vm)
        self.assertNotIn('path.read_bytes()', control_vm)


class ReleaseChecksTest(unittest.TestCase):
    """Agreed change 12: the rehearsal's checks, on a stand-in root."""

    def setUp(self):
        self.module = load(CONTROL_CI / 'release_checks.py', 'release_checks')
        self.root = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root)
        files = {}
        for name in ('managed-settings.json', 'CLAUDE.md'):
            for folder in ('etc', 'usr/etc'):
                path = self.root / folder / 'claude-code' / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(name)
                path.chmod(0o644)
            files[f'/etc/claude-code/{name}'] = dict(mode='0644', sha256=self.module.sha256(path))
        record = self.root / self.module.RECORD
        record.parent.mkdir(parents=True)
        record.write_text(json.dumps(dict(files=files)))
        self.folders = [str(self.root / 'home/Downloads'), str(self.root / 'home/Documents')]
        config = self.root / self.module.SERVICE_CONFIG
        config.parent.mkdir(parents=True)
        config.write_text(json.dumps(dict(owner_uid=os.getuid())))
        (self.root / self.module.PROXY_CONFIG).write_text(json.dumps(dict(
            folders=[f.removeprefix(str(self.root)) for f in self.folders])))
        mock.patch.object(self.module, 'ROOT', self.root).start()
        self.addCleanup(mock.patch.stopall)

    def test_the_managed_files_must_equal_the_images_copy(self):
        ok, value = self.module.claude_code_files()
        rows = value['files'].values()
        # Owned by the tester here, so only the owner check fails; the contents agree.
        self.assertFalse(ok)
        self.assertTrue(all(row['sha256'] == row['image_sha256'] == row['recorded'] for row in rows))
        (self.root / 'etc/claude-code/CLAUDE.md').write_text('changed locally')
        ok, value = self.module.claude_code_files()
        row = value['files']['/etc/claude-code/CLAUDE.md']
        self.assertNotEqual(row['sha256'], row['image_sha256'])
        (self.root / 'etc/claude-code/managed-mcp.json').write_text('{}')
        self.assertTrue(self.module.claude_code_files()[1]['managed_mcp'])

    def test_the_folders_must_exist_as_the_owners(self):
        # Where the shipped configuration keeps them (run 43556905450 read the wrong file).
        self.assertIn('owner_uid', json.loads((ROOT / 'control/settings/service.json').read_text()))
        self.assertIn('folders', json.loads((ROOT / 'control/settings/proxy.json').read_text()))
        ok, value = self.module.folders()
        self.assertFalse(ok)
        for folder in self.folders:
            os.makedirs(folder)
        self.assertTrue(self.module.folders()[0])

    def test_every_check_runs_and_a_failure_is_named(self):
        with mock.patch('builtins.print') as printed:
            self.assertEqual(self.module.main(['claude_code_files', 'folders']), 1)
        lines = [call.args[0] for call in printed.call_args_list]
        self.assertEqual(sorted(json.loads(lines[0])), ['claude_code_files', 'folders'])
        self.assertEqual(lines[1], 'CONTROL_RELEASE_CHECKS_FAILED claude_code_files folders')
        with self.assertRaises(SystemExit):
            self.module.main(['nonsense'])
        self.assertEqual(list(self.module.CHECKS),
                         ['service_user', 'unit', 'claude_code_files', 'folders', 'state_folders'])


if __name__ == '__main__':
    unittest.main()
