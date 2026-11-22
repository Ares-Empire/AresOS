"""Package 331 dispatch boundaries and ledger accounting with fake Actions history."""

import contextlib
import io
import json
import os
import pathlib
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from test_owner_staged_release import condition
from test_release27 import workflow_expression
from test_release28 import WORKFLOW, inputs, run_name
import rehearsal_guard as guard
import registry_auth
from release_diff import IMAGE_SOURCES_29


BRANCH = 'pkg/331-release-29'
REF = 'refs/heads/' + BRANCH
PATH = '.github/workflows/os-image.yml'
SHA = 'a' * 40
LEDGER = guard.PACKAGES['331']
CHECKS_AUTH = 'checks-29-authorize'
PUBLISH_AUTH = 'release-29-authorize'
SELECTORS = {
    'publish-29': (PUBLISH_AUTH, '', {'inputs.release_29': True}),
    'dry-run-29': ('release-29-dry-run', '', {'inputs.dry_run_29': True}),
    'release-29-baseline': ('release-29-rehearsal', 'release-29-baseline', {}),
    'release-29': ('release-29-rehearsal', 'release-29', {}),
}


def selected(mode='', **changes):
    world = {'github.ref_name': BRANCH, f'needs.{CHECKS_AUTH}.result': 'skipped',
             f'needs.{PUBLISH_AUTH}.result': 'skipped'} | changes
    return {name for name, job in WORKFLOW['jobs'].items() if condition(job['if'], mode=mode, **world)}


