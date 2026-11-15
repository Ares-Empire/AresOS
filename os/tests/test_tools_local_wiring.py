"""Package 22d, step 6: the wiring of its rehearsal mode `tools-local`.

Package 22d's VM walk (the owner tools from the desktop's password window, briefs/22d-tools-without-stick.md)
runs in package 22c's harness, with its own ledger entry, branch mapping and host-walk receipt. These tests
hold the wiring the way test_ways_back_probe holds 22c's: the ledger is the brief's budget, the mode runs the
rehearsal job on 22d's branch and nowhere else, every step script accepts 22d's environment, the guard proves
the native step in the run itself and writes 22d's authorization, and the driver keeps each route to its
package. No VM, privilege or real tool runs.
"""
import contextlib
import json
import os
import pathlib
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import model_scope
import owner_media
import owner_vm
import registry_auth
import rehearsal_guard as guard
import test_release27 as base
import test_ways_back_probe as wb
from test_owner_staged_release import condition

BRANCH = 'pkg/22d-tools-without-stick'
MODE = 'tools-local'
LEDGER = guard.PACKAGES['22d']
WORKFLOW, JOB = wb.WORKFLOW, wb.JOB
OTHER_MODES = ('inspect', 'fixture', 'probe', 'part-b', 'keyboard', 'owner-tools', 'update', 'reorder-probe', 'ways-back')


def inputs(mode=MODE):
    return dict(base.UPDATE_INPUTS, **{'github.ref_name': BRANCH, 'inputs.rehearsal': mode})


def job_steps(mode=MODE):
    """Each step of the rehearsal job that runs for this mode on package 22d's branch, with its environment."""
    world = inputs(mode)
    github = dict(base.UPDATE_GITHUB, GITHUB_REF_NAME=BRANCH)
    merged = {**WORKFLOW.get('env', {}), **JOB.get('env', {})}
    environment = dict(github, **{k: base.workflow_text(v, world) for k, v in merged.items()})
    for step in JOB['steps']:
        if 'run' in step and base.workflow_expression(step.get('if', 'success()'), world):
            yield step, dict(environment, **{k: base.workflow_text(v, world) for k, v in step.get('env', {}).items()})


class LedgerTest(unittest.TestCase):
    def test_the_brief_budget_is_the_ledger(self):
        self.assertEqual(LEDGER['branch'], BRANCH)
        self.assertEqual((LEDGER['minute_cap'], LEDGER['dispatch_caps'], LEDGER['vm_dispatch_cap']),
                         (1200, {'checks': 20, MODE: 4}, 4))
        self.assertEqual((LEDGER['full_cap'], LEDGER['part_b_cap'], LEDGER['publish_cap'], LEDGER['start']),
                         (0, 0, 0, 'first-dispatch'))
        self.assertEqual(LEDGER['titles'], {'checks': 'OS regressions only (no VM)', MODE: 'Two-disk rehearsal (tools-local)'})
        # The walk starts with package 22c's route, so its bounds are 22c's.
        self.assertEqual(LEDGER['job_bounds'], {'checks': 40, MODE: guard.PACKAGES['22c']['job_bounds']['ways-back']})
        self.assertEqual(LEDGER['organization_budget'], guard.PACKAGES['22c']['organization_budget'])
        self.assertIn('briefs/22d-tools-without-stick.md: 20 checks-only runs, 4 VM dispatches and 1200 minutes', LEDGER['budget'])
        self.assertIn('22d', guard.TITLED_PACKAGES)
        self.assertIn('22d', guard.OWN_RUN_PACKAGES)


