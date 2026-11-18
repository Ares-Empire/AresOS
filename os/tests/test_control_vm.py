"""Package 18c, B2: the pieces of the Control VM test that run without a VM (os/ci/control/, the checks.py hook)."""
import ast
import contextlib
import gzip
import importlib.util
import io
import json
import os
import pathlib
import pwd
import py_compile
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import types
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
        # What the CI layer puts beside checks.py and it imports (os/ci/overlay/Containerfile; console_keymap.py
        # since package 50).
        for name in ('overlay/checks.py', 'channel.py', 'overlay/console_keymap.py'):
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


class ChromePassTest(unittest.TestCase):
    """Brief 18c-b, item 5: the Chrome pass's pieces that run without a VM."""

    def actions(self):
        return load(CONTROL_CI / 'chrome_actions.py', f'chrome_actions_{id(self)}')

    def test_the_layer_installs_the_chrome_actions_and_the_runner_asks_each_once(self):
        containerfile = (CONTROL_CI / 'Containerfile').read_text()
        self.assertIn('COPY os/ci/control/chrome_actions.py /usr/libexec/aresos-ci/actions.d/chrome.py\n', containerfile)
        self.assertIn('RUN python3 -I -B /tmp/aresos-ci-chrome/chrome_layer.py /tmp/aresos-ci-chrome', containerfile)
        tree = ast.parse((CONTROL_CI / 'chrome_actions.py').read_text())
        actions = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                       and [target.id for target in node.targets] == ['ACTIONS'])
        names = [key.value for key in actions.keys]
        runner = load(CONTROL_CI / 'control_vm.py', 'control_vm_for_chrome')
        acts = [step for step in runner.CHROME_STEPS if step[0] == 'act']
        self.assertEqual([step[1] for step in acts], names)
        lines = [step[2] for step in acts if step[2]]
        self.assertEqual(len(set(lines)), len(lines))
        self.assertTrue(all(re.fullmatch('CONTROL_CHROME_[A-Z_]+', line) for line in lines))
        # The probe comes first and the last step carries a line, so no part is left without one.
        self.assertEqual(acts[0][1], 'chrome-polkit-start')
        self.assertTrue(acts[-1][2])
        self.assertEqual([step for step in runner.CHROME_STEPS if step[0] == 'reboot'], [('reboot',)])
        self.assertFalse(set(names) & {action for action, _ in runner.CHECKS})
        script = (ROOT / 'os/ci/check-build.sh').read_text()
        self.assertIn('sudo -E python3 os/ci/control/control_vm.py chrome\n        echo CHECK_BUILD_CONTROL_CHROME_PASSED',
                      script)

    def test_pkcheck_runs_under_the_units_own_sandbox(self):
        chrome = self.actions()
        properties = chrome.sandbox_properties((ROOT / 'control/packaging/aresos-toold.service').read_text())
        self.assertIn('User=aresos-tools', properties)
        self.assertIn('ProtectSystem=strict', properties)
        self.assertIn('ReadWritePaths=/run/aresos-tools /var/lib/aresos-tools /var/lib/aresos-operation-evidence',
                      properties)
        self.assertIn('CapabilityBoundingSet=', properties)
        self.assertFalse([p for p in properties if p.split('=', 1)[0] in ('ExecStart', 'Type', 'Restart', 'RestartSec')])
        self.assertFalse([p for p in properties if p.startswith(('StartLimit', 'Description', 'WantedBy'))])
        with mock.patch.object(chrome, 'UNIT_FILE', ROOT / 'control/packaging/aresos-toold.service'):
            command = chrome.as_service('probe', ['/usr/bin/pkcheck', '--action-id', 'x'])
        self.assertEqual(command[:2], ['systemd-run', '--unit=probe'])
        self.assertEqual(command[-4:], ['--', '/usr/bin/pkcheck', '--action-id', 'x'])
        self.assertIn('--property=User=aresos-tools', command)
        self.assertIn('--setenv=PATH=/usr/bin:/bin', command)

    def test_the_placeholder_and_the_message_are_read_from_the_installed_files(self):
        chrome = self.actions()
        tmpfiles = (ROOT / 'control/chrome/packaging/aresos-control-chrome.tmpfiles').read_text()
        self.assertEqual(chrome.placeholder(tmpfiles), b'{"format":0,"hosts":[]}')
        with self.assertRaises(chrome.Failure):
            chrome.placeholder(tmpfiles.replace('f /var/lib', 'f /var/other'))
        source = (ROOT / 'control/aresos_control/chrome/exclusions.py').read_text()
        message = chrome.settings_message(source)
        self.assertTrue(message.startswith('Chrome refuses reads and actions:'), message)
        self.assertIn('not a valid list', message)
        self.assertIn(chrome.EMPTY_LIST.strip(), tmpfiles.encode())

    def test_the_probe_host_moves_its_two_paths_to_the_run_folder(self):
        layer = load(CONTROL_CI / 'chrome_layer.py', 'chrome_layer_for_test')
        text = layer.probe_host(ROOT / 'control/chrome/ci/install/probe_host.py')
        self.assertIn("SOCKET = '/run/aresos-install-test/probe.sock'", text)
        self.assertIn("LOG = '/run/aresos-install-test/probe.jsonl'", text)
        self.assertNotIn('/out/', text)
        broken = self.folder / 'probe_host.py'
        broken.write_text(text)
        with self.assertRaises(AssertionError):
            layer.probe_host(broken)
        self.assertEqual(self.actions().RUN, pathlib.Path(layer.RUN))

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)


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

    def test_a_missing_evidence_folder_fails_and_is_named(self):
        # REVIEW-X1 #4: the packer skipped an absent folder, so check 9 could pass without its transcripts.
        files, errors = {}, []
        sizes = self.actions.packed(files, {'interactive/normal-yes.tar.gz': self.case('normal-yes', 1000),
                                            'interactive/normal-yes-transcripts.tar.gz':
                                                self.folder / 'normal-yes-transcripts'}, errors)
        self.assertEqual(list(files), ['interactive/normal-yes.tar.gz'])
        self.assertIsNone(sizes['interactive/normal-yes-transcripts.tar.gz'])
        self.assertEqual(errors, [f'evidence interactive/normal-yes-transcripts.tar.gz missing: no folder '
                                  f'{self.folder}/normal-yes-transcripts'])

    def test_check_9_fails_without_its_transcripts(self):
        # REVIEW-X1 #4: a case that ran must leave its own transcripts, and a copy that fails fails the check.
        evidence = self.folder / 'evidence'
        settings = self.folder / 'managed-settings.json'
        settings.write_text('{}')
        record = self.folder / 'control.json'
        record.write_text(json.dumps({'files': {str(settings): {'sha256': self.actions.sha256(settings)}}}))
        transcripts = self.folder / 'projects'

        def session(out, steps, mode, answers):
            (out / 'model').mkdir(parents=True)
            (out / 'model/requests.json').write_text('[]')
            return dict(turns=[dict(operation_id=f'op-{out.name}', prompt_shown=True, tool_result=None)],
                        owner_answers=1, continuations=[{'messages': [self.actions.REMINDER]}])

        def copy(target, before):
            # What sessions.transcripts() does with this case's transcripts, by `mode` below.
            if mode == 'raises':
                raise OSError('disk full')
            if mode == 'none':
                return []
            (target / 'work').mkdir(parents=True)
            (target / 'work/session.jsonl').write_text('{}')
            return [dict(name='work/session.jsonl', bytes=2)]

        sessions = mock.Mock(WORK=self.folder / 'work', SKIP='skip', NORMAL='normal', session=session,
                             transcripts=copy, transcript_files=dict, hook_lines=lambda log: [],
                             user_settings=lambda *rules: {'rules': list(rules[0])}, own_hook=lambda *a, **k: {})
        (self.folder / 'work').mkdir()

        def arrivals(op_id):
            return (1, {name: 1 for name in ('alpha', 'beta', 'hidden')}, 3) if op_id == 'op-normal-yes' else (0, {}, 0)

        def status(op_id):
            done = op_id == 'op-normal-yes'
            return {'operation': {'state': 'done' if done else 'reserved'},
                    'arrivals': ['alpha', 'beta', 'hidden'] if done else []}

        for name, value in (('layer_modules', lambda: (sessions, None)), ('wait_active', lambda: {}),
                            ('wait_sockets', lambda: ({'total': 0}, [])), ('EVIDENCE', evidence),
                            ('MANAGED_SETTINGS', settings), ('RECORD', record), ('arrivals_in_receiver', arrivals),
                            ('operation', status), ('release_held', lambda op_id: {'pending_after': 0}),
                            ('cli', lambda *argv, value=None: {'returncode': 0, 'json': {'ok': True,
                                                                                         'data': {'total': 0}}})):
            mock.patch.object(self.actions, name, value).start()
        self.addCleanup(mock.patch.stopall)
        expected = dict(send_arrivals=0, hook_calls=0, owner_answers=1)
        request = {'expected': {'normal-permission-user': expected}}
        mode = 'copied'
        passed = self.actions.interactive(request)
        self.assertEqual(passed['returncode'], 0, passed['stderr'])
        self.assertEqual(passed['summary']['transcripts']['normal-yes'], [{'name': 'work/session.jsonl', 'bytes': 2}])
        for mode, message in (('none', 'normal-yes: Claude Code wrote no transcript in this case'),
                              ('raises', 'normal-yes: transcripts not copied: OSError: disk full')):
            shutil.rmtree(evidence)
            failed = self.actions.interactive(request)
            self.assertEqual(failed['returncode'], 1, mode)
            self.assertIn(message, failed['stderr'], mode)
            self.assertIn('evidence interactive/normal-permission-user-transcripts.tar.gz missing', failed['stderr'],
                          mode)

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
        # Since 18e's fix round 2 (main): __init__'s loop makes each socket with listen(directory, kind), which binds
        # a temporary name, chmods it to SOCKET_MODES[kind] and renames it into place.
        tree = ast.parse((ROOT / 'control/aresos_control/daemon.py').read_text())
        daemon = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'Daemon')
        init = next(node for node in daemon.body if isinstance(node, ast.FunctionDef) and node.name == '__init__')
        loop = next(node for node in ast.walk(init) if isinstance(node, ast.For) and ast.unparse(node.target) == 'kind')
        calls = [ast.unparse(node) for node in ast.walk(loop) if isinstance(node, ast.Call)]
        self.assertIn('listen(directory, kind)', calls)
        listen = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'listen')
        chmod = [node for node in ast.walk(listen)
                 if isinstance(node, ast.Call) and ast.unparse(node.func) == 'os.chmod']
        self.assertEqual([ast.unparse(node.args[1]) for node in chmod], ['SOCKET_MODES[kind]'])
        modes = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                     and [ast.unparse(t) for t in node.targets] == ['SOCKET_MODES'])
        sockets = {f'{kind}.sock': modes[kind] for kind in ast.literal_eval(loop.iter)}
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

    def test_check_6s_held_work_texts_are_the_merged_hooks(self):
        # 18e fix round 2: the Stop reason and the prompt context end with REMINDER right after the held work's JSON.
        sys.path.insert(0, str(ROOT / 'control'))
        self.addCleanup(sys.path.remove, str(ROOT / 'control'))
        from aresos_control import hooks
        self.assertEqual(self.constant('HELD_REMINDER'), hooks.REMINDER)
        self.assertTrue(hooks.NOT_RUNNING.startswith(self.constant('NOT_RUNNING')))
        pending = {'items': [{'id': 'op-1', 'state': 'reserved'}], 'total': 1, 'cursor': None}
        reason = hooks.output({'hook_event_name': 'Stop'}, pending)['reason']
        prompt = hooks.output({'hook_event_name': 'UserPromptSubmit'}, pending)
        context = prompt['hookSpecificOutput']['additionalContext']
        for text in (reason, context):
            self.assertTrue(text.startswith(self.constant('REMINDER')), text)
            self.assertTrue(text.endswith('}' + self.constant('HELD_REMINDER')), text)
        folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, folder)
        actions, sessions = layer(folder / 'home')
        # The continuation's newest user text, as check 6 reads it, holds the reason's end.
        tail = sessions.last_user_text([{'role': 'user', 'content': 'ORDINARY_OWNER_TURN_12'},
                                        {'role': 'user', 'content': [{'type': 'text', 'text': 'Stop hook feedback:\n'
                                                                      '[cmd]: ' + reason}]}])
        self.assertIn('}' + actions.HELD_REMINDER, tail)
        # The prompt context: the first request carrying held work is the resume prompt's, in the merged wording.
        path = folder / 'requests.json'

        def first_carrying(*messages):
            path.write_text(json.dumps([{'messages': [{'role': 'user', 'content': 'ORDINARY_OWNER_TURN_12'}]},
                                        *({'messages': [message]} for message in messages)]))
            return actions.held_context(path, sessions.RESUME)
        resume = {'role': 'user', 'content': [{'type': 'text', 'text': context},
                                              {'type': 'text', 'text': sessions.RESUME}]}
        old = {'role': 'user', 'content': [{'type': 'text', 'text': context.removesuffix(hooks.REMINDER)},
                                           {'type': 'text', 'text': sessions.RESUME}]}
        stop_only = {'role': 'user', 'content': [{'type': 'text', 'text': reason}]}
        self.assertTrue(first_carrying(resume, stop_only))
        self.assertFalse(first_carrying(old, stop_only))          # the wording before fix round 2
        self.assertFalse(first_carrying(stop_only, resume))       # the held work first reached it at a stop
        self.assertFalse(actions.held_context(folder / 'missing.json', sessions.RESUME))
        source = (CONTROL_CI / 'actions.py').read_text()
        self.assertIn("expect(row['reminder_in_stop_reason'] and row['reminder_in_prompt_context'], "
                      "'the held-work wording', row)", source)

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


