import copy
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import keyboard_entries as ke
import keyboard_vm as vm


class KeyboardEntriesTest(unittest.TestCase):
    def snapshot(self):
        root=ROOT/'os/tests/fixtures/keyboard'
        rpm=json.loads((root/'stock-two-rpm.json').read_text())
        bootc=json.loads((root/'stock-two-bootc.json').read_text())
        return dict(rpm=rpm,bootc=bootc,bls=[self.bls(d) for d in rpm['deployments']])

    def bls(self,d):
        return dict(deployment='/sysroot/ostree/deploy/'+d['osname']+'/deploy/'+d['checksum']+'.'+str(d['serial']),
                    content='options rw ostree=/ostree/link vconsole.keymap=de\n')

    def pair(self):
        snapshot=self.snapshot(); stock=copy.deepcopy(snapshot['rpm']['deployments'][0])
        stock.update(pinned=True,booted=False)
        image=dict(stock,checksum='b'*64,serial=0,pinned=False,booted=True,**{'container-image-reference-digest':'sha256:'+'c'*64})
        snapshot['rpm']['deployments']=[image,stock]
        snapshot['bls']=[self.bls(d) for d in (image,stock)]
        for name,d in (('booted',image),('rollback',stock)):
            snapshot['bootc']['status'][name]['ostree'].update(checksum=d['checksum'],deploySerial=d['serial'])
            snapshot['bootc']['status'][name]['pinned']=d['pinned']
        return snapshot,stock,'ghcr.io/ares-empire/aresos@sha256:'+'c'*64

    def test_retained_plus_letter_rows_and_source_derived_us_are_layout_sensitive(self):
        for layout in ('de','us'):
            text=(ROOT/'os/tests/fixtures/keyboard'/f'{layout}-dumpkeys.txt').read_text()
            vm.loaded_map(text,layout)
            vm.loaded_map(text.replace('+',''),layout)
            for bad in (text.replace('+','++'), text.replace('+z','+zz'),text+'keycode 21 = +y\n',text.replace('keycode  44','keycode  45')):
                with self.subTest(layout=layout,bad=bad),self.assertRaises(AssertionError):
                    vm.loaded_map(bad,layout)
            with self.assertRaises(AssertionError):
                vm.loaded_map(text,'us' if layout=='de' else 'de')

    def test_nonbooted_entry_is_preserved_and_resolved_by_full_identity(self):
        before=self.snapshot();after=copy.deepcopy(before)
        after['bls'][0]['content']='options rw ostree=/ostree/newlink\n'
        ke.unchanged_old(before,after)
        after['bls'][1]['content']='options rw ostree=/ostree/newlink\n'
        with self.assertRaisesRegex(AssertionError,'non-booted'):
            ke.unchanged_old(before,after)
        for change in ('duplicate','missing','unresolved'):
            bad=copy.deepcopy(before)
            if change=='duplicate':bad['bls'].append(bad['bls'][0])
            elif change=='missing':bad['bls'].pop()
            else:bad['bls'][0]['deployment']='/boot/ostree-2.conf'
            with self.subTest(change=change),self.assertRaises(AssertionError):ke.entries(bad)

    def test_final_pair_rejects_surviving_old_stock_and_checks_rollback_identities(self):
        pair,stock,release=self.pair()
        ke.retained_pair(pair,stock,release)
        queued=copy.deepcopy(pair);queued['bootc']['status']['rollbackQueued']=True
        ke.retained_pair(queued,stock,release,queued=True)
        rolled=copy.deepcopy(pair)
        rolled['rpm']['deployments'].reverse()
        for d in rolled['rpm']['deployments']:d['booted']=ke.key(d)==ke.key(stock)
        rolled['bootc']['status']['booted'],rolled['bootc']['status']['rollback']=rolled['bootc']['status']['rollback'],rolled['bootc']['status']['booted']
        ke.retained_pair(rolled,stock,release)
        for change in ('old','unpinned','serial','digest','queued'):
            bad=copy.deepcopy(pair)
            if change=='old':bad['rpm']['deployments'].append(self.snapshot()['rpm']['deployments'][1])
            elif change=='unpinned':bad['rpm']['deployments'][1]['pinned']=False
            elif change=='serial':bad['bootc']['status']['rollback']['ostree']['deploySerial']=0
            elif change=='digest':bad['rpm']['deployments'][0]['container-image-reference-digest']='other'
            else:bad['bootc']['status']['rollbackQueued']=True
            with self.subTest(change=change),self.assertRaises(AssertionError):ke.retained_pair(bad,stock,release)

    def test_raw_statuses_are_exported_before_a_snapshot_decision_can_fail(self):
        guest=Mock();guest.capture_json.side_effect=[{'deployments':[]},{'status':{}},[{'deployment':'unresolved'}]]
        with patch.object(vm.td,'save') as save,self.assertRaises(AssertionError):vm.deployment_snapshot(guest,'before-repair')
        self.assertEqual([c.args[0] for c in guest.capture_json.call_args_list],['before-repair-rpm-ostree-status','before-repair-bootc-status','before-repair-resolved-bls'])
        save.assert_called_once()


if __name__=='__main__':unittest.main()
