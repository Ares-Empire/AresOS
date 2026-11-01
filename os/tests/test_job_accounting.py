"""14zz accounting regressions derived from the real retained probe 29 job."""
import copy
import hashlib
import io
import json
import pathlib
import sys
import os
import tempfile
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import rehearsal_guard as guard


def retained():
    binding=json.loads((ROOT/'os/tests/fixtures/owner-tools/14zz-accounting-source.json').read_text())
    raw=(ROOT/binding['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest()==binding['sha256']
    return json.loads(raw)


class JobAccountingTest(unittest.TestCase):
    def test_actual_probe29_negative_interval_charges26_not_one(self):
        job=retained()
        self.assertGreater(job['started_at'],job['completed_at'])
        result=guard.job_accounting(job,72)
        self.assertEqual((result['minutes'],result['rule']),(26,'ordered-span'))
        self.assertEqual(result['selected_start'],'2026-11-01T08:51:56+00:00')
        self.assertEqual(result['selected_completion'],'2026-11-01T09:17:30+00:00')

    def test_consistent_enclosing_job_interval_keeps_setup_and_cleanup_time(self):
        job=retained();job['started_at']='2026-11-01T08:51:55Z'
        result=guard.job_accounting(job,72)
        self.assertEqual((result['minutes'],result['rule']),(26,'job-interval'))

    def test_widest_supported_span_includes_outside_steps_and_earlier_job_start(self):
        job=retained();job['started_at']='2026-11-01T08:50:00Z';job['completed_at']='2026-11-01T09:17:00Z'
        result=guard.job_accounting(job,72)
        self.assertEqual((result['minutes'],result['rule']),(28,'ordered-span'))
        self.assertEqual(result['selected_completion'],'2026-11-01T09:17:28+00:00')

    def test_missing_or_unordered_steps_charge_the_whole_dispatch_bound(self):
        for bound in (72,160,220):
            for defect in ('absent','empty','missing-time','backward','reordered','naive'):
                job=retained()
                if defect=='absent':job.pop('steps')
                elif defect=='empty':job['steps']=[]
                elif defect=='missing-time':job['steps'][0].pop('started_at')
                elif defect=='backward':job['steps'][0]['completed_at']='2026-11-01T08:00:00Z'
                elif defect=='reordered':job['steps'][0],job['steps'][1]=job['steps'][1],job['steps'][0]
                else:job['steps'][0]['started_at']='2026-11-01T08:51:56'
                with self.subTest(bound=bound,defect=defect):
                    result=guard.job_accounting(job,bound)
                    self.assertEqual((result['minutes'],result['rule']),(bound,'full-bound'))

    def test_usable_steps_recover_missing_job_fields_but_unknown_bound_refuses(self):
        job=retained();job.pop('started_at');job.pop('completed_at')
        self.assertEqual(guard.job_accounting(job,72)['minutes'],26)
        job['steps']=[]
        with self.assertRaisesRegex(AssertionError,'approved full bound'):guard.job_minutes(job)

    def test_skipped_placeholder_is_free_and_valid_zero_time_keeps_minimum(self):
        self.assertEqual(guard.job_accounting(dict(conclusion='skipped'),72)['rule'],'skipped')
        job=retained();job.update(started_at='2026-11-01T09:00:00Z',completed_at='2026-11-01T09:00:00Z')
        job['steps']=[dict(started_at=job['started_at'],completed_at=job['completed_at'])]
        self.assertEqual(guard.job_minutes(job,72),1)


class LedgerComparisonTest(unittest.TestCase):
    def setUp(self):
        guard.configure('14');self.addCleanup(guard.configure,'11c')
        self.previous=dict(authorization=dict(allowance='14',start='first',accounting_policy=guard.ACCOUNTING_POLICY,history=dict(complete=True,ids_count=1,total_count=1),
            consumed_minutes=26,legacy_recorded_minutes=1,runs=[dict(run=1,minutes=26)],dispatch_counts=dict(probe=1,**{'owner-tools':0}),
            organization_budget=dict(source='month11',used_minutes=282,checked_at='2026-11-01T09:21:00+00:00')),dispatched_run=2)
        self.current=dict(allowance='14',start='first',accounting_policy=guard.ACCOUNTING_POLICY,history=dict(complete=True,ids_count=2,total_count=2),consumed_minutes=31,
            runs=[dict(run=1,minutes=26),dict(run=2,minutes=5,title=guard.SETTINGS['titles']['owner-tools'])],
            dispatch_counts=dict(probe=1,**{'owner-tools':1}))
        self.org=dict(source='month11',used_minutes=287,checked_at='2026-11-01T09:27:00+00:00')

    def test_baseline_uses_the_saved_recomputed_charge_not_the_legacy_value(self):
        result=guard.ledger_organization_check(self.current,self.org,self.previous)
        self.assertEqual((result['recomputed_previous_minutes'],result['package_increase'],result['organization_increase']),(26,5,5))

    def test_past_charge_reduction_is_not_erased_and_old_policy_refuses(self):
        self.current['runs'][0]['minutes']=20;self.current['consumed_minutes']=25
        with self.assertRaisesRegex(AssertionError,'decreased'):guard.ledger_organization_check(self.current,self.org,self.previous)
        self.current['runs'][1]['minutes']=10;self.current['consumed_minutes']=30;self.org['used_minutes']=292
        with self.assertRaisesRegex(AssertionError,'more than 5'):guard.ledger_organization_check(self.current,self.org,self.previous)
        self.current['runs'][0]['minutes']=26;self.current['runs'][1]['minutes']=5;self.current['consumed_minutes']=31;self.org['used_minutes']=287
        self.previous['authorization'].pop('accounting_policy')
        with self.assertRaisesRegex(AssertionError,'must be recomputed'):guard.ledger_organization_check(self.current,self.org,self.previous)

    def test_five_minutes_tolerance_passes_six_refuses(self):
        self.org['used_minutes']=292
        self.assertEqual(guard.ledger_organization_check(self.current,self.org,self.previous)['organization_increase'],10)
        self.org['used_minutes']=293
        with self.assertRaisesRegex(AssertionError,'more than 5'):guard.ledger_organization_check(self.current,self.org,self.previous)

    def test_wrong_period_missing_run_duplicate_stale_baseline_or_decrease_refuses(self):
        for defect in ('period','missing','duplicate','old-checkpoint','decrease','incomplete','wrong-dispatch'):
            before,current,org=copy.deepcopy(self.previous),copy.deepcopy(self.current),copy.deepcopy(self.org)
            if defect=='period':org['source']='month12'
            elif defect=='missing':before['authorization']['runs'][0]['run']=99
            elif defect=='duplicate':current['runs'].append(copy.deepcopy(current['runs'][0]))
            elif defect=='old-checkpoint':current['dispatch_counts']['probe']=2
            elif defect=='decrease':org['used_minutes']=281
            elif defect=='incomplete':before['authorization']['history']['complete']=False
            else:before['dispatched_run']=99
            with self.subTest(defect=defect),self.assertRaises(AssertionError):guard.ledger_organization_check(current,org,before)

    def test_dispatch_guard_refuses_undercount_before_writing_authorization(self):
        self.org['used_minutes']=293
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as directory:
            path=pathlib.Path(directory)/'previous.json';path.write_text(json.dumps(self.previous))
            env=dict(REHEARSAL_PACKAGE='14',GITHUB_REF_NAME=guard.BRANCH,GITHUB_SHA='a'*40,REHEARSAL_PREVIOUS_DISPATCH=str(path))
            with patch.dict(os.environ,env),patch.object(sys,'argv',['guard.py','probe','292']), \
                    patch.object(guard,'budget',return_value=copy.deepcopy(self.current)), \
                    patch.object(guard,'organization_budget',return_value=self.org), \
                    patch.object(pathlib.Path,'write_text') as write,patch.object(sys,'stdout',io.StringIO()):
                with self.assertRaisesRegex(AssertionError,'more than 5'):guard.main()
            write.assert_not_called()


if __name__=='__main__':unittest.main()