class DispatchTest(unittest.TestCase):
    def test_the_mode_is_a_workflow_option_and_the_branch_maps_to_package_22d(self):
        self.assertIn(MODE, WORKFLOW['on']['workflow_dispatch']['inputs']['rehearsal']['options'])
        expression = re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['env']['REHEARSAL_PACKAGE'].strip())[1]
        self.assertEqual(base.workflow_expression(expression, inputs()), '22d')
        self.assertEqual(base.workflow_expression(expression, wb.inputs('ways-back')), '22c')

    def test_the_mode_runs_the_rehearsal_job_on_its_branch_and_nothing_else_runs_there(self):
        on_branch = {'github.ref_name': BRANCH}
        for name, job in WORKFLOW['jobs'].items():
            with self.subTest(job=name):
                self.assertEqual(condition(job['if'], mode=MODE, **on_branch), name == 'rehearsal')
                for other in ('inputs.release_13', 'inputs.release_27', 'inputs.checks_only',
                              'inputs.switch_from_run', 'inputs.probe_run'):
                    self.assertFalse(condition(job['if'], mode=MODE, **on_branch, **{other: True}) and name == 'rehearsal')
                self.assertFalse(condition(job['if'], mode=MODE, **on_branch, **{'inputs.check_build': 'build'})
                                 and name == 'rehearsal')
            for mode in OTHER_MODES:
                with self.subTest(job=name, other_mode=mode):
                    self.assertFalse(condition(job['if'], mode=mode, **on_branch))
            with self.subTest(job=name, checks=True):
                # Checks only: the regressions and, beside them, the full ways-back model when its sources changed.
                self.assertEqual(condition(job['if'], mode='', **on_branch, **{'inputs.checks_only': True}), name in ('regressions', 'model'))
                self.assertFalse(condition(job['if'], mode='', **on_branch))

    def test_no_other_branch_can_run_the_mode(self):
        for branch in ('main', wb.BRANCH, 'pkg/27-first-update-release', 'pkg/14-owner-tools', 'pkg/16-staged-release',
                       'pkg/13-keyboard-layout', 'pkg/23-minecraft-starts'):
            for name, job in WORKFLOW['jobs'].items():
                with self.subTest(branch=branch, job=name):
                    self.assertFalse(condition(job['if'], mode=MODE, **{'github.ref_name': branch}))


class JobGatesTest(unittest.TestCase):
    def test_every_step_script_accepts_the_package_22d_environment(self):
        failures, evaluated = [], set()
        for step, environment in job_steps():
            for script, argv, removed in base.step_runs(step, environment, inputs()):
                scan = base.GateScan({k: v for k, v in environment.items() if k not in removed}, argv)
                for path, line, text, passed in scan.run(script):
                    evaluated.add(path)
                    if not passed:
                        failures.append(f"{step['name']}: {path}:{line}: {text}")
        self.assertEqual(failures, [])
        self.assertLessEqual({'os/ci/owner_capabilities.py', 'os/ci/owner_devices.py', 'os/ci/owner_media.py',
                              'os/ci/registry_auth.py', 'os/ci/rehearsal_guard.py', 'os/ci/owner_vm.py'}, evaluated)

    def test_the_steps_scripts_arguments_and_bounds_are_package_22ds(self):
        steps = list(job_steps())
        runs = {(script, tuple(argv[1:])) for step, environment in steps
                for script, argv, _ in base.step_runs(step, environment, inputs())}
        bound = str(LEDGER['job_bounds'][MODE])
        self.assertEqual(steps[0][1]['REHEARSAL_PACKAGE'], '22d')
        for expected in (('os/ci/owner_capabilities.py', ()), ('os/ci/rehearsal_guard.py', ('probe-budget-ci', bound)),
                         ('os/ci/rehearsal_guard.py', ('ci', bound)), ('os/ci/registry_auth.py', ('create',)),
                         ('os/ci/registry_auth.py', ('preflight',)), ('os/ci/registry_auth.py', ('pull',)),
                         ('os/ci/registry_auth.py', ('cleanup',)), ('os/ci/owner_devices.py', ()),
                         ('os/ci/owner_counter_kernel.py', ()), ('os/ci/installer_inspect.py', ()),
                         ('os/ci/prepare_two_disks.py', ()), ('os/ci/owner_vm.py', (MODE,))):
            self.assertIn(expected, runs)
        self.assertFalse({script for script, _ in runs} & {'os/ci/keyboard_vm.py', 'os/ci/two_disk_vm.py', 'os/ci/rehearsal_auth.py'})
        names = [step['name'] for step, _ in steps]
        self.assertLess(names.index(guard.NATIVE_STEP), names.index('Require completed native preflight before any package 13 VM'))
        world = inputs()
        self.assertEqual(base.workflow_text(JOB['timeout-minutes'], world), bound)
        vm, = [step for step, _ in steps if 'os/ci/owner_vm.py' in step['run']]
        self.assertLess(int(base.workflow_text(vm['timeout-minutes'], world)), int(bound))
        self.assertTrue(all('secrets.GHCR_READ_TOKEN' not in json.dumps(step) for step, _ in steps))


