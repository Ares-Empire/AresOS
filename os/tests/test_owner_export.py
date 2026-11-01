import importlib.util
import json
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import test_owner_tools as common
media=common.module('media')
owner=common.owner


class ExportTest(unittest.TestCase):
    def test_readonly_refusals_and_success_unmount_with_private_records_only(self):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as directory:
            root=pathlib.Path(directory)
            usb=root/'usb';usb.mkdir()
            fingerprint=common.bundle.build(usb/'ares-tools')
            store=root/'records';store.mkdir()
            (store/'prepared.json').write_text('{"passed":true}')
            diagnostics=root/'diagnostics'
            failure=dict(status='stopped',command=['records'],error='fixture refusal',trace=[])
            with patch.object(owner,'STOP_RECORDS',diagnostics),patch.object(owner.os,'geteuid',return_value=0),common.private_metadata(root):
                owner.refusal_record(SimpleNamespace(read=lambda *args:'retained firmware fixture',trace=[]),failure)
            diagnostic,=diagnostics.glob('*.json')
            mount=root/'mount'
            calls=[]
            class Host:
                mounted=False
                def json(self,*args):
                    return dict(blockdevices=[dict(path='/dev/SYNTHETIC',type='disk',tran='usb',rm=True,mountpoints=[None],children=[dict(path='/dev/SYNTHETIC1',
                        type='part',label='ARESTOOLS',fstype='exfat',uuid='synthetic',mountpoints=[str(mount)] if self.mounted else [None])])])
                def mutate(self,*args):
                    calls.append(args)
                    assert usb.resolve().is_relative_to(root.resolve()) and mount.resolve().is_relative_to(root.resolve())
                    if args[0]=='mount':
                        mount.rmdir();usb.rename(mount);self.mounted=True
                    elif args[0]=='umount':
                        mount.rename(usb);mount.mkdir();self.mounted=False
                    elif args[0]!='sync':raise AssertionError(args)
            host=Host()
            def export(): return media.export(host,store,fingerprint,owner.checked_bundle,owner.require)
            with patch.object(media,'MOUNT',mount):
                original=(usb/'ares-tools/at').read_bytes()
                (usb/'ares-tools/at').write_bytes(b'BAD')
                with self.assertRaises(owner.Stop):export()
                self.assertFalse(host.mounted)
                self.assertFalse(any(c[0]=='mount' and '--read-only' not in c for c in calls))
                self.assertFalse((usb/'ares-records').exists())
                (usb/'ares-tools/at').write_bytes(original)
                target=usb/'ares-records';target.mkdir();(target/'prepared.json').write_text('DIFFERENT')
                calls.clear()
                with self.assertRaisesRegex(owner.Stop,'immutable'):export()
                self.assertEqual((target/'prepared.json').read_text(),'DIFFERENT')
                self.assertFalse(any(c[0]=='mount' and '--read-only' not in c for c in calls))
                (target/'prepared.json').unlink()
                result=export()
                self.assertIn('SAFE TO REMOVE',result[-1])
                self.assertFalse(host.mounted)
                self.assertEqual((target/'prepared.json').read_bytes(),(store/'prepared.json').read_bytes())
                exported=target/('diagnostic-'+diagnostic.name)
                self.assertEqual(set(p.name for p in target.iterdir()),{'prepared.json',exported.name})
                self.assertEqual(exported.read_bytes(),diagnostic.read_bytes())
                # Reboot model: discard volatile state, create fresh readers;
                # both the persistent internal record and off-device copy stay.
                volatile=root/'run';volatile.mkdir();(volatile/'discarded').write_text('volatile')
                (volatile/'discarded').unlink();volatile.rmdir()
                self.assertEqual(json.loads(diagnostic.read_text())['status'],'stopped')
                self.assertEqual(json.loads(exported.read_text())['error'],'fixture refusal')

    def test_bad_usb_identity_never_mounts(self):
        for bad in (dict(tran='nvme'),dict(rm=False),dict(fstype='ntfs'),dict(uuid='')):
            class Host:
                def json(self,*args):
                    disk=dict(path='/dev/SYNTHETIC',type='disk',tran='usb',rm=True,mountpoints=[None])
                    volume=dict(path='/dev/SYNTHETIC1',type='part',label='ARESTOOLS',fstype='exfat',uuid='known',mountpoints=[None])
                    disk.update({k:v for k,v in bad.items() if k in ('tran','rm')})
                    volume.update({k:v for k,v in bad.items() if k not in ('tran','rm')})
                    return dict(blockdevices=[dict(disk,children=[volume])])
            with self.subTest(bad=bad),self.assertRaises(owner.Stop): media.find(Host(),owner.require)


if __name__=='__main__':unittest.main()
