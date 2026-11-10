"""Stage-two review regressions: independent effects and retained obligations."""
import copy
import unittest
from unittest.mock import patch

from owner_state_oracle.model import Oracle, Fact
from owner_state_oracle.records import Record
from owner_state_oracle.compare import compare_proofs
from owner_state_oracle.perturb import coherent_change, evaluate, snapshot_mutations, snapshot_fields
from owner_state_oracle.context import differences


ROLES = {'Sent': ['\\Sent'], 'Drafts': ['\\Drafts'], 'Trash': ['\\Trash'], 'Source': []}
REF = {'account': 'box', 'folder': 'Source', 'uidvalidity': 2, 'uid': 1, 'message_id': '<m@mail.invalid>'}


def filing_case(kind='rename', related=False, target=False, scan=False):
    oracle = Oracle()
    key = 'mail:' + kind + ':r'
    row = {'id': 'r', 'account': 'box', 'source': 'Source', 'sources': [REF], 'target': 'MissingTarget', 'state': 'started', 'check_open': True}
    oracle.seed_sequence = 1
    oracle.call('control_pending' if related else 'mail_accounts', {}, 2)
    oracle.script[-1].update(start_seq=1, end_seq=2)
    roles = {**ROLES, **({'MissingTarget': []} if target else {})}
    oracle.server('LIST', 'box', roles=roles, before_seq=1, check_sources=[key] if related else [], mailboxes={})
    if scan:
        oracle.server('SCAN_RESULT', 'box', before_seq=1, check_sources=[key])
    closed = {**row, 'state': 'done', 'check_open': False}
    record = Record(rows={key: closed}, events=[{'seq': 1, 'time': 1, 'action': 'fixture', 'set': {key: row}},
                    {'seq': 2, 'time': 2, 'action': 'mail_filing_check', 'set': {key: closed}}], committed={1, 2})
    oracle.seed_events = copy.deepcopy(record.events[:1])
    return oracle, record, key


def filing_followups(oracle, record, key):
    for seq, action, changes in ((3, 'mail_notice_ack', {key: {**record.rows[key], 'ack': True}}),
                                 (4, 'control_pending', {}), (5, 'mail_filing_notices', {}),
                                 (6, 'control_pending', {}), (7, 'control_archive', {key: None})):
        # The last pending read is beyond approval expiry; an open check has no
        # expiry resolution. Archive is explicitly scripted as an owner attempt.
        clock = seq if seq < 6 else 100000 + seq
        args = {'operation_id': 'r'} if action.endswith('_notice_ack') else (
            {'before': clock - 1, 'confirm': 'archive finished history'} if action == 'control_archive' else {})
        oracle.call(action, args, clock)
        oracle.script[-1].update(start_seq=seq-1, end_seq=seq)
        record.events.append({'seq': seq, 'time': clock, 'action': action, 'set': changes})
        record.committed.add(seq)
        for name, value in changes.items():
            if value is None:
                record.rows.pop(name, None)
            else:
                record.rows[name] = value
        yield action, copy.deepcopy(oracle), copy.deepcopy(record)


