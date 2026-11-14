"""Package 22c, stage 0: the reorder probe's wiring and its own logic.

The wiring half holds every list that names packages 14, 16 and 27 to package 22c as well, for
every VM mode in package 22c's ledger (os/ci/rehearsal-packages.json): stage 2 adds its rehearsal
mode there and these tests then demand the rest. The probe half runs the real control flow of
os/ci/reorder_probe.py over a modelled disk and shows that each expectation of the brief (P6) is
recorded as contradicted when the disk behaves otherwise. No VM, privilege or real `ostree` runs.
"""
import contextlib
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import model_scope
import owner_media
import owner_vm
import registry_auth
import rehearsal_guard as guard
import reorder_probe as rp
import test_owner_walk as walk
import test_release27 as base
from test_owner_staged_release import condition

BRANCH = 'pkg/22c-ways-back-after-update'
LEDGER = guard.PACKAGES['22c']
VM_MODES = tuple(mode for mode in LEDGER['dispatch_caps'] if mode != 'checks')
WORKFLOW = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
JOB = WORKFLOW['jobs']['rehearsal']
OTHER_MODES = ('inspect', 'fixture', 'probe', 'part-b', 'keyboard', 'owner-tools', 'update')


def inputs(mode):
    return dict(base.UPDATE_INPUTS, **{'github.ref_name': BRANCH, 'inputs.rehearsal': mode})


def job_steps(mode):
    """Each step of the rehearsal job that runs for this mode on package 22c's branch, with its environment."""
    world = inputs(mode)
    github = dict(base.UPDATE_GITHUB, GITHUB_REF_NAME=BRANCH)
    merged = {**WORKFLOW.get('env', {}), **JOB.get('env', {})}
    environment = dict(github, **{k: base.workflow_text(v, world) for k, v in merged.items()})
    for step in JOB['steps']:
        if 'run' in step and base.workflow_expression(step.get('if', 'success()'), world):
            yield step, dict(environment, **{k: base.workflow_text(v, world) for k, v in step.get('env', {}).items()})


class DispatchTest(unittest.TestCase):
    def test_the_ledger_names_the_probe_and_every_mode_is_a_workflow_option_with_its_title(self):
        self.assertIn('reorder-probe', VM_MODES)
        options = WORKFLOW['on']['workflow_dispatch']['inputs']['rehearsal']['options']
        for mode in VM_MODES:
            with self.subTest(mode=mode):
                self.assertIn(mode, options)
                self.assertEqual(LEDGER['titles'][mode], f'Two-disk rehearsal ({mode})')
                self.assertIn("format('Two-disk rehearsal ({0})', inputs.rehearsal)", WORKFLOW['run-name'])
        self.assertEqual(LEDGER['titles']['checks'], 'OS regressions only (no VM)')
        self.assertEqual(base.workflow_expression(re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['env']['REHEARSAL_PACKAGE'].strip())[1],
                                                  inputs(VM_MODES[0])), '22c')

    def test_package_22c_modes_run_the_rehearsal_job_on_its_branch_and_nothing_else_runs_there(self):
        on_branch = {'github.ref_name': BRANCH}
        for name, job in WORKFLOW['jobs'].items():
            for mode in VM_MODES:
                with self.subTest(job=name, mode=mode):
                    self.assertEqual(condition(job['if'], mode=mode, **on_branch), name == 'rehearsal')
                    # Never together with another kind of dispatch.
                    for other in ('inputs.release_13', 'inputs.release_27', 'inputs.checks_only',
                                  'inputs.switch_from_run', 'inputs.probe_run'):
                        self.assertFalse(condition(job['if'], mode=mode, **on_branch, **{other: True}) and name == 'rehearsal')
                    self.assertFalse(condition(job['if'], mode=mode, **on_branch, **{'inputs.check_build': 'build'})
                                     and name == 'rehearsal')
            for mode in OTHER_MODES:
                with self.subTest(job=name, other_mode=mode):
                    self.assertFalse(condition(job['if'], mode=mode, **on_branch))
            with self.subTest(job=name, checks=True):
                # Checks only: the regressions and, beside them, the full ways-back model when its sources changed (22c, 1b).
                self.assertEqual(condition(job['if'], mode='', **on_branch, **{'inputs.checks_only': True}), name in ('regressions', 'model'))
                self.assertFalse(condition(job['if'], mode='', **on_branch))

    def test_no_other_branch_can_run_a_package_22c_mode(self):
        for branch in ('main', 'pkg/27-first-update-release', 'pkg/14-owner-tools', 'pkg/16-staged-release',
                       'pkg/13-keyboard-layout', 'pkg/23-minecraft-starts'):
            for name, job in WORKFLOW['jobs'].items():
                for mode in VM_MODES:
                    with self.subTest(branch=branch, job=name, mode=mode):
                        self.assertFalse(condition(job['if'], mode=mode, **{'github.ref_name': branch}))


class SuiteJobsTest(unittest.TestCase):
    """Stage 1b, additions 1 and 2: every job that runs the whole suite runs its namespace tests
    (test_owner_update.ToolsUpdateTest skips silently without the step) and explores the model's slice."""
    NAMESPACES = ('sudo sysctl -w kernel.apparmor_restrict_unprivileged_userns=0\n'
                  'unshare -Urm true\n')

    def test_each_suite_job_allows_user_namespaces_before_its_tests_and_explores_the_slice(self):
        suites = {}
        for name, job in WORKFLOW['jobs'].items():
            steps = job['steps']
            runs = [i for i, step in enumerate(steps) if 'unittest discover -s os/tests -v' in step.get('run', '')]
            if not runs:
                continue
            suite, = runs
            allow = [i for i, step in enumerate(steps) if step.get('name') == 'Allow unprivileged user namespaces on disposable runner']
            with self.subTest(job=name):
                self.assertEqual(len(allow), 1)
                self.assertLess(allow[0], suite)
                self.assertEqual(steps[allow[0]]['run'], self.NAMESPACES)
                self.assertNotIn('if', steps[allow[0]])
                self.assertEqual(steps[suite]['env']['ARESOS_MODEL_SCOPE'], 'slice')
            suites[name] = steps[suite]['name']
        self.assertEqual(suites, {'regressions': 'Run regression and syntax checks', 'image': 'Install tools on disposable runner',
                                  'rehearsal': guard.NATIVE_STEP})

class JobGatesTest(unittest.TestCase):
    """Every script the rehearsal job runs for a package 22c mode accepts the environment the job gives it
    (test_release27.UpdateJobGatesTest's scan, for this branch: package 27's first runs died on such gates)."""

    def test_every_step_script_accepts_the_package_22c_environment(self):
        for mode in VM_MODES:
            failures, evaluated = [], set()
            for step, environment in job_steps(mode):
                for script, argv, removed in base.step_runs(step, environment, inputs(mode)):
                    scan = base.GateScan({k: v for k, v in environment.items() if k not in removed}, argv)
                    for path, line, text, passed in scan.run(script):
                        evaluated.add(path)
                        if not passed:
                            failures.append(f"{step['name']}: {path}:{line}: {text}")
            with self.subTest(mode=mode):
                self.assertEqual(failures, [])
                self.assertLessEqual({'os/ci/owner_capabilities.py', 'os/ci/owner_devices.py', 'os/ci/owner_media.py',
                                      'os/ci/registry_auth.py', 'os/ci/rehearsal_guard.py', 'os/ci/owner_vm.py'}, evaluated)

    def test_the_steps_scripts_arguments_and_bounds_are_package_22cs(self):
        for mode in VM_MODES:
            steps = list(job_steps(mode))
            runs = {(script, tuple(argv[1:])) for step, environment in steps
                    for script, argv, _ in base.step_runs(step, environment, inputs(mode))}
            bound = str(LEDGER['job_bounds'][mode])
            with self.subTest(mode=mode):
                self.assertEqual(steps[0][1]['REHEARSAL_PACKAGE'], '22c')
                for expected in (('os/ci/owner_capabilities.py', ()), ('os/ci/rehearsal_guard.py', ('probe-budget-ci', bound)),
                                 ('os/ci/rehearsal_guard.py', ('ci', bound)), ('os/ci/registry_auth.py', ('create',)),
                                 ('os/ci/registry_auth.py', ('preflight',)), ('os/ci/registry_auth.py', ('pull',)),
                                 ('os/ci/registry_auth.py', ('cleanup',)), ('os/ci/owner_devices.py', ()),
                                 ('os/ci/owner_counter_kernel.py', ()), ('os/ci/installer_inspect.py', ()),
                                 ('os/ci/prepare_two_disks.py', ()), ('os/ci/owner_vm.py', (mode,))):
                    self.assertIn(expected, runs)
                self.assertTrue(any(script == 'os/ci/registry_auth.py' and argv[:1] == ('signature',) for script, argv in runs))
                # Neither another package's VM driver nor the owner-secret credential steps run.
                self.assertFalse({script for script, _ in runs} & {'os/ci/keyboard_vm.py', 'os/ci/two_disk_vm.py',
                                                                 'os/ci/rehearsal_auth.py'})
                names = [step['name'] for step, _ in steps]
                self.assertLess(names.index(guard.NATIVE_STEP), names.index('Require completed native preflight before any package 13 VM'))
                # The job bound is the ledger's; the VM step ends before the job does; a hosted job ends at 360.
                world = inputs(mode)
                self.assertEqual(base.workflow_text(JOB['timeout-minutes'], world), bound)
                vm, = [step for step, _ in steps if 'os/ci/owner_vm.py' in step['run']]
                self.assertLess(int(base.workflow_text(vm['timeout-minutes'], world)), int(bound))
                self.assertLessEqual(int(bound), 360)
                self.assertTrue(all('secrets.GHCR_READ_TOKEN' not in json.dumps(step) for step, _ in steps))


# Decisions where package 22c's probe deliberately differs from package 27's update rehearsal
# (or that no literal can settle), each with its reason. Everything else must decide alike.
REVIEWED = {
    ('os/ci/owner_vm.py', "authorization['allowance'] == package"): "the guard's dispatch authorization names the running package",
    ('os/ci/owner_vm.py', "{'16': 'os/manifest/ci/16/host-walk.json', '27': 'os/manifest/ci/27/host-walk.json', "
                          "'22c': 'os/manifest/ci/22c/host-walk.json'}.get(package, 'os/manifest/ci/14/host-walk/result.json')"):
        "each package's own host walk",
    ('os/ci/owner_vm.py', "package == '27'"): 'package 27 recorded its bound sources; package 22c does so in stage 2',
    ('os/ci/owner_vm.py', "mode == 'update'"): "package 27's route after release 27 is confirmed",
    ('os/ci/owner_vm.py', "mode == 'reorder-probe'"): 'the probe leaves the shared route after release 27 is confirmed',
    ('os/ci/rehearsal_auth.py', "mode in ('probe', 'part-b') or release_diff"):
        'owner-secret auth: its create, preflight and pull steps do not run on this branch',
}


