import copy
import json
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import image_diff
import rehearsal_guard as guard
import registry_auth


class KeyboardReleaseTest(unittest.TestCase):
    def test_diff_allows_exact_keyboard_bytes_and_nothing_else(self):
        old = {'usr/bin/aresos-session': dict(sha256='old', bytes=1, mode=0o755, uid=0, gid=0, kind=32768, xattrs={}),
               'usr/lib/systemd/system/a.service': dict(sha256='unit')}
        new = copy.deepcopy(old)
        new['usr/bin/aresos-session']['sha256'] = 'session'
        new['usr/libexec/aresos-keyboard'] = dict(old['usr/bin/aresos-session'], sha256='helper')
        expected = {'usr/bin/aresos-session': 'session', 'usr/libexec/aresos-keyboard': 'helper'}
        self.assertEqual(set(image_diff.compare(old, new, expected)), set(expected))
        for path, value in (('usr/bin/unexplained', {}), ('usr/lib/systemd/system/a.service', dict(sha256='changed'))):
            bad = dict(new, **{path: value})
            with self.assertRaises(AssertionError):
                image_diff.compare(old, bad, expected)
        bad = copy.deepcopy(new); bad['usr/bin/aresos-session']['mode'] = 0o777
        with self.assertRaises(AssertionError):
            image_diff.compare(old, bad, expected)

    def test_package13_starts_at_dispatch_counts_privacy_and_rejects_overrun(self):
        guard.configure('13')
        self.addCleanup(guard.configure, '11c')
        self.assertEqual((guard.MINUTE_CAP, guard.FULL_CAP), (380, 0))
        base = dict(head_sha='a'*40, status='completed', conclusion='success', run_attempt=1)
        runs = [dict(base, id=1, event='push', display_title='privacy', created_at='2026-10-25T00:00:00Z'),
                dict(base, id=2, event='workflow_dispatch', display_title='Package 13 image release', created_at='2026-10-25T01:00:00Z'),
                dict(base, id=3, event='pull_request', display_title='privacy', created_at='2026-10-25T02:00:00Z')]
        job = dict(conclusion='success', started_at='2026-10-25T01:00:00Z', completed_at='2026-10-25T01:01:01Z')
        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(376)
            self.assertEqual(result['consumed_minutes'], 4)
            self.assertEqual(result['dispatch_counts']['release-13'], 1)
            with self.assertRaisesRegex(AssertionError, 'exceeds 380'):
                guard.budget(377)
            runs.append(dict(runs[1], id=4))
            with self.assertRaisesRegex(AssertionError, 'dispatch allowance exhausted'):
                guard.budget(0)

    def test_org_auth_fails_closed_without_job_token_and_never_uses_owner_fallback(self):
        env = dict(GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                   GITHUB_REF_NAME='pkg/13-keyboard-layout', REHEARSAL_MODE='probe', GHCR_READ_TOKEN='must-not-use')
        with patch.object(registry_auth, 'IMAGE', 'ghcr.io/ares-empire/aresos'), patch.dict(registry_auth.RELEASE, visibility='private'), \
             patch.dict(registry_auth.os.environ, env, clear=True), patch.object(registry_auth.legacy, 'create') as legacy:
            with self.assertRaisesRegex(AssertionError, 'no owner-token fallback'):
                registry_auth.create()
            legacy.assert_not_called()
            for key, value in (('GITHUB_EVENT_NAME', 'push'), ('GITHUB_REF_NAME', 'main'), ('REHEARSAL_MODE', 'part-b')):
                with patch.dict(registry_auth.os.environ, {key: value}), self.assertRaises(AssertionError):
                    registry_auth.require_dispatch()


if __name__ == '__main__':
    unittest.main()
