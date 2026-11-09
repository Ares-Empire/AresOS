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
        allowed = {'contextlib', 'email', 'context', 'copy', 'dataclasses', 'hashlib', 'json', 'pathlib', 'sqlite3', 'shutil', 'tempfile', 'time', 're', 'model', 'records'}
        for name in ('__init__.py', 'records.py', 'model.py', 'compare.py', 'context.py', 'gaps.py'):
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

    def test_same_evidence_ack_clean_and_recurrence_are_independent(self):
        oracle, record = self.recorded()
        record.rows['notice:n'] = {'id': 'n', 'source_key': 'op:g:send', 'check_kind': 'sent_copies'}
        first = oracle.expected(record)
        self.assertEqual(first, oracle.expected(record))
        record.events.append({'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:n': {**record.rows['notice:n'], 'ack': True}}})
        self.assertEqual(oracle.expected(record), set())
        record.events.append({'seq': 2, 'action': 'mail_sent_copy_check', 'set': {'op:g:send': {'sent_copy_check': {'state': 'checked', 'clean': True}}}})
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
        for command in ('DATA', 'APPEND', 'MOVE', 'COPY', 'STORE', 'EXPUNGE', 'CREATE', 'DELETE', 'RENAME', 'POST', 'RECEIVE'):
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
            oracle.call('filing check', {}, 2)
            oracle.script[-1]['end_seq'] = 2
            oracle.server('LIST', before_seq=1, roles={'Target': [], 'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']})
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
        record.events.append({'seq': 1, 'action': 'mail_notice_ack', 'set': {'notice:old': {**old, 'ack': True}}})
        self.assertEqual(oracle.expected(record), set())
        record.events.append({'seq': 2, 'action': 'mail_sent_copy_check', 'set': {'op:g:send': {'sent_copy_check': {'state': 'checked', 'clean': True}}}})
        oracle.call('mail_operation_status', {'operation_id': 'g:send'}, 125)
        oracle.script[-1]['end_seq'] = 2
        oracle.server('SENT', 'box', 'Sent', oracle.servers[0]['identities'], source='op:g:send', before_seq=1)
        record.rows['notice:new'] = {**old, 'id': 'new'}
        self.assertEqual(oracle.expected(record), set())
        self.assertTrue(oracle.invalid_clean_results)

    def test_public_notice_must_expose_exact_context_not_only_opaque_id_and_role(self):
        from owner_state_oracle.compare import notice_facts
        oracle = Oracle()
        source = 'mail:rename:r'
        context = {'id': 'r', 'account': 'box', 'source': 'Source', 'target': 'Target', 'message_count': 3}
        evidence = {'target': 'Target', 'role': 'Trash'}
        saved = {'id': 'n', 'source_key': source, 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(evidence)}
        record = Record(rows={source: {**context, 'state': 'partial'}, 'notice:n': saved},
                        events=[{'seq': 1, 'action': 'mail_folder_rename', 'set': {source: {**context, 'state': 'started'}}}])
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
        from owner_state_oracle.gaps import Gaps, pack, unpack
        recorded = Gaps(recording=True)
        for case in ('flow/single/1', 'flow/single/2'):
            check = recorded.checker(case)
            check('warning', {Fact('source', 'warning')}, set())
            check.finish()
        packed = pack(recorded.entries)
        self.assertEqual(len(packed['groups']), 1)
        self.assertEqual(unpack(packed), recorded.entries)
        strict = Gaps(recording=True)
        strict.recording, strict.entries = False, unpack(packed)
        check = strict.checker('flow/single/3')
        check('warning', {Fact('source', 'warning')}, set())
        with self.assertRaisesRegex(AssertionError, 'Unlisted'):
            check.finish()

    def test_every_pinned_gap_belongs_to_an_executed_suite(self):
        from owner_state_oracle.gaps import PATH, unpack
        sweep = Path(__file__).resolve().parents[1] / 'mail_tests/test_owner_state_sweep.py'
        owners = {'contract', 'channel', 'G22-rename', 'G22-evidence', 'G22-latch'}
        for node in ast.parse(sweep.read_text()).body:
            if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id in {'FLOWS', 'EXTRA'} for target in node.targets):
                owners.update(ast.literal_eval(node.value))
        for case, detail in unpack(json.loads(PATH.read_text())).items():
            with self.subTest(case=case):
                self.assertIn(case.split('/')[0], owners, 'An unowned gap would evade suite completeness')
                self.assertIn(detail['stage'], (2, 3))
                self.assertTrue(detail['row'])
                delta = detail['delta']
                self.assertGreater(delta['calls'], 0)
                self.assertTrue(delta['failures'])
                seen = set()
                for failure in delta['failures']:
                    self.assertTrue(failure['missing'] or failure['extra'])
                    for page in failure['pages']:
                        self.assertIn(page, range(delta['calls']))
                        self.assertNotIn(page, seen)
                        seen.add(page)

    def test_special_rename_role_cannot_supply_clean_proof(self):
        oracle = Oracle()
        source, evidence = 'mail:rename:r', {'target': 'Target', 'role': '\\All'}
        record = Record(rows={'notice:a': {'id': 'a', 'source_key': source, 'check_kind': 'rename', 'evidence_fingerprint': fingerprint(evidence)}})
        oracle.warning(source, 'rename', evidence, record)
        oracle.call('check', {}, 2)
        oracle.script[-1]['end_seq'] = 2
        oracle.server('LIST', before_seq=1, roles={'Target': ['\\All'], 'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash']})
        self.assertFalse(oracle.clean_proof(source, 'rename', 2))
