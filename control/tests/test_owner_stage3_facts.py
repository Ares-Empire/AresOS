"""Owner facts keep interrupted evidence separate from a later clean result."""
import tempfile
import sqlite3
from pathlib import Path
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.mail.adapter import Mail
from aresos_control.owner_state import owner_view
from aresos_control.storage import Store
from owner_state_oracle.records import decode

WORK = Path(__file__).resolve().parents[2] / '.work' / 'owner-stage3-tests'
WORK.mkdir(parents=True, exist_ok=True)


class OwnerStageThreeFacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.mail = Mail(self.store, None)

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def test_interrupted_evidence_survives_clean_check_ack_and_restart(self):
        identity = self.store.generation + ':' + 'a' * 32
        key = 'op:' + identity
        op = {'id': identity, 'generation': self.store.generation, 'app': 'mail', 'action': 'mail_send',
              'state': 'done', 'stages': {}, 'payload': {},
              'approval': {'description': {'action': 'mail_send', 'account': 'box'}}, 'input_hash': 'b' * 64,
              'expires': 0, 'reason': 'Synthetic completed delivery'}
        self.store.write({key: op}, 'fixture', 'Synthetic completed operation')
        self.mail.register_sent_check(op)
        epoch = self.store.owner_projection.open_epoch(key)
        with patch.object(self.store, 'write', side_effect=Refused('storage_error', 'Synthetic failing disk')):
            with self.assertRaises(Refused):
                self.mail.sent_copy_count(op, [{'uid': 1}, {'uid': 2}], commit_clean=True)
        self.assertEqual(epoch, self.store.owner_projection.open_epoch(key))
        self.store.check_sessions = set()
        self.mail.register_sent_check(op)
        self.mail.sent_copy_count(op, [], commit_clean=True)
        notices = self.store.items('notice:')
        self.assertEqual(1, len(notices))
        notice_key, warning = notices[0]
        self.assertEqual('evidence_unrecorded', warning['check_kind'])
        self.assertEqual(epoch, warning['untrusted_content']['lost_check'])
        self.assertFalse(warning['ack'])
        self.assertIsNone(self.store.owner_projection.open_epoch(key))
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertEqual(warning, self.store.get(notice_key))
        warning['ack'] = True
        self.store.write({notice_key: warning}, 'mail_notice_ack', 'Synthetic acknowledgement')
        self.store.write_failed = True
        projected = owner_view(self.store).get(notice_key)
        self.assertTrue(projected['ack'])
        self.assertEqual(epoch, projected['untrusted_content']['lost_check'])
        record = decode(self.root / 'state', self.root / 'evidence')
        self.assertTrue(record.owner_rows[notice_key]['ack'])

    def test_qualification_codes_survive_without_sqlite_prose(self):
        key = 'mail:account:box'
        self.store.write({key: {'id': 'box', 'ready': False, 'onboarded': True,
            'special': {'trash': 'Trash'}, 'sent_policy': 'client', 'safe_folder_delete': True,
            'folder_delete_reason': 'Qualified: synthetic verified probe details',
            'signature': 'Authored signature stays in SQLite'}}, 'fixture', 'Synthetic qualification')
        self.store.write_failed = True
        failure = sqlite3.OperationalError('database or disk is full')
        failure.sqlite_errorcode = sqlite3.SQLITE_FULL
        with patch.object(self.store, 'get', side_effect=failure):
            account = owner_view(self.store).get(key)
        self.assertEqual('client', account['sent_policy'])
        self.assertTrue(account['safe_folder_delete'])
        self.assertTrue(account['folder_delete_reason'].startswith('Qualified:'))
        self.assertNotIn('signature', account)
        public = self.mail.public_account(account)
        self.assertFalse(public['ready'])
        self.assertTrue(public['safe_folder_delete'])
        self.assertTrue(public['folder_delete_reason'].startswith('Qualified:'))


if __name__ == '__main__':
    unittest.main()

class PreparedRestoreProof(unittest.TestCase):
    def test_prepared_boundary_explains_only_the_recorded_backup_holes(self):
        from owner_state_oracle.model import Oracle
        from owner_state_oracle.records import Record
        oracle = Oracle()
        oracle.call('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, 1000)
        oracle.script[-1].update(start_seq=5, end_seq=6, restore_precondition=True, restore_working_head=3)
        event = {'seq': 6, 'action': 'control_restore_confirm', 'restore_range': [4, 5]}
        record = Record(committed=set(range(1, 6)), prepared=[event])
        self.assertEqual({4, 5}, oracle.prepared_restore_sequences(record))
        event['restore_range'] = [2, 5]
        self.assertFalse(oracle.prepared_restore_sequences(record))
        event['restore_range'] = [4, 6]
        self.assertFalse(oracle.prepared_restore_sequences(record))
        event['restore_range'] = [4, 5]
        oracle.script[-1]['restore_precondition'] = False
        self.assertFalse(oracle.prepared_restore_sequences(record))
