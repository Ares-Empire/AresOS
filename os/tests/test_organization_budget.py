import copy
import datetime
import io
import json
import os
import pathlib
import subprocess
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'ci'))
import rehearsal_guard as guard


class OrganizationBudgetTest(unittest.TestCase):
    def setUp(self):
        guard.configure('13'); self.addCleanup(guard.configure,'11c')
        self.now=datetime.datetime(2026,10,25,tzinfo=datetime.timezone.utc)
        row=dict(product='Actions',sku='actions_linux',unitType='minutes',grossQuantity=1255,
                 discountQuantity=1257,netQuantity=0,grossAmount=7.53,discountAmount=7.542,netAmount=0)
        self.response=dict(timePeriod=dict(year=2026,month=10),organization='Ares-Empire',usageItems=[row])

    def call(self,reserve=184):
        with patch.object(guard,'read_only',return_value=json.dumps(self.response).encode()) as read:
            result=guard.organization_budget(reserve,self.now)
        read.assert_called_once_with('organizations/Ares-Empire/settings/billing/usage/summary?year=2026&month=10')
        return result

    def test_full_plan_uses_gross_or_discount_conservatively_and_keeps_150(self):
        result=self.call()
        self.assertEqual((result['used_minutes'],result['remaining_minutes'],result['after_reservation']),(1257,743,559))
        self.assertEqual(self.call(593)['after_reservation'],150)
        with self.assertRaisesRegex(AssertionError,'must leave 150'):self.call(594)

    def test_storage_is_not_minutes_and_no_net_paid_usage_is_allowed(self):
        storage=dict(self.response['usageItems'][0],sku='actions_storage',unitType='gigabyte-hours',grossQuantity=10,discountQuantity=10)
        self.response['usageItems'].append(storage)
        self.assertEqual(self.call()['used_minutes'],1257)
        for field in ('netAmount','netQuantity'):
            storage[field]=1
            with self.assertRaisesRegex(AssertionError,'outside the free'):self.call()
            storage[field]=0

    def test_missing_stale_malformed_or_unknown_usage_fails_closed(self):
        original=copy.deepcopy(self.response)
        changes=[lambda r:r.update(organization='other'),lambda r:r['timePeriod'].update(month=9),
                 lambda r:r.update(usageItems=[]),lambda r:r.update(nextPage=2),
                 lambda r:r['usageItems'].append(copy.deepcopy(r['usageItems'][0])),
                 lambda r:r['usageItems'][0].update(sku='actions_windows'),
                 lambda r:r['usageItems'][0].update(unitType='hours'),
                 lambda r:r['usageItems'][0].update(grossQuantity=-1),
                 lambda r:r['usageItems'][0].update(grossQuantity=float('nan')),
                 lambda r:r['usageItems'][0].update(discountQuantity=True)]
        for change in changes:
            self.response=copy.deepcopy(original);change(self.response)
            with self.subTest(response=self.response),self.assertRaises(AssertionError):self.call()
        for reserve in (-1,True,1.5):
            with self.assertRaisesRegex(AssertionError,'invalid organization'):self.call(reserve)

    def test_unreadable_billing_stops_without_new_credentials_or_mutation(self):
        error=subprocess.CalledProcessError(1,['gh','api'],stderr=b'gh: Forbidden (HTTP 403)')
        with patch.object(guard,'read_only',side_effect=error) as read,self.assertRaises(subprocess.CalledProcessError):
            guard.organization_budget(184,self.now)
        self.assertEqual(read.call_count,1)

    def test_scheduling_requires_billing_but_job_token_ci_needs_no_billing_permission(self):
        ledger=dict(history=dict(complete=True,ids_count=1,total_count=1),dispatch_counts=dict(probe=1),runs=[])
        run=dict(head_branch=guard.BRANCH,head_sha='a'*40,display_title=guard.SETTINGS['titles']['probe'],event='workflow_dispatch')
        env=dict(REHEARSAL_PACKAGE='13',REHEARSAL_MODE='probe',GITHUB_SHA='a'*40,GITHUB_RUN_ID='7',GITHUB_REF_NAME=guard.BRANCH)
        with patch.dict(os.environ,env),patch.object(guard,'budget',return_value=ledger), \
             patch.object(guard,'api',return_value=run),patch.object(pathlib.Path,'write_text') as write, \
             patch.object(sys,'stdout',io.StringIO()),patch.object(guard,'organization_budget',side_effect=AssertionError('billing unavailable')) as billing:
            with patch.object(sys,'argv',['guard.py','probe','184']),self.assertRaisesRegex(AssertionError,'billing unavailable'):
                guard.main()
            billing.assert_called_once_with(184);write.assert_not_called();billing.reset_mock()
            with patch.object(sys,'argv',['guard.py','probe-budget-ci','42']):guard.main()
            billing.assert_not_called()


if __name__=='__main__':unittest.main()
