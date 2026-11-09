"""Focused coverage/lifecycle/quiet cases use the same strict gap mechanism."""
import unittest
from owner_state_oracle.gaps import Gaps
import owner_state_cases


class OwnerStateContracts(unittest.TestCase):
    def test_matrix_contracts(self):
        gaps = Gaps()
        owner_state_cases.run(gaps)
        self.assertEqual(gaps.seen, {key for key in gaps.entries if key.startswith('contract/')})
