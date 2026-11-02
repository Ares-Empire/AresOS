import json
import pathlib
import shutil
import subprocess
import sys
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
            fingerprint=common.fixture_bundle(usb/'ares-tools')
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


class ExportSurvivalTest(unittest.TestCase):
    bundle_source = common.ROOT / 'os/owner-tools/payload'
    copy_bundle = staticmethod(common.fixture_bundle)

    def test_real_stop_export_reboot_and_fresh_export_preserve_exact_diagnostic(self):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as directory:
            root = pathlib.Path(directory).resolve()
            home, volatile, stick = root/'var/lib/ares', root/'run', root/'fixture-stick'
            self.copy_bundle(home/'tools', self.bundle_source)
            self.copy_bundle(stick/'ares-tools', self.bundle_source)
            (home/'records').mkdir()
            volatile.mkdir()
            (volatile/'must-disappear').write_bytes(b'old boot state')
            runner = common.ROOT/'os/tests/owner_export_fixture.py'

            def entry(*args):
                # A fresh interpreter runs the real __main__ block each time;
                # -I -B is also the production at launcher's invocation mode.
                result = subprocess.run([sys.executable, '-I', '-B', str(runner), str(root), *args],
                                        text=True, capture_output=True, timeout=30)
                self.assertEqual(result.stderr, '', result.stderr)
                return result

            stop = entry('records', 'unexpected')
            self.assertEqual(stop.returncode, 1, stop.stdout)
            self.assertIn('STOP: Unexpected arguments;', stop.stdout)
            self.assertNotIn('PASS ', stop.stdout)
            written = list(root.rglob('*-records.json'))
            self.assertEqual(len(written), 1, 'Controlled STOP must actually save a diagnostic')
            self.assertEqual(json.loads(written[0].read_bytes())['status'], 'stopped')
            diagnostics = list((home/'diagnostics').glob('*.json'))
            self.assertEqual(len(diagnostics), 1,
                             'STOP diagnostic missing from persistent /var/lib/ares/diagnostics')
            diagnostic, = diagnostics
            original = diagnostic.read_bytes()
            record = json.loads(original)
            self.assertEqual(record['status'], 'stopped')
            self.assertEqual(record['command'], ['records'])
            self.assertTrue(record['error'].startswith('Unexpected arguments;'))
            self.assertTrue(record['firmware']['observed'])
            self.assertEqual(list(volatile.rglob('*.json')), [])
            self.assertEqual(list((home/'records').iterdir()), [])
            calls = [json.loads(line) for line in (root/'host-calls.jsonl').read_text().splitlines()]
            self.assertEqual(calls, [['/usr/bin/efibootmgr', '-v']])

            for rebooted in (False, True):
                if rebooted:
                    # All tool processes have exited. Remove the ENTIRE /run
                    # tree, including the real media.MOUNT, not a dummy file.
                    self.assertTrue((volatile/'ares-tools-media').is_dir())
                    shutil.rmtree(volatile)
                    self.assertFalse(volatile.exists())
                    volatile.mkdir()
                    self.assertEqual(list(volatile.iterdir()), [])
                    self.assertEqual(copy.read_bytes(), original)
                exported = entry('export')
                self.assertEqual(exported.returncode, 0, exported.stdout)
                self.assertIn('PASS export\n', exported.stdout)
                self.assertIn('Records copied with SHA256 readback', exported.stdout)
                self.assertIn('SAFE TO REMOVE ARESTOOLS', exported.stdout)
                copy = stick/'ares-records'/('diagnostic-' + diagnostic.name)
                self.assertEqual(copy.read_bytes(), original)
                self.assertEqual(diagnostic.read_bytes(), original)
                self.assertEqual(list((volatile/'ares-tools-media').iterdir()), [])
                if rebooted:
                    self.assertFalse((volatile/'must-disappear').exists())
            self.assertEqual(list((home/'diagnostics').glob('*.json')), [diagnostic])
            self.assertEqual(len(list((home/'records').glob('*-export.json'))), 2)


if __name__=='__main__':unittest.main()
