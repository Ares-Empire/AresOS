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
        self.assertLessEqual(value['whole_job_with_margin_minutes'],value['qualification_bound_minutes'])
        self.assertEqual(guard.OWNER_QUALIFICATION_BOUND,240)
        self.assertLessEqual(180+(before+after)/60,value['qualification_bound_minutes'])
        self.assertEqual((value['probe_bound_minutes'],value['vm_limit_minutes'],value['qualification_bound_minutes']),(72,180,220))
        self.assertEqual(value['starting_minutes']+72+220,2436)
        self.assertEqual(value['cap_minutes'],2750)

    def test_review_fix_reset_projection_fits_the_last_approved_limits(self):
        import hashlib
        value=json.loads((ROOT/'os/manifest/ci/14/14zzc-timing/projection.json').read_text())
        self.assertEqual(value['status'],'passed')
        self.assertEqual(value['margin_fraction'],.25)
        self.assertEqual(len(value['projection']),19)
        self.assertAlmostEqual(sum(x['seconds'] for x in value['projection'])/60,value['vm_projection_minutes'])
        self.assertAlmostEqual(value['vm_projection_minutes']*1.25,value['vm_with_margin_minutes'])
        self.assertGreater(value['vm_with_margin_minutes'],180)
        self.assertLessEqual(value['vm_with_margin_minutes'],200)
        self.assertLessEqual(value['whole_job_with_margin_minutes'],240)
        self.assertEqual((value['vm_limit_minutes'],value['qualification_bound_minutes'],value['probe_bound_minutes']),(200,240,72))
        self.assertEqual(value['round_worst_case_minutes'],2301+72+240)
        self.assertLessEqual(value['round_worst_case_minutes'],2750)
        self.assertEqual(value['caps'],{'probe':32,'owner-tools':21})
        self.assertEqual([x['path'] for x in value['sources']],['os/manifest/ci/14/14zzb-timing/projection.json',
            'os/manifest/ci/14/14zzb-round/terminal-facts.json','.work/14/run-41324240079/evidence.zip','os/owner-tools/commands.json'])
        # A source set aside until the next VM rehearsal (see test_checkout_sources)
        # must match the bytes recorded then; every other source keeps its hash.
        from test_checkout_sources import pending_rebind, checkout
        waiting={row['path']:row['sha256'] for row in pending_rebind()}
        # Once a rehearsal rebinds a waiting source, its current binding holds;
        # the list may hold other files again after that rehearsal (27b).
        bound={row['path']:row['sha256'] for row in checkout.merge(checkout.active_tables(ROOT))}
        for index in (0,1,3):
            row=value['sources'][index]
            expected=waiting.get(row['path'],bound.get(row['path'],row['sha256']))
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),expected)
        self.assertEqual(value['sources'][2]['sha256'],json.loads((ROOT/'os/manifest/ci/14/14zzb-round/qualification20-artifact.json').read_text())['sha256'])
        old=self.value; q20=json.loads((ROOT/'os/manifest/ci/14/14zzb-round/terminal-facts.json').read_text())
        observed=old['observed_runs']+[dict(qualification=20,stages=q20['stages'])]
        for row in value['projection'][:14]:
            candidates=[s['seconds'] for v in observed for s in v['stages'] if s['stage']==row['stage']
                and not (row['stage']=='default-stock' and v['qualification']!=20)]
            self.assertEqual(row['seconds'],max(candidates))
        boots=old['comparable_stock_candidates']+[s for v in observed for s in v['stages'] if s['stage'] in ('aresos-intl','aresos-back-de')]
        self.assertEqual([x['seconds'] for x in value['projection'][16:18]],[max(x['seconds'] for x in boots)]*2)
        bootstrap=value['projection'][-1]
        commands=json.loads((ROOT/'os/owner-tools/commands.json').read_text())
        self.assertEqual(bootstrap['lines'],len(commands['install'].splitlines()))
        self.assertLessEqual(bootstrap['maximum_line_chars'],bootstrap['old_line_chars'])
        self.assertEqual(bootstrap['seconds'],(bootstrap['lines']-1)*bootstrap['seconds_per_extra_line'])
