import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import yaml

from test_release27 import UPDATE_INPUTS, workflow_expression

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
import dispatch as client
from script import BOOLEAN_CONFLICTS, LEDGER, STRING_CONFLICTS, LedgerRef, validate_dispatch

WORKFLOW = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
JOBS = WORKFLOW['jobs']
BRANCH = 'pkg/334a-bench-hosted'
BENCH_SCRIPT = 'reviews/334a-bench-hosted/bench/session-health.json'
WORLD = dict(UPDATE_INPUTS, **{'github.ref_name': BRANCH, 'inputs.rehearsal': '', 'inputs.full_model': False,
                             'inputs.check_build': 'bench', 'needs.image.result': 'skipped'})


def enabled(step, world, *, status='success'):
    condition = step.get('if', 'success()').strip()
    if condition.startswith('${{'):
        condition = condition[3:-2].strip()
    statuses = {'success()': status == 'success', 'failure()': status == 'failure',
                'cancelled()': status == 'cancelled', 'always()': True}
    # Actions adds an implicit success check only if the condition has no status function.
    if not any(call in condition for call in statuses):
        condition = f'success() && ({condition})'
    for call, value in statuses.items():
        condition = condition.replace(call, str(value))
    return bool(workflow_expression(condition, world))


class BenchDispatchTest(unittest.TestCase):
    def test_bench_refuses_every_competing_input(self):
        inputs = {'check_build': 'bench', 'release_13': 'false', 'switch_from_run': ''}
        validate_dispatch({'inputs': inputs}, 'bench')
        for key, value in [('release_13', 'true'), ('release_27', True), ('release_28', True), ('dry_run_28', True),
                           ('checks_only', True), ('full_model', 'true'), ('rehearsal', 'probe'),
                           ('probe_run', '123'), ('switch_from_run', 'false')]:
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, 'exclusive'):
                validate_dispatch({'inputs': dict(inputs, **{key: value})}, 'bench')

    def test_shell_refuses_non_hosted_calls_before_running_tools(self):
        for mode in ('bench', 'bench-pass'):
            result = subprocess.run(['/usr/bin/bash', ROOT / 'os/ci/check-build.sh', mode], cwd=ROOT,
                                    capture_output=True, env={'PATH': '/nonexistent', 'GITHUB_ACTIONS': 'true',
                                                              'GITHUB_JOB': 'check-build',
                                                              'RUNNER_ENVIRONMENT': 'self-hosted'})
            self.assertEqual(result.returncode, 2)
            self.assertEqual(result.stderr, b'Bench requires the hosted check-build job\n')

    def test_unusable_driver_setup_exits_two(self):
        result = subprocess.run([sys.executable, '-B', ROOT / 'os/ci/bench/driver.py'], cwd=ROOT,
                                capture_output=True, env={})
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stderr, b'Bench VM unusable during setup or cleanup\n')

    def test_workflow_routes_competing_jobs_away_from_bench(self):
        def jobs(**overrides):
            return {name for name, job in JOBS.items() if enabled(job, dict(WORLD, **overrides))}

        branches = {BRANCH: ['probe']}
        for package in json.loads(LEDGER.read_bytes()).values():
            modes = [mode for mode, title in package.get('titles', {}).items()
                     if title == f'Two-disk rehearsal ({mode})']
            branches[package['branch']] = modes or ['probe']
        conflicts = {name: True for name in BOOLEAN_CONFLICTS}
        conflicts.update(probe_run='123', switch_from_run='123')
        self.assertEqual(conflicts.keys() | {'rehearsal'}, set(BOOLEAN_CONFLICTS) | set(STRING_CONFLICTS))
        for branch, rehearsals in branches.items():
            with self.subTest(branch=branch):
                self.assertEqual(jobs(**{'github.ref_name': branch}), {'check-build'})
            for name, value in conflicts.items():
                with self.subTest(branch=branch, conflict=name):
                    self.assertEqual(jobs(**{'github.ref_name': branch, f'inputs.{name}': value}), set())
            for rehearsal in rehearsals:
                with self.subTest(branch=branch, rehearsal=rehearsal):
                    dispatch = {'github.ref_name': branch, 'inputs.rehearsal': rehearsal}
                    self.assertIn('rehearsal', jobs(**dispatch, **{'inputs.check_build': ''}))
                    self.assertEqual(jobs(**dispatch), set())
        # A prior successful image is another path into the switch job.
        self.assertEqual(jobs(**{'needs.image.result': 'success'}), {'check-build'})
        self.assertEqual(jobs(**{'github.event_name': 'push'}), set())

    def test_workflow_guard_runs_on_managed_refs_before_tools_or_budget(self):
        steps = JOBS['check-build']['steps']
        reserve, = (step for step in steps if 'rehearsal_guard.py' in step.get('run', ''))
        guard, = (step for step in steps if 'os/ci/bench/script.py' in step.get('run', ''))
        self.assertTrue(steps[0]['uses'].startswith('actions/checkout@'))
        self.assertEqual(steps.index(guard), 2)
        self.assertFalse(guard.get('continue-on-error'))
        self.assertFalse(enabled(guard, dict(WORLD, **{'inputs.check_build': 'resolve'})))
        managed = ['pkg/42-release-28', 'pkg/331-release-29']
        with tempfile.TemporaryDirectory(dir=ROOT) as folder:
            # R29 holds its ledger entry on its own branch before integration.
            checkout = pathlib.Path(folder)
            script = checkout / 'os/ci/bench/script.py'
            script.parent.mkdir(parents=True)
            script.write_bytes((ROOT / script.relative_to(checkout)).read_bytes())
            ledger = json.loads(LEDGER.read_bytes())
            ledger['331'] = {'branch': managed[-1]}
            (script.parents[1] / LEDGER.name).write_text(json.dumps(ledger))
            for ref in managed:
                with self.subTest(ref=ref):
                    world = dict(WORLD, **{'github.ref_name': ref})
                    self.assertTrue(enabled(guard, world))
                    self.assertFalse(enabled(reserve, world))
                    result = subprocess.run(re.split(r'\s+', guard['run'].splitlines()[0]), cwd=checkout,
                                            capture_output=True, text=True, env={
                                                'GITHUB_ACTIONS': 'true', 'RUNNER_ENVIRONMENT': 'github-hosted',
                                                'GITHUB_JOB': 'check-build', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                                                'GITHUB_REF_TYPE': 'branch', 'GITHUB_REF_NAME': ref,
                                            })
                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(result.stderr, 'Bench dispatch refused on a ledger-managed ref\n')

    def test_client_checks_target_ledger_before_submit(self):
        ref = 'pkg/331-release-29'
        ledger = json.dumps({'331': {'branch': ref}}).encode()
        with patch.object(client.subprocess, 'run') as run, patch.object(client, 'urlopen') as read:
            read.return_value.__enter__.return_value.read.return_value = ledger
            with self.assertRaisesRegex(LedgerRef, 'ledger-managed'):
                client.submit(ref, BENCH_SCRIPT)
            request = read.call_args.args[0]
            self.assertEqual(parse_qs(urlsplit(request.full_url).query), {'ref': [f'refs/heads/{ref}']})
            self.assertEqual(request.get_method(), 'GET')
            self.assertFalse(request.has_header('Authorization'))
            self.assertFalse(any(call.args[0][:3] == ['gh', 'workflow', 'run'] for call in run.call_args_list))
            client.submit(BRANCH, BENCH_SCRIPT)
            self.assertEqual(run.call_args.args[0], ['gh', 'workflow', 'run', 'os-image.yml', '--repo', client.REPO,
                                                    '--ref', BRANCH, '-f', 'check_build=bench',
                                                    '-f', f'bench_script={BENCH_SCRIPT}'])

    def test_only_scanned_bench_evidence_reaches_upload(self):
        steps = JOBS['check-build']['steps']
        scan, = (step for step in steps if step.get('id') == 'bench-evidence')
        upload, = (step for step in steps if step.get('with', {}).get('name') == 'bench-evidence')
        self.assertEqual(scan['run'], 'python3 -B os/ci/bench/evidence.py evidence/bench')
        self.assertTrue(upload['uses'].startswith('actions/upload-artifact@'))
        self.assertEqual(upload['with']['path'], 'evidence/bench/')
        self.assertLess(steps.index(scan), steps.index(upload))
        uploads = [step for step in steps if step.get('uses', '').startswith('actions/upload-artifact@')]
        for outcome in ('success', 'failure', 'skipped'):
            for safe in ('true', 'false', ''):
                for cancelled in (False, True):
                    with self.subTest(outcome=outcome, safe=safe, cancelled=cancelled):
                        world = dict(WORLD, **{'steps.bench-vm.outcome': outcome,
                                              'steps.bench-evidence.outputs.safe': safe})
                        status = 'cancelled' if cancelled else 'failure' if outcome == 'failure' else 'success'
                        self.assertEqual(enabled(scan, world, status=status),
                                         not cancelled and outcome != 'skipped')
                        active_uploads = [step for step in uploads if enabled(step, world, status=status)]
                        self.assertEqual(active_uploads, [upload] if not cancelled and safe == 'true' else [])
