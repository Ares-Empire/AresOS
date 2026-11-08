"""Review 12 regressions against production storage and Mail, offline IMAP only."""
from contextlib import contextmanager
import copy
import sqlite3
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from aresos_control import retention
from aresos_control.archive import archive
from aresos_control.common import Refused
from aresos_control.space import SAFETY_FLOOR
from aresos_control.engine import Engine
import test_review_fixes_19 as round19
import test_review_fixes_18 as round18


@contextmanager
def disk_budget(root, free):
    """Charge real file growth against a synthetic starting free-byte balance."""
    def allocated():
        return sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
    start = allocated()
    with patch('aresos_control.space.shutil.disk_usage',
               side_effect=lambda _: SimpleNamespace(free=free - (allocated() - start))):
        yield


class Ledger20(unittest.TestCase):
    setUp = round19.Recovery19.setUp
    call = round19.Recovery19.call
    data = round19.Recovery19.data
    compose = round19.Recovery19.compose
    approval = round19.Recovery19.approval
    snapshot = round19.Recovery19.snapshot
    restart = round19.Recovery19.restart
    send = round19.Recovery19.send
    owner = round19.Recovery19.owner
    uncertain = round19.Recovery19.uncertain
    backup = round18.Recovery18.backup
    restore = round18.Recovery18.restore

    def test_review20_2000_real_delete_records_index_at_30mib_preserves_cancel_and_streamed_status(self):
        for uid in self.imap.boxes['Source']:
            self.imap.boxes['Source'][uid] = self.imap.raw.replace(b'Subject: Filing', b'Subject: ' + b'Synthetic ' * 110)
        items = [self.mail.named_item({'account': 'box', 'folder': 'Source',
                 'uidvalidity': self.imap.validities['Source'], 'uid': uid, 'message_id': self.imap.mid})
                 for uid in self.imap.boxes['Source']]
        approval = self.approval('delete', {'items': items, 'mode': 'trash'})
        store = self.engine.store
        op = self.engine.operation(approval['operation_id'])
        for _ in range(2000):
            store.write({'op:' + op['id']: op}, 'mail_delete', 'Synthetic repeated delete approval record', op['id'])
        with disk_budget(self.root, 30 * 1024 * 1024):
            self.restart()
            self.assertIsNone(self.engine.store.index)
            result = self.call('prepare_delete', {'items': items, 'mode': 'trash'})
            self.assertEqual(result['error']['code'], 'storage_limit')
            self.assertIn('index build', result['error']['message'])
            self.assertEqual(self.data('operation_status', {'operation_id': op['id']})['operation']['state'], 'reserved')
            self.assertEqual(self.data('operation_cancel', {'operation_id': op['id']})['operation']['state'], 'failed')
            self.assertNotIn('cancel:' + op['id'], self.engine.store.ledger.holds)
            self.assertEqual(self.engine.store._read_journal()[1], self.engine.store.sequence)

    def test_review20_2150_archive_attempts_at_20mib_preserve_pending_cancel(self):
        pending = self.approval('send', self.compose())
        completed = 0
        with disk_budget(self.root, 20 * 1024 * 1024):
            for _ in range(2150):
                result = self.engine.request({'v': 1, 'method': 'call', 'action': 'control_archive',
                    'arguments': {'before': time.time() - 1, 'confirm': 'archive finished history'}}, admin=True)
                if not result['ok']:
                    self.assertEqual(result['error']['code'], 'storage_limit', result)
                    break
                completed += 1
            self.assertGreater(completed, 0)
            self.assertFalse(self.engine.store.write_failed)
            self.assertEqual(self.data('operation_cancel', {'operation_id': pending['operation_id']})['operation']['state'], 'failed')
        print('Review20 archives admitted before ledger refusal (2150 attempted maximum):', completed)

    def test_review20_38_uncertain_repairs_and_archives_at_20mib_preserve_cancel(self):
        with disk_budget(self.root, 20 * 1024 * 1024):
            round19.Recovery19.test_review19_38_uncertain_repairs_with_archives_keep_one_and_cancel_works(self)

    def test_review20_all_writers_preserve_live_rights_and_cancel_uses_only_its_own(self):
        pending = self.approval('send', self.compose())
        store = self.engine.store
        held = copy.deepcopy(store.ledger.holds)
        before = self.snapshot()
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + store.ledger.held)):
            writers = [lambda: store.write({}, 'fixture', 'Ordinary write'),
                       lambda: store.write({}, 'control_expire', 'Expiry write'),
                       lambda: self.engine.blobs.put(b'Synthetic import'),
                       lambda: self.mail.wires.put(b'Synthetic wire'),
                       lambda: self.mail.transport.store_password('synthetic', 'synthetic'),
                       lambda: self.engine.receiver.configure({'failure': 'none'}),
                       lambda: archive(store, time.time() - 1)]
            for writer in writers:
                with self.assertRaises(Refused):
                    writer()
                self.assertEqual(store.ledger.holds, held)
                self.assertFalse(store.write_failed)
            self.assertEqual(self.snapshot(), before)
            self.data('operation_cancel', {'operation_id': pending['operation_id']})
        self.assertEqual(store.ledger.held, 0)

    def test_review20_rights_release_on_send_expiry_cancel_and_repair_settlement_and_survive_restart(self):
        for end in ('send', 'expiry', 'cancel'):
            pending = self.approval('send', self.compose(text='Synthetic ' + end))
            key = 'cancel:' + pending['operation_id']
            self.assertIn(key, self.engine.store.ledger.holds)
            self.restart()
            self.assertIn(key, self.engine.store.ledger.holds)
            if end == 'send':
                with patch.object(self.mail, 'execute', return_value=('done', 'Synthetic completed send')):
                    self.data('send', pending)
            elif end == 'expiry':
                with patch('aresos_control.engine.time.time', return_value=pending['description']['expires_at'] + 1):
                    self.engine.expire()
            else:
                self.data('operation_cancel', {'operation_id': pending['operation_id']})
            self.assertNotIn(key, self.engine.store.ledger.holds)
        old, args, repair = self.uncertain()
        key = 'settle:' + repair['id']
        self.assertIn(key, self.engine.store.ledger.holds)
        self.restart()
        self.assertIn(key, self.engine.store.ledger.holds)
        mid = self.mail.message_id(old['id'])
        self.imap.boxes['Sent'][1] = f'Message-ID: {mid}\r\n\r\nSynthetic'.encode()
        held = self.engine.store.ledger.held
        with patch.object(retention, 'HISTORY_BYTES', 0), \
             patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + held)):
            self.assertEqual(self.data('operation_repair', args)['operation']['state'], 'done')
        self.assertNotIn(key, self.engine.store.ledger.holds)

    def test_review20_restore_confirmation_owns_and_releases_its_reservation_without_an_index(self):
        self.backup()
        pending = self.approval('send', self.compose())
        self.restore()
        store = self.engine.store
        self.assertIn('restore', store.ledger.holds)
        store.index.close()
        store.index = None
        store.index_refusal = 'Synthetic admission refusal'
        with patch('aresos_control.space.shutil.disk_usage', return_value=SimpleNamespace(free=SAFETY_FLOOR + store.ledger.held)):
            result = self.owner('control_restore_confirm', {'confirm': 'invalidate earlier approvals'})
        self.assertIn(pending['operation_id'], result['unknown'])
        self.assertNotIn('restore', store.ledger.holds)
        self.assertNotIn('cancel:' + pending['operation_id'], store.ledger.holds)
        self.assertFalse(self.call('send', pending)['ok'])


