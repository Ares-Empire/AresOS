"""Round 17 quota regressions using real journals and the production Mail adapter."""
import copy
import sqlite3
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control import retention
from aresos_control.space import SAFETY_FLOOR
from aresos_control.common import canonical
import test_review_fixes_12 as round12
import test_review_fixes_16 as round16


class Recovery17(unittest.TestCase):
    setUp = round12.PlainQuestions12.setUp
    call = round12.PlainQuestions12.call
    data = round12.PlainQuestions12.data
    compose = round12.PlainQuestions12.compose
    approval = round12.PlainQuestions12.approval
    restart = round16.Review16.restart
    snapshot = round16.Review16.snapshot

    def test_review17_unchanged_prepare_reuses_exact_approval_and_no_history_even_at_free_limit(self):
        composition = self.compose()
        approval = self.approval('send', composition)
        before = self.snapshot()
        limit = self.engine.store.history_size() + retention.REQUEST_RESERVE + retention.RECOVERY_RESERVE - 1
        with patch.object(retention, 'HISTORY_BYTES', limit):
            for _ in range(24):
                self.assertEqual(self.approval('send', composition), approval)
                self.assertEqual(self.snapshot(), before)
        self.restart()
        self.assertEqual(self.approval('send', composition), approval)
        self.assertEqual(len(self.engine.store.items('op:')), 1)
        changed = self.compose(text='Changed composition')
        self.assertNotEqual(self.approval('send', changed)['operation_id'], approval['operation_id'])
        self.data('operation_cancel', {'operation_id': approval['operation_id']})
        fresh = self.approval('send', composition)
        self.assertNotEqual(fresh['operation_id'], approval['operation_id'])
        with patch('aresos_control.engine.time.time', return_value=fresh['description']['expires_at'] + 1):
            self.assertNotEqual(self.approval('send', composition)['operation_id'], fresh['operation_id'])

    def test_review17_free_limit_preserves_cancel_both_ack_paths_repair_and_expiry(self):
        args = self.compose()
        approval = self.approval('send', args)
        other = self.approval('send', self.compose(text='Other'))
        op = self.engine.operation(other['operation_id'])
        op.update(state='partial', stages={'smtp_data': 'accepted:250', 'sent_copy': 'done', 'answered_flag': 'failed'})
        self.engine.store.write({'op:' + op['id']: op, 'notice:warning': {
            'id': 'warning', 'app': 'mail', 'state': 'partial', 'ack': False,
            'untrusted_content': {'reason': 'Inspect preserved messages'}}}, 'fixture', 'Synthetic accepted send and notice')
        expires = self.approval('send', self.compose(text='Expires'))
        # A reduced production quota puts ordinary work one byte past admission.
        cap = self.engine.store.history_size() + retention.REQUEST_RESERVE + retention.RECOVERY_RESERVE - 1
        with patch.object(retention, 'HISTORY_BYTES', cap), \
             patch.object(self.mail.transport, 'smtp', side_effect=AssertionError('Recovery must never submit')):
            before = self.snapshot()
            refused = self.call('compose', {'account': 'box', 'text': 'More free work'})
            self.assertEqual(refused['error']['code'], 'storage_limit', refused)
            self.assertIn('recovery capacity reserved', refused['error']['message'])
            self.assertEqual(self.snapshot(), before)
            self.assertEqual(self.data('operation_cancel', {'operation_id': approval['operation_id']})['operation']['state'], 'failed')
            self.assertTrue(self.data('notice_ack', {'operation_id': approval['operation_id']})['operation']['ack'])
            self.assertTrue(self.data('notice_ack', {'operation_id': 'warning'})['notice']['ack'])
            before_ack = self.snapshot()
            self.data('notice_ack', {'operation_id': 'warning'})
            self.data('notice_ack', {'operation_id': approval['operation_id']})
            self.assertEqual(self.snapshot(), before_ack)
            repaired = self.data('operation_repair', {'operation_id': other['operation_id'], 'stage': 'answered_flag'})
            self.assertEqual(repaired['operation']['state'], 'done')
            self.assertEqual(repaired['original']['state'], 'done')
            with patch('aresos_control.engine.time.time', return_value=expires['description']['expires_at'] + 1):
                self.engine.expire()
            self.assertEqual(self.engine.operation(expires['operation_id'])['state'], 'failed')
        self.restart()

    def test_review17_free_limit_and_physical_reserve_preserve_owner_restore_confirmation(self):
        backup = sqlite3.connect(self.root / 'backup.sqlite')
        self.engine.store.db.backup(backup)
        backup.close()
        approval = self.approval('send', self.compose())
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        from aresos_control.engine import Engine
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.engine.store.locked)
        cap = self.engine.store.history_size() + retention.REQUEST_RESERVE + retention.RECOVERY_RESERVE - 1
        with patch.object(retention, 'HISTORY_BYTES', cap), \
             patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + self.engine.store.ledger.held)):
            result = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_restore_confirm',
                        'arguments': {'confirm': 'invalidate earlier approvals'}}, admin=True)
            self.assertTrue(result['ok'], result)
            self.assertIn(approval['operation_id'], result['data']['unknown'])
        self.restart()
        self.assertFalse(self.call('send', approval)['ok'])

    def test_review17_free_writes_cannot_consume_recovery_bytes_and_recovery_still_obeys_hard_cap(self):
        store = self.engine.store
        cap = store.history_size() + retention.RECOVERY_RESERVE
        with patch.object(retention, 'HISTORY_BYTES', cap):
            with self.assertRaisesRegex(Exception, 'recovery capacity reserved'):
                store.write({}, 'fixture', 'Cannot use recovery space')
            store.write({}, 'control_expire', 'Safety maintenance uses reserve')
        before = self.snapshot()
        with patch.object(retention, 'HISTORY_BYTES', store.history_size()):
            with self.assertRaisesRegex(Exception, 'Recovery audit history'):
                store.write({}, 'control_expire', 'No write beyond hard cap')
        self.assertEqual(self.snapshot(), before)
        self.restart()