# Where package 22d's VM step decides otherwise than package 22c's rehearsal, each with its reason.
REVIEWED = {
    ('os/ci/owner_vm.py', "authorization['allowance'] == package"): "the guard's dispatch authorization names the running package",
    ('os/ci/owner_vm.py', "{'16': 'os/manifest/ci/16/host-walk.json', '27': 'os/manifest/ci/27/host-walk.json', "
                          "'22c': 'os/manifest/ci/22c/host-walk.json', '22d': 'os/manifest/ci/22d/host-walk.json'}"
                          ".get(package, 'os/manifest/ci/14/host-walk/result.json')"):
        "each package's own host walk (22c's receipt stays frozen; review 1)",
    ('os/ci/owner_vm.py', "mode == 'ways-back'"): "22c's rehearsal records its bound sources and walks brief 22c's route",
    ('os/ci/owner_vm.py', "mode == 'tools-local'"): "22d's rehearsal records its bound sources and walks brief 22d's route",
}


class DecisionsTest(unittest.TestCase):
    def test_the_rehearsal_decides_like_package_22cs_except_where_reviewed(self):
        tools_local = dict(REHEARSAL_PACKAGE='22d', REHEARSAL_MODE=MODE, GITHUB_REF_NAME=BRANCH, argv=['os/ci/owner_vm.py', MODE])
        ways_back = dict(REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='ways-back', GITHUB_REF_NAME=wb.BRANCH,
                         argv=['os/ci/owner_vm.py', 'ways-back'])
        differing, used, paths = base.differing_decisions([tools_local, ways_back], REVIEWED)
        self.assertEqual(differing, [])
        self.assertEqual(sorted(set(REVIEWED) - used), [], 'stale reviewed decisions')


class GuardTest(unittest.TestCase):
    def setUp(self):
        guard.configure('22d')
        self.addCleanup(guard.configure, '11c')

    def test_the_vm_mode_proves_its_native_step_in_its_own_run(self):
        self.assertTrue(guard.own_native(MODE))
        self.assertFalse(guard.own_native('checks'))
        self.assertEqual(guard.native_gate(MODE, 'probe-budget-ci', dict(runs=[]), 'a' * 40)['status'], 'pending')
        with self.assertRaisesRegex(AssertionError, 'no current probe native preflight'):
            guard.native_gate(MODE, 'ci', dict(runs=[]), 'a' * 40)

    def test_the_guard_step_reserves_and_writes_package_22ds_authorization(self):
        run = dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='in_progress', conclusion=None,
                   created_at='2026-11-15T18:00:00Z', id=11, display_title=LEDGER['titles'][MODE], head_branch=BRANCH)
        environment = dict(REHEARSAL_PACKAGE='22d', REHEARSAL_MODE=MODE, GITHUB_RUN_ID='11', GITHUB_SHA='a' * 40, GITHUB_REF_NAME=BRANCH)
        proof = dict(complete=True, ids_count=1, total_count=1)
        with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder), patch.dict(os.environ, environment, clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch('builtins.print'), \
                patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=[run], history=proof)
                             if path.startswith('actions/runs?') else run), \
                patch.object(model_scope, 'decide', return_value=('slice', ['unchanged'])):
            guard.main()
            written = json.loads(pathlib.Path('evidence/22d-dispatch-authorization.json').read_text())
        self.assertEqual((written['allowance'], written['reserved_minutes'], written['native']['status']), ('22d', 345, 'pending'))
        self.assertEqual(written['dispatch_counts'][MODE], 1)
        self.assertEqual(written['model'], dict(status='not-needed', scope='slice', reasons=['unchanged']))
        # Another package's branch never spends 22d's ledger.
        with patch.dict(os.environ, dict(environment, GITHUB_REF_NAME=wb.BRANCH), clear=True), \
                patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']):
            with self.assertRaisesRegex(AssertionError, 'wrong package branch'):
                guard.main()


