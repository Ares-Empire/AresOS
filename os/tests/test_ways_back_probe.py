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
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
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


class DecisionsTest(unittest.TestCase):
    def test_the_probe_decides_like_package_27s_update_rehearsal_except_where_reviewed(self):
        probe = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='reorder-probe', GITHUB_REF_NAME=BRANCH,
                     argv=['os/ci/owner_vm.py', 'reorder-probe'])
        differing, used, paths = base.differing_decisions([probe, base.WORLDS['update']], REVIEWED)
        self.assertEqual(differing, [])
        self.assertEqual(sorted(set(REVIEWED) - used), [], 'stale reviewed decisions')
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
        # A second VM mode (stage 2's rehearsal) shares the same four.
        second = dict(LEDGER, dispatch_caps=dict(LEDGER['dispatch_caps'], rehearsal=4),
                      titles=dict(LEDGER['titles'], rehearsal='Two-disk rehearsal (rehearsal)'),
                      job_bounds=dict(LEDGER['job_bounds'], rehearsal=345))
        runs = [self.run_row(1, 'reorder-probe'), self.run_row(2, 'reorder-probe'),
                dict(self.run_row(3, 'checks'), display_title='Two-disk rehearsal (rehearsal)'),
                dict(self.run_row(4, 'checks'), display_title='Two-disk rehearsal (rehearsal)')]
        with patch.object(guard, 'SETTINGS', second), self.history(runs):
            self.assertEqual(guard.budget(0)['dispatch_counts'], dict(checks=0, rehearsal=2, **{'reorder-probe': 2}))
            runs.append(dict(self.run_row(5, 'checks'), display_title='Two-disk rehearsal (rehearsal)'))
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
        with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder), patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch('builtins.print'), \
                patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=[run], history=proof)
                             if path.startswith('actions/runs?') else run):
            guard.main()
            written = json.loads(pathlib.Path('evidence/22c-dispatch-authorization.json').read_text())
        self.assertEqual((written['allowance'], written['reserved_minutes'], written['native']['status']), ('22c', 345, 'pending'))
        self.assertEqual(written['dispatch_counts']['reorder-probe'], 1)
        with patch.dict(os.environ, dict(environment, REHEARSAL_MODE='checks'), clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch.object(guard, 'budget') as budget:
            budget.return_value = dict(history=proof, runs=[], dispatch_counts={})
            with self.assertRaisesRegex(AssertionError, 'native deferral is only for probe budget reservation'):
                guard.main()


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
                ('14', 'reorder-probe', 'pkg/14-owner-tools', 'the reorder probe is package 22c only'),
                ('22c', 'update', BRANCH, 'the update rehearsal is package 27 only'),
                ('22c', 'owner-tools', BRANCH, 'the reorder probe is package 22c only'),
                ('22c', 'probe', BRANCH, 'the reorder probe is package 22c only')):
            with self.subTest(package=package, mode=mode):
                with self.assertRaises(AssertionError):
                    self.main(package, mode, branch)
                with self.assertRaisesRegex(AssertionError, message):
                    self.main(package, mode, branch, any_runner=True)

    def test_the_probe_reads_package_22cs_host_walk_and_refuses_a_stale_one(self):
        # With a fresh receipt the driver passes every gate and reaches its first host work.
        with self.assertRaisesRegex(RuntimeError, 'past the gates'):
            self.main('22c', 'reorder-probe', BRANCH)
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
        self.assertEqual(receipt['stages']['reorder-probe'], walk.PROBE_STAGES)
        paths = [row['path'] for row in receipt['sources']]
        self.assertEqual(paths, sorted(set(paths)))
        for needed in ('os/ci/reorder_probe.py', 'os/ci/owner_vm.py', 'os/ci/grub_bls.py', 'os/ci/keyboard_entries.py',
                       'os/tests/test_owner_walk.py', 'os/tests/test_ways_back_probe.py', '.github/workflows/os-image.yml',
                       'os/ci/rehearsal-packages.json', 'reviews/22c-ways-back-after-update/walk-host.py'):
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


if __name__ == '__main__':
    unittest.main()
