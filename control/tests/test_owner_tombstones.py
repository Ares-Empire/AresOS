"""Archive retirement must preserve a verifiable resolution across backup restore."""
import copy
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch

from aresos_control.archive import archive
from aresos_control.common import Refused, digest
from aresos_control.storage import Store

WORK = Path(__file__).resolve().parents[2] / '.work' / 'owner-tombstone-tests'
WORK.mkdir(parents=True, exist_ok=True)


class OwnerTombstones(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / 'state', self.root / 'evidence')

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def finished(self, number, ack=True):
        identity = self.store.generation + ':' + format(number, '032x')
        return {'id': identity, 'generation': self.store.generation, 'input_hash': digest(number),
                'app': 'testapp', 'action': 'testapp_send', 'state': 'done', 'expires': 0,
                'approval': {'description': {'action': 'testapp_send'}}, 'payload': {},
                'stages': {}, 'context_version': 1, 'reason': 'Synthetic finished send',
                'notice': True, 'ack': ack}

    def write(self, rows):
        with patch('time.time', return_value=1000):
            self.store.write(rows, 'fixture', 'Synthetic committed lifecycle input')

    def archive(self):
        return archive(self.store, 1001)

    def test_tombstone_with_two_sent_occurrences_is_at_most_128_bytes(self):
        op = self.finished(1)
        key = 'op:' + op['id']
        op['notice'] = False
        base = 'sent-' + digest(op['id'])[:32]
        ids = [base, base + '-' + 'a' * 32]
        notices = {'notice:' + identity: {'id': identity, 'app': 'testapp',
                   'state': 'partial', 'ack': True, 'source_key': key,
                   'untrusted_content': {'operation_id': op['id'], 'message_count': 2}}
                   for identity in ids}
        self.write({key: op, **notices})
        self.archive()
        stone, size = next((stone, size) for _, stone, _, size in self.store.owner_projection.stones()
                           if stone and stone['key'] == key)
        self.assertEqual(sorted(ids), sorted(stone['ack']))
        self.assertLessEqual(size, 128)
        print('TOMBSTONE two acknowledged warnings:', size, 'bytes including framing')

    def test_one_run_retires_clean_send_beside_a_new_duplicate_warning(self):
        from types import SimpleNamespace
        clean, duplicate = self.finished(1), self.finished(2)
        for row in (clean, duplicate):
            row.update(app='mail', action='mail_send',
                       payload={'composition': {'mail': {'account': 'box'}}},
                       sent_copy_check={'state': 'checked', 'clean': True, 'count': 1})
        self.write({'op:' + row['id']: row for row in (clean, duplicate)})
        reads = []
        def matches(account, mid):
            reads.append(mid)
            count = 1 if mid == clean['id'] else 2
            return [{'account': 'box', 'folder': 'Sent', 'uidvalidity': 1,
                     'uid': n, 'message_id': mid} for n in range(1, count + 1)]
        mail = SimpleNamespace(account=lambda *a, **k: {'id': 'box'},
                               message_id=lambda identity: identity, sent_matches=matches)
        result = archive(self.store, 1001, mail)
        self.assertEqual(1, result['operations'])
        self.assertEqual(sorted([clean['id'], duplicate['id']]), sorted(reads))
        self.assertIsNone(self.store.get('op:' + clean['id']))
        self.assertIsNotNone(self.store.get('op:' + duplicate['id']))
        notices = self.store.items('notice:')
        self.assertEqual(1, len(notices))
        self.assertFalse(notices[0][1]['ack'])
        self.assertTrue(any(stone and stone['key'] == 'op:' + clean['id']
                            for _,stone,_,_ in self.store.owner_projection.stones()))
        archive(self.store, 1001, mail)
        self.assertEqual([key for key,_ in notices], [key for key,_ in self.store.items('notice:')])

    def test_only_the_six_record_kinds_are_written_and_no_readable_event_copy(self):
        from aresos_control.owner_projection import KINDS
        self.assertEqual(set(KINDS), {'context', 'resolution', 'check-open', 'check-result', 'acknowledgement', 'tombstone'})
        op = self.finished(1)
        self.write({'op:' + op['id']: op})
        for _, data, _, _ in self.store.owner_projection._records(self.store.owner_projection.path):
            for row in data.values():
                self.assertIn(row['kind'], KINDS)
                self.assertNotIn('record', row)
                self.assertNotIn('approval', row.get('facts') or {})
                self.assertNotIn('reason', row.get('facts') or {})
        self.assertFalse((self.store.evidence_dir / 'owner-source.bin').exists())
        self.assertNotIn(b'Synthetic finished send', self.store.owner_projection.path.read_bytes())

    def test_committed_projection_tail_removal_fails_loudly(self):
        before = self.store.owner_projection.path.read_bytes()
        self.write({'intent:open': {'id': 'recovery-open', 'app': 'testapp', 'state': 'started'}})
        self.store.owner_projection.path.write_bytes(before)
        with self.assertRaises(Refused) as error:
            list(self.store.owner_projection.iter_items())
        self.assertEqual('evidence_corrupt', error.exception.code)

    def test_re_read_export_precedes_retirement_and_failure_keeps_live_history(self):
        op = self.finished(1)
        self.write({'op:' + op['id']: op})
        before = self.store.owner_projection.path.read_bytes()
        with patch.object(self.store.owner_projection, '_export', side_effect=Refused('evidence_corrupt', 'Synthetic reread failure')):
            with self.assertRaises(Refused):
                self.archive()
        self.assertTrue(self.store.owner_projection.path.read_bytes().startswith(before))
        self.assertFalse(self.store.owner_projection.tombstones.exists())
        self.store.owner_projection.compact()
        self.assertTrue(self.store.owner_projection.tombstones.exists())

    def test_tampered_missing_or_substituted_export_fails_loudly(self):
        op = self.finished(1)
        self.write({'op:' + op['id']: op})
        result = self.archive()
        path = Path(result['path'])
        original = path.read_bytes()
        for raw in (None, original.replace(b'Synthetic finished send', b'Synthetic tampered send'), b'{}\n'):
            with self.subTest(raw=raw is None):
                if raw is None:
                    path.unlink()
                else:
                    path.write_bytes(raw)
                with self.assertRaises(Refused) as error:
                    list(self.store.owner_projection.iter_items())
                self.assertEqual('evidence_corrupt', error.exception.code)
                path.write_bytes(original)

    def test_one_and_1001_archived_sends_have_same_live_size(self):
        def add(start, end):
            for offset in range(start, end, 100):
                rows = [self.finished(n) for n in range(offset, min(offset + 100, end))]
                self.write({'op:' + row['id']: row for row in rows})
                self.archive()
        add(1, 2)
        one = self.store.owner_projection.path.stat().st_size
        add(2, 1002)
        self.assertEqual(one, self.store.owner_projection.path.stat().st_size)
        stones = [row for _, row, _, _ in self.store.owner_projection.stones() if row and row['key'].startswith('op:')]
        self.assertEqual(1001, len(stones))
        print('TOMBSTONE live bound:', one, 'bytes after 1 and 1001 archived synthetic sends')

    def test_unacknowledged_warning_open_check_and_unresolved_work_stay_live(self):
        op = self.finished(1, ack=False)
        rows = {'op:' + op['id']: op,
                'intent:open': {'id': 'recovery-open', 'app': 'testapp', 'state': 'started'},
                'mail:filing:check': {'id': 'check', 'state': 'done', 'check_open': True},
                'notice:warning': {'id': 'warning', 'app': 'mail', 'ack': False, 'state': 'partial',
                                   'source_key': 'mail:filing:warning', 'untrusted_content': {'reason': 'Synthetic warning'}},
                'mail:filing:warning': {'id': 'warning', 'state': 'done'}}
        self.write(rows)
        self.archive()
        live = {key for _, changes, _, _ in self.store.owner_projection._records(self.store.owner_projection.path) for key in changes}
        self.assertTrue(set(rows) <= live)
        self.assertIsNotNone(self.store.get('op:' + op['id']))

    def test_compact_without_confirmed_export_keeps_every_record(self):
        op = self.finished(1)
        self.write({'op:' + op['id']: op})
        before = self.store.owner_projection.path.read_bytes()
        self.store.owner_projection.compact()
        self.assertEqual(before, self.store.owner_projection.path.read_bytes())
        self.assertFalse(self.store.owner_projection.tombstones.exists())

    def test_newer_unexported_check_keeps_full_projection_history(self):
        op = self.finished(1)
        key = 'op:' + op['id']
        self.write({key: op})
        def checkpoint(label):
            if label == 'archive_exported':
                newer = copy.deepcopy(op)
                newer['sent_copy_check'] = {'state': 'checked', 'clean': True}
                with patch('time.time', return_value=1002):
                    self.store.write({key: newer}, 'fixture', 'Synthetic newer check result')
        self.store.checkpoint = checkpoint
        self.archive()
        self.assertIn(key, {k for _, changes, _, _ in self.store.owner_projection._records(self.store.owner_projection.path) for k in changes})
        if self.store.owner_projection.tombstones.exists():
            self.assertFalse(any(stone['key'] == key for _, stone, _, _ in self.store.owner_projection.stones() if stone))

    def test_source_and_projection_read_every_fixture_fact_without_sqlite_or_index(self):
        rows = {'intent:open': {'id': 'recovery-open', 'app': 'testapp', 'state': 'started'},
                'notice:warning': {'id': 'warning', 'app': 'testapp', 'state': 'partial', 'ack': False,
                                  'source_key': 'intent:open', 'untrusted_content': {'reason': 'Synthetic warning'}},
                'mail:account:incomplete': {'id': 'incomplete', 'ready': False, 'onboarded': False}}
        self.write(rows)
        from aresos_control.owner_projection import fact, selected
        expected = {k: fact(k,v) for k,v in self.store.iter_items('') if selected(k)}
        compact = dict(self.store.owner_projection.iter_items())
        class FailedReader:
            def execute(self, *args):
                raise sqlite3.OperationalError('database or disk is full')
        with patch.object(self.store, 'db', FailedReader()), patch.object(self.store, 'index', FailedReader()):
            self.assertEqual(expected, dict(self.store.owner_projection.iter_items()))
            self.assertEqual(compact, dict(self.store.owner_projection.iter_items()))
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertTrue(set(rows) <= dict(self.store.owner_projection.iter_items()).keys())

    def test_tombstone_publication_failure_does_not_drop_live_history(self):
        op = self.finished(1)
        self.write({'op:' + op['id']: op})
        before = self.store.owner_projection.path.read_bytes()
        replace = __import__('os').replace
        def failed(source, destination):
            if Path(destination) == self.store.owner_projection.tombstones:
                raise OSError('Synthetic tombstone publication failure')
            return replace(source, destination)
        with patch('aresos_control.owner_projection.os.replace', side_effect=failed):
            with self.assertRaises(OSError):
                self.archive()
        self.assertTrue(self.store.owner_projection.path.read_bytes().startswith(before))
        self.assertFalse(self.store.owner_projection.tombstones.exists())
        self.assertEqual([], list(self.store.evidence_dir.glob('*.partial')))

    def test_free_change_check_warning_and_ack_survive_older_backup(self):
        identity = 'b' * 32
        key = 'mail:rename:' + identity
        started = {'id': identity, 'state': 'started', 'account': 'box',
                   'source': 'Source', 'target': 'Target', 'message_count': 1,
                   'context_version': 1, 'context': {'command': 'RENAME', 'account': 'box',
                   'identities': [{'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1}],
                   'source': 'Source', 'destination': 'Target', 'roles': {}, 'recipients': []}}
        self.write({key: started})
        backup = self.root / 'free-old.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            self.store.db.backup(db)
        checked = {**started, 'state': 'partial', 'observed_role': 'Trash',
                   'check_open': False, 'warning_checks': {'rename': {'warning': True,
                   'fingerprint': digest(['Target', 'Trash']), 'occurrence_id': identity}}}
        notice = {'id': identity, 'app': 'mail', 'state': 'partial', 'ack': False,
                  'source_key': key, 'check_kind': 'rename',
                  'evidence_fingerprint': digest(['Target', 'Trash']),
                  'untrusted_content': {'filing_id': identity, 'intent_key': key,
                                        'message_count': 1, 'reason': 'Inside Trash; nothing was deleted.'}}
        self.write({key: checked, 'notice:' + identity: notice})
        def restore():
            self.store.close()
            (self.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
            self.store = Store(self.root / 'state', self.root / 'evidence')
            self.assertTrue(self.store.locked)
            self.store.confirm_restore()
        restore()
        self.assertFalse(self.store.get('notice:' + identity)['ack'])
        self.assertEqual('Trash', self.store.get(key)['observed_role'])
        self.assertFalse(self.store.get(key)['check_open'])
        notice = self.store.get('notice:' + identity)
        notice['ack'] = True
        self.write({'notice:' + identity: notice})
        restore()
        self.assertTrue(self.store.get('notice:' + identity)['ack'])
        self.assertEqual('Trash', self.store.get(key)['observed_role'])
        self.assertFalse(self.store.get(key)['check_open'])

    def test_older_backup_cannot_resurrect_acknowledged_warning_or_finished_work(self):
        op = self.finished(1, ack=False)
        notice = {'id': 'warning', 'app': 'testapp', 'ack': False, 'state': 'partial',
                  'source_key': 'op:' + op['id'], 'untrusted_content': {'reason': 'Synthetic warning'}}
        self.write({'op:' + op['id']: op, 'notice:warning': notice})
        backup = self.root / 'old.sqlite'
        with closing(sqlite3.connect(backup)) as db:
            self.store.db.backup(db)
        op['ack'], notice['ack'] = True, True
        self.write({'op:' + op['id']: op, 'notice:warning': notice})
        self.archive()
        stones = [stone for _, stone, _, _ in self.store.owner_projection.stones() if stone]
        self.assertEqual(sorted(['warning', op['id']]), sorted(next(stone['ack'] for stone in stones if stone['key'] == 'op:' + op['id'])))
        self.store.close()
        (self.root / 'state/control.sqlite').write_bytes(backup.read_bytes())
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertTrue(self.store.locked)
        self.store.confirm_restore()
        self.assertIsNone(self.store.get('op:' + op['id']))
        self.assertTrue(self.store.get('notice:warning')['ack'])
        before = dict(self.store.owner_projection.iter_items())
        self.store.close()
        self.store = Store(self.root / 'state', self.root / 'evidence')
        self.assertEqual(before, dict(self.store.owner_projection.iter_items()))


if __name__ == '__main__':
    unittest.main()
