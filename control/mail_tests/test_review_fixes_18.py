"""Review 10: read-only completed repairs and independent owner recovery room."""
import copy
import sqlite3
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control import retention
from aresos_control.space import SAFETY_FLOOR
from aresos_control.common import Refused
from aresos_control.engine import Engine
import test_review_fixes_17 as round17


class Recovery18(unittest.TestCase):
    setUp = round17.Recovery17.setUp
    call = round17.Recovery17.call
    data = round17.Recovery17.data
    compose = round17.Recovery17.compose
    approval = round17.Recovery17.approval
    snapshot = round17.Recovery17.snapshot
    restart = round17.Recovery17.restart

    def send(self, failed=None):
        approval = self.approval('send', self.compose())
        def accepted(operation, composition, raw, stage):
            stage('smtp_data', 'accepted:250')
            return 'done', 'Synthetic DATA acceptance'
        def local(operation, stage):
            if stage == failed:
                raise Refused('stage_missing', 'Synthetic failed local stage')
            return 'done' if stage == 'sent_copy' else 'not_needed'
        with patch.object(self.mail, 'send_smtp', side_effect=accepted), \
             patch.object(self.mail, 'local_stage', side_effect=local):
            result = self.data('send', approval)['operation']
        self.assertEqual(result['state'], 'partial' if failed else 'done', result)
        return result

    def owner(self, action, arguments):
        result = self.engine.request({'v': 1, 'method': 'call', 'action': action,
                                      'arguments': arguments}, admin=True)
        self.assertTrue(result['ok'], result)
        return result['data']

    def backup(self):
        backup = sqlite3.connect(self.root / 'backup.sqlite')
        try:
            self.engine.store.db.backup(backup)
        finally:
            backup.close()

    def restore(self):
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.engine.store.locked)

    def test_review18_completed_repairs_leave_journal_sqlite_audit_and_sizes_unchanged_at_full_capacity(self):
        for failed in (None, 'sent_copy'):
            old = self.send(failed)
            args = {'operation_id': old['id'], 'stage': 'sent_copy'}
            with patch.object(self.mail, 'local_stage', return_value='done'):
                result = self.data('operation_repair', args)
            before = self.snapshot()
            sizes = (self.engine.store.history_size(), len(self.engine.store.audit()),
                     (self.root / 'state/control.sqlite').stat().st_size)
            with patch.object(retention, 'HISTORY_BYTES', 0), \
                 patch.object(self.mail, 'local_stage', side_effect=AssertionError('Completed stage must not act')):
                for _ in range(100):
                    self.assertEqual(self.data('operation_repair', args), result)
            self.assertEqual(self.snapshot(), before)
            self.assertEqual((self.engine.store.history_size(), len(self.engine.store.audit()),
                             (self.root / 'state/control.sqlite').stat().st_size), sizes)
        self.restart()
        before = self.snapshot()
        self.assertEqual(self.data('operation_repair', args), result)
        self.assertEqual(self.snapshot(), before)

    def test_review18_ineligible_repairs_refuse_before_recording_or_adapter_action(self):
        sent = self.send('sent_copy')
        old = self.engine.operation(sent['id'])
        for changes, stage in (({'action': 'mail_delete'}, 'sent_copy'),
                               ({'stages': {'sent_copy': 'failed'}}, 'sent_copy'),
                               ({}, 'unknown'),
                               ({'stages': {'smtp_data': 'accepted:250'}}, 'sent_copy'),
                               ({'stages': {'smtp_data': 'accepted:250', 'sent_copy': 'attempting'}}, 'sent_copy'),
                               ({'state': 'reserved'}, 'sent_copy')):
            with self.subTest(changes=changes, stage=stage):
                op = {**copy.deepcopy(old), **changes}
                op['payload'] = self.engine.operation(old['id'])['payload']
                self.engine.store.write({'op:' + old['id']: op}, 'fixture', 'Synthetic ineligible repair')
                before = self.snapshot()
                with patch.object(self.mail, 'local_stage', side_effect=AssertionError('Ineligible repair acted')):
                    self.assertFalse(self.call('operation_repair', {'operation_id': old['id'], 'stage': stage})['ok'])
                self.assertEqual(self.snapshot(), before)

    def test_review18_review_sequence_redundant_repairs_cancel_and_preceding_backup_restore(self):
        old = self.send()
        pending = self.approval('send', self.compose(text='Keep pending'))
        self.backup()
        cap = self.engine.store.history_size() + retention.RECOVERY_REQUEST + 1
        with patch.object(retention, 'HISTORY_BYTES', cap):
            before = self.snapshot()
            for _ in range(100):
                self.data('operation_repair', {'operation_id': old['id'], 'stage': 'sent_copy'})
            self.assertEqual(self.snapshot(), before)
            self.data('operation_cancel', {'operation_id': pending['operation_id']})
        self.restore()
        with patch.object(retention, 'HISTORY_BYTES', cap):
            self.owner('control_restore_confirm', {'confirm': 'invalidate earlier approvals'})
            self.owner('control_archive', {'before': time.time() - 1,
                                          'confirm': 'archive finished history'})
        self.assertFalse(self.call('send', pending)['ok'])

    def test_review18_restore_confirms_above_every_quota_and_can_archive_afterward(self):
        self.backup()
        approval = self.approval('send', self.compose())
        self.restore()
        with patch.object(retention, 'HISTORY_BYTES', 0), \
             patch('aresos_control.space.shutil.disk_usage',
                   return_value=SimpleNamespace(free=SAFETY_FLOOR + self.engine.store.ledger.held)):
            self.owner('control_restore_confirm', {'confirm': 'invalidate earlier approvals'})
        self.owner('control_archive', {'before': time.time() - 1,
                                      'confirm': 'archive finished history'})
        self.assertFalse(self.call('send', approval)['ok'])
        self.restart()

    def test_review18_repairs_and_ordinary_recovery_cannot_consume_restore_room(self):
        old = self.send('sent_copy')
        store = self.engine.store
        before = self.snapshot()
        with patch.object(retention, 'HISTORY_BYTES', store.history_size()):
            self.assertEqual(self.call('operation_repair', {'operation_id': old['id'],
                                                         'stage': 'sent_copy'})['error']['code'], 'storage_limit')
            with self.assertRaises(Refused):
                store.write({}, 'control_expire', 'Cannot consume owner restore capacity')
        with patch('aresos_control.space.shutil.disk_usage',
                   return_value=SimpleNamespace(free=SAFETY_FLOOR + self.engine.store.ledger.held)):
            self.assertEqual(self.call('operation_repair', {'operation_id': old['id'],
                                                         'stage': 'sent_copy'})['error']['code'], 'storage_limit')
        self.assertEqual(self.snapshot(), before)
