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
        allowed = {'contextlib', 'copy', 'dataclasses', 'hashlib', 'json', 'pathlib', 'sqlite3', 'shutil', 'tempfile', 'time', 'model', 'records'}
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

    def test_real_expectation_path_rejects_every_mutation_without_precommand_context(self):
        for command in ('DATA', 'APPEND', 'MOVE', 'COPY', 'STORE', 'EXPUNGE', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE'):
            oracle = Oracle()
            oracle.call('synthetic mutation', {}, 1)
            oracle.server(command, 'box', accepted=True, reply='lost')
            with self.subTest(command=command):
                self.assertTrue(oracle.context_errors(), command)

    def test_raw_trash_list_warns_even_if_production_claims_done_and_closed(self):
        oracle = Oracle()
        context = {'mail:rename:r': {'id': 'r', 'account': 'box', 'source': 'Source', 'target': 'Target', 'roles_before': {}}}
        oracle.call('mail_folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Target'}, 1)
        oracle.server('RENAME', 'box', roles={'Target': []}, arguments=['Source', 'Target'], committed_before=context)
        oracle.server('LIST', 'box', roles={'Target': ['\\Trash']})
        record = Record(rows={'mail:rename:r': {**context['mail:rename:r'], 'state': 'done', 'check_open': False}})
        self.assertTrue(any(f.kind == 'rename' and f.detail == '{"role":"Trash"}' for f in oracle.expected(record)))

    def test_bad_completion_without_server_acceptance_is_caught(self):
        oracle = Oracle()
        row = {'id': 'g:s', 'action': 'mail_send', 'state': 'done'}
        self.assertTrue(oracle.completion_errors(Record(rows={'op:g:s': row})))
        oracle.server('DATA', identities=[{'message_id': '<g.s@mail.aresos.invalid>'}])
        self.assertFalse(oracle.completion_errors(Record(rows={'op:g:s': row})))

    def test_filing_clean_ack_recurrence_uses_a_new_occurrence(self):
        for kind in ('rename', 'filing'):
            oracle = Oracle()
            source = 'mail:rename:r' if kind == 'rename' else 'mail:filing:r'
            evidence = {'target': 'Target', 'role': 'Trash'}
            first = {'id': 'old', 'source_key': source, 'check_kind': kind,
                     'evidence_fingerprint': fingerprint(evidence)}
            record = Record(rows={'notice:old': first})
            one = oracle.warning(source, kind, evidence, record)
            self.assertEqual(one.occurrence, 'old')
            record.events = [{'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:old': {**first, 'ack': True}}},
                {'seq': 2, 'action': 'mail_filing_check', 'set': {source: {'warning_checks': {kind: {'warning': False}}}}}]
            oracle.expected(record)
            record.rows['notice:new'] = {**first, 'id': 'new'}
            two = oracle.warning(source, kind, evidence, record)
            self.assertEqual(two.occurrence, 'new')
            self.assertNotEqual(one, two)

    def test_occurrence_binding_matches_evidence_not_last_unused_notice(self):
        oracle = Oracle()
        a, b = {'target': 'A', 'role': 'Trash'}, {'target': 'B', 'role': 'Drafts'}
        record = Record(rows={'notice:a': {'id': 'a', 'source_key': 'mail:rename:r', 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(a)},
                              'notice:b': {'id': 'b', 'source_key': 'mail:rename:r', 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(b)}})
        self.assertEqual(oracle.warning('mail:rename:r', 'rename', a, record).occurrence, 'a')

    def test_cached_refusal_mutation_uses_script_and_committed_transaction_state(self):
        oracle = Oracle()
        oracle.call('mail_compose', {}, 1, {'admission': 'full'})
        self.assertEqual(oracle.request_state(Record(), oracle.script[-1]), {Fact('request', 'storage_limit')})
        oracle.call('mail_compose', {}, 2, {})
        expected = oracle.request_state(Record(), oracle.script[-1])
        with self.assertRaises(AssertionError):
            oracle.compare('cached refusal mutation', expected, {Fact('request', 'storage_limit')})

    def test_working_check_closed_without_committed_result_cannot_change_expectations(self):
        state, evidence = self.disk()
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            event = json.loads(db.execute('SELECT value FROM events').fetchone()[0])
            event['set']['mail:rename:r'] = {'id': 'r', 'state': 'started', 'account': 'box'}
            db.execute('UPDATE events SET value=?', (canonical(event),))
            db.execute('CREATE TABLE kv(k TEXT,v TEXT)')
            db.execute('INSERT INTO kv VALUES (?,?)', ('mail:rename:r', canonical({'id': 'r', 'state': 'done', 'check_open': False})))
            db.commit()
        oracle = Oracle()
        expected = oracle.expected(decode(state, evidence))
        self.assertIn(Fact('mail:rename:r', 'recovery'), expected)
        with self.assertRaises(AssertionError):
            oracle.compare('premature check closure', expected, set())

    def test_wrong_passive_page_is_not_masked_by_healthy_pending_view(self):
        from owner_state_oracle.compare import compare_views
        oracle = Oracle()
        record = Record(rows={'op:a': {'id': 'a', 'app': 'mail', 'state': 'reserved'},
                              'op:b': {'id': 'b', 'app': 'mail', 'state': 'reserved'}})
        def read(action, args):
            return {'ok': True, 'pending': {'items': [{'operation_id': 'WRONG', 'state': 'reserved'}], 'total': 2, 'cursor': None}}
        with self.assertRaises(AssertionError):
            compare_views(read, oracle, lambda: record, oracle.compare)
