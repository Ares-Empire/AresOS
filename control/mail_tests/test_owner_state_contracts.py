"""Focused coverage/lifecycle/quiet cases use the same strict gap mechanism."""
import base64
import gzip
import json
import unittest
from owner_state_oracle.gaps import Gaps
import owner_state_cases


class OwnerStateContracts(unittest.TestCase):
    def test_matrix_contracts(self):
        gaps = Gaps(recording=True)
        owner_state_cases.run(gaps)
        print('OWNER-GAP-CONTRACTS:' + base64.b64encode(gzip.compress(json.dumps(gaps.entries, sort_keys=True).encode())).decode(), flush=True)
