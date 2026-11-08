"""Review 13: admission follows actual restore work and interrupted rights."""
import sqlite3
from contextlib import closing
from types import SimpleNamespace
from unittest.mock import patch

from aresos_control.engine import Engine
from aresos_control.space import SAFETY_FLOOR, record_budget
from support import EngineCase
import test_journal_streaming as streaming


class RestoreWork21(EngineCase):
    def seed_completed(self, count):
        streaming.JournalStreaming.seed_history(self, count, operations=True)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        # The older streaming fixture predates operation_versions. Supply the
        # versions an ordinary Store.write commits alongside each operation.
        for op_id, seq, _ in self.engine.store.iter_latest():
            self.engine.store.db.execute('INSERT OR REPLACE INTO operation_versions VALUES (?,?)', (op_id, seq))
        self.engine.store.db.commit()

    def backup(self):
        with closing(sqlite3.connect(self.root / 'backup.sqlite')) as backup:
            self.engine.store.db.backup(backup)

    def restore(self):
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertTrue(self.engine.store.locked)

    def test_review21_100_completed_metadata_rollback_at_8mib_has_no_reconstruction(self):
        self.seed_completed(100)
        self.backup()
        self.engine.store.write({'fixture:metadata': 1}, 'fixture', 'Synthetic metadata only')
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=8 * 1024 * 1024)):
            self.restore()
            self.assertEqual(list(self.engine.store._restore_operations()), [])
            self.assertEqual(self.engine.store.ledger.holds['restore'], 256 * 1024)
            self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertFalse(self.engine.store.locked)
        self.assertTrue(all(op['state'] == 'done' for _, op in self.engine.store.iter_items('op:')))

    def test_review21_10000_completed_hold_matches_only_three_changed_operations(self):
        self.seed_completed(10000)
        self.backup()
        ids = []
        for _, op in self.engine.store.iter_items('op:'):
            ids.append(op['id'])
            op['reason'] = 'Synthetic changed evidence after backup'
            self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic operation update', op['id'])
            if len(ids) == 3:
                break
        self.restore()
        work = list(self.engine.store._restore_operations())
        self.assertEqual([op['id'] for op in work], ids)
        expected = 256 * 1024 + sum(record_budget(op) for op in work)
        self.assertEqual(self.engine.store.ledger.holds['restore'], expected)
        result = self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertEqual(result['unknown'], ids)
        self.assertEqual(sum(op['state'] == 'done' for _, op in self.engine.store.iter_items('op:')), 9997)
        self.assertNotIn('restore', self.engine.store.ledger.holds)


class Crash(BaseException):
    pass


class ReservedReplay21(EngineCase):
    def crash_prepared(self, name):
        if name == 'sqlite_prepared':
            raise Crash()

    def test_review21_cancel_prepared_replay_spends_original_hold_and_status_serves(self):
        approval = self.reserve()
        op_id = approval['operation_id']
        held = self.engine.store.ledger.held
        self.engine.store.checkpoint = self.crash_prepared
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + held)):
            with self.assertRaises(Crash):
                self.engine.dispatch('testapp_operation_cancel', {'operation_id': op_id})
            self.restart()
            self.assertIsNone(self.engine.store.index)
            result = self.data('testapp_operation_status', {'operation_id': op_id})
            self.assertEqual(result['operation']['state'], 'failed')
            self.assertIn('cancelled', result['operation']['reason'])
        self.assertEqual(self.engine.store.ledger.holds, {})
        self.assertEqual(self.engine.store.committed, self.engine.store.sequence)

    def test_review21_prepared_restore_confirmation_replays_from_its_existing_hold(self):
        with closing(sqlite3.connect(self.root / 'backup.sqlite')) as backup:
            self.engine.store.db.backup(backup)
        approval = self.reserve()
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        held = self.engine.store.ledger.held
        self.engine.store.checkpoint = self.crash_prepared
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + held)):
            with self.assertRaises(Crash):
                self.engine.store.confirm_restore()
            self.restart()
            self.assertFalse(self.engine.store.locked)
            result = self.data('testapp_operation_status', {'operation_id': approval['operation_id']})
            self.assertEqual(result['operation']['state'], 'unknown')
        self.assertNotIn('restore', self.engine.store.ledger.holds)
        self.assertEqual(self.engine.store.committed, self.engine.store.sequence)
