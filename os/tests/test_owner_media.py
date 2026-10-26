import contextlib
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_media
import owner_fuse
from owner_fuse_shim import Volume


class MediaFuseTest(unittest.TestCase):
    @contextlib.contextmanager
    def fixture(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary, contextlib.ExitStack() as stack:
            root=pathlib.Path(temporary).resolve(); (root/'evidence').mkdir()
            stack.enter_context(patch.dict(os.environ,GITHUB_ACTIONS='true',GITHUB_REPOSITORY='Ares-Empire/AresOS',
                GITHUB_REF_NAME='pkg/14-owner-tools',REHEARSAL_PACKAGE='14'))
            stack.enter_context(patch.object(owner_media.td,'WORK',root))
            stack.enter_context(patch.object(owner_media.td,'EVIDENCE',root/'evidence'))
            media=owner_media.Media(); volume=Volume(root,media.mount)
            stack.enter_context(patch.object(subprocess,'run',side_effect=volume.run))
            stack.enter_context(patch.object(subprocess,'check_output',side_effect=volume.output))
            yield media,volume

    def test_clean_fsck_readonly_every_file_check_precedes_backing_hash(self):
        with self.fixture() as (media,volume),patch.object(owner_media,'digest',wraps=owner_media.digest) as hashed:
            media.create()
            commands=[c[0] for c in volume.calls]
            self.assertEqual(commands.count('mount.exfat-fuse'),2)
            self.assertEqual(commands.count('fsck.exfat'),1)
            self.assertLess(commands.index('pwsh'),commands.index('fsck.exfat'))
            self.assertLess(commands.index('fsck.exfat'),len(commands)-1)
            self.assertEqual(volume.calls[-1],['losetup','--detach',volume.loop])
            self.assertFalse(volume.active); hashed.assert_called_once_with(media.path)
            self.assertIsNotNone(media.expected)
            self.assertIn('--read-only',next(c for c in volume.calls if c[0]=='losetup' and '--read-only' in c))

    def test_wrong_driver_format_source_and_flags_refuse_before_copy(self):
        for name,value in (('fstype','exfat'),('kind','ntfs'),('source','/dev/WRONG'),('bad_flags',True)):
            with self.subTest(name=name),self.fixture() as (media,volume):
                setattr(volume,name,value)
                with self.assertRaises(AssertionError):media.create()
                self.assertFalse(any(c[0]=='pwsh' for c in volume.calls))
                self.assertIsNone(media.expected)

    def test_fsck_failure_and_tampered_readback_never_authorize_attach(self):
        for name in ('fsck_failure','corrupt'):
            with self.subTest(name=name),self.fixture() as (media,volume):
                setattr(volume,name,True)
                error = ValueError if name == 'corrupt' else subprocess.CalledProcessError
                with self.assertRaises(error):media.create()
                self.assertIsNone(media.expected); self.assertFalse(volume.active)

    def test_incomplete_unmount_never_detaches_loop_or_hashes(self):
        with self.fixture() as (media,volume):
            volume.linger=True
            with self.assertRaisesRegex(AssertionError,'unmount did not complete'):media.create()
            self.assertFalse(any(c[:2]==['losetup','--detach'] for c in volume.calls))
            self.assertIsNone(media.expected)

    def test_unreadable_mount_state_refuses(self):
        for code,text,stderr in ((2,'',''),(1,'unexpected',''),(0,'{"filesystems":[]}',''),
                                 (1,'','synthetic unreadable mount table')):
            result=subprocess.CompletedProcess([],code,text,stderr)
            with self.subTest(code=code),patch.object(subprocess,'run',return_value=result),self.assertRaises(AssertionError):
                owner_fuse.mounts('--source','/dev/SYNTHETIC')


if __name__=='__main__':unittest.main()
