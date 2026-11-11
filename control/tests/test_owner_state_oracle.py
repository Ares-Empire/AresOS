"""Independent oracle tests run in the base container, without a mail server."""
from contextlib import closing
import ast
import copy
import json
import hashlib
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

from owner_state_oracle.model import Fact, Oracle
from owner_state_oracle.records import Record, canonical, decode, fingerprint
from owner_state_oracle.compare import pages


def empty_scan(oracle, listing, sources):
    listing['mailboxes'] = {name: [] for name in listing['roles']}
    for name in listing['roles']:
        oracle.server('SELECT', listing.get('account'), name)
        oracle.server('SEARCH', listing.get('account'), name, arguments=[None, 'ALL'], response_text=[''])
    oracle.server('SCAN_RESULT', listing.get('account'), before_seq=listing.get('before_seq', 0), check_sources=sources,
                  scan_start=next(i for i, event in enumerate(oracle.servers) if event is listing))


class OwnerOracle(unittest.TestCase):
    def test_expectation_imports_are_standard_library_only(self):
        root = Path(__file__).resolve().parents[1] / 'owner_state_oracle'
        modules = {'__init__', 'records', 'model', 'compare', 'context', 'gaps', 'local', 'identity', 'caller_capture', 'resolutions', 'perturb', 'effects', 'projection'}
        def validate(source):
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    self.assertTrue(all(a.name.split('.')[0] in sys.stdlib_module_names - {'builtins', 'importlib'} for a in node.names), ast.dump(node))
                if isinstance(node, ast.ImportFrom):
                    if node.level:
                        self.assertEqual(node.level, 1)
                        self.assertIn(node.module, modules)
                        self.assertTrue((root / (node.module + '.py')).is_file())
                    else:
                        self.assertIn(node.module.split('.')[0], sys.stdlib_module_names - {'builtins', 'importlib'})
                if isinstance(node, (ast.Name, ast.Attribute, ast.Constant)):
                    value = node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else node.value
                    if isinstance(value, str):
                        self.assertNotIn(value, {'__import__', '__builtins__', 'eval', 'exec', 'compile', 'import_module'})
        for name in modules:
            validate((root / (name + '.py')).read_text())
        for source in ("builtins.__import__('aresos_control')", "getattr(builtins, '__import__')('aresos_control')",
                       "from builtins import __import__ as load", "import records", "from records import decode",
                       "from ..aresos_control import storage", "from .driver import Driver"):
            with self.assertRaises(AssertionError, msg=source):
                validate(source)

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
        self.assertEqual(len(expected), 2)
        fact = next(f for f in expected if f.kind == 'sent_copies')
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
        restarts = []
        def changed(*_):
            restarts.append(True)
            return {'ok': True, 'data': {'page_changed': True, 'cursor': str(len(restarts))}}
        with self.assertRaisesRegex(AssertionError, 'Nonconvergent changed catalogue'):
            list(pages(changed, 'log'))
        self.assertEqual(len(restarts), 4)

    def test_same_evidence_ack_clean_and_recurrence_are_independent(self):
        oracle, record = self.recorded()
        record.rows['notice:n'] = {'id': 'n', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        first = oracle.expected(record)
        self.assertEqual(first, oracle.expected(record))
        oracle.call('mail_notice_ack', {'operation_id': 'n' if 'notice:n' in record.rows else 'old'}, 123)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        record.events.append({'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:n': {**record.rows['notice:n'], 'ack': True}}})
        self.assertEqual(oracle.expected(record), set())
        record.events.append({'seq': 2, 'action': 'mail_sent_copy_check', 'set': {'op:g:send': {**record.rows['op:g:send'], 'sent_copy_check': {'state': 'checked', 'clean': True}}}})
        oracle.call('mail_operation_status', {'operation_id': 'g:send'}, 124)
        oracle.script[-1]['end_seq'] = 2
        oracle.server('SENT', 'box', 'Sent', oracle.servers[0]['identities'][:1], source='op:g:send', before_seq=1)
        self.assertEqual(oracle.expected(record), set())
        oracle.call('mail_operation_status', {'operation_id': 'g:send'}, 125)
        oracle.server('SENT', 'box', 'Sent', oracle.servers[0]['identities'], source='op:g:send', before_seq=2)
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
        for command in ('DATA', 'APPEND', 'MOVE', 'COPY', 'STORE', 'EXPUNGE', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE', 'CONFIGURE'):
            oracle = Oracle()
            oracle.call('synthetic mutation', {}, 1)
            oracle.server(command, 'box', accepted=True, reply='lost')
            with self.subTest(command=command):
                self.assertTrue(oracle.context_errors(), command)

    def test_raw_trash_list_warns_even_if_production_claims_done_and_closed(self):
        oracle = Oracle()
        context = {'mail:rename:r': {'id': 'r', 'account': 'box', 'source': 'Source', 'target': 'Target', 'roles_before': {}, 'state': 'started'}}
        oracle.call('mail_folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Target'}, 1)
        oracle.server('RENAME', 'box', roles={'Target': []}, arguments=['Source', 'Target'], committed_before=context, created_before={'mail:rename:r': 1}, call_start_seq=0)
        oracle.server('LIST', 'box', roles={'Target': ['\\Trash']})
        record = Record(rows={'mail:rename:r': {**context['mail:rename:r'], 'state': 'done', 'check_open': False}})
        self.assertTrue(any(f.kind == 'rename' and f.detail == '{"role":"Trash"}' for f in oracle.expected(record)))

    def test_bad_completion_without_server_acceptance_is_caught(self):
        oracle = Oracle()
        row = {'id': 'g:s', 'action': 'mail_send', 'state': 'done'}
        self.assertTrue(oracle.completion_errors(Record(rows={'op:g:s': row})))
        oracle.call('mail_send', {'operation_id': 'g:s', 'description': {}}, 1)
        oracle.server('DATA', identities=[{'message_id': '<g.s@mail.aresos.invalid>'}],
                      committed_before={'op:g:s': {**row, 'state': 'submitting'}})
        self.assertTrue(oracle.completion_errors(Record(rows={'op:g:s': row})))
        oracle.server('SENT', folder='Sent', roles={'Sent': ['\\Sent']},
                      identities=[{'message_id': '<g.s@mail.aresos.invalid>'}], source='op:g:s')
        self.assertFalse(oracle.completion_errors(Record(rows={'op:g:s': row})))

    def test_preflight_reason_uses_evidence_before_this_calls_data(self):
        for prior_data, wanted in ((False, 'Far-side submission evidence already exists; inspect evidence, never submit again.'),
                                   (True, 'Submission outcome uncertain; inspect evidence, never retry.')):
            oracle = Oracle()
            oracle.call('mail_send', {'operation_id': 'g:s'}, 1)
            oracle.script[-1].update(start_seq=0, end_seq=3)
            if prior_data:
                oracle.server('DATA', source='op:g:s', before_seq=1,
                    identities=[{'message_id': '<g.s@mail.aresos.invalid>'}],
                    committed_before={'op:g:s': {'id': 'g:s', 'state': 'submitting', 'action': 'mail_send'}})
            oracle.server('SENT', source='op:g:s', before_seq=2,
                identities=[{'message_id': '<g.s@mail.aresos.invalid>'}])
            state, reason = oracle.outcome({'id': 'g:s', 'state': 'unknown'}, {'seq': 3, 'action': 'mail_send'})
            self.assertEqual(('unknown', wanted), (state, reason))

    def test_onboarding_rcpt_without_data_needs_one_current_account_bound_probe(self):
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new'}, 1)
        key = 'op:g:probe'
        row = {'action': 'mail_send', 'state': 'submitting',
               'payload': {'composition': {'mail': {'account': 'new'}}}}
        event = oracle.server('RCPT', account='new', recipients=['owner@mail.invalid'],
            smtp_transaction=1, before_seq=3, call_start_seq=1,
            committed_before={key: row}, created_before={key: 2})
        self.assertIn(event, oracle.operation_events(key, 4))
        event['created_before'][key] = 1
        self.assertNotIn(event, oracle.operation_events(key, 4))
        event['created_before'][key] = 2
        event['committed_before']['op:g:other'] = row
        event['created_before']['op:g:other'] = 2
        self.assertNotIn(event, oracle.operation_events(key, 4))

    def test_unavailable_filing_result_needs_independent_failure_and_an_open_check(self):
        oracle = Oracle()
        oracle.call('mail_move', {}, 1, {'trace': [(1, 'file.write', 'ENOSPC')]})
        oracle.script[-1].update(start_seq=0, end_seq=2)
        row = {'state': 'started', 'check_open': True, 'role_check_unavailable': True,
               'observed_role': 'an unverified role'}
        event = {'seq': 2, 'action': 'mail_filing_check'}
        self.assertTrue(oracle.unavailable_filing_result('mail:filing:f', row, event))
        oracle.script[-1]['faults'] = {}
        self.assertFalse(oracle.unavailable_filing_result('mail:filing:f', row, event))
        self.assertTrue(any(f.kind == 'false-unavailable-result' for f in oracle.lifecycle_errors))

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
            oracle.call('mail_notice_ack', {'operation_id': 'old'}, 1)
            oracle.script[-1].update(start_seq=0, end_seq=1)
            record.events = [{'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:old': {**first, 'ack': True}}},
                {'seq': 2, 'action': 'mail_filing_check', 'set': {source: {'warning_checks': {kind: {'warning': False}}}}}]
            oracle.call('filing check', {}, 2)
            oracle.script[-1]['end_seq'] = 2
            listing = oracle.server('LIST', before_seq=1, check_sources=[source], roles={'Target': [], 'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']})
            if kind == 'filing':
                empty_scan(oracle, listing, [source])
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

    def test_known_gap_requires_exact_failure_and_rejects_unexpected_pass(self):
        from owner_state_oracle.gaps import Gaps
        recorded = Gaps(recording=True)
        check = recorded.checker('named-case')
        check('page-equality', {Fact('source', 'warning')}, set())
        check.finish()
        strict = Gaps(recording=True)
        strict.recording, strict.entries = False, copy.deepcopy(recorded.entries)
        check = strict.checker('named-case')
        check('page-equality', {Fact('source', 'warning')}, set())
        check.finish()
        self.assertEqual(strict.seen, {'named-case/page-equality'})
        check = strict.checker('named-case')
        check('page-equality', set(), set())
        with self.assertRaisesRegex(AssertionError, 'Unexpected pass'):
            check.finish()
        check = strict.checker('named-case')
        check('page-equality', {Fact('source', 'warning')}, {Fact('other', 'spurious')})
        with self.assertRaisesRegex(AssertionError, 'Known gap changed'):
            check.finish()

    def test_missing_search_and_lost_working_row_do_not_erase_registered_duplicate_expectation(self):
        oracle = Oracle()
        operation = {'id': 'g:s', 'app': 'mail', 'state': 'done', 'payload': {'composition': {'mail': {'account': 'box'}}}}
        record = Record(rows={'mail:account:box': {'special': {'sent': 'Sent', 'drafts': 'Drafts', 'trash': 'Trash'}}},
            events=[{'seq': 1, 'time': 1, 'action': 'mail_send', 'set': {'op:g:s': operation}}])
        oracle.call('control_pending', {}, 2)
        oracle.server('FIXTURE_STATE', roles={'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']},
            mailboxes={'Sent': [{'account': 'box', 'folder': 'Sent', 'uidvalidity': 1, 'uid': uid,
                'message_id': '<g.s@mail.aresos.invalid>'} for uid in (1, 2)]})
        oracle.reply({'ok': True})
        expected = oracle.expected(record, live=True)
        self.assertTrue(any(f.kind == 'sent_copies' for f in expected))
        with self.assertRaises(AssertionError):
            oracle.compare('omitted evidence read mutation', expected, set())

    def test_known_gap_cannot_be_hidden_by_omitting_its_view(self):
        from owner_state_oracle.gaps import Gaps
        ledger = Gaps(recording=True)
        check = ledger.checker('case')
        check('warning', {Fact('source', 'warning')}, set())
        check.finish()
        ledger.recording = False
        check = ledger.checker('case')
        with self.assertRaisesRegex(AssertionError, 'not executed'):
            check.finish()

    def test_false_production_clean_cannot_resurrect_acknowledged_same_evidence(self):
        oracle, record = self.recorded()
        old = {'id': 'old', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        record.rows['notice:old'] = old
        oracle.expected(record)
        oracle.call('mail_notice_ack', {'operation_id': 'n' if 'notice:n' in record.rows else 'old'}, 123)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        record.events.append({'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:old': {**old, 'ack': True}}})
        self.assertEqual(oracle.expected(record), set())
        record.events.append({'seq': 2, 'action': 'mail_sent_copy_check', 'set': {'op:g:send': {**record.rows['op:g:send'], 'sent_copy_check': {'state': 'checked', 'clean': True}}}})
        oracle.call('mail_operation_status', {'operation_id': 'g:send'}, 125)
        oracle.script[-1]['end_seq'] = 2
        oracle.server('SENT', 'box', 'Sent', oracle.servers[0]['identities'], source='op:g:send', before_seq=1)
        record.rows['notice:new'] = {**old, 'id': 'new'}
        self.assertEqual(oracle.expected(record), set())
        self.assertTrue(oracle.invalid_clean_results)

    def test_public_notice_must_expose_exact_context_not_only_opaque_id_and_role(self):
        from owner_state_oracle.compare import notice_facts
        oracle = Oracle()
        oracle.seed_sequence = 1
        source = 'mail:rename:r'
        context = {'id': 'r', 'account': 'box', 'source': 'Source', 'target': 'Target', 'message_count': 3}
        evidence = {'target': 'Target', 'role': 'Trash'}
        saved = {'id': 'n', 'source_key': source, 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(evidence)}
        record = Record(rows={source: {**context, 'state': 'partial'}, 'notice:n': saved},
                        events=[{'seq': 1, 'action': 'mail_folder_rename', 'set': {source: {**context, 'state': 'partial'}}}])
        oracle.detected.add(oracle.warning(source, 'rename', evidence, record, context))
        expected = oracle.expected(record)
        correct = {'operation_id': 'n', 'app': 'mail', 'state': 'partial', 'untrusted_content': {
            'filing_id': 'n', 'message_count': 3, 'folders': ['Source', 'Target'], 'folders_more': 0, 'folders_more_text': '',
            'intent_key': source, 'reason': 'Nothing was deleted. It is now Target, inside Trash.'}}
        self.assertEqual(notice_facts(correct, record, oracle), expected)
        for field in ('app', 'state', 'filing_id', 'message_count', 'folders', 'intent_key'):
            wrong = copy.deepcopy(correct)
            (wrong if field in {'app', 'state'} else wrong['untrusted_content'])[field] = 'WRONG'
            with self.subTest(field=field), self.assertRaises(AssertionError):
                oracle.compare('public context mutation', expected, notice_facts(wrong, record, oracle))

    def test_exact_context_cannot_be_supplied_by_another_attempt_or_changed_fields(self):
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 4, 'uid': 7, 'message_id': '<m@mail.invalid>'}
        roles = {'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']}
        context = {'command': 'STORE', 'account': 'box', 'roles': {'sent': ['Sent'], 'drafts': ['Drafts'], 'trash': ['Trash']},
                   'source': 'Source', 'identities': [ref], 'flags': ['+FLAGS.SILENT', '(\\Seen)']}
        def evaluate(current):
            oracle = Oracle()
            oracle.call('mail_flag', {'references': [ref], 'add': ['\\Seen']}, 1)
            oracle.server('STORE', 'box', 'Source', [ref], roles, arguments=['7', '+FLAGS.SILENT', '(\\Seen)'],
                call_start_seq=10, created_before={'intent:old': 1, 'intent:current': 11}, committed_before={
                    'intent:old': {'state': 'started', 'action': 'mail_flag', 'context': context},
                    'intent:current': {'state': 'started', 'action': 'mail_flag', 'context': current}})
            return oracle.context_errors()
        self.assertFalse(evaluate(context))
        for field in context:
            changed = copy.deepcopy(context)
            changed[field] = None
            with self.subTest(field=field):
                self.assertTrue(evaluate(changed), field)

    def test_post_context_binds_exact_url_body_source_and_current_operation(self):
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 4, 'message_id': '<list@mail.invalid>'}
        roles = {'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']}
        context = {'command': 'POST', 'account': 'box', 'roles': {'sent': ['Sent'], 'drafts': ['Drafts'], 'trash': ['Trash']},
                   'source': ref, 'destination': 'https://leave.mail.invalid/stop', 'body': 'List-Unsubscribe=One-Click'}
        def errors(value):
            oracle = Oracle()
            oracle.call('mail_unsubscribe', {'operation_id': 'g:p', 'description': {'reference': ref}}, 1)
            oracle.server('POST', 'box', roles=roles, url=context['destination'], body=context['body'],
                call_start_seq=10, created_before={'op:g:p': 2, 'op:g:other': 1}, committed_before={
                    'op:g:p': {'id': 'g:p', 'state': 'submitting', 'action': 'mail_unsubscribe', 'payload': {'method': 'POST'}, 'context': value},
                    'op:g:other': {'id': 'g:other', 'state': 'submitting', 'action': 'mail_unsubscribe', 'payload': {'method': 'POST'}, 'context': context}})
            return oracle.context_errors()
        self.assertFalse(errors(context))
        for field in context:
            value = copy.deepcopy(context)
            value[field] = 'WRONG'
            with self.subTest(field=field):
                self.assertTrue(errors(value))

    def test_ordinary_rename_does_not_warn_or_bind_an_older_same_target(self):
        oracle = Oracle()
        old = {'id': 'old', 'account': 'box', 'source': 'Older', 'target': 'Target', 'state': 'done', 'message_count': 0}
        new = {'id': 'new', 'account': 'box', 'source': 'Source', 'target': 'Target', 'state': 'started', 'message_count': 0}
        before = {'Source': [], 'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']}
        oracle.call('mail_folder_rename', {'account': 'box', 'folder': 'Source', 'name': 'Target'}, 1)
        oracle.server('RENAME', 'box', roles=before, arguments=['Source', 'Target'],
            committed_before={'mail:rename:old': old, 'mail:rename:new': new},
            created_before={'mail:rename:old': 1, 'mail:rename:new': 11}, call_start_seq=10)
        after = {**before, 'Target': []}
        after.pop('Source')
        oracle.server('LIST', 'box', roles=after)
        record = Record(rows={'mail:rename:old': old, 'mail:rename:new': {**new, 'state': 'done'}})
        self.assertEqual(oracle.expected(record), set())
        after['Trash'], after['Target'] = [], ['\\Trash']
        oracle.server('LIST', 'box', roles=after)
        warned = oracle.expected(record)
        self.assertEqual({f.source for f in warned}, {'mail:rename:new'})

    def test_trash_delete_context_does_not_authorize_expunge_before_crash(self):
        oracle = Oracle()
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 7, 'message_id': 'm'}
        roles = {'special': {'sent': 'Sent', 'drafts': 'Drafts', 'trash': 'Trash'}}
        row = {'id': 'g:d', 'app': 'mail', 'action': 'mail_delete', 'state': 'submitting',
               'payload': {'mode': 'trash', 'items': [{'reference': ref}]}, 'roles_before': roles}
        oracle.call('mail_delete', {'operation_id': 'g:d', 'description': {'mode': 'trash'}}, 1)
        oracle.server('EXPUNGE', 'box', 'Source', [ref], {'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']},
            arguments=['7'], committed_before={'op:g:d': row}, created_before={'op:g:d': 1}, call_start_seq=10)
        self.assertFalse(oracle.completion_errors(Record(rows={'op:g:d': row})))
        self.assertTrue(oracle.context_errors(), 'A matching UID cannot turn trash approval into permanent deletion')

    def test_decoder_follows_hash_valid_archived_manifests_recursively(self):
        import hashlib
        state, evidence = self.disk()
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            first = json.loads(db.execute('SELECT value FROM events').fetchone()[0])
            directory = evidence / 'archives'
            directory.mkdir()
            raw_a = (canonical({'event': first}) + '\n').encode()
            path_a = directory / 'a.jsonl'
            path_a.write_bytes(raw_a)
            second_record = {'format': 2, 'seq': 2, 'previous': first['record']['hash'], 'time': 124, 'generation': 'g', 'operations': []}
            second_record['hash'] = fingerprint(second_record)
            second = {'seq': 2, 'time': 124, 'action': 'control_archive', 'outcome': 'done',
                'set': {'archive:a': {'path': str(path_a), 'sha256': hashlib.sha256(raw_a).hexdigest()}}, 'record': second_record}
            raw_b = (canonical({'event': second}) + '\n').encode()
            path_b = directory / 'b.jsonl'
            path_b.write_bytes(raw_b)
            third_record = {'format': 2, 'seq': 3, 'previous': second_record['hash'], 'time': 125, 'generation': 'g', 'operations': []}
            third_record['hash'] = fingerprint(third_record)
            third = {'seq': 3, 'time': 125, 'action': 'control_archive', 'outcome': 'done',
                'set': {'archive:b': {'path': str(path_b), 'sha256': hashlib.sha256(raw_b).hexdigest()}}, 'record': third_record}
            db.execute('DELETE FROM events')
            db.execute('INSERT INTO events VALUES (?,?)', (3, canonical(third)))
            db.execute('UPDATE head SET seq=3,hash=?', (third_record['hash'],))
            db.commit()
        with (evidence / 'operations.jsonl').open('a') as stream:
            for value in (second_record, third_record):
                stream.write(canonical(value) + '\n' + canonical({'commit': value['seq'], 'hash': value['hash']}) + '\n')
        decoded = decode(state, evidence)
        self.assertEqual(decoded.generation, 'g')
        self.assertEqual([e['seq'] for e in decoded.events], [1, 2, 3])
        self.assertEqual(decoded.working_sequences, {3})
        path_a.write_bytes(raw_a + b'changed')
        with self.assertRaisesRegex(ValueError, 'Archive publication hash'):
            decode(state, evidence)

    def test_unprepared_fence_is_distinct_from_a_replayable_prepared_event(self):
        state, evidence = self.disk(marker=False)
        prepared = decode(state, evidence)
        self.assertEqual(prepared.unprepared_fences, set())
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            db.execute('DELETE FROM events')
            db.execute("UPDATE head SET seq=0,hash=''")
            db.commit()
        unprepared = decode(state, evidence)
        self.assertEqual(unprepared.unprepared_fences, {1})
        self.assertEqual(unprepared.rows, {})

    def test_server_transcript_freezes_arguments_and_role_history(self):
        from owner_state_oracle.transcript import Transcript
        trace = Transcript()
        arguments, roles = {'target': 'Target', 'items': [1]}, {'Target': []}
        call = trace.begin('mail_copy', arguments)
        event = trace.command('COPY', 'box', 'Source', roles)
        arguments['items'].append(2)
        roles['Target'].append('\\Trash')
        self.assertEqual(trace.script[0]['arguments']['items'], [1])
        self.assertEqual(event['roles'], {'Target': []})
        self.assertEqual(event['call'], call)

    def test_grouped_gap_storage_preserves_exact_cases_without_wildcards(self):
        from owner_state_oracle.gaps import Gaps, full_pack, unpack
        recorded = Gaps(recording=True)
        for case in ('flow/single/1', 'flow/single/2'):
            check = recorded.checker(case)
            check('warning', {Fact('source', 'warning')}, set())
            check.finish()
        packed = full_pack(recorded.entries)
        self.assertEqual(len(packed['groups']), 1)
        self.assertEqual(unpack(packed), recorded.entries)
        strict = Gaps(recording=True)
        strict.recording, strict.entries = False, unpack(packed)
        check = strict.checker('flow/single/3')
        check('warning', {Fact('source', 'warning')}, set())
        with self.assertRaisesRegex(AssertionError, 'Unlisted'):
            check.finish()

    def test_every_pinned_gap_belongs_to_an_executed_suite(self):
        from owner_state_oracle.gaps import PATH, owned
        sweep = Path(__file__).resolve().parents[1] / 'mail_tests/test_owner_state_sweep.py'
        owners = {'contract', 'channel', 'G22-rename', 'G22-evidence', 'G22-latch'}
        for node in ast.parse(sweep.read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'FLOWS', 'EXTRA'} for t in node.targets):
                owners.update(ast.literal_eval(node.value))
        ledger = json.loads(PATH.read_text())
        self.assertEqual(ledger['format'], 3)
        ids = set()
        for group in ledger['groups']:
            self.assertNotIn(group['id'], ids)
            ids.add(group['id'])
            self.assertIn(group['suite'], owners)
            self.assertIn(group['stage'], (2, 3))
            self.assertTrue(group['row'])
            self.assertGreater(group['count'], 0)
            self.assertEqual(len(group['sha256']), 64)
            count = sum(owned(group, shard, 4, worker, 3) for shard in range(4) for worker in range(3))
            self.assertEqual(count, 12 if group['owner'] in {'suite', 'shared'} else 1)

    def test_compact_ledger_pins_delta_keys_groups_and_execution(self):
        from owner_state_oracle.gaps import Gaps, pack
        entries = {f'flow/single/{p}/0/live/view': {'row': 'M14', 'stage': 3,
            'delta': {'calls': 1, 'failures': [{'pages': [0], 'missing': [['a']], 'extra': []}]}} for p in (1, 2)}
        def verify(values):
            gaps = Gaps(recording=True)
            gaps.groups = {g['id']: g for g in pack(entries)['groups']}
            gaps.entries, gaps.recording = values, False
            gaps.verify({'flow'}, artifact=False)
        verify(entries)
        mutations = []
        flipped = copy.deepcopy(entries)
        next(iter(flipped.values()))['delta']['calls'] = 2
        mutations.append(flipped)
        mutations.append(dict(list(entries.items())[1:]))
        mutations.append({**entries, 'flow/single/3/0/live/view': next(iter(entries.values()))})
        moved = copy.deepcopy(entries)
        next(iter(moved.values()))['row'] = 'M06'
        mutations.append(moved)
        mutations.append({})  # Every formerly failing assertion now passes.
        for mutated in mutations:
            with self.assertRaises(AssertionError):
                verify(mutated)

    def test_isolated_sweep_process_failure_cannot_report_success(self):
        from contextlib import redirect_stdout
        import io
        import os
        import sys
        from ci.mail.tests import run_workers
        command = [sys.executable, '-c', 'import os,sys; w=os.environ["OWNER_SWEEP_WORKER"]; print("child="+w); sys.exit(int(w))']
        for count in (2, 3):
            output = io.StringIO()
            with redirect_stdout(output):
                result, good = run_workers(command, os.environ, lambda: 'parent result', count=count)
            self.assertEqual(result, 'parent result')
            self.assertFalse(good)
            for worker in range(count):
                self.assertIn('child=' + str(worker), output.getvalue())
                self.assertIn(f'worker={worker}/{count} exit={worker}', output.getvalue())

    def local_delete_record(self):
        items = {key: {'id': key, 'revision': 1, 'sender': 'fixture', 'subject': key, 'date': 'synthetic', 'flagged': False}
                 for key in ('a', 'b')}
        target = {'reference': {'scope': 'testapp/fixture/items', 'epoch': 'epoch', 'id': 'a', 'revision': 1},
                  **{key: items['a'][key] for key in ('sender', 'subject', 'date')}}
        arguments = {'operation_id': 'g:d', 'description': {'account': 'fixture', 'items': [target]}}
        operation = {'id': 'g:d', 'action': 'testapp_delete', 'app': 'testapp', 'state': 'submitting',
                     'approval': copy.deepcopy(arguments), 'payload': {'items': [target]}}
        operation['context'] = {'command': 'LOCAL_DELETE', 'account': 'fixture', 'arguments': copy.deepcopy(arguments),
            'identities': [target['reference']], 'source': 'fixture/items', 'destination': None, 'roles': {}, 'recipients': []}
        oracle = Oracle()
        oracle.call('testapp_delete', arguments, 1)
        events = [
            {'seq': 1, 'time': 1, 'action': 'fixture', 'set': {'op:g:d': operation, 'testapp': {'epoch': 'epoch', 'items': items}}},
            {'seq': 2, 'time': 1, 'action': 'testapp_delete', 'operation_id': 'g:d', 'set': {'testapp': {'epoch': 'epoch', 'items': {'b': items['b']}}}},
            {'seq': 3, 'time': 1, 'action': 'testapp_delete', 'set': {'op:g:d': {**operation, 'state': 'done'}}}]
        return oracle, Record(events=[copy.deepcopy(event) for event in events])

    def test_local_delete_requires_prior_context_even_before_terminal_outcome(self):
        oracle, record = self.local_delete_record()
        self.assertEqual(oracle.local_context_errors(record), set())
        del record.events[0]['set']['op:g:d']
        self.assertTrue(oracle.local_context_errors(record))
        record.events.pop()
        self.assertTrue(oracle.local_context_errors(record), 'Submitting/partial effects require context too')

    def test_local_delete_rejects_extra_target_wrong_reference_and_changed_survivor(self):
        for mutation in ('extra', 'reference', 'survivor', 'no-effect'):
            oracle, record = self.local_delete_record()
            if mutation == 'extra':
                record.events[1]['set']['testapp']['items'] = {}
            elif mutation == 'reference':
                record.events[0]['set']['op:g:d']['payload']['items'][0]['reference']['revision'] = 2
            elif mutation == 'survivor':
                record.events[1]['set']['testapp']['items']['b']['flagged'] = True
            else:
                record.events.pop(1)
            with self.subTest(mutation=mutation):
                self.assertTrue(oracle.local_context_errors(record))

    def test_local_delete_allows_batches_and_prepared_effects_with_prior_context(self):
        oracle, record = self.local_delete_record()
        effect, terminal = record.events[1:]
        record.events, record.prepared = record.events[:1], [effect]
        self.assertEqual(oracle.local_context_errors(record), set())
        record.events, record.prepared = [], [*record.events, effect]
        self.assertTrue(oracle.local_context_errors(record))
        oracle, record = self.local_delete_record()
        item = record.events[0]['set']['testapp']['items']['b']
        target = {'reference': {'scope': 'testapp/fixture/items', 'epoch': 'epoch', 'id': 'b', 'revision': 1},
                  **{key: item[key] for key in ('sender', 'subject', 'date')}}
        oracle.script[0]['arguments']['description']['items'].append(target)
        operation = record.events[0]['set']['op:g:d']
        operation['payload']['items'] = copy.deepcopy(oracle.script[0]['arguments']['description']['items'])
        operation['approval'] = copy.deepcopy(oracle.script[0]['arguments'])
        operation['context']['arguments'] = copy.deepcopy(oracle.script[0]['arguments'])
        operation['context']['identities'] = [item['reference'] for item in operation['payload']['items']]
        record.events[2]['seq'] = 4
        record.events.insert(2, {'seq': 3, 'time': 1, 'action': 'testapp_delete', 'operation_id': 'g:d',
                                'set': {'testapp': {'epoch': 'epoch', 'items': {}}}})
        self.assertEqual(oracle.local_context_errors(record), set())
        record.events.pop(2)
        self.assertTrue(oracle.local_context_errors(record), 'Done requires the complete approved removal set')

    def local_account_record(self, action):
        before = {'id': 'box', 'format': 'plain', 'signature': '', 'special': {'sent': 'Sent'},
                  'roots': {}, 'optional': {}, 'delimiter': '/'}
        after = {**before, 'signature': 'new'} if action == 'mail_account_settings' else copy.deepcopy(before)
        arguments = {'id': 'box', 'signature': 'new'} if action == 'mail_account_settings' else {
            'id': 'box', 'roles_hash': fingerprint({key: after[key] for key in ('special', 'roots', 'optional', 'delimiter')})}
        context = {'account': 'box', 'arguments': arguments, 'roles': {'sent': ['Sent']}}
        oracle = Oracle()
        oracle.call(action, arguments, 1)
        events = [{'seq': 1, 'time': 1, 'action': 'fixture', 'set': {'mail:account:box': before,
            'intent:local': {'action': action, 'state': 'started', 'context': context}}},
            {'seq': 2, 'time': 1, 'action': action, 'set': {'mail:account:box': after}}]
        return oracle, Record(events=[copy.deepcopy(event) for event in events])

    def test_local_settings_and_role_review_require_exact_current_arguments(self):
        for action in ('mail_account_settings', 'mail_account_folders'):
            for mutation in ('arguments', 'effect', 'late', 'historical'):
                oracle, record = self.local_account_record(action)
                self.assertEqual(oracle.local_context_errors(record), set())
                if mutation == 'arguments':
                    record.events[0]['set']['intent:local']['context']['arguments'] = {'id': 'wrong'}
                elif mutation == 'effect':
                    record.events[1]['set']['mail:account:box']['signature'] = 'unexpected'
                elif mutation == 'late':
                    del record.events[0]['set']['intent:local']
                else:
                    record.events[0]['time'] = 0
                with self.subTest(action=action, mutation=mutation):
                    self.assertTrue(oracle.local_context_errors(record))

    def test_fixture_configuration_requires_exact_pre_effect_arguments(self):
        oracle = Oracle()
        arguments = {'refuse': [], 'failure': 'none'}
        oracle.call('testapp_fixture_configure', arguments, 1)
        context = {'command': 'CONFIGURE', 'account': 'fixture', 'source': 'fixture',
                   'destination': 'receiver/config', 'arguments': arguments}
        event = oracle.server('CONFIGURE', 'fixture', arguments=arguments,
            committed_before={'intent:x': {'action': 'testapp_fixture_configure', 'state': 'started', 'context': context}},
            created_before={'intent:x': 2}, call_start_seq=1)
        self.assertEqual(oracle.context_errors(), set())
        event['arguments'] = {'refuse': ['extra'], 'failure': 'none'}
        self.assertTrue(oracle.context_errors())
        event['arguments'], event['committed_before'] = arguments, {}
        self.assertTrue(oracle.context_errors())

    def test_role_review_keeps_historical_and_old_and_current_protected_roots(self):
        from owner_state_oracle.local import protected_roots
        before = {'special': {'trash': 'Trash', 'drafts': 'Drafts'},
            'roots': {'trash': {'folder': 'Trash', 'delimiter': '/'}, 'drafts': {'folder': 'Drafts', 'delimiter': '/'}},
            'protected_special': {'trash': [{'folder': 'OldTrash', 'delimiter': '.'}],
                                  'drafts': [{'folder': 'OldDrafts', 'delimiter': '.'}]}}
        after = copy.deepcopy(before)
        after['special']['trash'] = 'NewTrash'
        after['roots']['trash'] = {'folder': 'NewTrash', 'delimiter': '/'}
        after['protected_special']['trash'] += [before['roots']['trash'], after['roots']['trash']]
        after['protected_special']['drafts'].append(before['roots']['drafts'])
        self.assertTrue(protected_roots(before, after, None))
        for mutation in ('history', 'old', 'current', 'extra'):
            changed = copy.deepcopy(after)
            if mutation == 'extra':
                changed['protected_special']['trash'].append({'folder': 'Unapproved', 'delimiter': '/'})
            else:
                changed['protected_special']['trash'].pop({'history': 0, 'old': 1, 'current': 2}[mutation])
            with self.subTest(mutation=mutation):
                self.assertFalse(protected_roots(before, changed, None))
        oracle, record = self.local_account_record('mail_account_folders')
        historical = {'trash': [{'folder': 'OldTrash', 'delimiter': '.'}]}
        record.events[0]['set']['mail:account:box']['protected_special'] = historical
        record.events[1]['set']['mail:account:box']['protected_special'] = copy.deepcopy(historical)
        self.assertEqual(oracle.local_context_errors(record), set())
        record.events[1]['set']['mail:account:box']['protected_special'] = {}
        self.assertTrue(oracle.local_context_errors(record))

    def status_response(self):
        operation = {'id': 'g:d', 'generation': 'g', 'app': 'testapp', 'action': 'testapp_send',
                     'approval': {}, 'state': 'submitting', 'expires': 1, 'stages': {}, 'reason': 'Submitting'}
        return {'ok': True, 'data': {'operation': operation, 'evidence': {}},
                'pending': {'items': [], 'total': 0, 'cursor': None}}

    def test_schema_failure_is_exact_and_an_unexpected_repair_fails(self):
        import response_checks
        from owner_state_oracle.responses import read_response
        from owner_state_oracle.gaps import Gaps
        request = {'method': 'call', 'action': 'testapp_operation_status'}
        invalid = self.status_response()
        invalid['data'].pop('operation')
        invalid['data']['unsupported_evidence'] = {'code': 'storage_limit', 'message': 'Synthetic'}
        reply, failures = read_response(lambda: response_checks.validate_response(request, invalid))
        self.assertEqual(reply, invalid)
        details = [json.loads(value) for value in failures]
        self.assertEqual({value['rule'] for value in details}, {'required', 'additionalProperties'})
        self.assertEqual(next(value['missing'] for value in details if value['rule'] == 'required'), ['operation'])
        self.assertEqual(next(value['extra'] for value in details if value['rule'] == 'additionalProperties'), ['unsupported_evidence'])
        recorded = Gaps(recording=True)
        check = recorded.checker('schema-case')
        check('schema', set(), {Fact('response', 'schema', detail=value) for value in failures})
        check.finish()
        strict = Gaps(recording=True)
        strict.entries, strict.recording = recorded.entries, False
        _, repaired = read_response(lambda: response_checks.validate_response(request, self.status_response()))
        check = strict.checker('schema-case')
        check('schema', set(), {Fact('response', 'schema', detail=value) for value in repaired})
        with self.assertRaisesRegex(AssertionError, 'Unexpected pass'):
            check.finish()

    def test_response_capture_does_not_swallow_unrelated_validation_errors(self):
        from jsonschema import ValidationError
        import response_checks
        from owner_state_oracle.responses import read_response
        error = ValidationError('Unrelated failure after a valid nested reply')
        def unrelated():
            response_checks.validate_response({'method': 'call', 'action': 'testapp_operation_status'}, self.status_response())
            raise error
        with self.assertRaises(ValidationError) as raised:
            read_response(unrelated)
        self.assertIs(raised.exception, error)

    def test_script_calendar_ignores_host_date_and_follows_effective_clock(self):
        import time
        from unittest.mock import patch
        from owner_state_oracle.clock import scripted_calendar
        real_localtime = time.localtime
        real_nanos = time.time_ns
        epoch = 1794225600
        host_date = real_localtime(epoch + 10 * 86400)
        def host_localtime(seconds=None):
            return host_date if seconds is None else real_localtime(seconds)
        with patch.object(time, 'time', return_value=epoch), patch.object(time, 'localtime', side_effect=host_localtime) as host:
            self.assertEqual(time.localtime(), host_date)
            with scripted_calendar():
                self.assertEqual(time.localtime(), real_localtime(epoch))
                self.assertEqual(time.time_ns(), epoch * 1_000_000_000)
                self.assertEqual(time.localtime(0), real_localtime(0))
                with patch.object(time, 'time', return_value=epoch + 86400):
                    self.assertEqual(time.localtime(), real_localtime(epoch + 86400))
                    self.assertEqual(time.time_ns(), (epoch + 86400) * 1_000_000_000)
            self.assertIs(time.localtime, host)
            with self.assertRaisesRegex(RuntimeError, 'synthetic'):
                with scripted_calendar():
                    raise RuntimeError('synthetic')
            self.assertIs(time.localtime, host)
        self.assertIs(time.localtime, real_localtime)
        self.assertIs(time.time_ns, real_nanos)

    def test_fixture_ids_are_unique_reproducible_and_scoped(self):
        import uuid
        from owner_state_oracle.identity import scripted_ids
        original = uuid.uuid4
        sequences = []
        for _ in range(2):
            with scripted_ids('repair'):
                sequences.append([uuid.uuid4() for _ in range(32)])
            self.assertIs(uuid.uuid4, original)
        self.assertEqual(sequences[0], sequences[1])
        self.assertEqual(len(set(sequences[0])), 32)
        self.assertTrue(all(value.version == 4 for value in sequences[0]))
        self.assertNotEqual(sequences[0], sorted(sequences[0]))
        with scripted_ids('onboarding'):
            self.assertNotEqual(uuid.uuid4(), sequences[0][0])
        with self.assertRaisesRegex(RuntimeError, 'synthetic'):
            with scripted_ids('repair'):
                raise RuntimeError('synthetic')
        self.assertIs(uuid.uuid4, original)

    def test_repair_context_binding_handles_both_opaque_id_orders(self):
        from owner_state_oracle.context import differences
        for parent, child in (('g:a', 'g:z'), ('g:z', 'g:a')):
            oracle = Oracle()
            oracle.call('mail_operation_repair', {'operation_id': parent, 'stage': 'sent_copy'}, 123)
            context = dict(command='APPEND', account='box', identities=[{'message_id': '<' + parent.replace(':', '.') + '@mail.aresos.invalid>'}],
                           roles={'sent': ['Sent']}, source='local', destination='Sent', sha256='wire')
            rows = {'op:' + parent: {'id': parent, 'state': 'partial', 'context': context},
                    'op:' + child: {'id': child, 'state': 'submitting', 'repair_of': parent,
                                   'action': 'mail_operation_repair', 'payload': {'stage': 'sent_copy'}, 'context': dict(context)}}
            # Match the production scan's lexicographic ordering in both cases.
            event = oracle.server('APPEND', 'box', 'Sent', [{'message_id': '<' + parent.replace(':', '.') + '@mail.aresos.invalid>'}], {'Sent': ['\\Sent']},
                                  raw_sha256='wire', committed_before=dict(sorted(rows.items())))
            self.assertEqual(differences(event, oracle.script), ('op:' + child, []))
            event['committed_before']['op:' + child]['context']['destination'] = 'Wrong'
            self.assertEqual(differences(event, oracle.script), ('op:' + child, ['destination', 'script.context.destination']))

    def test_notice_order_uses_distinct_public_ids_even_when_source_time_ties(self):
        from owner_state_oracle.compare import ordered_notices, notice_identity
        record = Record(rows={'op:g:p': {'id': 'g:p', 'app': 'mail'}},
                        events=[{'time': 12, 'seq': 1, 'set': {'op:g:p': {}}}])
        facts = [Fact('op:g:p', kind) for kind in ('recovery', 'recovery-context', 'unchecked', 'unchecked-context')]
        wanted = [set(facts[2:]), set(facts[:2])]
        for values in (facts, list(reversed(facts)), set(facts)):
            self.assertEqual(ordered_notices(record, values), wanted)
        self.assertEqual(notice_identity(record, facts[0]), 'recovery-g:p')
        self.assertEqual(notice_identity(record, facts[2]), 'sent-check-' + fingerprint('g:p')[:32])
        import os
        import subprocess
        import sys
        script = "from owner_state_oracle.compare import ordered_notices; from owner_state_oracle.model import Fact; from owner_state_oracle.records import Record; facts={Fact('op:g:p', k) for k in ('recovery','recovery-context','unchecked','unchecked-context')}; print([[f.kind for f in sorted(group)] for group in ordered_notices(Record(),facts)])"
        for seed in ('1', '4'):
            result = subprocess.run([sys.executable, '-c', script], env={**os.environ, 'PYTHONHASHSEED': seed},
                                    capture_output=True, text=True, check=True)
            self.assertEqual(result.stdout.strip(), "[['unchecked', 'unchecked-context'], ['recovery', 'recovery-context']]")

    def test_synthetic_notice_id_formats_and_saved_creation_order(self):
        from owner_state_oracle.compare import ordered_notices, notice_identity
        record = Record(rows={'intent:generic': {'id': 'generic-id'}, 'mail:filing:f': {'id': 'f'},
                              'mail:rename:r': {'id': 'r'}, 'notice:r': {'ack': True},
                              'notice:recovery-g:p': {'created_at': 30}, 'notice:occurrence': {'created_at': 20}})
        for source, identity in [('export:e', 'recovery-e'), ('mail:account:box', 'recovery-' + fingerprint('mail:account:box')[:32]),
                                 ('intent:generic', 'generic-id'), ('mail:filing:f', 'f'),
                                 ('mail:rename:r', 'check-' + fingerprint('mail:rename:r')[:32]),
                                 ('legacy-intent:mail_flag:1', 'recovery-' + fingerprint('legacy-intent:mail_flag:1')[:32])]:
            self.assertEqual(notice_identity(record, Fact(source, 'recovery')), identity)
        recovery, warning = Fact('op:g:p', 'recovery'), Fact('op:g:p', 'sent_copies', 'occurrence')
        self.assertEqual(ordered_notices(record, {warning, recovery}), [{recovery}, {warning}])

    def test_special_rename_role_cannot_supply_clean_proof(self):
        oracle = Oracle()
        source, evidence = 'mail:rename:r', {'target': 'Target', 'role': '\\All'}
        record = Record(rows={'notice:a': {'id': 'a', 'source_key': source, 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(evidence)}})
        oracle.warning(source, 'rename', evidence, record)
        oracle.call('check', {}, 2)
        oracle.script[-1]['end_seq'] = 2
        oracle.server('LIST', before_seq=1, roles={'Target': ['\\All'], 'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']})
        self.assertFalse(oracle.clean_proof(source, 'rename', 2))


