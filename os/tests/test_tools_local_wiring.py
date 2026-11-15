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
                         (2400, {'checks': 20, MODE: 6}, 6))
        self.assertEqual((LEDGER['full_cap'], LEDGER['part_b_cap'], LEDGER['publish_cap'], LEDGER['start']),
                         (0, 0, 0, 'first-dispatch'))
        self.assertEqual(LEDGER['titles'], {'checks': 'OS regressions only (no VM)', MODE: 'Two-disk rehearsal (tools-local)'})
        # The walk starts with package 22c's route, so its bounds are 22c's.
        self.assertEqual(LEDGER['job_bounds'], {'checks': 40, MODE: guard.PACKAGES['22c']['job_bounds']['ways-back']})
        self.assertEqual(LEDGER['organization_budget'], guard.PACKAGES['22c']['organization_budget'])
        self.assertIn('briefs/22d-tools-without-stick.md: 20 checks-only runs, 4 VM dispatches and 1200 minutes', LEDGER['budget'])
        # Raised to 2400 by the integrator in part b (2026-11-15), as for 22c; the checks cap stays.
        self.assertIn('the minute cap is raised from 1200 to 2400', LEDGER['budget'])
        # Step 6, part e (integrator, 2026-11-15): the VM dispatches from 4 to 6, as for 22c; the note says why.
        self.assertIn("Step 6, part e (integrator's decision, 2026-11-15): the VM dispatch cap is raised from 4 to 6 "
                      "(tools-local from 4 to 6)", LEDGER['budget'])
        self.assertIn('the caps exist to stop runaway loops, and three runs stopped on harness issues', LEDGER['budget'])
        self.assertIn('22d', guard.TITLED_PACKAGES)
        self.assertIn('22d', guard.OWN_RUN_PACKAGES)

    def test_six_vm_dispatches_and_no_seventh(self):
        job = dict(name='Pinned live ISO inspection and two-disk rehearsal', conclusion='failure',
                   started_at='2026-11-15T18:00:00Z', completed_at='2026-11-15T19:00:00Z',
                   steps=[dict(name='Set up job', conclusion='success', started_at='2026-11-15T18:00:00Z',
                               completed_at='2026-11-15T19:00:00Z')])
        runs = [dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='completed', conclusion='failure',
                     created_at='2026-11-15T18:00:00Z', id=n, display_title=LEDGER['titles'][MODE]) for n in range(1, 7)]
        guard.configure('22d')
        self.addCleanup(guard.configure, '11c')
        with patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=runs) if path.startswith('actions/runs?')
                          else dict(total_count=1, jobs=[job])):
            result = guard.budget(0)
            self.assertEqual((result['dispatch_counts'], result['consumed_minutes']), ({'checks': 0, MODE: 6}, 360))
            runs.append(dict(runs[-1], id=7))
            with self.assertRaisesRegex(AssertionError, MODE + ' dispatch allowance exhausted'):
                guard.budget(0)


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