# The same for stage 2's rehearsal: it leaves the shared route where the probe does, records its
# bound sources as package 27 did, and takes its own way from release 27 confirmed.
REVIEWED_REHEARSAL = {key: reason for key, reason in REVIEWED.items() if key[1] != "mode == 'reorder-probe'"}
REVIEWED_REHEARSAL[('os/ci/owner_vm.py', "package == '27'")] = "package 27 recorded its bound sources under its own key; package 22c's rehearsal does below"
REVIEWED_REHEARSAL[('os/ci/owner_vm.py', "mode == 'ways-back'")] = \
    "the rehearsal records its bound sources (22c-bound-sources) and walks brief E's route after release 27 is confirmed"


class DecisionsTest(unittest.TestCase):
    def test_the_probe_decides_like_package_27s_update_rehearsal_except_where_reviewed(self):
        probe = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='reorder-probe', GITHUB_REF_NAME=BRANCH,
                     argv=['os/ci/owner_vm.py', 'reorder-probe'])
        differing, used, paths = base.differing_decisions([probe, base.WORLDS['update']], REVIEWED)
        self.assertEqual(differing, [])
        self.assertEqual(sorted(set(REVIEWED) - used), [], 'stale reviewed decisions')
        self.assertIn('os/ci/reorder_probe.py', paths)

    def test_the_rehearsal_decides_like_package_27s_update_rehearsal_except_where_reviewed(self):
        rehearsal = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='ways-back', GITHUB_REF_NAME=BRANCH,
                         argv=['os/ci/owner_vm.py', 'ways-back'])
        differing, used, paths = base.differing_decisions([rehearsal, base.WORLDS['update']], REVIEWED_REHEARSAL)
        self.assertEqual(differing, [])
        self.assertEqual(sorted(set(REVIEWED_REHEARSAL) - used), [], 'stale reviewed decisions')
        self.assertIn('os/ci/reorder_probe.py', paths)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        guard.configure('22c')
        self.addCleanup(guard.configure, '11c')

    def history(self, runs, job=None):
        job = job or dict(name='Pinned live ISO inspection and two-disk rehearsal', conclusion='success',
                          started_at='2026-11-13T18:00:00Z', completed_at='2026-11-13T20:00:00Z',
                          steps=[dict(name='Set up job', conclusion='success', started_at='2026-11-13T18:00:00Z',
                                      completed_at='2026-11-13T20:00:00Z')])
        return patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=runs) if path.startswith('actions/runs?')
                            else dict(total_count=1, jobs=[job]))

    def run_row(self, number, kind, **more):
        return dict(dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='completed', conclusion='success',
                         created_at='2026-11-13T18:00:00Z', id=number, display_title=LEDGER['titles'][kind]), **more)

    def test_the_brief_budget_is_the_ledger(self):
        self.assertEqual((guard.BRANCH, guard.MINUTE_CAP, guard.FULL_CAP, guard.PART_B_CAP), (BRANCH, 1200, 0, 0))
        self.assertEqual(LEDGER['vm_dispatch_cap'], 4)
        self.assertEqual(LEDGER['publish_cap'], 0)
        self.assertEqual(set(LEDGER['titles']), set(LEDGER['dispatch_caps']))
        self.assertEqual(set(LEDGER['job_bounds']), set(LEDGER['dispatch_caps']))
        self.assertTrue(all(LEDGER['dispatch_caps'][mode] <= LEDGER['vm_dispatch_cap'] for mode in VM_MODES))

    def test_four_vm_dispatches_in_all_whatever_their_modes(self):
        runs = [self.run_row(n, 'reorder-probe') for n in range(1, 5)] + [self.run_row(9, 'checks')]
        with self.history(runs):
            result = guard.budget(0)
            self.assertEqual(result['dispatch_counts'], {'checks': 1, **{mode: 4 if mode == 'reorder-probe' else 0 for mode in VM_MODES}})
            runs.append(self.run_row(5, 'reorder-probe'))
            with self.assertRaisesRegex(AssertionError, 'reorder-probe dispatch allowance exhausted'):
                guard.budget(0)
        # The second VM mode (stage 2's rehearsal) shares the same four: the probe used one, three remain.
        self.assertEqual(VM_MODES, ('reorder-probe', 'ways-back'))
        self.assertEqual(LEDGER['dispatch_caps']['ways-back'], 3)
        runs = [self.run_row(1, 'reorder-probe'), self.run_row(2, 'ways-back'), self.run_row(3, 'ways-back'), self.run_row(4, 'ways-back')]
        with self.history(runs):
            self.assertEqual(guard.budget(0)['dispatch_counts'], {'checks': 0, 'reorder-probe': 1, 'ways-back': 3})
            runs.append(self.run_row(5, 'reorder-probe'))
            with self.assertRaisesRegex(AssertionError, 'VM dispatch allowance exhausted'):
                guard.budget(0)

    def test_minutes_count_every_run_and_an_unaccountable_job_costs_its_whole_bound(self):
        runs = [self.run_row(1, 'reorder-probe'), self.run_row(2, 'checks')]
        with self.history(runs):
            # Two accounted hours each (the modelled job), then the reservation must still fit 1200.
            self.assertEqual(guard.budget(345)['consumed_minutes'], 240)
            with self.assertRaisesRegex(AssertionError, 'exceeds 1200'):
                guard.budget(961)
        with self.history([self.run_row(1, 'reorder-probe')], job=dict(name='x', conclusion='failure', steps=[])):
            self.assertEqual(guard.budget(0)['consumed_minutes'], LEDGER['job_bounds']['reorder-probe'])
        with self.history([self.run_row(1, 'reorder-probe', run_attempt=2)]):
            with self.assertRaisesRegex(AssertionError, 'a rerun is an additional dispatch'):
                guard.budget(0)

    def test_every_vm_mode_proves_its_native_step_in_its_own_run(self):
        for mode in VM_MODES:
            with self.subTest(mode=mode):
                self.assertTrue(guard.own_native(mode))
                self.assertEqual(guard.native_gate(mode, 'probe-budget-ci', dict(runs=[]), 'a' * 40)['status'], 'pending')
                with self.assertRaisesRegex(AssertionError, 'no current probe native preflight'):
                    guard.native_gate(mode, 'ci', dict(runs=[]), 'a' * 40)
                # A passing checks-only run on the same head also proves it; two of them stop.
                checks = dict(title=LEDGER['titles']['checks'], sha='a' * 40, conclusion='success', run=7)
                self.assertEqual(guard.native_gate(mode, 'ci', dict(runs=[checks]), 'a' * 40),
                                 dict(status='passed', sha='a' * 40, run=7, source='checks-only dispatch'))
                with self.assertRaisesRegex(AssertionError, 'duplicate native checks'):
                    guard.native_gate(mode, 'ci', dict(runs=[checks, dict(checks, run=8)]), 'a' * 40)
        self.assertFalse(guard.own_native('checks'))
        guard.configure('27')
        self.assertFalse(guard.own_native('reorder-probe'))
        self.assertTrue(guard.own_native('update'))

    def test_the_guard_step_reserves_and_writes_package_22cs_authorization(self):
        run = self.run_row(11, 'reorder-probe', status='in_progress', conclusion=None, head_branch=BRANCH)
        environment = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='reorder-probe', GITHUB_RUN_ID='11', GITHUB_SHA='a' * 40,
                           GITHUB_REF_NAME=BRANCH)
        proof = dict(complete=True, ids_count=1, total_count=1)
        # The model's sources unchanged (the full-model gate has its own tests below).
        with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder), patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch('builtins.print'), \
                patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=[run], history=proof)
                             if path.startswith('actions/runs?') else run), \
                patch.object(model_scope, 'decide', return_value=('slice', ['unchanged'])):
            guard.main()
            written = json.loads(pathlib.Path('evidence/22c-dispatch-authorization.json').read_text())
        self.assertEqual((written['allowance'], written['reserved_minutes'], written['native']['status']), ('22c', 345, 'pending'))
        self.assertEqual(written['dispatch_counts']['reorder-probe'], 1)
        self.assertEqual(written['model'], dict(status='not-needed', scope='slice', reasons=['unchanged']))
        with patch.dict(os.environ, dict(environment, REHEARSAL_MODE='checks'), clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch.object(guard, 'budget') as budget:
            budget.return_value = dict(history=proof, runs=[], dispatch_counts={})
            with self.assertRaisesRegex(AssertionError, 'native deferral is only for probe budget reservation'):
                guard.main()

    # Review 4, finding 4: changed model sources need the full model passed on the same head.
    SHA = 'a' * 40
    T0, T1 = '2026-11-13T18:00:00Z', '2026-11-13T18:20:00Z'
    FULL = ('full', ['os/owner-tools/owner.py', 'os/tests/ways_back_ledger.py'])

    def job(self, name, steps, sha=SHA):
        return dict(name=name, head_sha=sha, conclusion='success', started_at=self.T0, completed_at=self.T1,
                    steps=[dict(name=step, status='completed', conclusion=conclusion, started_at=self.T0, completed_at=self.T1)
                           for step, conclusion in steps])

    def checks_jobs(self, full='success', sha=SHA, name=guard.MODEL_JOB):
        """A checks-only run's two jobs; the model job's full step passed, was skipped (the slice) or failed."""
        regressions = self.job('Regression checks only (no image build or VM)', [('Run regression and syntax checks', 'success')], sha)
        model = self.job(name, [('Decide between the full model and the bounded slice', 'success'), (guard.MODEL_STEP, full)], sha)
        return dict(total_count=2, jobs=[regressions, model])

    def test_the_model_gate_reads_the_model_jobs_full_step_by_its_workflow_names(self):
        model = WORKFLOW['jobs']['model']
        self.assertEqual(model['name'], guard.MODEL_JOB)
        step, = [s for s in model['steps'] if s.get('name') == guard.MODEL_STEP]
        self.assertEqual(step['if'], "steps.scope.outputs.scope == 'full'")
        self.assertEqual(step['env'], {'ARESOS_MODEL_SCOPE': 'full'})
        self.assertIn('-k test_reachable_state_space', step['run'])
        # The comment beside the rehearsal's slice names the gate that now enforces it.
        native, = [s for s in JOB['steps'] if s.get('name') == guard.NATIVE_STEP]
        self.assertEqual(native['env']['ARESOS_MODEL_SCOPE'], 'slice')
        self.assertIn('rehearsal_guard.model_gate', (ROOT / '.github/workflows/os-image.yml').read_text())

    def test_changed_model_sources_need_the_full_model_passed_on_the_same_head(self):
        checks = dict(title=LEDGER['titles']['checks'], sha=self.SHA, conclusion='success', run=7)
        path = 'actions/runs/7/jobs?per_page=100'

        def gate(runs, jobs, scope=self.FULL):
            with patch.object(model_scope, 'decide', return_value=scope), \
                    patch.object(guard, 'api', side_effect=lambda p: jobs[p]) as api:
                return guard.model_gate(dict(runs=runs), self.SHA), api

        # Unchanged sources: nothing required and nothing read.
        result, api = gate([], {}, ('slice', ['no dependency of the full model changed']))
        self.assertEqual(result['status'], 'not-needed')
        api.assert_not_called()
        # Changed: a passing checks-only run on this head whose model job passed the full step.
        result, _ = gate([checks], {path: self.checks_jobs()})
        self.assertEqual((result['status'], result['scope'], result['run'], result['job'], result['step']),
                         ('passed', 'full', 7, guard.MODEL_JOB, guard.MODEL_STEP))
        self.assertEqual(result['reasons'], self.FULL[1])
        for case, runs, jobs in (
                ('no checks-only run', [], {}),
                ('the slice was chosen there', [checks], {path: self.checks_jobs('skipped')}),
                ('the full model failed', [checks], {path: self.checks_jobs('failure')}),
                ('another head', [dict(checks, sha='b' * 40)], {}),
                ('a failed checks-only run', [dict(checks, conclusion='failure')], {}),
                ('the job of another head', [checks], {path: self.checks_jobs(sha='b' * 40)}),
                ('a step of that name in another job', [checks], {path: self.checks_jobs(name='Regression checks only (no image build or VM)')})):
            with self.subTest(case), self.assertRaisesRegex(AssertionError, 'STOP: the full ways-back model has not passed on this head'):
                gate(runs, jobs)

    def test_a_direct_vm_dispatch_stops_before_its_minutes_and_its_vm_without_the_full_model(self):
        """The reviewer's case: a VM dispatch with no checks-only run on its head. Its own native step
        used to be enough; now both guard steps (the budget and the gate before any VM) stop while the
        head changed the model's sources, and pass with unchanged sources or the full model passed."""
        current = self.run_row(11, 'reorder-probe', status='in_progress', conclusion=None, head_branch=BRANCH,
                               path='.github/workflows/os-image.yml')
        native = dict(total_count=1, jobs=[self.job('Pinned live ISO inspection and two-disk rehearsal', [(guard.NATIVE_STEP, 'success')])])
        checks = self.run_row(7, 'checks', head_branch=BRANCH)

        def main(mode, runs, scope):
            environment = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='reorder-probe', GITHUB_RUN_ID='11', GITHUB_SHA=self.SHA,
                               GITHUB_REF_NAME=BRANCH)
            answers = {'actions/runs/11': current, 'actions/runs/11/jobs?per_page=100': native,
                       'actions/runs/7/jobs?per_page=100': self.checks_jobs()}
            proof = dict(complete=True, ids_count=len(runs), total_count=len(runs))
            api = lambda path: dict(workflow_runs=runs, history=proof) if path.startswith('actions/runs?') else answers[path]
            with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder), patch.dict(os.environ, environment, clear=True), \
                    patch.object(sys, 'argv', ['rehearsal_guard.py', mode, '345']), patch('builtins.print'), \
                    patch.object(guard, 'api', side_effect=api), patch.object(model_scope, 'decide', return_value=scope):
                guard.main()
                return json.loads(pathlib.Path('evidence/22c-dispatch-authorization.json').read_text())

        for mode, native_status in (('probe-budget-ci', 'pending'), ('ci', 'passed')):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(AssertionError, 'STOP: the full ways-back model has not passed on this head'):
                    main(mode, [current], self.FULL)
                # Unchanged sources: the direct dispatch passes as before (in ci through its own native step).
                written = main(mode, [current], ('slice', ['unchanged']))
                self.assertEqual((written['native']['status'], written['model']['status']), (native_status, 'not-needed'))
                # Changed sources and a passing full model on this head: it passes, naming that run.
                written = main(mode, [current, checks], self.FULL)
                self.assertEqual((written['model']['status'], written['model']['run']), ('passed', 7))


