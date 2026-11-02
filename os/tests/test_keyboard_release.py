import copy
import json
import os
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
        self.assertEqual((guard.MINUTE_CAP, guard.FULL_CAP), (460, 0))
        base = dict(head_sha='a'*40, status='completed', conclusion='success', run_attempt=1)
        runs = [dict(base, id=1, event='push', display_title='privacy', created_at='2026-10-25T00:00:00Z'),
                dict(base, id=2, event='workflow_dispatch', display_title='Package 13 image release', created_at='2026-10-25T01:00:00Z'),
                dict(base, id=3, event='pull_request', display_title='privacy', created_at='2026-10-25T02:00:00Z')]
        job = dict(conclusion='success', started_at='2026-10-25T01:00:00Z', completed_at='2026-10-25T01:01:01Z',
                   steps=[dict(name='Run fixture task',conclusion='success',started_at='2026-10-25T01:00:00Z',completed_at='2026-10-25T01:01:01Z')])
        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(456)
            self.assertEqual(result['consumed_minutes'], 4)
            self.assertEqual(result['dispatch_counts']['release-13'], 1)
            with self.assertRaisesRegex(AssertionError, 'exceeds 460'):
                guard.budget(457)
            runs.append(dict(runs[1], id=4))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-13'], 2)
            runs.append(dict(runs[1], id=5))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-13'], 3)
            runs.append(dict(runs[1], id=6))
            with self.assertRaisesRegex(AssertionError, 'dispatch allowance exhausted'):
                guard.budget(0)

    def test_publish_boundary_counts_success_and_failure_but_not_skipped_steps(self):
        guard.configure('13')
        self.addCleanup(guard.configure, '11c')
        run = dict(id=1, event='workflow_dispatch', head_sha='a'*40, run_attempt=1, status='completed',
                   conclusion='failure', created_at='2026-10-25T01:00:00Z', display_title='Package 13 image release')
        step = dict(name=guard.PUBLISH_STEP, status='completed', conclusion='skipped',
                    started_at='2026-10-25T01:00:00Z',completed_at='2026-10-25T01:01:00Z')
        job = dict(name='image',conclusion='failure', started_at='2026-10-25T01:00:00Z', completed_at='2026-10-25T01:01:00Z', steps=[step])
        def api(path):
            return dict(workflow_runs=[run]) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        with patch.object(guard, 'api', side_effect=api):
            self.assertEqual(guard.budget(0)['publish_attempts'], [])
            for conclusion in ('success','failure','cancelled'):
                step['conclusion']=conclusion
                self.assertEqual(guard.budget(0)['publish_attempts'], [dict(run=1,conclusion=conclusion)])
            job.update(conclusion='skipped',steps=[])
            self.assertEqual(guard.budget(0)['publish_attempts'],[])
            job['conclusion']='failure'
            with self.assertRaisesRegex(AssertionError,'boundary missing'):
                guard.budget(0)

    def test_prior_publish_blocks_another_dispatch_or_publish_authorization(self):
        result=dict(history=dict(complete=True,ids_count=1,total_count=1),
                    dispatch_counts={'release-13':2},publish_attempts=[dict(run=1,conclusion='failure')])
        env=dict(REHEARSAL_PACKAGE='13',REHEARSAL_MODE='release-13',GITHUB_REF_NAME='pkg/13-keyboard-layout',
                 GITHUB_RUN_ID='2',GITHUB_SHA='a'*40,GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY=guard.REPOSITORY)
        run=dict(head_branch=env['GITHUB_REF_NAME'],head_sha=env['GITHUB_SHA'],event='workflow_dispatch',display_title='Package 13 image release')
        for mode in ('release-13','publish-ci'):
            with patch.dict(os.environ,env),patch.object(sys,'argv',['guard',mode,'0']),patch.object(guard,'budget',return_value=result),patch.object(guard,'api',return_value=run):
                with self.assertRaisesRegex(AssertionError,'prior attempt reached publishing'):
                    guard.main()
        guard.configure('11c')

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
