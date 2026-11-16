import hashlib
import json
import os
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
            def export(): return media.export(host,store,[fingerprint],owner.checked_bundle,owner.require)
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

    @staticmethod
    def other_bundle(destination):
        """Another complete bundle: the fixture's bytes with one file changed and its manifests regenerated."""
        common.fixture_bundle(destination)
        with (destination / 'media.py').open('a') as stream:
            stream.write('# another version\n')
        rows = json.loads((destination / 'SHA256.json').read_text())
        for row in rows:
            row['sha256'] = hashlib.sha256((destination / row['path']).read_bytes()).hexdigest()
        raw = (json.dumps(rows, indent=2) + '\n').encode()
        sums = ''.join(row['sha256'] + '  ' + row['path'] + '\n' for row in rows) + hashlib.sha256(raw).hexdigest() + '  SHA256.json\n'
        (destination / 'SHA256.json').write_bytes(raw)
        (destination / 'SHA256SUMS').write_text(sums)
        return owner.checked_bundle(destination)

    def test_a_stick_with_tools_this_laptop_installed_before_takes_records_and_a_foreign_one_does_not(self):
        """22d, decision 6: after stick-free updates the stick in the drawer holds older tools."""
        with tempfile.TemporaryDirectory(dir=common.ROOT / 'os/tests') as directory:
            root = pathlib.Path(directory)
            usb, mount, store = root / 'usb', root / 'mount', root / 'records'
            usb.mkdir(); mount.mkdir(); store.mkdir()
            installed = common.fixture_bundle(root / 'installed')
            on_stick = self.other_bundle(usb / 'ares-tools')
            self.assertNotEqual(installed, on_stick)
            (store / 'prepared.json').write_text('{"passed":true}')
            calls = []
            class Host:
                where = None  # the folder the stick is mounted at
                def json(self, *args):
                    return dict(blockdevices=[dict(path='/dev/SYNTHETIC', type='disk', tran='usb', rm=True, mountpoints=[None], children=[dict(
                        path='/dev/SYNTHETIC1', type='part', label='ARESTOOLS', fstype='exfat', uuid='synthetic', mountpoints=[self.where])])])
                def mutate(self, *args):
                    calls.append(args)
                    if args[0] == 'mount':
                        mount.rmdir(); usb.rename(mount); self.where = str(mount)
                    elif args[0] == 'umount':
                        pathlib.Path(args[-1]).rename(usb); mount.mkdir(exist_ok=True); self.where = None
                    elif args[0] != 'sync':
                        raise AssertionError(args)
            host = Host()
            def export(accepted): return media.export(host, store, accepted, owner.checked_bundle, owner.require, 1001)
            with patch.object(media, 'MOUNT', mount):
                for accepted in ([installed], [installed, 'f' * 64]):
                    with self.subTest(accepted=len(accepted)):
                        calls.clear()
                        with self.assertRaisesRegex(owner.Stop, '^Tools manifest differs; do not copy records$'):
                            export(accepted)
                        self.assertIsNone(host.where)
                        self.assertFalse(any(c[0] == 'mount' and '--read-only' not in c for c in calls))
                        self.assertFalse((usb / 'ares-records').exists())
                self.assertEqual(export([installed, 'f' * 64, on_stick]), [
                    'Records copied with SHA256 readback',
                    'The stick holds tools this laptop installed before (SHA256 ' + on_stick + '), not the installed ones',
                    'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart'])
                self.assertIsNone(host.where)
                self.assertEqual((usb / 'ares-records/prepared.json').read_bytes(), (store / 'prepared.json').read_bytes())
                self.assertEqual(owner.checked_bundle(usb / 'ares-tools'), on_stick)
                # The same stick found mounted somewhere: accepted or refused by the same rule, before anything is unmounted.
                elsewhere = root / 'elsewhere'
                usb.rename(elsewhere); host.where = str(elsewhere); calls.clear()
                with self.assertRaisesRegex(owner.Stop, '^Mounted tools bundle differs$'):
                    export([installed])
                self.assertEqual(calls, [])
                self.assertEqual(export([installed, on_stick])[-1], 'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart')
                # The installed tools on the stick: the two lines as before, no third.
                shutil.rmtree(usb / 'ares-tools')
                common.fixture_bundle(usb / 'ares-tools')
                self.assertEqual(export([installed, on_stick]), ['Records copied with SHA256 readback',
                                                                 'SAFE TO REMOVE ARESTOOLS; unplug before every shutdown/restart'])

    def test_without_a_stick_a_checked_copy_stays_on_this_laptop_and_the_message_says_so(self):
        """22d, decision 6: a root-owned folder under /run that only the calling login uid is let into."""
        with tempfile.TemporaryDirectory(dir=common.ROOT / 'os/tests') as directory:
            root = pathlib.Path(directory)
            store, diagnostics, local = root / 'records', root / 'diagnostics', root / 'run/ares-records'
            store.mkdir(); diagnostics.mkdir(); local.parent.mkdir()
            (store / 'prepared.json').write_text('{"passed":true}')
            (store / 'title.json').write_text('{"title":1}')
            (diagnostics / '20261115T000000.000000Z-install.json').write_text('{"status":"stopped"}')
            calls = []
            class Host:
                def json(self, *args): return dict(blockdevices=[])
                def mutate(self, *args): calls.append(args)
            def export(reader): return media.export(Host(), store, ['a' * 64], owner.checked_bundle, owner.require, reader)
            def copied(): return {p.name: p.read_bytes() for p in local.iterdir()}
            with patch.object(media, 'LOCAL', local), patch.object(media, 'MOUNT', root / 'never-mounted'):
                lines = export(1001)
                self.assertEqual(lines, ['Tools stick absent: records copied to ' + str(local) + ' with SHA256 readback',
                                         'This copy is on this laptop, not off it; uid 1001 can read it, and a restart deletes it',
                                         'For a copy off the laptop plug in the tools stick and run export again'])
                # Only a stick export may say the words that prove a copy off the laptop.
                self.assertFalse(any('SAFE TO REMOVE' in line or 'ARESTOOLS' in line for line in lines))
                self.assertEqual(copied(), {'prepared.json': b'{"passed":true}', 'title.json': b'{"title":1}',
                                            'diagnostic-20261115T000000.000000Z-install.json': b'{"status":"stopped"}'})
                # Root's own folder and files, closed to everyone; then exactly one grant, to the caller, after the copies.
                self.assertEqual(local.stat().st_mode & 0o7777, 0o700)
                self.assertEqual({p.stat().st_mode & 0o7777 for p in local.iterdir()}, {0o600})
                self.assertEqual(calls, [('setfacl', '--recursive', '--modify', 'user:1001:rX', '--', str(local))])
                self.assertFalse((root / 'never-mounted').exists())
                # A later export replaces the folder whole: exactly today's records, for today's caller.
                (store / 'title.json').unlink()
                (store / 'later.json').write_text('{}')
                for reader in (None, 0):
                    calls.clear()
                    self.assertEqual(export(reader)[1], 'This copy is on this laptop, not off it; only root can read it, and a restart deletes it')
                    self.assertEqual(calls, [])
                    self.assertEqual(set(copied()), {'prepared.json', 'later.json', 'diagnostic-20261115T000000.000000Z-install.json'})
                # Anything that is not an earlier export's folder is left alone.
                before = copied()
                (local / 'folder').mkdir()
                with self.assertRaisesRegex(owner.Stop, '^Local records folder is not an earlier export; preserve it and get help$'):
                    export(1001)
                (local / 'folder').rmdir()
                with patch.object(media.os, 'geteuid', return_value=os.geteuid() + 1), self.assertRaisesRegex(owner.Stop, 'not an earlier export'):
                    export(1001)
                self.assertEqual(copied(), before)
                elsewhere = root / 'elsewhere'
                local.rename(elsewhere); local.symlink_to(elsewhere)
                with self.assertRaisesRegex(owner.Stop, 'not an earlier export'):
                    export(1001)
                self.assertTrue(local.is_symlink())
                self.assertEqual({p.name: p.read_bytes() for p in elsewhere.iterdir()}, before)
                self.assertEqual(calls, [])
                # A copy that reads back differently stops before anyone is let in.
                local.unlink()
                real = shutil.copyfile
                def damaged(source, target):
                    real(source, target)
                    pathlib.Path(target).write_bytes(b'damaged')
                with patch.object(media.shutil, 'copyfile', side_effect=damaged), self.assertRaisesRegex(owner.Stop, '^Local record copy differs$'):
                    export(1001)
                self.assertEqual(calls, [])
                # Review 2, N4: a missing or failing setfacl leaves the complete copy root's and says why, through
                # the real Host's own refusals; never a STOP, never "do not reboot".
                class Real(owner.Host):
                    def json(self, *args): return dict(blockdevices=[])
                failed = subprocess.CompletedProcess(['setfacl'], 1, '', 'setfacl: Operation not supported')
                for which, ran, reason in ((None, None, 'Required tool missing: setfacl'),
                                           ('/usr/bin/setfacl', failed, 'Operation failed: setfacl'),
                                           ('/usr/bin/setfacl', OSError(8, 'Exec format error'), '[Errno 8] Exec format error')):
                    with self.subTest(reason=reason), patch.object(owner.shutil, 'which', return_value=which), \
                            patch.object(owner.subprocess, 'run', side_effect=[ran]) as started:
                        lines = media.export(Real(), store, ['a' * 64], owner.checked_bundle, owner.require, 1001)
                        self.assertEqual(lines, ['Tools stick absent: records copied to ' + str(local) + ' with SHA256 readback',
                                                 'This copy is on this laptop, not off it; only root can read it, since uid 1001 '
                                                 'could not be let in (' + reason + '), and a restart deletes it',
                                                 'For a copy off the laptop plug in the tools stick and run export again'])
                        self.assertFalse(any('reboot' in line for line in lines))
                        self.assertEqual(started.call_count, 0 if which is None else 1)
                        self.assertEqual(set(copied()), {'prepared.json', 'later.json', 'diagnostic-20261115T000000.000000Z-install.json'})
                        self.assertEqual(local.stat().st_mode & 0o7777, 0o700)
                        self.assertEqual({p.stat().st_mode & 0o7777 for p in local.iterdir()}, {0o600})
        self.assertEqual(media.LOCAL, pathlib.Path('/run/ares-records'))

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

    def test_real_export_without_a_stick_leaves_the_copy_on_this_laptop_and_never_claims_more(self):
        """22d: the real entry in a fresh process, no stick plugged in, called from a login without a terminal."""
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as directory:
            root = pathlib.Path(directory).resolve()
            home, volatile = root/'var/lib/ares', root/'run'
            self.copy_bundle(home/'tools', self.bundle_source)
            (home/'records').mkdir()
            (home/'records/prepared.json').write_text('{"passed":true}')
            volatile.mkdir()
            (root/'proc/self').mkdir(parents=True)
            runner = common.ROOT/'os/tests/owner_export_fixture.py'

            def entry(*args):
                result = subprocess.run([sys.executable, '-I', '-B', str(runner), str(root), *args],
                                        text=True, capture_output=True, timeout=30, stdin=subprocess.DEVNULL)
                self.assertEqual(result.stderr, '', result.stderr)
                return result

            self.assertEqual(entry('records', 'unexpected').returncode, 1)
            diagnostic, = (home/'diagnostics').glob('*.json')
            local = volatile/'ares-records'
            for login, reader in (('1001\n', 'uid 1001'), ('4294967295\n', 'only root')):
                (root/'proc/self/loginuid').write_text(login)
                (root/'host-calls.jsonl').unlink(missing_ok=True)
                # Every private record and diagnostic present when the export runs (its own record comes after the copy).
                expected = {p.name: p.read_bytes() for p in (home/'records').glob('*.json')}
                expected['diagnostic-' + diagnostic.name] = diagnostic.read_bytes()
                exported = entry('export')
                self.assertEqual(exported.returncode, 0, exported.stdout)
                self.assertEqual(exported.stdout.splitlines(), [
                    'PASS export',
                    'Tools stick absent: records copied to ' + str(local) + ' with SHA256 readback',
                    'This copy is on this laptop, not off it; ' + reader + ' can read it, and a restart deletes it',
                    'For a copy off the laptop plug in the tools stick and run export again',
                    'Full diagnostics: /var/lib/ares/records (private)'])
                self.assertNotIn('SAFE TO REMOVE', exported.stdout)
                looked, *grants = [json.loads(line) for line in (root/'host-calls.jsonl').read_text().splitlines()]
                self.assertEqual(looked[0], '/usr/bin/lsblk')
                self.assertEqual(grants, [['/usr/bin/setfacl', '--recursive', '--modify', 'user:1001:rX', '--', str(local)]]
                                 if reader == 'uid 1001' else [])
                # Byte for byte, nothing else, nothing mounted.
                self.assertEqual({p.name: p.read_bytes() for p in local.iterdir()}, expected)
                self.assertIn('prepared.json', expected)
                self.assertFalse((volatile/'ares-tools-media').exists())
            self.assertEqual(len(list((home/'records').glob('*-export.json'))), 2)


if __name__=='__main__':unittest.main()
