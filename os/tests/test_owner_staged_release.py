"""Package16 owns only a bounded probe; all other owner qualification stays gated."""
import copy
import json
import os
import pathlib
import re
import sys
import unittest
from unittest.mock import patch

import yaml

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import rehearsal_guard as guard
import owner_media
import owner_vm
import registry_auth

BRANCH='pkg/16-staged-release'


def condition(expression, *, mode='probe', **overrides):
    """Evaluate the workflow's boolean job boundaries for the package16 ref."""
    values={'github.ref_name':BRANCH,'github.event_name':'workflow_dispatch',
            'inputs.rehearsal':mode,'inputs.checks_only':False,'inputs.release_13':False,
            'inputs.switch_from_run':'','inputs.probe_run':'',
            'needs.image.result':'skipped'}
    values.update(overrides)
    for name,value in values.items(): expression=expression.replace(name,repr(value))
    expression=expression.replace('always()','True').replace('cancelled()','False')
    expression=expression.replace('&&',' and ').replace('||',' or ')
    expression=re.sub(r'!(?!=)',' not ',expression)
    return bool(eval(expression,{'__builtins__':{}},{}))


class StagedProbeTest(unittest.TestCase):
    def setUp(self):
        guard.configure('16'); self.addCleanup(guard.configure,'11c')

    def test_own_small_probe_only_ledger_and_no_billing_privacy_minutes(self):
        self.assertEqual((guard.BRANCH,guard.MINUTE_CAP,guard.FULL_CAP,guard.PART_B_CAP),(BRANCH,120,0,0))
        self.assertEqual(guard.SETTINGS['dispatch_caps'],{'probe':2})
        self.assertEqual(guard.SETTINGS['publish_cap'],0)
        self.assertEqual(guard.SETTINGS['titles'],{'probe':'Two-disk rehearsal (probe)'})
        self.assertEqual(guard.SETTINGS['organization_budget']['other_repos_reserve'],150)
        for key in ('push_privacy_reservation','closing_privacy_reservation'):
            self.assertEqual(guard.SETTINGS[key],dict(minutes=0,decision='briefs/14zw-local-privacy.md'))
        with self.assertRaisesRegex(AssertionError,'package14 only'): guard.owner_reservations()
        self.assertEqual(guard.PACKAGES['14']['dispatch_caps'],{'probe':34,'owner-tools':21})
        self.assertEqual(guard.PACKAGES['14']['minute_cap'],2750)

    def test_wrong_mode_or_reservation_refuses_before_queries(self):
        cases=[(mode,72) for mode in ('owner-tools','part-b','keyboard','fixture','inspect','checks','release-13','publish-ci')]
        cases += [('probe',n) for n in (0,42,70,71,73,120)]
        for mode,reserve in cases:
            with self.subTest(mode=mode,reserve=reserve),patch.dict(os.environ,REHEARSAL_PACKAGE='16',clear=True), \
                 patch.object(sys,'argv',['rehearsal_guard.py',mode,str(reserve)]),patch.object(guard,'budget') as budget:
                with self.assertRaises(AssertionError):guard.main()
                budget.assert_not_called()

    def test_native_preflight_still_required_at_the_exact_head(self):
        run=dict(id=12,event='workflow_dispatch',path='.github/workflows/os-image.yml',head_branch=BRANCH,
                 head_sha='a'*40,run_attempt=1,display_title=guard.SETTINGS['titles']['probe'])
        step=dict(name=guard.NATIVE_STEP,status='completed',conclusion='success')
        job=dict(name='Pinned live ISO inspection and two-disk rehearsal',head_sha='a'*40,steps=[step])
        with patch.object(guard,'api',return_value=dict(total_count=1,jobs=[job])):
            self.assertEqual(guard.probe_native(run,'a'*40,current=True)['status'],'passed')
            step['conclusion']='failure'
            with self.assertRaisesRegex(AssertionError,'native preflight'):guard.probe_native(run,'a'*40,current=True)
            step['conclusion']='success'
            with self.assertRaises(AssertionError):guard.probe_native(run,'b'*40,current=True)

    def test_second_dispatch_allowed_third_and_over_budget_refused(self):
        base=dict(event='workflow_dispatch',head_sha='a'*40,status='completed',conclusion='success',
                  run_attempt=1,display_title=guard.SETTINGS['titles']['probe'],created_at='2026-11-02T00:00:00Z')
        runs=[dict(base,id=1)]
        job=dict(conclusion='success',started_at='2026-11-02T00:00:00Z',completed_at='2026-11-02T00:01:00Z',
                 steps=[dict(name='probe',status='completed',conclusion='success',
                  started_at='2026-11-02T00:00:00Z',completed_at='2026-11-02T00:01:00Z')])
        def api(path):return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1,jobs=[job])
        with patch.object(guard,'api',side_effect=api):
            self.assertEqual(guard.budget(72)['dispatch_counts'],{'probe':1})
            runs.append(dict(base,id=2))
            self.assertEqual(guard.budget(72)['dispatch_counts'],{'probe':2})
            with self.assertRaisesRegex(AssertionError,'exceeds 120'):guard.budget(119)
            runs.append(dict(base,id=3))
            with self.assertRaisesRegex(AssertionError,'probe dispatch allowance'):guard.budget(0)

    def test_runner_and_registry_accept_only_matching_branch_package_probe(self):
        env=dict(GITHUB_ACTIONS='true',GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY=guard.REPOSITORY,
                 GITHUB_REF_NAME=BRANCH,REHEARSAL_PACKAGE='16',REHEARSAL_MODE='probe')
        with patch.dict(os.environ,env,clear=True):
            owner_media.require_runner();registry_auth.require_dispatch()
            with patch.object(registry_auth.legacy,'create') as legacy:
                with self.assertRaisesRegex(AssertionError,'no owner-token fallback'):registry_auth.create()
                legacy.assert_not_called()
        for key,value in (('GITHUB_REF_NAME','pkg/14-owner-tools'),('REHEARSAL_PACKAGE','14'),
                          ('REHEARSAL_MODE','owner-tools'),('REHEARSAL_MODE','keyboard'),
                          ('GITHUB_REPOSITORY','elsewhere/AresOS')):
            with self.subTest(key=key,value=value),patch.dict(os.environ,dict(env,**{key:value}),clear=True):
                with self.assertRaises(AssertionError):owner_media.require_runner()
                with self.assertRaises(AssertionError):registry_auth.require_dispatch()

    def test_owner_driver_refuses_qualification_even_with_probe_environment(self):
        env=dict(GITHUB_ACTIONS='true',GITHUB_REPOSITORY=guard.REPOSITORY,GITHUB_REF_NAME=BRANCH,
                 REHEARSAL_PACKAGE='16',REHEARSAL_MODE='probe')
        with patch.dict(os.environ,env,clear=True),patch.object(sys,'argv',['owner_vm.py','owner-tools']), \
             patch.object(pathlib.Path,'read_text') as read,patch.object(owner_vm,'Media') as media:
            with self.assertRaisesRegex(AssertionError,'package16 permits only the owner-tools probe'):owner_vm.main()
            read.assert_not_called();media.assert_not_called()

    def test_workflow_dispatch_only_runs_owner_probe_and_never_other_jobs(self):
        workflow=yaml.load((ROOT/'.github/workflows/os-image.yml').read_text(),Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['on']),{'workflow_dispatch'})
        self.assertIn("github.ref_name == 'pkg/16-staged-release' && '16'",workflow['env']['REHEARSAL_PACKAGE'])
        for mode in ('','inspect','fixture','probe','part-b','keyboard','owner-tools'):
            for name,job in workflow['jobs'].items():
                with self.subTest(mode=mode,job=name):
                    self.assertEqual(condition(job['if'],mode=mode),name=='rehearsal' and mode=='probe')
        for input in ('inputs.checks_only','inputs.release_13','inputs.switch_from_run','inputs.probe_run'):
            for name,job in workflow['jobs'].items():
                with self.subTest(input=input,job=name):
                    self.assertFalse(condition(job['if'],**{input:True}))
        job=workflow['jobs']['rehearsal']
        steps={s.get('name'):s for s in job['steps']}
        for name in ('Prove package 14 native host capabilities before expensive downloads',
                     'Prepare package 13 job-token credentials without owner-secret fallback',
                     'Verify the exact private signature natively for the offline guest',
                     'Remove package 13 job-token credentials'):
            self.assertTrue(condition(steps[name]['if']))
        for name in ('Create runner-temporary pinned-image credentials','Remove owner registry credentials'):
            self.assertFalse(condition(steps[name]['if']))
        self.assertIn('test "$REHEARSAL_PACKAGE" = 14 || test "$REHEARSAL_PACKAGE" = 16',
                      steps['Prepare disposable file disks and qualify the real live environment']['run'])
        self.assertIn("package+'-dispatch-authorization.json'",(ROOT/'os/ci/owner_vm.py').read_text())


if __name__=='__main__':unittest.main()