class RunnerTest(unittest.TestCase):
    ENVIRONMENT = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=guard.REPOSITORY,
                       GITHUB_REF_NAME=BRANCH, REHEARSAL_PACKAGE='22c')

    def test_runner_and_registry_accept_only_package_22cs_branch_package_and_modes(self):
        for mode in VM_MODES:
            environment = dict(self.ENVIRONMENT, REHEARSAL_MODE=mode)
            with self.subTest(mode=mode), patch.dict(os.environ, environment, clear=True):
                owner_media.require_runner()
                registry_auth.require_dispatch()
            for key, value in (('GITHUB_REF_NAME', 'pkg/27-first-update-release'), ('GITHUB_REF_NAME', 'main'),
                               ('REHEARSAL_PACKAGE', '27'), ('REHEARSAL_PACKAGE', '14'), ('REHEARSAL_MODE', 'update'),
                               ('REHEARSAL_MODE', 'probe'), ('REHEARSAL_MODE', 'owner-tools'), ('REHEARSAL_MODE', 'checks'),
                               ('GITHUB_REPOSITORY', 'elsewhere/AresOS')):
                with self.subTest(mode=mode, key=key, value=value), patch.dict(os.environ, dict(environment, **{key: value}), clear=True):
                    with self.assertRaises(AssertionError):
                        owner_media.require_runner()
                    with self.assertRaises(AssertionError):
                        registry_auth.require_dispatch()

    def main(self, package, mode, branch, files=None, any_runner=False):
        """owner_vm.main up to the walk check, with the evidence files a passed native step leaves."""
        native = dict(status='passed', sha='a' * 40)
        capabilities = dict(status='passed', sha='a' * 40, checks={name: True for name in __import__('owner_capabilities').CHECKS})
        given = {'evidence/' + package + '-dispatch-authorization.json': json.dumps(dict(allowance=package, native=native)),
                 'evidence/14-host-capabilities.json': json.dumps(capabilities)}
        given.update(files or {})
        original = pathlib.Path.read_text
        read = lambda path, *a, **k: given[path.as_posix()] if path.as_posix() in given else original(path, *a, **k)
        environment = dict(self.ENVIRONMENT, GITHUB_REF_NAME=branch, REHEARSAL_PACKAGE=package, REHEARSAL_MODE=mode, GITHUB_SHA='a' * 40)
        # The first host work after the gates (the evidence folder) ends the call: nothing global is touched.
        past = Mock(mkdir=Mock(side_effect=RuntimeError('past the gates')))
        with patch.dict(os.environ, environment, clear=True), patch.object(sys, 'argv', ['owner_vm.py', mode]), \
                patch('pathlib.Path.read_text', read), patch.object(owner_vm.td, 'EVIDENCE', past), \
                patch.object(owner_vm, 'Media') as media, contextlib.ExitStack() as stack:
            if any_runner:
                stack.enter_context(patch.object(owner_media, 'require_runner'))
            try:
                owner_vm.main()
            finally:
                media.assert_not_called()

    def test_the_driver_keeps_each_route_to_its_package(self):
        # The runner check refuses first; the driver's own check refuses too (shown with the runner check set aside).
        for package, mode, branch, message in (
                ('27', 'reorder-probe', 'pkg/27-first-update-release', 'the update rehearsal is package 27 only'),
                ('14', 'reorder-probe', 'pkg/14-owner-tools', 'are package 22c only'),
                ('27', 'ways-back', 'pkg/27-first-update-release', 'the update rehearsal is package 27 only'),
                ('14', 'ways-back', 'pkg/14-owner-tools', 'are package 22c only'),
                ('22c', 'update', BRANCH, 'the update rehearsal is package 27 only'),
                ('22c', 'owner-tools', BRANCH, 'are package 22c only'),
                ('22c', 'probe', BRANCH, 'are package 22c only')):
            with self.subTest(package=package, mode=mode):
                with self.assertRaises(AssertionError):
                    self.main(package, mode, branch)
                with self.assertRaisesRegex(AssertionError, message):
                    self.main(package, mode, branch, any_runner=True)

    def test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one(self):
        # With a fresh receipt the driver passes every gate and reaches its first host work.
        for mode in VM_MODES:
            with self.subTest(mode=mode), self.assertRaisesRegex(RuntimeError, 'past the gates'):
                self.main('22c', mode, BRANCH)
        walk_path = 'os/manifest/ci/22c/host-walk.json'
        receipt = json.loads((ROOT / walk_path).read_text())
        receipt['sources'][0] = dict(receipt['sources'][0], sha256='0' * 64)
        with self.assertRaisesRegex(AssertionError, 'Host walk is stale'):
            self.main('22c', 'reorder-probe', BRANCH, {walk_path: json.dumps(receipt)})


class HostWalkReceiptTest(unittest.TestCase):
    PATH = ROOT / 'os/manifest/ci/22c/host-walk.json'

    def test_the_receipt_is_this_packages_and_binds_the_probe(self):
        receipt = json.loads(self.PATH.read_text())
        self.assertEqual((receipt['status'], receipt['stick_across_reboot']), ('passed', False))
        self.assertEqual(receipt['stages'], {'reorder-probe': walk.PROBE_STAGES, 'ways-back': walk.WAYS_BACK_STAGES})
        self.assertEqual(set(receipt['set_default_indexes']), set(VM_MODES))
        paths = [row['path'] for row in receipt['sources']]
        self.assertEqual(paths, sorted(set(paths)))
        for needed in ('os/ci/reorder_probe.py', 'os/ci/owner_vm.py', 'os/ci/grub_bls.py', 'os/ci/keyboard_entries.py',
                       'os/tests/test_owner_walk.py', 'os/tests/test_ways_back_probe.py', '.github/workflows/os-image.yml',
                       'os/ci/rehearsal-packages.json', 'reviews/22c-ways-back-after-update/walk-host.py',
                       # The rehearsal route's answers come from the tools over test_ways_back's machine.
                       'os/owner-tools/owner.py', 'os/release/start-next.sh', 'os/tests/test_ways_back.py',
                       'os/tests/test_owner_update.py', 'os/tests/ways_back_keyboard.py'):
            self.assertIn(needed, paths)
        previous = json.loads((ROOT / 'os/manifest/ci/27/host-walk.json').read_text())
        self.assertLessEqual({row['path'] for row in previous['sources'] if (ROOT / row['path']).is_file()}, set(paths))

    @unittest.skipIf((ROOT / 'os/manifest/ci/22c/source-bindings.json').exists(), "historical once package 22c's rehearsal recorded its bindings")
    def test_the_receipt_is_fresh_so_a_dispatch_does_not_stop_as_stale(self):
        """Regenerate with `python3 reviews/22c-ways-back-after-update/walk-host.py` after changing a file it binds."""
        import hashlib
        receipt = json.loads(self.PATH.read_text())
        stale = [row['path'] for row in receipt['sources']
                 if hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest() != row['sha256']]
        self.assertEqual(stale, [])


