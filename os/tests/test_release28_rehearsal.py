"""Package 42, step 3: release 28's rehearsal mode `release-28` and its wiring (modelled on test_tools_local_wiring).

The ledger kind has cap 3 (step 6 raised it from 0 with the lead's OK); the mode runs the rehearsal job on package 42's
branch and nowhere else; every step script accepts package 42's environment; the guard proves the native step in
the run itself; the announced bundle is version 4's code with tools_version 5 and release 28's record; the stand-in
origin holds 634e1237's trees, then that bundle; and the local walk passes with Control riding and without.
No VM, privilege or real tool runs.
"""
import contextlib
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import model_scope
import owner_media
import registry_auth
import rehearsal_guard as guard
import release28_walk as walk
import test_release27 as base
import test_tools_local_wiring as local
import test_ways_back_probe as wb
from test_owner_staged_release import condition

BRANCH = 'pkg/42-release-28'
MODE = 'release-28'
LEDGER = guard.PACKAGES['42']
WORKFLOW, JOB = wb.WORKFLOW, wb.JOB
OTHER_MODES = local.OTHER_MODES + ('tools-local',)


def inputs(mode=MODE):
    return dict(base.UPDATE_INPUTS, **{'github.ref_name': BRANCH, 'inputs.rehearsal': mode})


def job_steps(mode=MODE):
    world = inputs(mode)
    github = dict(base.UPDATE_GITHUB, GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH)
    merged = {**WORKFLOW.get('env', {}), **JOB.get('env', {})}
    environment = dict(github, **{k: base.workflow_text(v, world) for k, v in merged.items()})
    for step in JOB['steps']:
        if 'run' in step and base.workflow_expression(step.get('if', 'success()'), world):
            yield step, dict(environment, **{k: base.workflow_text(v, world) for k, v in step.get('env', {}).items()})


def record(digest='28' * 32, identity=walk.IDENTITY, daily_wheel=True):
    import test_owner_walk
    value = json.loads(test_owner_walk.release28_record())
    value['reference'] = 'ghcr.io/ares-empire/aresos@sha256:' + digest
    value['signature']['identity'], value['daily_wheel'] = identity, daily_wheel
    return (json.dumps(value, indent=2) + '\n').encode()


class LedgerTest(unittest.TestCase):
    def test_the_kind_is_recorded_with_cap_3_and_22ds_bounds(self):
        # Step 3 recorded it with cap 0; step 6 raised it to the brief's three rehearsal runs.
        self.assertEqual(LEDGER['dispatch_caps'][MODE], 7)
        self.assertEqual((LEDGER['dispatch_caps']['checks'], LEDGER['minute_cap']), (12, 2400))
        self.assertIn('Step 6 (2026-11-19, the lead): release-28 from 0 to 3', LEDGER['budget'])
        self.assertEqual(LEDGER['job_bounds'][MODE], guard.PACKAGES['22d']['job_bounds']['tools-local'])
        self.assertEqual(LEDGER['titles'][MODE], 'Two-disk rehearsal (release-28)')
        self.assertIn('adds the rehearsal kind release-28', LEDGER['budget'])
        self.assertIn("with cap 0: step 6 raises it, with the lead's OK", LEDGER['budget'])
        # The publish gate: shut until step 5 opened it for one publish (review 1, B1; board #388).
        self.assertEqual((LEDGER['dispatch_caps']['publish-28'], LEDGER['publish_cap']), (1, 1))

    def test_the_cap_stops_the_dispatch_after_it(self):
        run = dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='completed', conclusion='failure',
                   created_at='2026-11-17T18:00:00Z', id=1, display_title=LEDGER['titles'][MODE])
        # One timed step, so the guard charges the job's 10 minutes, not its 345-minute bound: seven unaccountable
        # runs would pass the 2400-minute cap before the dispatch cap this test is about.
        job = dict(name='Pinned live ISO inspection and two-disk rehearsal', conclusion='failure',
                   started_at='2026-11-17T18:00:00Z', completed_at='2026-11-17T18:10:00Z',
                   steps=[dict(name='Set up job', started_at='2026-11-17T18:00:00Z', completed_at='2026-11-17T18:10:00Z')])
        guard.configure('42')
        self.addCleanup(guard.configure, '11c')
        api = lambda path: dict(workflow_runs=[run]) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        with patch.object(guard, 'api', side_effect=api):
            # Cap 0 (step 3) stopped the first dispatch.
            with patch.dict(LEDGER['dispatch_caps'], {MODE: 0}), \
                    self.assertRaisesRegex(AssertionError, MODE + ' dispatch allowance exhausted'):
                guard.budget(0)
            self.assertEqual(guard.budget(0)['dispatch_counts'][MODE], 1)
        # Cap 7 (step 6, then 2026-11-20 four times; rehearsal 4 stopped on the walk's login rule, rehearsal 5 on a
        # stalled serial console, rehearsal 6 on the Terminal's environment): the eighth stops.
        runs = [dict(run, id=n) for n in range(1, 9)]
        api = lambda path: dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        with patch.object(guard, 'api', side_effect=api):
            with self.assertRaisesRegex(AssertionError, MODE + ' dispatch allowance exhausted'):
                guard.budget(0)
            del runs[-1]
            self.assertEqual(guard.budget(0)['dispatch_counts'][MODE], 7)


