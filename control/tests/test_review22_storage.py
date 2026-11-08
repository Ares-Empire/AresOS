"""Review 14: interrupted writes preserve complete fences and storage errors."""
import errno
import json
import sqlite3
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from support import EngineCase, message


class Journal22(EngineCase):
    def test_review22_short_commit_prepare_fails_and_full_replay_clears_latch(self):
        store = self.engine.store
        write = store.journal.write
        def short_commit(data):
            return write(data[:13]) if 'commit' in json.loads(data) else write(data)
        with patch.object(store.journal, 'write', side_effect=short_commit):
            result = self.call('testapp_prepare_send', message())
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Disk full', result['error']['message'])
        self.assertTrue(store.write_failed)
        before = (store.evidence_dir / 'operations.jsonl').read_bytes()
        self.assertTrue(before.endswith(b'\n'))
        self.assertNotIn('commit', json.loads(before.splitlines()[-1]))
        refused = self.call('testapp_prepare_send', message())
        self.assertEqual(refused['error']['code'], 'storage_limit')
        self.assertIn('Disk full', refused['error']['message'])
        self.assertTrue(store.write_failed)
        self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
        self.restart()
        self.assertFalse(self.engine.store.write_failed)
        self.assertFalse(self.engine.store.locked)
        self.assertEqual(self.engine.store.committed, self.engine.store.sequence)
        self.reserve(subject='Full write after space returned')

    def test_review22_short_event_then_enospc_discards_partial_and_syncs(self):
        store = self.engine.store
        before = (store.evidence_dir / 'operations.jsonl').read_bytes()
        write = store.journal.write
        def interrupted(data):
            write(data[:13])
            raise OSError(errno.ENOSPC, 'Synthetic disk full after partial event')
        with patch.object(store.journal, 'write', side_effect=interrupted), \
             patch('aresos_control.storage.os.fsync', wraps=__import__('os').fsync) as sync:
            result = self.call('testapp_prepare_send', message())
        self.assertFalse(result['ok'], result)
        self.assertEqual(result['error']['code'], 'storage_limit')
        self.assertIn('Disk full', result['error']['message'])
        self.assertTrue(store.write_failed)
        self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
        sync.assert_called_once_with(store.journal.fileno())
        self.restart()
        self.reserve()

    def test_review22_zero_and_short_event_writes_are_not_success(self):
        for count in (0, 13):
            store = self.engine.store
            before = (store.evidence_dir / 'operations.jsonl').read_bytes()
            write = store.journal.write
            def short(data):
                return write(data[:count])
            with self.subTest(count=count), patch.object(store.journal, 'write', side_effect=short):
                result = self.call('testapp_prepare_send', message())
            self.assertEqual(result['error']['code'], 'storage_limit', result)
            self.assertTrue(store.write_failed)
            self.assertEqual((store.evidence_dir / 'operations.jsonl').read_bytes(), before)
            self.restart()

    def test_review22_startup_truncates_torn_event_or_commit_and_replays_prepared(self):
        for tail in ('event', 'commit'):
            with self.subTest(tail=tail):
                approval = self.reserve()
                self.engine.close()
                path = self.root / 'independent/operations.jsonl'
                rows = path.read_bytes().splitlines(keepends=True)
                if tail == 'event':
                    path.write_bytes(b''.join(rows) + b'{"format":2,"seq":')
                else:
                    path.write_bytes(b''.join(rows[:-1]) + rows[-1][:13])
                self.engine = Engine(self.root / 'state', self.root / 'independent')
                self.assertFalse(self.engine.store.locked)
                self.assertEqual(self.engine.store.committed, self.engine.store.sequence)
                self.assertEqual(self.engine.operation(approval['operation_id'])['state'], 'reserved')
                self.reserve()

    def test_review22_corrupt_committed_record_and_middle_tail_still_rejected(self):
        self.reserve()
        self.engine.close()
        path = self.root / 'independent/operations.jsonl'
        before = path.read_bytes()
        for damaged in (before.replace(b'"format":2', b'"format":3', 1),
                        before + b'{"format":\n' + before.splitlines(keepends=True)[-1]):
            with self.subTest(damaged=damaged[-40:]):
                path.write_bytes(damaged)
                with self.assertRaises(Refused) as error:
                    Engine(self.root / 'state', self.root / 'independent')
                self.assertEqual(error.exception.code, 'evidence_corrupt')
                self.assertEqual(path.read_bytes(), damaged)
        path.write_bytes(before)
        self.engine = Engine(self.root / 'state', self.root / 'independent')

    def test_review22_storage_errno_and_sqlite_errors_never_become_mail_transport(self):
        errors = [(OSError(errno.ENOSPC, 'Synthetic full disk'), 'storage_limit'),
                  (OSError(errno.EDQUOT, 'Synthetic quota'), 'storage_limit'),
                  (OSError(errno.EIO, 'Synthetic disk error'), 'storage_error')]
        for code in (sqlite3.SQLITE_FULL, sqlite3.SQLITE_IOERR):
            error = sqlite3.OperationalError('Synthetic SQLite storage failure')
            error.sqlite_errorcode = code
            errors.append((error, 'storage_limit' if code == sqlite3.SQLITE_FULL else 'storage_error'))
        for error, code in errors:
            with self.subTest(error=error), patch.object(self.engine.store, '_append', side_effect=error):
                result = self.call('testapp_prepare_send', message())
            self.assertFalse(result['ok'], result)
            self.assertEqual(result['error']['code'], code)
            self.assertNotIn('transport', result['error']['message'].lower())
            self.engine.store.write_failed = False
