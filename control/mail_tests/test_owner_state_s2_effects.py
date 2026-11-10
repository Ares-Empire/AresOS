"""Real result-write faults followed by an unauthorized draft APPEND retry."""
from contextlib import ExitStack
import copy
import hashlib
import unittest
from unittest.mock import patch

from aresos_control.engine import Engine
from aresos_control.mail.adapter import Mail, mutation
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from owner_state_oracle.perturb import evaluate, freeze
from test_owner_state_sweep import OwnerScenario
from storage_faults import OSWrites


class EffectRegressions(unittest.TestCase):
    def filing_scan(self, body='valid', absent_target=False, lie=False, omit_warning=False, arrival=False):
        scenario = OwnerScenario('fixture')
        try:
            fixture = scenario.fixture
            scenario.action, scenario.args = 'control_pending', {}
            driver = Driver(scenario)
            reference = {'account': 'box', 'folder': 'Source', 'uidvalidity': fixture.imap.validities['Source'],
                         'uid': 1, 'message_id': fixture.imap.mid}
            row = {'id': 'scan', 'account': 'box', 'verb': 'move', 'sources': [reference],
                   'target': 'Gone' if absent_target else 'Target', 'state': 'started', 'check_open': True,
                   'roles_before': fixture.account['special'],
                   'records': [{'source': reference, 'sha256': hashlib.sha256(fixture.imap.boxes['Source'][1]).hexdigest(),
                                'destination': None}]}
            key = 'mail:filing:scan'
            driver.fixture_input({key: row}, 'Synthetic interrupted filing')
            uid, write = fixture.imap.uid, fixture.engine.store.write
            select = fixture.imap.select
            arrived = []
            if arrival:
                fixture.imap.boxes['Source'] = {1: fixture.imap.boxes['Source'][1]}
            def selected(folder, *args, **kwargs):
                if arrival and folder.strip('"') == 'Source' and not arrived:
                    arrived.append(True)
                    fixture.imap.boxes['Source'][2] = b'Message-ID: <arrival@mail.invalid>\r\n\r\nUnrelated arriving mail'
                return select(folder, *args, **kwargs)
            def fetched(command, *args):
                answer = uid(command, *args)
                if command == 'FETCH' and 'BODY.PEEK[]' in str(args) and body != 'valid':
                    if body == 'empty':
                        return 'OK', []
                    if body == 'wrong-uid':
                        return 'OK', [(b'1 (UID 999 FLAGS () BODY[] {1}', b'x'), b')']
                    return 'OK', [b'1 (UID 1 FLAGS ())']
                return answer
            def persisted(changes, action, *args, **kwargs):
                if lie and action == 'mail_filing_check' and key in changes:
                    changes[key].update(state='done', check_open=False)
                if omit_warning and action == 'mail_filing_check':
                    for name in list(changes):
                        if name.startswith('notice:'):
                            del changes[name]
                return write(changes, action, *args, **kwargs)
            with patch.object(fixture.imap, 'select', side_effect=selected), patch.object(fixture.imap, 'uid', side_effect=fetched), patch.object(fixture.engine.store, 'write', side_effect=persisted), driver.observe():
                result = scenario.call()
            driver.reply(result)
            scans = [event for event in driver.oracle.servers if event['command'] == 'SCAN_RESULT']
            self.assertTrue(scans)
            if arrival:
                self.assertTrue(arrived)
                listing = next(e for e in driver.oracle.servers if e['command'] == 'LIST' and e.get('check_sources'))
                search = next(e for e in driver.oracle.servers if e['command'] == 'SEARCH' and e.get('folder') == 'Source' and e.get('arguments') == [None, 'ALL'])
                self.assertEqual([r['uid'] for r in listing['mailboxes']['Source']], [1])
                self.assertEqual([r['uid'] for r in search['identities']], [1, 2])
            self.assertEqual(scans[-1]['accepted'], body == 'valid')
            # Revalidate the actual recorded replies even if the summary lies.
            for event in scans:
                event['accepted'] = True
            registry = Gaps(recording=True)
            driver.compare(registry.checker('scan'))
            expected, errors = evaluate(freeze(driver.oracle), copy.deepcopy(driver.snapshot()))
            return expected, errors, driver.snapshot().rows[key]
        finally:
            scenario.close()

    def test_onboarding_effect_join_requires_its_call_identity_and_smtp_transaction(self):
        from owner_state_plants import record
        from owner_state_oracle.perturb import clone
        oracle, decoded, deltas = record('onboarding')
        self.assertFalse(deltas)
        oracle.lifecycle(decoded)
        data = next(e for e in oracle.servers if e['command'] == 'DATA')
        key = oracle.bound(data)[0]
        rcpt = next(e for e in oracle.servers if e['command'] == 'RCPT')
        self.assertIn(rcpt, oracle.operation_events(key, float('inf')))
        for field, replacement in (('call', -1), ('account', 'other'), ('smtp_transaction', -1)):
            altered = clone(oracle)
            next(e for e in altered.servers if e['command'] == 'RCPT')[field] = replacement
            _, errors = evaluate(altered, decoded)
            self.assertTrue(any(f.kind == 'unjustified-stage' and f.detail.startswith(('rcpt:', 'recipient:')) for _, f in errors), field)
        for field, replacement in (('call', -1), ('identities', [{'message_id': '<other@mail.invalid>'}])):
            altered = clone(oracle)
            next(e for e in altered.servers if e['command'] == 'APPEND' and e.get('append_flags') == '(\\Seen)')[field] = replacement
            _, errors = evaluate(altered, decoded)
            self.assertTrue(any(f.kind in {'false-completion', 'unjustified-stage'} for _, f in errors), field)

    def test_ok_fetch_without_a_matching_body_cannot_close_a_filing_check(self):
        for body in ('empty', 'wrong-uid', 'no-literal'):
            with self.subTest(body=body):
                expected, errors, _ = self.filing_scan(body=body, lie=True)
                self.assertTrue(any(f.kind == 'unjustified-check-close' for _, f in errors))
                self.assertTrue(any(f.source == 'mail:filing:scan' and f.kind == 'recovery' for f in expected))

    def test_complete_filing_scan_can_commit_a_warning_when_destination_disappeared(self):
        expected, errors, row = self.filing_scan(absent_target=True)
        self.assertEqual(row['state'], 'partial')
        self.assertFalse(row.get('check_open'))
        self.assertTrue(row['warning_checks']['filing']['warning'])
        self.assertTrue(all(item['scan_complete'] for item in row['locations']))
        self.assertFalse(any(f.kind in {'unjustified-check-close', 'unsupported-resolution'} for _, f in errors), errors)
        self.assertFalse(any(f.source == 'mail:filing:scan' and f.kind == 'recovery' for f in expected), expected)

    def test_unrelated_mail_arriving_after_list_has_complete_search_and_body_evidence(self):
        expected, errors, row = self.filing_scan(arrival=True)
        self.assertEqual(row['state'], 'partial')
        self.assertFalse(row.get('check_open'))
        self.assertTrue(row['warning_checks']['filing']['warning'])
        self.assertTrue(all(item['scan_complete'] for item in row['locations']))
        self.assertFalse(any(f.kind in {'unjustified-check-close', 'unsupported-resolution'} for _, f in errors), errors)
        self.assertFalse(any(f.source == 'mail:filing:scan' and f.kind == 'recovery' for f in expected), expected)

    def test_absent_filing_destination_requires_the_warning_to_be_committed(self):
        expected, errors, _ = self.filing_scan(absent_target=True, omit_warning=True)
        self.assertTrue(any(f.kind == 'unjustified-check-close' for _, f in errors))
        self.assertTrue(any(f.source == 'mail:filing:scan' and f.kind == 'recovery' for f in expected))

    def test_relative_rename_uses_the_independently_listed_parent_delimiter(self):
        scenario = OwnerScenario('fixture')
        try:
            fixture = scenario.fixture
            for values in (fixture.imap.boxes, fixture.imap.roles, fixture.imap.validities):
                values['Parent/Source'] = values.pop('Source')
            scenario.action, scenario.args = 'mail_folder_rename', {'account': 'box', 'folder': 'Parent/Source', 'name': 'Changed'}
            def rename(source, target):
                source, target = source.strip('"'), target.strip('"')
                for values in (fixture.imap.boxes, fixture.imap.roles, fixture.imap.validities):
                    values[target] = values.pop(source)
                return 'OK', [b'Renamed']
            driver = Driver(scenario)
            with patch.object(fixture.imap, 'rename', side_effect=rename, create=True), driver.observe():
                result = scenario.call()
            driver.reply(result)
            self.assertTrue(result['ok'], result)
            self.assertEqual(result['data']['folder'], 'Parent/Changed')
            self.assertEqual(result['data']['state'], 'done')
            registry = Gaps(recording=True)
            driver.compare(registry.checker('relative-rename'))
            self.assertFalse(registry.entries)
            self.assertFalse(driver.oracle.lifecycle_errors)
        finally:
            scenario.close()

    def test_sent_copy_with_approved_bcc_header_matches_the_data_wire(self):
        scenario = OwnerScenario('fixture')
        try:
            fixture = scenario.fixture
            scenario.flow, scenario.action = 'send', 'mail_send'
            scenario.args = fixture.approval('send', fixture.compose(to=['recipient@mail.invalid'], bcc=['hidden@mail.invalid']))
            scenario.operation_id = scenario.args['operation_id']
            driver = Driver(scenario)
            with driver.observe():
                result = scenario.call()
            driver.reply(result)
            self.assertTrue(result['ok'], result)
            self.assertEqual(result['data']['operation']['state'], 'done')
            data = next(e for e in driver.oracle.servers if e['command'] == 'DATA')
            append = next(e for e in driver.oracle.servers if e['command'] == 'APPEND')
            self.assertNotEqual(data['raw_hex'], append['raw_hex'])
            self.assertFalse(driver.oracle.context_errors())
            self.assertFalse(driver.oracle.completion_errors(driver.snapshot()))
        finally:
            scenario.close()

    def test_clean_send_is_quiet_and_a_separate_delayed_copy_race_warns(self):
        for flow, copies in (('send', 1), ('send_duplicate', 2)):
            scenario = OwnerScenario(flow)
            try:
                driver = Driver(scenario)
                with driver.observe():
                    result = scenario.call()
                driver.reply(result)
                self.assertTrue(result['ok'], result)
                self.assertEqual(len(scenario.fixture.imap.boxes['Sent']), copies)
                warnings = [fact for fact in driver.oracle.expected(driver.snapshot()) if fact.kind == 'sent_copies']
                self.assertEqual(bool(warnings), copies == 2)
                self.assertEqual(bool(result['pending'].get('notices')), copies == 2)
            finally:
                scenario.close()

    def test_uid_expunge_requires_the_exact_deleted_flag_and_preserves_unnamed_mail(self):
        scenario = OwnerScenario('delete_permanent')
        try:
            imap = scenario.fixture.imap
            imap.select('Source')
            self.assertEqual(imap.uid('EXPUNGE', '1')[0], 'OK')
            self.assertIn(1, imap.boxes['Source'])
            imap.uid('STORE', '1', '+FLAGS.SILENT', '(\\Deleted)')
            imap.uid('EXPUNGE', '1')
            self.assertNotIn(1, imap.boxes['Source'])
            self.assertIn(7, imap.boxes['Source'])
        finally:
            scenario.close()

    def attempt(self, mode='single', cleanup=None, restart=False):
        scenario = OwnerScenario('draft_append')
        try:
            driver = Driver(scenario)
            fault = OSWrites(1, mode=mode, cleanup_at=cleanup)
            retried = []
            def retry(mail, account, folder, raw, flags=None, recipients=()):
                value = mail.append_context(account, folder, raw, flags, recipients)
                with mutation(mail.store, value):
                    first = mail.append(account, folder, raw, flags)
                    with fault.wrap(mail.store):
                        try:
                            mail.store.write({}, 'mail_draft_save', 'Mail change completed', outcome='done')
                        except Exception:
                            # Deliberately broken production retries with the
                            # very same committed intent after losing its result.
                            retried.append(True)
                            mail.append(account, folder, raw, flags)
                    return first
            with patch.object(Mail, 'append_with_context', retry), driver.observe(fault):
                result = scenario.call()
            driver.reply(result)
            self.assertTrue(fault.failed)
            self.assertTrue(retried)
            if restart:
                scenario.fixture.engine.close()
                scenario.bind(Engine(scenario.fixture.root / 'state', scenario.fixture.root / 'evidence'))
            registry = Gaps(recording=True)
            if mode == 'persistent':
                exhaustion = OSWrites(1, mode='persistent')
                with exhaustion.wrap(scenario.fixture.engine.store):
                    driver.compare(registry.checker('duplicate/exhausted'))
            driver.compare(registry.checker('duplicate/restored'))
            _, errors = evaluate(freeze(driver.oracle), copy.deepcopy(driver.snapshot()))
            self.assertTrue(any(f.kind == 'duplicate-effect' for _, f in errors))
            self.assertTrue(registry.entries)
            return fault.cleanup_points
        finally:
            scenario.close()

    def test_retry_after_lost_result_in_persistent_cleanup_restart_and_restored_space(self):
        cleanup_points = self.attempt()
        self.assertTrue(cleanup_points, 'The cleanup pair must be a real reached boundary')
        for restart in (False, True):
            self.attempt('persistent', restart=restart)
            self.attempt(cleanup=cleanup_points[0][0], restart=restart)

    def test_separately_scripted_draft_saves_have_distinct_intents(self):
        scenario = OwnerScenario('draft_append')
        try:
            driver = Driver(scenario)
            for _ in range(2):
                with driver.observe():
                    result = scenario.call()
                driver.reply(result)
                self.assertTrue(result['ok'], result)
            events = [e for e in driver.oracle.servers if e['command'] == 'APPEND']
            from owner_state_oracle.context import bind
            self.assertEqual(len(events), 2)
            self.assertNotEqual(*(bind(e, driver.oracle.script)[0] for e in events))
            self.assertFalse(any(f.kind == 'duplicate-effect' for f in driver.oracle.completion_errors(driver.snapshot())))
            self.assertFalse(driver.oracle.context_errors())
        finally:
            scenario.close()
