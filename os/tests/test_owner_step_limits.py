"""Couple approved limits to the retained q17/q19 timing evidence."""
import datetime,json,pathlib,sys,unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import rehearsal_guard as guard

class OwnerStepLimitTest(unittest.TestCase):
    def setUp(self):
        self.value=json.loads((ROOT/'os/manifest/ci/14/14zzb-timing/projection.json').read_text())

    def test_every_known_stage_uses_the_slower_real_interval(self):
        value=self.value
        self.assertEqual({row['qualification'] for row in value['observed_runs']},{17,19})
        self.assertEqual(len(value['projection']),17)
        for row in value['projection'][:12]:
            self.assertEqual({x['qualification'] for x in row['observations']},{17,19})
            for observed in row['observations']:
                start=datetime.datetime.fromisoformat(observed['started_at'])
                end=datetime.datetime.fromisoformat(observed['completed_at'].replace('Z','+00:00'))
                self.assertAlmostEqual((end-start).total_seconds(),observed['seconds'])
            self.assertEqual(row['seconds'],max(x['seconds'] for x in row['observations']))
        self.assertEqual(len(value['qualification17_completed_command_facts']),3)

    def test_each_remaining_group_gets_a_whole_slowest_comparable_boot(self):
        value=self.value
        stock=max(x['seconds'] for x in value['comparable_stock_candidates'])
        windows=max(x['seconds'] for x in value['comparable_windows_candidates'])
        self.assertEqual([x['seconds'] for x in value['projection'][12:15]],[stock]*3)
        self.assertEqual([x['seconds'] for x in value['projection'][15:]],[windows]*2)
        self.assertEqual(value['projection'][12]['comparable_stage'],'tools-stock')
        self.assertEqual(value['projection'][15]['comparable_stage'],'prepared-unattended-windows')

    def test_vm_margin_and_whole_job_fit_the_exact_approved_bounds(self):
        value=self.value
        seconds=sum(x['seconds'] for x in value['projection'])
        self.assertEqual(value['margin_fraction'],0.25)
        self.assertAlmostEqual(seconds/60,value['vm_projection_minutes'])
        self.assertAlmostEqual(seconds*1.25/60,value['vm_with_margin_minutes'])
        self.assertLessEqual(value['vm_with_margin_minutes'],180)
        before=max(x['before_vm_seconds'] for x in value['observed_runs'])
        after=max(x['after_vm_seconds'] for x in value['observed_runs'])
        self.assertAlmostEqual((seconds+before+after)*1.25/60,value['whole_job_with_margin_minutes'])
        self.assertLessEqual(value['whole_job_with_margin_minutes'],guard.OWNER_QUALIFICATION_BOUND)
        self.assertEqual(guard.OWNER_QUALIFICATION_BOUND,220)
        self.assertLessEqual(180+(before+after)/60,guard.OWNER_QUALIFICATION_BOUND)
        self.assertEqual((value['probe_bound_minutes'],value['vm_limit_minutes'],value['qualification_bound_minutes']),(72,180,220))
        self.assertEqual(value['starting_minutes']+72+220,2436)
        self.assertEqual(value['cap_minutes'],2750)
