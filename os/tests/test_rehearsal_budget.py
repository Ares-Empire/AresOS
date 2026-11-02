import pathlib
import sys
import unittest
import yaml
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import rehearsal_guard as guard


class BudgetTest(unittest.TestCase):
    def test_part_b_reservation_keeps_legacy_limits_and_covers_owner_limits(self):
        workflow = yaml.load((pathlib.Path(__file__).resolve().parents[2] /
                              '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        job = workflow['jobs']['rehearsal']
        self.assertEqual(job['timeout-minutes'], "${{ inputs.rehearsal == 'owner-tools' && 240 || github.ref_name == 'pkg/14-owner-tools' && inputs.rehearsal == 'probe' && 70 || (inputs.rehearsal == 'part-b' || inputs.rehearsal == 'keyboard') && 130 || 40 }}")
        vm, = [s for s in job['steps'] if 'two_disk_vm.py' in s.get('run', '')]
        self.assertEqual(vm['timeout-minutes'], "${{ inputs.rehearsal == 'owner-tools' && 200 || (inputs.rehearsal == 'part-b' || inputs.rehearsal == 'keyboard') && 106 || 80 }}")
        guards = [s for s in job['steps'] if 'rehearsal_guard.py' in s.get('run', '')]
        self.assertEqual(len(guards), 2)
        reserve, = [s for s in guards if s['name'].startswith('Reserve the separate 11c')]
        self.assertIn("'${{ inputs.rehearsal == 'owner-tools' && 240 || github.ref_name == 'pkg/14-owner-tools' && inputs.rehearsal == 'probe' && 72 || (inputs.rehearsal == 'part-b' || inputs.rehearsal == 'keyboard') && 130 || 42 }}'", reserve['run'])
        native, = [s for s in guards if s['name']=='Require completed native preflight before any package 13 VM']
        self.assertEqual(native['if'], "(github.ref_name == 'pkg/13-keyboard-layout' || github.ref_name == 'pkg/14-owner-tools') && inputs.rehearsal == 'probe'")
        self.assertEqual(native['run'], "python3 os/ci/rehearsal_guard.py ci '${{ github.ref_name == 'pkg/14-owner-tools' && 72 || 42 }}'")
        self.assertNotIn('full', workflow['on']['workflow_dispatch']['inputs']['rehearsal']['options'])
        self.assertEqual(vm['run'].count('two_disk_vm.py'), 1)

    def test_full_dispatch_count_includes_current_run_and_rejects_sixth(self):
        runs = [dict(id=i, display_title='Two-disk rehearsal (full)', head_sha='a' * 40,
                     created_at=guard.START, status='completed', conclusion='success') for i in range(5)]
        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(jobs=[])
        with patch.object(guard, 'api', side_effect=api):
            result = guard.budget(182, current=4)
            self.assertEqual(result['full_dispatched'], 5)
            runs.append(dict(runs[0], id=5))
            with self.assertRaisesRegex(AssertionError, 'full-run allowance exhausted'):
                guard.budget(0, current=5)

    def test_allowance_includes_privacy_push_and_pr_jobs_and_excludes_old_runs(self):
        def run(number, title, date=guard.START, status='completed'):
            return dict(id=number, display_title=title, head_sha='a' * 40, conclusion='success',
                        created_at=date, status=status)
        runs = [run(1, 'privacy-check'), run(2, 'privacy-check'), run(3, 'Two-disk rehearsal (probe)'),
                run(4, 'Two-disk rehearsal (full)', '2026-10-22T23:00:00Z')]
        job = dict(conclusion='success', started_at='2026-10-23T16:21:00Z', completed_at='2026-10-23T16:22:01Z',
                   steps=[dict(name='Run fixture task',started_at='2026-10-23T16:21:00Z',completed_at='2026-10-23T16:22:01Z')])
        def api(path):
            if path.startswith('actions/runs?'):
                self.assertNotIn('workflow_dispatch', path)
                return dict(workflow_runs=runs)
            return dict(jobs=[job, dict(conclusion='skipped')])
        with patch.object(guard, 'api', side_effect=api):
            self.assertEqual((guard.START, guard.MINUTE_CAP, guard.FULL_CAP), ('2026-10-23T16:21:00Z', 900, 5))
            result = guard.budget(894)
            self.assertEqual(result['consumed_minutes'], 6)
            self.assertEqual(result['full_dispatched'], 0)
            with self.assertRaisesRegex(AssertionError, 'exceeds 900'):
                guard.budget(895)
            runs[1]['status'] = 'in_progress'
            with self.assertRaisesRegex(AssertionError, 'active'):
                guard.budget(0)

    def test_single_part_b_count_includes_current_and_rejects_a_second(self):
        runs = [dict(id=1, display_title='Two-disk rehearsal (part-b)', head_sha='a' * 40,
                     created_at=guard.START, status='in_progress', conclusion=None)]
        with patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=runs)):
            self.assertEqual(guard.budget(130, current=1)['part_b_dispatched'], 1)
            runs.append(dict(runs[0], id=2, status='completed'))
            with patch.object(guard, 'api', side_effect=lambda path: dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(jobs=[])), \
                 self.assertRaisesRegex(AssertionError, 'Part B qualification allowance exhausted'):
                guard.budget(130, current=1)
