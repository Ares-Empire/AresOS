import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import build_tools
import image_diff
import rehearsal_auth
import registry_auth


class BuildToolsTest(unittest.TestCase):
    def fixture(self, root):
        tools={}
        for name in build_tools.NAMES:
            file=root/name
            file.write_text('#!'+sys.executable+'\nprint("ABSOLUTE_TOOL_EXECUTED")\n')
            file.chmod(0o755)
            tools[name]=str(file.resolve())
        tools['python3']=str(pathlib.Path(sys.executable).resolve())
        tools['bash']=str(pathlib.Path(shutil.which('bash')).resolve())
        return tools

    def test_wrapper_validates_resolved_tools_and_diff_executes_without_path(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve()
            tools=self.fixture(root)
            with patch.object(build_tools.shutil,'which',side_effect=lambda name:tools[name]):
                resolved=build_tools.resolve()
            manifest=root/'tools.json';manifest.write_text(json.dumps(resolved))
            environment=dict(os.environ,PATH='/no-host-tool-search',RUNNER_TEMP=str(root/'credentials-must-not-exist'))
            result=subprocess.run([resolved['bash'],str(ROOT/'os/ci/build-keyboard-release.sh'),resolved['python3'],str(manifest),'--check-tools'],
                                  cwd=ROOT,env=environment,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertIn('BUILD_TOOLS_VALIDATED_WITHOUT_CREDENTIALS',result.stdout)
            self.assertFalse((root/'credentials-must-not-exist').exists())
            with patch.dict(os.environ,environment,clear=True),patch.object(image_diff,'TOOLS',resolved):
                self.assertEqual(image_diff.command('podman','--version'),'ABSOLUTE_TOOL_EXECUTED')
                self.assertEqual(image_diff.command('skopeo','--version'),'ABSOLUTE_TOOL_EXECUTED')

    def test_bad_paths_missing_keys_and_nonexecutables_stop_before_auth(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve();tools=self.fixture(root)
            for name in build_tools.NAMES:
                for value in ('',name,str(root/'absent'),str(root)):
                    with self.subTest(name=name,value=value),patch.object(rehearsal_auth,'auth_file') as auth:
                        with self.assertRaisesRegex(RuntimeError,'STOP:'):
                            build_tools.build(dict(tools,**{name:value}))
                        auth.assert_not_called()
            with patch.object(build_tools.os,'access',return_value=False),patch.object(rehearsal_auth,'auth_file') as auth:
                with self.assertRaisesRegex(RuntimeError,'non-executable'):
                    build_tools.build(tools)
                auth.assert_not_called()
            with self.assertRaisesRegex(RuntimeError,'exactly'):
                build_tools.validate({})
            with patch.object(build_tools.shutil,'which',return_value=None),self.assertRaisesRegex(RuntimeError,'before credentials'):
                build_tools.resolve()
            for python in ('python3',str(root/'missing-python')):
                result=subprocess.run([tools['bash'],str(ROOT/'os/ci/build-keyboard-release.sh'),python,str(root/'absent.json')],
                                      cwd=ROOT,env=dict(os.environ,PATH='/no-host-tool-search'),capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('before credentials',result.stderr)

    def test_paths_are_explicit_at_sudo_and_resolution_precedes_secret_creation(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root=pathlib.Path(directory).resolve();tools=self.fixture(root)
            manifest=root/'tools.json';manifest.write_text(json.dumps(tools))
            with patch.object(sys,'argv',['build_tools','launch',str(manifest)]),patch.object(build_tools.subprocess,'run') as run:
                build_tools.main()
            argv=run.call_args.args[0]
            self.assertEqual(argv[:3],[tools['sudo'],'-E',tools['bash']])
            self.assertEqual(argv[-2:],[tools['python3'],str(manifest)])
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        steps=workflow['jobs']['image']['steps']
        resolve,= [i for i,s in enumerate(steps) if s.get('run')=='python3 os/ci/build_tools.py resolve evidence/build-tools.json']
        auth,=[i for i,s in enumerate(steps) if s.get('run')=='sudo -E python3 os/ci/rehearsal_auth.py create']
        self.assertLess(resolve,auth)

    def test_r29_build_modes_require_the_exact_dispatch_branch_before_registry_access(self):
        branch = 'pkg/331-release-29'
        env = dict(GITHUB_ACTIONS='true', REHEARSAL_PACKAGE='331', GITHUB_REPOSITORY='Ares-Empire/AresOS', GITHUB_REF_NAME=branch,
                   GITHUB_REF='refs/heads/' + branch, GITHUB_EVENT_NAME='workflow_dispatch')
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            tools = self.fixture(pathlib.Path(directory))
            for mode in ('dry-run-29', 'publish-29'):
                self.assertEqual(build_tools.RELEASE_MODES[mode], '29')
                with patch.dict(os.environ, env | {'REHEARSAL_MODE': mode}, clear=True), \
                        patch.object(registry_auth, 'auth_file', side_effect=RuntimeError('fixture registry boundary')) as auth:
                    with self.assertRaisesRegex(RuntimeError, 'fixture registry boundary'):
                        build_tools.build_release(tools, '29')
                    auth.assert_called_once_with()
                for wrong in ({'GITHUB_REF': 'refs/tags/' + branch}, {'GITHUB_REF': 'refs/heads/main'},
                              {'GITHUB_EVENT_NAME': 'push'}, {'REHEARSAL_MODE': 'release-29'},
                              {'REHEARSAL_PACKAGE': '42'}, {'GHCR_READ_TOKEN': 'fixture'}):
                    with self.subTest(mode=mode, wrong=wrong), patch.object(registry_auth, 'auth_file') as auth, \
                            patch.dict(os.environ, env | {'REHEARSAL_MODE': mode} | wrong, clear=True):
                        with self.assertRaises(AssertionError):
                            build_tools.build_release(tools, '29')
                        auth.assert_not_called()

    def test_r29_build_registry_auth_uses_the_immutable_r28_record_even_if_active_pin_changes(self):
        branch = registry_auth.BASELINE_BRANCH
        expected = json.loads(registry_auth.historical_records()['28'])
        env = dict(GITHUB_ACTIONS='true', REHEARSAL_PACKAGE='331', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                   GITHUB_REF_NAME=branch, GITHUB_REF='refs/heads/' + branch, GITHUB_EVENT_NAME='workflow_dispatch')
        for mode in build_tools.RELEASE_BUILDS['29']['modes']:
            with self.subTest(mode=mode), patch.dict(os.environ, env | {'REHEARSAL_MODE': mode}, clear=True), \
                    patch.object(registry_auth, 'RELEASE', {'reference': 'fixture wrong active pointer'}), \
                    patch.object(registry_auth, 'org_release', return_value=False), \
                    patch.object(registry_auth, 'write_auth') as write, \
                    patch.object(registry_auth, 'require_private_package') as private, \
                    patch.object(registry_auth, 'inspect_digest') as read, \
                    patch.object(registry_auth, 'job_auth_file', return_value='fixture job auth file'):
                registry_auth.create()
                registry_auth.preflight()
                write.assert_called_once_with('ghcr.io/ares-empire/aresos')
                private.assert_called_once_with()
                read.assert_called_once_with(expected['reference'])
                self.assertEqual(registry_auth.auth_file(), 'fixture job auth file')
        for context in ({'REHEARSAL_MODE': 'release-29-baseline'}, {'REHEARSAL_MODE': 'release-29'},
                        {'REHEARSAL_MODE': 'dry-run-29', 'GITHUB_REF': 'refs/tags/' + branch}):
            with self.subTest(context=context), patch.dict(os.environ, env | context, clear=True), \
                    patch.object(registry_auth, 'write_auth') as write, self.assertRaisesRegex(AssertionError, 'R29 dispatch'):
                registry_auth.create()
            write.assert_not_called()

    def test_r29_publish_script_checks_the_exact_job_and_stops_before_credentials(self):
        branch = registry_auth.BASELINE_BRANCH
        env = dict(GITHUB_ACTIONS='true', REHEARSAL_PACKAGE='331', REHEARSAL_MODE='publish-29', GITHUB_JOB='release-29',
                   GITHUB_REPOSITORY='Ares-Empire/AresOS', GITHUB_REF_NAME=branch, GITHUB_REF='refs/heads/' + branch,
                   GITHUB_EVENT_NAME='workflow_dispatch')
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            root = pathlib.Path(directory)
            fake_guard = root / 'python3'
            fake_guard.write_text('#!/bin/bash\n[[ "$*" == "os/ci/rehearsal_guard.py publish-ci 0" ]] || exit 2\necho FIXTURE_GUARD\n')
            fake_guard.chmod(0o755)
            for wrong in ({}, {'GITHUB_REF': 'refs/tags/' + branch}, {'GITHUB_REF': 'refs/heads/' + branch.upper()},
                          {'REHEARSAL_PACKAGE': '42'}, {'REHEARSAL_MODE': 'dry-run-29'},
                          {'GITHUB_JOB': 'release-29-authorize'}, {'GITHUB_ACTIONS': 'false'}):
                with self.subTest(wrong=wrong):
                    # No executable besides the guard can be reached through this PATH.
                    result = subprocess.run(['/bin/bash', 'os/ci/publish.sh'], cwd=ROOT, capture_output=True, text=True,
                                            env=env | {'PATH': str(root)} | wrong)
                    self.assertEqual(result.returncode, 1, result)
                    if wrong:
                        self.assertEqual(result.stdout, '')
                    else:
                        self.assertEqual(result.stdout.strip(), 'FIXTURE_GUARD')
                        self.assertIn('prospective shipment checks before publishing', result.stderr)


if __name__=='__main__':
    unittest.main()
