"""Execute the complete release verifier against closed Git/GitHub stand-ins."""
import contextlib
import copy
import io
import json
import os
import pathlib
import runpy
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
    def verify(self, *, change=None, failed_git=None):
        release = copy.deepcopy(RELEASE)
        pr = dict(merged=True, merge_commit_sha=MERGED,
                  head=dict(ref='pkg/13-keyboard-layout'), base=dict(ref='main'))
        if change:
            change(pr)
        calls = []
        run_id = release['run'].rsplit('/', 1)[1]
        run = dict(head_sha=SOURCE, path='.github/workflows/os-image.yml',
                   head_branch='pkg/13-keyboard-layout', event='workflow_dispatch',
                   display_title='Package 13 image release', run_attempt=1)
        responses = {
            'repos/Ares-Empire/AresOS/actions/runs/' + run_id: run,
            'repos/Ares-Empire/AresOS/actions/runs/' + run_id + '/jobs?per_page=100':
                dict(total_count=1, jobs=[dict(name='image', conclusion='success')]),
            'repos/Ares-Empire/AresOS/pulls/12': pr,
        }
        allowed = [
            ['git', 'fetch', '--no-tags', 'origin', SOURCE],
            ['git', 'fetch', '--no-tags', 'origin', 'refs/pull/12/head'],
            ['git', 'merge-base', '--is-ancestor', SOURCE, 'FETCH_HEAD'],
            ['git', 'merge-base', '--is-ancestor', MERGED, 'HEAD'],
            ['git', 'diff', '--exit-code', SOURCE, 'HEAD', '--', *PAYLOAD],
        ]

        def output(command, **kwargs):
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

        with patch.object(sys, 'argv', ['verify_release.py', run_id]), \
             patch.dict(os.environ, GITHUB_REPOSITORY='Ares-Empire/AresOS'), \
             patch('pathlib.Path.read_text', read), \
             patch('subprocess.check_output', side_effect=output), \
             patch('subprocess.run', side_effect=git), contextlib.redirect_stdout(io.StringIO()):
            runpy.run_path(str(ROOT / 'os/ci/verify_release.py'), run_name='__main__')
        return calls

    def test_complete_pinned_binding_and_original_payload_check_pass(self):
        with self.assertRaises(SystemExit) as done:
            self.verify()
        self.assertEqual(done.exception.code, 0)

    def test_unmerged_pr_refuses(self):
        with self.assertRaisesRegex(AssertionError, 'must be merged'):
            self.verify(change=lambda p: p.update(merged=False))

    def test_wrong_merge_commit_refuses(self):
        with self.assertRaisesRegex(AssertionError, 'merge commit differs'):
            self.verify(change=lambda p: p.update(merge_commit_sha='a' * 40))

    def test_wrong_head_refuses(self):
        with self.assertRaisesRegex(AssertionError, 'head differs'):
            self.verify(change=lambda p: p['head'].update(ref='wrong'))

    def test_wrong_base_refuses(self):
        with self.assertRaisesRegex(AssertionError, 'base differs'):
            self.verify(change=lambda p: p['base'].update(ref='wrong'))

    def test_missing_binding_fields_refuse(self):
        for field in ('merged', 'merge_commit_sha', 'head', 'base'):
            with self.subTest(field=field), self.assertRaises(KeyError):
                self.verify(change=lambda p: p.pop(field))

    def test_source_outside_pr_history_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(failed_git=['git', 'merge-base', '--is-ancestor', SOURCE, 'FETCH_HEAD'])

    def test_merge_outside_current_history_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(failed_git=['git', 'merge-base', '--is-ancestor', MERGED, 'HEAD'])

    def test_payload_difference_still_refuses(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.verify(failed_git=['git', 'diff', '--exit-code', SOURCE, 'HEAD', '--', *PAYLOAD])


if __name__ == '__main__':
    unittest.main()