class RepairIdentity20(unittest.TestCase):
    setUp = round19.Recovery19.setUp
    call = round19.Recovery19.call
    data = round19.Recovery19.data
    compose = round19.Recovery19.compose
    approval = round19.Recovery19.approval
    snapshot = round19.Recovery19.snapshot
    send = round19.Recovery19.send
    owner = round19.Recovery19.owner
    backup = round18.Recovery18.backup

    def restore_with_transport(self):
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'evidence')
        self.mail.store = self.engine.store
        self.mail.blobs = self.engine.blobs
        self.mail.wires = self.engine.adapters['mail'].wires
        self.mail.transport.ledger = self.engine.store.ledger
        self.mail.check_result = self.engine.check_composition_result
        self.engine.adapters['mail'] = self.mail
        self.assertTrue(self.engine.store.locked)

    def test_review20_restore_unknown_repair_retains_original_and_stage_and_reuses_one_attempt(self):
        old = self.send('sent_copy')
        self.backup()
        args = {'operation_id': old['id'], 'stage': 'sent_copy'}
        with patch.object(self.mail, 'local_stage', side_effect=OSError('Synthetic lost APPEND answer')):
            repair = self.data('operation_repair', args)['operation']
        self.restore_with_transport()
        self.owner('control_restore_confirm', {'confirm': 'invalidate earlier approvals'})
        restored = self.engine.operation(repair['id'])
        self.assertEqual(restored['repair_of'], old['id'])
        self.assertEqual(restored['payload']['stage'], 'sent_copy')
        self.assertIn('settle:' + repair['id'], self.engine.store.ledger.holds)
        with patch.object(self.mail, 'sent_matches', side_effect=OSError('Synthetic unavailable evidence')), \
             patch.object(self.mail, 'local_stage', side_effect=AssertionError('Must reuse unresolved attempt')):
            result = self.data('operation_repair', args)
        self.assertEqual(result['operation']['id'], repair['id'])
        self.assertEqual(result['operation']['state'], 'unknown')
        unresolved = [op for _, op in self.engine.store.items('op:')
                      if op.get('repair_of') == old['id'] and op['state'] == 'unknown']
        self.assertEqual(len(unresolved), 1)

    def test_review20_older_evidence_without_repair_stage_refuses_both_new_stages(self):
        old = self.send('sent_copy')
        self.backup()
        args = {'operation_id': old['id'], 'stage': 'sent_copy'}
        from aresos_control.storage import short_description
        def older(op):
            result = short_description(op)
            result.pop('repair', None)
            return result
        with patch('aresos_control.storage.short_description', side_effect=older), \
             patch.object(self.mail, 'local_stage', side_effect=OSError('Synthetic lost APPEND answer')):
            repair = self.data('operation_repair', args)['operation']
        self.restore_with_transport()
        self.owner('control_restore_confirm', {'confirm': 'invalidate earlier approvals'})
        restored = self.engine.operation(repair['id'])
        self.assertTrue(restored['repair_identity_missing'])
        self.assertEqual(restored['repair_of'], old['id'])
        op = self.engine.operation(old['id'])
        op['stages']['answered_flag'] = 'failed'
        self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic two failed stages')
        before = self.snapshot()
        with patch.object(self.mail, 'local_stage', side_effect=AssertionError('Legacy uncertainty must not allocate')):
            for stage in ('sent_copy', 'answered_flag'):
                result = self.call('operation_repair', {'operation_id': old['id'], 'stage': stage})
                self.assertEqual(result['error']['code'], 'repair_identity_missing')
                self.assertIn('permanent stage identity', result['error']['message'])
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(len([op for _, op in self.engine.store.items('op:') if op.get('repair_of') == old['id']]), 1)
