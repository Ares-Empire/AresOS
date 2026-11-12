"""Required normal-use contracts; no expected-failure ledger is consulted."""
import unittest

from owner_state_cases import run_quiet
from test_owner_state_sweep import FLOWS, EXTRA, exercise


class QuietChecks:
    def __init__(self, test):
        self.test = test
        self.entries = {}
        self.calls = set()
        self.aliases = {}

    def bind(self, record):
        pass

    def checker(self, case):
        def check(view, expected, actual):
            self.calls.add((case, view))
            # Stage 3's missing disclosures/details are optional. Normal use
            # must still add no warnings when none are owed, over-count them,
            # duplicate them or lose the stage-2 approval/context guarantees.
            if view.endswith('.notice-count'):
                wanted, got = next(iter(expected)), next(iter(actual))
                self.test.assertLessEqual(int(got.detail), int(wanted.detail), (case, view))
            if (view.endswith('.notice-head') and not expected or
                view.endswith('.notice-duplicates') or
                view in {'R2.context-before-command', 'operation-approval'}):
                self.test.assertEqual(actual, expected, (case, view, expected, actual))
        return check


class NormalUse(unittest.TestCase):
    def test_every_fault_free_point_zero_has_no_spurious_warnings_or_context_loss(self):
        checks = QuietChecks(self)
        for flow in FLOWS + EXTRA:
            with self.subTest(flow=flow):
                exercise(flow, gaps=checks)
                self.assertIn((flow + '/single/0/0/live-restored', 'R2.context-before-command'), checks.calls)
                print(f'Owner quiet point-zero flow={flow} PASS', flush=True)

    def test_clean_send_move_copy_rename_delete_and_legacy_contracts_are_quiet(self):
        # These fixtures remove deliberate duplicate/role-race triggers; their
        # existing assertions also demand done, no passive notices and no
        # oracle lifecycle/completion errors for every clean operation.
        checks = QuietChecks(self)
        run_quiet(checks)
        self.assertTrue(checks.calls)
