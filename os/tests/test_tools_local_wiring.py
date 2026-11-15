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
                         (2400, {'checks': 20, MODE: 4}, 4))
        self.assertEqual((LEDGER['full_cap'], LEDGER['part_b_cap'], LEDGER['publish_cap'], LEDGER['start']),
                         (0, 0, 0, 'first-dispatch'))
        self.assertEqual(LEDGER['titles'], {'checks': 'OS regressions only (no VM)', MODE: 'Two-disk rehearsal (tools-local)'})
        # The walk starts with package 22c's route, so its bounds are 22c's.
        self.assertEqual(LEDGER['job_bounds'], {'checks': 40, MODE: guard.PACKAGES['22c']['job_bounds']['ways-back']})
        self.assertEqual(LEDGER['organization_budget'], guard.PACKAGES['22c']['organization_budget'])
        self.assertIn('briefs/22d-tools-without-stick.md: 20 checks-only runs, 4 VM dispatches and 1200 minutes', LEDGER['budget'])
        # Raised to 2400 by the integrator (2026-11-15), as for 22c; the run and dispatch caps stay.
        self.assertIn('the minute cap is raised from 1200 to 2400', LEDGER['budget'])
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



class WalkTest(unittest.TestCase):
    """The local walk (test_owner_walk's tools-local route): the real harness over the modelled guest."""

    @classmethod
    def setUpClass(cls):
        import test_owner_walk
        cls.walked = test_owner_walk.walk(route='tools-local')
        cls.stages = test_owner_walk.TOOLS_LOCAL_STAGES

    def test_the_walk_passes_every_stage_of_the_brief(self):
        result = self.walked['result']
        self.assertEqual(self.walked['stages'], self.stages)
        self.assertEqual([s['stage'] for s in result['stages']], ['tl-v3', 'tl-cancel', 'tl-unanswered', 'tl-cut', 'tl-install',
                         'tl-tamper', 'tl-stick-next', 'tl-export', 'tl-export-stick'])
        # N-d: no closed-stdin stage.
        self.assertIs(result['closed_stdin_stage'], False)
        self.assertEqual({'final-unattended-windows', 'final-detached-windows'} & set(self.walked['markers']),
                         {'final-unattended-windows', 'final-detached-windows'})

    def test_every_window_shows_its_label_and_is_screenshotted(self):
        import tools_local
        bootstrap = owner_vm.bundle_module('bootstrap')
        fingerprint = self.walked['local'].head
        dialogs = self.walked['result']['dialogs']
        self.assertEqual([d['answer'] for d in dialogs], ['password', 'escape', 'none: closed by the caller', 'password',
                         'password', 'password', 'password'])
        self.assertEqual(dialogs[0]['label'], bootstrap.label(tools_local.TOOLS_V3, bootstrap.ACTIONS['tools-routine']))
        for row in dialogs[1:-1]:
            self.assertEqual(row['label'], bootstrap.label(fingerprint, bootstrap.ACTIONS['tools-routine']))
            self.assertEqual(row['label_length'], 70)
        self.assertEqual(dialogs[-1]['label'], bootstrap.label(fingerprint, bootstrap.ACTIONS['export-routine']))
        self.assertTrue(all(row['screenshot'] == row['stage'] + '-window' for row in dialogs))

    def test_the_closed_window_signals_only_its_helper_and_the_receipt_names_the_folder(self):
        stages = {s['stage']: s for s in self.walked['result']['stages']}
        r1 = stages['tl-unanswered']
        self.assertEqual(r1['signalled'], [r1['helper']])
        self.assertEqual(self.walked['local'].signalled, [r1['helper']])
        install = stages['tl-install']
        self.assertEqual(install['receipt']['caller'], dict(login_uid=1001, terminal=False))
        self.assertEqual(install['receipt']['source'], 'folder')
        self.assertEqual(install['resumed_phase'], 'publish')
        self.assertNotEqual(install['sudo_n_true']['status'], 0)

    def test_each_announced_commit_records_both_hashes_and_one_tree(self):
        import subprocess, tools_local
        announced = self.walked['result']['announced']
        self.assertEqual([row['real'] for row in announced][0], tools_local.V3_COMMIT)
        for row in announced:
            real = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', row['real'] + ':os/owner-tools'], text=True).strip()
            self.assertEqual((row['tree'], row['trees_equal']), (real, True))
            self.assertNotEqual(row['standin'], row['real'])

    def test_a_window_answered_wrongly_stops_the_walk(self):
        import test_owner_walk, tools_local
        window = tools_local.Walk.window
        def typed_into_cancel(walk, stage, out, fingerprint, action, answer):
            return window(walk, stage, out, fingerprint, action, 'password' if answer == 'escape' else answer)
        with patch.object(tools_local.Walk, 'window', typed_into_cancel), self.assertRaises(AssertionError):
            test_owner_walk.walk(route='tools-local')


