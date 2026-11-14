"""Real bootstrap and harmless marker payload; only mount/unmount are stand-ins."""
import os
import pathlib
import shlex
import shutil
import subprocess
import tempfile
import unittest
import hashlib
import json

import test_owner_tools as common
bootstrap = common.module('bootstrap')


class BootstrapTest(unittest.TestCase):
    def run_case(self, change, source='stick'):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); usb=root/'usb'; usb.mkdir(); private=root/'private'; private.mkdir()
            # The folder source reads a local folder in place of the mounted stick (22c, addition 3).
            payload=usb/'ares-tools'; common.fixture_bundle(payload)
            # A harmless, executable payload fixture makes any early execute,
            # source or Python import observable, without touching the host.
            (payload/'at').write_text('#!/bin/bash\nprintf "%s\\n" "$PWD" > "$ARES_PAYLOAD_MARKER"\n/usr/bin/python3 -I -B ./owner.py\n')
            (payload/'owner.py').write_text('pass\n')
            rows=json.loads((payload/'SHA256.json').read_text())
            for row in rows:row['sha256']=hashlib.sha256((payload/row['path']).read_bytes()).hexdigest()
            raw=(json.dumps(rows,indent=2)+'\n').encode();(payload/'SHA256.json').write_bytes(raw)
            sums=''.join(x['sha256']+'  '+x['path']+'\n' for x in rows)+hashlib.sha256(raw).hexdigest()+'  SHA256.json\n'
            (payload/'SHA256SUMS').write_text(sums)
            fingerprint=hashlib.sha256(sums.encode()).hexdigest()
            if change=='at':(payload/'at').write_text('#!/bin/bash\necho EARLY > "$ARES_PAYLOAD_MARKER"\nexit 99\n')
            elif change=='owner.py':(payload/'owner.py').write_text('import os,pathlib\npathlib.Path(os.environ["ARES_PAYLOAD_MARKER"]).write_text("EARLY")\nraise SystemExit(99)\n')
            elif change=='extra': (payload/'extra').write_text('unexpected')
            elif change=='missing': (payload/'owner.py').unlink()
            elif change=='root-link':
                other=usb/'real-tools';payload.rename(other)
                payload.symlink_to(other,target_is_directory=True)
            elif change=='inner-link':
                # A link to a file with exactly the expected bytes still refuses: links never pass.
                outside=root/'release.json';(payload/'release.json').rename(outside)
                (payload/'release.json').symlink_to(outside)
            elif change=='special':
                # A FIFO in a listed file's place: refused before anything reads it (a read would hang).
                (payload/'release.json').unlink();os.mkfifo(payload/'release.json')
            elif change=='fingerprint':
                fingerprint=hashlib.sha256(b'another bundle').hexdigest()
            before=self.snapshot(usb)
            bins=root/'bin'; bins.mkdir()
            mounts=root/'mounts'
            fakes={
                'mount': 'test "$1" = -o; test "$2" = ro,nodev,nosuid,noexec; test "$3" = LABEL=ARESTOOLS; rmdir "$4"; ln -s "$ARES_TEST_USB" "$4"',
                'umount': 'test -L "$1"; rm -- "$1"; mkdir "$1"',
            } if source=='stick' else {
                # The folder block never mounts anything.
                'mount': 'echo mount >> "$ARES_TEST_MOUNTS"; exit 97', 'umount': 'echo umount >> "$ARES_TEST_MOUNTS"; exit 97',
            }
            for name,script in fakes.items():
                p=bins/name; p.write_text('#!/bin/bash\nset -eu\n'+script+'\n');p.chmod(0o700)
            words=shlex.split(bootstrap.command(fingerprint,source))
            self.assertEqual(words[:3],['sudo','bash','-c'])
            body=words[3].replace('/run/ares-bootstrap.XXXXXX',str(private/'ares-bootstrap.XXXXXX'))
            body=body.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin','export PATH='+shlex.quote(str(bins))+':/usr/sbin:/usr/bin:/sbin:/bin')
            if source=='folder':
                self.assertEqual(body.count(bootstrap.FOLDER),1)
                body=body.replace(bootstrap.FOLDER,shlex.quote(str(payload)))
            marker=root/'executed'
            result=subprocess.run(['/bin/bash','-c',body],env=dict(os.environ,ARES_TEST_USB=str(usb),ARES_PAYLOAD_MARKER=str(marker),
                ARES_TEST_MOUNTS=str(mounts)),text=True,capture_output=True,timeout=15)
            if change:
                self.assertNotEqual(result.returncode,0)
                self.assertIn('STOP bootstrap',result.stdout)
                self.assertFalse(marker.exists(),'Payload execution occurred before verification')
            else:
                self.assertEqual(result.returncode,0,result.stderr)
                executed=pathlib.Path(marker.read_text().strip())
                self.assertTrue(executed.is_relative_to(private))
                self.assertNotEqual(executed,payload)
                self.assertEqual((executed/'at').read_bytes(),(payload/'at').read_bytes())
            self.assertTrue(all(not (p/'m').is_symlink() for p in private.iterdir()),'Bootstrap left the stick mounted')
            self.assertFalse(mounts.exists(),'The folder block mounted something')
            # The source is only read: the stick or the folder is left exactly as it was.
            self.assertEqual(self.snapshot(usb),before)

    @staticmethod
    def snapshot(folder):
        def state(p):
            if p.is_symlink(): return 'link', os.readlink(p)
            if p.is_fifo(): return 'fifo', None
            return ('file', p.read_bytes()) if p.is_file() else ('dir', oct(p.stat().st_mode))
        return {p.relative_to(folder).as_posix(): state(p) for p in sorted(folder.rglob('*'))}

    def both(self, *changes):
        for source in bootstrap.SOURCES:
            for change in changes:
                with self.subTest(source=source, change=change):
                    self.run_case(change, source)

    def test_modified_at_never_executes(self): self.both('at')
    def test_modified_owner_never_executes(self): self.both('owner.py')
    def test_extra_file_never_executes(self): self.both('extra', 'root-link')
    def test_missing_file_never_executes(self): self.both('missing')
    def test_verified_private_copy_reaches_execution_boundary(self): self.both(None)
    # Addition 3: links, special files and a wrong fingerprint refuse from either source.
    def test_links_special_files_and_a_wrong_fingerprint_never_execute(self): self.both('inner-link', 'special', 'fingerprint')

    def test_the_two_blocks_differ_in_exactly_their_source_lines(self):
        fingerprint = 'a' * 64
        stick, folder = (bootstrap.command(fingerprint, source) for source in ('stick', 'folder'))
        stick_body, folder_body = (shlex.split(block)[3].splitlines() for block in (stick, folder))
        self.assertEqual(stick_body[:3], folder_body[:3])
        self.assertEqual(stick_body[3:6], bootstrap.source_lines('stick'))
        self.assertEqual(folder_body[3:5], bootstrap.source_lines('folder'))
        self.assertEqual(stick_body[6:], folder_body[5:])
        self.assertEqual((len(stick.splitlines()), len(folder.splitlines())), (13, 12))
        self.assertEqual(bootstrap.command(fingerprint), stick)  # the stick stays the default, byte for byte
        for word in ('mount', 'LABEL=', 'ARESTOOLS', 'umount'):
            self.assertNotIn(word, folder)
        self.assertEqual(folder.count(bootstrap.FOLDER + ' .;'), 1)
        self.assertTrue(all(len(line) < 120 for line in folder.splitlines()))
        with self.assertRaisesRegex(ValueError, 'Unknown bundle source'):
            bootstrap.command(fingerprint, 'network')

    def test_documented_command_is_generated_from_complete_system_manifest(self):
        import json
        fingerprint=common.bundle.check(common.ROOT/'os/owner-tools/payload')
        commands=json.loads((common.ROOT/'os/owner-tools/commands.json').read_text())
        self.assertEqual(commands['install'],bootstrap.command(fingerprint))
        self.assertIn(commands['install'],(common.ROOT/'docs/INSTALL.md').read_text())

if __name__=='__main__': unittest.main()
