import contextlib
import hashlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import call, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import rehearsal_guard as guard


def failure(code):
    return subprocess.CalledProcessError(1, ['gh', 'api'], stderr=f'gh: Server Error (HTTP {code})\n'.encode())


class ReadRetryTest(unittest.TestCase):
    def setUp(self):
        guard.READ_RETRIES.clear()

    def test_observed_gh_http_and_connection_formats(self):
        self.assertEqual(guard.failure_status(b'gh: Not Found (HTTP 404)\n'), 404)
        self.assertEqual(guard.failure_status(b'gh: Server Error (HTTP 502)\n'), 502)
        self.assertEqual(guard.failure_status(b'gh: HTTP 503\n'), 503)
        observed = b'Get "https://api.github.com/repos/Ares-Empire/AresOS": proxyconnect tcp: dial tcp 127.0.0.1:1: connectex: No connection could be made because the target machine actively refused it.\n'
        self.assertEqual(guard.failure_status(observed), 'connection')
        for text in (b'invalid character in JSON', b'authentication required',
                     b'Get "https://api.github.com/": tls: failed to verify certificate: x509 error'):
            self.assertIsNone(guard.failure_status(text))

    def test_502_then_success_has_exact_clean_ledger_minutes_and_full_count(self):
        runs = [dict(id=n, display_title='Two-disk rehearsal (full)', head_sha='a' * 40,
                     created_at=guard.START, status='completed', conclusion='success') for n in (1, 2)]
        jobs = dict(jobs=[dict(conclusion='success', started_at=guard.START,
                              completed_at='2026-10-23T16:22:01Z',
                              steps=[dict(name='Run fixture task',started_at=guard.START,completed_at='2026-10-23T16:22:01Z')]), dict(conclusion='skipped')])
        responses = [json.dumps(dict(total_count=len(runs), workflow_runs=runs)).encode(), json.dumps(jobs).encode(), json.dumps(jobs).encode()]
        with patch.object(guard.subprocess, 'check_output', side_effect=responses), patch.object(guard.time, 'sleep') as sleep, \
             contextlib.redirect_stderr(io.StringIO()):
            clean = guard.budget(182)
            sleep.assert_not_called()
        log = io.StringIO()
        with patch.object(guard.subprocess, 'check_output', side_effect=[responses[0], failure(502), *responses[1:]]) as get, \
             patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stderr(log):
            retried = guard.budget(182)
        self.assertEqual(retried, clean)
        self.assertEqual((retried['consumed_minutes'], retried['full_dispatched']), (4, 2))
        self.assertTrue(all(c.args[0][2:4] == ['--method', 'GET'] for c in get.call_args_list))
        sleep.assert_called_once_with(10)
        self.assertIn('"status": 502', log.getvalue())
        self.assertIn('actions/runs/1/jobs?per_page=100', log.getvalue())
        self.assertEqual(guard.READ_RETRIES[0]['attempt'], 1)

    def test_five_502s_fail_closed_without_authorization(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            original = pathlib.Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(guard.subprocess, 'check_output', side_effect=[failure(502) for _ in range(5)]) as get, \
                     patch.object(guard.time, 'sleep') as sleep, patch.object(sys, 'argv', ['guard', 'probe', '42']), \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
                    guard.main()
                self.assertEqual(get.call_count, 5)
                self.assertEqual(sleep.call_args_list, [call(10), call(20), call(40), call(60)])
                self.assertFalse(pathlib.Path('.work/11c/11c-dispatch-authorization.json').exists())
            finally:
                os.chdir(original)

    def test_4xx_auth_cli_and_parse_failures_never_retry(self):
        errors = [failure(n) for n in (400, 401, 403, 404, 429)] + [
            subprocess.CalledProcessError(4, ['gh', 'api'], stderr=b'authentication required'),
            subprocess.CalledProcessError(1, ['gh', 'api'], stderr=b'invalid character in JSON response'),
            subprocess.CalledProcessError(1, ['gh', 'api'], stderr=b'unknown failure')]
        for error in errors:
            with self.subTest(stderr=error.stderr), patch.object(guard.subprocess, 'check_output', side_effect=error) as get, \
                 patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stderr(io.StringIO()), \
                 self.assertRaises(subprocess.CalledProcessError):
                guard.api('actions/runs')
            self.assertEqual(get.call_count, 1)
            sleep.assert_not_called()
        with patch.object(guard.subprocess, 'check_output', return_value=b'not JSON') as get, \
             patch.object(guard.time, 'sleep') as sleep, self.assertRaises(json.JSONDecodeError):
            guard.api('actions/runs')
        self.assertEqual(get.call_count, 1)
        sleep.assert_not_called()

    def test_connection_failure_retries_but_missing_gh_does_not(self):
        error = subprocess.CalledProcessError(1, ['gh', 'api'], stderr=b'Get "https://api.github.com/": dial tcp: lookup api.github.com: no such host')
        with patch.object(guard.subprocess, 'check_output', side_effect=[error, b'{}']), \
             patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(guard.api('actions/runs'), {})
        sleep.assert_called_once_with(10)
        self.assertEqual(guard.READ_RETRIES[0]['status'], 'connection')
        with patch.object(guard.subprocess, 'check_output', side_effect=FileNotFoundError('gh')), \
             patch.object(guard.time, 'sleep') as sleep, self.assertRaises(FileNotFoundError):
            guard.api('actions/runs')
        sleep.assert_not_called()

    def artifact_main(self, failures):
        raw = (ROOT / 'reviews/11-two-disk-rehearsal/artifacts/11j-probe-1-two-disk-evidence.zip').read_bytes()
        metadata = json.loads((ROOT / 'os/manifest/ci/11j/probe-1/run.json').read_text())
        responses = [json.dumps(metadata).encode(), json.dumps(dict(artifacts=[dict(
            id=123, name='two-disk-evidence', expired=False, digest='sha256:' + hashlib.sha256(raw).hexdigest())])).encode(),
            *[failure(502) for _ in range(failures)], raw]
        environment = dict(REHEARSAL_MODE='part-b', PROBE_RUN=str(metadata['id']), GITHUB_SHA=metadata['head_sha'])
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            original = pathlib.Path.cwd()
            try:
                os.chdir(directory)
                with patch.dict(os.environ, environment), patch.object(sys, 'argv', ['guard', 'ci', '182']), \
                     patch.object(guard, 'budget', return_value=dict(consumed_minutes=464, full_dispatched=5, part_b_dispatched=1,
                         history=dict(complete=True, ids_count=5, total_count=5))), \
                     patch.object(guard.subprocess, 'check_output', side_effect=responses) as get, \
                     patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stdout(io.StringIO()), \
                     contextlib.redirect_stderr(io.StringIO()):
                    if failures == 5:
                        with self.assertRaises(subprocess.CalledProcessError):
                            guard.main()
                        self.assertFalse(pathlib.Path('evidence/11c-dispatch-authorization.json').exists())
                    else:
                        guard.main()
                        result = json.loads(pathlib.Path('evidence/11c-dispatch-authorization.json').read_text())
                        self.assertEqual((result['consumed_minutes'], result['full_dispatched']), (464, 5))
                        self.assertEqual(result['probe']['commit'], metadata['head_sha'])
                        self.assertEqual(len(result['read_retries']), 1)
                self.assertEqual(get.call_count, 2 + min(failures + 1, 5))
                self.assertEqual(sleep.call_args_list, [call(n) for n in guard.RETRY_WAITS[:min(failures, 4)]])
            finally:
                os.chdir(original)

    def test_artifact_zip_502_then_success_preserves_digest_and_full_gate(self):
        self.artifact_main(1)

    def test_artifact_zip_five_502s_never_authorize(self):
        self.artifact_main(5)


if __name__ == '__main__':
    unittest.main()
