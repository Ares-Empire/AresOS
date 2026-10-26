import hashlib
import copy
import datetime
import json
import os
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import rehearsal_guard as guard
import owner_vm as vm
import registry_auth


class GuardTest(unittest.TestCase):
    def setUp(self):
        guard.configure('14')
        self.addCleanup(guard.configure,'11c')

    def test_package14_counts_all_dispatches_and_privacy_and_refuses_overrun(self):
        self.assertEqual((guard.MINUTE_CAP,guard.FULL_CAP,guard.PART_B_CAP),(520,0,0))
        self.assertEqual(guard.SETTINGS['dispatch_caps'],{'probe':10,'owner-tools':2})
        self.assertEqual(guard.SETTINGS['organization_budget']['other_repos_reserve'],0)
        self.assertEqual(guard.PACKAGES['13']['organization_budget']['other_repos_reserve'],150)
        base=dict(head_sha='a'*40,status='completed',conclusion='success',run_attempt=1)
        runs=[dict(base,id=1,event='push',display_title='privacy',created_at='2026-10-25T00:00:00Z'),
              dict(base,id=2,event='workflow_dispatch',display_title='Two-disk rehearsal (probe)',created_at='2026-10-25T01:00:00Z'),
              dict(base,id=3,event='pull_request',display_title='privacy',created_at='2026-10-25T02:00:00Z')]
        job=dict(conclusion='success',started_at='2026-10-25T01:00:00Z',completed_at='2026-10-25T01:01:01Z')
        def api(path):return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1,jobs=[job])
        with patch.object(guard,'api',side_effect=api):
            self.assertEqual(guard.budget(516)['consumed_minutes'],4)
            with self.assertRaisesRegex(AssertionError,'exceeds 520'):guard.budget(517)
            runs.append(dict(runs[1],id=4))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],2)
            runs.append(dict(runs[1],id=5))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],3)
            runs.append(dict(runs[1],id=6))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],4)
            runs.append(dict(runs[1],id=7))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],5)
            runs.append(dict(runs[1],id=8))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],6)
            runs.append(dict(runs[1],id=9))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],7)
            runs.append(dict(runs[1],id=10))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],8)
            runs.append(dict(runs[1],id=11))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],9)
            runs.append(dict(runs[1],id=12))
            self.assertEqual(guard.budget(0)['dispatch_counts']['probe'],10)
            runs.append(dict(runs[1],id=13))
            with self.assertRaisesRegex(AssertionError,'probe dispatch allowance'):guard.budget(0)

    def test_wrong_or_incomplete_native_proof_never_reaches_vm_or_media(self):
        for status,sha in (('pending','a'*40),('failed','a'*40),('passed','b'*40)):
            proof=dict(allowance='14',native=dict(status=status,sha=sha))
            with patch.object(sys,'argv',['owner_vm.py','probe']),patch.dict(os.environ,GITHUB_SHA='a'*40), \
                 patch('pathlib.Path.read_text',return_value=json.dumps(proof)),patch.object(vm,'Media') as media, \
                 self.assertRaises(AssertionError):vm.main()
            media.assert_not_called()

    def test_october_reservation_drops_only_closing_privacy(self):
        plan=guard.owner_reservations(datetime.datetime(2026,10,26,tzinfo=datetime.timezone.utc))
        self.assertEqual({k:plan[k] for k in ('push','probe','qualification','closing_privacy')},
                         dict(push=6,probe=42,qualification=130,closing_privacy=0))
        self.assertEqual((plan['pre_push'],plan['before_probe'],plan['before_qualification']),(178,172,130))
        self.assertTrue(plan['merge_requires_privacy'])
        self.assertNotIn('closing_privacy_reservation',guard.PACKAGES['13'])

    def test_zero_closing_reservation_expires_and_restored_twelve_works(self):
        november=datetime.datetime(2026,11,1,tzinfo=datetime.timezone.utc)
        with self.assertRaisesRegex(AssertionError,'October2026 only'): guard.owner_reservations(november)
        changed=copy.deepcopy(guard.SETTINGS);changed['closing_privacy_reservation']['minutes']=12
        with patch.object(guard,'SETTINGS',changed):
            plan=guard.owner_reservations(november)
            self.assertEqual((plan['pre_push'],plan['before_probe'],plan['before_qualification']),(190,184,142))

    def test_missing_or_altered_closing_decision_refuses(self):
        for field,value in (('minutes',False),('minutes',-1),('minutes',6),('normal_minutes',0),
                             ('exception_month','2026-11'),('decision','unreviewed')):
            changed=copy.deepcopy(guard.SETTINGS);changed['closing_privacy_reservation'][field]=value
            with self.subTest(field=field,value=value),patch.object(guard,'SETTINGS',changed),self.assertRaises(AssertionError):
                guard.owner_reservations()
        changed=copy.deepcopy(guard.SETTINGS);changed.pop('closing_privacy_reservation')
        with patch.object(guard,'SETTINGS',changed),self.assertRaisesRegex(AssertionError,'missing closing'):
            guard.owner_reservations()

    def test_host_reservation_cannot_drop_probe_or_qualification_bound(self):
        for mode,reserve in (('probe',171),('owner-tools',129)):
            with self.subTest(mode=mode),patch.dict(os.environ,REHEARSAL_PACKAGE='14',clear=True), \
                 patch.object(sys,'argv',['rehearsal_guard.py',mode,str(reserve)]),patch.object(guard,'budget') as budget, \
                 self.assertRaisesRegex(AssertionError,'incomplete owner dispatch reservation'):
                guard.main()
            budget.assert_not_called()

    def test_new_head_requires_fresh_probe_and_owner_token_has_no_fallback(self):
        run=dict(event='workflow_dispatch',path='.github/workflows/os-image.yml',head_branch=guard.BRANCH,
                 head_sha='a'*40,display_title='Two-disk rehearsal (probe)',status='completed',conclusion='success')
        guard.require_probe(run,'a'*40)
        with self.assertRaisesRegex(AssertionError,'same harness commit'):guard.require_probe(run,'b'*40)
        env=dict(GITHUB_EVENT_NAME='workflow_dispatch',GITHUB_REPOSITORY=guard.REPOSITORY,GITHUB_REF_NAME=guard.BRANCH,
                 REHEARSAL_PACKAGE='14',REHEARSAL_MODE='owner-tools',GHCR_READ_TOKEN='SYNTHETIC-NOT-USED')
        with patch.dict(os.environ,env,clear=True),patch.object(registry_auth.legacy,'create') as legacy:
            with self.assertRaisesRegex(AssertionError,'no owner-token fallback'):registry_auth.create()
            legacy.assert_not_called()

    def test_pinned_qmp_contract_and_firmware_audit_are_not_widened(self):
        folder=ROOT/'os/manifest/ci/14/hotplug-sources'
        for source in json.loads((folder/'index.json').read_text()):
            self.assertIn('/qemu/qemu/v8.2.2/',source['url'])
            self.assertEqual(hashlib.sha256((folder/source['file']).read_bytes()).hexdigest(),source['sha256'])
        self.assertIn('qmp_set_link', (folder/'net_net.c').read_text())
        self.assertIn('ncs[i]->link_down = !up', (folder/'net_net.c').read_text())
        self.assertIn('ni->netdev = qemu_find_netdev(nd_id)', (folder/'net_net.c').read_text())
        self.assertIn('DEFINE_PROP_BOOL("removable", MSDState, removable, false)',(folder/'hw_usb_dev-storage-classic.c').read_text())
        self.assertIn("'command': 'blockdev-add'",(folder/'qapi_block-core.json').read_text())
        self.assertIn("'event': 'DEVICE_DELETED'",(folder/'qapi_qdev.json').read_text())
        self.assertIn("'id': 'owner-tools-usb'",(ROOT/'os/ci/owner_media.py').read_text())


if __name__=='__main__':unittest.main()
