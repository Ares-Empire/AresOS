import base64
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import rehearsal_auth as auth
import two_disk_vm as vm


class OwnerAuthTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name).resolve()
        self.workspace = self.root / 'workspace'
        self.workspace.mkdir()
        (self.workspace / 'evidence').mkdir()
        temporary = self.root / 'runner-temp'
        temporary.mkdir()
        self.environment = dict(GITHUB_WORKSPACE=str(self.workspace), RUNNER_TEMP=str(temporary),
            GITHUB_EVENT_NAME='workflow_dispatch', REHEARSAL_MODE='probe', GHCR_READ_TOKEN='fixture-read-token')

    def test_secret_is_only_referenced_in_the_dispatch_probe_full_create_step(self):
        workflow = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        references = []
        for name, job in workflow['jobs'].items():
            self.assertNotIn('secrets.GHCR_READ_TOKEN', json.dumps({k: v for k, v in job.items() if k != 'steps'}))
            for step in job['steps']:
                if 'secrets.GHCR_READ_TOKEN' in json.dumps(step):
                    references.append((name, step))
                self.assertNotIn('secrets.GHCR_READ_TOKEN', step.get('run', ''))
        self.assertEqual(len(references), 2)
        release_name, release_step = next((n,s) for n,s in references if n == 'image')
        self.assertEqual(release_name, 'image')
        for required in ("github.event_name == 'workflow_dispatch'", 'inputs.release_13', "github.ref_name == 'pkg/13-keyboard-layout'"):
            self.assertIn(required, release_step['if'])
        self.assertEqual(release_step['env']['REHEARSAL_MODE'], 'release-13')
        self.assertNotIn('GH_TOKEN', release_step['env'])
        self.assertEqual(release_step['run'], 'sudo -E python3 os/ci/rehearsal_auth.py create')
        name, step = next((n,s) for n,s in references if n == 'rehearsal')
        self.assertEqual(name, 'rehearsal')
        self.assertIn("github.event_name == 'workflow_dispatch'", workflow['jobs'][name]['if'])
        for required in ("github.event_name == 'workflow_dispatch'", "inputs.rehearsal == 'probe'", "inputs.rehearsal == 'part-b'"):
            self.assertIn(required, step['if'])
        self.assertEqual(step['env']['GHCR_READ_TOKEN'], '${{ secrets.GHCR_READ_TOKEN }}')
        self.assertNotIn('GH_TOKEN', step['env'])
        self.assertIn("github.ref_name != 'pkg/13-keyboard-layout'", step['if'])
        self.assertEqual(step['run'], 'sudo -E python3 os/ci/rehearsal_auth.py create')

    def test_auth_is_outside_workspace_and_always_removed_before_artifact_upload(self):
        workflow = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        steps = workflow['jobs']['rehearsal']['steps']
        index, cleanup = next((i, s) for i, s in enumerate(steps) if s.get('run') == 'sudo -E python3 os/ci/rehearsal_auth.py cleanup')
        self.assertEqual(cleanup['if'], "always() && github.ref_name != 'pkg/13-keyboard-layout' && github.ref_name != 'pkg/14-owner-tools' && github.ref_name != 'pkg/16-staged-release'")
        org_index, org_cleanup = next((i,s) for i,s in enumerate(steps) if s.get('run') == 'sudo -E python3 os/ci/registry_auth.py cleanup')
        self.assertEqual(org_cleanup['if'], "always() && (github.ref_name == 'pkg/13-keyboard-layout' || (github.ref_name == 'pkg/14-owner-tools' || github.ref_name == 'pkg/16-staged-release'))")
        for i, step in enumerate(steps):
            if 'actions/upload-artifact@' in step.get('uses', ''):
                self.assertGreater(i, index)
                self.assertGreater(i, org_index)
                self.assertEqual(step['with']['path'], 'evidence/')
        output = io.StringIO()
        with patch.dict(os.environ, self.environment, clear=True), contextlib.chdir(self.workspace), contextlib.redirect_stdout(output):
            with patch.object(auth.os, 'open', wraps=os.open) as opened, patch.object(auth.subprocess, 'run') as command:
                auth.create()
                command.assert_not_called()
                self.assertEqual(opened.call_args.args[2], 0o600)
            path = auth.auth_directory() / 'auth.json'
            self.assertFalse(path.is_relative_to(self.workspace))
            value = json.loads(path.read_text())
            self.assertEqual(set(value['auths']), {auth.IMAGE})
            encoded = value['auths'][auth.IMAGE]['auth']
            self.assertEqual(base64.b64decode(encoded).decode(), 'carlsenares:fixture-read-token')
            if os.name == 'posix':
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            auth.cleanup()
            self.assertFalse(path.exists())
            self.assertTrue(json.loads(pathlib.Path('evidence/owner-auth-cleanup.json').read_text())['removed'])
        self.assertNotIn('fixture-read-token', output.getvalue())
        self.assertNotIn(encoded, output.getvalue())

    def test_missing_secret_wrong_event_or_mode_and_workspace_path_fail_closed(self):
        for change in (dict(GHCR_READ_TOKEN=''), dict(GITHUB_EVENT_NAME='push'),
                        dict(GITHUB_EVENT_NAME='pull_request'), dict(REHEARSAL_MODE='inspect'), dict(REHEARSAL_MODE='full'),
                       dict(RUNNER_TEMP=str(self.workspace))):
            with self.subTest(change=change), patch.dict(os.environ, dict(self.environment, **change), clear=True):
                with self.assertRaises((AssertionError, RuntimeError)):
                    auth.create()
                self.assertFalse((pathlib.Path(self.environment['RUNNER_TEMP']) / auth.DIRECTORY).exists())

    def test_preflight_accepts_only_the_pinned_digest_and_discards_error_output(self):
        with patch.dict(os.environ, self.environment, clear=True), contextlib.chdir(self.workspace):
            for returncode, digest in ((0, auth.DIGEST), (1, 'fixture-read-token'), (0, 'sha256:wrong')):
                with self.subTest(returncode=returncode, digest=digest), patch.object(auth, 'auth_file', return_value=self.root / 'auth.json'), \
                     patch.object(auth.subprocess, 'run', return_value=Mock(returncode=returncode, stdout=digest, stderr='fixture-read-token')) as command, \
                     contextlib.redirect_stdout(io.StringIO()) as output:
                    if returncode == 0 and digest == auth.DIGEST:
                        auth.preflight(dict(reference=auth.REFERENCE))
                    else:
                        with self.assertRaisesRegex(RuntimeError, 'no fallback'):
                            auth.preflight(dict(reference=auth.REFERENCE))
                    proof = pathlib.Path('evidence/private-registry-preflight.json').read_text()
                    self.assertNotIn('fixture-read-token', proof + output.getvalue())
                    self.assertEqual(command.call_args.args[0][-1], 'docker://' + auth.REFERENCE)
            with patch.object(auth.subprocess, 'run') as command, self.assertRaises(AssertionError):
                auth.preflight(dict(reference=auth.IMAGE + ':latest'))
            command.assert_not_called()

    def test_guest_uses_only_a_read_only_share_not_an_encoded_secret_command(self):
        guest = object.__new__(vm.Guest)
        guest.owner_auth_directory = self.root / 'runner-temp' / auth.DIRECTORY
        guest.boot_number = 1
        guest.command = Mock()
        args = guest.peripheral_args()
        self.assertIn('readonly=on', ' '.join(args))
        self.assertIn('addr=0x6', ' '.join(args))
        guest.prepare_registry_auth('must-not-enter-command')
        source = guest.command.call_args.args[1]
        self.assertIn('ro,cache=none', source)
        self.assertIn('stat -c %u /run/aresos-owner-auth/auth.json', source)
        self.assertIn('stat -c %u /run/aresos-owner-auth)', source)
        self.assertIn('ln -sfn /run/aresos-owner-auth/auth.json', source)
        self.assertNotIn('must-not-enter-command', source)
        self.assertNotIn('base64', source)
        self.assertNotIn('cat ', source)

    def test_cleanup_refuses_unexpected_files_in_the_temporary_directory(self):
        with patch.dict(os.environ, self.environment, clear=True):
            directory = auth.auth_directory()
            directory.mkdir()
            (directory / 'unrelated').write_text('preserve')
            with self.assertRaisesRegex(AssertionError, 'Unexpected'):
                auth.cleanup()
            self.assertTrue((directory / 'unrelated').exists())

    def test_registry_diagnostics_are_never_written_to_public_console_evidence(self):
        guest = object.__new__(vm.Guest)
        with patch.object(vm.sw.Guest, 'command') as command:
            for script in ('DOCKER_CONFIG=/run/registry cosign verify pinned', 'bootc switch --retain pinned'):
                guest.command('registry-read', script)
                self.assertTrue(command.call_args.kwargs['private'])
            guest.command('safe-check', 'bootc status --json')
            self.assertFalse(command.call_args.kwargs['private'])

    def test_failed_layer_pull_has_no_retry_or_credential_diagnostics(self):
        with patch.dict(os.environ, self.environment, clear=True), \
             patch.object(auth.pathlib.Path, 'read_text', return_value=json.dumps(dict(reference=auth.REFERENCE))), \
             patch.object(auth, 'auth_file', return_value=self.root / 'runner-temp/auth.json'), \
             patch.object(auth.subprocess, 'run', return_value=Mock(returncode=1, stderr=b'fixture-read-token')) as command, \
             patch.object(auth.subprocess, 'check_output') as inspect, contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(RuntimeError, 'no fallback'):
                auth.pull()
            command.assert_called_once()
            argv = command.call_args.args[0]
            self.assertEqual(argv[0:2], ['skopeo', 'copy'])
            self.assertIn('docker://' + auth.REFERENCE, argv)
            self.assertNotIn('fixture-read-token', ' '.join(argv) + output.getvalue())
            inspect.assert_not_called()

    def test_auth_file_rejects_runner_uid_and_relaxed_permissions(self):
        directory = self.root / 'auth-share'
        directory.mkdir()
        (directory / 'auth.json').write_text('{}')
        with patch.dict(os.environ, self.environment, clear=True), patch.object(auth, 'auth_directory', return_value=directory):
            for mode, uid in ((0o100600, 1001), (0o100644, 0)):
                with self.subTest(mode=mode, uid=uid), patch.object(pathlib.Path, 'stat', return_value=Mock(st_mode=mode, st_uid=uid)):
                    with self.assertRaises(AssertionError):
                        auth.auth_file()
            with patch.object(pathlib.Path, 'stat', return_value=Mock(st_mode=0o100600, st_uid=0)):
                self.assertEqual(auth.auth_file(), directory / 'auth.json')