class PasswordScanTest(unittest.TestCase):
    """REVIEW-X1 #2: check 8 passes only when it searched everything: every file, every folder, the whole journal."""
    NEEDLE = b'0123456789abcdef0123456789abcdef'

    def setUp(self):
        self.folder = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(self.cleanup)
        self.actions, _ = layer(self.folder / 'home')
        # search_for() imports tree_scan from the layer's folder, as in the guest: the same module object here.
        mock.patch.object(sys, 'path', [str(CONTROL_CI)] + sys.path).start()
        self.addCleanup(mock.patch.stopall)
        self.scanner = importlib.import_module('tree_scan')
        self.vanishing = self.scanner.VANISHING
        # This folder is under /tmp, a runtime folder in the guest: here nothing may vanish unless a test says so.
        mock.patch.object(self.scanner, 'VANISHING', ('/nothing-vanishes-here/',)).start()
        self.root = self.folder / 'scanned'
        (self.root / 'state').mkdir(parents=True)
        (self.root / 'state/password').write_bytes(b'x' + self.NEEDLE)
        (self.root / 'state/clean.txt').write_text('nothing\n')
        # The layer's folder is the checkout's; the journal is a stand-in.
        mock.patch.object(self.actions, 'HERE', CONTROL_CI).start()
        mock.patch.object(self.actions, 'JOURNAL', [sys.executable, '-c', 'print("MESSAGE=quiet")']).start()

    def cleanup(self):
        for path in self.folder.rglob('*'):
            if not path.is_symlink():
                path.chmod(0o700)
        shutil.rmtree(self.folder)

    def search(self):
        return self.actions.search_for([self.NEEDLE], roots=[str(self.root)])

    def test_a_clean_search_finds_the_one_file_and_reads_the_journal(self):
        found = self.search()
        self.assertEqual(found['hits'], [[str(self.root / 'state/password'), 0]])
        self.assertEqual((found['files'], found['errors'], found['vanished']), ({str(self.root): 2}, [], []))
        self.assertEqual((found['in_journal'], found['journal_returncode']), (False, 0))
        source = (CONTROL_CI / 'actions.py').read_text()
        check = source[source.index('def passwords(request):'):source.index('# Check 2 again')]
        self.assertIn("and not found['in_journal'] and not found['errors'], summary", check)
        self.assertNotIn('os.walk', check)

    @unittest.skipIf(os.geteuid() == 0, 'root reads a file of mode 0000')
    def test_one_unreadable_file_fails(self):
        (self.root / 'state/locked.db').write_bytes(self.NEEDLE)
        (self.root / 'state/locked.db').chmod(0)
        found = self.search()
        self.assertEqual(found['errors'], [f'{self.root}/state/locked.db: PermissionError: Permission denied'])
        self.assertEqual(found['files'], {str(self.root): 2})

    @unittest.skipIf(os.geteuid() == 0, 'root lists a folder of mode 0000')
    def test_a_folder_that_cannot_be_listed_fails(self):
        (self.root / 'private').mkdir()
        (self.root / 'private/secret.txt').write_bytes(self.NEEDLE)
        (self.root / 'private').chmod(0)
        found = self.search()
        self.assertEqual(found['errors'], [f'{self.root}/private: PermissionError: Permission denied'])
        # A root that isn't there is an error too, never zero files.
        self.assertEqual(self.actions.search_for([self.NEEDLE], roots=[str(self.folder / 'none')])['errors'],
                         [f'{self.folder}/none: FileNotFoundError: No such file or directory'])

    def test_a_journal_export_that_fails_fails(self):
        mock.patch.object(self.actions, 'JOURNAL', [sys.executable, '-c', 'import sys; print("MESSAGE=partial"); '
                                                    'sys.stderr.write("Failed to open journal"); sys.exit(1)']).start()
        found = self.search()
        self.assertEqual((found['journal_returncode'], found['errors']),
                         (1, ['journal export exited 1: Failed to open journal']))

    def listed(self, folder, change, before=False):
        """`change` runs once, on the real file system: when the scanner has read `folder`'s listing to its end and
        before it opens a name in it (what a running process does between the two), or, with `before`, as it starts
        to list the folder. By path (os.walk in X2's scanner) and by descriptor (this round's)."""
        real, done = os.scandir, []
        identity = (os.stat(folder).st_dev, os.stat(folder).st_ino)

        class Listing:
            def __init__(self, entries):
                self.entries = entries

            def __iter__(self):
                return self

            def __next__(self):
                return next(self.entries)

            def __enter__(self):
                return self

            def __exit__(self, *error):
                self.close()

            def close(self):
                self.entries.close()
                if not done:
                    done.append(True)
                    change()

        def scandir(path='.'):
            info = os.stat(path)
            if done or (info.st_dev, info.st_ino) != identity:
                return real(path)
            if before:
                done.append(True)
                change()
                return real(path)
            return Listing(real(path))

        return mock.patch('os.scandir', side_effect=scandir)

    def stated(self, path, clean=b'nothing\n'):
        """RECHECK-X2 #1's race, on the real file system: once the scanner has stat'ed the file, a running process
        removes it, and a clean file is under its name when the scanner looks there again. Returns the two patches
        and what happened."""
        real_lstat, real_fstat, first, happened = os.lstat, os.fstat, os.lstat(path), []

        def lstat(target, **options):  # X2's scanner stats by path, and looks again when its open fails
            if str(target) == path and happened == ['removed']:
                pathlib.Path(path).write_bytes(clean)
                happened.append('back')
            info = real_lstat(target, **options)
            if str(target) == path and not happened:
                os.unlink(path)
                happened.append('removed')
            return info

        def fstat(descriptor):  # this round's stats the file it holds open
            info = real_fstat(descriptor)
            if (info.st_dev, info.st_ino) == (first.st_dev, first.st_ino) and not happened:
                os.unlink(path)
                pathlib.Path(path).write_bytes(clean)
                happened.extend(['removed', 'back'])
            return info

        return mock.patch('os.lstat', side_effect=lstat), mock.patch('os.fstat', side_effect=fstat), happened

    def test_runtime_content_that_vanishes_unread_fails_and_is_named(self):
        # RECHECK-X1 #2: a runtime file that a process removed between the listing and the read was skipped, so
        # check 8 could pass without having read it. Unread content fails like a file that can't be read.
        state, clean = self.root / 'state', self.root / 'state/clean.txt'
        with self.listed(state, clean.unlink):  # a running process removed it between the listing and the read
            outside = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual(outside['errors'], [f'{self.root}/state/clean.txt: FileNotFoundError: No such file or directory'])
        clean.write_text('nothing\n')
        runtime_folders = mock.patch.object(self.scanner, 'VANISHING', (f'{self.root}/',))
        with self.listed(state, clean.unlink), runtime_folders:
            runtime = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual(runtime['errors'], [f'{self.root}/state/clean.txt: gone before it was read, so its content '
                                             'is unsearched'])
        self.assertEqual((runtime['vanished'], runtime['files']), ([str(self.root / 'state/clean.txt')],
                                                                   {str(self.root): 1}))
        # Check 8 fails on it: search_for() passes the error on, and passwords() asserts there is none.
        clean.write_text('nothing\n')
        with self.listed(state, clean.unlink), runtime_folders:
            self.assertEqual(len(self.search()['errors']), 1)
        # Only a path named in MAY_VANISH, with its reason, may vanish unread; MAY_VANISH names none today.
        self.assertEqual(self.scanner.MAY_VANISH, {})
        clean.write_text('nothing\n')
        with self.listed(state, clean.unlink), runtime_folders, \
                mock.patch.object(self.scanner, 'MAY_VANISH', {str(self.root / 'state/clean.txt'): 'a reason'}):
            exempt = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual((exempt['errors'], exempt['vanished']), ([], [str(self.root / 'state/clean.txt')]))
        # A folder that vanishes before it is listed: everything in it is unread too. Removed as the scanner starts
        # to list it (it lists as empty then), and removed before the scanner opens it.
        clean.write_text('nothing\n')
        cache = self.root / 'cache'
        for folder, before in ((cache, True), (self.root, False)):
            cache.mkdir()
            (cache / 'held.txt').write_bytes(self.NEEDLE)
            with self.listed(folder, lambda: shutil.rmtree(cache), before=before), runtime_folders:
                gone = self.scanner.scan([str(self.root)], [self.NEEDLE])
            self.assertEqual((gone['vanished'], gone['errors']), ([str(self.root / 'cache')], [
                f'{self.root}/cache: gone before it was read, so its content is unsearched']), before)
        # RECHECK-X2 #1: there is no second try. X2 read a file again that was gone and then back, and so searched
        # whatever had been put there in place of the file it had listed. Gone when it is opened, and back under its
        # name the moment the scanner has seen that: still gone unread, and the new file is not read in its place.
        opening = os.open

        def back_once_seen_gone(path, flags, *more, **options):
            try:
                return opening(path, flags, *more, **options)
            except FileNotFoundError:
                clean.write_text('nothing\n')
                raise

        with self.listed(state, clean.unlink), mock.patch('os.open', side_effect=back_once_seen_gone), runtime_folders:
            again = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertTrue(clean.exists())
        self.assertEqual((again['errors'], again['vanished'], again['files']), (
            [f'{clean}: gone before it was read, so its content is unsearched'], [str(clean)], {str(self.root): 1}))
        self.assertEqual(self.vanishing, ('/run/', '/tmp/', '/var/tmp/'))

    def test_a_file_removed_and_replaced_once_the_scanner_has_stated_it_is_the_one_searched(self):
        # RECHECK-X2 #1: the scanner stats /tmp/control-debug.log, which holds the password; a process removes it
        # before the scanner opens it, and a clean file is under that name when the scanner looks again. X2 read the
        # clean file: errors [], vanished [], no hit, the listed content never searched.
        debug, password = str(self.root / 'state/debug.log'), str(self.root / 'state/password')
        pathlib.Path(debug).write_bytes(b'login ' + self.NEEDLE)
        lstat, fstat, happened = self.stated(debug)
        with lstat, fstat, mock.patch.object(self.scanner, 'VANISHING', (f'{self.root}/',)):
            found = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual((happened, pathlib.Path(debug).read_bytes()), (['removed', 'back'], b'nothing\n'))
        self.assertTrue([debug, 0] in found['hits'] or any(error.startswith(debug) for error in found['errors']),
                        f'the file the scanner stat\'ed was removed and replaced; its content was neither searched '
                        f'nor named as an error: {found}')
        # The scanner holds the file it stat'ed, so that file is the one searched, removed or not; the clean one
        # came after the listing and is no part of it.
        self.assertEqual((found['hits'], found['errors'], found['vanished']), ([[debug, 0], [password, 0]], [], []))
        self.assertEqual(found['files'], {str(self.root): 3})

    def test_what_is_put_under_a_listed_name_before_it_is_opened_is_never_searched_in_its_place(self):
        # RECHECK-X2 #1, one step earlier: the same swap between the folder's listing and the scanner's first look
        # at the file. X2 never saw it (errors [], no hit). The listing's inode number says which file was listed.
        state, debug, password = self.root / 'state', self.root / 'state/debug.log', str(self.root / 'state/password')
        aside = self.folder / 'aside'
        aside.mkdir()

        def replaced(path):
            listed = path.lstat().st_ino
            return lambda: [f'{path}: not the file its folder listed (inode {listed} there, {path.lstat().st_ino} '
                            'opened): replaced before it was read, so its content is unsearched']

        def scan(folder, change, errors):
            with self.listed(folder, change):
                found = self.scanner.scan([str(self.root)], [self.NEEDLE])
            # The listed one is an error; nothing put in its place is searched for it; the rest is searched.
            self.assertEqual((found['errors'], found['hits'], found['vanished'], found['files']),
                             (errors(), [[password, 0]], [], {str(self.root): 2}))

        # A file, replaced as programs replace one: the new one written beside it and renamed over it.
        debug.write_bytes(b'login ' + self.NEEDLE)
        errors = replaced(debug)

        def renamed_over():
            (aside / 'debug.new').write_text('nothing\n')
            os.replace(aside / 'debug.new', debug)

        scan(state, renamed_over, errors)
        debug.unlink()
        # A folder, with another folder in its place: neither is walked as the one that was listed.
        cache, other = self.root / 'cache', aside / 'other'
        for folder in (cache, other):
            folder.mkdir()
        (cache / 'held.txt').write_bytes(self.NEEDLE)
        (other / 'clean.txt').write_text('nothing\n')
        errors = replaced(cache)

        def another_folder():
            os.rename(cache, aside / 'cache.old')
            os.rename(other, cache)

        scan(self.root, another_folder, errors)
        # A folder, with a link in its place: not followed to where it leads.
        (aside / 'elsewhere').mkdir()
        (aside / 'elsewhere/held.txt').write_bytes(self.NEEDLE)
        errors = replaced(cache)

        def a_link():
            os.rename(cache, aside / 'cache.older')
            os.symlink(aside / 'elsewhere', cache)

        scan(self.root, a_link, errors)
        cache.unlink()
        # A file, with a folder in its place.
        debug.write_bytes(b'login ' + self.NEEDLE)
        errors = replaced(debug)

        def a_folder():
            os.rename(debug, aside / 'debug.old')
            debug.mkdir()
            (debug / 'inside.txt').write_bytes(self.NEEDLE)

        scan(state, a_folder, errors)

    def mountinfo(self, mounts):
        """Mount facts only; real temporary files supply every listing and opened inode."""
        info = self.folder / 'numbering-mountinfo'
        info.write_text(''.join(f'{40 + index} 30 0:21 / {str(point).replace(" ", r"\040")} rw - {kind} fixture '
                                f'rw,user_id={os.getuid()},group_id={os.getgid()}\n'
                                for index, (point, kind) in enumerate(mounts.items())))
        real = open

        def opened(path, *args, **kwargs):
            return real(info if path == '/proc/self/mountinfo' else path, *args, **kwargs)

        return mock.patch('builtins.open', side_effect=opened)

    def entries(self, folder, transform):
        """Transform a real directory iterator, without mounting anything or replacing file contents/stat results."""
        real, identity = os.scandir, folder.stat().st_ino

        @contextlib.contextmanager
        def scandir(fd):
            with real(fd) as entries:
                if isinstance(fd, int) and os.fstat(fd).st_ino == identity:
                    yield iter(transform(entries))
                else:
                    yield entries

        return mock.patch('os.scandir', side_effect=scandir)

    @staticmethod
    def numbered(entry, inode):
        return types.SimpleNamespace(name=entry.name, inode=lambda: inode)

    def test_mount_points_and_portal_numbering_are_established_from_mountinfo(self):
        state, password = self.root / 'state', str(self.root / 'state/password')
        # A mount point's listing number belongs to the covered folder, independently of another listing.
        with self.mountinfo({state: 'tmpfs'}), self.entries(self.root, lambda entries: (
                self.numbered(entry, 123456789) for entry in entries)):
            found = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual((found['errors'], found['hits'], found['files']), ([], [[password, 0]], {str(self.root): 2}))
        # The portal convention needs both FUSE mount facts and the constant on every name.
        with self.mountinfo({state: 'fuse.portal'}), self.entries(state, lambda entries: (
                self.numbered(entry, 4294967295) for entry in entries)):
            found = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual((found['errors'], found['hits'], found['files']), ([], [[password, 0]], {str(self.root): 2}))
        self.assertEqual(found['paths'], {'learned': 4, 'searched': 2, 'listed': 2})

    def test_non_fuse_non_mount_point_numbering_mismatches_are_errors(self):
        state = self.root / 'state'
        for mounts in ({self.root: 'tmpfs'}, {self.root: 'fuse.portal', state: 'tmpfs'}):
            with self.subTest(mounts=mounts), self.mountinfo(mounts), self.entries(state, lambda entries: (
                    self.numbered(entry, 4294967295) for entry in entries)):
                found = self.scanner.scan([str(self.root)], [self.NEEDLE])
            self.assertEqual(len(found['errors']), 2)
            self.assertTrue(all('not the file its folder listed' in error for error in found['errors']))
            self.assertEqual((found['hits'], found['files']), ([], {str(self.root): 0}))
        # FUSE alone is insufficient, as is one constant name in a mixed listing.
        for number in (lambda entry: entry.inode() + 1000,
                       lambda entry: 4294967295 if entry.name == 'password' else entry.inode()):
            with self.subTest(number=number), self.mountinfo({state: 'fuse.portal'}), self.entries(
                    state, lambda entries: (self.numbered(entry, number(entry)) for entry in entries)):
                found = self.scanner.scan([str(self.root)], [self.NEEDLE])
            self.assertTrue(any(str(state / 'password') in error for error in found['errors']))
            self.assertEqual(found['hits'], [])

    def test_double_rename_fools_numbering_detection(self):
        # RECHECK-X3 #2: A listed, B opened, A restored for verification, B restored for stat/read.
        state, debug = self.root / 'state', self.root / 'state/debug.log'
        first, second = self.folder / 'first', self.folder / 'second'
        debug.write_bytes(self.NEEDLE)
        second.write_text('clean replacement')
        a, b = debug.stat().st_ino, second.stat().st_ino
        self.assertNotEqual(a, b)
        identity, original, calls = state.stat().st_ino, self.scanner.listing, []

        def listing(fd, *args):
            if os.fstat(fd).st_ino != identity:
                return original(fd, *args)
            calls.append('listing')
            if len(calls) == 1:
                result = original(fd, *args)
                debug.rename(first)
                second.rename(debug)
                return result
            self.assertEqual(len(calls), 2)
            debug.rename(second)
            first.rename(debug)
            result = original(fd, *args)
            debug.rename(first)
            second.rename(debug)
            return result

        with mock.patch.object(self.scanner, 'listing', side_effect=listing):
            found = self.search()
        self.assertEqual(found['errors'], [
            f'{debug}: not the file its folder listed (inode {a} there, {b} opened): replaced before it was read, '
            'so its content is unsearched'])
        self.assertEqual(len(calls), 1)  # Ordinary mismatches never ask the changing listing for permission.
        self.assertEqual(first.read_bytes(), self.NEEDLE)
        self.assertEqual((found['hits'], found['files']), ([[str(state / 'password'), 0]], {str(self.root): 2}))

    def test_second_listing_learns_a_new_name_then_discards_it(self):
        # RECHECK-X3 #1: a verification listing observes late.log, which must join the same work list.
        state, late = self.root / 'state', self.root / 'state/late.log'
        identity, original, observed = state.stat().st_ino, self.scanner.listing, []

        def listing(fd, *args):
            result = original(fd, *args)
            if os.fstat(fd).st_ino == identity and len(observed) == 1:
                late.write_bytes(self.NEEDLE)
            return result

        def entries(real):
            names = []
            observed.append(names)
            for entry in real:
                names.append(entry.name)
                yield self.numbered(entry, 4294967295)

        with self.mountinfo({state: 'fuse.portal'}), self.entries(state, entries), \
                mock.patch.object(self.scanner, 'listing', side_effect=listing):
            found = self.search()
        self.assertTrue(any('late.log' in names for names in observed[1:]))
        self.assertIn([str(late), 0], found['hits'])
        self.assertEqual(found['errors'], [])
        self.assertEqual(found['paths'], {'learned': 5, 'searched': 3, 'listed': 2})

    def test_partial_listing_refusal_discards_yielded_names(self):
        # RECHECK-X3 #1: the real owner's subprocess cannot clear an observed name that disappeared.
        portal, mounts = self.fuse_portal()
        private = portal / 'private.log'
        private.write_bytes(self.NEEDLE)
        inode, yielded = private.stat().st_ino, []

        def partial(entries):
            for entry in entries:
                if entry.name == 'private.log':
                    yielded.append(entry.name)
                    yield entry
                    raise PermissionError(13, 'Permission denied')
            raise AssertionError('private.log was not listed')

        calls, owner = self.owner(private.unlink)
        with self.entries(portal, partial), mounts, owner:
            found = self.search()
        self.assertEqual(yielded, ['private.log'])
        self.assertTrue(any(str(private) in error and 'did not search it either' in error for error in found['errors']),
                        found)
        self.assertIn([str(private), inode], json.loads(calls[0][1])['cover'])
        self.assertEqual(found['paths']['refused'], 2)
        self.assertEqual(found['hits'], [[str(self.root / 'state/password'), 0]])
        # If it remains, both the folder and its observed file can be covered by the owner.
        private.write_bytes(self.NEEDLE)
        calls, owner = self.owner()
        with self.entries(portal, partial), mounts, owner:
            recovered = self.search()
        self.assertEqual(recovered['errors'], [])
        self.assertIn([str(private), 0], recovered['hits'])

    def test_repeated_name_cannot_overwrite_its_first_observed_identity(self):
        # Sibling: a dict comprehension used to keep only the last of two entries for the same name.
        state, debug = self.root / 'state', self.root / 'state/debug.log'
        held, replacement = self.folder / 'held', self.folder / 'replacement'
        debug.write_bytes(self.NEEDLE)
        replacement.write_text('clean replacement')
        real = os.scandir

        def repeated(entries):
            for entry in entries:
                yield entry
                if entry.name == 'debug.log':
                    debug.rename(held)
                    replacement.rename(debug)
                    with real(state) as again:
                        yield next(item for item in again if item.name == 'debug.log')

        with self.entries(state, repeated):
            found = self.search()
        self.assertTrue(any(str(debug) in error for error in found['errors']), found)
        self.assertEqual(held.read_bytes(), self.NEEDLE)

    def test_a_name_whose_inode_is_refused_cannot_be_cleared_by_the_owner(self):
        # Sibling: observing the name precedes entry.inode(); without that identity handover cannot prove coverage.
        portal, mounts = self.fuse_portal()
        private = portal / 'private.log'
        private.write_bytes(self.NEEDLE)

        def refused_inode():
            raise PermissionError(13, 'Permission denied')

        def entries(real):
            for entry in real:
                if entry.name == 'private.log':
                    yield types.SimpleNamespace(name=entry.name, inode=refused_inode)
                else:
                    yield entry

        _, owner = self.owner(private.unlink)
        with self.entries(portal, entries), mounts, owner:
            found = self.search()
        self.assertTrue(any(str(private) in error for error in found['errors']), found)

    def test_benign_atomic_rewrite_fails_closed(self):
        state, clean = self.root / 'state', self.root / 'state/clean.txt'
        replacement = self.folder / 'replacement'
        replacement.write_text('also harmless')
        with self.listed(state, lambda: os.replace(replacement, clean)):
            found = self.search()
        self.assertEqual(len(found['errors']), 1)
        self.assertIn(f'{clean}: not the file its folder listed', found['errors'][0])

    def test_a_repeated_name_whose_inode_is_refused_stays_an_error(self):
        # An earlier successful observation cannot supply the identity missing from a later observation.
        state, seen = self.root / 'state', []

        def refused_inode():
            raise PermissionError(13, 'Permission denied')

        def entries(real):
            for entry in real:
                if entry.name == 'password':
                    seen.append(entry.name)
                    if len(seen) > 1:
                        yield types.SimpleNamespace(name=entry.name, inode=refused_inode)
                        continue
                yield self.numbered(entry, 4294967295)

        with self.mountinfo({state: 'fuse.portal'}), self.entries(state, entries):
            found = self.scanner.scan([str(self.root)], [self.NEEDLE], handover=[str(state)])
        self.assertGreater(len(seen), 1)
        self.assertTrue(any(str(state / 'password') in error for error in found['errors']), found)

    def test_every_path_the_scan_learns_ends_in_one_outcome(self):
        # RECHECK-X2: one record per learned path, and the answer is made from the records.
        outside = self.folder / 'outside'
        outside.mkdir()
        (outside / 'held.txt').write_bytes(self.NEEDLE)
        os.symlink(outside, self.root / 'link')  # never followed
        os.symlink(self.root / 'state/password', self.root / 'state/again')  # the file it leads to is searched once
        os.mkfifo(self.root / 'pipe')  # never opened: nobody writes to it, so a read would wait for ever
        (self.root / 'empty').mkdir()
        found = self.scanner.scan([str(self.root)], [self.NEEDLE])
        self.assertEqual(found['paths'], {'learned': 8, 'searched': 2, 'listed': 3, 'not a file': 3})
        self.assertEqual((found['hits'], found['errors'], found['files']), (
            [[str(self.root / 'state/password'), 0]], [], {str(self.root): 2}))
        # A root that is a link is followed (/root is one in the guest); a root that is a file is searched.
        os.symlink(self.root / 'state', self.folder / 'root')
        found = self.scanner.scan([str(self.folder / 'root'), str(outside / 'held.txt')], [self.NEEDLE])
        self.assertEqual((found['files'], found['errors']),
                         ({str(self.folder / 'root'): 2, str(outside / 'held.txt'): 1}, []))
        self.assertEqual(found['hits'], [[str(self.folder / 'root/password'), 0], [str(outside / 'held.txt'), 0]])
        # With paths that could not be read, the outcomes still add up to what was learned, and each of those paths
        # is an error: a file that can't be read, a folder that can't be listed, one gone before it was opened.
        if os.geteuid() != 0:
            (self.root / 'state/locked.db').write_bytes(self.NEEDLE)
            (self.root / 'state/locked.db').chmod(0)
            (self.root / 'empty').chmod(0)
            with self.listed(self.root, (self.root / 'pipe').unlink):
                found = self.scanner.scan([str(self.root)], [self.NEEDLE])
            self.assertEqual(found['paths'], {'learned': 9, 'searched': 2, 'listed': 2, 'not a file': 2, 'error': 3})
            self.assertEqual(found['errors'], [f'{self.root}/empty: PermissionError: Permission denied',
                                               f'{self.root}/pipe: FileNotFoundError: No such file or directory',
                                               f'{self.root}/state/locked.db: PermissionError: Permission denied'])
        self.assertEqual(sum(count for outcome, count in found['paths'].items() if outcome != 'learned'),
                         found['paths']['learned'])

    def test_a_needle_across_short_reads_is_found(self):
        # A pipe, or a file still being written, hands out what it has: X2 kept only the last read's end, so a
        # needle across three reads was missed. The journal's export is read with the same function.
        class Stream:
            def __init__(self, *pieces):
                self.pieces = list(pieces)

            def read(self, size):
                return self.pieces.pop(0) if self.pieces else b''

        needle = self.NEEDLE
        pieces = (b'x' * 100 + needle[:20], needle[20:25], needle[25:] + b'y' * 50)
        self.assertEqual(self.scanner.found_in(Stream(*pieces), [b'absent' * 6, needle]), {1})
        self.assertEqual(self.scanner.found_in(Stream(b'x' * 100, needle[:-1], b'y'), [needle]), set())
        mock.patch.object(self.actions, 'JOURNAL', [sys.executable, '-c', 'import sys; print("MESSAGE=" + sys.argv[1])',
                                                    needle.decode()]).start()
        self.assertEqual((self.search()['in_journal'], self.search()['errors']), (True, []))
        source = (CONTROL_CI / 'actions.py').read_text()
        self.assertIn('in_journal = bool(scanner.found_in(journal.stdout, needles))', source)

    def fuse_portal(self):
        """A stand-in for the document portal's FUSE mount under the scanned folder, and its mountinfo line."""
        portal = self.root / 'user/1001/doc'
        portal.mkdir(parents=True)
        (portal / 'shared.txt').write_text('nothing')
        info = self.folder / 'mountinfo'
        info.write_text(f'40 30 0:21 / {self.root}/user/1001/doc rw,nosuid,nodev relatime shared:20 - fuse.portal '
                        f'portal rw,user_id={os.getuid()},group_id={os.getgid()}\n'
                        '41 30 0:22 / /sys/fs/fuse/connections rw - fusectl fusectl rw\n'
                        f'42 30 0:23 / {self.root}/with\\040space rw - fuse.gvfsd-fuse gvfsd rw,user_id=1001\n')
        self.assertEqual(self.scanner.fuse_mounts([str(self.root)], info),
                         [(str(portal), 'fuse.portal', os.getuid()), (f'{self.root}/with space', 'fuse.gvfsd-fuse', 1001)])
        real = self.scanner.fuse_mounts
        return portal, mock.patch.object(self.scanner, 'fuse_mounts', side_effect=lambda roots: real(roots, info)[:1])

    def owner(self, before=lambda: None):
        """A stand-in for runuser: the real tree_scan.py, started as this user once `before` has changed what the
        mount's owner will find. Returns the calls made and the patch."""
        calls = []

        def run(argv, input=None, timeout=300, cwd='/'):
            calls.append((argv, input))
            before()
            result = subprocess.run([sys.executable, '-I', argv[-1]], input=input, capture_output=True, text=True,
                                    timeout=60)
            return dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)

        return calls, mock.patch.object(self.actions, 'run', side_effect=run)

    def test_root_walks_a_fuse_mount_first_and_its_owner_only_where_root_is_refused(self):
        # RECHECK-X1 #2: not every FUSE mount refuses root (allow_other). One root can read is root's alone.
        portal, mounts = self.fuse_portal()
        owner = pwd.getpwuid(os.getuid()).pw_name
        with mock.patch.object(self.actions, 'run', side_effect=AssertionError('no owner walk')), mounts:
            found = self.search()
        self.assertEqual(found['files'], {str(self.root): 3})
        self.assertEqual((found['owner_walks'], found['errors']), ([], []))
        self.assertEqual(found['fuse_mounts'], [dict(mount=str(portal), type='fuse.portal', owner=owner,
                                                     root_refused=0)])

    @unittest.skipIf(os.geteuid() == 0, 'root lists a folder of mode 0000')
    def test_a_fuse_mount_that_refuses_root_is_walked_as_its_owner_never_skipped(self):
        # The document portal mounts $XDG_RUNTIME_DIR/doc in his session without allow_other: FUSE refuses root.
        portal, mounts = self.fuse_portal()
        (portal / 'held.txt').write_bytes(self.NEEDLE)
        portal.chmod(0)  # root's refusal, here this user's
        calls, run = self.owner(lambda: portal.chmod(0o700))  # the owner's walk is let in
        with run, mounts:
            found = self.search()
        argv, given = calls[0]
        owner = pwd.getpwuid(os.getuid()).pw_name
        self.assertEqual(argv[:3] + argv[-3:], ['runuser', '-u', owner, '/usr/bin/python3', '-I',
                                                 str(CONTROL_CI / 'tree_scan.py')])
        self.assertNotIn(self.NEEDLE.hex(), ' '.join(argv))
        self.assertIn(self.NEEDLE.hex(), given)
        # Root's walk was refused at the mount; the owner's walk searched it and found what it holds.
        self.assertEqual(found['files'], {str(self.root): 2})
        self.assertEqual(found['owner_walks'], [dict(mount=str(portal), type='fuse.portal', owner=owner, files=2,
                                                     root_refused=1)])
        self.assertEqual(found['hits'], [[str(self.root / 'state/password'), 0], [str(portal / 'held.txt'), 0]])
        self.assertEqual(found['errors'], [])
        # The owner's walk failing leaves root's refusal and the failure as errors.
        portal.chmod(0)
        with mock.patch.object(self.actions, 'run', return_value=dict(returncode=1, stdout='', stderr='refused')), \
                mounts:
            found = self.search()
        self.assertEqual(found['errors'], [f'{portal}: PermissionError: Permission denied',
                                           f'{portal} (fuse.portal) as {owner}: exit 1: refused'])
        # A refusal outside any FUSE mount stays an error (test_a_folder_that_cannot_be_listed_fails).

    @unittest.skipIf(os.geteuid() == 0, 'root reads a file of mode 0000')
    def test_what_root_is_refused_inside_a_fuse_mount_its_owner_must_search_path_by_path(self):
        # RECHECK-X2 #2: root lists a FUSE folder and is refused on private.log in it. X2 handed the owner only the
        # mount point and took the owner's answer for the whole mount: a private.log that was gone by then, or that
        # the owner's view left out, was searched by nobody, with no error.
        portal, mounts = self.fuse_portal()
        private, password = portal / 'private.log', str(self.root / 'state/password')
        owner = pwd.getpwuid(os.getuid()).pw_name
        refusal = f'{private}: PermissionError: Permission denied'
        unsearched = f"{refusal}, and {owner}'s walk did not search it either"

        def search(before):
            private.unlink(missing_ok=True)
            private.write_bytes(b'login ' + self.NEEDLE)
            private.chmod(0)  # root's refusal on this one file, here this user's
            calls, run = self.owner(before)
            with run, mounts:
                found = self.search()
            self.assertEqual(found['fuse_mounts'], [dict(mount=str(portal), type='fuse.portal', owner=owner,
                                                         root_refused=1)])
            # Root searched what it could: the two files outside the mount and shared.txt in it.
            self.assertEqual(found['files'], {str(self.root): 3})
            return found, json.loads(calls[0][1])

        # Recovered: the owner can read it, so the owner's walk searches it and finds what it holds.
        found, request = search(lambda: private.chmod(0o600))
        self.assertEqual((found['hits'], found['errors']), ([[password, 0], [str(private), 0]], []))
        self.assertEqual(found['owner_walks'], [dict(mount=str(portal), type='fuse.portal', owner=owner, files=2,
                                                     root_refused=1)])
        # Gone before the owner's walk, or left out of the owner's view: the walk never meets it, and root's
        # refusal stands.
        found, request = search(private.unlink)
        self.assertEqual((found['errors'], found['hits']), ([unsearched], [[password, 0]]))
        # The owner is told the path, with the number root's listing gave it, and walks the whole mount.
        self.assertEqual((request['roots'], request['cover']), ([str(portal)], [[str(private), mock.ANY]]))
        # Another file under that name by then: not the one root was refused.
        def another_file():
            (self.folder / 'private.new').write_text('nothing\n')
            os.replace(self.folder / 'private.new', private)

        found, request = search(another_file)
        self.assertEqual(found['errors'], [
            f'{private}: not the file root was refused (inode {request["cover"][0][1]} in root\'s listing, '
            f'{private.stat().st_ino} in this one), so that one is unsearched', unsearched])
        self.assertEqual(found['hits'], [[password, 0]])
        # Refused to its owner too: the owner's error, and root's refusal stands.
        found, request = search(lambda: None)
        self.assertEqual((found['errors'], found['hits']), ([refusal, unsearched], [[password, 0]]))
        # A folder in the mount that root can't list: its owner lists it and searches what is in it.
        private.unlink()
        (portal / 'by-app').mkdir()
        (portal / 'by-app/held.txt').write_bytes(self.NEEDLE)
        (portal / 'by-app').chmod(0)
        calls, run = self.owner(lambda: (portal / 'by-app').chmod(0o700))
        with run, mounts:
            found = self.search()
        self.assertEqual((found['hits'], found['errors']), ([[password, 0], [str(portal / 'by-app/held.txt'), 0]], []))
        self.assertEqual(json.loads(calls[0][1])['cover'],
                         [[str(portal / 'by-app'), (portal / 'by-app').stat().st_ino]])
        # Unmounted before its owner walked it: the walk was of the folder under the mount point, not of the mount.
        (portal / 'by-app').chmod(0)
        mountinfo = (self.folder / 'mountinfo').read_text()
        calls, run = self.owner(lambda: ((portal / 'by-app').chmod(0o700), (self.folder / 'mountinfo').write_text('')))
        with run, mounts:
            found = self.search()
        self.assertEqual(found['errors'], [f"{portal} (fuse.portal): no longer mounted after {owner}'s walk, so what "
                                           'root was refused there may not be what was walked'])
        (self.folder / 'mountinfo').write_text(mountinfo)
        # An owner's answer that names no covered paths (X2's tree_scan.py) never passes: root's refusal can only be
        # taken back by the path being named.
        (portal / 'by-app').chmod(0)
        old = dict(returncode=0, stderr='', stdout=json.dumps(dict(files={str(portal): 0}, hits=[], vanished=[],
                                                                  errors=[], refused={})))
        with mock.patch.object(self.actions, 'run', return_value=old), mounts, self.assertRaises(KeyError):
            self.search()


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

    def test_archives_nested_past_the_depth_limit_are_unreadable(self):
        # REVIEW-X1 #3: below DEPTH the bytes were searched raw only, so a fourth gzip level hid the password.
        nested = self.SECRET
        for level in range(1, 5):
            nested = gzip.compress(nested)
            (self.evidence / f'control/nested-{level}.gz').write_bytes(nested)
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertIn('control/nested-4.gz: gzip nested deeper than 3 levels', found['unreadable'])
        self.assertIn('control/nested-4.gz', found['holding'])
        # Three levels are read to the end and the password found inside them.
        self.assertIn('control/nested-3.gz!gunzip!gunzip!gunzip', found['hits'])
        self.assertEqual(len(found['unreadable']), 1, found['unreadable'])
        # A tar.gz inside a tar.gz is four levels too.
        inner = self.folder / 'inner.tar.gz'
        self.tar(inner, {'deep.txt': self.SECRET})
        self.tar(self.evidence / 'control/twice.tar.gz', {'inner.tar.gz': inner.read_bytes()})
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertIn('control/twice.tar.gz: tar nested deeper than 3 levels', found['unreadable'])

    def test_a_damaged_tar_holding_a_compressed_password_is_unreadable(self):
        # REVIEW-X1 #3: is_tarfile() refused a tar with a bad checksum, so it was searched as raw bytes, and tarfile
        # ends an archive quietly at a later header it can't read.
        def damaged(path, members, broken):
            self.tar(path, members, compress=None)
            data = bytearray(path.read_bytes())
            data[broken + 148:broken + 156] = b'0000000\0'  # the header's checksum field, now wrong
            path.write_bytes(bytes(data))
        compressed = gzip.compress(b'login ' + self.SECRET)
        damaged(self.evidence / 'control/first.tar', {'requests.json.gz': compressed}, 0)
        # The second header: after the first one (512 bytes) and its data, padded to 512.
        damaged(self.evidence / 'control/second.tar', {'clean.txt': b'nothing', 'requests.json.gz': compressed}, 1024)
        self.assertNotIn(self.SECRET, (self.evidence / 'control/first.tar').read_bytes())
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['hits'], [])
        self.assertEqual(found['holding'], ['control/first.tar', 'control/second.tar'])
        self.assertIn('control/first.tar: tar: ', found['unreadable'][0])
        self.assertIn('control/second.tar: tar: a header at byte 1024 could not be read', found['unreadable'][1])
        # The same archives undamaged: the password is found, nothing unreadable.
        (self.evidence / 'control/first.tar').unlink()
        self.tar(self.evidence / 'control/second.tar', {'clean.txt': b'nothing', 'requests.json.gz': compressed},
                 compress=None)
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual((found['unreadable'], found['hits']),
                         ([], ['control/second.tar!requests.json.gz!gunzip']))

    @staticmethod
    def rehead(data, changes, offset=0):
        """A tar with its header at offset changed ({byte: bytes}) and its checksum written again, as a valid one."""
        block = bytearray(data[offset:offset + tarfile.BLOCKSIZE])
        for at, value in changes.items():
            block[at:at + len(value)] = value
        block[148:156] = b' ' * 8
        block[148:156] = b'%06o\0 ' % sum(block)
        return data[:offset] + bytes(block) + data[offset + tarfile.BLOCKSIZE:]

    def test_every_tar_tarfile_reads_is_searched_whatever_its_magic(self):
        # RECHECK-X1 #3: X1 recognised a tar only by its exact POSIX or GNU magic and version, so a V7 tar (no magic)
        # and a ustar header with version "01", both of which tarfile reads, were searched as plain bytes only.
        compressed = gzip.compress(b'login ' + self.SECRET)
        plain = self.folder / 'plain.tar'
        self.tar(plain, {'secret.gz': compressed}, compress=None)
        data = plain.read_bytes()
        self.assertEqual(data[257:265], tarfile.POSIX_MAGIC)
        # V7: no magic, version, owner names or prefix (offset 257 to 500 empty).
        (self.evidence / 'control/v7.tar').write_bytes(self.rehead(data, {257: bytes(243)}))
        (self.evidence / 'control/version-01.tar').write_bytes(self.rehead(data, {263: b'01'}))
        # A member of a type tarfile doesn't know: it hands one out as a regular file, and so does GNU tar.
        (self.evidence / 'control/unknown-type.tar').write_bytes(self.rehead(data, {156: b'Z'}))
        for name in ('v7.tar', 'version-01.tar', 'unknown-type.tar'):
            raw = (self.evidence / 'control' / name).read_bytes()
            self.assertNotIn(self.SECRET, raw)
            with tarfile.open(fileobj=io.BytesIO(raw), mode='r:') as archive:
                self.assertEqual(archive.getnames(), ['secret.gz'], name)
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['unreadable'], [])
        self.assertEqual(found['hits'], ['control/unknown-type.tar!secret.gz!gunzip', 'control/v7.tar!secret.gz!gunzip',
                                         'control/version-01.tar!secret.gz!gunzip'])
        # Recognisable but malformed: the POSIX magic with version "01" and a bad checksum is unreadable, as is the
        # GNU magic with one; a V7 header with a bad checksum has nothing left to recognise it by.
        for name in ('v7.tar', 'unknown-type.tar'):
            (self.evidence / 'control' / name).unlink()
        broken = bytearray(self.rehead(data, {263: b'01'}))
        broken[148:156] = b'0000000\0'
        (self.evidence / 'control/version-01.tar').write_bytes(bytes(broken))
        gnu = self.folder / 'gnu.tar'
        with tarfile.open(gnu, 'w', format=tarfile.GNU_FORMAT) as archive:
            info = tarfile.TarInfo('secret.gz')
            info.size = len(compressed)
            archive.addfile(info, io.BytesIO(compressed))
        broken = bytearray(gnu.read_bytes())
        self.assertEqual(broken[257:265], tarfile.GNU_MAGIC)
        broken[148:156] = b'0000000\0'
        (self.evidence / 'control/gnu.tar').write_bytes(bytes(broken))
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['hits'], [])
        self.assertEqual(found['holding'], ['control/gnu.tar', 'control/version-01.tar'])
        self.assertEqual([line.split(': ', 2)[:2] for line in found['unreadable']],
                         [['control/gnu.tar', 'tar'], ['control/version-01.tar', 'tar']])

    def test_formats_the_scan_does_not_unpack_are_unreadable_and_ordinary_logs_are_not(self):
        import lzma
        import zipfile
        (self.evidence / 'control/log.xz').write_bytes(lzma.compress(self.SECRET))
        with zipfile.ZipFile(self.evidence / 'control/screens.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('screen.txt', self.SECRET)
        (self.evidence / 'control/truncated.gz').write_bytes(gzip.compress(self.SECRET * 100)[:-20])
        # Ordinary evidence: text that names the formats, a header-like line at byte 257, binary that isn't one.
        (self.evidence / 'control/journal.txt').write_text('x' * 257 + 'ustar is a tar format; PK\x03\x04 BZh91AY\n')
        (self.evidence / 'control/gnu.txt').write_text('y' * 257 + 'ustar  00 marks a GNU header\n')
        (self.evidence / 'control/screen.png').write_bytes(b'\x89PNG\r\n\x1a\n' + os.urandom(2048))
        found = self.scan.scan(self.evidence, self.SECRET)
        self.assertEqual(found['holding'], ['control/log.xz', 'control/screens.zip', 'control/truncated.gz'])
        self.assertEqual([line.split(': ', 1)[1] for line in found['unreadable']],
                         ['xz data, which this scan does not unpack', 'zip data, which this scan does not unpack',
                          'gzip: Compressed file ended before the end-of-stream marker was reached'])

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
