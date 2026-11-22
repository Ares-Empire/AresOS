import pathlib
import re
import subprocess
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci/bench'))
from script import validate_dispatch


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

    def test_workflow_routes_competing_jobs_away_from_bench(self):
        workflow = (ROOT / '.github/workflows/os-image.yml').read_text()
        conditions = dict(re.findall(r'^  ([a-z][a-z0-9-]*):\n(?:    [^\n]*\n)*?    if: ([^\n]+)', workflow, re.M))
        for job in ('image', 'release-27', 'release-28', 'release-28-dry-run'):
            self.assertIn("&& inputs.check_build == ''", conditions[job], job)
        for job in ('switch', 'rehearsal', 'regressions', 'model'):
            self.assertIn("&& inputs.check_build != 'bench' &&", conditions[job], job)
        self.assertIn("inputs.check_build == 'bench' ||", conditions['check-build'])
        self.assertLess(workflow.index('os/ci/bench/script.py'), workflow.index('Install pinned tools on disposable runner'))
        self.assertIn("steps.bench-evidence.outputs.safe == 'true'", workflow)
