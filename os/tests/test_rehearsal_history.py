import contextlib
import copy
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


def response(total, runs):
    return json.dumps(dict(total_count=total, workflow_runs=runs)).encode()


def failure(code):
    return subprocess.CalledProcessError(1, ['gh', 'api'], stderr=f'gh: Server Error (HTTP {code})\n'.encode())


class HistoryTest(unittest.TestCase):
    def setUp(self):
        guard.READ_RETRIES.clear()
        self.runs = [dict(id=i, display_title='Two-disk rehearsal (full)' if i <= 5 else 'privacy-check',
                         head_sha='a' * 40, status='completed', conclusion='success',
                         created_at='2026-10-23T17:00:00Z' if i <= 100 else
                         '2026-10-23T16:21:24Z' if i == 101 else '2026-10-22T23:00:00Z') for i in range(1, 124)]
        self.runs[99]['created_at'] = '2026-10-23T16:43:29Z'
        self.first = response(123, self.runs[:100])
        self.second = response(123, self.runs[100:])

    def test_two_pages_are_exact_union_with_total_count_and_no_filter_changes(self):
        with patch.object(guard.subprocess, 'check_output', side_effect=[self.first, self.second]) as get, \
             contextlib.redirect_stderr(io.StringIO()):
            listing = guard.api(guard.RUN_HISTORY_PATH)
        self.assertEqual(listing['workflow_runs'], self.runs)
        proof = listing['history']
        self.assertEqual((proof['pages_read'], proof['ids_count'], proof['total_count']), (2, 123, 123))
        self.assertEqual(proof['run_ids'], list(range(1, 124)))
        self.assertEqual([p['returned'] for p in proof['pages']], [100, 23])
        self.assertEqual([c.args[0][-1] for c in get.call_args_list],
            [f'repos/{guard.REPOSITORY}/{guard.RUN_HISTORY_PATH}&page={p}' for p in (1, 2)])

    def test_real_11l_boundary_now_counts_the_allowance_run_only_on_page_two(self):
        requested = []
        job = dict(conclusion='success', started_at=guard.START, completed_at='2026-10-23T16:22:00Z',
                   steps=[dict(name='Run fixture task',started_at=guard.START,completed_at='2026-10-23T16:22:00Z')])
        def get(command, **kwargs):
            path = command[-1]; requested.append(path)
            if path.endswith('&page=1'): return self.first
            if path.endswith('&page=2'): return self.second
            return json.dumps(dict(jobs=[job])).encode()
        with patch.object(guard.subprocess, 'check_output', side_effect=get), contextlib.redirect_stderr(io.StringIO()):
            ledger = guard.budget(186)
        self.assertGreater(self.runs[99]['created_at'], guard.START)
        self.assertEqual([r['run'] for r in ledger['runs']], list(range(1, 102)))
        self.assertEqual((ledger['consumed_minutes'], ledger['full_dispatched'], ledger['part_b_dispatched']), (101, 5, 0))
        self.assertIn('/actions/runs/101/jobs?per_page=100', requested[-1])
        self.assertEqual(len(requested), 2 + 101)

    def refuses_without_authorization(self, responses, message, limit=None):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            previous = pathlib.Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(sys, 'argv', ['guard', 'probe', '186']), \
                     patch.object(guard.subprocess, 'check_output', side_effect=responses) as get, \
                     patch.object(guard.time, 'sleep') as sleep, \
                     patch.object(guard, 'HISTORY_PAGE_LIMIT', limit or 20), \
                     contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()), \
                     self.assertRaisesRegex(AssertionError, message):
                    guard.main()
                self.assertFalse(pathlib.Path('.work/11c/11c-dispatch-authorization.json').exists())
                sleep.assert_not_called()
                return get.call_count
            finally:
                os.chdir(previous)

    def test_count_shift_duplicate_missing_and_empty_page_fail_with_no_authorization(self):
        cases = [
            (response(124, self.runs[100:]), 'inconsistent history total_count'),
            (response(123, [self.runs[99], *self.runs[100:122]]), 'duplicate history run id'),
            (response(123, self.runs[100:122]), 'missing or excess history ids'),
            (response(123, []), 'empty history page'),
        ]
        for second, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(self.refuses_without_authorization([self.first, second], reason), 2)

    def test_missing_id_and_malformed_count_never_authorize(self):
        runs = copy.deepcopy(self.runs[100:]); del runs[-1]['id']
        self.refuses_without_authorization([self.first, response(123, runs)], 'missing or malformed history run id')
        for count in (None, True, -1, '123'):
            with self.subTest(count=count):
                self.refuses_without_authorization([response(count, self.runs[:100])], 'malformed history total_count')

    def test_page_two_502_recovers_through_unchanged_bounded_retry(self):
        with patch.object(guard.subprocess, 'check_output', side_effect=[self.first, failure(502), self.second]) as get, \
             patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stderr(io.StringIO()):
            listing = guard.api(guard.RUN_HISTORY_PATH)
        self.assertEqual(listing['workflow_runs'], self.runs)
        self.assertEqual(get.call_count, 3)
        sleep.assert_called_once_with(10)
        self.assertEqual(guard.READ_RETRIES[0]['attempt'], 1)
        self.assertTrue(guard.READ_RETRIES[0]['path'].endswith('&page=2'))

    def page_error(self, code, attempts):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            previous = pathlib.Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(sys, 'argv', ['guard', 'probe', '186']), \
                     patch.object(guard.subprocess, 'check_output', side_effect=[self.first, *[failure(code) for _ in range(attempts)]]) as get, \
                     patch.object(guard.time, 'sleep') as sleep, contextlib.redirect_stderr(io.StringIO()), \
                     self.assertRaises(subprocess.CalledProcessError):
                    guard.main()
                self.assertFalse(pathlib.Path('.work/11c/11c-dispatch-authorization.json').exists())
                self.assertEqual(get.call_count, 1 + attempts)
                self.assertEqual(sleep.call_args_list, [call(n) for n in guard.RETRY_WAITS[:attempts - 1]])
            finally:
                os.chdir(previous)

    def test_page_two_five_502s_fail_closed(self):
        self.page_error(502, 5)

    def test_page_two_404_fails_immediately(self):
        self.page_error(404, 1)

    def test_hard_page_limit_fails_closed(self):
        self.assertEqual(self.refuses_without_authorization([self.first], 'history page limit', limit=1), 1)

    def test_empty_complete_history_is_distinct_from_an_empty_intermediate_page(self):
        with patch.object(guard.subprocess, 'check_output', return_value=response(0, [])), \
             contextlib.redirect_stderr(io.StringIO()):
            proof = guard.api(guard.RUN_HISTORY_PATH)['history']
        self.assertEqual((proof['pages_read'], proof['ids_count'], proof['total_count']), (1, 0, 0))


if __name__ == '__main__':
    unittest.main()