class WorkflowTest(unittest.TestCase):
    def test_r29_modes_and_titles_only_select_their_exact_branch_jobs(self):
        dispatch = WORKFLOW['on']['workflow_dispatch']['inputs']
        for flag in ('release_29', 'dry_run_29'):
            self.assertEqual((dispatch[flag]['type'], dispatch[flag]['default']), ('boolean', 'false'))
        self.assertTrue(set(guard.R29_WALKS) <= set(dispatch['rehearsal']['options']))
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
                for other in ('probe', 'release-28', *guard.R29_WALKS):
                    self.assertEqual(selected(other, **flags), set())
        checks = {'inputs.checks_only': True, 'inputs.full_model': True}
        resolve = {'inputs.check_build': 'resolve'}
        self.assertEqual(selected(**resolve), {'check-build'})
        self.assertEqual(selected(**(checks | resolve)), set())
        self.assertEqual(selected(**{'inputs.check_build': 'build'}), set())
        self.assertEqual(selected('probe'), set())
        self.assertEqual(selected(**{'inputs.switch_from_run': '1'}), set())
        self.assertEqual(run_name(inputs() | collisions | {'inputs.rehearsal': 'release-29'}), LEDGER['titles']['publish-29'])
        world = inputs() | {'github.ref_name': BRANCH}
        self.assertEqual(run_name(world | checks), LEDGER['titles']['checks'])
        self.assertEqual(run_name(world | resolve), LEDGER['titles']['resolve'])
        for flags in ({}, checks | resolve, {'inputs.rehearsal': 'probe'},
                      {'inputs.dry_run_29': True, 'inputs.full_model': True}, {'inputs.check_build': 'build'}):
            with self.subTest(rejected=flags):
                self.assertEqual(selected(**flags), set())
                self.assertEqual(run_name(world | flags), 'OS image')
                self.assertEqual(run_name(world | flags | {'inputs.release_29': True}), LEDGER['titles']['publish-29'])
        for mode in ('release_29', 'dry_run_29'):
            for legacy in ('release_28', 'dry_run_28'):
                world = {'github.ref_name': 'pkg/42-release-28', 'inputs.' + mode: True, 'inputs.' + legacy: True}
                self.assertEqual(selected(**world), set())

    def test_r29_publish_stub_requires_success_and_is_read_only(self):
        job = WORKFLOW['jobs']['release-29']
        self.assertEqual(job['needs'], PUBLISH_AUTH)
        self.assertEqual(job['permissions'], {'contents': 'read'})
        stop, = job['steps']
        self.assertIn('exit 1', stop['run'])
        self.assertNotIn('secrets.', json.dumps(job))
        for status in ('success', 'failure', 'cancelled', 'skipped'):
            with self.subTest(status=status):
                flags = {'inputs.release_29': True, f'needs.{PUBLISH_AUTH}.result': status}
                expected = {PUBLISH_AUTH, 'release-29'} if status == 'success' else {PUBLISH_AUTH}
                self.assertEqual(selected(**flags), expected)

    def test_r29_guards_use_read_only_permissions_and_scoped_tokens(self):
        for kind, (job_name, _, _) in SELECTORS.items():
            with self.subTest(kind=kind):
                job = WORKFLOW['jobs'][job_name]
                permissions = {'contents': 'read', 'actions': 'read', 'packages': 'read'}
                self.assertEqual(job['permissions'], permissions)
                checkout, authorize, *remaining = job['steps']
                self.assertTrue(checkout['uses'].startswith('actions/checkout@'))
                walk = kind in guard.R29_WALKS
                self.assertEqual(checkout['with'], {'persist-credentials': 'false'} | ({'fetch-depth': '0'} if walk else {}))
                self.assertEqual(authorize['env'], {'GH_TOKEN': '${{ secrets.GITHUB_TOKEN }}',
                                 'REHEARSAL_MODE': '${{ inputs.rehearsal }}' if walk else kind})
                self.assertEqual(authorize['run'], f"python3 os/ci/rehearsal_guard.py ci {LEDGER['reservations'][kind]}")
                if kind == 'publish-29':
                    self.assertEqual(remaining, [])
                elif kind == 'dry-run-29':
                    stop, = remaining
                    self.assertIn('exit 1', stop['run'])
        job = WORKFLOW['jobs']['check-build']
        guard_step = job['steps'][1]
        self.assertTrue(condition(guard_step['if'], **{'github.ref_name': BRANCH}))
        self.assertEqual(guard_step['env']['REHEARSAL_MODE'], 'resolve')
        self.assertEqual(job['permissions'], {'contents': 'read', 'actions': 'read', 'packages': 'read'})

    def test_both_checks_jobs_need_the_combined_authorization_only_on_package_331(self):
        jobs = WORKFLOW['jobs']
        workers = {'regressions', 'model'}
        self.assertEqual(jobs[CHECKS_AUTH]['permissions'], {'contents': 'read', 'actions': 'read', 'packages': 'read'})
        checkout, reserve, receipt = jobs[CHECKS_AUTH]['steps']
        self.assertEqual(checkout['with'], {'persist-credentials': 'false'})
        self.assertEqual(reserve['env'], {'GH_TOKEN': '${{ secrets.GITHUB_TOKEN }}', 'REHEARSAL_MODE': 'checks'})
        minutes = sum(int(jobs[name]['timeout-minutes']) for name in workers | {CHECKS_AUTH})
        self.assertEqual(minutes, 100)
        self.assertEqual(reserve['run'], f'python3 os/ci/rehearsal_guard.py ci {minutes}')
        self.assertEqual(receipt['with']['path'], 'evidence/331-dispatch-authorization.json')
        for name in workers:
            self.assertEqual(jobs[name]['needs'], CHECKS_AUTH)
            for step in jobs[name]['steps']:
                if 'rehearsal_guard.py ci' in step.get('run', ''):
                    self.assertFalse(condition(step['if'], **{'github.ref_name': BRANCH}))
        for status in ('success', 'failure', 'cancelled', 'skipped'):
            with self.subTest(status=status):
                flags = {'inputs.checks_only': True, 'inputs.full_model': True, f'needs.{CHECKS_AUTH}.result': status}
                expected = workers | {CHECKS_AUTH} if status == 'success' else {CHECKS_AUTH}
                self.assertEqual(selected(**flags), expected)
        self.assertEqual(selected(**{'github.ref_name': 'pkg/42-release-28', 'inputs.checks_only': True}), workers)
        r28_guard = jobs['regressions']['steps'][1]
        self.assertTrue(condition(r28_guard['if'], **{'github.ref_name': 'pkg/42-release-28'}))
        reservation = r28_guard['run'].split('${{', 1)[1].removesuffix('}}')
        self.assertEqual(workflow_expression(reservation, inputs()), 60)

    def test_r29_vm_steps_and_artifacts_keep_baseline_and_qualification_distinct(self):
        job = WORKFLOW['jobs']['release-29-rehearsal']
        self.assertEqual(job['timeout-minutes'], '345')
        steps = job['steps']
        registry, = [i for i, step in enumerate(steps) if 'registry_auth.py baseline' in step.get('run', '')]
        iso, = [i for i, step in enumerate(steps) if 'installer_inspect.py' in step.get('run', '')]
        vm, = [i for i, step in enumerate(steps) if 'owner_vm.py release-29' in step.get('run', '')]
        self.assertLess(registry, iso)
        self.assertLess(iso, vm)
        self.assertNotIn('timeout-minutes', steps[vm])
        self.assertNotIn('GHCR_READ_TOKEN', json.dumps(job))
        self.assertNotIn('publish.sh', json.dumps(job))
        for mode in guard.R29_WALKS:
            with self.subTest(mode=mode):
                name = workflow_expression(job['name'].removeprefix('${{').removesuffix('}}'),
                                           inputs() | {'inputs.rehearsal': mode})
                self.assertEqual(LEDGER['job_bounds'][name], 345)
                eligible = [s for s in steps if not s.get('if') or condition(s['if'], mode=mode,
                            **{'steps.evidence.outputs.safe': 'true'})]
                verify = [s for s in eligible if 'verify_release.py' in s.get('run', '')]
                self.assertEqual(len(verify), int(mode == 'release-29'))
                receipts = [s['with']['name'] for s in eligible if 'receipt' in s.get('with', {}).get('name', '')]
                self.assertEqual(receipts, ['release-29-baseline-receipt' if mode.endswith('baseline')
                                            else 'release-29-qualifying-receipt'])


