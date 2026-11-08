"""Review 13: production exports/evidence, with offline I/O fault injection."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control.common import Refused, sha256
from aresos_control.files import FilePolicy
from aresos_control.proxy import Proxy
from aresos_control import exports
import test_review_fixes_19 as round19
import test_review_fixes_20 as round20


@contextmanager
def failing_stream(mode):
    original = os.fdopen
    class Writer:
        def __init__(self, stream):
            self.stream = stream
        def __getattr__(self, key):
            return getattr(self.stream, key)
        def write(self, data):
            self.stream.write(data[:max(1, len(data) // 2)])
            raise OSError(errno.ENOSPC, 'Synthetic full disk')
    @contextmanager
    def fdopen(fd, opened_mode, *args, **kwargs):
        with original(fd, opened_mode, *args, **kwargs) as stream:
            yield Writer(stream) if opened_mode == mode else stream
    with patch('os.fdopen', side_effect=fdopen):
        yield


class Exports21(unittest.TestCase):
    setUp = round19.Recovery19.setUp
    call = round19.Recovery19.call
    data = round19.Recovery19.data
    compose = round19.Recovery19.compose
    approval = round19.Recovery19.approval
    restart = round19.Recovery19.restart

    def attachment(self, size=128 * 1024):
        raw = b'Synthetic attachment\x00' + b'x' * size
        self.raw = raw
        # Keep MIME/provider concerns out of the disk test; production export
        # admission, blob publication, proxy completion and cleanup all run.
        def attachment(args):
            key, export_id = exports.put(self.engine.store, self.engine.blobs, raw)
            return None, {'sha256': key, 'size': len(raw), 'name': 'synthetic.bin', 'export_id': export_id}
        self.mail.attachment = attachment
        self.reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': self.imap.validities['Source'],
                          'uid': 1, 'message_id': self.imap.mid}
        return {'reference': self.reference, 'part': '1.2'}

    def assert_clean(self):
        directory = self.engine.blobs.directory
        self.assertFalse((directory / sha256(self.raw)).exists())
        self.assertFalse((directory / ('.origins-' + sha256(self.raw))).exists())
        self.assertEqual(list(directory.glob('.upload-*')), [])
        self.assertEqual(list(self.engine.store.iter_items('export:')), [])
        self.assertFalse(any(key.startswith('export:') for key in self.engine.store.ledger.holds))

    def test_review21_5mib_uncached_export_at_12mib_refuses_before_either_copy_and_cancel_works(self):
        pending = self.approval('send', self.compose())
        args = self.attachment(5 * 1024 * 1024)
        with round20.disk_budget(self.root, 12 * 1024 * 1024):
            result = self.call('attachment_save', args)
            self.assertEqual(result['error']['code'], 'storage_limit', result)
            self.assert_clean()
            self.assertEqual(self.data('operation_cancel', {'operation_id': pending['operation_id']})['operation']['state'], 'failed')

    def test_review21_enospc_during_blob_bytes_or_origin_publication_retains_nothing(self):
        args = self.attachment()
        for mode in ('wb', 'w'):
            with self.subTest(mode=mode), failing_stream(mode):
                result = self.call('attachment_save', args)
            self.assertEqual(result['error']['code'], 'storage_limit', result)
            self.assertIn('Disk full', result['error']['message'])
            self.assert_clean()

    def test_review21_enospc_during_caller_write_cleans_download_and_new_private_blob(self):
        args = self.attachment()
        caller_root = Path(__file__).resolve().parents[1] / 'test-work'
        caller_root.mkdir(exist_ok=True)
        caller = tempfile.TemporaryDirectory(dir=caller_root)
        self.addCleanup(caller.cleanup)
        home = Path(caller.name) / 'home'
        folder = home / 'Downloads'
        folder.mkdir(parents=True)
        proxy = Proxy('mail', {'act_socket': str(self.root / 'unused.sock'), 'home': str(home), 'folders': [str(folder)]})
        engine = self.engine
        class Client:
            def request(self, request):
                return engine.request({'v': 1, **request})
            def call(self, name, arguments):
                return self.request({'method': 'call', 'action': name, 'arguments': arguments})
            def download(self, app, key, limit, export_id=None):
                result = self.request({'method': 'download', 'app': app, 'sha256': key, 'export_id': export_id})
                return result, engine.blobs.read(key) if result['ok'] else None
        proxy.client = Client()
        original_open = os.open
        def unnamed(path, flags, *values, **kwargs):
            if path == '.':
                fd, name = tempfile.mkstemp(dir=self.root)
                os.unlink(name)
                return fd
            return original_open(path, flags, *values, **kwargs)
        # macOS lacks Linux's unnamed inode primitive; substitute only that
        # inode creation. FilePolicy's actual write/flush/error cleanup runs.
        original_save = proxy.files.save
        def save(*values, **kwargs):
            with failing_stream('wb'):
                return original_save(*values, **kwargs)
        with patch.object(proxy.files, 'directory', side_effect=lambda _: original_open(folder, os.O_RDONLY)), \
             patch('os.O_TMPFILE', 0, create=True), patch('os.open', side_effect=unnamed), \
             patch.object(proxy.files, 'save', side_effect=save):
            result = proxy.call('attachment_save', args)
        self.assertEqual(result['error']['code'], 'storage_limit', result)
        self.assertIn('Disk full', result['error']['message'])
        self.assertEqual(list(folder.iterdir()), [])
        self.assert_clean()

    def test_review21_export_hold_survives_restart_and_blocks_other_service_writes_until_completion(self):
        args = self.attachment()
        item = self.data('attachment_save', args)['file']
        key = 'export:' + item['export_id']
        held = self.engine.store.ledger.holds[key]
        self.restart()
        self.assertEqual(self.engine.store.ledger.holds[key], held)
        from aresos_control.space import SAFETY_FLOOR
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + held)):
            with self.assertRaises(Refused):
                self.engine.store.write({}, 'fixture', 'Cannot consume caller export hold')
            result = self.engine.request({'v': 1, 'method': 'saved', 'app': 'mail', 'export_id': item['export_id'], 'outcome': 'refused'})
            self.assertTrue(result['ok'], result)
        self.assert_clean()