class DispatchTest(unittest.TestCase):
    def test_the_mode_is_a_workflow_option_and_the_branch_maps_to_package_42(self):
        self.assertIn(MODE, WORKFLOW['on']['workflow_dispatch']['inputs']['rehearsal']['options'])
        expression = re.fullmatch(r'\$\{\{(.*)\}\}', WORKFLOW['env']['REHEARSAL_PACKAGE'].strip())[1]
        self.assertEqual(base.workflow_expression(expression, inputs()), '42')
        # The run's title (the guard counts it by title) is the ledger's.
        self.assertTrue(WORKFLOW['run-name'].startswith("${{ inputs.rehearsal && format('Two-disk rehearsal ({0})', inputs.rehearsal) || "))
        self.assertEqual('Two-disk rehearsal ({0})'.format(MODE), LEDGER['titles'][MODE])

    def test_the_mode_runs_the_rehearsal_job_on_its_branch_and_nothing_else_runs_there(self):
        on_branch = {'github.ref_name': BRANCH}
        for name, job in WORKFLOW['jobs'].items():
            with self.subTest(job=name):
                self.assertEqual(condition(job['if'], mode=MODE, **on_branch), name == 'rehearsal')
                for other in ('inputs.release_13', 'inputs.release_27', 'inputs.release_28', 'inputs.dry_run_28',
                              'inputs.checks_only', 'inputs.switch_from_run', 'inputs.probe_run'):
                    self.assertFalse(condition(job['if'], mode=MODE, **on_branch, **{other: True}) and name == 'rehearsal')
                self.assertFalse(condition(job['if'], mode=MODE, **on_branch, **{'inputs.check_build': 'build'})
                                 and name == 'rehearsal')
            for mode in OTHER_MODES:
                with self.subTest(job=name, other_mode=mode):
                    self.assertFalse(condition(job['if'], mode=mode, **on_branch) and name == 'rehearsal')

    def test_no_other_branch_can_run_the_mode(self):
        for branch in ('main', wb.BRANCH, local.BRANCH, 'pkg/27-first-update-release', 'pkg/14-owner-tools',
                       'pkg/16-staged-release', 'pkg/13-keyboard-layout'):
            for name, job in WORKFLOW['jobs'].items():
                with self.subTest(branch=branch, job=name):
                    self.assertFalse(condition(job['if'], mode=MODE, **{'github.ref_name': branch}))

    def test_22ds_mode_on_its_branch_is_unchanged(self):
        for name, job in WORKFLOW['jobs'].items():
            with self.subTest(job=name):
                self.assertEqual(condition(job['if'], mode='tools-local', **{'github.ref_name': local.BRANCH}), name == 'rehearsal')


class JobGatesTest(unittest.TestCase):
    def test_every_step_script_accepts_the_package_42_environment(self):
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

    def test_the_steps_scripts_arguments_and_bounds_are_package_42s(self):
        steps = list(job_steps())
        runs = {(script, tuple(argv[1:])) for step, environment in steps
                for script, argv, _ in base.step_runs(step, environment, inputs())}
        bound = str(LEDGER['job_bounds'][MODE])
        self.assertEqual(steps[0][1]['REHEARSAL_PACKAGE'], '42')
        for expected in (('os/ci/owner_capabilities.py', ()), ('os/ci/rehearsal_guard.py', ('probe-budget-ci', bound)),
                         ('os/ci/rehearsal_guard.py', ('ci', bound)), ('os/ci/registry_auth.py', ('create',)),
                         ('os/ci/registry_auth.py', ('preflight',)), ('os/ci/registry_auth.py', ('pull',)),
                         ('os/ci/registry_auth.py', ('cleanup',)), ('os/ci/owner_devices.py', ()),
                         ('os/ci/owner_counter_kernel.py', ()), ('os/ci/prepare_two_disks.py', ()), ('os/ci/owner_vm.py', (MODE,))):
            self.assertIn(expected, runs)
        self.assertFalse({script for script, _ in runs} & {'os/ci/keyboard_vm.py', 'os/ci/two_disk_vm.py', 'os/ci/rehearsal_auth.py'})
        world = inputs()
        self.assertEqual(base.workflow_text(JOB['timeout-minutes'], world), bound)
        vm, = [step for step, _ in steps if 'os/ci/owner_vm.py' in step['run']]
        vm_minutes = int(base.workflow_text(vm['timeout-minutes'], world))
        self.assertEqual(vm_minutes, 290)
        self.assertGreaterEqual(int(bound) - vm_minutes, 45 + 10)
        self.assertTrue(all('secrets.GHCR_READ_TOKEN' not in json.dumps(step) for step, _ in steps))


# Where package 42's VM step decides otherwise than package 22d's rehearsal, each with its reason.
REVIEWED = {
    ('os/ci/owner_vm.py', "authorization['allowance'] == package"): "the guard's dispatch authorization names the running package",
    ('os/ci/owner_vm.py', [key for key in local.REVIEWED if key[1].startswith("{'16'")][0][1]): "each package's own host walk",
    ('os/ci/owner_vm.py', "mode == 'tools-local'"): "22d's rehearsal records its bound sources and walks brief 22d's route",
    ('os/ci/owner_vm.py', "mode == 'release-28'"): "42's rehearsal records its bound sources and walks brief 42's route (B)",
}