class VerifyReleaseTest(unittest.TestCase):
    """Step 6c (integrator, 2026-11-15): in the tools-local mode release 27's trees are bound to its source commit.

    Run 43690565301 stopped at verify_release.py: this branch's image sources hold the next release's unreleased
    changes, while the VM runs the pinned release 27 image. Every identity check stays; only 22d's mode reads
    the recorded trees at the source commit instead of at HEAD."""
    MODE_ENVIRONMENT = dict(GITHUB_REF_NAME=BRANCH, REHEARSAL_PACKAGE='22d', REHEARSAL_MODE=MODE)
    # What run 43690565301's checkout held: four image sources moved on after release 27.
    MOVED = {'os/Containerfile': 'c' * 40, 'os/build.sh': 'd' * 40, 'os/config': 'e' * 40, 'os/packages.lock.json': 'f' * 40}

    def verify(self, environment=MODE_ENVIRONMENT, **kwargs):
        return base.run_verify_release(self, environment=environment, **kwargs)

    def test_trees_found_at_the_source_commit_pass_and_name_the_paths_that_differ(self):
        code, printed, calls = self.verify(head=self.MOVED)
        source = base.RELEASE27_SOURCE
        self.assertEqual(code, 0)
        self.assertIn('the image under test is release 27 built from ' + source, printed)
        self.assertIn('differ in os/Containerfile, os/build.sh, os/config, os/packages.lock.json because they hold '
                      'unreleased changes', printed)
        # The commit was in the clone: no fetch; every recorded tree read at the source commit.
        self.assertEqual(calls[0], ['git', 'cat-file', '-e', source + '^{commit}'])
        self.assertNotIn('fetch', [c[1] for c in calls])
        self.assertEqual(sorted(c[4].split(':', 1)[1] for c in calls if c[4:5] and c[4].startswith(source + ':')),
                         sorted(base.RELEASE27_TREES))
        # An unchanged checkout passes too and says so.
        code, printed, _ = self.verify()
        self.assertEqual(code, 0)
        self.assertIn('differ in no path because', printed)

    def test_a_source_commit_missing_from_the_clone_is_fetched_first(self):
        code, _, calls = self.verify(head=self.MOVED, present=False)
        source = base.RELEASE27_SOURCE
        self.assertEqual(code, 0)
        self.assertEqual(calls[:2], [['git', 'cat-file', '-e', source + '^{commit}'], ['git', 'fetch', '--no-tags', 'origin', source]])

    def test_a_missing_or_different_tree_at_the_source_commit_refuses(self):
        for path in ('os/config', 'os/manifest/base.json', 'os/tests/audit.py'):
            for tree in ('a' * 40, None):
                with self.subTest(path=path, tree=tree), self.assertRaisesRegex(
                        AssertionError, 'does not hold its recorded tree: ' + re.escape(path)):
                    self.verify(head=self.MOVED, at_source={path: tree})

    def test_every_identity_check_still_applies_in_the_mode(self):
        with self.assertRaisesRegex(AssertionError, 'must have succeeded'):
            self.verify(job='image')
        with self.assertRaises(AssertionError):  # the rows' shape
            self.verify(trees=dict(base.RELEASE27_TREES))
        with self.assertRaises(AssertionError):  # a recorded tree that is no object ID
            self.verify(trees=[dict(tree='HEAD', path=path) for path in base.RELEASE27_TREES])
        with self.assertRaises(AssertionError):  # a path list other than release 27's
            self.verify(trees=[dict(tree=tree, path=path) for path, tree in base.RELEASE27_TREES.items()
                               if path != 'os/keys'])

    def test_other_branches_packages_and_modes_still_compare_head(self):
        """22c's and 27's branches, and 22d's branch outside its mode (the regressions step runs without
        REHEARSAL_PACKAGE), behave as before: HEAD's trees, no git command beyond rev-parse."""
        for environment in (dict(GITHUB_REF_NAME=wb.BRANCH, REHEARSAL_PACKAGE='22c', REHEARSAL_MODE='ways-back'),
                            dict(GITHUB_REF_NAME='pkg/27-first-update-release', REHEARSAL_PACKAGE='27', REHEARSAL_MODE='update'),
                            dict(self.MODE_ENVIRONMENT, REHEARSAL_PACKAGE='22c'), dict(self.MODE_ENVIRONMENT, REHEARSAL_MODE='ways-back'),
                            dict(self.MODE_ENVIRONMENT, GITHUB_REF_NAME='main'),
                            {k: v for k, v in self.MODE_ENVIRONMENT.items() if k != 'REHEARSAL_PACKAGE'}, {}):
            with self.subTest(**environment):
                self.assertEqual(self.verify(environment), (0, 'Qualified private org release ' + base.RELEASE27_SOURCE
                    + '; runtime payload unchanged; testing ghcr.io/ares-empire/aresos@sha256:' + '27' * 32 + '\n', []))
                with self.assertRaisesRegex(AssertionError, 'Release 27 runtime payload changed: os/Containerfile'):
                    self.verify(environment, head=self.MOVED)



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



# What WalkTest's walk opens and runs. An audit hook cannot be removed, so it is added once and records only
# while that walk runs: absolute paths (resolved when opened) and command lines.
RECORDING = dict(hooked=False, into=None)


