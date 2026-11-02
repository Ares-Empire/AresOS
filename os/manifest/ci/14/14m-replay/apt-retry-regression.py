"""Execute the real rehearsal install text with repo-local, nonprivileged shims.

No apt, sudo, package installation, network, firmware or device operation runs.
"""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

import yaml

ROOT = pathlib.Path.cwd()
WORKFLOW = '.github/workflows/os-image.yml'
SCRIPT = 'os/ci/install-tools.sh'
BASELINE = 'f0d2e22'
STEP = 'Install pinned rehearsal tools on disposable runner'

SHIM = r'''#!/usr/bin/python3
import json, os, pathlib, sys
name = pathlib.Path(sys.argv[0]).name
args = sys.argv[1:]
root = pathlib.Path(os.environ['APT_FIXTURE'])
pins = json.loads((root/'os/ci/toolchain.json').read_text())
if name == 'sudo':
    assert args[0] == 'apt-get', args
    os.execvp(args[0], args)
elif name in ('apt-get', 'apt-cache'):
    assert args.count('Acquire::Retries=3') == 1, args
    i = args.index('Acquire::Retries=3'); assert args[i-1] == '-o'
    if name == 'apt-get':
        log = root/'apt.jsonl'
        count = len(log.read_text().splitlines())+1 if log.exists() else 1
        with log.open('a') as stream: stream.write(json.dumps(args)+'\n')
        if count == int(os.environ.get('APT_FAIL_AT', '0')): sys.exit(73)
    elif 'policy' in args and args[-1] in pins['packages']:
        print('Candidate: ' + ('wrong-version' if os.environ.get('APT_BAD_CANDIDATE') else pins['packages'][args[-1]]))
elif name == 'jq':
    query = args[1]
    if query == '.repository': print(pins['repository'])
    elif query == '.suites[]': print('\n'.join(pins['suites']))
    else:
        assert query == '.packages | to_entries[] | [.key, .value] | @tsv', query
        for package, version in pins['packages'].items(): print(package+'\t'+version)
elif name == 'dpkg-query':
    if '${source:Version}' in ' '.join(args): print('2024.02-2ubuntu0.10')
    else: print('SYNTHETIC installed-package inventory')
elif name == 'python3':
    assert len(args) == 2 and args[0] == 'os/ci/firmware_contract.py', args
    (root/'firmware-reached').write_text('synthetic source check only\n')
elif name in ('sha256sum', 'uname', 'modinfo'): print('SYNTHETIC ' + name)
else: raise AssertionError((name, args))
'''


def baseline(path):
    # This is a Windows worktree: its gitdir spelling requires Windows Git,
    # including when the harmless command execution runs under existing WSL.
    git = shutil.which('git.exe') or 'git'
    return subprocess.check_output([git, 'show', BASELINE + ':' + path], text=True)


class AptRetryRegression(unittest.TestCase):
    def exercise(self, fail=0, bad_candidate=False):
        workflow = yaml.load((ROOT/WORKFLOW).read_text(), Loader=yaml.BaseLoader)
        step, = [s for s in workflow['jobs']['rehearsal']['steps'] if s.get('name') == STEP]
        with tempfile.TemporaryDirectory(dir=ROOT/'.work/14') as temporary:
            folder = pathlib.Path(temporary).resolve()
            (folder/'os/ci').mkdir(parents=True)
            for path in (SCRIPT, 'os/ci/toolchain.json'):
                (folder/path).write_bytes((ROOT/path).read_bytes())
            binary = folder/'bin'; binary.mkdir()
            for name in ('sudo', 'apt-get', 'apt-cache', 'jq', 'dpkg-query', 'sha256sum', 'uname', 'modinfo', 'python3'):
                shim = binary/name; shim.write_text(SHIM); shim.chmod(0o700)
            env = dict(os.environ, PATH=str(binary)+os.pathsep+os.environ['PATH'],
                       APT_FIXTURE=str(folder), APT_FAIL_AT=str(fail))
            if bad_candidate: env['APT_BAD_CANDIDATE'] = '1'
            result = subprocess.run(['/bin/bash', '--noprofile', '--norc'], input=step['run'],
                                    text=True, capture_output=True, cwd=folder, env=env, timeout=30)
            calls = [json.loads(row) for row in (folder/'apt.jsonl').read_text().splitlines()]
            reached = (folder/'firmware-reached').exists()
            if not fail and not bad_candidate:
                pins = json.loads((folder/'os/ci/toolchain.json').read_text())
                expected = [key+'='+value for key,value in pins['packages'].items()]
                self.assertEqual((folder/'evidence/toolchain-packages.txt').read_text().splitlines(), expected)
                for row in calls[1:3]: self.assertEqual(row[-len(expected):], expected)
                sources = (folder/'evidence/toolchain-sources.list').read_text().splitlines()
                self.assertEqual(len(sources), 2*len(pins['suites']))
                for line in sources: self.assertIn(pins['repository'], line)
                self.assertEqual((folder/'evidence/toolchain.json').read_bytes(), (ROOT/'os/ci/toolchain.json').read_bytes())
            return result, calls, reached

    def test_exact_change_scope_and_unchanged_pins(self):
        before = baseline(WORKFLOW)
        expected = before.replace('name: '+STEP+'\n        timeout-minutes: 10',
                                  'name: '+STEP+'\n        timeout-minutes: 20')
        expected = expected.replace('sudo apt-get install -y --no-install-recommends libarchive-tools',
                                    'sudo apt-get -o Acquire::Retries=3 install -y --no-install-recommends libarchive-tools')
        self.assertEqual((ROOT/WORKFLOW).read_text(), expected)
        self.assertEqual((ROOT/SCRIPT).read_text().replace('options=(-o Acquire::Retries=3 ', 'options=('), baseline(SCRIPT))
        self.assertEqual((ROOT/'os/ci/toolchain.json').read_text(), baseline('os/ci/toolchain.json'))

    def test_all_six_apt_invocations_get_exactly_three_retries_and_same_packages(self):
        result, calls, reached = self.exercise()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(len(calls), 6)
        self.assertTrue(reached)

    def test_each_apt_failure_propagates_and_stops_without_shell_reruns(self):
        for failed_call in range(1, 7):
            with self.subTest(failed_call=failed_call):
                result, calls, reached = self.exercise(fail=failed_call)
                self.assertEqual(result.returncode, 73, result.stderr)
                self.assertEqual(len(calls), failed_call)
                self.assertEqual(reached, failed_call == 6)

    def test_wrong_candidate_still_refuses_before_any_install(self):
        result, calls, reached = self.exercise(bad_candidate=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(calls), 1)
        self.assertFalse(reached)


if __name__ == '__main__': unittest.main(verbosity=2)