class LedgerTest(unittest.TestCase):
    def setUp(self):
        # Lead-approved allowances must not change the guard fixtures.
        self.enterContext(patch.dict(LEDGER, minute_cap=0, full_cap=0, part_b_cap=0, publish_cap=0,
                                    dispatch_caps=dict.fromkeys(LEDGER['reservations'], 0)))
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

    def authorize(self, kind, mode='ci', reserve=None, **context):
        if reserve is None:
            reserve = 0 if mode == 'publish-ci' else LEDGER['reservations'][kind]
        self.runs.append(self.run_row(kind, self.current, None))
        try:
            with tempfile.TemporaryDirectory() as tmp, contextlib.chdir(tmp), contextlib.redirect_stdout(io.StringIO()), \
                    patch.object(guard, 'api', side_effect=self.api), \
                    patch.dict(os.environ, self.environment | {'REHEARSAL_MODE': kind} | context, clear=True), \
                    patch.object(sys, 'argv', ['rehearsal_guard.py', mode, str(reserve)]):
                guard.main()
                return json.loads(pathlib.Path('evidence/331-dispatch-authorization.json').read_text())
        finally:
            self.runs.pop()

    def completed_checks(self, run_id=2):
        self.runs.append(self.run_row('checks', run_id, 'success'))
        start, end = '2026-11-22T00:00:05Z', '2026-11-22T00:01:05Z'
        self.jobs[run_id] = [
            dict(name=name, head_sha=SHA, conclusion='success', started_at=start, completed_at=end, steps=[
                dict(name=step, status='completed', conclusion='success', started_at=start, completed_at=end)])
            for name, step in ((guard.REGRESSIONS_JOB, 'Run regression and syntax checks'), (guard.MODEL_JOB, guard.MODEL_STEP))
        ]

    def test_zero_caps_and_a_same_named_tag_stop_the_current_job(self):
        self.assertEqual(LEDGER['dispatch_caps']['publish-29'], 0)
        self.assertEqual(LEDGER['publish_cap'], 0)
        self.assertEqual(LEDGER['dispatch_caps']['release-29'], 0)
        with patch.dict(LEDGER, minute_cap=345):
            with self.assertRaisesRegex(AssertionError, 'publish-29 dispatch allowance exhausted'):
                self.authorize('publish-29')
            with self.assertRaisesRegex(AssertionError, 'release-29 dispatch allowance exhausted'):
                self.authorize('release-29')
        with self.assertRaisesRegex(AssertionError, 'wrong package 331 branch ref'):
            self.authorize('publish-29', GITHUB_REF='refs/tags/' + BRANCH)
        with self.assertRaisesRegex(AssertionError, 'wrong package 331 branch ref'):
            self.authorize('publish-29', GITHUB_REF=REF.upper())

    def test_the_publish_job_requires_both_caps_open(self):
        with patch.dict(LEDGER, publish_cap=1, minute_cap=185):
            with self.assertRaisesRegex(AssertionError, 'publish-29 dispatch allowance exhausted'):
                self.authorize('publish-29')
            with patch.dict(LEDGER['dispatch_caps'], {'publish-29': 1}):
                self.assertEqual(self.authorize('publish-29')['dispatch_counts']['publish-29'], 1)
                self.assertEqual(self.authorize('publish-29', mode='publish-ci')['publish_attempts'], [])
                # GitHub's selector accepts this case variant. A successful guard is still required.
                with self.assertRaisesRegex(AssertionError, 'wrong package 331 branch ref'):
                    self.authorize('publish-29', GITHUB_REF='refs/heads/pkg/331-Release-29')
        with patch.dict(LEDGER['dispatch_caps'], {'publish-29': 1}), patch.dict(LEDGER, minute_cap=185):
            with self.assertRaisesRegex(AssertionError, 'ledger allows no publish'):
                self.authorize('publish-29')

    def test_closing_publish_preserves_spent_dispatch_and_upload_without_blocking_other_modes(self):
        self.runs.append(self.run_row('publish-29', 1, 'success'))
        self.jobs[1] = [dict(name='release-29', conclusion='success',
                             started_at='2026-11-22T00:00:00Z', completed_at='2026-11-22T00:01:00Z',
                             steps=[dict(name=guard.PUBLISH_STEP, conclusion='success', status='completed',
                                         started_at='2026-11-22T00:00:05Z', completed_at='2026-11-22T00:00:55Z')])]
        # Simulate the later lead-approved read-only allowances, with both publish caps closed.
        with patch.dict(LEDGER['dispatch_caps'], {'checks': 1, 'release-29': 1}), patch.dict(LEDGER, minute_cap=348):
            guard.configure('331')
            checks = self.authorize('checks')
            self.completed_checks()
            rehearsal = self.authorize('release-29')
            for ledger in (checks, rehearsal):
                self.assertEqual(ledger['dispatch_caps']['publish-29'], 0)
                self.assertEqual(ledger['publish_cap'], 0)
                self.assertEqual(ledger['dispatch_counts']['publish-29'], 1)
                self.assertEqual(ledger['dispatch_counts']['checks'], 1)
                self.assertEqual(ledger['publish_attempts'], [dict(run=1, conclusion='success')])
            self.assertEqual(checks['consumed_minutes'], 1)
            self.assertEqual(rehearsal['consumed_minutes'], 3)
            self.assertEqual(rehearsal['dispatch_counts']['release-29'], 1)
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
                    with patch.dict(LEDGER['dispatch_caps'], {kind: 1}), patch.dict(LEDGER, minute_cap=345):
                        guard.configure('331')
                        with patch.object(guard, 'api', side_effect=self.api):
                            ledger = guard.budget(0)
                        self.assertEqual(ledger['dispatch_counts'][kind], 1)
                        self.assertEqual(ledger['runs'][0]['conclusion'], conclusion)
                        self.assertEqual(ledger['publish_attempts'], [])
                        with self.assertRaisesRegex(AssertionError, kind + ' dispatch allowance exhausted'):
                            self.authorize(kind)

    def test_checks_reserve_both_workers_and_the_authorization_job(self):
        with patch.dict(LEDGER['dispatch_caps'], checks=1):
            with patch.dict(LEDGER, minute_cap=95):
                with self.assertRaisesRegex(AssertionError, r'0 \+ 100 reserved exceeds 95 minutes'):
                    self.authorize('checks')
                for reserve in (60, 35, 95):
                    with self.assertRaisesRegex(AssertionError, '100-minute reservation'):
                        self.authorize('checks', reserve=reserve)
            with patch.dict(LEDGER, minute_cap=100):
                ledger = self.authorize('checks')
                self.assertEqual(ledger['reserved_minutes'], 100)
                self.assertEqual(ledger['dispatch_counts']['checks'], 1)

    def test_rejected_titles_count_and_keep_any_timed_cost(self):
        world = inputs() | {'github.ref_name': BRANCH}
        rejected_title = run_name(world)
        collision = {'inputs.release_29': True, 'inputs.checks_only': True}
        self.runs.extend([
            dict(self.run_row('checks', 1, 'cancelled'), display_title=rejected_title),
            dict(self.run_row('checks', 2, 'failure'), display_title='Unrecognized dispatch title'),
            dict(self.run_row('publish-29', 3, 'failure'), display_title=run_name(world | collision)),
            dict(self.run_row('checks', 4, 'failure'), display_title='Two-disk rehearsal (part-b)'),
        ])
        start, end = '2026-11-22T00:00:05Z', '2026-11-22T00:01:05Z'
        self.jobs[2] = [dict(name='early failure', conclusion='failure', started_at=start, completed_at=end,
                             steps=[dict(name='Set up job', conclusion='failure', started_at=start, completed_at=end)])]
        with patch.dict(LEDGER['dispatch_caps'], checks=1), patch.dict(LEDGER, minute_cap=101):
            ledger = self.authorize('checks')
            self.assertEqual(ledger['dispatch_counts']['rejected'], 3)
            self.assertEqual(ledger['dispatch_counts']['publish-29'], 1)
            self.assertEqual(ledger['consumed_minutes'], 1)
            self.assertEqual(ledger['publish_attempts'], [])

    def test_untimed_failed_and_cancelled_jobs_charge_committed_bounds(self):
        kind = 'publish-29'
        self.runs.append(self.run_row(kind, 1, 'cancelled'))
        self.jobs[1] = [dict(name='release-29-authorize', conclusion='failure', steps=None),
                        dict(name='release-29', conclusion='cancelled', steps=[
                            dict(name='Set up job', started_at='2026-11-22T00:00:00Z',
                                 completed_at='2026-11-22T00:00:35Z')]),
                        dict(name='image', conclusion='failure', steps=[])]
        with patch.dict(LEDGER['dispatch_caps'], checks=1), patch.dict(LEDGER, minute_cap=645):
            ledger = self.authorize('checks')
        self.assertEqual(ledger['dispatch_counts'][kind], 1)
        self.assertEqual(ledger['consumed_minutes'], 545)
        self.assertEqual([job['rule'] for job in ledger['runs'][0]['jobs']], ['full-bound'] * 3)
        self.assertEqual(ledger['publish_attempts'], [])

    def test_separate_baseline_budget_and_same_head_checks(self):
        baseline, qualify = guard.R29_WALKS
        self.assertEqual(LEDGER['initial_dispatch_limits'], {'dry-run-29': 2, 'publish-29': 1, qualify: 3})
        with patch.dict(LEDGER['dispatch_caps'], {'checks': 1, baseline: 1}), patch.dict(LEDGER, minute_cap=447):
            with self.assertRaisesRegex(AssertionError, 'same-head regressions'):
                self.authorize(baseline)
            self.completed_checks()
            self.jobs[2][1]['steps'][0]['conclusion'] = 'skipped'
            with self.assertRaisesRegex(AssertionError, 'same-head regressions'):
                self.authorize(baseline)
            self.jobs[2][1]['steps'][0]['conclusion'] = 'success'
            self.runs[-1]['head_sha'] = 'b' * 40
            with self.assertRaisesRegex(AssertionError, 'same-head regressions'):
                self.authorize(baseline)
            self.runs[-1]['head_sha'] = SHA
            ledger = self.authorize(baseline)
            self.assertEqual(ledger['dispatch_counts'][baseline], 1)
            self.assertEqual(ledger['dispatch_counts'][qualify], 0)
            self.assertEqual(ledger['dispatch'], dict(mode=baseline, commit=SHA, run_id='50', attempt='1'))
            self.assertEqual(ledger['native']['run'], ledger['model']['run'])
            self.assertEqual(ledger['reserved_minutes'], 345)
            with self.assertRaisesRegex(AssertionError, 'release-29 dispatch allowance exhausted'):
                self.authorize(qualify)


