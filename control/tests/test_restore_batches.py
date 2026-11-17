"""Review 12: confirmation never adds a history-sized permanent journal line."""
from contextlib import closing
import errno
import gc
import os
import sqlite3
import tracemalloc
from unittest.mock import patch
import uuid

from aresos_control.common import canonical
from aresos_control.engine import Engine
from aresos_control.storage import RESTORE_BATCH_BYTES, RESTORE_BATCH_COUNT
from support import EngineCase
import test_journal_streaming as streaming


class RestoreBatches(EngineCase):
    def test_review20_1000_and_10000_restored_operations_have_fixed_verification_peak_and_bounded_records(self):
        metrics = []
        for count in (1000, 10000):
            if count == 10000:
                # Reuse the same private fixture tree; a fresh backup precedes
                # the next independent group of missing operations.
                self.assertFalse(self.engine.store.locked)
            backup = sqlite3.connect(self.root / 'backup.sqlite')
            self.engine.store.db.backup(backup)
            backup.close()
            streaming.JournalStreaming.seed_history(self, count, operations=True)
            (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
            self.engine = Engine(self.root / 'state', self.root / 'independent')
            self.assertTrue(self.engine.store.locked)
            start = self.engine.store.sequence
            result = self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
            # The second restore also retains the first group's unknowns.
            unknown_count = 1000 if count == 1000 else 11000
            self.assertEqual(len(result['unknown']), 100)
            self.assertEqual(result['unknown_more'], {'count': unknown_count - 100, 'action': 'control_pending'})
            self.assertLess(len(canonical(result).encode()), 16 * 1024)
            self.assertNotIn('restore', self.engine.store.ledger.holds)
            records = 0
            for record in self.engine.store.events:
                if record['seq'] <= start:
                    continue
                records += 1
                self.assertLessEqual(len(record['operations']), RESTORE_BATCH_COUNT)
                self.assertLessEqual(len(canonical(record).encode()), RESTORE_BATCH_BYTES)
            self.assertGreater(records, count // RESTORE_BATCH_COUNT)
            gc.collect()
            tracemalloc.start()
            try:
                verified = self.engine.store._read_journal()[1]
                retained, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            self.assertEqual(verified, self.engine.store.sequence)
            self.assertLess(peak, 2 * 1024 * 1024)
            metrics.append((retained, peak))
            self.restart()
            self.assertFalse(self.engine.store.locked)
        print('Review20 restored journal verification (retained, peak bytes), 1k/10k missing operations:', metrics)

    def test_review20_crash_after_first_restore_batch_keeps_lock_until_confirmation_finishes(self):
        backup = sqlite3.connect(self.root / 'backup.sqlite')
        self.engine.store.db.backup(backup)
        backup.close()
        streaming.JournalStreaming.seed_history(self, 100, operations=True)
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        class Crash(BaseException):
            pass
        committed = []
        def checkpoint(name):
            if name == 'journal_committed':
                committed.append(name)
                if len(committed) == 1:
                    raise Crash()
        self.engine.store.checkpoint = checkpoint
        with self.assertRaises(Crash):
            self.engine.store.confirm_restore()
        self.assertTrue(self.engine.store.get('restore_pending'))
        self.restart()
        self.assertTrue(self.engine.store.locked)
        result = self.call('testapp_prepare_send', {'account': 'fixture', 'to': ['alpha'],
            'cc': [], 'bcc': [], 'subject': 'Synthetic', 'text': 'Synthetic', 'attachments': []})
        self.assertEqual(result['error']['code'], 'restore_required')
        result = self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertEqual(len(result['unknown']), 100)
        self.assertFalse(self.engine.store.locked)
        self.assertIsNone(self.engine.store.get('restore_pending'))
        self.assertEqual(sum(1 for _, op in self.engine.store.iter_items('op:') if op['state'] == 'unknown'), 100)

    def confirm_failing_at_its_last_marker_sync(self, rollback_fails):
        """Brief 20-restore-lock-followups, item 1: the running store keeps its lock."""
        with closing(sqlite3.connect(self.root / 'older.sqlite')) as backup:
            self.engine.store.db.backup(backup)
        self.engine.store.write({'fixture:later': {'value': 1}}, 'fixture', 'Synthetic later commit')
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'older.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        store = self.engine.store
        self.assertTrue(store.locked)
        before = store.generation
        journal = store.evidence_dir / 'operations.jsonl'
        sync, failed = os.fsync, []
        def fsync(descriptor):
            # The confirm's only write: its record, then its commit marker.
            if descriptor == store.journal.fileno() and not failed and journal.read_bytes().splitlines()[-1].startswith(b'{"commit"'):
                failed.append(descriptor)
                raise OSError(errno.ENOSPC, 'Synthetic full disk at the last commit marker')
            return sync(descriptor)
        rollback = patch.object(store, '_truncate_journal', side_effect=OSError(errno.ENOSPC, 'Synthetic failed rollback')) \
            if rollback_fails else patch.object(store, '_truncate_journal', wraps=store._truncate_journal)
        generation = uuid.UUID(int=20)
        with patch('aresos_control.storage.os.fsync', fsync), rollback, patch('aresos_control.storage.uuid.uuid4', return_value=generation):
            reply = self.call('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertEqual(len(failed), 1)
        self.assertEqual((reply['ok'], reply['error']['code']), (False, 'storage_limit'), reply)
        # Rolled back or not, the marker's sync failed: the lock stays.
        self.assertEqual(journal.read_bytes().splitlines()[-1].startswith(b'{"commit"'), rollback_fails)
        self.assertTrue(store.locked)
        pending = self.call('control_pending')
        self.assertTrue(pending['ok'], pending)
        self.assertIs(pending['data']['restore_required'], True)
        self.assertEqual(self.call('control_log')['error']['code'], 'restore_required')
        self.restart()
        self.assertFalse(self.engine.store.locked)
        self.assertEqual(self.engine.store.generation, generation.hex)
        self.assertNotEqual(self.engine.store.generation, before)
        self.assertIs(self.data('control_pending')['restore_required'], False)

    def test_confirm_whose_last_marker_sync_fails_keeps_the_lock_until_a_restart(self):
        self.confirm_failing_at_its_last_marker_sync(rollback_fails=False)

    def test_confirm_whose_marker_stays_after_a_failed_sync_keeps_the_lock_until_a_restart(self):
        self.confirm_failing_at_its_last_marker_sync(rollback_fails=True)
