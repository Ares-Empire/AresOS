"""Package 18c, B2: the pieces of the Control VM test that run without a VM (os/ci/control/, the checks.py hook)."""
import ast
import importlib.util
import json
import os
import pathlib
import re
import shutil
import sys
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
                                    ('interactive_model', 'Model')})
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