class DecisionsTest(unittest.TestCase):
    def test_the_rehearsal_decides_like_package_22ds_except_where_reviewed(self):
        release_28 = dict(REHEARSAL_PACKAGE='42', REHEARSAL_MODE=MODE, GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH, argv=['os/ci/owner_vm.py', MODE])
        tools_local = dict(REHEARSAL_PACKAGE='22d', REHEARSAL_MODE='tools-local', GITHUB_REF_NAME=local.BRANCH,
                           argv=['os/ci/owner_vm.py', 'tools-local'])
        differing, used, paths = base.differing_decisions([release_28, tools_local], REVIEWED)
        self.assertEqual(differing, [])
        self.assertEqual(sorted(set(REVIEWED) - used), [], 'stale reviewed decisions')


class GuardTest(unittest.TestCase):
    def setUp(self):
        guard.configure('42')
        self.addCleanup(guard.configure, '11c')

    def test_the_vm_mode_proves_its_native_step_in_its_own_run_and_the_image_kinds_do_not(self):
        self.assertTrue(guard.own_native(MODE))
        for kind in ('dry-run-28', 'publish-28', 'resolve', 'checks'):
            self.assertFalse(guard.own_native(kind))
        self.assertEqual(guard.native_gate(MODE, 'probe-budget-ci', dict(runs=[]), 'a' * 40)['status'], 'pending')

    def test_the_guard_step_stops_at_cap_0_and_writes_package_42s_authorization_once_raised(self):
        run = dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='in_progress', conclusion=None,
                   created_at='2026-11-17T18:00:00Z', id=11, display_title=LEDGER['titles'][MODE], head_branch=BRANCH)
        environment = dict(REHEARSAL_PACKAGE='42', REHEARSAL_MODE=MODE, GITHUB_RUN_ID='11', GITHUB_SHA='a' * 40, GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH)
        proof = dict(complete=True, ids_count=1, total_count=1)
        api = lambda path: dict(workflow_runs=[run], history=proof) if path.startswith('actions/runs?') else run

        def main():
            with tempfile.TemporaryDirectory() as folder, contextlib.chdir(folder), patch.dict(os.environ, environment, clear=True), \
                    patch.object(sys, 'argv', ['rehearsal_guard.py', 'probe-budget-ci', '345']), patch('builtins.print'), \
                    patch.object(guard, 'api', side_effect=api), patch.object(model_scope, 'decide', return_value=('slice', ['unchanged'])):
                guard.main()
                return json.loads(pathlib.Path('evidence/42-dispatch-authorization.json').read_text())
        # Cap 0 (step 3) stopped it; cap 3 (step 6) lets it write the authorization.
        with patch.dict(LEDGER['dispatch_caps'], {MODE: 0}), \
                self.assertRaisesRegex(AssertionError, MODE + ' dispatch allowance exhausted'):
            main()
        written = main()
        self.assertEqual((written['allowance'], written['reserved_minutes'], written['native']['status']), ('42', 345, 'pending'))
        self.assertEqual(written['model'], dict(status='not-needed', scope='slice', reasons=['unchanged']))


class RunnerTest(unittest.TestCase):
    ENVIRONMENT = dict(GITHUB_ACTIONS='true', GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY=guard.REPOSITORY,
                       GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH, REHEARSAL_PACKAGE='42', REHEARSAL_MODE=MODE)

    def test_runner_and_registry_accept_only_package_42s_branch_package_and_mode(self):
        with patch.dict(os.environ, self.ENVIRONMENT, clear=True):
            owner_media.require_runner()
            registry_auth.require_dispatch()
        for key, value in (('GITHUB_REF_NAME', local.BRANCH), ('GITHUB_REF_NAME', 'main'), ('REHEARSAL_PACKAGE', '22d'),
                           ('REHEARSAL_MODE', 'tools-local'), ('REHEARSAL_MODE', 'update'), ('REHEARSAL_MODE', 'checks'),
                           ('GITHUB_REPOSITORY', 'elsewhere/AresOS')):
            with self.subTest(key=key, value=value), patch.dict(os.environ, dict(self.ENVIRONMENT, **{key: value}), clear=True):
                with self.assertRaises(AssertionError):
                    owner_media.require_runner()
        # The image kinds read release 27 with the job token, but never reach the owner route's media.
        for kind in ('dry-run-28', 'publish-28'):
            with patch.dict(os.environ, dict(self.ENVIRONMENT, REHEARSAL_MODE=kind), clear=True):
                registry_auth.require_dispatch()
                with self.assertRaises(AssertionError):
                    owner_media.require_runner()

    def test_the_driver_keeps_the_route_to_its_package(self):
        main = wb.RunnerTest.main.__get__(wb.RunnerTest())
        for package, mode, branch, message in (
                ('22d', MODE, local.BRANCH, 'the tools-local rehearsal is package 22d only'),
                ('42', 'tools-local', BRANCH, 'the tools-local rehearsal is package 22d only'),
                ('42', 'update', BRANCH, 'the update rehearsal is package 27 only'),
                ('42', 'owner-tools', BRANCH, 'the release-28 rehearsal is package 42 only')):
            with self.subTest(package=package, mode=mode):
                with self.assertRaisesRegex(AssertionError, message):
                    main(package, mode, branch, any_runner=True)


