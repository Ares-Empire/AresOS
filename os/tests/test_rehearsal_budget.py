import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import rehearsal_guard as guard


class BudgetTest(unittest.TestCase):
    def test_allowance_includes_privacy_push_and_pr_jobs_and_excludes_old_runs(self):
        def run(number, title, date=guard.START, status='completed'):
            return dict(id=number, display_title=title, head_sha='a' * 40, conclusion='success',
                        created_at=date, status=status)
        runs = [run(1, 'privacy-check'), run(2, 'privacy-check'), run(3, 'Two-disk rehearsal (probe)'),
                run(4, 'Two-disk rehearsal (full)', '2026-10-22T23:00:00Z')]
        job = dict(conclusion='success', started_at='2026-10-23T16:21:00Z', completed_at='2026-10-23T16:22:01Z')
        def api(path):
            if path.startswith('actions/runs?'):
                self.assertNotIn('workflow_dispatch', path)
                return dict(workflow_runs=runs)
            return dict(jobs=[job, dict(conclusion='skipped')])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(324)
            self.assertEqual(result['consumed_minutes'], 6)
            self.assertEqual(result['full_dispatched'], 0)
            with self.assertRaisesRegex(AssertionError, 'exceeds 330'):
                guard.budget(325)
            runs[1]['status'] = 'in_progress'
            with self.assertRaisesRegex(AssertionError, 'active'):
                guard.budget(0)