class WalkOrderTest(unittest.TestCase):
    def test_the_six_moves_visit_all_six_orders_and_end_at_the_start(self):
        order, seen = list(rp.START), []
        for role in rp.MOVES:
            self.assertNotEqual(order[0], role)  # every move changes what starts next
            order = rp.moved(order, role)
            seen.append(tuple(order))
        self.assertEqual(tuple(seen), rp.ORDERS)
        self.assertEqual(len(set(seen)), 6)
        self.assertEqual(seen[-1], rp.START)
        # Each row runs twice and each row is first twice.
        self.assertEqual(sorted(order[0] for order in rp.ORDERS), ['R13', 'R13', 'R27', 'R27', 'S', 'S'])

    def test_the_local_walk_types_the_route_and_only_plain_commands_after_the_confirmation(self):
        commands = json.loads((ROOT / 'os/owner-tools/commands.json').read_text())
        for ps2 in (False, True):
            with self.subTest(ps2=ps2):
                result = walk.walk(ps2=ps2, route='reorder-probe')
                self.assertEqual(result['stages'], walk.PROBE_STAGES)
                self.assertEqual(result['result']['status'], 'passed')
                self.assertEqual(result['disk'].sets, [2, 1, 2, 2, 1, 2])
                typed = [text.rstrip('\n') for text, profile in result['visible_blocks']]
                # Package 27's route: the laptop's 15f bootstrap, then version 2's, each once.
                version_2 = dict(commands, install=owner_vm.bundle_module('bootstrap').command(owner_vm.TOOLS_V2))['install']
                self.assertEqual(typed.count(owner_vm.laptop_commands()['install']), 1)
                self.assertEqual(typed.count(version_2), 1)
                confirmed = max(index for index, text in enumerate(typed) if text == commands['title'])
                self.assertFalse([text for text in typed[confirmed + 1:] if '/var/lib/ares/at' in text])
                self.assertEqual(typed.count(commands['update']), 1)
                self.assertNotIn(commands['previous'], typed)
                names = [name for name, source in result['commands']]
                self.assertEqual([name for name in names if name.endswith('-set-default')],
                                 [f'walk-{n}-moved-set-default' for n in range(1, 7)])
                # The stock is started three times, each with the German login on tty3 and its greeter.
                self.assertEqual(result['result']['stock_starts'], ['walk-1-booted', 'walk-4-booted', 'menu-stock'])
                self.assertEqual(result['result']['menu']['choice']['keys'], ['home', 'down', 'down', 'ret'])
                checks = result['checks']
                self.assertEqual([c for c in checks if c.startswith('menu-stock-menu-')],
                                 ['menu-stock-menu-home', 'menu-stock-menu-down', 'menu-stock-menu-down', 'menu-stock-menu-ret'])
                self.assertEqual(len([c for c in checks if c.endswith('-plain-reboot')]), 8)
                table = result['result']['stages']
                self.assertEqual([row['order'] for row in table if row['stage'].endswith('-moved')], [list(o) for o in rp.ORDERS])
                self.assertEqual([row['running'] for row in table if row['stage'].endswith('-booted')],
                                 ['S', 'R27', 'R13', 'S', 'R13', 'R27', 'R27'])
                self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])


def fake_bin(folder, **programs):
    """Stand-in commands in a folder that is the whole PATH: the real ostree, rpm or journalctl can never run."""
    folder.mkdir()
    for name, body in programs.items():
        path = folder / name
        path.write_text('#!' + sys.executable + '\nimport json,sys\n' + body + '\n')
        path.chmod(0o755)
    return dict(PATH=str(folder))


def run_program(source, environment):
    done = subprocess.run([sys.executable, '-c', source], capture_output=True, text=True, env=environment)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


class GuestProgramsTest(unittest.TestCase):
    """The three programs the probe runs in the guest, run here against a modelled tree and stand-in commands."""

    def tree(self, root, disk):
        boot, ostree = root / 'boot', root / 'sysroot/ostree'
        (boot / 'loader.0/entries').mkdir(parents=True)
        (boot / 'loader').symlink_to('loader.0')
        for entry in disk.entries():
            (boot / 'loader.0/entries' / pathlib.PurePosixPath(entry['file']).name).write_text(entry['content'])
        links = ostree / f'boot.0.{disk.links}/default' / ('b' * 64)
        links.mkdir(parents=True)
        (ostree / 'boot.0').symlink_to(f'boot.0.{disk.links}')
        for place, role in enumerate(disk.order):
            target = pathlib.Path(str(root) + disk.path(role))
            target.mkdir(parents=True)
            (links / str(place)).symlink_to(os.path.relpath(target, links))
            row = disk.rows[role]
            target.with_name(target.name + '.origin').write_text(
                '[origin]\ncontainer-image-reference=' + row['container-image-reference'] + '\n'
                + ('\n[libostree-transient]\npinned=true\n' if row['pinned'] else ''))
        (root / 'proc/sys/kernel/random').mkdir(parents=True)
        layout = disk.layout()
        (root / 'proc/cmdline').write_text('BOOT_IMAGE=(hd0,gpt2)/ostree/x ' + layout['cmdline'] + '\n')
        (root / 'proc/sys/kernel/random/boot_id').write_text('0f0f0f0f-boot\n')

    def test_the_layout_program_reads_the_running_row_the_links_and_the_pin(self):
        disk = walk.LaptopDisk(walk.retained('aresos'))
        disk.set_default(2)  # the stock first, release 27 still running
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder) / 'root'
            self.tree(root, disk)
            environment = fake_bin(pathlib.Path(folder) / 'bin', ostree="print('* default fixture'); sys.exit(0)",
                                   rpm="print('ostree-2026.4-1.fc44.x86_64')",
                                   **{'grub2-editenv': "print('boot_success=1') if sys.argv[1:]==['-','list'] else sys.exit(2)"})
            source = rp.LAYOUT.replace("root=pathlib.Path('/')", 'root=pathlib.Path(' + repr(str(root)) + ')')
            self.assertNotEqual(source, rp.LAYOUT)
            layout = run_program(source, environment)
        # As in the VM: release 27 started from place 0, and after the move that place holds the stock.
        self.assertEqual(layout['running'], disk.path('S'))
        self.assertEqual(layout, dict(disk.layout(), boot_id=layout['boot_id'], cmdline=layout['cmdline'], admin_status=layout['admin_status'],
                                      grubenv=layout['grubenv'], packages=layout['packages'], origins=layout['origins'],
                                      loader_directories=layout['loader_directories'], ostree_boot_targets=layout['ostree_boot_targets']))
        self.assertEqual((layout['loader_link'], layout['ostree_boot_links']), ('loader.0', {'boot.0': 'boot.0.0'}))
        self.assertEqual(layout['loader_directories']['loader.0'], ['ostree-1.conf', 'ostree-2.conf', 'ostree-3.conf'])
        self.assertEqual(layout['admin_status']['argv'], ['ostree', 'admin', 'status'])
        self.assertEqual(layout['grubenv']['stdout'], 'boot_success=1\n')
        self.assertEqual(len(layout['origins']), 3)
        self.assertEqual(len(layout['ostree_boot_targets']), 6)  # through boot.0 and through boot.0.0
        roles = {walk.vm.ke.key(row): role for role, row in disk.rows.items()}
        facts = rp.observe(roles, disk.snapshot(), layout)
        self.assertEqual((facts['order'], facts['running'], facts['running_by_kernel_argument']), (['S', 'R27', 'R13'], 'R27', 'S'))
        self.assertEqual(facts['origin_pins'], dict(R27=False, R13=False, S=True))
        self.assertEqual((facts['pinned'], facts['bootc']['rollback'], facts['bootc']['rollback_queued']), (['S'], 'S', True))
        self.assertEqual((facts['menu_order'], facts['titles_name_the_place']), (['S', 'R27', 'R13'], True))
        self.assertEqual(facts['boot_id'], '0f0f0f0f-boot')

    def test_the_real_layout_program_only_reads(self):
        for word in ('write', 'unlink', 'rename', 'symlink_to', 'mkdir', 'rmtree', 'set-default', 'cleanup', 'kargs', "'w'"):
            self.assertNotIn(word, rp.LAYOUT)
        self.assertIn("run('ostree','admin','status')", rp.LAYOUT)
        self.assertIn("root=pathlib.Path('/')", rp.LAYOUT)
        compile(rp.LAYOUT, 'layout', 'exec'); compile(rp.JOURNAL, 'journal', 'exec')

    def test_the_journal_program_keeps_only_ostrees_swap_lines(self):
        line = 'Bootloader updated; bootconfig swap: yes; bootversion: boot.0.1, deployment count change: 0'
        rows = [dict(MESSAGE='Started Session 3.', _COMM='systemd'),
                dict(MESSAGE=line, _COMM='ostree', SYSLOG_IDENTIFIER='ostree', _PID='812', _MACHINE_ID='not exported',
                     OSTREE_BOOTLOADER='none', __REALTIME_TIMESTAMP='1'),
                dict(MESSAGE=[98, 111, 111, 116], _COMM='binary'),
                dict(MESSAGE='audit: argv mentions bootconfig swap inside a longer text', _COMM='auditd'),
                dict(_COMM='no message; bootconfig swap')]
        with tempfile.TemporaryDirectory() as folder:
            body = ("if sys.argv[1:]==['--sync']: sys.exit(0)\nassert sys.argv[1:]==['-b','-o','json','--no-pager']\n"
                    "for row in " + repr(rows) + ": print(json.dumps(row))")
            found = run_program(rp.JOURNAL, fake_bin(pathlib.Path(folder) / 'bin', journalctl=body))
        self.assertEqual([row['MESSAGE'] for row in found], [line, rows[3]['MESSAGE']])
        self.assertEqual(found[0], dict(MESSAGE=line, _COMM='ostree', SYSLOG_IDENTIFIER='ostree', _PID='812',
                                        OSTREE_BOOTLOADER='none', __REALTIME_TIMESTAMP='1'))
        self.assertEqual(rp.swap_lines(found[0]['MESSAGE']), ['yes'])
        self.assertEqual(rp.swap_lines(found[1]['MESSAGE']), [])

    def test_the_move_is_one_plain_set_default_and_never_index_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            log = pathlib.Path(folder) / 'calls'
            body = ("open(" + repr(str(log)) + ",'a').write(json.dumps(sys.argv[1:])+'\\n')\n"
                    "print('Transaction complete; bootconfig swap: no; bootversion: boot.1.0, deployment count change: 0')\n"
                    "print('note',file=sys.stderr); sys.exit(0)")
            done = run_program(rp.set_default_program(2), fake_bin(pathlib.Path(folder) / 'bin', ostree=body))
            self.assertEqual(log.read_text().splitlines(), ['["admin", "set-default", "2"]'])
        self.assertEqual((done['argv'], done['returncode'], done['stderr']), (['ostree', 'admin', 'set-default', '2'], 0, 'note\n'))
        self.assertEqual(rp.swap_lines(done['stdout']), ['no'])
        for index in (0, -1, '2', True, None):
            with self.subTest(index=index), self.assertRaises(AssertionError):
                rp.set_default_program(index)
        # Nothing else changes anything: no sync, pin, cleanup or reboot in the program.
        program = rp.set_default_program(1)
        self.assertEqual(re.findall(r"'ostree', 'admin', '([a-z-]+)'", program), ['set-default'])
        self.assertEqual(program.count('subprocess.run('), 1)


