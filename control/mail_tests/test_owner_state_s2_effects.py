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
