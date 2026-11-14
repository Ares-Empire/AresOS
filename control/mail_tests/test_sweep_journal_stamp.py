"""The Mail sweep stamps the journal like production's cache key (final fixes).

Chrome's committed projection caches on the journal's (inode, size, mtime).
Production re-reads the journal only after it changed; one small flow keeps a
fresh stamp per stat, so the cache-miss path still runs under every fault.
"""
import unittest

from sweep_scripts import PER_STAT_JOURNAL_FLOWS
from test_review23_sweep import FLOWS, Scenario


class JournalStamp(unittest.TestCase):
    def stamps(self, flow):
        scenario = Scenario(flow)
        try:
            store = scenario.fixture.engine.store
            journal = store.evidence_dir / 'operations.jsonl'
            database = scenario.fixture.root / 'state/control.sqlite'
            before = [journal.stat().st_mtime_ns for _ in range(2)]
            databases = [database.stat().st_mtime_ns for _ in range(2)]
            store.write({'fixture:journal-stamp': {'probe': 1}}, 'fixture', 'Synthetic journal change')
            after = [journal.stat().st_mtime_ns for _ in range(2)]
        finally:
            scenario.close()
        return before, after, databases

    def test_unchanged_journal_keeps_its_stamp_and_a_change_renews_it(self):
        before, after, databases = self.stamps('status')
        self.assertEqual(before[0], before[1])
        self.assertNotEqual(after[0], before[1])
        self.assertEqual(after[0], after[1])
        # The independent Driver's decode key still changes on every stat.
        self.assertNotEqual(databases[0], databases[1])

    def test_one_swept_flow_keeps_a_cache_miss_at_every_stat(self):
        self.assertEqual(PER_STAT_JOURNAL_FLOWS, {'cancel'})
        self.assertIn('cancel', FLOWS)
        before, after, _ = self.stamps('cancel')
        self.assertNotEqual(before[0], before[1])
        self.assertNotEqual(after[0], after[1])


if __name__ == '__main__':
    unittest.main()
