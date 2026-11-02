"""Execute the complete release verifier against closed Git/GitHub stand-ins."""
import ast
import contextlib
import copy
import io
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
RELEASE = json.loads((ROOT / 'os/manifest/release.json').read_text())
SOURCE = RELEASE['source_commit']
MERGED = '775be05b7f0d6971cbdc8a3bd1aea617fc008c4d'
PAYLOAD = ['os/Containerfile.keyboard', 'os/.containerignore', 'os/packages.lock.json',
           'os/config', 'os/policy', 'os/manifest/base.json', 'os/keys', 'os/tests/audit.py']


class SquashBindingTest(unittest.TestCase):
    def verify(self, *, binding=None, failed_git=None, shallow=b'false\n'):
        release = copy.deepcopy(RELEASE)
        calls = []
        run_id = release['run'].rsplit('/', 1)[1]
        run = dict(head_sha=SOURCE, path='.github/workflows/os-image.yml',
                   head_branch='pkg/13-keyboard-layout', event='workflow_dispatch',
                   display_title='Package 13 image release', run_attempt=1)
        responses = {
            'repos/Ares-Empire/AresOS/actions/runs/' + run_id: run,
            'repos/Ares-Empire/AresOS/actions/runs/' + run_id + '/jobs?per_page=100':
                dict(total_count=1, jobs=[dict(name='image', conclusion='success')]),
        }
        allowed = [
            ['git', 'fetch', '--no-tags', 'origin', SOURCE],
            ['git', 'fetch', '--no-tags', 'origin', 'refs/pull/12/head'],
            ['git', 'merge-base', '--is-ancestor', SOURCE, 'FETCH_HEAD'],
            ['git', 'fetch', '--no-tags', 'origin', MERGED],
            ['git', 'merge-base', '--is-ancestor', MERGED, 'HEAD'],
            ['git', 'diff', '--exit-code', SOURCE, 'HEAD', '--', *PAYLOAD],
            ['git', 'diff', '--exit-code', SOURCE, MERGED, '--', *PAYLOAD],
        ]

        def output(command, **kwargs):
            if command == ['git', 'rev-parse', '--is-shallow-repository']:
                calls.append(command)
                return shallow
            self.assertEqual(command[:2], ['gh', 'api'])
            self.assertIn(command[2], responses)
            calls.append(command)
            return json.dumps(responses[command[2]]).encode()

        def git(command, **kwargs):
            self.assertEqual(kwargs, dict(check=True))
            self.assertIn(command, allowed)
            calls.append(command)
            if command == failed_git:
                raise subprocess.CalledProcessError(1, command)
            return subprocess.CompletedProcess(command, 0)

        original_read = pathlib.Path.read_text

        def read(path, *args, **kwargs):
            if path.as_posix() == 'evidence/release.json':
                return json.dumps(release)
            return original_read(path, *args, **kwargs)

        self.calls = calls
        path = ROOT / 'os/ci/verify_release.py'
        tree = ast.parse(path.read_text())
        if binding is not None:
            assignment, = [n for n in tree.body if isinstance(n, ast.Assign)
                           and any(isinstance(t, ast.Name) and t.id == 'SQUASH_BINDING' for t in n.targets)]
            assignment.value = ast.parse(repr(binding), mode='eval').body
            ast.fix_missing_locations(tree)
        with patch.object(sys, 'argv', ['verify_release.py', run_id]), \
             patch.dict(os.environ, GITHUB_REPOSITORY='Ares-Empire/AresOS'), \
             patch('pathlib.Path.read_text', read), \
             patch('subprocess.check_output', side_effect=output), \
             patch('subprocess.run', side_effect=git), contextlib.redirect_stdout(io.StringIO()):
            exec(compile(tree, str(path), 'exec'), {'__name__': '__main__'})
        return calls

    def test_complete_pinned_binding_and_original_payload_check_pass(self):
        with self.assertRaises(SystemExit) as done:
            self.verify()
        self.assertEqual(done.exception.code, 0)
        self.assertEqual(len(self.calls), 10)
        self.assertFalse(any('/pulls/' in str(command) for command in self.calls))

    def test_each_reviewed_constant_refuses_when_changed(self):
        pinned = (12, True, MERGED, 'pkg/13-keyboard-layout', 'main')
        for index, wrong in enumerate((13, False, 'a' * 40, 'wrong-head', 'wrong-base')):
            changed = list(pinned); changed[index] = wrong
            with self.subTest(index=index), self.assertRaisesRegex(AssertionError, 'constants differ'):
                self.verify(binding=tuple(changed))
            self.assertEqual(self.calls, [], 'Changed pins must refuse before any git/API read')

    def test_shallow_or_unknown_history_refuses_before_api_reads(self):
        for value in (b'true\n', b'', b'unknown\n'):
            with self.subTest(value=value), self.assertRaisesRegex(SystemExit, 'full history; shallow repository'):
                self.verify(shallow=value)
            self.assertEqual(self.calls, [['git', 'rev-parse', '--is-shallow-repository']])

    def test_each_failed_fetch_refuses(self):
        for ref in (SOURCE, 'refs/pull/12/head', MERGED):
            with self.subTest(ref=ref), self.assertRaises(subprocess.CalledProcessError):
                self.verify(failed_git=['git', 'fetch', '--no-tags', 'origin', ref])

    def test_source_outside_pr_history_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(failed_git=['git', 'merge-base', '--is-ancestor', SOURCE, 'FETCH_HEAD'])

    def test_merge_outside_current_history_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(failed_git=['git', 'merge-base', '--is-ancestor', MERGED, 'HEAD'])

    def test_each_payload_difference_refuses(self):
        for target in ('HEAD', MERGED):
            with self.subTest(target=target), self.assertRaises(subprocess.CalledProcessError):
                self.verify(failed_git=['git', 'diff', '--exit-code', SOURCE, target, '--', *PAYLOAD])


if __name__ == '__main__':
    unittest.main()
