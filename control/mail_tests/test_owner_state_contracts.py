"""Focused coverage/lifecycle/quiet cases use the same strict gap mechanism."""
import unittest
from owner_state_oracle.gaps import Gaps
import owner_state_cases


class OwnerStateContracts(unittest.TestCase):
    def test_matrix_contracts(self):
        gaps = Gaps()
        owner_state_cases.run(gaps)
        gaps.verify({'contract'})

    def test_every_fault_free_flow_has_only_named_production_gaps(self):
        import hashlib
        import json
        from pathlib import Path
        from test_owner_state_sweep import FLOWS, EXTRA, exercise
        from owner_state_oracle.records import canonical
        allowed = json.loads(Path(__file__).with_name('owner_state_quiet_gaps.json').read_text())
        self.assertLessEqual(set(allowed), set(FLOWS + EXTRA))
        for flow in FLOWS + EXTRA:
            with self.subTest(flow=flow):
                gaps = Gaps(recording=True)
                exercise(flow, gaps=gaps)
                entry = allowed.get(flow)
                if entry is None:
                    self.assertFalse(gaps.entries, (flow, gaps.entries))
                else:
                    self.assertEqual(entry['stage'], 3)
                    self.assertTrue(entry['production_behavior'])
                    self.assertEqual(sorted(k.split('/live-restored/')[1] for k in gaps.entries), entry['views'])
                    self.assertEqual(len(gaps.entries), entry['count'])
                    self.assertEqual(hashlib.sha256(canonical(gaps.entries).encode()).hexdigest(), entry['sha256'], (flow, gaps.entries))
                print(f'Owner quiet flow={flow} production_gaps={len(gaps.entries)} oracle_gaps=0', flush=True)