def recorder(event, args):
    into = RECORDING['into']
    if into is None:
        return
    if event == 'open' and isinstance(args[0], (str, bytes, os.PathLike)):
        into['opened'].add(os.path.abspath(os.fsdecode(args[0])))
    elif event == 'subprocess.Popen':
        into['commands'].append([os.fsdecode(word) if isinstance(word, (bytes, os.PathLike)) else str(word) for word in args[1]])


class WalkTest(unittest.TestCase):
    """The local walk (test_owner_walk's tools-local route): the real harness over the modelled guest."""

    @classmethod
    def setUpClass(cls):
        import test_owner_walk
        if not RECORDING['hooked']:
            sys.addaudithook(recorder)
            RECORDING['hooked'] = True
        cls.reads = RECORDING['into'] = dict(opened=set(), commands=[])
        try:
            cls.walked = test_owner_walk.walk(route='tools-local')
        finally:
            RECORDING['into'] = None
        cls.stages = test_owner_walk.TOOLS_LOCAL_STAGES

    def test_the_walk_reads_no_image_source_of_release_27_from_this_checkout(self):
        """Step 6c: in this mode verify_release binds release 27's trees to its source commit, not to this
        checkout, whose image sources hold the next release's changes. So the harness must predict nothing about
        the release 27 VM from them: no file under these paths opened, no git read of them at any commit.

        os/manifest/base.json is the exception: in the VM (not in this walk) the stock install reads its
        `reference`, the base release 27 was built on, and verify_release asserts it equals the release's base in
        every mode. The steps the walk replaces (the stock install, each start, the snapshots, the audits) were
        read by hand for step 6c (PROGRESS.md)."""
        payload = [path for path in base.RELEASE27_TREES if path != 'os/manifest/base.json']
        inside = sorted({pathlib.Path(p).relative_to(ROOT).as_posix() for p in self.reads['opened']
                         if pathlib.Path(p).is_relative_to(ROOT)})
        self.assertEqual([p for p in inside if any(p == x or p.startswith(x + '/') for x in payload)], [])
        git = [c for c in self.reads['commands'] if c[:1] == ['git']]
        named = lambda word: word.split(':', 1)[1] if ':' in word else word  # a `<commit>:<path>` word names the path
        self.assertEqual([c for c in git if any(named(w) == x or named(w).startswith(x + '/') for w in c[1:] for x in payload)], [])
        git = [' '.join(c) for c in git]
        # The recorder saw the walk: release 27's record, version 2's route, and git reads of the tools.
        self.assertLessEqual({'os/manifest/release.json', 'os/manifest/releases/13.json'}, set(inside))
        self.assertTrue([c for c in git if ':os/owner-tools' in c])

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
        # Step 6d: each window settled before its picture, and the picture differs in the centre from the one
        # taken just before that stage's launcher was typed.
        shots = self.walked['local'].shots
        for row in dialogs:
            self.assertEqual((row['settled'], row['before']), (True, row['stage'] + '-before'))
            self.assertGreaterEqual(row['centre_changed'], tools_local.CENTRE_CHANGED)
            self.assertLess(shots.index(row['before']), shots.index(row['screenshot']))

    def test_a_launcher_lost_after_a_vt_switch_is_typed_once_more(self):
        """tl-install's caller is started right after the console at tty3 (a real VT switch): its first line is lost."""
        local = self.walk_with(lost={'tl-install': 1})
        launcher = 'bash /run/aresos-caller-tl-install.sh\n'
        self.assertEqual(sum(text == launcher for text, _ in local.typed), 2)
        shots = local.shots
        self.assertLess(shots.index('tl-install-before'), shots.index('tl-install-launch-miss'))
        self.assertLess(shots.index('tl-install-launch-miss'), shots.index('tl-install-before-retry'))
        self.assertLess(shots.index('tl-install-before-retry'), shots.index('tl-install-window'))
        # Every other stage typed its launcher once.
        others = [text for text, _ in local.typed if text.startswith('bash /run/aresos-caller-') and text != launcher]
        self.assertEqual(len(others), len(set(others)))

    def test_a_window_missing_from_the_screen_stops_before_the_password(self):
        found = []
        with self.assertRaisesRegex(AssertionError, r'^STOP: no window on the screen at tl-v3 '):
            self.walk_with(hidden={'tl-v3'}, found=found)
        local, = found
        self.assertIn('tl-v3-window', local.shots)
        # Nothing typed after the window was seen (his password was typed earlier, at tty4's passwd and sudo).
        self.assertEqual(local.typed[local.windows['tl-v3']['typed']:], [])

    def walk_with(self, lost=(), hidden=(), found=None):
        """The local walk with some launcher lines lost or some windows kept off the screen."""
        import test_owner_walk
        made = [] if found is None else found

        class Local(test_owner_walk.ToolsLocal):
            def __init__(self, *args):
                super().__init__(*args)
                self.lost, self.hidden = dict(lost), set(hidden)
                made.append(self)
        with patch.object(test_owner_walk, 'ToolsLocal', Local):
            test_owner_walk.walk(route='tools-local')
        return made[0]

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


