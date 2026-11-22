"""Package 331 dispatch boundaries and ledger accounting with fake Actions history."""

import contextlib
import io
import json
import os
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_owner_staged_release import condition
from test_release27 import workflow_expression
from test_release28 import WORKFLOW, inputs, run_name
import rehearsal_guard as guard


BRANCH = 'pkg/331-release-29'
REF = 'refs/heads/' + BRANCH
PATH = '.github/workflows/os-image.yml'
SHA = 'a' * 40
LEDGER = guard.PACKAGES['331']
SELECTORS = {
    'publish-29': ('release-29', '', {'inputs.release_29': True}),
    'dry-run-29': ('release-29-dry-run', '', {'inputs.dry_run_29': True}),
    'release-29': ('release-29-rehearsal', 'release-29', {}),
}


def selected(mode='', **changes):
    world = {'github.ref_name': BRANCH} | changes
    return {name for name, job in WORKFLOW['jobs'].items() if condition(job['if'], mode=mode, **world)}


class WorkflowTest(unittest.TestCase):
    def test_r29_modes_and_titles_only_select_their_exact_branch_jobs(self):
        dispatch = WORKFLOW['on']['workflow_dispatch']['inputs']
        for flag in ('release_29', 'dry_run_29'):
            self.assertEqual((dispatch[flag]['type'], dispatch[flag]['default']), ('boolean', 'false'))
        self.assertIn('release-29', dispatch['rehearsal']['options'])
        for kind, (job, mode, flags) in SELECTORS.items():
            with self.subTest(kind=kind):
                self.assertEqual(selected(mode, **flags), {job})
                for branch in ('main', 'pkg/42-release-28', 'pkg/331-release-29-other'):
                    self.assertEqual(selected(mode, **(flags | {'github.ref_name': branch})), set())
                for context in ({'github.ref': 'refs/tags/' + BRANCH}, {'github.event_name': 'push'},
                                {'github.repository': 'example/AresOS'}):
                    self.assertEqual(selected(mode, **(flags | context)), set())
                world = inputs() | {'github.ref_name': BRANCH, 'inputs.rehearsal': mode} | flags
                self.assertEqual(run_name(world), LEDGER['titles'][kind])
        package = WORKFLOW['env']['REHEARSAL_PACKAGE'].removeprefix('${{').removesuffix('}}')
        world = inputs() | {'github.ref_name': BRANCH, 'github.ref': REF}
        self.assertEqual(workflow_expression(package, world), '331')
        self.assertNotEqual(workflow_expression(package, world | {'github.ref': 'refs/tags/' + BRANCH}), '331')

    def test_r29_collisions_select_no_jobs_and_publish_attempts_keep_their_title(self):
        collisions = {'inputs.release_29': True, 'inputs.dry_run_29': True, 'inputs.release_13': True,
                      'inputs.release_27': True, 'inputs.release_28': True, 'inputs.dry_run_28': True,
                      'inputs.checks_only': True, 'inputs.check_build': 'resolve', 'inputs.switch_from_run': '42',
                      'inputs.probe_run': '42', 'inputs.full_model': True}
        for kind, (_, mode, flags) in SELECTORS.items():
            for key, value in collisions.items():
                if key not in flags:
                    with self.subTest(kind=kind, collision=key):
                        self.assertEqual(selected(mode, **(flags | {key: value})), set())
            if not mode:
                for other in ('probe', 'release-28', 'release-29'):
                    self.assertEqual(selected(other, **flags), set())
        checks = {'inputs.checks_only': True, 'inputs.full_model': True}
        resolve = {'inputs.check_build': 'resolve'}
        self.assertEqual(selected(**checks), {'regressions', 'model'})
        self.assertEqual(selected(**resolve), {'check-build'})
        self.assertEqual(selected(**(checks | resolve)), set())
        self.assertEqual(selected(**{'inputs.check_build': 'build'}), set())
        self.assertEqual(selected('probe'), set())
        self.assertEqual(selected(**{'inputs.switch_from_run': '1'}), set())
        self.assertEqual(run_name(inputs() | collisions | {'inputs.rehearsal': 'release-29'}), LEDGER['titles']['publish-29'])
        for mode in ('release_29', 'dry_run_29'):
            for legacy in ('release_28', 'dry_run_28'):
                world = {'github.ref_name': 'pkg/42-release-28', 'inputs.' + mode: True, 'inputs.' + legacy: True}
                self.assertEqual(selected(**world), set())

    def test_only_the_publish_job_gets_publish_permissions_and_tokens_are_scoped(self):
        for kind, (job_name, _, _) in SELECTORS.items():
            with self.subTest(kind=kind):
                job = WORKFLOW['jobs'][job_name]
                permissions = {'contents': 'read', 'actions': 'read', 'packages': 'read'}
                if kind == 'publish-29':
                    permissions.update({'packages': 'write', 'id-token': 'write'})
                self.assertEqual(job['permissions'], permissions)
                checkout, authorize, stop = job['steps']
                self.assertTrue(checkout['uses'].startswith('actions/checkout@'))
                self.assertEqual(checkout['with'], {'persist-credentials': 'false'})
                self.assertEqual(authorize['env'], {'GH_TOKEN': '${{ secrets.GITHUB_TOKEN }}', 'REHEARSAL_MODE': kind})
                self.assertEqual(authorize['run'], 'python3 os/ci/rehearsal_guard.py ci 0')
                self.assertIn('exit 1', stop['run'])
        for job_name, kind in (('regressions', 'checks'), ('model', 'checks'), ('check-build', 'resolve')):
            job = WORKFLOW['jobs'][job_name]
            guards = [i for i, step in enumerate(job['steps']) if 'rehearsal_guard.py ci' in step.get('run', '')
                      and condition(step['if'], **{'github.ref_name': BRANCH})]
            self.assertEqual(guards, [1])
            self.assertEqual(job['steps'][1]['env']['REHEARSAL_MODE'], kind)
            self.assertEqual(job['permissions']['actions'], 'read')
            self.assertNotIn('write', job['permissions'].values())


