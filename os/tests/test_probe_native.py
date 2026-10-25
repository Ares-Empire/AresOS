import copy
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ci'))
import rehearsal_guard as guard


class ProbeNativeTest(unittest.TestCase):
    def setUp(self):
        guard.configure('13')
        self.addCleanup(guard.configure,'11c')
        self.sha='a'*40
        self.run=dict(id=7,event='workflow_dispatch',path='.github/workflows/os-image.yml',
            head_branch=guard.BRANCH,head_sha=self.sha,run_attempt=1,
            display_title=guard.SETTINGS['titles']['probe'],status='completed',conclusion='success')
        self.jobs=dict(total_count=1,jobs=[dict(name='Pinned live ISO inspection and two-disk rehearsal',
            head_sha=self.sha,steps=[dict(name=guard.NATIVE_STEP,status='completed',conclusion='success')])])
        self.records=dict(runs=[dict(run=7,title=self.run['display_title'],sha=self.sha,conclusion='success')])

    def test_only_probe_budget_reservations_may_defer_native_and_extra_probe_is_bounded(self):
        self.assertEqual(guard.SETTINGS['dispatch_caps'],{'release-13':3,'checks':1,'probe':4,'keyboard':3})
        for mode in ('probe','probe-budget-ci'):
            self.assertEqual(guard.native_gate('probe',mode,{},self.sha)['status'],'pending')
        with self.assertRaisesRegex(AssertionError,'passing probe'):
            guard.native_gate('keyboard','keyboard',dict(runs=[]),self.sha)
        runs=[dict(self.run,id=i,created_at='2026-10-25T02:02:34Z') for i in (1,2,3,4)]
        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=0,jobs=[])
        with patch.object(guard,'api',side_effect=api):
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],4)
            runs.append(dict(runs[0],id=5))
            with self.assertRaisesRegex(AssertionError,'dispatch allowance exhausted'):
                guard.budget(0)

    def test_current_probe_requires_the_actual_completed_successful_native_step(self):
        current=dict(self.run,status='in_progress',conclusion=None)
        with patch.object(guard,'api',return_value=self.jobs):
            self.assertEqual(guard.native_gate('probe','ci',dict(runs=[]),self.sha,current)['run'],7)
        for status,conclusion in (('in_progress',None),('completed','failure'),('completed','skipped')):
            bad=copy.deepcopy(self.jobs);bad['jobs'][0]['steps'][0].update(status=status,conclusion=conclusion)
            with self.subTest(status=status,conclusion=conclusion),patch.object(guard,'api',return_value=bad):
                with self.assertRaisesRegex(AssertionError,'has not passed'):
                    guard.probe_native(current,self.sha,current=True)

    def test_qualification_uses_passing_probe_preflight_on_exact_head(self):
        def api(path):
            return self.jobs if '/jobs?' in path else self.run
        with patch.object(guard,'api',side_effect=api):
            self.assertEqual(guard.native_gate('keyboard','keyboard',self.records,self.sha)['status'],'passed')
            for field,value in (('head_sha','b'*40),('conclusion','failure'),('run_attempt',2),('event','push')):
                bad=dict(self.run,**{field:value})
                with self.subTest(field=field),self.assertRaises(AssertionError):
                    guard.probe_native(bad,self.sha)

    def test_incomplete_or_ambiguous_native_evidence_fails_closed(self):
        for changed in (dict(self.jobs,total_count=2),dict(self.jobs,jobs=[]),
                        dict(total_count=2,jobs=self.jobs['jobs']*2)):
            with self.subTest(changed=changed),patch.object(guard,'api',return_value=changed):
                with self.assertRaises((AssertionError,ValueError)):
                    guard.probe_native(self.run,self.sha)
        workflow=pathlib.Path('.github/workflows/os-image.yml').read_text()
        rehearsal=workflow.split('  rehearsal:\n',1)[1]
        self.assertLess(rehearsal.index('name: '+guard.NATIVE_STEP),rehearsal.index('name: Require completed native preflight'))
        self.assertLess(rehearsal.index('name: Require completed native preflight'),rehearsal.index('name: Prepare package 13 job-token credentials'))


if __name__=='__main__':
    unittest.main()