class VerifyReleaseTest(local.VerifyReleaseTest):
    """Release 27's trees at its source commit in this mode too (the VM starts on release 27; this branch's image
    sources are release 28's)."""
    MODE_ENVIRONMENT = dict(GITHUB_REF_NAME=BRANCH, GITHUB_REF='refs/heads/' + BRANCH, REHEARSAL_PACKAGE='42', REHEARSAL_MODE=MODE)

    def verify(self, environment=MODE_ENVIRONMENT, **kwargs):
        return base.run_verify_release(self, environment=environment, **kwargs)

    def test_other_branches_packages_and_modes_still_compare_head(self):
        for environment in (dict(self.MODE_ENVIRONMENT, REHEARSAL_MODE='dry-run-28'), dict(self.MODE_ENVIRONMENT, REHEARSAL_PACKAGE='22d'),
                            dict(self.MODE_ENVIRONMENT, GITHUB_REF_NAME='main')):
            with self.subTest(**environment), self.assertRaisesRegex(AssertionError, 'Release 27 runtime payload changed'):
                self.verify(environment, head=self.MOVED)


class AnnouncedTest(unittest.TestCase):
    """Lead's decision 1: version 4's code with tools_version 5 and release 28's record, so a new fingerprint."""

    def setUp(self):
        self.record = record()
        self.made = walk.announced(self.record, ROOT)

    def payload(self):
        """The announced payload folder: 634e1237's payload with the generated files in place."""
        folder = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        names = subprocess.check_output(['git', '-C', str(ROOT), 'ls-tree', '-r', '--name-only', walk.V4_COMMIT, 'os/owner-tools/payload'],
                                        text=True).split()
        for name in names:
            target = folder / name.removeprefix('os/owner-tools/payload/')
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(self.made['files'].get(name) or subprocess.check_output(['git', '-C', str(ROOT), 'show', walk.V4_COMMIT + ':' + name]))
        return folder

    def test_only_the_history_record_and_the_generated_files_change(self):
        files = self.made['files']
        history = json.loads(files['os/owner-tools/history.json'])
        v4 = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', walk.V4_COMMIT + ':os/owner-tools/history.json']))
        self.assertEqual(history, dict(tools_version=5, releases=[*v4['releases'], dict(
            reference='ghcr.io/ares-empire/aresos@sha256:' + '28' * 32, identity=walk.IDENTITY, daily_wheel=True)]))
        self.assertEqual(files['os/owner-tools/payload/history.json'], files['os/owner-tools/history.json'])
        self.assertEqual(files['os/owner-tools/payload/release.json'], self.record)
        self.assertEqual(files['os/manifest/release.json'], self.record)
        self.assertEqual(self.made['version'], 5)
        self.assertNotEqual(self.made['fingerprint'], walk.TOOLS_V4)

    def test_the_manifests_are_bundle_pys_and_the_tools_accept_the_lineage(self):
        folder = self.payload()
        rows = json.loads((folder / 'SHA256.json').read_text())
        for row in rows:
            self.assertEqual(hashlib.sha256((folder / row['path']).read_bytes()).hexdigest(), row['sha256'])
        sums = (folder / 'SHA256SUMS').read_bytes()
        self.assertEqual(hashlib.sha256(sums).hexdigest(), self.made['fingerprint'])
        self.assertTrue(sums.endswith((hashlib.sha256((folder / 'SHA256.json').read_bytes()).hexdigest() + '  SHA256.json\n').encode()))
        # The manifests bundle.py writes over the same files, with this record as release.json.
        bundle = owner_media.bundle_module('bundle')
        root = pathlib.Path(self.enterContext(tempfile.TemporaryDirectory()))
        for name, source in bundle.PAYLOAD.items():
            (root / source).parent.mkdir(parents=True, exist_ok=True)
            (root / source).write_bytes((folder / name).read_bytes())
        self.assertEqual(bundle.manifests(root), ((folder / 'SHA256.json').read_bytes(), sums))
        owner = owner_media.bundle_module('owner')
        lineage = owner.lineage(folder)
        self.assertEqual((lineage['tools_version'], lineage['releases'][-1]['reference']), (5, json.loads(self.record)['reference']))

    def test_the_lines_and_the_guide_name_the_new_tools(self):
        bootstrap = owner_media.bundle_module('bootstrap')
        commands = json.loads(self.made['files']['os/owner-tools/commands.json'])
        fingerprint = self.made['fingerprint']
        self.assertEqual(commands['install'], bootstrap.command(fingerprint))
        for name, line in bootstrap.lines(fingerprint).items():
            self.assertEqual(commands[name], line)
        checkout = json.loads((ROOT / 'os/owner-tools/commands.json').read_text())
        self.assertEqual({k: v for k, v in commands.items() if k not in ('install', *bootstrap.lines(fingerprint))},
                         {k: v for k, v in checkout.items() if k not in ('install', *bootstrap.lines(fingerprint))})
        guide = self.made['files'][walk.GUIDE].decode().split('\n')
        self.assertEqual((guide[0], guide[2]), ('Owner tools version 5: ' + fingerprint[:8], fingerprint))

    def test_a_record_that_is_not_release_28s_stops(self):
        r27 = 'https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/27-first-update-release'
        for value, message in ((record(identity=r27), 'signature identity'),
                               (record(daily_wheel=False), 'daily wheel'), (record(digest='zz'), 'org image digest'),
                               (record()[:-1], 'not a written record')):
            with self.subTest(message=message), self.assertRaisesRegex(AssertionError, message):
                walk.announced(value, ROOT)
        v4 = json.loads(subprocess.check_output(['git', '-C', str(ROOT), 'show', walk.V4_COMMIT + ':os/owner-tools/history.json']))
        known = v4['releases'][-1]['reference'].split('@sha256:')[1]
        with self.assertRaisesRegex(AssertionError, 'version 4 already knows release 28'):
            walk.announced(record(digest=known), ROOT)


