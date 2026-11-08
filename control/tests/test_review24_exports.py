"""Post-publication failures retain the storage cause and rollback evidence."""
import errno
import os
from pathlib import Path
import stat
from unittest.mock import patch

from aresos_control.common import Refused, sha256
from aresos_control.files import FilePolicy
from support import EngineCase


class Exports24(EngineCase):
    def test_review24_published_export_enospc_keeps_disk_full_and_rollback_outcome(self):
        folder = self.root / 'Downloads'
        folder.mkdir()
        files = FilePolicy(str(self.root), [str(folder)])
        original_open, sync, link = os.open, os.fsync, os.link
        # macOS lacks O_TMPFILE and /proc; keep the pinned inode and production
        # publication/rollback code, substituting only those Linux primitives.
        inode = folder / 'synthetic-inode'
        def unnamed(path, flags, *args, **kwargs):
            if path == '.':
                return original_open(inode, os.O_CREAT | os.O_RDWR, 0o600)
            return original_open(path, flags, *args, **kwargs)
        def publish(source, target, **kwargs):
            link(inode, folder / target)
            inode.unlink()
        for rollback_fails in (False, True):
            with self.subTest(rollback_fails=rollback_fails):
                def fail(fd):
                    if stat.S_ISDIR(os.fstat(fd).st_mode):
                        raise OSError(errno.ENOSPC, 'Synthetic publication sync failure')
                    if rollback_fails and (folder / 'saved.bin').exists():
                        raise OSError(errno.EIO, 'Synthetic rollback sync failure')
                    return sync(fd)
                with patch('os.O_TMPFILE', 0, create=True), patch('os.open', side_effect=unnamed), \
                     patch('os.link', side_effect=publish), patch('os.fsync', side_effect=fail), \
                     patch.object(files, 'directory', side_effect=lambda _: original_open(folder, os.O_RDONLY)), \
                     patch.object(files, 'real_directory'), \
                     self.assertRaises(Refused) as caught:
                    files.save(str(folder), 'saved.bin', b'Synthetic export', sha256(b'Synthetic export'))
                self.assertEqual(caught.exception.code, 'storage_limit')
                self.assertIn('Disk full', str(caught.exception))
                self.assertIn('could not be confirmed' if rollback_fails else 'emptied and synced', str(caught.exception))
                self.assertEqual((folder / 'saved.bin').read_bytes(), b'')
                (folder / 'saved.bin').unlink()