class Guest:
    """The serial root shell of a modelled disk, for the probe's own logic."""

    def __init__(self, disk):
        self.disk, self.names = disk, []

    def capture_json(self, name, source):
        self.names.append(name)
        if name.endswith('-layout'):
            return self.disk.layout()
        if name.endswith(('-journal-before', '-journal-after')):
            return list(self.disk.journal)
        if name.endswith('-set-default'):
            words = shlex.split(source)
            index, = re.findall(r"^argv=\['ostree', 'admin', 'set-default', '([0-9]+)'\]$", words[words.index('python3') + 2], re.M)
            return self.disk.set_default(int(index))
        raise AssertionError('Unwalked capture: ' + name)


def probe_walk(disk):
    """The probe's walk of the six orders over a disk (no menu); returns the probe, with what stopped it."""
    guest = Guest(disk)
    roles = {role: walk.vm.ke.key(row) for role, row in disk.rows.items()}
    with patch.object(rp.kb, 'deployment_snapshot', side_effect=lambda guest, stage: guest.disk.snapshot()), \
            patch.object(rp.td, 'save'), patch('builtins.print'):
        probe = rp.Probe(roles)
        probe.stopped = None
        try:
            _, snapshot = probe.capture(guest, 'walk-0-start', 'start', running='R27', order=rp.START)
            for number, role in enumerate(rp.MOVES, 1):
                probe.move(guest, f'walk-{number}-moved', role, snapshot)
                disk.restart()
                _, snapshot = probe.restarted(guest, f'walk-{number}-booted', 'restart with no choice', rp.ORDERS[number - 1][0])
        except AssertionError as error:
            probe.stopped = str(error)
    return probe


def points(probe):
    return sorted({row['point'] for row in probe.contradicted()})


class ExpectationsTest(unittest.TestCase):
    """Each point of P6 is recorded as contradicted when the disk behaves otherwise (and only then)."""

    def disk(self, **methods):
        return type('Disk', (walk.LaptopDisk,), methods)(walk.retained('aresos'))

    def test_the_expected_disk_meets_every_expectation(self):
        probe = probe_walk(self.disk())
        self.assertEqual(probe.contradicted(), [])
        result = probe.result(commit='a' * 40)
        self.assertEqual((result['status'], len(result['stages']), len(result['swaps'])), ('passed', 13, 6))
        self.assertEqual(result['orders_seen'], [list(order) for order in rp.ORDERS])
        self.assertEqual([row['bootconfig_swap'] for row in result['stages'] if row['stage'].endswith('-moved')], ['no'] * 6)
        # After a move the kernel's link names the row that took the running row's place: reported, not judged.
        self.assertEqual([row['kernel_argument_resolves_to'] for row in result['stages'] if row['stage'].endswith('-moved')], list(rp.MOVES))
        self.assertTrue(all(row['kernel_argument_resolves_to'] == row['running'] for row in result['stages']
                            if not row['stage'].endswith('-moved')))
        first = result['stages'][1]
        self.assertEqual((first['order'], first['running'], first['bootc_rollback'], first['rollback_queued'], first['pinned']),
                         (['S', 'R27', 'R13'], 'R27', 'S', True, ['S']))
        self.assertEqual([t['title'] for t in first['titles']], [f'Bazzite (ostree:{n})' for n in range(3)])
        self.assertGreater(result['expectations']['checked'], 100)

    def test_a_set_default_that_appends_or_swaps_is_contradicted(self):
        def append(self, index):
            self.order.append(self.order.pop(index))
            return self.wrote(index)

        def swap(self, index):
            self.order[0], self.order[index] = self.order[index], self.order[0]
            return self.wrote(index)
        for name, method in (('append', append), ('swap', swap)):
            with self.subTest(name):
                probe = probe_walk(self.disk(set_default=method))
                self.assertIsNone(probe.stopped)
                self.assertIn('set-default puts the target first and keeps the others in their old relative order', points(probe))
                # The first move already shows it, on the first capture after it.
                first = next(row for row in probe.contradicted())
                self.assertEqual((first['stage'], first['detail']['target']), ('walk-1-moved', 'S'))

    def test_a_lost_pin_a_changed_identity_or_changed_stock_options_is_contradicted(self):
        def unpin(self, index):
            self.rows['S']['pinned'] = False
            return walk.LaptopDisk.set_default(self, index)
        found = points(probe_walk(self.disk(set_default=unpin)))
        self.assertIn('only the stock is pinned', found)
        self.assertIn('every deployment keeps its identity, reference, digest and flags', found)

        def redeploy(self, index):
            self.rows['R13']['container-image-reference-digest'] = 'sha256:' + 'e' * 64
            return walk.LaptopDisk.set_default(self, index)
        self.assertEqual(points(probe_walk(self.disk(set_default=redeploy))),
                         ['every deployment keeps its identity, reference, digest and flags'])

        def entries(self):
            rows = walk.LaptopDisk.entries(self)
            if self.sets:
                stock = next(row for row in rows if row['deployment'] == self.path('S'))
                stock['content'] = stock['content'].replace(' rw\n', ' rw quiet\n')
            return rows
        self.assertEqual(points(probe_walk(self.disk(entries=entries))), ["the stock's boot options stay the same"])

    def test_a_start_of_another_row_or_a_changed_list_after_a_restart_is_contradicted(self):
        def second(self, choice=None):
            walk.LaptopDisk.restart(self, 1 if choice is None else choice)
        self.assertEqual(points(probe_walk(self.disk(restart=second))), ['the expected row runs'])

        def reorder(self, choice=None):
            walk.LaptopDisk.restart(self, choice)
            self.order.reverse()
        found = points(probe_walk(self.disk(restart=reorder)))
        self.assertIn('a restart leaves the order as it was', found)

    def test_a_start_whose_kernel_argument_names_another_row_is_contradicted(self):
        def elsewhere(self, choice=None):
            walk.LaptopDisk.restart(self, choice)
            self.started_at = 2
        self.assertEqual(points(probe_walk(self.disk(restart=elsewhere))),
                         ['at a start, rpm-ostree, bootc and the kernel argument name the same running row'])

    def test_wrong_bootc_slots_are_contradicted(self):
        def inverted(self):
            state = walk.LaptopDisk.snapshot(self)
            state['bootc']['status']['rollbackQueued'] = not state['bootc']['status']['rollbackQueued']
            return state
        self.assertEqual(points(probe_walk(self.disk(snapshot=inverted))),
                         ["rollbackQueued is true exactly when bootc's rollback slot comes before the running row"])

        def last_other(self):
            state = walk.LaptopDisk.snapshot(self)
            rows = [row for row in state['rpm']['deployments'] if not row['booted']]
            tree = state['bootc']['status']['rollback']['ostree']
            tree.update(checksum=rows[-1]['checksum'], deploySerial=rows[-1]['serial'])
            return state
        self.assertIn("bootc's rollback slot is the first other deployment", points(probe_walk(self.disk(snapshot=last_other))))

    def test_a_missing_or_doubled_swap_line_or_a_failed_command_is_contradicted(self):
        def silent(self, index):
            done = walk.LaptopDisk.set_default(self, index)
            self.journal.pop()
            return dict(done, stdout='')
        self.assertEqual(points(probe_walk(self.disk(set_default=silent))),
                         ['ostree prints and logs one bootconfig swap line for the move'])

        def failed(self, index):
            return dict(argv=[], returncode=1, stdout='', stderr='error: fixture')
        probe = probe_walk(self.disk(set_default=failed))
        self.assertIn('set-default exits 0', points(probe))
        self.assertIn('set-default puts the target first and keeps the others in their old relative order', points(probe))
        # A later target that is first already is not moved: nothing is run for it.
        self.assertIn('the target is not first before its move', points(probe))
        self.assertIsNone(probe.stopped)

    def test_a_removed_staged_or_unknown_deployment_stops_or_is_contradicted(self):
        def lose(self, index):
            done = walk.LaptopDisk.set_default(self, index)
            if 'R13' in self.order:
                self.order.remove('R13')
            return done
        probe = probe_walk(self.disk(set_default=lose))
        self.assertIn('nothing is created, removed or staged, and no transaction is open', points(probe))
        # The walk cannot go on once its next target is gone.
        self.assertEqual(probe.stopped, 'STOP: the target is not in the list exactly once')

        def foreign(self):
            state = walk.LaptopDisk.snapshot(self)
            state['rpm']['deployments'][-1]['checksum'] = 'f' * 64
            return state
        self.assertIn('none of the three installed systems', probe_walk(self.disk(snapshot=foreign)).stopped)

        def staged(self):
            state = walk.LaptopDisk.snapshot(self)
            state['rpm']['deployments'][0]['staged'] = bool(self.sets)
            return state
        self.assertIn('nothing is created, removed or staged, and no transaction is open', points(probe_walk(self.disk(snapshot=staged))))

    def test_the_result_names_every_contradiction_and_the_run_would_fail(self):
        def second(self, choice=None):
            walk.LaptopDisk.restart(self, 1 if choice is None else choice)
        result = probe_walk(self.disk(restart=second)).result()
        self.assertEqual(result['status'], 'contradicted')
        self.assertEqual({row['point'] for row in result['expectations']['contradicted']}, {'the expected row runs'})
        self.assertEqual(len(result['stages']), 13)  # the walk went on and recorded every stage


RUN = ROOT / 'reviews/22c-ways-back-after-update/runs/reorder-probe-43470161858'
# What a capture says about the disk, by role; boot ids and timestamps are no part of it.
COMPARED = ('order', 'running', 'pinned', 'staged', 'transaction', 'bootc', 'menu_order', 'title_indexes', 'titles_name_the_place',
            'origin_pins', 'running_by_kernel_argument', 'loader_link', 'ostree_boot_links')