class StandInOriginTest(unittest.TestCase):
    """Lead's decision 2: the stand-in for 634e1237, then the stand-in announced commit; the hashes are recorded."""

    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.record = record()
        cls.standin = walk.standin_origin(pathlib.Path(cls.folder.name) / 'origin', cls.record, ROOT)

    @classmethod
    def tearDownClass(cls):
        cls.folder.cleanup()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.standin['repository']), *args], text=True).strip()

    def test_main_holds_634e1237s_trees_then_the_announced_commit(self):
        commits = self.standin['commits']
        self.assertEqual(self.git('rev-list', 'main'), commits['announced'] + '\n' + commits['v4'])
        self.assertEqual(self.git('rev-parse', 'version-4'), commits['v4'])
        for path in (*walk.BOUND, walk.GUIDE):
            real = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', walk.V4_COMMIT + ':' + path], text=True).strip()
            self.assertEqual(self.git('rev-parse', commits['v4'] + ':' + path), real)
            self.assertEqual(self.standin['hashes']['v4'][path], real)
        self.assertEqual(self.standin['trees']['v4'], walk.V4_TREE)
        self.assertEqual(self.git('ls-tree', '--name-only', commits['v4']), 'docs\nos')

    def test_the_announced_commit_differs_from_634e1237_in_the_generated_files_only(self):
        changed = self.git('diff', '--name-only', self.standin['commits']['v4'], self.standin['commits']['announced']).split()
        self.assertEqual(sorted(changed), sorted(walk.announced(self.record, ROOT)['files']))
        self.assertEqual(hashlib.sha256(subprocess.check_output(['git', '-C', str(self.standin['repository']), 'show',
                         self.standin['commits']['announced'] + ':os/owner-tools/payload/SHA256SUMS'])).hexdigest(), self.standin['fingerprint'])
        # Modes are kept: the tools' entry stays executable.
        self.assertEqual(self.git('ls-tree', self.standin['commits']['announced'], 'os/owner-tools/at').split()[0],
                         self.git('ls-tree', self.standin['commits']['v4'], 'os/owner-tools/at').split()[0])

    def test_a_real_commit_matches_only_with_the_same_tree_and_release_blob(self):
        bound = dict(bound=self.standin['hashes']['announced'], fingerprint=self.standin['fingerprint'], version=5)
        self.assertEqual(walk.matches(self.standin['commits']['announced'], bound, self.standin['repository']), [])
        self.assertEqual(walk.matches(self.standin['commits']['v4'], bound, self.standin['repository']), [*walk.BOUND, walk.GUIDE])
        self.assertEqual(walk.matches(walk.V4_COMMIT, bound, ROOT), [*walk.BOUND, walk.GUIDE])

    def test_only_verified_v4_may_defer_and_never_qualifies(self):
        head = walk.V4_COMMIT
        self.assertEqual(walk.real_commit(head, self.standin, ROOT, allow_deferred=True),
                         dict(carries_release_28=False, head=head, equal=False, deferred=True))
        with self.assertRaisesRegex(AssertionError, 'requires a successful real-commit comparison'):
            walk.real_commit(head, self.standin, ROOT)
        # The stand-in announced commit as "this checkout": it carries release 28 and equals itself.
        announced = self.standin['commits']['announced']
        self.assertEqual(walk.real_commit(announced, self.standin, self.standin['repository']),
                         dict(carries_release_28=True, head=announced, equal=True))
        # A commit naming release 28 with other tools stops.
        other = dict(self.standin, hashes=dict(self.standin['hashes'], announced=dict(self.standin['hashes']['announced'],
                     **{'os/owner-tools': walk.V4_TREE})))
        with self.assertRaisesRegex(AssertionError, 'differs from the rehearsed bundle in os/owner-tools'):
            walk.real_commit(announced, other, self.standin['repository'])

    def commit_with(self, files, base='announced'):
        repo = self.standin['repository']
        root, _ = walk.tree_with(repo, self.git('rev-parse', self.standin['commits'][base] + '^{tree}'), files)
        return walk.git('commit-tree', root, '-m', 'test candidate', source=repo,
                        env=walk.tools_local.STANDIN_ENV).decode().strip()

    def test_a_new_bundle_with_another_newest_reference_must_not_defer(self):
        path = 'os/owner-tools/history.json'
        history = json.loads(walk.announced(self.record, ROOT)['files'][path])
        history['releases'][-1]['reference'] = 'ghcr.io/ares-empire/aresos@sha256:' + '99'*32
        candidate = self.commit_with({path: (json.dumps(history, indent=2)+'\n').encode()})
        for deferred in (False, True):
            with self.subTest(deferred=deferred), self.assertRaisesRegex(AssertionError, 'differs from the rehearsed bundle'):
                walk.real_commit(candidate, self.standin, self.standin['repository'], allow_deferred=deferred)

    def test_changed_v4_tools_or_release_are_not_an_unchanged_baseline(self):
        for path in walk.BOUND:
            file = path + '/owner.py' if path == 'os/owner-tools' else path
            candidate = self.commit_with({file: b'changed\n'}, base='v4')
            with self.subTest(path=path), self.assertRaisesRegex(AssertionError, 'differs from the rehearsed bundle'):
                walk.real_commit(candidate, self.standin, self.standin['repository'], allow_deferred=True)

    def test_real_guide_binds_line_one_and_full_fingerprint_but_allows_other_text(self):
        original = walk.announced(self.record, ROOT)['files'][walk.GUIDE].decode().splitlines()
        for index in (0, 2):
            lines = list(original)
            lines[index] = walk.guide_line(walk.TOOLS_V4, 4) if index == 0 else walk.TOOLS_V4
            candidate = self.commit_with({walk.GUIDE: ('\n'.join(lines)+'\n').encode()})
            with self.subTest(line=index+1), self.assertRaisesRegex(AssertionError, 'docs/OWNER-TOOLS.md'):
                walk.real_commit(candidate, self.standin, self.standin['repository'])
        candidate = self.commit_with({walk.GUIDE: ('\n'.join(original)+'\nUpdated explanatory prose.\n').encode()})
        self.assertTrue(walk.real_commit(candidate, self.standin, self.standin['repository'])['equal'])

    def test_vm_route_cannot_accept_the_uncut_baseline(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        vm = SimpleNamespace(td=SimpleNamespace(WORK=pathlib.Path(self.folder.name)), Console=Mock(), laptop_update=Mock())
        with patch.dict(os.environ, GITHUB_SHA=walk.V4_COMMIT), \
                patch.object(walk, 'facts_27', return_value=json.loads(self.record)), \
                patch.object(walk, 'standin_origin', return_value=self.standin), \
                self.assertRaisesRegex(AssertionError, 'requires a successful real-commit comparison'):
            walk.rehearsal(vm, None, None, None, None, None, None, self.record)
        vm.laptop_update.assert_not_called()

    def test_control_qualification_reaches_the_route_after_real_commit_comparison(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        vm = SimpleNamespace(td=SimpleNamespace(WORK=pathlib.Path(self.folder.name)), Console=Mock(),
                             laptop_update=Mock(side_effect=RuntimeError('route started')), TOOLS_V2='fixture')
        with patch.dict(os.environ, GITHUB_SHA=walk.V4_COMMIT), \
                patch.object(walk, 'facts_27', return_value=json.loads(self.record)), \
                patch.object(walk, 'standin_origin', return_value=self.standin), \
                patch.object(walk, 'real_commit', return_value=dict(equal=True)), \
                patch.object(walk, 'CONTROL_RIDES', True), \
                self.assertRaisesRegex(RuntimeError, 'route started'):
            walk.rehearsal(vm, None, None, None, None, None, None, self.record)
        vm.laptop_update.assert_called_once()


class ReceiptTest(unittest.TestCase):
    def test_generator_records_the_production_setting_and_passes_it_to_the_walk(self):
        import runpy, test_owner_walk
        namespace = runpy.run_path(str(ROOT / 'reviews/42-release-28/walk-host.py'))
        self.assertIn('os/config/usr/libexec/aresos-desktop', namespace['ADDED'])
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            previous = root / 'os/manifest/ci/22d/host-walk.json'
            previous.parent.mkdir(parents=True)
            previous.write_text('{"sources":[]}')
            namespace['main'].__globals__.update(ROOT=root, ADDED=set())
            observed = dict(stages=[], checks=[], markers=[], commands=[], typed=[])
            for control in (False, True):
                with self.subTest(control=control), patch.object(walk, 'CONTROL_RIDES', control), \
                        patch.object(test_owner_walk, 'walk', return_value=observed) as local_walk, \
                        contextlib.redirect_stdout(io.StringIO()):
                    namespace['main']()
                    local_walk.assert_called_once_with(route=MODE, control=control)
                    receipt = json.loads((root / 'os/manifest/ci/42/host-walk.json').read_text())
                    self.assertIs(receipt['control_rides'], control)
                    walk.receipt_setting(receipt)
                    with self.assertRaisesRegex(AssertionError, 'Control setting differs'):
                        walk.receipt_setting(dict(receipt, control_rides=not control))
                    with self.assertRaisesRegex(AssertionError, 'Control setting differs'):
                        walk.receipt_setting({})

    def test_vm_driver_rejects_an_opposite_setting_before_guest_setup(self):
        import owner_vm, owner_capabilities
        sha = 'a' * 40
        files = {'evidence/42-dispatch-authorization.json': dict(allowance='42', native=dict(status='passed', sha=sha)),
                 'evidence/14-host-capabilities.json': dict(status='passed', sha=sha,
                       checks={key: True for key in owner_capabilities.CHECKS}),
                 'os/manifest/ci/42/host-walk.json': dict(status='passed', stick_across_reboot=False,
                       control_rides=True, sources=[dict(sha256=hashlib.sha256(b'fixture').hexdigest(), path='fixture')])}
        def read(path, *args, **kwargs):
            return json.dumps(files[str(path)])
        with patch.dict(os.environ, REHEARSAL_PACKAGE='42', GITHUB_SHA=sha), \
                patch.object(sys, 'argv', ['owner_vm.py', MODE]), patch.object(owner_media, 'require_runner'), \
                patch.object(pathlib.Path, 'read_text', read), patch.object(pathlib.Path, 'read_bytes', return_value=b'fixture'), \
                patch.object(walk, 'CONTROL_RIDES', False), patch.object(owner_vm.td, 'start_installed') as start, \
                self.assertRaisesRegex(AssertionError, 'Control setting differs'):
            owner_vm.main()
        start.assert_not_called()


class HomeProbeTest(unittest.TestCase):
    """Run the submitted home probe, including its daily-user reader, against the provisioner's layout."""

    def setUp(self):
        from test_owner_walk import Release28Session
        from types import SimpleNamespace
        from unittest.mock import Mock
        self.session = Release28Session(False)
        self.addCleanup(self.session.close)
        self.guest = SimpleNamespace(capture_json=self.session.capture)
        self.vm = SimpleNamespace(sw=SimpleNamespace(framed=lambda source: source), td=SimpleNamespace(save=Mock()))
        self.session.boot('release-28')
        self.before = walk.home(self.guest, 'release-28', self.vm, plant=True)

    def test_real_provisioner_links_are_required_at_their_actual_locations(self):
        self.assertEqual(self.session.links, walk.INSTANCE_LINKS)
        for name, target in self.session.links.items():
            self.assertEqual(self.before['entries'][name]['target'], target)
        self.assertNotIn('minecraft/libraries', self.before['entries'])
        # The invented nested libraries layout and a missing patches link must both STOP.
        for name in ('libraries', 'patches', 'minecraft/mods', 'minecraft/saves'):
            with self.subTest(link=name):
                p = self.session.Path(walk.INSTANCE + '/' + name)
                target = p.readlink()
                p.unlink()
                try:
                    with self.assertRaisesRegex(AssertionError, 'incorrect instance link'):
                        walk.home(self.guest, 'final-28', self.vm)
                finally:
                    p.symlink_to(target)

    def test_changed_link_text_stops_even_when_the_new_target_is_accessible(self):
        p = self.session.Path(walk.INSTANCE + '/libraries')
        p.unlink()
        p.symlink_to(self.session.Path(walk.INSTANCE_LINKS['patches']))
        with self.assertRaisesRegex(AssertionError, 'incorrect instance link'):
            walk.home(self.guest, 'final-28', self.vm)

    def test_rollback_preserves_link_text_and_worlds_without_r28_image_targets(self):
        self.session.boot('previous-27')
        targets = self.session.boots[-1]['targets']
        self.assertEqual(targets, {name: name == 'minecraft/saves' for name in self.session.links})
        back = walk.home(self.guest, 'previous-27', self.vm, image_targets=False)
        walk.home_unchanged(self.before, back)
        self.session.boot('final-28')
        self.assertTrue(all(self.session.boots[-1]['targets'].values()))
        again = walk.home(self.guest, 'final-28', self.vm)
        walk.home_unchanged(self.before, again, prism_started=True)

    def test_image_targets_are_required_again_after_forward(self):
        self.session.boot('previous-27')
        self.session.boot('final-28')
        for name in ('patches', 'libraries', 'minecraft/mods'):
            with self.subTest(link=name):
                target = self.session.Path(self.session.links[name])
                target.rmdir()
                try:
                    with self.assertRaisesRegex(AssertionError, 'inaccessible as ares'):
                        walk.home(self.guest, 'final-28', self.vm)
                finally:
                    target.mkdir()

    def test_saved_world_contains_owned_level_and_region_data_through_saves(self):
        for name, data in walk.WORLD_FILES.items():
            row = self.before['worlds'][walk.WORLD + '/' + name]
            self.assertEqual(row['sha256'], hashlib.sha256(bytes.fromhex(data)).hexdigest())
            self.assertEqual((row['uid'], row['gid']), (1001, 1001))
        self.assertEqual(self.before['accessible']['worlds'], self.before['worlds'])

    def test_world_deletion_corruption_and_denial_stop_on_either_boot(self):
        for stage in ('previous-27', 'final-28'):
            for name in walk.WORLD_FILES:
                for fault in ('delete', 'corrupt', 'deny', 'owner', 'mode'):
                    with self.subTest(stage=stage, file=name, fault=fault):
                        self.session.boot(stage)
                        p = self.session.Path(walk.INSTANCE_LINKS['minecraft/saves']) / walk.WORLD / name
                        data = p.read_bytes()
                        try:
                            if fault == 'delete': p.unlink()
                            if fault == 'corrupt': p.write_bytes(b'corrupt')
                            if fault == 'deny': self.session.modes[str(p)] = 0
                            if fault == 'owner': self.session.owners[str(p)] = (0, 0)
                            if fault == 'mode': self.session.modes[str(p)] = 0o600
                            with self.assertRaisesRegex(AssertionError, 'STOP:.*(saved-world|inaccessible as ares)'):
                                after = walk.home(self.guest, stage, self.vm, image_targets=stage != 'previous-27')
                                walk.home_unchanged(self.before, after, prism_started=stage == 'final-28')
                        finally:
                            p.write_bytes(data)
                            self.session.modes.pop(str(p), None)
                            self.session.owners.pop(str(p), None)


class WalkTest(unittest.TestCase):
    """The local walk (test_owner_walk's release-28 route) with Control off, as it stays, and on."""

    @classmethod
    def setUpClass(cls):
        import test_owner_walk
        cls.module = test_owner_walk
        cls.walked = {control: test_owner_walk.walk(route=MODE, control=control) for control in (False, True)}

    def test_only_control_part_a_rides(self):
        self.assertIs(walk.CONTROL_RIDES, True)
        self.assertIs(walk.CHROME_RIDES, False)

    def test_local_walk_uses_the_real_release_record_after_the_cut(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            releases = root / 'os/manifest/releases'
            releases.mkdir(parents=True)
            (releases / '27.json').write_bytes((ROOT / walk.R27_RECORD).read_bytes())
            actual = record(digest='ab'*32)
            with patch.object(self.module, 'ROOT', root):
                self.assertNotEqual(self.module.release28_record(), actual)
                (releases / '28.json').write_bytes(actual)
                self.assertEqual(self.module.release28_record(), actual)

    def test_every_stage_of_brief_b_passes(self):
        for control, walked in self.walked.items():
            with self.subTest(control=control):
                result = walked['result']
                self.assertEqual(walked['stages'], self.module.RELEASE28_STAGES)
                self.assertEqual([s['stage'] for s in result['stages']], ['r28-v4', 'r28-tools'])
                self.assertEqual((result['tools_version'], result['tools_version_4']), (5, walk.TOOLS_V4))
                self.assertEqual([row['line_1'][:22] for row in result['compared']], ['Owner tools version 4:', 'Owner tools version 5:'])
                self.assertEqual(result['no_foot']['stop'], walk.FOOT_STOP)
                self.assertEqual(result['game_scope']['memory_high'], '2684354560')
                self.assertTrue(result['home']['planted'])
                self.assertEqual(result['home']['worlds'], result['home']['after_forward_worlds'])
                self.assertFalse(result['qualified'])
                self.assertEqual(result['terminal_path'], self.module.vm.DAILY_PATH)
                names = [name for name, _ in walked['commands']]
                self.assertLess(names.index('release-28-terminal'), names.index('release-28-path-result'))
                self.assertLess(names.index('release-28-path-result'), names.index('release-28-polkit'))
                home_probe = next(source for name, source in walked['session'].executed if name == 'release-28-home')
                self.assertIn("'schemaVersion': 4", home_probe)
                self.assertEqual(walked['session'].events, ['foot ended', 'terminal opened', 'game scope'])
                boots = {row['stage']: row['targets'] for row in walked['session'].boots}
                for stage in ('release-27', 'previous-27'):
                    self.assertEqual(boots[stage], {name: name == 'minecraft/saves' for name in walk.INSTANCE_LINKS})
                for stage in ('release-28', 'final-28'):
                    self.assertTrue(all(boots[stage].values()))
                self.assertEqual(walked['local'].installs[-1], dict(manifest=result['tools'], previous_manifest=walk.TOOLS_V4,
                                                                    previous_version=4, tools_version=5))
                self.assertLessEqual({'final-unattended-windows', 'final-detached-windows'}, set(walked['markers']))

    def test_part_a_runs_the_bound_checker_on_both_r28_boots_without_browser_sites(self):
        off, on = self.walked[False]['result'], self.walked[True]['result']
        self.assertFalse(off['control_checked'])
        self.assertTrue(on['control_checked'])
        self.assertEqual(set(on['control']), {'release-28', 'final-28'})
        for walked in self.walked.values():
            self.assertIsNone(walked['result']['sites_sha256'])
            self.assertFalse([name for name, _ in walked['commands'] if name.endswith(('-sites', '-sites-hash'))])
        for row in on['control'].values():
            self.assertEqual(row['checker_sha256'], hashlib.sha256((ROOT / walk.CONTROL_CHECKER).read_bytes()).hexdigest())
            self.assertTrue(all(r['ok'] for r in row['checks'].values()))
        names = [name for name, _ in self.walked[True]['commands']]
        self.assertEqual([name for name in names if name.endswith('-control')], ['release-28-control', 'final-28-control'])

    def test_each_announced_commit_records_its_bound_hashes(self):
        rows = self.walked[False]['result']['announced']
        real = self.walked[False]['result']['real_commit']
        self.assertEqual([row['real'] for row in rows], [walk.V4_COMMIT, real['head'] if real['equal'] else None])
        self.assertEqual(rows[0]['bound']['os/owner-tools'], walk.V4_TREE)
        self.assertEqual(set(rows[1]['bound']), set(walk.BOUND))


if __name__ == '__main__':
    unittest.main()
