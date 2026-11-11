"""D3: admission/open check precedes the first maintenance journal write."""
import errno
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from storage_faults import OSWrites
from test_owner_state_sweep import OwnerScenario


def crash_restart(scenario):
    root = scenario.fixture.root
    with tempfile.TemporaryDirectory(dir=root, prefix='captured-crash-') as saved:
        saved = Path(saved)
        for area in ('state', 'evidence'):
            shutil.copytree(root / area, saved / area)
        scenario.fixture.engine.close()
        for area in ('state', 'evidence'):
            shutil.rmtree(root / area)
            shutil.copytree(saved / area, root / area)
    scenario.bind(Engine(root / 'state', root / 'evidence'))


class MaintenanceAdmission(unittest.TestCase):
    def test_first_write_full_disk_regression(self):
        # STORAGE-S3-FIRST-WRITE.py's exact point-1 persistent failure. With no
        # committed gate the maintenance body and its journal must never start.
        scenario = OwnerScenario('maintenance')
        try:
            driver, fault = Driver(scenario), OSWrites(1, mode='persistent')
            work = scenario.fixture.engine._expire
            with patch.object(scenario.fixture.engine, '_expire', wraps=work) as body:
                with driver.observe(fault), fault.wrap(scenario.fixture.engine.store):
                    result = scenario.call()
                body.assert_not_called()
            self.assertTrue(fault.failed)
            self.assertNotIn('journal.write', fault.points)
            self.assertFalse(result['ok'])
            driver.reply(result, delivered=False)
            crash_restart(scenario)
            gaps = Gaps(recording=True)
            driver.compare(gaps.checker('maintenance-first-write'))
            self.assertFalse(gaps.entries, gaps.entries)
        finally:
            scenario.close()

    def test_physical_full_disk_refuses_before_any_write_then_recovers(self):
        scenario = OwnerScenario('maintenance')
        try:
            store = scenario.fixture.engine.store
            fault = OSWrites()
            with patch('aresos_control.space.shutil.disk_usage', return_value=shutil._ntuple_diskusage(1, 1, 0)):
                with fault.wrap(store), self.assertRaises(Refused) as refused:
                    scenario.fixture.engine.expire()
            self.assertEqual('storage_limit', refused.exception.code)
            self.assertFalse(fault.points)
            self.assertFalse(store.write_failed)
            scenario.fixture.engine.expire()
            self.assertFalse(scenario.fixture.engine.pending(resolve_checks=False).get('notices'))
        finally:
            scenario.close()

    def test_failing_disk_after_admission_retains_generic_warning_across_crash(self):
        scenario = OwnerScenario('maintenance')
        try:
            driver = Driver(scenario)
            work = scenario.fixture.engine._expire
            def fail_body():
                # Fail the very first journal write of the maintenance body;
                # cleanup fails as in the supplied counterexample.
                with OSWrites(1, mode='persistent').wrap(scenario.fixture.engine.store):
                    return work()
            with patch.object(scenario.fixture.engine, '_expire', side_effect=fail_body):
                result = scenario.call()
            self.assertFalse(result['ok'])
            store = scenario.fixture.engine.store
            self.assertTrue(store.get('notice:background-storage')['check_open'])
            self.assertIn('check:notice:background-storage', store.ledger.holds)
            store.deferred_notices.clear()  # RAM contributes no authority.
            crash_restart(scenario)
            if scenario.fixture.engine.store.locked:
                scenario.fixture.engine.store.confirm_restore()
            notices = scenario.fixture.engine.pending(resolve_checks=False)['notices']
            warning = next(n for n in notices if n['operation_id'] == 'background-storage')
            self.assertIn('no committed result', warning['untrusted_content']['reason'])
            self.assertNotIn('background-storage', scenario.fixture.engine.store.deferred_notices)
        finally:
            scenario.close()


if __name__ == '__main__':
    unittest.main()

class ExportResolution(unittest.TestCase):
    def test_failed_resolving_commit_warns_in_the_calls_own_reply_D4(self):
        scenario = OwnerScenario('testapp_export')
        try:
            store = scenario.fixture.engine.store
            write = store.write
            def refusing(changes, *args, **kwargs):
                if any(k.startswith('export:') and v is None for k, v in changes.items()):
                    raise Refused('storage_error', 'Synthetic failed export resolution')
                return write(changes, *args, **kwargs)
            with patch.object(store, 'write', side_effect=refusing):
                result = scenario.call()
            self.assertFalse(result['ok'])
            self.assertTrue(any(n['untrusted_content'].get('intent_key', '').startswith('export:')
                                for n in result['pending']['notices']))
        finally:
            scenario.close()

    def test_crash_before_resolving_commit_warns_in_next_view_D4(self):
        scenario = OwnerScenario('testapp_export')
        try:
            store = scenario.fixture.engine.store
            write = store.write
            class Crash(BaseException):
                pass
            def crashing(changes, *args, **kwargs):
                if any(k.startswith('export:') and v is None for k, v in changes.items()):
                    raise Crash()
                return write(changes, *args, **kwargs)
            with patch.object(store, 'write', side_effect=crashing), self.assertRaises(Crash):
                scenario.call()
            self.assertTrue(store.items('export:'))
            crash_restart(scenario)
            self.assertTrue(any(n['untrusted_content'].get('intent_key', '').startswith('export:')
                                for n in scenario.fixture.engine.pending(resolve_checks=False)['notices']))
        finally:
            scenario.close()