class VerifyReleaseTest(unittest.TestCase):
    def test_r29_verification_binds_the_publish_job_and_recorded_source(self):
        source = 'b' * 40
        reference = 'ghcr.io/ares-empire/aresos@sha256:' + '29' * 32
        base = json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference']
        previous = json.loads(registry_auth.historical_records()['28'])
        record = dict(reference=reference, base=base, source_commit=source, visibility='private',
                      run='https://github.com/Ares-Empire/AresOS/actions/runs/29', tag='29-' + source,
                      daily_wheel=True, image_diff=dict(status='passed', unexplained=[], problems=[],
                          unexplained_count=0, base_ancestry_verified=True, pinned_base=base,
                          previous=previous['reference'], previous_source=previous['source_commit']),
                      signature=dict(method='cosign keyless', identity=registry_auth.R29_IDENTITY,
                                     issuer='https://token.actions.githubusercontent.com'),
                      job_token_read=dict(status='passed', reference=reference, secret='GITHUB_TOKEN',
                                          owner_token_used=False, visibility='private', manifest_read=True),
                      control=dict(source_revision=source, chrome_build='c' * 64),
                      source_trees=[dict(tree='d' * 40, path=path) for path in IMAGE_SOURCES_29])
        run = dict(head_branch=BRANCH, head_sha=source, path=PATH, event='workflow_dispatch',
                   display_title=LEDGER['titles']['publish-29'], run_attempt=1, status='completed', conclusion='success')
        step = dict(name=guard.PUBLISH_STEP, status='completed', conclusion='success')
        job = dict(name='release-29', head_sha=source, conclusion='success', steps=[step])
        env = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=guard.REPOSITORY,
                   GITHUB_REF=REF, GITHUB_REF_NAME=BRANCH, REHEARSAL_PACKAGE='331', REHEARSAL_MODE='release-29')
        original_text, original_bytes = pathlib.Path.read_text, pathlib.Path.read_bytes
        for near_miss in (None, 'baseline', 'tag', 'artifact', 'publish-step', 'attempt', 'source', 'old-run'):
            def output(argv):
                if argv[:2] == ['gh', 'api']:
                    if argv[-1].endswith('/jobs?per_page=100'):
                        changed = job | {'steps': [step | {'conclusion': 'skipped'}]} if near_miss == 'publish-step' else job
                        return json.dumps(dict(total_count=1, jobs=[changed])).encode()
                    changed = {'run_attempt': 2} if near_miss == 'attempt' else {}
                    if near_miss == 'old-run':
                        changed = {'head_branch': 'pkg/42-release-28'}
                    return json.dumps(run | changed).encode()
                if argv == ['git', 'rev-parse', '--is-shallow-repository']:
                    return b'false\n'
                self.assertIn(argv, [['git', 'rev-parse', source + ':' + path] for path in IMAGE_SOURCES_29])
                return (('e' if near_miss == 'source' else 'd') * 40 + '\n').encode()

            def read_text(path, *args, **kwargs):
                if path == pathlib.Path('evidence/release.json'):
                    return json.dumps(record | ({'tag': 'unrelated'} if near_miss == 'artifact' else {}))
                return original_text(path, *args, **kwargs)

            def read_bytes(path):
                if path == pathlib.Path('os/manifest/releases/29.json'):
                    return json.dumps(record).encode()
                return original_bytes(path)

            context = {'REHEARSAL_MODE': 'release-29-baseline'} if near_miss == 'baseline' else (
                       {'GITHUB_REF': 'refs/tags/' + BRANCH} if near_miss == 'tag' else {})
            expected = AssertionError if near_miss else SystemExit
            with self.subTest(near_miss=near_miss), patch.dict(os.environ, env | context, clear=True), \
                    patch.object(sys, 'argv', ['verify_release.py', '29']), \
                    patch.object(pathlib.Path, 'read_text', read_text), patch.object(pathlib.Path, 'read_bytes', read_bytes), \
                    patch.object(subprocess, 'check_output', side_effect=output), \
                    patch.object(subprocess, 'run', return_value=subprocess.CompletedProcess([], 0)), \
                    contextlib.redirect_stdout(io.StringIO()) as printed, self.assertRaises(expected):
                runpy.run_path('os/ci/verify_release.py', run_name='__main__')
            if near_miss is None:
                self.assertIn('Qualified R29 private publish', printed.getvalue())