class StageOneFixMutations(unittest.TestCase):
    def test_spontaneous_ack_cannot_erase_warning(self):
        oracle, record = OwnerOracle.recorded(self)
        row = {'id': 'n', 'source_key': 'op:g:send', 'check_kind': 'sent_copies', 'ack': True}
        record.rows['notice:n'] = row
        record.events = [{'seq': 1, 'action': 'mail_sent_copy_check', 'set': {'notice:n': row}}]
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'sent_copies' for f in expected))
        self.assertIn(Fact('notice:n', 'unjustified-ack'), oracle.lifecycle_errors)
        with self.assertRaises(AssertionError):
            oracle.compare('automatic ack', expected, set())

    def test_scripted_ack_cannot_close_unfinished_check(self):
        oracle = Oracle()
        source = 'mail:rename:r'
        old = {'id': 'r', 'state': 'started', 'check_open': True, 'account': 'box'}
        oracle.call('mail_notice_ack', {'operation_id': 'r'}, 1)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {source: old}},
            {'seq': 2, 'action': 'mail_notice_ack', 'set': {source: {**old, 'state': 'done', 'check_open': False}}}])
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'recovery' for f in expected))
        self.assertIn(Fact(source, 'unjustified-check-close', detail='2'), oracle.lifecycle_errors)
        with self.assertRaises(AssertionError):
            oracle.compare('ack closes check', expected, set())

    def test_archive_cannot_remove_unresolved_reservation(self):
        oracle = Oracle()
        row = {'id': 'g:r', 'app': 'mail', 'state': 'reserved'}
        record = Record(events=[{'seq': 1, 'action': 'mail_prepare_send', 'set': {'op:g:r': row}},
            {'seq': 2, 'action': 'control_archive', 'set': {'op:g:r': None}}])
        expected = oracle.expected(record)
        self.assertIn(Fact('op:g:r', 'unjustified-removal'), oracle.lifecycle_errors)
        self.assertEqual(oracle.holds(record), {Fact('cancel:g:r', 'held')})
        with self.assertRaises(AssertionError):
            oracle.compare('archive drops reservation', expected, set())

    def test_matching_context_and_command_cannot_change_script_uid(self):
        from owner_state_oracle.context import differences
        requested = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1, 'message_id': '<one@mail.invalid>'}
        wrong = {**requested, 'uid': 2, 'message_id': '<two@mail.invalid>'}
        oracle = Oracle()
        oracle.call('mail_flag', {'references': [requested], 'add': ['\\Seen']}, 1)
        event = oracle.server('STORE', 'box', 'Source', [wrong], {}, arguments=['2', '+FLAGS.SILENT', '(\\Seen)'],
            call_start_seq=0, created_before={'intent:x': 1}, committed_before={'intent:x': {
                'state': 'started', 'action': 'mail_flag', 'context': {'command': 'STORE', 'account': 'box', 'roles': {},
                'source': 'Source', 'identities': [wrong], 'flags': ['+FLAGS.SILENT', '(\\Seen)']}}})
        self.assertIn('script.command.identities', differences(event, oracle.script)[1])
        self.assertIn('script.context.identities', differences(event, oracle.script)[1])

    def test_empty_healthy_catalogue_cannot_refuse_itself(self):
        from owner_state_oracle.compare import compare_status
        oracle = Oracle()
        oracle.call('mail_filing_notices', {}, 1)
        reply = {'ok': False, 'error': {'code': 'storage_limit'}}
        oracle.reply(reply)
        self.assertEqual(oracle.expected(Record(), live=True), set())
        with self.assertRaises(AssertionError):
            compare_status(reply, oracle, Record(), oracle.script[-1], oracle.compare, 'empty')
        compare_status({'ok': True}, oracle, Record(), oracle.script[-1], oracle.compare, 'empty')

    def background(self):
        oracle = Oracle()
        oracle.call('control_pending', {}, 1, {'background': True, 'trace': [(1, 'journal.write', 'ENOSPC'), (2, 'file.truncate', 'EIO')]})
        return oracle

    def test_background_first_cause_present_lost_and_restart(self):
        from owner_state_oracle.compare import notice_facts
        oracle = self.background()
        expected = oracle.expected(Record())
        notice = {'operation_id': 'background-storage', 'untrusted_content': {'reason': 'Disk full or storage quota exhausted; free storage and check the recorded request or operation before retrying.'}}
        self.assertEqual(expected, notice_facts(notice, Record(), oracle))
        with self.assertRaises(AssertionError):
            oracle.compare('lost after failed persistence', expected, set())
        restarted = Oracle()
        restarted.script = copy.deepcopy(oracle.script)
        self.assertEqual(restarted.expected(Record()), expected)
        wrong = copy.deepcopy(notice)
        wrong['untrusted_content']['reason'] = 'Storage I/O failed; check the disk.'
        with self.assertRaises(AssertionError):
            oracle.compare('cleanup replaced first cause', expected, notice_facts(wrong, Record(), oracle))

    def test_every_action_error_and_continuation_envelope_keeps_live_warning(self):
        from owner_state_oracle.compare import compare_envelope
        oracle = self.background()
        record = Record()
        expected = oracle.expected(record)
        reply = {'ok': True, 'pending': {'items': [], 'total': 0, 'cursor': None, 'notices': [
            {'operation_id': 'background-storage', 'untrusted_content': {'reason': 'Disk full or storage quota exhausted'}}]}}
        for label in ('original-action', 'error-reply', 'continuation-page'):
            compare_envelope(label, reply, record, oracle, expected, oracle.compare)
            wrong = copy.deepcopy(reply)
            wrong['pending']['notices'] = []
            with self.assertRaises(AssertionError):
                compare_envelope(label, wrong, record, oracle, expected, oracle.compare)

    def test_completed_qualification_comes_from_probe_evidence(self):
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new'}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        oracle.server('DATA', 'new', accepted=True)
        oracle.server('SENT', 'new', identities=[])
        oracle.server('DELETE', 'new', accepted=False, response_code='NO', response_text=['[CANNOT] Generic refusal'])
        record = Record(events=[{'seq': 1, 'action': 'mail_account_add', 'outcome': 'done', 'set': {'mail:account:new': {
            'id': 'new', 'onboarded': True, 'ready': True, 'sent_policy': 'server', 'safe_folder_delete': True}}}])
        expected = oracle.qualification_facts({}, record)
        good = {'ok': True, 'data': {'accounts': [{'id': 'new', 'ready': False, 'sent_policy': 'client', 'safe_folder_delete': False, 'folder_delete_reason': 'Probe survival or cleanup could not be verified; owner must inspect.'}]}}
        self.assertEqual(expected, oracle.qualification_facts(good, record, actual=True))
        for field, value in (('ready', True), ('sent_policy', 'server'), ('safe_folder_delete', True), ('folder_delete_reason', 'Qualified: all safe.')):
            wrong = copy.deepcopy(good)
            wrong['data']['accounts'][0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                oracle.compare('qualification', expected, oracle.qualification_facts(wrong, record, actual=True))
        oracle.call('mail_accounts', {}, 2)
        self.assertEqual(expected, oracle.qualification_facts({}, record))

    def test_recovery_handle_is_checked_on_pages_reads_and_ack(self):
        from owner_state_oracle.compare import notice_facts
        oracle = Oracle()
        source = 'mail:rename:r'
        record = Record(rows={source: {'id': 'r', 'state': 'started'}})
        expected = oracle.expected(record)
        good = {'operation_id': 'r', 'app': 'mail', 'state': 'unknown', 'untrusted_content': {'intent_key': source, 'recovery_warning': True, 'reason': 'Check roles.'}}
        self.assertEqual(expected, notice_facts(good, record, oracle))
        for label in ('page', 'repeat', 'restart'):
            wrong = {**good, 'operation_id': 'changed'}
            with self.assertRaises(AssertionError):
                oracle.compare(label, expected, notice_facts(wrong, record, oracle))
        oracle.call('mail_notice_ack', {'operation_id': 'r'}, 1)
        record.events = [{'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:r': {'id': 'r', 'ack': True}}}]
        oracle.script[-1].update(start_seq=0, end_seq=1)
        after = oracle.expected(record)
        self.assertIn(Fact(source, 'recovery-handle', 'check-' + fingerprint(source)[:32]), after)

    def test_audit_checks_identity_explanation_evidence_and_marking(self):
        from owner_state_oracle.compare import audit_fact
        event = {'seq': 1, 'time': 1, 'action': 'mail_send', 'operation_id': 'g:x', 'summary': 'Synthetic explanation', 'outcome': 'partial', 'untrusted_content': {'stage': 'smtp_data', 'outcome': 'accepted'}}
        expected = audit_fact(event, expected=True)
        public = {**event, 'summary': 'Mail audit event', 'untrusted_content': {'summary': event['summary'], **event['untrusted_content']}}
        self.assertEqual(expected, audit_fact(public))
        wrongs = [{**public, 'operation_id': 'g:other'}, {**public, 'summary': 'wrong'},
            {**public, 'untrusted_content': {'summary': 'wrong', 'stage': 'smtp_data', 'outcome': 'accepted'}},
            {**public, 'untrusted_content': {'summary': event['summary'], 'stage': 'APPEND', 'outcome': 'accepted'}}]
        unmarked = copy.deepcopy(public)
        unmarked.update(unmarked.pop('untrusted_content'))
        wrongs.append(unmarked)
        for wrong in wrongs:
            with self.assertRaises(AssertionError):
                Oracle().compare('audit', {expected}, {audit_fact(wrong)})

    def test_unbound_semantic_occurrence_binds_after_persistence_and_acks(self):
        oracle, record = OwnerOracle.recorded(self)
        first = oracle.expected(record)
        semantic = dict(oracle.semantic_occurrences)
        self.assertTrue(any(f.occurrence.startswith('uncommitted:') for f in first))
        record.rows['notice:later'] = {'id': 'later', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        bound = oracle.expected(record)
        self.assertEqual(semantic, oracle.semantic_occurrences)
        self.assertEqual({f.occurrence for f in bound}, {'later'})
        oracle.call('mail_notice_ack', {'operation_id': 'later'}, 124)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        record.events = [{'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:later': {**record.rows['notice:later'], 'ack': True}}}]
        self.assertEqual(oracle.expected(record), set())
        self.assertEqual(semantic, oracle.semantic_occurrences)

    def test_D3_generic_warning_requires_committed_evidence_and_open_check(self):
        from owner_state_oracle.compare import retained_role
        source = 'mail:rename:r'
        content = {'intent_key': source, 'reason': "Evidence was seen but couldn't be recorded; check Trash"}
        notice = {'operation_id': 'generic', 'untrusted_content': content}
        record = Record(rows={source: {'state': 'started'}, 'notice:generic': {
            'id': 'generic', 'source_key': source, 'untrusted_content': content, 'ack': False}})
        expected = {Fact(source, 'observed-role', detail='Trash')}
        self.assertEqual(retained_role(source, 'Trash', record, {'items': [notice]}), expected)
        for rows in ({source: {'state': 'started'}}, {'notice:generic': record.rows['notice:generic']},
            {source: {'state': 'done'}, 'notice:generic': record.rows['notice:generic']}):
            self.assertEqual(retained_role(source, 'Trash', Record(rows=rows), {'items': [notice]}), set())
        vague = {**notice, 'untrusted_content': {'intent_key': source, 'reason': 'Not yet checked'}}
        self.assertEqual(retained_role(source, 'Trash', record, {'items': [vague]}), set())

    def test_coherent_wrong_append_flags_are_not_authorized(self):
        from owner_state_oracle.context import differences
        oracle = Oracle()
        oracle.call('mail_operation_repair', {'operation_id': 'g:parent', 'stage': 'sent_copy'}, 1)
        context = {'command': 'APPEND', 'account': 'box', 'roles': {'sent': ['Sent']}, 'source': 'local', 'destination': 'Sent',
            'sha256': 'wire', 'identities': [{'message_id': '<g.parent@mail.aresos.invalid>'}], 'append_flags': '(\\Draft)'}
        event = oracle.server('APPEND', 'box', 'Sent', [{'message_id': '<g.parent@mail.aresos.invalid>'}], {'Sent': ['\\Sent']}, append_flags='(\\Draft)', raw_sha256='wire',
            committed_before={'op:g:repair': {'id': 'g:repair', 'state': 'submitting', 'repair_of': 'g:parent',
            'action': 'mail_operation_repair', 'payload': {'stage': 'sent_copy'}, 'context': context}})
        self.assertEqual(differences(event, oracle.script)[1], ['script.command.append-flags', 'script.context.append-flags'])
        event['append_flags'] = event['committed_before']['op:g:repair']['context']['append_flags'] = '(\\Seen)'
        self.assertEqual(differences(event, oracle.script)[1], [])

    def test_qualification_distinguishes_each_negative_probe_reason(self):
        ref = {'account': 'new', 'folder': 'Probe', 'uidvalidity': 1, 'uid': 1, 'message_id': '<probe@mail.invalid>', 'sha256': 'wire'}
        def scenario():
            oracle = Oracle()
            oracle.call('mail_account_add', {'id': 'new'}, 1)
            oracle.script[-1].update(start_seq=0, end_seq=1)
            oracle.server('APPEND', 'new', 'Probe', arrived=[ref])
            oracle.server('DELETE', 'new', arguments=['Probe'], accepted=False, response_code='NO', response_text=['[CANNOT] Nonempty DELETE forbidden'])
            oracle.server('FETCH', 'new', 'Probe', identities=[ref])
            oracle.server('EXPUNGE', 'new', 'Probe', identities=[ref], arguments=['1'])
            oracle.server('DELETE', 'new', arguments=['Probe'], accepted=True, response_code='OK')
            record = Record(events=[{'seq': 1, 'action': 'mail_account_add', 'outcome': 'done', 'set': {
                'mail:account:new': {'id': 'new', 'onboarded': True},
                'op:probe': {'action': 'mail_onboarding_folder_probe', 'state': 'refused', 'payload': {'folder': 'Probe'}},
                'op:cleanup': {'action': 'mail_delete', 'state': 'done', 'payload': {'items': [{'reference': ref}]}},
                'op:empty': {'action': 'mail_onboarding_folder_probe', 'state': 'done', 'payload': {'folder': 'Probe', 'empty': True}}}}])
            return oracle, record
        oracle, record = scenario()
        self.assertEqual(oracle.qualification(record)['new']['folder_delete_reason'], 'qualified')
        self.assertTrue(oracle.qualification(record)['new']['safe_folder_delete'])
        oracle, record = scenario()
        record.events[0]['set']['op:cleanup']['state'] = 'reserved'
        expected = oracle.qualification(record)
        later = copy.deepcopy(record.events[0]['set']['op:cleanup'])
        later['state'] = 'failed'
        record.events.append({'seq': 2, 'action': 'mail_delete', 'set': {'op:cleanup': later}})
        restarted = Oracle()
        restarted.script, restarted.servers = copy.deepcopy(oracle.script), copy.deepcopy(oracle.servers)
        self.assertEqual(restarted.qualification(record), expected, 'Later expiry cannot rewrite why qualification failed')
        for kind in ('generic-cleaned', 'probe-missing', 'exact-cleanup-failed', 'empty-cleanup-failed', 'survival-unverified'):
            oracle, record = scenario()
            if kind == 'generic-cleaned':
                oracle.servers[1]['response_text'] = ['[CANNOT] Generic refusal']
            elif kind == 'probe-missing':
                oracle.servers[1]['accepted'] = True
            elif kind == 'exact-cleanup-failed':
                oracle.servers[3].update(accepted=False, response_code='NO')
                record.events[0]['set']['op:cleanup']['state'] = 'failed'
            elif kind == 'empty-cleanup-failed':
                oracle.servers[4].update(accepted=False, response_code='NO')
                record.events[0]['set']['op:empty']['state'] = 'failed'
            else:
                oracle.servers[2]['accepted'] = False
            expected = oracle.qualification(record)['new']
            self.assertEqual(expected['folder_delete_reason'], kind)
            self.assertFalse(expected['safe_folder_delete'])
            wrong = {'data': {'accounts': [{'id': 'new', **expected, 'folder_delete_reason': 'Qualified: fabricated'}]}}
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                oracle.compare('wrong qualification reason', oracle.qualification_facts({}, record), oracle.qualification_facts(wrong, record, actual=True))

    def test_coherent_wrong_send_message_identity_is_not_authorized(self):
        from owner_state_oracle.context import differences
        oracle = Oracle()
        oracle.call('mail_send', {'operation_id': 'g:one'}, 1)
        context = {'command': 'DATA', 'account': 'box', 'roles': {}, 'source': 'owner@mail.invalid', 'destination': 'smtp',
            'sha256': 'wire', 'identities': [{'message_id': '<g.two@mail.aresos.invalid>'}], 'recipients': ['peer@mail.invalid']}
        event = oracle.server('DATA', 'box', identities=context['identities'], roles={}, sender='owner@mail.invalid', recipients=['peer@mail.invalid'], raw_sha256='wire',
            committed_before={'op:g:one': {'id': 'g:one', 'state': 'submitting', 'action': 'mail_send', 'context': context}})
        self.assertEqual(differences(event, oracle.script)[1], ['script.command.message-identity', 'script.context.message-identity'])

    def test_compact_packer_preserves_full_ledger_page_validation(self):
        from owner_state_oracle.gaps import pack
        detail = {'row': 'M14', 'stage': 3, 'delta': {'calls': 1, 'failures': [{'pages': [0], 'missing': [['a']], 'extra': []}]}}
        pack({'case/view': detail})
        for mutation in ('zero-calls', 'empty-failures', 'empty-delta', 'page-outside-calls', 'repeated-page', 'bad-stage', 'empty-row'):
            wrong = copy.deepcopy(detail)
            if mutation == 'zero-calls': wrong['delta']['calls'] = 0
            elif mutation == 'empty-failures': wrong['delta']['failures'] = []
            elif mutation == 'empty-delta': wrong['delta']['failures'][0]['missing'] = []
            elif mutation == 'page-outside-calls': wrong['delta']['failures'][0]['pages'] = [1]
            elif mutation == 'repeated-page': wrong['delta']['failures'][0]['pages'] = [0, 0]
            elif mutation == 'bad-stage': wrong['stage'] = 4
            else: wrong['row'] = ''
            with self.subTest(mutation=mutation), self.assertRaises(AssertionError):
                pack({'case/view': wrong})

    def test_caller_fixture_names_are_injective_and_same_width_as_tempfile(self):
        from owner_state_oracle.identity import caller_name
        names = set()
        for flow in ('attachment_export', 'testapp_export', 'export_rollback'):
            for mode in ('single', 'persistent'):
                for phase in ('live', 'crash'):
                    for point in range(301):
                        for cleanup in (0, 1, 65, 4095):
                            name = caller_name(flow, point, mode, cleanup, phase)
                            self.assertEqual(len(name), 11)
                            self.assertNotIn(name, names)
                            names.add(name)
        with self.assertRaises(ValueError):
            caller_name('attachment_export', 4096)

    def test_caller_capture_conversion_keeps_wrong_targets_distinguishable(self):
        from owner_state_oracle.caller_capture import stabilize
        from owner_state_oracle.identity import caller_name
        path = '/workspace/control/test-work/tmpabcdefgh/Downloads'
        event = {'action': 'mail_attachment_save', 'untrusted_content': {'folder': path, 'name': 'export.bin'}}
        fact = ['event:#1', 'mail_attachment_save', '', canonical(event)]
        key = 'attachment_export/persistent/101/0/exhausted/aresos log.page'
        entries = {key: {'row': 'M14', 'stage': 3, 'delta': {'calls': 1, 'failures': [{'pages': [0], 'missing': [fact], 'extra': []}]}}}
        converted, count = stabilize(entries)
        self.assertEqual(count, 1)
        actual = json.loads(converted[key]['delta']['failures'][0]['missing'][0][3])
        self.assertEqual(actual['untrusted_content']['folder'], '/workspace/control/test-work/' + caller_name('attachment_export', 101, 'persistent') + '/Downloads')
        wrong = copy.deepcopy(entries)
        other = copy.deepcopy(fact)
        other[3] = canonical({'action': 'mail_attachment_save', 'untrusted_content': {'folder': '/workspace/control/test-work/tmpijklmnop/Downloads', 'name': 'export.bin'}})
        wrong[key]['delta']['failures'][0]['extra'] = [other]
        with self.assertRaises(ValueError):
            stabilize(wrong)
        # The public audit equality still compares the complete literal path.
        from owner_state_oracle.compare import audit_fact
        record = {'seq': 1, 'time': 1, 'action': 'mail_attachment_save', 'summary': 'save', 'outcome': 'started', 'operation_id': None, **event}
        public = {**record, 'summary': 'Mail audit event', 'untrusted_content': {'summary': 'save', **event['untrusted_content']}}
        expected = audit_fact(record, expected=True)
        self.assertEqual(expected, audit_fact(public))
        public['untrusted_content']['folder'] += '-wrong'
        with self.assertRaises(AssertionError):
            Oracle().compare('wrong caller target', {expected}, {audit_fact(public)})


