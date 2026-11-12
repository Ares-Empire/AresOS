"""The permanent restore fence cannot consume the compactable SQLite quota."""
import sqlite3
import time
from unittest.mock import patch

from aresos_control import retention
from aresos_control.engine import Engine
from support import EngineCase


class JournalCapacity(EngineCase):
    def test_review18_archive_cycle_frees_capacity_despite_larger_independent_journal_and_old_restore_replay(self):
        with patch('aresos_control.engine.time.time', return_value=1000):
            closed = self.reserve()
            self.data('testapp_send', closed)
            pending = self.reserve(subject='Pending before archive')
            for _ in range(800):
                self.engine.store.write({}, 'fixture', 'Completed free work ' + 'x' * 512)
        backup = sqlite3.connect(self.root / 'backup.sqlite')
        self.engine.store.db.backup(backup)
        backup.close()
        store = self.engine.store
        journal_path = store.evidence_dir / 'operations.jsonl'
        journal = journal_path.read_bytes()
        cap = len(journal)
        before = store.history_size()
        with patch.object(retention, 'HISTORY_BYTES', cap), \
             patch.object(retention, 'REQUEST_RESERVE', 65536), \
             patch.object(retention, 'RECOVERY_RESERVE', 65536):
            self.assertEqual(self.call('testapp_fixture_configure', {'failure': 'none', 'refuse': []},
                                       admin=True)['error']['code'], 'storage_limit')
            result = self.data('control_archive', {'before': time.time() - 1,
                              'confirm': 'archive finished history'}, admin=True)
            self.assertLess(result['history_bytes'], before)
            self.assertGreater(journal_path.stat().st_size, cap)
            self.assertTrue(journal_path.read_bytes().startswith(journal))
            self.configure()
            self.assertEqual(store.history_size(), store.db.execute('PRAGMA page_count').fetchone()[0]
                             * store.db.execute('PRAGMA page_size').fetchone()[0])
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertTrue(self.engine.store.locked)
        self.assertEqual(self.call('testapp_send', closed)['error']['code'], 'restore_required')
        self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        for approval in (closed, pending):
            self.assertFalse(self.call('testapp_send', approval)['ok'])
        self.assertEqual(len(self.engine.receiver.evidence(closed['operation_id'])['arrivals']), 3)
        self.assertEqual(self.engine.store._read_journal()[1], len(self.engine.store.events))
        self.restart()
