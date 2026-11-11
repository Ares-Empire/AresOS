"""Every flow's public owner views survive a main-SQLite read failure."""
import sqlite3
import unittest
from unittest.mock import patch

from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from storage_faults import OSWrites
from test_owner_state_sweep import FLOWS, EXTRA, OwnerScenario


class ProjectionFallback(unittest.TestCase):
    def test_every_flow_with_sqlite_unreadable(self):
        for flow in FLOWS + EXTRA:
            with self.subTest(flow=flow):
                scenario = OwnerScenario(flow)
                try:
                    driver = Driver(scenario)
                    with driver.observe():
                        result = scenario.call()
                    driver.reply(result)
                    store = scenario.fixture.engine.store
                    fault = OSWrites(1, mode='persistent')
                    database = store.db
                    class FailedReads:
                        def execute(self, *args, **kwargs):
                            fault.hit('sqlite.main.read', sqlite=True)
                            error = sqlite3.OperationalError('database or disk is full')
                            error.sqlite_errorcode = sqlite3.SQLITE_FULL
                            raise error
                        def __getattr__(self, name):
                            return getattr(database, name)
                    gaps = Gaps(recording=True)
                    # These forced main-database read failures are independently
                    # logged; the projection and disposable index remain readable.
                    with fault.wrap(store), patch.object(store, 'db', FailedReads()):
                        driver.compare(gaps.checker('fallback/' + flow))
                    self.assertTrue(fault.failed)
                    self.assertFalse(gaps.entries, (flow, gaps.entries))
                finally:
                    scenario.close()


if __name__ == '__main__':
    unittest.main()