class StageOneRoundTwo(unittest.TestCase):
    def expired(self, notice=True):
        oracle = Oracle()
        oracle.call('control_pending', {}, 11)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        row = {'id': 'g:r', 'app': 'mail', 'action': 'mail_send', 'state': 'reserved', 'expires': 10,
               'reason': 'Awaiting exact approval; nothing submitted.'}
        expired = {**row, 'state': 'failed', 'reason': 'expired: nothing submitted', 'notice': notice}
        record = Record(events=[{'seq': 1, 'action': 'mail_send', 'set': {'op:g:r': row}},
            {'seq': 2, 'action': 'mail_send', 'set': {'op:g:r': expired}}])
        return oracle, record

    def test_expiry_notice_false_cannot_erase_obligation(self):
        oracle, record = self.expired(False)
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'pending' for f in expected))
        self.assertIn(Fact('op:g:r', 'lost-operation-notice'), oracle.lifecycle_errors)
        with self.assertRaises(AssertionError):
            oracle.compare('expiry flag', expected, set())

    def test_archive_cannot_remove_unacknowledged_expiry_including_first_read(self):
        oracle, record = self.expired()
        record.events.append({'seq': 3, 'action': 'control_archive', 'set': {'op:g:r': None}})
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'pending' for f in expected))
        self.assertIn(Fact('op:g:r', 'unjustified-removal'), oracle.lifecycle_errors)
        with self.assertRaises(AssertionError):
            oracle.compare('archive expiry', expected, set())

    def test_only_matching_committed_ack_ends_expiry_obligation(self):
        for identity, committed in (('other', True), ('g:r', False), ('g:r', True)):
            oracle, record = self.expired()
            oracle.expected(record)
            oracle.call('mail_notice_ack', {'operation_id': identity}, 12)
            oracle.script[-1].update(start_seq=2, end_seq=3)
            if committed:
                record.events.append({'seq': 3, 'action': 'mail_notice_ack', 'set': {
                    'op:g:r': {**record.events[1]['set']['op:g:r'], 'ack': True}}})
            expected = oracle.expected(record)
            self.assertEqual(any(f.kind == 'pending' for f in expected), not (identity == 'g:r' and committed))
            if identity == 'g:r' and committed:
                oracle.call('control_archive', {'confirm': 'archive finished history'}, 13)
                oracle.script[-1].update(start_seq=3, end_seq=4)
                record.events.append({'seq': 4, 'action': 'control_archive', 'set': {'op:g:r': None, 'archive:fixture': {'sha256': fingerprint([])}}})
                self.assertEqual(oracle.expected(record), set())
                self.assertEqual(oracle.lifecycle_errors, set())

    def test_expiry_obligation_survives_restore_and_restart(self):
        oracle, record = self.expired()
        expected = oracle.expected(record)
        self.assertEqual(oracle.expected(Record()), expected)
        restarted = Oracle()
        restarted.script = copy.deepcopy(oracle.script)
        self.assertEqual(restarted.expected(record), expected)

    def test_coherent_wrong_delete_destination_violates_script(self):
        from owner_state_oracle.context import differences
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1, 'message_id': '<one@mail.invalid>'}
        oracle = Oracle()
        oracle.call('mail_delete', {'operation_id': 'g:d', 'description': {'mode': 'trash', 'items': [{'reference': ref}]}}, 1)
        roles = {'Trash': ['\\Trash'], 'Other': []}
        row = {'id': 'g:d', 'state': 'submitting', 'context': {'account': 'box', 'command': 'MOVE',
            'roles': {'trash': ['Trash']}, 'source': 'Source', 'destination': 'Other', 'identities': [ref]}}
        event = oracle.server('MOVE', 'box', 'Source', [ref], roles, arguments=['1', 'Other'], committed_before={'op:g:d': row})
        errors = differences(event, oracle.script)[1]
        self.assertIn('script.command.destination', errors)
        self.assertIn('script.context.destination', errors)
        event['arguments'][1] = event['committed_before']['op:g:d']['context']['destination'] = 'Trash'
        self.assertEqual(differences(event, oracle.script)[1], [])

    def flag(self, add, remove, flags):
        oracle = Oracle()
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1}
        oracle.call('mail_flag', {'references': [ref], 'add': add, 'remove': remove}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        row = {'state': 'started', 'action': 'mail_flag', 'context': {'account': 'box', 'command': 'STORE',
            'roles': {}, 'source': 'Source', 'identities': [ref], 'flags': flags}}
        oracle.server('STORE', 'box', 'Source', [ref], {}, arguments=['1', *flags],
            call_start_seq=0, created_before={'intent:x': 1}, committed_before={'intent:x': row})
        oracle.reply({'ok': True})
        return oracle

    def test_empty_removal_cannot_replace_requested_flag_addition(self):
        oracle = self.flag(['\\Seen'], [], ['-FLAGS.SILENT', '()'])
        errors = oracle.context_errors()
        self.assertTrue(errors)
        self.assertTrue(any('script.command.flags' in f.detail for f in errors))
        self.assertTrue(any('missing' in f.detail for f in errors))

    def test_complete_flag_plan_requires_both_nonempty_branches(self):
        good = self.flag(['\\Seen'], [], ['+FLAGS.SILENT', '(\\Seen)'])
        self.assertEqual(good.context_errors(), set())
        incomplete = self.flag(['\\Seen'], ['\\Flagged'], ['-FLAGS.SILENT', '(\\Flagged)'])
        self.assertTrue(any('missing' in f.detail and '\\\\Seen' in f.detail for f in incomplete.context_errors()))

    def test_missing_original_onboarding_error_envelope_is_compared(self):
        from owner_state_oracle.driver import Driver
        oracle = StageOneFixMutations.background(self)
        oracle.call('mail_account_add', {'id': 'new'}, 2)
        oracle.script[-1]['request_method'] = 'mail_account_add'
        driver = Driver.__new__(Driver)
        driver.oracle, driver.envelopes_seen, driver.envelopes = oracle, set(), []
        driver.snapshot = lambda: Record()
        driver.capture_response(len(oracle.script) - 1, {'ok': False, 'error': {'code': 'storage_limit'}})
        self.assertEqual(len(driver.envelopes), 1)
        with self.assertRaises(AssertionError):
            driver.drain_envelopes(oracle.compare)

    def test_missing_envelope_fails_even_when_quiet_and_synthetic_results_are_named(self):
        from owner_state_oracle.driver import Driver
        from owner_state_oracle.compare import compare_envelope
        oracle = Oracle()
        with self.assertRaises(AssertionError):
            compare_envelope('quiet original', {'ok': True}, Record(), oracle, set(), oracle.compare)
        driver = Driver.__new__(Driver)
        driver.oracle, driver.envelopes_seen, driver.envelopes = oracle, set(), []
        driver.snapshot = lambda: Record()
        for flow in ('expiry', 'maintenance', 'restart_index', 'restart_tail'):
            oracle.call('control_pending', {}, 1)
            oracle.script[-1]['synthetic_result'] = flow
            driver.capture_response(len(oracle.script) - 1, {'ok': True})
        self.assertEqual(driver.envelopes, [])

    def probes(self, state='done', fault=None):
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new'}, 1, {'trace': [fault]} if fault else {})
        oracle.script[-1].update(start_seq=0, end_seq=4)
        ref = {'account': 'new', 'folder': 'Probe', 'uidvalidity': 1, 'uid': 1, 'message_id': '<probe@mail.invalid>'}
        oracle.server('APPEND', 'new', 'Probe', arrived=[ref], before_seq=0)
        oracle.server('DELETE', 'new', arguments=['Probe'], accepted=False, response_code='NO',
            response_text=['[CANNOT] Nonempty DELETE forbidden'], before_seq=0, fault_point=10)
        oracle.server('FETCH', 'new', 'Probe', identities=[ref])
        oracle.server('EXPUNGE', 'new', 'Probe', identities=[ref], arguments=['1'], before_seq=1, fault_point=20)
        oracle.server('DELETE', 'new', arguments=['Probe'], before_seq=2, fault_point=30)
        oracle.server('DATA', 'new')
        oracle.server('SENT', 'new', identities=[ref])
        record = Record(events=[
            {'seq': 1, 'action': 'mail_onboarding_folder_probe', 'set': {'op:probe': {'action': 'mail_onboarding_folder_probe',
                'state': 'refused', 'payload': {'folder': 'Probe'}}}},
            {'seq': 2, 'action': 'mail_delete', 'set': {'op:cleanup': {'action': 'mail_delete', 'state': state,
                'payload': {'items': [{'reference': ref}]}}}},
            {'seq': 3, 'action': 'mail_onboarding_folder_probe', 'set': {'op:empty': {'action': 'mail_onboarding_folder_probe',
                'state': 'done', 'payload': {'folder': 'Probe', 'empty': True}}}},
            {'seq': 4, 'action': 'mail_account_add', 'outcome': 'done', 'set': {'mail:account:new': {'id': 'new', 'onboarded': True}}}])
        return oracle, record

    def test_coherent_false_cleanup_state_and_public_reason_are_rejected(self):
        oracle, record = self.probes('failed')
        expected = oracle.qualification_facts({}, record)
        self.assertTrue(any(f.kind == 'unjustified-probe-result' for f in oracle.lifecycle_errors))
        wrong = {'data': {'accounts': [{'id': 'new', 'ready': True, 'sent_policy': 'server', 'safe_folder_delete': False,
            'folder_delete_reason': 'Exact probe UID EXPUNGE cleanup failed'}]}}
        with self.assertRaises(AssertionError):
            oracle.compare('false qualification', expected, oracle.qualification_facts(wrong, record, actual=True))

    def test_empty_probe_false_failure_and_wrong_commit_order_are_rejected(self):
        for mutation in ('false-state', 'wrong-order'):
            oracle, record = self.probes()
            if mutation == 'false-state':
                record.events[2]['set']['op:empty']['state'] = 'failed'
            else:
                oracle.servers[4]['before_seq'] = 3
            self.assertEqual(oracle.qualification(record)['new']['folder_delete_reason'], 'qualified')
            self.assertTrue(any(f.source == 'op:empty' and f.kind == 'unjustified-probe-result' for f in oracle.lifecycle_errors))

    def test_probe_failure_needs_a_later_fault_or_failed_reply(self):
        for fault, reason in (((5, 'journal.write', 'ENOSPC'), 'qualified'),
                              ((25, 'journal.write', 'ENOSPC'), 'exact-cleanup-failed')):
            oracle, record = self.probes('failed', fault)
            self.assertEqual(oracle.qualification(record)['new']['folder_delete_reason'], reason)
        oracle, record = self.probes('failed')
        oracle.servers[3].update(accepted=False, response_code='NO')
        self.assertEqual(oracle.qualification(record)['new']['folder_delete_reason'], 'exact-cleanup-failed')
        self.assertEqual(oracle.lifecycle_errors, set())

    def test_fault_after_observed_probe_commit_cannot_justify_false_failure(self):
        oracle, record = self.probes('failed', (35, 'journal.write', 'ENOSPC'))
        oracle.commit_fault_points[(1, 2)] = 30
        self.assertEqual(oracle.qualification(record)['new']['folder_delete_reason'], 'qualified')
        self.assertTrue(any(f.source == 'op:cleanup' and f.kind == 'unjustified-probe-result' for f in oracle.lifecycle_errors))

    def test_open_account_and_filing_obligations_survive_row_removal(self):
        for key, row in (('mail:account:new', {'id': 'new', 'onboarded': False}),
                         ('mail:filing:f', {'id': 'f', 'state': 'started', 'account': 'box'})):
            oracle = Oracle()
            record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {key: row}},
                {'seq': 2, 'action': 'control_archive', 'set': {key: None}}])
            expected = oracle.expected(record)
            self.assertTrue(any(f.source == key and f.kind == 'recovery' for f in expected))
            self.assertIn(Fact(key, 'unjustified-removal'), oracle.lifecycle_errors)

    def test_mutated_committed_context_and_unproved_resolution_do_not_end_work(self):
        oracle = Oracle()
        oracle.call('mail_delete', {'operation_id': 'g:d'}, 1)
        oracle.script[-1].update(start_seq=1, end_seq=3)
        old = {'id': 'g:d', 'app': 'mail', 'action': 'mail_delete', 'state': 'submitting', 'payload': {'mode': 'trash'}}
        record = Record(events=[{'seq': 1, 'action': 'mail_delete', 'set': {'op:g:d': old}},
            {'seq': 2, 'action': 'mail_delete', 'set': {'op:g:d': {**old, 'state': 'done', 'payload': {'mode': 'permanent'}}}}])
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'recovery' for f in expected))
        self.assertIn(Fact('op:g:d', 'changed-operation-context', detail='payload'), oracle.lifecycle_errors)
        self.assertIn(Fact('op:g:d', 'unjustified-resolution'), oracle.lifecycle_errors)

    def test_stage_outcome_needs_correlated_delivered_command(self):
        for stage, outcome in (('smtp_data', 'accepted:250'), ('sent_copy', 'done'), ('folder', 'deleted')):
            oracle = Oracle()
            row = {'id': 'g:s', 'app': 'mail', 'action': 'mail_send', 'state': 'submitting', 'stages': {stage: outcome}}
            record = Record(events=[{'seq': 1, 'action': 'mail_send', 'set': {'op:g:s': row}}])
            oracle.expected(record)
            self.assertIn(Fact('op:g:s', 'unjustified-stage', detail=stage), oracle.lifecycle_errors)

    def test_forged_restore_archive_and_notice_metadata_are_detected(self):
        oracle = Oracle()
        oracle.call('mail_accounts', {}, 10)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        record = Record(events=[{'seq': 1, 'time': 10, 'action': 'mail_accounts', 'set': {
            'restore_pending': True, 'archived:g:s': {'seq': 1},
            'notice:n': {'id': 'wrong', 'created_at': 1000}}}])
        oracle.expected(record)
        self.assertTrue({'unjustified-restore-transition', 'unjustified-archive-marker', 'notice-identity', 'notice-creation-time'} <=
                        {f.kind for f in oracle.lifecycle_errors})

    def test_decoder_validates_event_time_and_full_operation_against_fence(self):
        state, evidence = OwnerOracle.disk(self)
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            event = json.loads(db.execute('SELECT value FROM events').fetchone()[0])
            event['time'] += 1
            db.execute('UPDATE events SET value=?', (canonical(event),))
            db.commit()
        with self.assertRaisesRegex(ValueError, 'independent fence'):
            decode(state, evidence)
        event['time'] -= 1
        operation = {'id': 'g:s', 'generation': 'g', 'input_hash': 'input', 'state': 'submitting'}
        fence = event['record']
        fence['operations'] = [operation]
        fence['hash'] = fingerprint({k:v for k,v in fence.items() if k != 'hash'})
        event['set']['op:g:s'] = {**operation, 'state': 'done'}
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            db.execute('UPDATE events SET value=?', (canonical(event),))
            db.execute('UPDATE head SET hash=?', (fence['hash'],))
            db.commit()
        (evidence / 'operations.jsonl').write_text(canonical(fence) + '\n' + canonical({'commit': 1, 'hash': fence['hash']}) + '\n')
        with self.assertRaisesRegex(ValueError, 'Operation differs'):
            decode(state, evidence)

    def test_decoder_missing_history_cannot_be_justified_by_current_head(self):
        state, evidence = OwnerOracle.disk(self)
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            db.execute('DELETE FROM events')
            db.commit()
        with self.assertRaisesRegex(ValueError, 'Committed history missing'):
            decode(state, evidence)

    def test_onboarding_context_cannot_authorize_another_account_or_unrelated_folder(self):
        from owner_state_oracle.context import differences
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new', 'addresses': ['owner@mail.invalid']}, 1)
        context = {'command': 'DELETE', 'account': 'other', 'roles': {}, 'source': 'Other', 'destination': 'Other', 'identities': []}
        row = {'state': 'started', 'action': 'mail_account_add', 'context': context}
        event = oracle.server('DELETE', 'other', roles={}, arguments=['Other'], call_start_seq=0,
            created_before={'intent:x': 1}, committed_before={'intent:x': row})
        errors = differences(event, oracle.script, oracle.servers)[1]
        self.assertIn('script.command.account', errors)
        self.assertIn('script.context.account', errors)
        self.assertIn('script.probe-creation', errors)
        self.assertIn('script.command.destination', errors)

    def test_false_app_flag_cannot_hide_a_scripted_mail_reservation(self):
        oracle = Oracle()
        row = {'id': 'g:r', 'app': 'testapp', 'action': 'mail_send', 'state': 'reserved'}
        record = Record(events=[{'seq': 1, 'action': 'mail_send', 'set': {'op:g:r': row}}])
        expected = oracle.expected(record, app='mail')
        self.assertTrue(any(f.kind == 'pending' for f in expected))
        self.assertIn(Fact('op:g:r', 'unjustified-app-scope'), oracle.lifecycle_errors)
        with self.assertRaises(AssertionError):
            oracle.compare('false app scope', expected, set())

    def test_coherent_wrong_app_and_action_cannot_hide_scripted_reservation(self):
        oracle = Oracle()
        oracle.call('mail_prepare_send', {}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        row = {'id': 'g:r', 'app': 'testapp', 'action': 'testapp_send', 'state': 'reserved'}
        record = Record(events=[{'seq': 1, 'action': 'testapp_send', 'set': {'op:g:r': row}}])
        self.assertTrue(any(f.kind == 'pending' for f in oracle.expected(record, app='mail')))
        self.assertIn(Fact('op:g:r', 'unjustified-operation-action'), oracle.lifecycle_errors)


class StageOneRoundThree(unittest.TestCase):
    def test_initial_payload_and_completion_require_every_approved_target(self):
        oracle = Oracle()
        refs = [dict(account='box', folder='Source', uidvalidity=1, uid=n, message_id='<synthetic@mail.invalid>') for n in (1, 2)]
        items = [{'reference': r} for r in refs]
        oracle.call('mail_delete', {'operation_id': 'g:d', 'description': {'items': items, 'mode': 'permanent'}}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=3)
        row = {'id': 'g:d', 'app': 'mail', 'action': 'mail_delete', 'state': 'submitting', 'payload': {'items': items[:1], 'mode': 'permanent'}}
        oracle.server('EXPUNGE', 'box', 'Source', refs, arguments=['1'], before_seq=1)
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'op:g:d': row}},
            {'seq': 2, 'action': 'mail_delete', 'set': {'op:g:d': {**row, 'state': 'done'}}}])
        expected = oracle.expected(record)
        self.assertTrue(any(f.kind == 'recovery' for f in expected))
        self.assertIn(Fact('op:g:d', 'unapproved-payload', detail='items'), oracle.lifecycle_errors)
        self.assertTrue(oracle.completion_errors(Record(rows={'op:g:d': {**row, 'state': 'done'}})))

    def test_unallowlisted_state_edges_retain_reservation_and_recovery(self):
        for before, after, kind in (('reserved', 'refused', 'pending'), ('unknown', 'reserved', 'recovery')):
            oracle = Oracle()
            oracle.call('mail_operation_status', {'operation_id': 'g:d'}, 2)
            oracle.script[-1].update(start_seq=1, end_seq=2)
            row = {'id': 'g:d', 'app': 'mail', 'action': 'mail_delete', 'state': before}
            record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'op:g:d': row}},
                {'seq': 2, 'action': 'mail_delete', 'set': {'op:g:d': {**row, 'state': after, 'notice': False}}}])
            self.assertTrue(any(f.kind == kind for f in oracle.expected(record)))
            self.assertIn(Fact('op:g:d', 'unjustified-resolution'), oracle.lifecycle_errors)

    def test_restore_cannot_explain_a_later_missing_sequence(self):
        from owner_state_oracle.records import unexplained_sequences
        record = Record(committed={1, 2, 3}, events=[
            {'seq': 1, 'action': 'control_restore_confirm', 'set': {'generation': 'g'}},
            {'seq': 3, 'action': 'fixture', 'set': {}}])
        self.assertEqual(unexplained_sequences(record), {2})
        oracle = Oracle()
        oracle.expected(record)
        self.assertIn(Fact('sequence:2', 'missing-committed-history'), oracle.lifecycle_errors)

    def test_incomplete_account_survives_rollback_restore_and_explicit_removal(self):
        for deletion in (False, True):
            oracle = Oracle()
            row = {'id': 'new', 'onboarded': False}
            original = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'mail:account:new': row}}])
            first = oracle.expected(original)
            oracle.call('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, 2)
            oracle.script[-1].update(start_seq=1, end_seq=2)
            restored = Record(events=[{'seq': 2, 'action': 'control_restore_confirm', 'set': {'generation': 'new'}}])
            if deletion:
                restored.events = original.events + [{'seq': 2, 'action': 'control_restore_confirm', 'set': {'mail:account:new': None, 'generation': 'new'}}]
            self.assertTrue(first <= oracle.expected(restored))
            self.assertTrue(oracle.lifecycle_errors)

    def test_false_filing_hash_cannot_justify_false_locations(self):
        oracle = Oracle()
        real_hash = hashlib.sha256(b'real-bytes').hexdigest()
        source = dict(account='box', folder='Source', uidvalidity=1, uid=1, message_id='<synthetic@mail.invalid>')
        oracle.call('mail_move', {'references': [source], 'target': 'Target'}, 1)
        oracle.server('FIXTURE_STATE', 'box', mailboxes={'Source': [{**source, 'sha256': real_hash}]})
        mutation = oracle.server('MOVE', 'box', 'Source', [{**source, 'sha256': real_hash}], arguments=['1', 'Target'])
        listing = oracle.server('LIST', 'box', roles={'Target': []}, mailboxes={'Target': [{**source, 'folder': 'Target', 'sha256': real_hash}]})
        oracle.server('SELECT', 'box', 'Target')
        oracle.server('SEARCH', 'box', 'Target', arguments=[None, 'ALL'], response_text=['1'])
        oracle.server('FETCH', 'box', 'Target', arguments=['1', '(UID FLAGS BODY.PEEK[])'],
                      fetch_result=[{'metadata_hex': b'1 (UID 1 BODY[] {10}'.hex(), 'literal_hex': b'real-bytes'.hex()}])
        oracle.server('SCAN_RESULT', 'box', check_sources=['mail:filing:f'], scan_start=2)
        context = {'id': 'f', 'records': [{'source': source, 'sha256': 'false-bytes'}]}
        locations = oracle.locations(context, listing, mutation)
        self.assertEqual(locations[0]['observed_locations'][0]['folder'], 'Target')
        self.assertIn(Fact('mail:filing:f', 'unverified-source-hash', detail=canonical(source)), oracle.lifecycle_errors)

    def test_resolution_table_fails_closed_for_every_missing_proof(self):
        from owner_state_oracle.resolutions import RESOLUTIONS, permitted
        self.assertFalse(permitted('new-production-resolution', {}))
        for kind, rule in RESOLUTIONS.items():
            required = rule.proofs
            self.assertTrue(permitted(kind, dict.fromkeys(required, True)))
            for proof in required:
                incomplete = dict.fromkeys(required, True)
                incomplete.pop(proof)
                self.assertFalse(permitted(kind, incomplete), (kind, proof))

    def test_decoder_restore_at_one_rejects_missing_later_intent(self):
        state, evidence = OwnerOracle.disk(self)
        with closing(sqlite3.connect(state / 'control.sqlite')) as db:
            first = json.loads(db.execute('SELECT value FROM events').fetchone()[0])
            first['action'] = 'control_restore_confirm'
            db.execute('UPDATE events SET value=? WHERE seq=1', (canonical(first),))
            fences = [first['record']]
            for seq in (2, 3):
                fence = {'format': 2, 'seq': seq, 'previous': fences[-1]['hash'], 'time': 123 + seq,
                         'generation': 'g', 'operations': []}
                fence['hash'] = fingerprint(fence)
                fences.append(fence)
            last = {'seq': 3, 'time': 126, 'action': 'fixture', 'set': {}, 'record': fences[-1]}
            db.execute('INSERT INTO events VALUES (?,?)', (3, canonical(last)))
            db.execute('UPDATE head SET seq=3,hash=?', (fences[-1]['hash'],))
            db.commit()
        (evidence / 'operations.jsonl').write_text(''.join(canonical(f) + '\n' + canonical({'commit': f['seq'], 'hash': f['hash']}) + '\n' for f in fences))
        with self.assertRaisesRegex(ValueError, 'Committed history missing'):
            decode(state, evidence)

    def test_rollback_to_existing_reserved_row_does_not_erase_unknown_recovery(self):
        oracle = Oracle()
        row = {'id': 'g:d', 'app': 'mail', 'action': 'mail_delete', 'state': 'unknown'}
        oracle.expected(Record(rows={'op:g:d': row}))
        restored = Record(rows={'op:g:d': {**row, 'state': 'reserved'}})
        self.assertTrue(any(f.kind == 'recovery' for f in oracle.expected(restored)))
        self.assertIn(Fact('op:g:d', 'narrowed-obligation', detail='operation'), oracle.lifecycle_errors)

    def test_onboarding_resolution_releases_only_corroborated_completion(self):
        oracle = Oracle()
        row = {'id': 'new', 'onboarded': False}
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'mail:account:new': row}}])
        self.assertTrue(any(f.kind == 'recovery' for f in oracle.expected(record)))
        oracle.call('mail_account_add', {'id': 'new'}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        oracle.server('DATA', 'new', before_seq=1)
        record.events.append({'seq': 2, 'action': 'mail_account_add', 'outcome': 'done', 'set': {'mail:account:new': {**row, 'onboarded': True}}})
        self.assertFalse(any(f.source == 'mail:account:new' and f.kind == 'recovery' for f in oracle.expected(record)))

    def test_perturbation_self_test_detects_a_deliberately_broken_oracle(self):
        from unittest.mock import patch
        from owner_state_oracle.perturb import check
        oracle = Oracle()
        record = Record(rows={'x': {'state': 'reserved'}})
        def broken(self, value, **kwargs):
            return {Fact('x', 'pending')} if value.rows.get('x', {}).get('state') == 'reserved' else set()
        with patch.object(Oracle, 'expected', broken), patch.object(Oracle, 'hold_facts', return_value=set()):
            with self.assertRaisesRegex(AssertionError, 'Silent owner-state perturbation.*broken-scenario.*remove-row:x'):
                check('broken-scenario', oracle, record)

    def test_scripted_repair_keeps_its_parent_stage_and_settlement_hold(self):
        oracle = Oracle()
        args = {'operation_id': 'g:parent', 'stage': 'answered_flag'}
        oracle.call('mail_operation_repair', args, 1)
        oracle.script[-1].update(start_seq=0, end_seq=2)
        row = {'id': 'g:repair', 'action': 'mail_operation_repair', 'app': 'mail',
               'repair_of': 'g:wrong', 'payload': {'operation_id': 'g:wrong', 'stage': 'sent_copy'}, 'state': 'reserved'}
        record = Record(events=[{'seq': 1, 'action': 'mail_operation_repair', 'set': {'op:g:repair': row}},
            {'seq': 2, 'action': 'mail_operation_repair', 'set': {'op:g:repair': {**row, 'state': 'submitting'}}}])
        projected = oracle.lifecycle(record)
        self.assertEqual(projected.rows['op:g:repair']['state'], 'submitting')
        self.assertEqual(projected.rows['op:g:repair']['repair_of'], 'g:parent')
        self.assertEqual(projected.rows['op:g:repair']['payload'], args)
        self.assertIn(Fact('settle:g:repair', 'held'), oracle.holds(record))
        self.assertIn(Fact('op:g:repair', 'unapproved-repair-context'), oracle.lifecycle_errors)

    def test_a_current_storage_fault_cannot_resolve_earlier_unknown_work(self):
        oracle = Oracle()
        oracle.call('mail_operation_status', {'operation_id': 'g:d'}, 2, {'trace': [(1, 'journal.write', 'ENOSPC')]})
        oracle.script[-1].update(start_seq=1, end_seq=2)
        row = {'id': 'g:d', 'action': 'mail_delete', 'app': 'mail', 'state': 'unknown'}
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'op:g:d': row}},
            {'seq': 2, 'action': 'mail_delete', 'set': {'op:g:d': {**row, 'state': 'failed', 'notice': False}}}])
        self.assertTrue(any(f.kind == 'recovery' for f in oracle.expected(record)))
        self.assertIn(Fact('op:g:d', 'unjustified-resolution'), oracle.lifecycle_errors)

    def test_stage_event_metadata_is_compared_to_its_committed_stage(self):
        oracle = Oracle()
        row = {'id': 'g:d', 'action': 'mail_send', 'app': 'mail', 'state': 'submitting', 'stages': {'sent_copy': 'done'}}
        record = Record(events=[{'seq': 1, 'action': 'mail_send', 'operation_id': 'g:d',
            'untrusted_content': {'stage': 'sent_copy', 'outcome': 'failed'}, 'set': {'op:g:d': row}}])
        oracle.expected(record)
        self.assertIn(Fact('op:g:d', 'changed-stage-event', detail='1'), oracle.lifecycle_errors)

    def test_restore_requires_an_independently_observed_restore_precondition(self):
        for locked in (False, True):
            oracle = Oracle()
            oracle.call('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, 1)
            oracle.script[-1].update(start_seq=1, end_seq=2, restore_precondition=locked)
            event = {'seq': 2, 'action': 'control_restore_confirm', 'set': {'generation': 'new'}}
            self.assertEqual(oracle.restore_proof(event), locked)
            oracle.expected(Record(events=[event], committed={2}))
            self.assertEqual(Fact('sequence:2', 'unsupported-resolution', detail='restore') in oracle.lifecycle_errors, not locked)

    def test_intent_and_export_scope_come_from_the_script(self):
        for source in ('intent:i', 'export:e'):
            oracle = Oracle()
            oracle.call('mail_attachment_save', {}, 1)
            oracle.script[-1].update(start_seq=0, end_seq=1)
            row = {'id': source.split(':')[1], 'action': 'testapp_send', 'app': 'testapp', 'state': 'started'}
            record = Record(events=[{'seq': 1, 'action': 'mail_attachment_save', 'set': {source: row}}])
            self.assertTrue(any(f.source == source and f.kind == 'recovery' for f in oracle.expected(record, app='mail')))
            self.assertIn(Fact(source, 'unjustified-app-scope'), oracle.lifecycle_errors)

    def test_expiry_notice_survives_a_different_current_recovery_state(self):
        oracle, record = StageOneRoundTwo.expired(self)
        initial = oracle.expected(record)
        notice = Fact('op:g:r', 'operation-notice', 'g:r', 'expired')
        self.assertIn(notice, initial)
        recovered = {**record.events[-1]['set']['op:g:r'], 'state': 'unknown',
                     'reason': 'Restored log: newer evidence is missing.', 'notice': False}
        self.assertIn(notice, oracle.expected(Record(rows={'op:g:r': recovered})))
        from owner_state_oracle.compare import pending_facts
        self.assertNotIn(notice, pending_facts({'items': [{'operation_id': 'g:r', **recovered}]}))

    def test_legacy_and_modern_intent_ids_bind_once(self):
        for identity in ('i', 'recovery-i'):
            oracle = Oracle()
            oracle.seed_sequence = 1
            row = {'id': identity, 'app': 'mail', 'action': 'mail_flag', 'state': 'started'}
            record = Record(rows={'intent:i': row}, events=[{'seq': 1, 'action': 'fixture', 'set': {'intent:i': row}}])
            initial = oracle.expected(record)
            self.assertIn(Fact('intent:i', 'recovery-handle', identity), initial)
            self.assertEqual(oracle.lifecycle_errors, set())
            changed = {**row, 'id': 'recovery-i' if identity == 'i' else 'i'}
            later = Record(rows={'intent:i': changed}, events=[{'seq': 1, 'action': 'fixture', 'set': {'intent:i': changed}}])
            self.assertEqual(oracle.expected(later), initial)
            self.assertIn(Fact('intent:i', 'source-identity'), oracle.lifecycle_errors)

    def test_valid_sent_check_reopen_is_corroborated_before_its_read(self):
        oracle = Oracle()
        oracle.seed_sequence = 1
        oracle.call('mail_accounts', {}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=3)
        row = {'id': 'g:s', 'app': 'mail', 'action': 'mail_send', 'state': 'done',
               'sent_copy_check': {'state': 'checked', 'clean': True}}
        opened = {**row, 'sent_copy_check': {'state': 'open', 'clean': True}}
        record = Record(events=[{'seq': 1, 'action': 'fixture', 'set': {'op:g:s': row}},
            {'seq': 2, 'action': 'mail_sent_copy_check_open', 'set': {'op:g:s': opened}}])
        oracle.server('SENT', 'box', 'Sent', [], source='op:g:s', before_seq=2)
        oracle.expected(record)
        self.assertNotIn(Fact('op:g:s', 'unjustified-check-reopen', detail='2'), oracle.lifecycle_errors)
        record.events[-1]['set']['op:g:s'] = {**opened, 'sent_copy_check': row['sent_copy_check']}
        self.assertTrue(any(f.kind == 'unchecked' for f in oracle.expected(record)))
        self.assertIn(Fact('op:g:s', 'missing-check-enrollment', detail='2'), oracle.lifecycle_errors)
        record.events[-1]['set']['op:g:s'] = opened
        record.events[-1]['action'] = 'mail_send'
        oracle.expected(record)
        self.assertIn(Fact('op:g:s', 'unjustified-check-reopen', detail='2'), oracle.lifecycle_errors)


class StageTwoPartA(unittest.TestCase):
    def test_pre_move_list_and_undelivered_results_never_close_filing(self):
        source = dict(account='box', folder='Source', uidvalidity=1, uid=1, message_id='<synthetic@mail.invalid>')
        roles = {'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash'], 'Target': []}
        for post in ('absent', 'lost', 'negative', 'delivered'):
            oracle = Oracle()
            oracle.call('mail_move', {'references': [source], 'target': 'Target'}, 1)
            oracle.script[-1].update(start_seq=0, end_seq=2)
            row = {'id': 'f', 'account': 'box', 'verb': 'move', 'sources': [source], 'target': 'Target', 'state': 'started'}
            oracle.server('LIST', 'box', roles=roles, before_seq=0)
            oracle.server('MOVE', 'box', 'Source', [source], roles, arguments=['1', 'Target'], before_seq=1,
                          call_start_seq=0, created_before={'mail:filing:f': 1}, committed_before={'mail:filing:f': row}, copyuid_delivered=False)
            if post != 'absent':
                listing = oracle.server('LIST', 'box', roles=roles, before_seq=1, accepted=post != 'negative', reply='lost' if post == 'lost' else 'delivered')
            if post == 'delivered':
                empty_scan(oracle, listing, ['mail:filing:f'])
            record = Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_move', 'set': {'mail:filing:f': row}},
                {'seq': 2, 'time': 1, 'action': 'mail_move', 'set': {'mail:filing:f': {**row, 'state': 'done', 'check_open': False}}}])
            from owner_state_oracle.compare import compare_proofs
            failures = []
            compare_proofs(oracle, record, lambda view, expected, actual: failures.extend(actual - expected))
            if post == 'delivered':
                self.assertNotIn(Fact('mail:filing:f', 'unjustified-check-close', detail='2'), failures)
            else:
                self.assertIn(Fact('mail:filing:f', 'unjustified-check-close', detail='2'), failures)
                self.assertTrue(any(f.kind == 'recovery' for f in oracle.expected(record)))

    def test_another_unsubscribe_post_cannot_resolve_this_operation(self):
        from owner_state_oracle.compare import compare_proofs
        oracle = Oracle()
        ref = {'account': 'box', 'folder': 'Source', 'uidvalidity': 1, 'uid': 1, 'message_id': '<synthetic@mail.invalid>'}
        rows, events = {}, []
        for n, status in ((1, 200), (2, 500)):
            opid = 'g:post' + str(n)
            args = {'operation_id': opid, 'description': {'reference': ref, 'target': 'https://unsubscribe.invalid/' + str(n), 'method': 'POST', 'body': 'List-Unsubscribe=One-Click'}}
            oracle.call('mail_unsubscribe', args, n)
            start = (n - 1) * 2
            oracle.script[-1].update(start_seq=start, end_seq=start + 2)
            row = dict(id=opid, app='mail', action='mail_unsubscribe', state='submitting', payload=args['description'])
            key = 'op:' + opid
            oracle.server('POST', 'box', arguments=[], status=status, url=args['description']['target'], body='List-Unsubscribe=One-Click',
                before_seq=start + 1, call_start_seq=start, created_before={key: start + 1}, committed_before={key: row})
            done = {**row, 'state': 'done'}
            events.extend([{'seq': start + 1, 'time': n, 'action': 'mail_unsubscribe', 'set': {key: row}},
                           {'seq': start + 2, 'time': n, 'action': 'mail_unsubscribe', 'set': {key: done}}])
            rows[key] = done
        failures = []
        compare_proofs(oracle, Record(rows=rows, events=events), lambda view, expected, actual: failures.extend(actual - expected))
        self.assertTrue(any(f.source == 'op:g:post2' and f.kind == 'false-completion' for f in failures))
        self.assertFalse(any(f.source == 'op:g:post1' and f.kind == 'false-completion' for f in failures))
        self.assertTrue(any(f.source == 'op:g:post2' and f.kind == 'recovery' for f in oracle.expected(Record(rows=rows, events=events))))

    def test_field_audit_includes_each_list_scalar_and_append_flags(self):
        from owner_state_oracle.perturb import audited_leaves, scalar_fields
        fields = {'recipients': ['one@mail.invalid', 'two@mail.invalid'], 'flags': ['\\Seen', '\\Flagged'],
                  'append_flags': ['\\Draft', '\\Seen'], 'targets': [1, 2], 'locations': ['Source', 'Target'], 'new_field': 4}
        changed = {path for path, _, _ in audited_leaves(fields, ())}
        self.assertLessEqual(set(scalar_fields(fields)), changed)
        self.assertIn(('append_flags', 0), changed)
        from unittest.mock import patch
        with patch('owner_state_oracle.perturb.leaves', return_value=iter([])):
            with self.assertRaisesRegex(AssertionError, 'Unaudited decoded fields'):
                list(audited_leaves(fields, ()))

    def test_helper_error_counts_only_when_forwarded_by_the_shared_comparison(self):
        from owner_state_oracle.perturb import evaluate
        from unittest.mock import patch
        oracle, record = Oracle(), Record()
        with patch.object(Oracle, 'expected', side_effect=ValueError('bad record')):
            self.assertTrue(evaluate(oracle, record)[1])
            with patch('owner_state_oracle.perturb.compare_proofs'):
                self.assertEqual(evaluate(oracle, record)[1], set())

    def test_record_audit_fails_if_a_new_field_is_not_perturbed(self):
        from owner_state_oracle.perturb import check, mutations
        from unittest.mock import patch
        record = Record(rows={'fixture': {'new_material_field': 'value'}}, head=(0, ''))
        selected = [item for item in mutations(record) if 'new_material_field' not in item[0]]
        with patch('owner_state_oracle.perturb.mutations', return_value=iter(selected)):
            with self.assertRaisesRegex(AssertionError, 'Unaudited decoded fields'):
                check('new-field', Oracle(), record)

    def test_frozen_oracle_does_not_retain_the_live_production_driver(self):
        from owner_state_oracle.perturb import freeze
        oracle = Oracle()
        oracle.response_observer = lambda *_: None
        oracle.call('mail_accounts', {}, 1)
        frozen = freeze(oracle)
        oracle.script[0]['arguments']['later'] = True
        self.assertIsNone(frozen.response_observer)
        self.assertEqual(frozen.script[0]['arguments'], {})

    def test_server_folder_decoder_preserves_quoting_ampersands_and_modified_utf7(self):
        from owner_state_oracle.transcript import folder_name
        self.assertEqual(folder_name(b'"Junk&-Other"'), 'Junk&Other')
        self.assertEqual(folder_name(b'"Junk&AOQ-"'), 'Junkä')
        self.assertEqual(folder_name(b'"Junk\\\\Root"'), 'Junk\\Root')
        self.assertEqual(folder_name(b'"Junk\\"two"'), 'Junk"two')

    def test_internal_probe_binding_uses_command_identity_with_multiple_open_probes(self):
        from owner_state_oracle.context import bind, differences
        script = [{'call': 1, 'action': 'mail_account_add', 'arguments': {}}]
        rows = {'op:first': {'id': 'first', 'state': 'submitting', 'payload': {'folder': 'Probe'}},
                'op:second': {'id': 'second', 'state': 'submitting', 'payload': {'composition': {'mail': {}}},
                              'context': {'command': 'DATA', 'account': 'box', 'source': 'sender@mail.invalid',
                                          'destination': 'wrong', 'recipients': [], 'identities': [{'message_id': '<second@mail.aresos.invalid>'}],
                                          'sha256': 'wire', 'roles': {}}}}
        event = {'call': 1, 'command': 'DATA', 'account': 'box', 'sender': 'sender@mail.invalid',
                 'roles': {}, 'recipients': [], 'raw_sha256': 'wire', 'call_start_seq': 0,
                 'created_before': {'op:first': 1, 'op:second': 2}, 'committed_before': rows,
                 'identities': [{'message_id': '<second@mail.aresos.invalid>'}]}
        self.assertEqual(bind(event, script)[0], 'op:second')
        self.assertIn('destination', differences(event, script)[1])
        # A coherently false context cannot change which approved operation
        # matches the command, nor stand in for an absent committed source.
        rows['op:second']['context']['identities'] = [{'message_id': '<first@mail.aresos.invalid>'}]
        self.assertEqual(bind(event, script)[0], 'op:second')
        self.assertIn('identities', differences(event, script)[1])
        del rows['op:second']
        self.assertIsNone(bind(event, script)[0])
