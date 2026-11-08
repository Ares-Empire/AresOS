"""Owner-only archive, replay/restore protection and interrupted compaction."""
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import time
from unittest.mock import patch

from aresos_control import retention
from aresos_control.common import sha256
from aresos_control.definitions import tools_for
from aresos_control.engine import Engine
from support import EngineCase, ROOT


class Archive(EngineCase):
    def seed(self):
        with patch('aresos_control.engine.time.time', return_value=1000):
            closed = self.reserve(text='Exported private body')
            self.data('testapp_send', closed)
            pending = self.reserve(subject='Keep open')
            notice = self.reserve(subject='Keep unacknowledged')
            self.data('testapp_operation_cancel', {'operation_id': notice['operation_id']})
            # Large completed free-change history makes compaction measurable.
            for _ in range(8):
                self.engine.store.write({}, 'fixture', 'old audit ' + 'x' * 12000)
        return closed, pending, notice

    def archive(self, admin=True):
        return self.call('control_archive', {'before': time.time() - 1, 'confirm': 'archive finished history'}, admin=admin)

    def test_review17_archive_is_owner_only_explicit_and_not_offered_to_claude(self):
        before = len(self.engine.store.events)
        self.assertEqual(self.archive(admin=False)['error']['code'], 'permission_denied')
        self.assertEqual(self.call('control_archive', {'before': 1, 'confirm': 'yes'}, admin=True)['error']['code'], 'invalid_input')
        self.assertEqual(self.call('control_archive', {'before': time.time() + 100, 'confirm': 'archive finished history'}, admin=True)['error']['code'], 'invalid_input')
        self.assertNotIn('archive', [tool['name'] for tool in tools_for('control')])
        self.assertEqual(len(self.engine.store.events), before)

    def test_review17_archive_exports_then_compacts_keeps_open_notices_and_journal_valid_after_restart(self):
        closed, pending, notice = self.seed()
        store = self.engine.store
        journal = (store.evidence_dir / 'operations.jsonl').read_bytes()
        before = store.history_size()
        result = self.archive()
        self.assertTrue(result['ok'], result)
        data = result['data']
        path = Path(data['path'])
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(sha256(path.read_bytes()), data['sha256'])
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        self.assertEqual(rows[0]['head']['hash'], store.events[-2]['hash'])
        self.assertIn('Exported private body', path.read_text())
        self.assertEqual(data['operations'], 1)
        self.assertEqual(sum('event' in row for row in rows), data['events'])
        self.assertLess(store.history_size(), before)
        self.assertTrue((store.evidence_dir / 'operations.jsonl').read_bytes().startswith(journal))
        self.assertIsNone(store.get('op:' + closed['operation_id']))
        self.assertEqual(self.engine.operation(pending['operation_id'])['state'], 'reserved')
        self.assertFalse(self.engine.operation(notice['operation_id']).get('ack', False))
        self.assertEqual(store.db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.restart()
        self.assertFalse(self.engine.store.locked)
        self.assertTrue(self.engine.pending()['items'])
        self.assertFalse(self.call('testapp_send', closed)['ok'])
        self.assertEqual(len(self.engine.receiver.evidence(closed['operation_id'])['arrivals']), 3)
        self.assertEqual(self.engine.store._read_journal()[1], len(self.engine.store.events))

    def test_review17_archive_remains_available_over_old_quota_and_restore_stays_detectable(self):
        closed, pending, notice = self.seed()
        backup = sqlite3.connect(self.root / 'prearchive.sqlite')
        self.engine.store.db.backup(backup)
        backup.close()
        with patch.object(retention, 'HISTORY_BYTES', self.engine.store.history_size()):
            result = self.archive()
            self.assertTrue(result['ok'], result)
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'prearchive.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertTrue(self.engine.store.locked)
        self.assertEqual(self.archive()['error']['code'], 'restore_required')
        self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertFalse(self.call('testapp_send', closed)['ok'])
        self.assertFalse(self.call('testapp_send', pending)['ok'])
        self.restart()
        self.assertFalse(self.engine.store.locked)

    def test_review17_archive_export_failure_never_removes_source_rows(self):
        self.seed()
        before = (list(self.engine.store.db.iterdump()), (self.engine.store.evidence_dir / 'operations.jsonl').read_bytes())
        with patch('aresos_control.archive.os.fsync', side_effect=OSError('Synthetic disk failure')):
            self.assertFalse(self.archive()['ok'])
        self.assertEqual((list(self.engine.store.db.iterdump()), (self.engine.store.evidence_dir / 'operations.jsonl').read_bytes()), before)
        self.assertEqual(list((self.engine.store.evidence_dir / 'archives').glob('*.partial')), [])
        self.restart()

    def test_review17_archive_preserves_unresolved_filing_and_open_repair_dependencies(self):
        closed, pending, notice = self.seed()
        with patch('aresos_control.engine.time.time', return_value=1000), \
             patch.object(self.engine.adapters['testapp'], 'repair', side_effect=RuntimeError('Uncertain local repair')):
            repair = self.data('testapp_operation_repair', {'operation_id': closed['operation_id'], 'stage': 'sent_copy'})['operation']
            self.engine.store.write({'notice:filing': {'id': 'filing', 'app': 'mail', 'state': 'partial', 'ack': False,
                'untrusted_content': {'reason': 'Inspect preserved messages'}},
                'mail:filing:filing': {'id': 'filing', 'state': 'partial'},
                'mail:filing-locations:filing:0': {'locations': ['Retained evidence']}}, 'fixture', 'Keep unresolved filing')
        self.assertEqual(repair['state'], 'unknown')
        result = self.archive()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['data']['operations'], 0)
        for key in ('op:' + closed['operation_id'], 'op:' + repair['id'], 'notice:filing',
                    'mail:filing:filing', 'mail:filing-locations:filing:0'):
            self.assertIsNotNone(self.engine.store.get(key))
        self.restart()
        self.assertFalse(self.engine.store.locked)

    def test_review17_archive_kill_at_every_durable_boundary_restarts_without_corruption_or_resubmission(self):
        # Each iteration uses a fresh child store underneath this worktree.
        import tempfile
        from support import WORK
        previous_root, previous_engine = self.root, self.engine
        try:
            for point in ('archive_exported', 'journal_appended', 'sqlite_prepared', 'sqlite_committed',
                          'journal_committed', 'archive_pruned', 'archive_compacted'):
                with self.subTest(point=point), tempfile.TemporaryDirectory(dir=WORK) as directory:
                    self.root = Path(directory)
                    self.engine = Engine(self.root / 'state', self.root / 'independent')
                    closed, pending, notice = self.seed()
                    self.engine.close()
                    child = subprocess.run([sys.executable, str(ROOT / 'control/tests/archive_worker.py'),
                                            str(self.root), point], capture_output=True, text=True, timeout=30)
                    self.assertEqual(child.returncode, -signal.SIGKILL, child.stdout + child.stderr)
                    self.engine = Engine(self.root / 'state', self.root / 'independent')
                    if self.engine.store.locked:
                        self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
                    self.assertEqual(self.engine.store.db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
                    replay = self.call('testapp_send', closed)
                    if replay['ok']:
                        self.assertEqual(replay['data']['operation']['state'], 'done')
                    else:
                        self.assertIn(replay['error']['code'], {'stale_reference', 'refused'})
                    self.assertEqual(len(self.engine.receiver.evidence(closed['operation_id'])['arrivals']), 3)
                    self.assertTrue(list((self.root / 'independent/archives').glob('*.jsonl')))
                    self.engine.close()
        finally:
            self.root, self.engine = previous_root, previous_engine
