"""Independent oracle tests run in the base container, without a mail server."""
from contextlib import closing
import ast
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from owner_state_oracle.model import Fact, Oracle
from owner_state_oracle.records import Record, canonical, decode, fingerprint
from owner_state_oracle.compare import pages


class OwnerOracle(unittest.TestCase):
    def test_expectation_imports_are_standard_library_only(self):
        root = Path(__file__).resolve().parents[1] / 'owner_state_oracle'
        allowed = {'contextlib', 'copy', 'dataclasses', 'hashlib', 'json', 'pathlib', 'sqlite3', 'shutil', 'tempfile', 'model', 'records'}
        for name in ('__init__.py', 'records.py', 'model.py', 'compare.py'):
            tree = ast.parse((root / name).read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(a.name.split('.')[0] in allowed for a in node.names), (name, ast.dump(node)))
                if isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split('.')[0], allowed, (name, ast.dump(node)))
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {'__import__', 'eval', 'exec'})

    def recorded(self):
        oracle = Oracle()
        oracle.call('mail_operation_status', {'operation_id': 'g:send'}, 123, {'at': 'journal.write'})
        copies = [{'account': 'box', 'folder': 'Sent', 'uidvalidity': 9, 'uid': uid, 'message_id': '<g.send@mail.aresos.invalid>'} for uid in (1, 2)]
        oracle.server('SENT', 'box', 'Sent', copies, {'Sent': ['\\Sent']}, source='op:g:send')
        oracle.reply({'ok': False}, delivered=False)
        record = Record(rows={'op:g:send': {'id': 'g:send', 'app': 'mail', 'state': 'done'}})
        return oracle, record

    def test_script_and_server_logs_derive_lost_duplicate_reply_without_notice_rows(self):
        oracle, record = self.recorded()
        expected = oracle.expected(record)
        self.assertEqual(len(expected), 1)
        fact = next(iter(expected))
        self.assertEqual((fact.source, fact.kind, fact.detail), ('op:g:send', 'sent_copies', '{"count":2}'))
        self.assertEqual(oracle.script[0]['reply'], 'lost')
        self.assertEqual(oracle.servers[0]['call'], oracle.script[0]['call'])

    def test_r1_memory_only_and_review19_and_round21_lost_duplicates_are_caught(self):
        for view in ('control_pending', 'mail catalogue', 'aresos log', 'passive'):
            oracle, record = self.recorded()
            with self.subTest(view=view), self.assertRaises(AssertionError):
                oracle.compare(view, oracle.expected(record), set())

    def test_r2_command_before_context_is_caught(self):
        oracle = Oracle()
        command = {'context': dict(account='box', identities=['m'], source='Source', destination='Target', roles={}, recipients=[])}
        with self.assertRaisesRegex(AssertionError, 'not committed before'):
            oracle.require_context(command, Record())
        oracle.require_context(command, Record(rows={'intent:x': command}))

    def test_r3_cached_refusal_is_caught(self):
        oracle = Oracle()
        oracle.call('mail_compose', {'text': 'local'}, 456, [])
        with self.assertRaises(AssertionError):
            oracle.compare('healthy-disk refusal', {Fact('request', 'allowed')}, {Fact('request', 'storage_limit')})

    def test_round27_check_closed_without_committed_result_is_caught(self):
        oracle = Oracle()
        record = Record(rows={'mail:rename:x': {'id': 'x', 'state': 'started', 'account': 'box'}})
        with self.assertRaises(AssertionError):
            oracle.compare('not yet checked', oracle.expected(record), set())

    def test_extras_and_each_view_fail_independently(self):
        oracle = Oracle()
        with self.assertRaises(AssertionError):
            oracle.compare('quiet', set(), {Fact('x', 'spurious')})
        for view in ('pending', 'catalogue', 'log', 'passive'):
            with self.subTest(view=view), self.assertRaises(AssertionError):
                oracle.compare(view, {Fact('x', 'recovery')}, set())

    def test_pages_drain_and_cannot_loop(self):
        calls = []
        def read(action, args):
            calls.append(dict(args))
            return {'ok': True, 'data': {'items': [len(calls)], 'cursor': 'next' if len(calls) == 1 else None}}
        self.assertEqual([p['items'] for p in pages(read, 'log')], [[1], [2]])
        with self.assertRaisesRegex(AssertionError, 'did not advance'):
            list(pages(lambda *_: {'ok': True, 'data': {'cursor': 'same'}}, 'log'))

    def test_same_evidence_ack_clean_and_recurrence_are_independent(self):
        oracle, record = self.recorded()
        record.rows['notice:n'] = {'id': 'n', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        first = oracle.expected(record)
        self.assertEqual(first, oracle.expected(record))
        record.events.append({'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:n': {**record.rows['notice:n'], 'ack': True}}})
        self.assertEqual(oracle.expected(record), set())
        record.events.append({'seq': 2, 'action': 'mail_sent_copy_check', 'set': {'op:g:send': {'sent_copy_check': {'clean': True}}}})
        oracle.server('SENT', 'box', 'Sent', oracle.servers[0]['identities'], source='op:g:send')
        record.rows['notice:new'] = {'id': 'new', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        self.assertEqual({f.occurrence for f in oracle.expected(record)}, {'new'})
        # Restore older working state must not resurrect n's acknowledgement.
        record.events = []
        oracle.servers = []
        self.assertNotIn('n', {f.occurrence for f in oracle.expected(record)})

    def disk(self, marker=True):
        temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[2] / '.work')
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        state, evidence = root / 'state', root / 'evidence'
        state.mkdir(); evidence.mkdir()
        row = {'format': 2, 'seq': 1, 'previous': '', 'time': 123, 'generation': 'g', 'operations': []}
        row['hash'] = fingerprint(row)
        event = {'seq': 1, 'time': 123, 'action': 'fixture', 'outcome': 'done', 'set': {'generation': 'g'}, 'record': row}
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            db.executescript('CREATE TABLE events(seq INTEGER,value TEXT); CREATE TABLE head(id INTEGER,seq INTEGER,hash TEXT);')
            db.execute('INSERT INTO events VALUES (?,?)', (1, canonical(event)))
            db.execute('INSERT INTO head VALUES (1,1,?)', (row['hash'],))
            db.commit()
        raw = canonical(row) + '\n'
        if marker:
            raw += canonical({'commit': 1, 'hash': row['hash']}) + '\n'
        (evidence / 'operations.jsonl').write_text(raw)
        return state, evidence

    def test_decoder_distinguishes_prepared_and_committed_without_kv(self):
        state, evidence = self.disk(False)
        record = decode(state, evidence)
        self.assertEqual(record.rows, {})
        self.assertEqual(len(record.prepared), 1)
        state, evidence = self.disk()
        self.assertEqual(decode(state, evidence).generation, 'g')

    def test_decoder_rejects_corruption_but_ignores_torn_tail(self):
        state, evidence = self.disk()
        path = evidence / 'operations.jsonl'
        raw = path.read_bytes()
        path.write_bytes(raw + b'{torn')
        self.assertEqual(decode(state, evidence).generation, 'g')
        path.write_bytes(raw.replace(b'"time":123', b'"time":124'))
        with self.assertRaisesRegex(ValueError, 'hash chain'):
            decode(state, evidence)

    def test_decoder_rejects_unsupported_format(self):
        state, evidence = self.disk()
        path = evidence / 'operations.jsonl'
        path.write_bytes(path.read_bytes().replace(b'"format":2', b'"format":999'))
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            decode(state, evidence)
