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
    def run_case(self, change):
        with tempfile.TemporaryDirectory(dir=common.ROOT/'os/tests') as temporary:
            root=pathlib.Path(temporary); usb=root/'usb'; usb.mkdir(); private=root/'private'; private.mkdir()
            payload=usb/'ares-tools'; common.bundle.build(payload)
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
            bins=root/'bin'; bins.mkdir()
            for name,script in {
                'mount': 'test "$1" = -o; test "$2" = ro,nodev,nosuid,noexec; test "$3" = LABEL=ARESTOOLS; rmdir "$4"; ln -s "$ARES_TEST_USB" "$4"',
                'umount': 'test -L "$1"; rm -- "$1"; mkdir "$1"',
            }.items():
                p=bins/name; p.write_text('#!/bin/bash\nset -eu\n'+script+'\n');p.chmod(0o700)
            words=shlex.split(bootstrap.command(fingerprint))
            self.assertEqual(words[:3],['sudo','bash','-c'])
            body=words[3].replace('/run/ares-bootstrap.XXXXXX',str(private/'ares-bootstrap.XXXXXX'))
            body=body.replace('export PATH=/usr/sbin:/usr/bin:/sbin:/bin','export PATH='+shlex.quote(str(bins))+':/usr/sbin:/usr/bin:/sbin:/bin')
            marker=root/'executed'
            result=subprocess.run(['/bin/bash','-c',body],env=dict(os.environ,ARES_TEST_USB=str(usb),ARES_PAYLOAD_MARKER=str(marker)),
                text=True,capture_output=True,timeout=15)
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

    def test_modified_at_never_executes(self): self.run_case('at')
    def test_modified_owner_never_executes(self): self.run_case('owner.py')
    def test_extra_file_never_executes(self):
        self.run_case('extra')
        self.run_case('root-link')
    def test_missing_file_never_executes(self): self.run_case('missing')
    def test_verified_private_copy_reaches_execution_boundary(self): self.run_case(None)

    def test_documented_command_is_generated_from_complete_system_manifest(self):
        import json
        fingerprint=common.bundle.check(common.ROOT/'os/owner-tools/payload')
        commands=json.loads((common.ROOT/'os/owner-tools/commands.json').read_text())
        self.assertEqual(commands['install'],bootstrap.command(fingerprint))
        self.assertIn(commands['install'],(common.ROOT/'docs/INSTALL.md').read_text())

if __name__=='__main__': unittest.main()