class CapturesTest(unittest.TestCase):
    """The modelled disk of the local walk reproduces every committed capture of the VM probe (run 43470161858).

    Stage 1a's fake host gets its own fixture test (brief B10); this one keeps the walk's model honest.
    """

    def captured(self, stage, suffix='-observed.json'):
        return json.loads((RUN / (stage + suffix)).read_text())

    def reproduce(self, disk):
        """Take the disk through the run's steps; return the stages where it differs from the capture."""
        result = json.loads((RUN / 'reorder-probe-result.json').read_text())
        roles = {walk.vm.ke.key(row): role for role, row in disk.rows.items()}
        differing = []

        def compare(stage):
            facts, capture = rp.observe(roles, disk.snapshot(), disk.layout()), self.captured(stage)
            fields = [name for name in COMPARED if facts[name] != capture[name]]
            entries = lambda value: [(e['file'], e['title'], e['title_index'], e['version'], e['role']) for e in value['entries']]
            if entries(facts) != entries(capture):
                fields.append('entries')
            if fields:
                differing.append((stage, fields))
        stages = [row['stage'] for row in result['stages']]
        self.assertEqual(stages, ['walk-0-start'] + [f'walk-{n}-{kind}' for n in range(1, 7) for kind in ('moved', 'booted')]
                         + ['menu-stock', 'after-menu-booted'])
        compare('walk-0-start')
        for number in range(1, 7):
            done, capture = None, self.captured(f'walk-{number}-moved', '-set-default.json')
            done = disk.set_default(int(capture['argv'][-1]))
            if (done['argv'], done['returncode'], done['stdout'].strip()) != (capture['argv'], capture['returncode'], capture['stdout'].strip()):
                differing.append((f'walk-{number}-moved', ['set-default output']))
            journal = self.captured(f'walk-{number}-moved', '-journal-after.json')
            if [row['MESSAGE'] for row in disk.journal] != [row['MESSAGE'] for row in journal]:
                differing.append((f'walk-{number}-moved', ['journal']))
            compare(f'walk-{number}-moved')
            disk.restart()
            compare(f'walk-{number}-booted')
        disk.grubenv['menu_show_once'] = '1'
        self.assertEqual(result['menu']['choice']['lines'], [line.strip() for line in disk.screen().splitlines() if 'ostree' in line])
        for keys in result['menu']['choice']['keys']:
            disk.key([keys])
        compare('menu-stock')
        disk.restart()
        compare('after-menu-booted')
        return differing

    def test_the_modelled_disk_reproduces_every_capture(self):
        self.assertEqual(self.reproduce(walk.LaptopDisk(walk.retained('aresos'))), [])

    def test_a_disk_that_appends_or_names_other_slots_does_not(self):
        def append(self, index):
            self.order.append(self.order.pop(index))
            return self.wrote(index)
        differing = self.reproduce(type('Disk', (walk.LaptopDisk,), dict(set_default=append))(walk.retained('aresos')))
        self.assertEqual(differing[0][0], 'walk-1-moved')
        self.assertIn('order', differing[0][1])

        def last_other(self):
            state = walk.LaptopDisk.snapshot(self)
            rows = [row for row in state['rpm']['deployments'] if not row['booted']]
            state['bootc']['status']['rollback']['ostree'].update(checksum=rows[-1]['checksum'], deploySerial=rows[-1]['serial'])
            return state
        differing = self.reproduce(type('Disk', (walk.LaptopDisk,), dict(snapshot=last_other))(walk.retained('aresos')))
        self.assertTrue(differing and all('bootc' in fields for stage, fields in differing if fields != ['set-default output']))

    def test_the_captures_are_complete_and_hold_no_identifier_or_token(self):
        index = json.loads((RUN / 'index.json').read_text())
        self.assertEqual(sorted(index['files'] + ['index.json']), sorted(path.name for path in RUN.iterdir()))
        self.assertEqual((index['status'], len(index['audits'])), ('contradicted', 21))
        self.assertTrue(all(row['protected_disk_equals_baseline'] for row in index['audits']))
        uuid = re.compile(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}')
        secret = re.compile(r'gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|\$(?:6|5|y)\$|x-access-token')
        for path in RUN.iterdir():
            text = path.read_text(encoding='utf-8')
            with self.subTest(file=path.name):
                self.assertIsNone(uuid.search(text))
                # index.json lists the patterns the captures were checked for.
                self.assertIsNone(secret.search(text) if path.name != 'index.json' else None)
        # The run's only contradictions are the probe's own first reading of the kernel argument, corrected since.
        result = json.loads((RUN / 'reorder-probe-result.json').read_text())
        self.assertEqual({(row['stage'].split('-')[-1], row['point']) for row in result['expectations']['contradicted']},
                         {('moved', 'rpm-ostree, bootc and the kernel argument name the same running row')})


class MenuTest(unittest.TestCase):
    def backup(self, disk):
        from grub_bls import stock_bls_entry
        return stock_bls_entry(disk.inventory(), disk.rows['S']['checksum'], disk.snapshot()['rpm']['deployments'])

    def choose(self, disk, screens, deadline=5):
        guest, saved = Mock(), {}
        guest.keys.side_effect = lambda keys: disk.key(keys)
        screens = iter(screens)
        with patch.object(rp, 'read_screen', side_effect=lambda guest, name: next(screens)), patch.object(rp.time, 'sleep'), \
                patch.object(rp, 'MENU_DEADLINE', deadline), \
                patch.object(rp.td, 'save', side_effect=lambda name, value: saved.__setitem__(name, value)):
            choice = rp.menu_choice(guest, self.backup(disk), 'menu-stock')
        return choice, guest, saved

    def test_the_stock_row_is_taken_only_after_the_rows_read_twice_as_recorded(self):
        disk = walk.LaptopDisk(walk.retained('aresos'))
        disk.grubenv['menu_show_once'] = '1'
        choice, guest, saved = self.choose(disk, ['', ' Bazzite (ostree:0)\n', disk.screen(), disk.screen()])
        self.assertEqual((choice['selected'], choice['frame'], choice['keys']), (True, 'menu-stock-attempt-04', ['home', 'down', 'down', 'ret']))
        self.assertEqual([call.args[0] for call in guest.keys.call_args_list], [['home'], ['down'], ['down'], ['ret']])
        self.assertEqual((disk.running, disk.order), ('S', ['R27', 'R13', 'S']))
        self.assertEqual(saved['b-grub-selection']['stock_position'], 2)

    def test_rows_that_read_otherwise_or_no_menu_send_no_key(self):
        disk = walk.LaptopDisk(walk.retained('aresos'))
        disk.grubenv['menu_show_once'] = '1'
        other = disk.screen().replace('(ostree:1)', '(ostree:7)')
        choice, guest, _ = self.choose(disk, [other, other])
        self.assertEqual((choice['selected'], guest.keys.call_count, disk.running), (False, 0, 'R27'))
        self.assertIn('GRUB OCR position disagreement', choice['reason'])
        choice, guest, _ = self.choose(disk, iter(lambda: '', None), deadline=0.2)
        self.assertEqual((choice['selected'], guest.keys.call_count), (False, 0))
        self.assertIn('no boot menu was read', choice['reason'])

    def test_the_stock_row_is_found_through_its_boot_entry_in_every_order_where_it_is_not_first(self):
        guest = Mock()
        for order in rp.ORDERS:
            disk = walk.LaptopDisk(walk.retained('aresos'))
            disk.order = list(order)
            guest.capture_json.return_value = disk.inventory()
            with self.subTest(order=order), patch.object(rp.td, 'save'):
                backup, reason, _ = rp.recorded_stock_entry(guest, 'menu', disk.snapshot(), disk.rows['S']['checksum'])
                if order[0] == 'S':
                    self.assertIsNone(backup)
                    self.assertIn('already the default', reason)
                else:
                    self.assertEqual((backup['menu_index'], reason), (order.index('S'), None))
                    self.assertEqual(backup['menu_titles'], [f'Bazzite (ostree:{n})' for n in range(3)])
                    self.assertEqual(backup['id'], f"ostree-{3 - order.index('S')}")
        # Titles that do not name the place (or a wrong file order) block the menu path.
        disk = walk.LaptopDisk(walk.retained('aresos'))
        rows = disk.inventory()
        rows[0]['title'] = rows[0]['title'].replace('ostree:0', 'ostree:1')
        rows[0]['content'] = rows[0]['content'].replace('ostree:0', 'ostree:1')
        guest.capture_json.return_value = rows
        with patch.object(rp.td, 'save'):
            backup, reason, _ = rp.recorded_stock_entry(guest, 'menu', disk.snapshot(), disk.rows['S']['checksum'])
        self.assertIsNone(backup)
        self.assertIn('BLS position disagreement', reason)

    def test_the_one_time_entry_takes_only_an_ostree_entry_id(self):
        guest = Mock()
        rp.one_time_entry(guest, 'menu-fallback', 'ostree-1')
        name, script = guest.command.call_args.args
        self.assertEqual((name, script), ('menu-fallback-one-time-entry', 'set -e; grub2-reboot ostree-1; grub2-editenv - list'))
        for entry in ('ostree-0', 'ostree-1; reboot', '../x', ''):
            with self.subTest(entry=entry), self.assertRaises(AssertionError):
                rp.one_time_entry(guest, 'menu-fallback', entry)


class ToolsFromHistoryTest(unittest.TestCase):
    def test_version_2_is_the_laptops_bundle_at_the_named_commit(self):
        """The probe installs in step 8 what the laptop runs today, whatever this checkout's payload is."""
        with tempfile.TemporaryDirectory() as folder, contextlib.chdir(ROOT):
            bundle = owner_vm.laptop_payload(pathlib.Path(folder) / 'v2', owner_vm.TOOLS_V2_COMMIT, owner_vm.TOOLS_V2)
            self.assertEqual(owner_vm.bundle_module('owner').checked_bundle(bundle), owner_vm.TOOLS_V2)
            self.assertEqual(json.loads((bundle / 'history.json').read_text())['tools_version'], 2)
            release = json.loads((bundle / 'release.json').read_text())['reference']
            self.assertEqual(release, json.loads((ROOT / 'os/manifest/release.json').read_text())['reference'])
            with self.assertRaisesRegex(AssertionError, 'laptop tools fingerprint'):
                owner_vm.laptop_payload(pathlib.Path(folder) / 'wrong', owner_vm.TOOLS_V2_COMMIT, owner_vm.LAPTOP_TOOLS)
        self.assertNotEqual(owner_vm.TOOLS_V2, owner_vm.LAPTOP_TOOLS)

    def test_the_stick_copy_takes_a_bundle_from_history(self):
        import inspect
        source = inspect.getsource(owner_media.Media.replace)
        self.assertIn("bundle_module('owner').checked_bundle(payload)", source)
        self.assertIn('assert fingerprint != old', source)


