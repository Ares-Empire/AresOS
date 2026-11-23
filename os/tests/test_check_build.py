"""The Deskflow shell modes stop before running host tools outside hosted CI."""
import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]


class CheckBuildTest(unittest.TestCase):
    def test_deskflow_modes_require_all_hosted_job_markers(self):
        hosted = dict(GITHUB_ACTIONS='true', RUNNER_ENVIRONMENT='github-hosted', GITHUB_JOB='check-build')
        for mode in ('deskflow', 'deskflow-pass'):
            for env in ({}, dict(hosted, GITHUB_ACTIONS='false'), dict(hosted, RUNNER_ENVIRONMENT='self-hosted'),
                        dict(hosted, GITHUB_JOB='image')):
                with self.subTest(mode=mode, env=env):
                    result = subprocess.run(
                        ['/usr/bin/bash', ROOT / 'os/ci/check-build.sh', mode], cwd=ROOT,
                        capture_output=True, text=True, env=dict(env, PATH='/nonexistent'), timeout=5,
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, '')
                    self.assertEqual(result.stderr, 'Deskflow requires the hosted check-build job\n')