def settle_functions():
    """DIALOG's cpu() and settle(), defined as the guest program defines them."""
    import tools_local
    namespace = {}
    exec('import pathlib,time\n' + tools_local.SETTLE, namespace)
    return namespace['cpu'], namespace['settle']


def stat_line(state, utime, stime, name='ksshaskpass'):
    """A /proc/<pid>/stat line: pid, (name), state, parent, nine fields, utime, stime, the rest."""
    return '4242 (' + name + ') ' + state + ' 4241 ' + ' '.join(['0'] * 9) + ' ' + str(utime) + ' ' + str(stime) + ' 0 0 20 0 1 0 98765\n'


class SettleTest(unittest.TestCase):
    """Step 6d: DIALOG reports the window only once the helper has settled (at least 3 s since first seen and its
    CPU time unchanged for 2 s), gives up after 20 s, and notices a helper that vanished. Fake /proc values and
    a fake clock."""

    def settle(self, ticks):
        """ticks(seconds since the first sighting) -> utime, or None once the helper is gone."""
        cpu, settle = settle_functions()
        clock = dict(now=100.0)

        def read(pid):
            value = ticks(clock['now'] - 100.0)
            if value is None:
                raise FileNotFoundError('/proc/' + str(pid) + '/stat')
            return stat_line('S', value, 7)

        def sleep(seconds):
            clock['now'] += seconds
        return settle(4242, cpu=lambda pid: cpu(pid, read=read), now=lambda: clock['now'], sleep=sleep)

    def test_the_cpu_time_is_utime_and_stime_after_the_last_parenthesis(self):
        cpu, _ = settle_functions()
        self.assertEqual(cpu(4242, read=lambda pid: stat_line('S', 12, 5)), 17)
        # A process may name itself with spaces and ')'.
        self.assertEqual(cpu(4242, read=lambda pid: stat_line('R', 30, 4, name='ksshask) (pass ) S 1')), 34)
        for state in ('Z', 'X'):
            self.assertIsNone(cpu(4242, read=lambda pid: stat_line(state, 12, 5)))
        def missing(pid):
            raise FileNotFoundError(pid)
        self.assertIsNone(cpu(4242, read=missing))
        self.assertIsNone(cpu(4242, read=lambda pid: '4242 (ksshaskpass) S 4241 0 0\n'))

    def test_an_idle_helper_settles_three_seconds_after_it_was_first_seen(self):
        waited = self.settle(lambda seconds: 40)
        self.assertEqual((waited['settled'], waited['gone']), (True, False))
        self.assertTrue(3.0 <= waited['settle_seconds'] <= 3.2, waited)

    def test_a_helper_still_drawing_settles_two_seconds_after_its_cpu_time_last_moved(self):
        waited = self.settle(lambda seconds: int(seconds * 10) if seconds < 5 else 50)
        self.assertEqual((waited['settled'], waited['gone']), (True, False))
        self.assertTrue(7.0 <= waited['settle_seconds'] <= 7.4, waited)

    def test_a_helper_that_never_settles_is_given_up_after_twenty_seconds(self):
        import inspect, tools_local
        waited = self.settle(lambda seconds: int(seconds * 10))
        self.assertEqual((waited['settled'], waited['gone']), (False, False))
        self.assertTrue(20.0 <= waited['settle_seconds'] <= 20.2, waited)
        # R1's caller closes the window 30 s after it first saw it: the wait, the picture and the serial round
        # trips must all come before that.
        _, settle = settle_functions()
        self.assertLessEqual(inspect.signature(settle).parameters['most'].default + 10, tools_local.Walk.R1_SECONDS)

    def test_a_helper_that_vanishes_is_reported_gone(self):
        waited = self.settle(lambda seconds: 40 if seconds < 1 else None)
        self.assertEqual((waited['settled'], waited['gone']), (False, True))
        self.assertTrue(1.0 <= waited['settle_seconds'] <= 1.2, waited)
        waited = self.settle(lambda seconds: None)
        self.assertEqual((waited['settled'], waited['gone'], waited['settle_seconds']), (False, True, 0.0))


