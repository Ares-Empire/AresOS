"""Real result-write faults followed by an unauthorized draft APPEND retry."""
from contextlib import ExitStack
import copy
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
