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


class PaidOverflowTest(unittest.TestCase):
    def setUp(self):
        guard.configure('14'); self.addCleanup(guard.configure,'11c')
        self.now=datetime.datetime(2026,10,26,tzinfo=datetime.timezone.utc)
        self.usage=dict(timePeriod=dict(year=2026,month=10),organization='Ares-Empire',usageItems=[
            dict(product='Actions',sku='actions_linux',unitType='minutes',grossQuantity=1869,
                 discountQuantity=1869,netQuantity=0,grossAmount=11.214,discountAmount=11.214,
                 netAmount=0,pricePerUnit=0.006)])
        self.budgets=dict(budgets=[dict(budget_type='ProductPricing',budget_product_sku='actions',
            budget_scope='organization',budget_entity_name='Ares-Empire',budget_amount=6,
            prevent_further_usage=True)],has_next_page=False,total_count=1)

    def call(self,reserve=178):
        with patch.object(guard,'read_only',side_effect=[json.dumps(self.usage).encode(),json.dumps(self.budgets).encode()]) as read:
            result=guard.organization_budget(reserve,self.now)
        self.assertEqual([c.args[0] for c in read.call_args_list],[
            'organizations/Ares-Empire/settings/billing/usage/summary?year=2026&month=10',
            'organizations/Ares-Empire/settings/billing/budgets'])
        return result

    def test_reads_budget_and_price_and_floors_paid_minutes(self):
        result=self.call();paid=result['paid_overflow']
        self.assertEqual((result['included_minutes_left'],paid['paid_minutes'],result['remaining_minutes'],result['after_reservation']),(131,1000,1131,953))
        self.assertEqual((paid['budget_amount'],paid['pricePerUnit'],paid['prevent_further_usage']),(6,0.006,True))
        self.assertEqual(paid['decision'],'briefs/14zc-six-dollar-round.md')
        self.assertEqual(len(paid['response_sha256']),64)
        self.assertEqual(self.call(1131)['after_reservation'],0)
        with self.assertRaisesRegex(AssertionError,'must leave 0'):self.call(1132)
        self.usage['usageItems'][0]['pricePerUnit']=0.03
        self.assertEqual(self.call(0)['paid_overflow']['paid_minutes'],200)

    def test_reported_paid_spend_is_not_available_twice(self):
        self.usage['usageItems'][0].update(grossQuantity=2014,discountQuantity=2000,netQuantity=14,netAmount=0.08)
        result=self.call(0)
        self.assertEqual((result['included_minutes_left'],result['paid_overflow']['paid_minutes'],result['remaining_minutes']),(0,986,986))
        self.assertEqual(result['paid_overflow']['available_budget'],5.92)
        storage=dict(self.usage['usageItems'][0],sku='actions_storage',unitType='gigabyte-hours',netAmount=0.01)
        self.usage['usageItems'].append(storage)
        self.assertEqual(self.call(0)['paid_overflow']['paid_minutes'],985)
        self.usage['usageItems'][0]['netAmount']=6.01
        with self.assertRaisesRegex(AssertionError,'exceeds approved'):self.call(0)

    def test_wrong_budget_prevention_amount_scope_or_sku_refuses(self):
        original=copy.deepcopy(self.budgets)
        for key,value in [('budget_amount',0),('budget_amount',1),('budget_amount',2),('budget_amount',3),
                          ('budget_amount',4),('budget_amount',5),('budget_amount',7),('budget_amount',True),('budget_amount','6'),
                          ('prevent_further_usage',False),('prevent_further_usage',1),
                          ('budget_product_sku','packages'),('budget_scope','repository'),
                          ('budget_entity_name','other'),('budget_type','unknown')]:
            self.budgets=copy.deepcopy(original);self.budgets['budgets'][0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(AssertionError):self.call()

    def test_incomplete_duplicate_missing_or_malformed_budget_refuses(self):
        original=copy.deepcopy(self.budgets)
        for change in [lambda r:r.update(has_next_page=True),lambda r:r.update(total_count=2),
                       lambda r:r.update(total_count=True),lambda r:r.update(budgets=[]),
                       lambda r:r.update(budgets=[None]),lambda r:r.update(extra=True),
                       lambda r:(r['budgets'].append(copy.deepcopy(r['budgets'][0])),r.update(total_count=2))]:
            self.budgets=copy.deepcopy(original);change(self.budgets)
            with self.subTest(budget=self.budgets),self.assertRaises(AssertionError):self.call()

    def test_missing_zero_negative_nonfinite_or_non_numeric_price_refuses(self):
        for value in (None,0,-1,float('nan'),float('inf'),True,'0.006'):
            self.usage['usageItems'][0]['pricePerUnit']=value
            with self.subTest(value=value),self.assertRaisesRegex(AssertionError,'pricePerUnit'):self.call()
        self.usage['usageItems'][0].pop('pricePerUnit')
        with self.assertRaisesRegex(AssertionError,'pricePerUnit'):self.call()

    def test_paid_overflow_is_not_approved_outside_october(self):
        self.now=datetime.datetime(2026,11,1,tzinfo=datetime.timezone.utc)
        self.usage['timePeriod']['month']=11
        with self.assertRaisesRegex(AssertionError,'October2026 only'):self.call()


if __name__=='__main__':unittest.main()
