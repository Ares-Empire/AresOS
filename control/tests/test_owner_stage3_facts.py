"""Owner facts keep interrupted evidence separate from a later clean result."""
import errno
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

    def test_unpublished_owner_fsync_failure_can_recover_without_reusing_its_chain(self):
        before = dict(self.store.owner_projection.iter_items())
        failure = OSError(errno.ENOSPC, 'Synthetic owner publication failure')
        with patch('os.fsync', side_effect=failure), self.assertRaises(OSError):
            self.store.write({'intent:unpublished': {'id': 'unpublished', 'app': 'mail',
                'action': 'mail_flag', 'state': 'started'}}, 'fixture', 'Synthetic unpublished facts')
        self.assertEqual(before, dict(self.store.owner_projection.iter_items()))
        self.store.refresh_restore()
        self.assertFalse(self.store.write_failed)
        self.store.write({'intent:next': {'id': 'next', 'app': 'mail',
            'action': 'mail_flag', 'state': 'started'}}, 'fixture', 'Synthetic next facts')
        record = decode(self.root / 'state', self.root / 'evidence')
        self.assertNotIn('intent:unpublished', record.owner_rows)
        self.assertIn('intent:next', record.owner_rows)




class PreparedRestoreProof(unittest.TestCase):
    def test_restore_confirmation_cannot_leave_a_reserved_approval_in_the_old_generation(self):
        from owner_state_oracle.model import Oracle, Fact
        from owner_state_oracle.records import Record
        oracle = Oracle()
        oracle.seed_sequence = 1
        row = {'id': 'old:p', 'app': 'testapp', 'action': 'testapp_send', 'generation': 'old',
               'state': 'reserved', 'reason': 'Awaiting exact approval; nothing submitted.'}
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'op:old:p': row}},
            {'seq': 2, 'action': 'control_restore_confirm', 'set': {'generation': 'new'}}])
        oracle.call('control_restore_confirm', {}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2, restore_precondition=True)
        oracle.expected(record)
        proof = Fact('op:old:p', 'missing-restore-operation-result', detail='2')
        self.assertIn(proof, oracle.lifecycle_errors)
        record.events[-1]['set']['op:old:p'] = {**row, 'state': 'failed'}
        oracle.lifecycle_errors.clear()
        oracle.expected(record)
        self.assertNotIn(proof, oracle.lifecycle_errors)

    def test_only_the_unfinished_transactions_own_fault_can_remain_a_refusal(self):
        from owner_state_oracle.model import Oracle
        from owner_state_oracle.records import Record
        oracle = Oracle()
        oracle.call('mail_move', {}, 1000, {'trace': [(5, 'file.write', 'ENOSPC')]})
        oracle.script[-1].update(start_seq=1, end_seq=2)
        oracle.call('mail_accounts', {}, 1001)
        oracle.script[-1].update(start_seq=2, end_seq=2)
        record = Record(committed={1}, prepared=[{'seq': 2}])
        self.assertIn('storage_limit', oracle.permitted_status(record, oracle.script[-1]))
        record.prepared = [{'seq': 3}]
        self.assertNotIn('storage_limit', oracle.permitted_status(record, oracle.script[-1]))
        record.prepared.clear()
        self.assertNotIn('storage_limit', oracle.permitted_status(record, oracle.script[-1]))

    def test_applied_prepared_head_is_not_a_restored_backup(self):
        from owner_state_oracle.records import Record, restore_lock
        fence = {'seq': 2, 'hash': 'prepared'}
        record = Record(fences=[{'seq': 1, 'hash': 'committed'}, fence], committed={1},
            prepared=[{'seq': 2, 'record': fence}], head=(2, 'prepared'))
        self.assertFalse(restore_lock(record))
        record.prepared[0].update(action='control_restore_confirm', space={'restoring': True})
        self.assertTrue(restore_lock(record))
        record.prepared.clear()
        self.assertTrue(restore_lock(record))
        record.head = (0, '')
        self.assertTrue(restore_lock(record))
        record.head = (1, 'changed')
        self.assertTrue(restore_lock(record))

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