class DialogProgramTest(unittest.TestCase):
    """The real DIALOG program, run here against a stand-in sudo and helper (argv[0] only, `sleep` underneath:
    no sudo, no ksshaskpass and nothing privileged runs)."""

    FAKE_SUDO = r'''import subprocess
helper=subprocess.Popen(['bash','-c','exec -a /usr/bin/ksshaskpass sleep 60'])
print(helper.pid,flush=True)
helper.wait()
'''

    @contextlib.contextmanager
    def helper(self):
        import signal, subprocess
        with tempfile.TemporaryDirectory() as folder:
            folder = pathlib.Path(folder)
            (folder / 'sudo.py').write_text(self.FAKE_SUDO)
            sudo = subprocess.Popen(['bash', '-c', 'exec -a /usr/bin/sudo ' + sys.executable + ' ' + str(folder / 'sudo.py')],
                                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True, start_new_session=True)
            try:
                helper = int(sudo.stdout.readline())
                (folder / 'started.json').write_text(json.dumps(dict(pid=sudo.pid)))
                yield folder, sudo.pid, helper
            finally:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(sudo.pid, signal.SIGKILL)
                sudo.wait()
                sudo.stdout.close()

    def dialog(self, folder):
        import subprocess, tools_local
        return subprocess.Popen([sys.executable, '-c', tools_local.program(tools_local.DIALOG, out=str(folder), seconds=15)],
                                stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True)

    def test_the_window_is_reported_once_its_helper_has_settled(self):
        import time
        with self.helper() as (folder, sudo, helper):
            started = time.monotonic()
            seen = json.loads(self.dialog(folder).communicate(timeout=60)[0])
            elapsed = time.monotonic() - started
        self.assertEqual((seen['status'], seen['sudo'], seen['helper'], seen['parent']), ('window', sudo, helper, sudo))
        self.assertEqual((seen['argv'], seen['uid']), (['/usr/bin/ksshaskpass', '60'], os.getuid()))
        self.assertEqual((seen['settled'], seen['gone']), (True, False))
        self.assertGreaterEqual(seen['settle_seconds'], 3)
        self.assertGreaterEqual(elapsed, 3)

    def test_a_helper_gone_before_it_settled_is_no_window(self):
        import signal, time
        with self.helper() as (folder, sudo, helper):
            dialog = self.dialog(folder)
            time.sleep(2)
            os.kill(helper, signal.SIGTERM)
            seen = json.loads(dialog.communicate(timeout=60)[0])
        self.assertEqual((seen['status'], seen['helper'], seen['settled'], seen['gone']),
                         ('the window closed before it settled', helper, False, True))
        self.assertLess(seen['settle_seconds'], 3)