class CallerTest(unittest.TestCase):
    """The caller program itself, run here against a stand-in sudo and helper (argv[0] only: no sudo,
    no ksshaskpass and nothing privileged runs). It has no controlling terminal, and R1 signals only the
    helper whose parent is the sudo it started."""

    FAKE_SUDO = r'''import os,signal,subprocess,sys,time
# A second child that is not the helper: it must never be signalled.
other=subprocess.Popen(['bash','-c','exec -a /usr/bin/ksshaskpass-not sleep 60'])
helper=subprocess.Popen(['bash','-c','exec -a /usr/bin/ksshaskpass sleep 60'])
code=helper.wait()
other.kill()
if code<0:
    print('sudo: no password was provided',file=sys.stderr); sys.exit(1)
'''

    def run_caller(self, unanswered):
        import subprocess, tools_local
        with tempfile.TemporaryDirectory() as folder:
            folder = pathlib.Path(folder)
            (folder / 'sudo.py').write_text(self.FAKE_SUDO)
            out = folder / 'out'
            out.mkdir()
            line = 'exec -a /usr/bin/sudo ' + sys.executable + ' ' + str(folder / 'sudo.py')
            params = dict(out=str(out), steps=['routine'], commit=None, checkout=str(ROOT), entries={},
                          lines=dict(routine=line), unanswered=unanswered)
            source = tools_local.program(tools_local.CALLER, params=json.dumps(params))
            subprocess.run([sys.executable, '-c', source], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                           start_new_session=True, check=True, timeout=60)
            return json.loads((out / 'done.json').read_text())

    def test_the_unanswered_window_is_closed_by_signalling_only_the_helper(self):
        done = self.run_caller(1)
        self.assertIs(done['terminal'], False)
        self.assertIs(done['stdin_terminal'], False)
        routine = done['routine']
        self.assertEqual(routine['signalled'], [routine['helper']])
        self.assertIs(routine['helper_gone'], True)
        self.assertEqual((routine['status'], routine['stderr'].strip()), (1, 'sudo: no password was provided'))

    def test_without_unanswered_the_caller_signals_nothing(self):
        import tools_local
        # The stand-in helper would wait 60 seconds; here its line ends by itself instead.
        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder)
            params = dict(out=folder, steps=['routine'], commit=None, checkout=str(ROOT), entries={},
                          lines=dict(routine='echo PASS install'), unanswered=0)
            import subprocess
            subprocess.run([sys.executable, '-c', tools_local.program(tools_local.CALLER, params=json.dumps(params))],
                           stdin=subprocess.DEVNULL, start_new_session=True, check=True, timeout=60)
            done = json.loads((out / 'done.json').read_text())
        self.assertEqual((done['routine']['status'], done['routine']['stdout'], done['routine']['signalled']), (0, 'PASS install\n', []))


class NextVersionTest(unittest.TestCase):
    def test_the_next_version_is_this_payload_one_version_higher(self):
        import tools_local
        owner = owner_vm.bundle_module('owner')
        with tempfile.TemporaryDirectory() as folder:
            number, fingerprint = tools_local.next_version(pathlib.Path(folder) / 'next', ROOT / 'os/owner-tools/payload')
            current = json.loads((ROOT / 'os/owner-tools/payload/history.json').read_text())
            self.assertEqual(number, current['tools_version'] + 1)
            self.assertEqual(owner.checked_bundle(pathlib.Path(folder) / 'next'), fingerprint)
            changed = [row['path'] for row in json.loads((pathlib.Path(folder) / 'next/SHA256.json').read_text())
                       if (ROOT / 'os/owner-tools/payload' / row['path']).read_bytes() != (pathlib.Path(folder) / 'next' / row['path']).read_bytes()]
            self.assertEqual(changed, ['history.json'])


class ReceiptTest(unittest.TestCase):
    """22d's own host-walk receipt is fresh: every bound file has the bytes it was walked with."""

    def test_the_receipt_is_fresh_and_names_this_walk(self):
        import hashlib
        receipt = json.loads((ROOT / 'os/manifest/ci/22d/host-walk.json').read_text())
        self.assertEqual((receipt['status'], receipt['stick_across_reboot']), ('passed', False))
        import test_owner_walk
        self.assertEqual(receipt['stages'], {MODE: test_owner_walk.TOOLS_LOCAL_STAGES})
        paths = {row['path'] for row in receipt['sources']}
        self.assertLessEqual({'os/ci/tools_local.py', 'os/ci/owner_vm.py', 'os/tests/test_owner_walk.py',
                              'os/tests/test_tools_local_wiring.py', 'reviews/22d-tools-without-stick/walk-host.py'}, paths)
        for row in receipt['sources']:
            self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(), row['sha256'], row['path'])


if __name__ == '__main__':
    unittest.main()
