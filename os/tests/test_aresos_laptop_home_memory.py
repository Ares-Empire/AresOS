"""Opt-in PSS regression check for the AresOS laptop."""

import os
import statistics
import unittest

from laptop_home_memory import measure


# Final reference runs, in KiB, from reviews/53e-home-memory/REPORT.md.
REFERENCE_MIN = 427_104
REFERENCE_MEDIAN = 428_124
REFERENCE_MAX = 429_545
LIMIT = REFERENCE_MEDIAN + max(0.15 * REFERENCE_MEDIAN, 3 * (REFERENCE_MAX - REFERENCE_MIN))


@unittest.skipUnless(os.environ.get('LAPTOP_HOME_TEST_MEMORY') == '1', 'opt in on AresOS with LAPTOP_HOME_TEST_MEMORY=1')
class LaptopHomeMemoryTest(unittest.TestCase):
    def test_software_background_layer_at_rest(self):
        totals = [measure()['total'] for _ in range(3)]
        median = statistics.median(totals)
        print(f'S background layer: PSS {totals} KiB, median {median} KiB, limit {LIMIT:.1f} KiB')
        self.assertLessEqual(median, LIMIT)