class LedgerTest(unittest.TestCase):
    def setUp(self):
        guard.configure('331')
        self.addCleanup(guard.configure, '11c')
        self.runs = []
        self.jobs = {}
        self.current = 50
        self.environment = dict(REHEARSAL_PACKAGE='331', GITHUB_REPOSITORY=guard.REPOSITORY,
                                GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REF=REF, GITHUB_REF_NAME=BRANCH,
                                GITHUB_RUN_ID=str(self.current), GITHUB_SHA=SHA)

    def run_row(self, kind, run_id, conclusion):
        return dict(id=run_id, event='workflow_dispatch', path=PATH, head_sha=SHA, head_branch=BRANCH,
                    run_attempt=1, display_title=LEDGER['titles'][kind], created_at='2026-11-22T00:00:00Z',
                    status='completed' if conclusion else 'in_progress', conclusion=conclusion)

    def api(self, path):
        if path == guard.RUN_HISTORY_PATH:
            length = len(self.runs)
            return dict(workflow_runs=self.runs, history=dict(complete=True, ids_count=length, total_count=length,
                                                            run_ids=[row['id'] for row in self.runs]))
        if path == 'actions/runs/' + str(self.current):
            return next(row for row in self.runs if row['id'] == self.current)
        run_id, = [row['id'] for row in self.runs if path == f"actions/runs/{row['id']}/jobs?per_page=100"]
        jobs = self.jobs.get(run_id, [])
        return dict(total_count=len(jobs), jobs=jobs)

    def authorize(self, kind, mode='ci', **context):
        self.runs.append(self.run_row(kind, self.current, None))
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp), contextlib.redirect_stdout(io.StringIO()), \
                    patch.object(guard, 'api', side_effect=self.api), \
                    patch.dict(os.environ, self.environment | {'REHEARSAL_MODE': kind} | context, clear=True), \
                    patch.object(sys, 'argv', ['rehearsal_guard.py', mode, '0']):
                guard.main()
                return json.loads(pathlib.Path('evidence/331-dispatch-authorization.json').read_text())
        finally:
            self.runs.pop()

    def test_zero_caps_and_a_same_named_tag_stop_the_current_job(self):
        self.assertEqual(LEDGER['dispatch_caps']['publish-29'], 0)
        self.assertEqual(LEDGER['publish_cap'], 0)
        self.assertEqual(LEDGER['dispatch_caps']['release-29'], 0)
        with self.assertRaisesRegex(AssertionError, 'publish-29 dispatch allowance exhausted'):
            self.authorize('publish-29')
        with self.assertRaisesRegex(AssertionError, 'release-29 dispatch allowance exhausted'):
            self.authorize('release-29')
        with self.assertRaisesRegex(AssertionError, 'wrong package 331 branch ref'):
            self.authorize('publish-29', GITHUB_REF='refs/tags/' + BRANCH)
        with self.assertRaisesRegex(AssertionError, 'wrong package 331 branch ref'):
            self.authorize('publish-29', GITHUB_REF=REF.upper())

    def test_the_publish_job_requires_both_caps_open(self):
        with patch.dict(LEDGER, publish_cap=1):
            with self.assertRaisesRegex(AssertionError, 'publish-29 dispatch allowance exhausted'):
                self.authorize('publish-29')
            with patch.dict(LEDGER['dispatch_caps'], {'publish-29': 1}):
                self.assertEqual(self.authorize('publish-29')['dispatch_counts']['publish-29'], 1)
                self.assertEqual(self.authorize('publish-29', mode='publish-ci')['publish_attempts'], [])
        with patch.dict(LEDGER['dispatch_caps'], {'publish-29': 1}):
            with self.assertRaisesRegex(AssertionError, 'ledger allows no publish'):
                self.authorize('publish-29')

    def test_closing_publish_preserves_spent_dispatch_and_upload_without_blocking_other_modes(self):
        self.runs.append(self.run_row('publish-29', 1, 'success'))
        self.jobs[1] = [dict(name='release-29', conclusion='success',
                             started_at='2026-11-22T00:00:00Z', completed_at='2026-11-22T00:01:00Z',
                             steps=[dict(name=guard.PUBLISH_STEP, conclusion='success', status='completed',
                                         started_at='2026-11-22T00:00:05Z', completed_at='2026-11-22T00:00:55Z')])]
        # Simulate the later lead-approved read-only allowances, with both publish caps closed.
        with patch.dict(LEDGER['dispatch_caps'], {'checks': 1, 'release-29': 1}), patch.dict(LEDGER, minute_cap=120):
            guard.configure('331')
            for kind in ('checks', 'release-29'):
                ledger = self.authorize(kind)
                self.assertEqual(ledger['dispatch_caps']['publish-29'], 0)
                self.assertEqual(ledger['publish_cap'], 0)
                self.assertEqual(ledger['dispatch_counts']['publish-29'], 1)
                self.assertEqual(ledger['dispatch_counts'][kind], 1)
                self.assertEqual(ledger['publish_attempts'], [dict(run=1, conclusion='success')])
                self.assertEqual(ledger['consumed_minutes'], 1)
            with self.assertRaisesRegex(AssertionError, 'publish-29 dispatch allowance exhausted'):
                self.authorize('publish-29')
            with patch.dict(LEDGER['dispatch_caps'], {'publish-29': 2}), patch.dict(LEDGER, publish_cap=1):
                with self.assertRaisesRegex(AssertionError, 'prior attempt reached publishing'):
                    self.authorize('publish-29')

    def test_early_failures_and_cancellations_spend_the_dispatch_without_an_upload(self):
        for kind in LEDGER['dispatch_caps']:
            for conclusion in ('failure', 'cancelled'):
                with self.subTest(kind=kind, conclusion=conclusion):
                    self.runs[:] = [self.run_row(kind, 1, conclusion)]
                    with patch.dict(LEDGER['dispatch_caps'], {kind: 1}):
                        with patch.object(guard, 'api', side_effect=self.api):
                            ledger = guard.budget(0)
                        self.assertEqual(ledger['dispatch_counts'][kind], 1)
                        self.assertEqual(ledger['runs'][0]['conclusion'], conclusion)
                        self.assertEqual(ledger['publish_attempts'], [])
                        with self.assertRaisesRegex(AssertionError, kind + ' dispatch allowance exhausted'):
                            self.authorize(kind)

    def test_an_untimed_cancelled_job_keeps_the_dispatch_and_charges_its_bound(self):
        kind = 'publish-29'
        self.runs.append(self.run_row(kind, 1, 'cancelled'))
        self.jobs[1] = [dict(name='release-29', conclusion='cancelled', steps=[])]
        with patch.dict(LEDGER, minute_cap=120, job_bounds={kind: 10}), patch.object(guard, 'api', side_effect=self.api):
            guard.configure('331')
            ledger = guard.budget(0)
        self.assertEqual(ledger['dispatch_counts'][kind], 1)
        self.assertEqual(ledger['consumed_minutes'], 10)
        self.assertEqual(ledger['publish_attempts'], [])