class WindowPictureTest(unittest.TestCase):
    """Step 6d: the window's picture must differ in the screen's centre from the one taken just before the
    launcher was typed; foot's lines at the top of its cleared screen do not count."""

    def test_only_a_window_in_the_screen_centre_counts(self):
        from PIL import Image, ImageDraw
        import tools_local
        prompt, launcher = ((8, 8, 400, 30), (220, 220, 204)), ((8, 8, 700, 60), (220, 220, 204))
        with tempfile.TemporaryDirectory() as folder:
            def picture(name, *boxes, size=(1280, 800)):
                image = Image.new('RGB', size, (36, 36, 36))
                for box, colour in boxes:
                    ImageDraw.Draw(image).rectangle(box, fill=colour)
                image.save(pathlib.Path(folder) / (name + '.png'))
                return pathlib.Path(folder) / (name + '.png')
            before = picture('before', prompt)
            change = lambda *boxes: tools_local.centre_change(before, picture('after', *boxes))
            self.assertEqual(change(prompt)['fraction'], 0)
            # The launcher line and the next prompt, at the top of foot's screen.
            self.assertEqual(change(launcher)['fraction'], 0)
            # One glyph in the middle is no window.
            self.assertLess(change(launcher, ((630, 390, 640, 410), (220, 220, 204)))['fraction'], tools_local.CENTRE_CHANGED)
            # A dialog placed in the middle of the screen.
            window = change(launcher, ((390, 290, 890, 510), (239, 240, 241)))
            self.assertEqual(window['box'], [320, 200, 960, 600])
            self.assertGreater(window['fraction'], 10 * tools_local.CENTRE_CHANGED)
            self.assertEqual(window['changed_box'], (70, 90, 571, 311))
            with self.assertRaisesRegex(AssertionError, '^STOP: the screen size changed'):
                tools_local.centre_change(before, picture('smaller', size=(1024, 768)))


class LauncherTest(unittest.TestCase):
    """Step 6d: the launcher typed in foot starts its caller once; typed a second time it refuses (`set -C`)."""

    def test_the_launcher_starts_its_caller_once(self):
        import subprocess, time, tools_local
        with tempfile.TemporaryDirectory() as folder:
            out = pathlib.Path(folder) / 'aresos-caller-tl-x'
            out.mkdir()
            ran = pathlib.Path(folder) / 'ran'
            pathlib.Path(str(out) + '.py').write_text('with open(' + repr(str(ran)) + ', "a") as stream: stream.write("x")\n')
            script = tools_local.launcher(str(out))
            self.assertEqual(script.splitlines()[:2], ['#!/bin/bash', 'set -C'])
            pathlib.Path(str(out) + '.sh').write_text(script)
            first = subprocess.run(['bash', str(out) + '.sh'], capture_output=True, text=True, timeout=30)
            deadline = time.monotonic() + 10
            while not ran.exists() and time.monotonic() < deadline:
                time.sleep(.05)
            second = subprocess.run(['bash', str(out) + '.sh'], capture_output=True, text=True, timeout=30)
            time.sleep(.5)
            self.assertEqual((first.returncode, first.stderr, ran.read_text()), (0, '', 'x'))
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('cannot overwrite existing file', second.stderr)