class FailedOwnerRead(unittest.TestCase):
    setUp = OwnerStageThreeFacts.setUp
    tearDown = OwnerStageThreeFacts.tearDown

    def test_daemon_error_survives_unavailable_sources_without_a_ram_snapshot(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from aresos_control.common import Refused
        from aresos_control.daemon import Daemon
        engine = SimpleNamespace(store=self.store,
            pending=Mock(side_effect=Refused('storage_error', 'Synthetic unavailable owner sources')))
        result = Daemon.error_result(SimpleNamespace(engine=engine),
            Refused('storage_error', 'Synthetic request failure'), True)
        self.assertFalse(result['ok'])
        self.assertEqual(result['error']['code'], 'storage_error')
        self.assertIn('Committed owner facts could not be read', result['pending']['unavailable'])
        self.assertFalse(hasattr(engine, '_last_pending'))

class RestoredNativeFacts(unittest.TestCase):
    setUp = OwnerStageThreeFacts.setUp
    tearDown = OwnerStageThreeFacts.tearDown

    def test_fence_only_filing_retains_warning_role_pages_and_original_open_epoch(self):
        from aresos_control.warnings import check_result
        from aresos_control.recovery import recovery_notices
        class Crash(BaseException):
            pass
        key = 'mail:filing:retained'
        source = {'id': 'retained', 'account': 'box', 'state': 'started', 'target': 'Target',
                  'context': {'command': 'MOVE', 'account': 'box'}, 'records': [], 'sources': []}
        self.store.write({key: source}, 'fixture', 'Synthetic open filing')
        epoch = self.store.owner_projection.open_epoch(key)
        result = {**source, 'state': 'partial', 'observed_role': 'Trash'}
        notices, identity = check_result(self.store, result, key, 'filing',
            {'target': 'Target', 'role': 'Trash'}, {'reason': 'The target Target is now Trash. Nothing was deleted.',
                'filing_id': 'retained', 'folders': ['Target'], 'message_count': 0})
        pages = {'mail:filing-locations:' + identity + ':meta': {'pages': 1, 'total_messages': 0},
                 'mail:filing-locations:' + identity + ':0': {'locations': [], 'fragments': []}}
        def crash(point):
            if point == 'journal_appended':
                raise Crash()
        self.store.checkpoint = crash
        with self.assertRaises(Crash):
            self.store.write({key: result, **notices, **pages}, 'mail_move', 'Synthetic observed warning')
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.store.checkpoint = crash
        with self.assertRaises(Crash):
            self.store.confirm_restore()
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.store.confirm_restore()
        self.assertEqual('started', self.store.get(key)['state'])
        self.assertEqual(epoch, self.store.owner_projection.open_epoch(key))
        self.assertIn('Trash', self.store.get('notice:' + identity)['untrusted_content']['reason'])
        self.assertTrue(any(n.get('check_only') for n in recovery_notices(self.store)))
        repeated, same_identity = check_result(self.store, self.store.get(key), key, 'filing',
            {'target': 'Target', 'role': 'Trash'}, {'reason': 'Repeated unchanged warning'})
        self.assertEqual(identity, same_identity)
        self.assertFalse(repeated)
        for page, value in pages.items():
            self.assertEqual(value, self.store.get(page))
        record = decode(self.root / 'state', self.root / 'evidence')
        self.assertEqual('Trash', record.owner_rows['notice:' + identity]['observed_role'])

    def test_each_native_occurrence_uses_its_own_original_role(self):
        from aresos_control.warnings import check_result
        key = 'mail:filing:roles'
        source = {'id': 'roles', 'account': 'box', 'state': 'partial', 'target': 'Target'}
        identities = []
        for role in ('Trash', 'Sent'):
            source['observed_role'] = role
            changes, identity = check_result(self.store, source, key, 'filing', {'role': role},
                {'reason': 'The target Target is now ' + role + '. Nothing was deleted.', 'filing_id': 'roles'})
            self.store.write({key: source, **changes}, 'fixture', 'Synthetic changed warning evidence')
            identities.append((identity, role))
        from aresos_control.owner_projection import fact
        view = owner_view(self.store)
        for identity, role in identities:
            row = self.store.get('notice:' + identity)
            inflated = view.inflate('notice:' + identity, fact('notice:' + identity, row))
            self.assertIn('now ' + role, inflated['untrusted_content']['reason'])

    def restore_backup(self, backup):
        self.store.close()
        (self.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.store.locked)
        self.store.confirm_restore()

    def test_free_context_recipient_hashes_survive_two_older_restores(self):
        from contextlib import closing
        backup = self.root / 'older.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            self.store.db.backup(db)
        key = 'intent:native'
        self.store.write({key: {'id': 'recovery-native', 'app': 'mail', 'action': 'mail_draft_save',
            'state': 'started', 'context_version': 1, 'context': {'format': 1, 'command': 'APPEND',
            'account': 'box', 'recipients': ['one@mail.invalid'], 'destination': 'Drafts'}}},
            'fixture', 'Synthetic native context')
        expected = dict(self.store.owner_projection.iter_items())[key]['context']
        for _ in range(2):
            self.restore_backup(backup)
            actual = dict(self.store.owner_projection.iter_items())[key]
            self.assertEqual(expected, actual['context'])
            self.assertNotIn('_owner_encoded', actual)

    def test_operation_stage_codes_and_context_survive_older_restore(self):
        from contextlib import closing
        from aresos_control.common import digest
        backup = self.root / 'older.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            self.store.db.backup(db)
        identity = self.store.generation + ':' + 'a' * 32
        key = 'op:' + identity
        op = {'id': identity, 'generation': self.store.generation, 'input_hash': digest(identity),
            'app': 'mail', 'action': 'mail_send', 'state': 'done', 'expires': 0,
            'approval': {'question': 'Synthetic approval', 'description': {'action': 'mail_send'}},
            'payload': {}, 'reason': 'Synthetic completion', 'context_version': 1,
            'context': {'command': 'SMTP', 'account': 'box', 'recipients': ['one@mail.invalid']},
            'stages': {'rcpt:one@mail.invalid': 'accepted:250',
                       'sent_copy_warning': 'Sent contains 2 copies with this Message-ID.'}}
        self.store.write({key: op}, 'fixture', 'Synthetic native stages')
        expected = dict(self.store.owner_projection.iter_items())[key]
        self.restore_backup(backup)
        actual = dict(self.store.owner_projection.iter_items())[key]
        self.assertEqual(expected['context'], actual['context'])
        self.assertEqual(expected['stages'], actual['stages'])
        self.assertEqual('unknown', actual['state'])
        from aresos_control.engine import Engine
        restored = self.store.get(key)
        self.assertNotIn('question', restored['approval'])
        public = Engine.public_operation(None, restored)
        self.assertEqual('mail_send', public['approval']['description']['action'])
        self.assertNotIn('_owner_encoded', public)
        self.assertNotIn('text', public['approval']['description'])

    def test_second_crash_during_fence_only_restore_cannot_publish_export_completion(self):
        class Crash(BaseException):
            pass
        key = 'export:interrupted'
        transfer = {'app': 'testapp', 'sha256': 'a' * 64, 'size': 24, 'created_blob': False}
        self.store.write({key: transfer}, 'fixture', 'Synthetic open export')
        def crash_after_fence(point):
            if point == 'journal_appended':
                raise Crash()
        self.store.checkpoint = crash_after_fence
        with self.assertRaises(Crash):
            self.store.write({key: None}, 'fixture', 'Synthetic unresolved publication')
        original = (self.root / 'evidence/operations.jsonl').read_bytes()
        abandoned = self.store.sequence
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.store.locked)
        self.store.checkpoint = crash_after_fence
        with self.assertRaises(Crash):
            self.store.confirm_restore()
        self.assertTrue((self.root / 'evidence/operations.jsonl').read_bytes().startswith(original))
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.store.locked)
        self.assertEqual(transfer, dict(self.store.owner_projection.iter_items())[key])
        self.store.confirm_restore()
        record = decode(self.root / 'state', self.root / 'evidence')
        self.assertNotIn(abandoned, record.committed)
        self.assertFalse(record.locked)
        self.assertEqual(transfer, record.owner_rows[key])
        self.assertIn(key, self.store.ledger.holds)
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertFalse(self.store.locked)
        self.assertEqual(transfer, dict(self.store.owner_projection.iter_items())[key])

    def test_committed_export_removal_survives_an_older_backup(self):
        from contextlib import closing
        key = 'export:finished'
        self.store.write({key: {'app': 'testapp', 'sha256': 'b' * 64, 'size': 24,
                               'created_blob': False}}, 'fixture', 'Synthetic open export')
        backup = self.root / 'with-export.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            self.store.db.backup(db)
        self.store.write({key: None}, 'fixture', 'Synthetic committed publication')
        self.restore_backup(backup)
        self.assertIsNone(self.store.get(key))
        self.assertNotIn(key, dict(self.store.owner_projection.iter_items()))

    def test_retained_positive_warning_keeps_its_binding_after_fence_only_restore(self):
        from aresos_control.common import digest
        class Crash(BaseException):
            pass
        identity = self.store.generation + ':' + 'c' * 32
        key = 'op:' + identity
        op = {'id': identity, 'generation': self.store.generation, 'input_hash': digest(identity),
              'app': 'mail', 'action': 'mail_send', 'state': 'done', 'expires': 0, 'stages': {},
              'approval': {'description': {'action': 'mail_send'}}, 'payload': {}, 'reason': 'Synthetic completion'}
        self.store.write({key: op}, 'fixture', 'Synthetic operation')
        self.mail.register_sent_check(op)
        def crash(point):
            if point == 'journal_appended':
                raise Crash()
        self.store.checkpoint = crash
        matches = [{'uid': 1}, {'uid': 2}]
        with self.assertRaises(Crash):
            self.mail.sent_copy_count(op, matches, commit_clean=True)
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.store.confirm_restore()
        self.mail = Mail(self.store, None)
        op = self.store.get(key)
        self.mail.register_sent_check(op)
        self.mail.sent_copy_count(op, matches, commit_clean=True)
        warnings = [(key, value) for key, value in self.store.items('notice:') if value.get('check_kind') == 'sent_copies']
        self.assertEqual(1, len(warnings))
        notice_key, notice = warnings[0]
        self.assertEqual('sent-' + digest(identity)[:32], notice['id'])
        notice['ack'] = True
        self.store.write({notice_key: notice}, 'mail_notice_ack', 'Synthetic acknowledgement')
        self.mail.register_sent_check(op)
        self.mail.sent_copy_count(op, matches, commit_clean=True)
        self.assertTrue(self.store.get(notice_key)['ack'])
        self.assertEqual(1, sum(value.get('check_kind') == 'sent_copies' for _, value in self.store.items('notice:')))


if __name__ == '__main__':
    unittest.main()