class StageTwoFixes(unittest.TestCase):
    def test_validator_figures_record_the_method_that_emitted_the_proof(self):
        oracle, record, _ = filing_case('rename', False, True, False)
        proofs = {}
        _, errors = evaluate(oracle, record, proofs)
        self.assertTrue(any(f.kind == 'unsupported-resolution' for _, f in errors))
        self.assertFalse(proofs.get('transition'))
        self.assertFalse(proofs.get('completion_errors'))

    def test_runtime_warning_cannot_use_missing_fingerprint_as_legacy_authority(self):
        oracle = Oracle()
        row = {'id': 'n', 'source_key': 'mail:rename:r', 'check_kind': 'rename', 'created_at': 1}
        _, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_folder_rename', 'set': {'notice:n': row}}]))
        self.assertTrue(any(f.kind == 'missing-warning-context' for _, f in errors))
        self.assertTrue(any(f.kind == 'missing-check-result' for _, f in errors))

    def test_recovery_result_keeps_the_enrolled_target_and_requires_a_result_row(self):
        oracle, record, key = filing_case('filing', True, True, True)
        record.events[-1]['set'][key] = {**record.rows[key], 'target': 'Changed'}
        record.rows[key] = record.events[-1]['set'][key]
        _, errors = evaluate(oracle, record)
        self.assertTrue(any(f.kind == 'changed-filing-context' for _, f in errors))
        record.events[-1]['set'][key] = {**record.events[0]['set'][key]}
        record.rows[key] = record.events[-1]['set'][key]
        _, errors = evaluate(oracle, record)
        self.assertTrue(any(f.kind == 'uncommitted-check-result' for _, f in errors))
        record.events[-1]['set'] = {}
        record.rows[key] = record.events[0]['set'][key]
        _, errors = evaluate(oracle, record)
        self.assertIn(('lifecycle-proof', Fact('filing-check', 'missing-check-result', detail='2')), errors)

    def test_missing_operation_identity_is_reported_before_interpreting_its_payload(self):
        oracle = Oracle()
        row = {'app': 'mail', 'action': 'mail_send', 'state': 'unknown',
               'payload': {'composition': {'mail': {'account': 'box'}}}}
        _, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_send', 'set': {'op:g:p': row}}]))
        self.assertTrue(any(f.kind == 'operation-identity' for _, f in errors))

    def test_cancellation_commit_cannot_omit_its_operation_result(self):
        oracle = Oracle()
        key = 'op:g:p'
        reserved = {'id': 'g:p', 'app': 'testapp', 'action': 'testapp_send', 'state': 'reserved',
                    'expires': 10, 'reason': 'Awaiting exact approval; nothing submitted.'}
        oracle.seed_sequence = 1
        oracle.call('testapp_operation_cancel', {'operation_id': 'g:p'}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        record = Record(rows={key: reserved}, events=[
            {'seq': 1, 'time': 1, 'action': 'fixture', 'set': {key: reserved}},
            {'seq': 2, 'time': 2, 'action': 'testapp_operation_cancel', 'operation_id': 'g:p',
             'summary': 'cancelled before submission', 'set': {}}])
        _, errors = evaluate(oracle, record)
        self.assertIn(('lifecycle-proof', Fact(key, 'missing-operation-result', detail='2')), errors)
        cancelled = {**reserved, 'state': 'failed', 'reason': 'cancelled: nothing submitted', 'notice': True}
        record.events[-1]['set'][key] = cancelled
        record.rows[key] = cancelled
        _, errors = evaluate(oracle, record)
        self.assertNotIn(('lifecycle-proof', Fact(key, 'missing-operation-result', detail='2')), errors)

    def test_first_filing_row_cannot_claim_a_result_before_its_check(self):
        oracle = Oracle()
        oracle.call('mail_move', {'references': [REF], 'target': 'Target'}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        row = {'id': 'f', 'account': 'box', 'verb': 'move', 'sources': [REF], 'target': 'Target', 'state': 'done'}
        expected, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_move', 'set': {'mail:filing:f': row}}]))
        self.assertTrue(any(f.kind == 'unsupported-resolution' for _, f in errors))
        self.assertIn(Fact('mail:filing:f', 'recovery'), expected)

    def test_an_earlier_sent_search_cannot_authorize_deleting_check_enrollment(self):
        oracle = Oracle()
        key = 'op:g:p'
        row = {'id': 'g:p', 'app': 'mail', 'action': 'mail_send', 'state': 'submitting',
               'reason': 'Durably submitting; do not cancel or retry.', 'sent_copy_check': {'state': 'open'}}
        oracle.seed_sequence = 1
        oracle.call('mail_operation_status', {'operation_id': 'g:p'}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        oracle.server('SENT', 'box', source=key, before_seq=1)
        changed = {k: v for k, v in row.items() if k != 'sent_copy_check'}
        record = Record(rows={key: changed}, events=[
            {'seq': 1, 'time': 1, 'action': 'fixture', 'set': {key: row}},
            {'seq': 2, 'time': 2, 'action': 'mail_send', 'set': {key: changed}}])
        for claim in ({}, {'sent_copy_check': {'state': 'checked'}}):
            with self.subTest(claim=claim):
                record.events[-1]['set'][key] = {**changed, **claim}
                record.rows[key] = record.events[-1]['set'][key]
                expected, errors = evaluate(oracle, record)
                self.assertIn(Fact(key, 'unchecked'), expected)
                self.assertTrue(any(f.kind == 'unjustified-check-close' for _, f in errors))

    def test_coherent_version_updates_copies_and_preserves_later_outcomes(self):
        oracle = Oracle()
        key = 'op:g:p'
        started = {'id': 'g:p', 'state': 'submitting', 'context': {'command': 'DATA'}}
        done = {**started, 'state': 'done'}
        record = Record(rows={key: done}, committed={1, 2}, events=[
            {'seq': 1, 'time': 1, 'action': 'mail_send', 'set': {key: started}},
            {'seq': 2, 'time': 2, 'action': 'mail_send', 'set': {key: done}}])
        for seq, row in ((1, started), (2, done)):
            oracle.server('DATA', before_seq=seq, committed_before={key: row}, created_before={key: 1})
        original_inputs = copy.deepcopy((oracle.script, oracle.servers, oracle.commit_observations, record))
        replay, changed = coherent_change(oracle, record, key, ('state',), 'state', 'unknown', 1)
        self.assertEqual(changed.events[0]['set'][key]['state'], 'unknown')
        self.assertEqual(changed.rows[key]['state'], 'done')
        self.assertEqual(replay.servers[0]['committed_before'][key]['state'], 'unknown')
        self.assertEqual(replay.servers[1]['committed_before'][key]['state'], 'done')
        replay, changed = coherent_change(oracle, record, key, kind='row', since=1)
        self.assertNotIn(key, changed.events[0]['set'])
        self.assertIn(key, changed.events[1]['set'])
        self.assertNotIn(key, replay.servers[0]['committed_before'])
        self.assertEqual(replay.servers[1]['created_before'][key], 2)
        replay, changed = coherent_change(oracle, record, key, ('context', 'command'), 'effect', 'APPEND', 1)
        self.assertEqual(changed.events[0]['set'][key]['context']['command'], 'APPEND')
        self.assertEqual(changed.events[1]['set'][key]['context']['command'], 'APPEND')
        self.assertEqual((oracle.script, oracle.servers, oracle.commit_observations, record), original_inputs)
        before = copy.deepcopy((replay.script, replay.servers, replay.commit_observations, changed))
        evaluate(replay, changed)
        self.assertEqual((replay.script, replay.servers, replay.commit_observations, changed), before)
    def test_missing_account_result_keeps_independent_setup_obligation(self):
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new'}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=3)
        oracle.server('CREATE', 'new', arguments=['AresOS-probe-x'], before_seq=1)
        record = Record(events=[{'seq': 3, 'time': 1, 'action': 'mail_account_add', 'summary': 'onboarding complete; Sent policy observed', 'outcome': 'done', 'set': {}}])
        expected, errors = evaluate(oracle, record)
        self.assertIn(Fact('mail:account:new', 'recovery'), expected)
        self.assertTrue(any(f.kind == 'qualification' for f in expected))
        self.assertTrue(any(f.kind == 'missing-account-result' for _, f in errors))

    def test_malformed_deadline_and_probe_reference_reach_semantic_comparison(self):
        oracle = Oracle()
        oracle.call('mail_prepare_send', {}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        row = {'id': 'g:p', 'app': 'mail', 'action': 'mail_send', 'state': 'reserved', 'expires': 'wrong',
               'reason': 'Awaiting exact approval; nothing submitted.'}
        expected, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_send', 'set': {'op:g:p': row}}]))
        self.assertTrue(expected)
        self.assertTrue(any(f.kind == 'unapproved-expiry' for _, f in errors))
        self.assertFalse(any(f.kind == 'invalid-record' for _, f in errors))
        oracle.script[-1]['clock_samples'] = [1.0]
        oracle.script[-1]['operation_ttl'] = 900
        row['expires'] = 1000901.0
        _, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_send', 'set': {'op:g:p': row}}]))
        self.assertTrue(any(f.kind == 'unapproved-expiry' for _, f in errors))
        oracle = Oracle()
        oracle.call('mail_account_add', {'id': 'new'}, 1)
        oracle.script[-1].update(start_seq=0, end_seq=1)
        row = {'id': 'g:p', 'app': 'mail', 'action': 'mail_delete', 'state': 'submitting', 'payload': {'items': [{}], 'mode': 'permanent'}}
        oracle.server('EXPUNGE', 'new', 'Probe', [REF], ROLES, arguments=['1'], before_seq=1, call_start_seq=0,
                      created_before={'op:g:p': 1}, committed_before={'op:g:p': row})
        _, errors = evaluate(oracle, Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_delete', 'set': {'op:g:p': row}}]))
        self.assertTrue(any(f.kind == 'unapproved-payload' for _, f in errors))
        self.assertTrue(any(f.kind == 'R2.EXPUNGE' for _, f in errors))
        self.assertFalse(any(f.kind == 'invalid-record' for _, f in errors))

    def test_deadline_authority_records_consumed_test_clock_samples(self):
        import time
        from owner_state_oracle.clock import recorded_samples
        oracle = Oracle()
        oracle.call('mail_prepare_send', {}, 0)
        with patch.object(time, 'time', side_effect=[1.0, 1.0, 2.0]):
            with recorded_samples(oracle, 0):
                self.assertEqual([time.time() for _ in range(3)], [1.0, 1.0, 2.0])
        self.assertEqual(oracle.script[0]['clock_samples'], [1.0, 2.0])
        self.assertEqual(oracle.script[0]['operation_ttl'], 900)

    def test_existing_fixture_error_cannot_make_a_changed_copy_authoritative(self):
        oracle = Oracle()
        oracle.seed_sequence = 1
        row = {'id': 'g:r', 'app': 'mail', 'action': 'mail_send', 'state': 'reserved',
               'reason': 'Awaiting exact approval; nothing submitted.'}
        oracle.call('fixture_input', {'changes': {'op:g:r': row}}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        record = Record(rows={'op:g:r': row}, events=[{'seq': 2, 'time': 2, 'action': 'fixture',
                        'set': {'op:g:r': row, 'extra': 'preexisting consistency difference'}}])
        expected, errors = evaluate(oracle, record)
        self.assertTrue(any(f.kind == 'changed-fixture-input' for _, f in errors))
        changed = copy.deepcopy(record)
        changed.events[0]['set']['op:g:r'].pop('reason')
        changed.rows['op:g:r'].pop('reason', None)
        actual, _ = evaluate(oracle, changed)
        self.assertEqual(actual, expected)
        self.assertTrue(any(f.kind == 'pending' and 'Awaiting exact approval' in f.detail for f in actual))

    def test_deleted_reason_cannot_replace_the_canonical_submitting_reason(self):
        oracle = Oracle()
        oracle.seed_sequence = 1
        oracle.call('mail_send', {'operation_id': 'g:s', 'description': {}}, 2)
        oracle.script[-1].update(start_seq=1, end_seq=2)
        row = {'id': 'g:s', 'app': 'mail', 'action': 'mail_send', 'state': 'reserved',
               'reason': 'Awaiting exact approval; nothing submitted.'}
        submitted = {k: v for k, v in {**row, 'state': 'submitting'}.items() if k != 'reason'}
        record = Record(rows={'op:g:s': submitted}, events=[
            {'seq': 1, 'time': 1, 'action': 'fixture', 'set': {'op:g:s': row}},
            {'seq': 2, 'time': 2, 'action': 'mail_send', 'set': {'op:g:s': submitted}}])
        expected, errors = evaluate(oracle, record)
        self.assertTrue(any(f.kind == 'unjustified-operation-reason' for _, f in errors))
        self.assertTrue(any(f.kind == 'pending' and 'Durably submitting' in f.detail for f in expected))

    def test_local_flag_requires_prior_context_and_accepts_atomic_completion(self):
        reference = {'scope': 'testapp/fixture/items', 'epoch': 'e', 'id': '1', 'revision': 4}
        item = {'id': '1', 'revision': 4, 'flagged': False}
        data = {'epoch': 'e', 'items': {'1': item}}
        args = {'reference': reference, 'flagged': True}
        for prior in (False, True):
            oracle = Oracle()
            oracle.seed_sequence = 1
            oracle.call('testapp_flag', args, 2)
            oracle.script[-1].update(start_seq=1, end_seq=3)
            context = {'command': 'LOCAL_FLAG', 'account': 'fixture', 'arguments': args, 'identities': [reference],
                       'source': 'fixture/items', 'destination': 'fixture/items', 'roles': {}, 'recipients': []}
            intent = {'id': 'recovery-i', 'app': 'testapp', 'action': 'testapp_flag', 'state': 'started', 'context': context, 'context_version': 1}
            effect = {'epoch': 'e', 'items': {'1': {**item, 'revision': 5, 'flagged': True}}}
            record = Record(rows={'testapp': effect}, committed={1, 2, 3}, events=[
                {'seq': 1, 'time': 1, 'action': 'fixture', 'set': {'testapp': data}},
                {'seq': 2, 'time': 2, 'action': 'testapp_flag', 'set': {'intent:i': intent} if prior else {}},
                {'seq': 3, 'time': 2, 'action': 'testapp_flag', 'set': {'testapp': effect, 'intent:i': None}}])
            expected, errors = evaluate(oracle, record)
            self.assertEqual(any(f.kind == 'R2.LOCAL_FLAG' for _, f in errors), not prior)
            if prior:
                self.assertFalse(errors)
                self.assertFalse(any(f.kind == 'recovery' for f in expected))

    def test_duplicate_draft_append_fails_even_without_completion_or_after_a_fault(self):
        for fault in (False, True):
            for complete in (False, True):
                for second_call in (False, True):
                    oracle = Oracle()
                    row = {'id': 'recovery-i', 'action': 'mail_draft_save', 'app': 'mail', 'state': 'started', 'context_version': 1,
                           'context': {'command': 'APPEND', 'account': 'box', 'source': 'local', 'destination': 'Drafts',
                                       'identities': [{'message_id': '<draft@mail.invalid>'}], 'sha256': 'wire', 'append_flags': '(\\Draft)',
                                       'roles': {'sent': ['Sent'], 'drafts': ['Drafts'], 'trash': ['Trash']}, 'recipients': []}}
                    oracle.call('mail_draft_save', {'composition_id': 'c', 'composition_hash': 'h'}, 1,
                                {'trace': [(2, 'journal.write', 'ENOSPC')]} if fault else {})
                    oracle.script[-1].update(start_seq=0, end_seq=2)
                    for index in range(2):
                        if second_call and index:
                            oracle.call('mail_draft_save', {'composition_id': 'c', 'composition_hash': 'h'}, 2)
                            oracle.script[-1].update(start_seq=2, end_seq=4)
                        key = 'intent:j' if second_call and index else 'intent:i'
                        current = {**row, 'id': 'recovery-j'} if key == 'intent:j' else row
                        oracle.server('APPEND', 'box', 'Drafts', [{'message_id': '<draft@mail.invalid>'}], ROLES,
                            append_flags='(\\Draft)', raw_sha256='wire', before_seq=1 if not second_call or not index else 3,
                            call_start_seq=0 if key == 'intent:i' else 2, created_before={key: 1 if key == 'intent:i' else 3}, committed_before={key: current})
                    events = [{'seq': 1, 'time': 1, 'action': 'mail_draft_save', 'set': {'intent:i': row}}]
                    if complete:
                        events.append({'seq': 2, 'time': 1, 'action': 'mail_draft_save', 'set': {'intent:i': None}})
                    _, errors = evaluate(oracle, Record(rows={} if complete else {'intent:i': row}, events=events))
                    self.assertEqual(any(f.kind == 'duplicate-effect' for _, f in errors), not second_call)

    def test_only_the_exact_complete_check_can_close_filing_or_rename(self):
        for kind in ('rename', 'filing'):
            for related, target, scan in ((False, True, True), (True, False, True), (True, True, False), (True, True, True)):
                with self.subTest(kind=kind, related=related, target=target, scan=scan):
                    oracle, record, key = filing_case(kind, related, target, scan)
                    expected, failures = evaluate(oracle, record)
                    valid = related and target and (scan or kind == 'rename')
                    self.assertEqual(any(f.kind == 'unjustified-check-close' for _, f in failures), not valid)
                    self.assertEqual(any(f.source == key and f.kind == 'recovery' for f in expected), not valid)

    def test_wrong_close_survives_ack_reads_expiry_archive_and_restart(self):
        for kind in ('rename', 'filing'):
            oracle, record, key = filing_case(kind, False, False, False)
            for action, replay, snapshot in filing_followups(oracle, record, key):
                expected, failures = evaluate(replay, snapshot)
                self.assertTrue(any(f.source == key and f.kind == 'recovery' for f in expected), action)
            restarted = copy.deepcopy(oracle)
            self.assertTrue(any(f.source == key and f.kind == 'recovery' for f in evaluate(restarted, record)[0]))

    def flag_case(self, fault):
        oracle = Oracle()
        oracle.call('mail_flag', {'references': [REF], 'add': ['\\Seen'], 'remove': ['\\Flagged']}, 1,
                    {'trace': [(3, 'journal.write', 'ENOSPC')]} if fault else {})
        oracle.script[-1].update(start_seq=0, end_seq=2, reply='delivered')
        context = {'command': 'STORE', 'account': 'box', 'source': 'Source', 'destination': None,
                   'identities': [REF], 'flags': ['+FLAGS.SILENT', '(\\Seen)'],
                   'roles': {'sent': ['Sent'], 'drafts': ['Drafts'], 'trash': ['Trash']}, 'recipients': []}
        row = {'id': 'recovery-i', 'app': 'mail', 'action': 'mail_flag', 'state': 'started', 'context': context, 'context_version': 1}
        oracle.server('STORE', 'box', 'Source', [REF], ROLES, arguments=['1', '+FLAGS.SILENT', '(\\Seen)'],
                      before_seq=1, call_start_seq=0, created_before={'intent:i': 1}, committed_before={'intent:i': row})
        record = Record(events=[{'seq': 1, 'time': 1, 'action': 'mail_flag', 'set': {'intent:i': row}},
                                {'seq': 2, 'time': 1, 'action': 'mail_flag', 'set': {'intent:i': None}}], committed={1, 2})
        return oracle, record

    def test_omitted_flag_branch_retains_recovery_with_and_without_a_fault(self):
        for fault in (False, True):
            oracle, record = self.flag_case(fault)
            expected, errors = evaluate(oracle, record)
            self.assertTrue(any(f.kind == 'unjustified-removal' for _, f in errors))
            self.assertTrue(any(f.source == 'intent:i' and f.kind == 'recovery' for f in expected))

    def test_receive_checks_actual_wrong_or_extra_recipient_before_completion(self):
        for actual in (['wrong'], ['allowed', 'extra']):
            oracle = Oracle()
            oracle.call('testapp_send', {'operation_id': 'g:s', 'description': {'to': ['allowed'], 'cc': [], 'bcc': []}}, 1)
            context = {'command': 'RECEIVE', 'account': 'fixture', 'source': 'fixture', 'destination': 'receiver',
                       'identities': [{'operation_id': 'g:s'}], 'recipients': ['allowed']}
            row = {'id': 'g:s', 'state': 'submitting', 'context_version': 1, 'context': context}
            event = oracle.server('RECEIVE', 'fixture', identities=[{'operation_id': 'g:s'}], recipients=actual,
                                  before_seq=1, committed_before={'op:g:s': row})
            self.assertIn('recipients', differences(event, oracle.script)[1])
            self.assertIn('script.command.recipients', differences(event, oracle.script)[1])

    def test_version_one_missing_context_cannot_use_legacy_fields(self):
        oracle = Oracle()
        oracle.call('mail_delete', {'operation_id': 'g:d', 'description': {'items': [{'reference': REF}], 'mode': 'permanent'}}, 1)
        row = {'id': 'g:d', 'state': 'submitting', 'payload': {'items': [{'reference': REF}], 'mode': 'permanent'}, 'context_version': 1}
        event = oracle.server('STORE', 'box', 'Source', [REF], ROLES, arguments=['1', '+FLAGS.SILENT', '(\\Deleted)'], committed_before={'op:g:d': row})
        self.assertTrue(differences(event, oracle.script)[1])
        row.pop('context_version')
        row['roles_before'] = ROLES
        event['committed_before']['op:g:d'] = row
        self.assertTrue(differences(event, oracle.script)[1])
        self.assertEqual(differences(event, oracle.script, legacy_keys={'op:g:d'})[1], [])

    def test_runtime_fixture_label_does_not_authorize_a_reason_or_transition(self):
        oracle = Oracle()
        oracle.seed_sequence = 1
        oracle.call('mail_send', {'operation_id': 'g:s', 'description': {}}, 2, {'trace': [(1, 'journal.write', 'ENOSPC')]})
        oracle.script[-1].update(start_seq=1, end_seq=2)
        before = {'id': 'g:s', 'app': 'mail', 'action': 'mail_send', 'state': 'submitting'}
        after = {**before, 'state': 'unknown', 'reason': 'All good: nothing to check.'}
        record = Record(events=[{'seq': 1, 'time': 1, 'action': 'fixture', 'set': {'op:g:s': before}},
                                {'seq': 2, 'time': 2, 'action': 'fixture', 'set': {'op:g:s': after}}])
        expected, errors = evaluate(oracle, record)
        self.assertTrue(any(f.kind == 'unscripted-fixture-event' for _, f in errors))
        self.assertTrue(any(f.kind == 'unjustified-operation-reason' for _, f in errors))
        self.assertFalse(any('All good' in f.detail for f in expected))

    def test_snapshot_field_audit_and_coherent_nested_deletion(self):
        oracle, record = self.flag_case(False)
        oracle.commit_observations[1] = copy.deepcopy(oracle.servers[0]['committed_before'])
        candidates = list(snapshot_mutations(oracle, record, ('done', 'started')))
        self.assertLessEqual(set(snapshot_fields(oracle)), {field for field, _, _ in candidates})
        replay, changed = coherent_change(oracle, record, 'intent:i', ('context',), 'key-deletion', since=1)
        self.assertNotIn('context', changed.events[0]['set']['intent:i'])
        self.assertNotIn('context', replay.servers[0]['committed_before']['intent:i'])
        self.assertNotIn('context', replay.commit_observations[1]['intent:i'])