class RehearsalWalkTest(unittest.TestCase):
    """Stage 2 (brief E, briefs/22c-stage-2-additions.md): the local walk of the rehearsal. From tools
    version 3 on, every way-back command the walk types is answered by the owner tools themselves
    (test_owner_walk.Oracle), so the lines the harness requires are the lines the tools print."""

    @classmethod
    def setUpClass(cls):
        cls.result = walk.walk(route='ways-back')
        cls.commands = json.loads((ROOT / 'os/owner-tools/commands.json').read_text())
        cls.rows = cls.result['result']['transcript']
        cls.words = {command: name for name, command in cls.commands.items()}

    def word(self, row):
        return self.words.get(row['command'], 'install')

    def test_the_route_is_the_laptops_history_then_version_3_from_the_stick(self):
        result, commands = self.result, self.commands
        self.assertEqual(result['stages'], walk.WAYS_BACK_STAGES)
        self.assertEqual(result['result']['status'], 'passed')
        typed = [text.rstrip('\n') for text, profile in result['visible_blocks']]
        version_2 = owner_vm.bundle_module('bootstrap').command(owner_vm.TOOLS_V2)
        blocks = [owner_vm.laptop_commands()['install'], version_2, commands['install']]
        self.assertEqual(len(set(blocks)), 3)
        self.assertEqual([typed.count(block) for block in blocks], [1, 1, 1])
        self.assertEqual(sorted(typed.index(block) for block in blocks), [typed.index(block) for block in blocks])
        checks = result['checks']
        for earlier, later in (('update-windows-copy-windows-copy', 'update-tools-hotplug'), ('update-tools-detach', 'tools-3-windows-copy'),
                               ('tools-3-windows-copy', 'tools-3-hotplug'), ('tools-3-hotplug', 'tools-3-detach'),
                               ('tools-3-detach', 'release-27-owner-reboot-tools-absent')):
            self.assertLess(checks.index(earlier), checks.index(later), (earlier, later))
        # The administrator password is set once, before the tools change; his sudo passes then and after the returns.
        self.assertEqual(typed.count('sudo passwd ares'), 1)
        self.assertEqual(typed.count('sudo -v'), 2)
        self.assertLess(typed.index('sudo passwd ares'), typed.index(commands['install']))
        self.assertEqual(result['markers'][-2:], ['final-unattended-windows', 'final-detached-windows'])
        self.assertEqual(result['result']['tools_version_3'], walk.common.bundle.check(ROOT / 'os/owner-tools/payload'))

    def test_forward_where_the_walk_returns_and_update_only_where_it_names_forward(self):
        rows, commands = self.rows, self.commands
        typed = [text.rstrip('\n') for text, profile in self.result['visible_blocks']]
        # update: package 27's staging with tools version 2, then once on the older AresOS, refused.
        self.assertEqual(typed.count(commands['update']), 2)
        update, = [row for row in rows if self.word(row) == 'update']
        self.assertEqual((update['boot'], update['system'], update['status']), ('back-13', 'R13', 'stopped'))
        self.assertTrue(update['error'].startswith('The release of these tools is installed already'), update['error'])
        self.assertIn(commands['forward'], update['error'])
        self.assertTrue(update['error'].endswith('nothing changed'))
        after = rows[rows.index(update) + 1]
        self.assertEqual((self.word(after), after['status'], after['system']), ('forward', 'passed', 'R13'))
        # Every return to the newest AresOS is forward: from the older AresOS (twice), from plain Bazzite
        # (by order, after keep-stock, after the cut) and on the newer AresOS itself taken in the boot menu.
        self.assertEqual([(row['boot'], row['system']) for row in rows if self.word(row) == 'forward'],
                         [('back-13', 'R13'), ('stock-1', 'S'), ('back-13b', 'R13'), ('menu-27', 'R27'), ('stock-2', 'S'), ('cut-stock', 'S')])
        self.assertEqual([(row['boot'], row['system']) for row in rows if self.word(row) == 'previous'],
                         [('abandon-27', 'R27'), ('forward-27b', 'R27'), ('forward-27c', 'R27')])
        self.assertEqual([(row['boot'], row['status'][:3]) for row in rows if self.word(row) == 'rollback'],
                         [('forward-27', 'pas'), ('stock-1', 'sto'), ('forward-27e', 'cut')])
        self.assertEqual([(row['boot'], row['lines'][0]) for row in rows if self.word(row) == 'keep-stock'],
                         [('stock-1', self.result['result']['names']['S'].replace('plain', 'Plain') + ' already starts next; nothing changed'),
                          ('menu-stock', 'Saved stock is default')])
        self.assertEqual(self.result['result']['typed']['forward'], 6)
        # forward is walked now: it left the waiting list (test_owner_equality refuses a listed command that is typed).
        waiting = json.loads((ROOT / 'os/manifest/ci/16/pending-rebind.json').read_text())
        self.assertNotIn('forward', waiting['unwalked_commands'])

    def test_the_guides_order_check_first_and_a_fresh_title_before_every_restart(self):
        rows = self.rows
        for stage in walk.WAYS_BACK_STAGES[5:]:
            boot = [self.word(row) for row in rows if row['boot'] == stage]
            with self.subTest(boot=stage):
                # After every start: check, then title (an abandoned trial is cleared first, from its fresh login).
                first = boot[1:3] if stage == 'abandon-27' else boot[:2]
                self.assertEqual(first, ['check', 'title'])
                self.assertEqual(boot[0], 'layout-abandon' if stage == 'abandon-27' else 'check')
                # check before previous, also after a boot-menu choice (review fixes 3).
                if 'previous' in boot:
                    self.assertLess(boot.index('check'), boot.index('previous'))
                if 'reboot' in boot:
                    self.assertEqual(boot[-2:], ['title', 'reboot'])
        # A return that the restart confirms says so once, in the check, never in the title after it.
        said = [(row['boot'], self.word(row), line.split(' to ')[0]) for row in rows for line in row['lines'] if line.endswith('confirmed after the restart')]
        self.assertEqual(said, [('back-13', 'check', 'Return'), ('forward-27', 'check', 'Forward'), ('stock-1', 'check', 'Rollback'),
                                ('forward-27b', 'check', 'Forward'), ('back-13b', 'check', 'Return'), ('forward-27c', 'check', 'Forward'),
                                ('forward-27d', 'check', 'Forward'), ('stock-2', 'check', 'Change'), ('forward-27e', 'check', 'Forward'),
                                ('cut-stock', 'check', 'Rollback'), ('final-27', 'check', 'Forward')])

    def test_the_two_menu_rows_the_cut_and_the_lists_by_identity(self):
        result = self.result['result']
        self.assertEqual([(m['stage'], m['system'], m['row'], m['choice']['keys']) for m in result['menus']],
                         [('menu-27', 'R27', 1, ['home', 'down', 'ret']), ('menu-stock', 'S', 2, ['home', 'down', 'down', 'ret'])])
        table = {row['stage']: row for row in result['stages']}
        # The restart that lands elsewhere: the newer AresOS runs while the older one starts next; then applied, nothing waits.
        self.assertEqual((table['menu-27']['order'], table['menu-27']['running']), (['R13', 'R27', 'S'], 'R27'))
        elsewhere = [row['lines'] for row in self.rows if row['stage'] == 'menu-27-check'][0]
        names = result['names']
        self.assertIn(names['R27'] + ' runs; ' + names['R13'] + ' starts next; this start was not the default', elsewhere)
        self.assertIn('Return to ' + result['previous_release'] + ' is in place and has not started yet', elsewhere)
        applied = [row['lines'] for row in self.rows if row['stage'] == 'owner-forward-4'][0]
        self.assertIn(names['R27'] + ' runs and now starts next; no restart is waiting', applied)
        self.assertFalse([line for line in applied if 'confirmed' in line or 'not finished' in line])
        # The boot menu without a record: the neutral line and no cause.
        neutral = [row['lines'] for row in self.rows if row['stage'] == 'menu-stock-check'][0]
        self.assertIn(names['S'] + ' runs; ' + names['R27'] + ' starts next; this start was not the default', neutral)
        self.assertFalse([line for line in neutral if 'confirmed' in line or 'in place' in line or 'not applied' in line])
        # The cut: the reorder in place, the journal still the intent, one hard reset; the check on stock records and confirms it.
        cut = result['cut']
        self.assertEqual((cut['order'], cut['running'], cut['journal_holds'], cut['journal']['word'], cut['journal']['status']),
                         (['S', 'R27', 'R13'], 'R27', 'the intent', 'rollback', 'intent'))
        self.assertIn('forward-27e-QMP-system-reset', self.result['checks'])
        self.assertIn('trial-27-QMP-system-reset', self.result['checks'])
        recorded = [row['lines'] for row in self.rows if row['stage'] == 'cut-stock-check'][0]
        self.assertEqual(recorded[0], 'The interrupted rollback to ' + result['references']['S'] + ' had made its change; it is recorded now')
        self.assertIn('Rollback to ' + result['references']['S'] + ' confirmed after the restart', recorded)
        self.assertEqual(table['cut-stock-recorded']['order'], ['S', 'R27', 'R13'])
        # Twelve reorders, each one list write; the stock runs four times; the walk ends on the newer AresOS.
        self.assertEqual(len(result['swaps']), 12)
        self.assertEqual(self.result['disk'].sets, [1, 1, 2, 1, 2, 1, 1, 1, 2, 1, 1, 1])
        self.assertEqual(result['stock_starts'], ['stock-1', 'menu-stock', 'stock-2', 'cut-stock'])
        self.assertEqual((result['stages'][-1]['order'], result['stages'][-1]['running']), (['R27', 'S', 'R13'], 'R27'))
        self.assertEqual(result['expectations']['contradicted'], [])
        self.assertEqual(table['forward-27b']['order'], ['R27', 'S', 'R13'])

    def test_the_walk_also_passes_with_the_ps2_health_checks(self):
        result = walk.walk(ps2=True, route='ways-back')
        self.assertEqual(result['stages'], walk.WAYS_BACK_STAGES)
        self.assertEqual([row['command'] for row in result['result']['transcript']], [row['command'] for row in self.rows])
        names = [name for name, source in result['commands']]
        for stage in ('stock-1', 'menu-27', 'cut-stock', 'final-27'):
            self.assertTrue(any(name.startswith(stage) and name.endswith('-xhci-health') for name in names), stage)