class RunnerTest(unittest.TestCase):
    ENVIRONMENT = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=guard.REPOSITORY,
                       GITHUB_REF_NAME=BRANCH, REHEARSAL_PACKAGE='22d', REHEARSAL_MODE=MODE)

    def test_runner_and_registry_accept_only_package_22ds_branch_package_and_mode(self):
        with patch.dict(os.environ, self.ENVIRONMENT, clear=True):
            owner_media.require_runner()
            registry_auth.require_dispatch()
        for key, value in (('GITHUB_REF_NAME', wb.BRANCH), ('GITHUB_REF_NAME', 'main'), ('REHEARSAL_PACKAGE', '22c'),
                           ('REHEARSAL_PACKAGE', '27'), ('REHEARSAL_MODE', 'ways-back'), ('REHEARSAL_MODE', 'reorder-probe'),
                           ('REHEARSAL_MODE', 'update'), ('REHEARSAL_MODE', 'checks'), ('GITHUB_REPOSITORY', 'elsewhere/AresOS')):
            with self.subTest(key=key, value=value), patch.dict(os.environ, dict(self.ENVIRONMENT, **{key: value}), clear=True):
                with self.assertRaises(AssertionError):
                    owner_media.require_runner()
                with self.assertRaises(AssertionError):
                    registry_auth.require_dispatch()
        # And 22c's modes stay 22c's: tools-local on 22c's branch is refused.
        with patch.dict(os.environ, dict(self.ENVIRONMENT, GITHUB_REF_NAME=wb.BRANCH, REHEARSAL_PACKAGE='22c'), clear=True):
            with self.assertRaises(AssertionError):
                owner_media.require_runner()

    def test_the_driver_keeps_the_route_to_its_package(self):
        main = wb.RunnerTest.main.__get__(wb.RunnerTest())
        for package, mode, branch, message in (
                ('22c', MODE, wb.BRANCH, 'are package 22c only'),
                ('27', MODE, 'pkg/27-first-update-release', 'the update rehearsal is package 27 only'),
                ('22d', 'ways-back', BRANCH, 'are package 22c only'),
                ('22d', 'update', BRANCH, 'the update rehearsal is package 27 only'),
                ('22d', 'owner-tools', BRANCH, 'the tools-local rehearsal is package 22d only')):
            with self.subTest(package=package, mode=mode):
                with self.assertRaises(AssertionError):
                    main(package, mode, branch)
                with self.assertRaisesRegex(AssertionError, message):
                    main(package, mode, branch, any_runner=True)



class StandInOriginTest(unittest.TestCase):
    """The guest's stand-in for GitHub (tools_local.standin_origin), built from this checkout."""

    def test_main_holds_version_3_then_this_head_with_the_real_trees(self):
        import subprocess
        import tools_local
        head = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
        with tempfile.TemporaryDirectory() as folder:
            made = tools_local.standin_origin(pathlib.Path(folder) / 'origin', head, ROOT)
            clone = pathlib.Path(folder) / 'AresOS'
            subprocess.run(['git', 'clone', '--quiet', str(made['bundle']), str(clone)], check=True)
            git = lambda *args: subprocess.check_output(['git', '-C', str(clone), *args], text=True).strip()
            stand_v3, stand_head = made['commits'][tools_local.V3_COMMIT], made['commits'][head]
            self.assertEqual(git('rev-parse', 'origin/main'), stand_head)
            self.assertEqual(git('rev-parse', 'version-3^{commit}'), stand_v3)
            self.assertEqual(git('rev-parse', stand_head + '^'), stand_v3)
            # Both are on main, as the folder line's merge-base check needs.
            for commit in (stand_v3, stand_head):
                subprocess.run(['git', '-C', str(clone), 'merge-base', '--is-ancestor', commit, 'origin/main'], check=True)
            # Each os/owner-tools tree is the real commit's, byte for byte; nothing else is in them.
            for real, stand in made['commits'].items():
                real_tree = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', real + ':os/owner-tools'], text=True).strip()
                self.assertEqual(git('rev-parse', stand + ':os/owner-tools'), real_tree)
                self.assertEqual(git('ls-tree', '--name-only', stand), 'os')
            # Version 3's fingerprint and this head's, read as the folder line reads them.
            import hashlib
            fingerprint = lambda commit: hashlib.sha256(subprocess.check_output(
                ['git', '-C', str(clone), 'show', commit + ':os/owner-tools/payload/SHA256SUMS'])).hexdigest()
            self.assertEqual(fingerprint(stand_v3), tools_local.TOOLS_V3)
            commands = json.loads(subprocess.check_output(['git', '-C', str(clone), 'show', stand_head + ':os/owner-tools/commands.json']))
            self.assertEqual(fingerprint(stand_head), hashlib.sha256((ROOT / 'os/owner-tools/payload/SHA256SUMS').read_bytes()).hexdigest())
            self.assertEqual(commands, json.loads((ROOT / 'os/owner-tools/commands.json').read_text()))

    def test_the_walk_is_not_dispatchable_until_built(self):
        import tools_local
        with self.assertRaisesRegex(AssertionError, 'not built yet'):
            tools_local.rehearsal(None, None, None, None, None, None)


if __name__ == '__main__':
    unittest.main()
