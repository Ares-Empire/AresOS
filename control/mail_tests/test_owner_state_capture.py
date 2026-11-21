"""Regressions for the two harness failures in capture 44352598226."""
import json
import unittest
from unittest.mock import patch

from owner_state_oracle.driver import Driver
from owner_state_oracle.gaps import Gaps
from test_owner_state_sweep import OwnerScenario, exercise
from test_owner_state_perturb import recovery_recordings


class CaptureHarness302(unittest.TestCase):
    def test_restart_preserves_the_live_connections_generation_view(self):
        scenario = OwnerScenario('restore')
        try:
            driver = Driver(scenario)
            generation = 'synthetic-live-generation'
            # An interrupted transaction can still own a live SQLite view.
            scenario.fixture.engine.store.db.execute("UPDATE kv SET v=? WHERE k='generation'", (json.dumps(generation),))
            with patch('owner_state_oracle.driver.startup_obligation') as obligation:
                driver.restarted()
            self.assertEqual(obligation.call_args.args[2], generation)
        finally:
            scenario.close()

    def test_failed_startup_can_be_crashed_with_the_old_engine_already_closed(self):
        for flow, point in (('restart_index', 27), ('restart_tail', 29)):
            for mode in ('single', 'persistent'):
                with self.subTest(flow=flow, point=point, mode=mode):
                    gaps = Gaps(recording=True)
                    exercise(flow, point, mode, gaps=gaps, phase='crash')
                    self.assertTrue(any(key.endswith('/crash-restart') for key in gaps.executed))
                    self.assertFalse(any(key.endswith(('/startup-replay', '.restore-lock')) for key in gaps.entries))

    def test_recovery_corpus_discovers_boundaries_after_trace_points_move(self):
        original = OwnerScenario.call
        def shifted(scenario):
            # Synthetic extra VFS sites reproduce a platform's longer trace.
            # Number them in the same trace as the account write; no
            # production state or expected rows are changed.
            if scenario.flow == 'onboarding':
                from storage_faults import ACTIVE
                for _ in range(8):
                    ACTIVE.hit('sqlite.main.write', sqlite=True)
            return original(scenario)
        with patch.object(OwnerScenario, 'call', shifted):
            recordings = recovery_recordings(self)
        self.assertEqual([name for name, _, _ in recordings], [
            'applied-tail/cancel', 'applied-tail/onboarding',
            'staged-restore/final', 'staged-restore/intermediate'])
        account = recordings[1][2]
        self.assertIn('mail:account:new', account.prepared[-1]['set'])
        self.assertGreater(account.head[0], max(account.committed))