class RehearsalHarnessTest(unittest.TestCase):
    """The rehearsal's own checks stop the walk: a wrong row map, a cut that did not happen, a cut that was not tested."""
    NAMES = dict(R27='newer AresOS 111111111111', R13='older AresOS 222222222222', S='plain Bazzite 333333333333')

    def walk(self):
        value = object.__new__(owner_vm.WaysBack)
        value.name, value.transcript, value.boot_stage, value.cut_proof = self.NAMES, [], 'forward-27e', None
        return value

    def facts(self, order, running):
        return dict(order=list(order), running=running, entries=[dict(role=role, title_index=place) for place, role in enumerate(order)])

    def test_the_first_line_and_the_row_map_are_required_exactly(self):
        value, names = self.walk(), self.NAMES
        menu = 'Boot menu at the next start: (ostree:0) %s, starts next; (ostree:1) %s; (ostree:2) %s' % (names['R13'], names['R27'], names['S'])
        facts = self.facts(('R13', 'R27', 'S'), 'R27')
        value.standing([names['R27'] + ' runs; ' + names['R13'] + ' starts next, after the restart', menu], facts, 'pending')
        value.standing([names['R27'] + ' runs; ' + names['R13'] + ' starts next; this start was not the default', menu], facts)
        with self.assertRaisesRegex(AssertionError, 'the tools do not say'):
            value.standing([names['R27'] + ' runs; ' + names['R13'] + ' starts next, after the restart', menu], facts)
        swapped = menu.replace('(ostree:1)', '(ostree:9)')
        with self.assertRaisesRegex(AssertionError, "row map differs from the boot entries"):
            value.standing([names['R27'] + ' runs; ' + names['R13'] + ' starts next, after the restart', swapped], facts, 'pending')
        first = self.facts(('S', 'R27', 'R13'), 'S')
        menu = 'Boot menu at the next start: (ostree:0) %s, starts next; (ostree:1) %s; (ostree:2) %s' % (names['S'], names['R27'], names['R13'])
        value.standing([names['S'] + ' runs and now starts next; no restart is waiting', menu], first, 'applied')
        with self.assertRaisesRegex(AssertionError, 'the tools do not say'):
            value.standing([names['S'] + ' runs and starts next', menu], first, 'applied')

    def cut(self, watcher, intent, order=('S', 'R27', 'R13')):
        value = self.walk()
        stock = ('s' * 64, 0, 'default')
        value.probe = Mock(roles={stock: 'S', ('n' * 64, 0, 'default'): 'R27', ('o' * 64, 0, 'default'): 'R13'})
        value.probe.journal.return_value = []
        value.probe.tool_move.return_value = (dict(order=list(order), running='R27'), None)
        value.probe.contradicted.return_value = []
        answers = iter([dict(status='watching'), watcher, intent])
        guest = Mock(capture_json=Mock(side_effect=lambda name, source: next(answers)))
        console = Mock(guest=guest, tty='tty3', commands=owner_vm.COMMANDS)
        with patch.object(owner_vm.td, 'save'), patch.object(owner_vm.owner_xhci, 'checkpoint'):
            try:
                value.cut(console, 'cut-rollback')
            except AssertionError as error:
                return guest, console, str(error)
        return guest, console, None

    def test_the_reset_follows_only_a_proved_cut(self):
        frozen = dict(status='frozen', pid=7, state='T', release_step_ended=True)
        intent = dict(word='rollback', status='intent', mode='reorder', target=['s' * 64, 0, 'default'])
        guest, console, error = self.cut(frozen, intent)
        self.assertIsNone(error)
        guest.hard_reset.assert_called_once_with('cut-rollback')
        console.visible.assert_called_once_with(owner_vm.COMMANDS['rollback'] + '\n', 'cut-rollback-command')
        # The watcher is started and answers before the command is typed.
        self.assertEqual([call.args[0] for call in guest.capture_json.call_args_list], ['cut-rollback-armed', 'cut-rollback-frozen', 'cut-rollback-intent'])
        order = [call[0] for call in guest.mock_calls]
        self.assertEqual(guest.command.call_args.args[0], 'cut-rollback-watch')
        self.assertLess(order.index('command'), order.index('capture_json'))
        self.assertLess(order.index('capture_json'), order.index('hard_reset'))
        for label, watcher, journal, order, message in (
                ('the record is already written', frozen, dict(intent, status='recorded'), ('S', 'R27', 'R13'), 'the cut was not tested; repeat it'),
                ('no reorder was seen', dict(status='no reorder seen'), intent, ('S', 'R27', 'R13'), 'was not stopped after its reorder'),
                ('the tools were not stopped', dict(frozen, state='S'), intent, ('S', 'R27', 'R13'), 'was not stopped after its reorder'),
                ('another journal', frozen, dict(intent, word='forward'), ('S', 'R27', 'R13'), 'unexpected journal before the reset'),
                ('the list is as before', frozen, intent, ('R27', 'S', 'R13'), 'not in place before the reset')):
            with self.subTest(label):
                guest, console, error = self.cut(watcher, journal, order)
                self.assertIn(message, error)
                guest.hard_reset.assert_not_called()

    def test_the_guest_programs_compile_and_the_run_records_package_22cs_bound_sources(self):
        for name, source in (('cut watch', owner_vm.CUT_WATCH), ('cut intent', owner_vm.CUT_INTENT),
                             ('updaters', owner_vm.UPDATERS.replace('@NAMES@', repr(('uupd.timer',)))),
                             ('cut wait', owner_vm.cut_wait("value['status']!='watching'", 5))):
            compile(source, name, 'exec')
        self.assertIn("argv'][4]==b'rollback'", owner_vm.CUT_WATCH)
        self.assertIn('signal.SIGSTOP', owner_vm.CUT_WATCH)
        self.assertNotIn('SIGCONT', owner_vm.CUT_WATCH)
        # No test-only switch in the bundle: the payload does not know the watcher or its file.
        for path in (ROOT / 'os/owner-tools/payload').rglob('*'):
            if path.is_file():
                self.assertNotIn(b'aresos-cut', path.read_bytes(), path)
        receipt = json.loads((ROOT / 'os/manifest/ci/22c/host-walk.json').read_text())
        with contextlib.chdir(ROOT), patch.dict(os.environ, GITHUB_SHA='a' * 40):
            bound = owner_vm.bound_sources(receipt['sources'], '22c', '27')
        earlier = json.loads((ROOT / 'os/manifest/ci/27/source-bindings.json').read_text())
        self.assertEqual((bound['package'], bound['commit']), ('22c', 'a' * 40))
        self.assertEqual([table['name'] for table in bound['tables']],
                         ['package22c host walk'] + [table['name'].replace('package27', 'package22c') for table in earlier['tables'][1:]])
        self.assertEqual([row['path'] for row in bound['tables'][0]['sources']], [row['path'] for row in receipt['sources']])
        gone = json.loads((ROOT / 'os/manifest/ci/16/pending-rebind.json').read_text())['removed']
        for before, after in zip(earlier['tables'][1:], bound['tables'][1:]):
            self.assertEqual([row['path'] for row in before['sources'] if row['path'] not in gone], [row['path'] for row in after['sources']])
        # The record step accepts exactly this shape (test_checkout_sources runs it on a repository of its own).
        self.assertIn("td.save('22c-bound-sources', bound_sources(walk['sources'], '22c', '27'))", (ROOT / 'os/ci/owner_vm.py').read_text())


@unittest.skipUnless(pathlib.Path('/usr/bin/python3').exists() and pathlib.Path('/proc/self/stat').exists(), 'needs /usr/bin/python3 and /proc')
class CutWatchTest(unittest.TestCase):
    """Brief E7's window, with real processes: the watcher stops a stand-in for the tools as soon as the
    link under the deployment folder is swapped; the stand-in's release step ends, and it never writes its record."""
    STAND_IN = ('import pathlib,subprocess,sys,time\n'
                'root=pathlib.Path(sys.argv[2])\n'
                'time.sleep(.6)\n'
                "step='import os,time; os.symlink(\"boot.0.0\",\"boot.new\"); os.replace(\"boot.new\",\"boot.0\"); time.sleep(.5)'\n"
                "subprocess.run([sys.executable,'-c',step],cwd=root/'ostree',check=True)\n"
                "(root/'record').write_text('recorded')\n")

    def run_watch(self, with_tools):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            ostree = root / 'ostree'
            for name in ('boot.0.0', 'boot.0.1'):
                (ostree / name).mkdir(parents=True)
            (ostree / 'boot.0').symlink_to('boot.0.1')
            (root / 'owner.py').write_text(self.STAND_IN)
            header = "OSTREE,OUT='/sysroot/ostree','/run/aresos-cut.json'"
            self.assertEqual(owner_vm.CUT_WATCH.count(header), 1)
            program = owner_vm.CUT_WATCH.replace(header, 'OSTREE,OUT=%r,%r' % (str(ostree), str(root / 'cut.json')))
            watcher = subprocess.Popen([sys.executable, '-c', program], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            tools = None
            try:
                for attempt in range(200):
                    if (root / 'cut.json').exists():
                        break
                    time.sleep(.05)
                self.assertEqual(json.loads((root / 'cut.json').read_text())['status'], 'watching')
                if with_tools:
                    # Started as the tools are (os/owner-tools/at): /usr/bin/python3 -I -B <folder>/owner.py rollback
                    tools = subprocess.Popen(['/usr/bin/python3', '-I', '-B', str(root / 'owner.py'), 'rollback', str(root)])
                else:
                    os.symlink('boot.0.0', ostree / 'boot.new')
                    os.replace(ostree / 'boot.new', ostree / 'boot.0')
                code = watcher.wait(timeout=30)
                value = json.loads((root / 'cut.json').read_text())
                time.sleep(1)  # the stand-in would have written its record by now
                return code, value, (root / 'record').exists(), watcher.stderr.read()
            finally:
                for process in (watcher, tools):
                    if process is not None and process.poll() is None:
                        process.kill()
                    if process is not None:
                        process.wait(timeout=10)
                        if process.stderr:
                            process.stderr.close()

    def test_the_tools_are_stopped_after_the_swap_and_never_write_their_record(self):
        code, value, recorded, errors = self.run_watch(with_tools=True)
        self.assertEqual((code, value['status'], value['state'], value['release_step_ended']), (0, 'frozen', 'T', True), errors)
        self.assertEqual((value['links_before'], value['links_after']), ([['boot.0', 'boot.0.1']], [['boot.0', 'boot.0.0']]))
        self.assertFalse(recorded)

    def test_a_swap_without_the_tools_process_is_reported_and_nothing_is_stopped(self):
        code, value, recorded, errors = self.run_watch(with_tools=False)
        self.assertEqual((code, value['status']), (1, 'reorder seen without the tools process'), errors)


if __name__ == '__main__':
    unittest.main()
