import pathlib
import sys
import unittest
import yaml
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import rehearsal_guard as guard


class BudgetTest(unittest.TestCase):
    def test_full_time_reservation_covers_one_complete_job_without_changing_probe_limits(self):
        workflow = yaml.load((pathlib.Path(__file__).resolve().parents[2] /
                              '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        job = workflow['jobs']['rehearsal']
        self.assertEqual(job['timeout-minutes'], "${{ inputs.rehearsal == 'full' && 180 || 40 }}")
        vm, = [s for s in job['steps'] if 'two_disk_vm.py' in s.get('run', '')]
        self.assertEqual(vm['timeout-minutes'], "${{ inputs.rehearsal == 'full' && 156 || 80 }}")
        reserve, = [s for s in job['steps'] if 'rehearsal_guard.py' in s.get('run', '')]
        self.assertIn("'${{ inputs.rehearsal == 'full' && 182 || 42 }}'", reserve['run'])
        self.assertEqual(vm['run'].count('two_disk_vm.py'), 1)

    def test_full_dispatch_count_includes_current_run_and_rejects_fifth(self):
        runs = [dict(id=i, display_title='Two-disk rehearsal (full)', head_sha='a' * 40,
                     created_at=guard.START, status='completed', conclusion='success') for i in range(4)]
        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(jobs=[])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(182, current=3)
            self.assertEqual(result['full_dispatched'], 4)
            runs.append(dict(runs[0], id=4))
            with self.assertRaisesRegex(AssertionError, 'full-run allowance exhausted'):
                guard.budget(0, current=4)

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
            self.assertEqual((guard.START, guard.MINUTE_CAP, guard.FULL_CAP), ('2026-10-23T16:21:00Z', 750, 4))
            result = guard.budget(744)
            self.assertEqual(result['consumed_minutes'], 6)
            self.assertEqual(result['full_dispatched'], 0)
            with self.assertRaisesRegex(AssertionError, 'exceeds 750'):
                guard.budget(745)
            runs[1]['status'] = 'in_progress'
            with self.assertRaisesRegex(AssertionError, 'active'):
                guard.budget(0)