class LaunchOrderTest(unittest.TestCase):
    """Walk.caller with a stand-in guest: Ctrl+U before each launcher, the picture just before it, the check
    that it ran, and one more attempt after a miss (VM runs: lines lost after a real VT switch)."""

    LAUNCHER = 'bash /run/aresos-caller-tl-x.sh\n'

    def run_caller(self, found):
        import time, tools_local
        from guest_shell import syntax
        events, answers = [], list(found)
        german = {tuple(owner_vm.physical_keys(c, 'de')): c for c in set(self.LAUNCHER)}

        class Guest:
            owner_layout = 'de'

            def keys(self, names):
                char = german.get(tuple(names))
                if char is None:
                    events.append(('keys', tuple(names)))
                elif events and events[-1][0] == 'typed':
                    events[-1] = ('typed', events[-1][1] + char)
                else:
                    events.append(('typed', char))

            def command(self, name, source, **kw):
                syntax(name, source)
                events.append(('command', name))

            def capture_json(self, name, source):
                syntax(name, source)
                events.append(('capture', name))
                return dict(found=answers.pop(0))

            def screenshot(self, name):
                events.append(('screenshot', name))
        real_sleep = time.sleep

        def sleep(seconds):
            # Only the walk's own waits belong to the order; the syntax check's subprocess keeps the real one.
            if sys._getframe(1).f_globals.get('__name__') == 'tools_local':
                events.append(('sleep', seconds))
            else:
                real_sleep(seconds)
        walk = tools_local.Walk(owner_vm, Guest(), 'not-typed-here', {}, 'a' * 40, 'b' * 64)
        with patch.object(tools_local.time, 'sleep', new=sleep):
            try:
                result = walk.caller('tl-x', ('routine',), 'c' * 40, lines=dict(routine='true'))
            except AssertionError as error:
                result = error
        return events, result, walk

    def attempt(self, shot, check):
        return [('keys', ('ctrl', 'u')), ('keys', ('ctrl', 'l')), ('sleep', .5), ('screenshot', shot),
                ('typed', self.LAUNCHER), ('capture', check)]

    def test_the_launcher_is_typed_on_a_cleared_line_after_its_picture(self):
        events, result, walk = self.run_caller([True])
        self.assertEqual(result, '/run/aresos-caller-tl-x')
        self.assertEqual(events, [('command', 'tl-x-caller-prepare'), ('keys', ('ctrl', 'alt', 'f1')), ('command', 'tl-x-foot-ready'),
                                  ('command', 'tl-x-session'), ('sleep', 1), *self.attempt('tl-x-before', 'tl-x-launched')])
        self.assertEqual(walk.before, {'tl-x': 'tl-x-before'})

    def test_a_lost_launcher_is_typed_once_more(self):
        events, result, walk = self.run_caller([False, True])
        self.assertEqual(result, '/run/aresos-caller-tl-x')
        self.assertEqual(events[4:], [('sleep', 1), *self.attempt('tl-x-before', 'tl-x-launched'), ('screenshot', 'tl-x-launch-miss'),
                                      *self.attempt('tl-x-before-retry', 'tl-x-launched-retry')])
        self.assertEqual(walk.before, {'tl-x': 'tl-x-before-retry'})

    def test_a_launcher_lost_twice_stops_naming_its_stage(self):
        events, result, _ = self.run_caller([False, False])
        self.assertIsInstance(result, AssertionError)
        self.assertRegex(str(result), '^STOP: the caller did not start at tl-x: ')
        self.assertEqual([e for e in events if e[0] == 'typed'], [('typed', self.LAUNCHER)] * 2)
        self.assertEqual(events[-1], ('capture', 'tl-x-launched-retry'))


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
    """22d's own host-walk receipt names this walk; it is fresh until 22d's record step and frozen after it."""

    def test_the_receipt_is_fresh_until_the_record_step_and_frozen_after(self):
        """Before the record step: regenerate with `python3 reviews/22d-tools-without-stick/walk-host.py` after
        changing a file it binds. After it (run 43737933979) the receipt is what the rehearsal walked and is never
        regenerated: bound files changed since wait on the pending list (`rebind.py pending`) for the next rehearsal,
        as package 22c's receipt does (test_ways_back_probe.HostWalkReceiptTest)."""
        import hashlib
        receipt = json.loads((ROOT / 'os/manifest/ci/22d/host-walk.json').read_text())
        self.assertEqual((receipt['status'], receipt['stick_across_reboot']), ('passed', False))
        import test_owner_walk
        self.assertEqual(receipt['stages'], {MODE: test_owner_walk.TOOLS_LOCAL_STAGES})
        paths = {row['path'] for row in receipt['sources']}
        self.assertLessEqual({'os/ci/tools_local.py', 'os/ci/owner_vm.py', 'os/tests/test_owner_walk.py',
                              'os/tests/test_tools_local_wiring.py', 'reviews/22d-tools-without-stick/walk-host.py'}, paths)
        bindings = ROOT / 'os/manifest/ci/22d/source-bindings.json'
        if bindings.exists():
            self.assertEqual(receipt['sources'], json.loads(bindings.read_text())['tables'][0]['sources'])
            return
        for row in receipt['sources']:
            self.assertEqual(hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest(), row['sha256'], row['path'])


if __name__ == '__main__':
    unittest.main()
