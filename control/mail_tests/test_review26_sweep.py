"""Self-tests for stronger completion, live admission and raw cleanup oracles."""
import errno
import unittest
from unittest.mock import patch

from aresos_control.common import Refused, sha256, storage_refusal
from test_review23_sweep import Scenario
from storage_faults import OSWrites


class Sweep26(unittest.TestCase):
    def test_review26_completion_oracle_rejects_one_data_and_only_unrelated_sent(self):
        scenario = Scenario('send')
        try:
            self.assertTrue(scenario.call()['ok'])
            self.assertEqual(scenario.remote['DATA'], 1)
            scenario.fixture.imap.boxes['Sent'] = {1: b'Message-ID: <unrelated@mail.invalid>\r\n\r\nOld mail'}
            with self.assertRaises(AssertionError):
                scenario.assert_completion(scenario.operation_id, 'done')
        finally:
            scenario.close()

    def test_review26_blob_enospc_then_implicit_close_eio_preserves_first_cause(self):
        scenario = Scenario('send')
        try:
            blobs = scenario.fixture.engine.blobs
            clean = OSWrites()
            with clean.wrap():
                blobs.put(b'Synthetic close discovery')
            write = next(i for i, label in enumerate(clean.points, 1) if label == 'file.write')
            trace = OSWrites(write)
            with trace.wrap(), self.assertRaises(Refused):
                blobs.put(b'Synthetic close primary')
            close = next(i for i, label, _ in trace.cleanup_points if i > write and label == 'file.close')
            pair = OSWrites(write, cleanup_at=close)
            with pair.wrap(), self.assertRaises(Refused) as caught:
                blobs.put(b'Synthetic close pair')
            self.assertEqual(caught.exception.code, 'storage_limit')
            self.assertIn('Disk full', str(caught.exception))
            self.assertTrue(any('Cleanup' in note and 'I/O' in note for note in caught.exception.__notes__))
        finally:
            scenario.close()

    def test_review26_admission_sweep_recovers_live_without_restart(self):
        # Fail before admission's actual work, then restore space on the SAME
        # Store. Never replay a remote mutation: pending + a fresh local write
        # are the next safe calls in a flow that already touched the server.
        from aresos_control.space import SpaceLedger
        from aresos_control import retention
        flows = ('send', 'repair', 'delete_trash', 'delete_permanent', 'unsubscribe_mailto', 'unsubscribe_https',
                 'status', 'settlement', 'cancel', 'restore', 'attachment_export', 'testapp_export',
                 'password', 'filing_move', 'filing_copy', 'filing_rename', 'expiry', 'maintenance', 'archive')
        counts = {}
        for flow in flows:
            clean = Scenario(flow)
            points = []
            admit, retain = SpaceLedger.admit, retention.admit
            def ledger(instance, *args, **kwargs):
                points.append('ledger')
                return admit(instance, *args, **kwargs)
            def quota(*args, **kwargs):
                points.append('retention')
                return retain(*args, **kwargs)
            try:
                with patch.object(SpaceLedger, 'admit', ledger), patch.object(retention, 'admit', quota):
                    clean.call()
            finally:
                clean.close()
            for number in range(1, len(points) + 1):
                scenario, cursor = Scenario(flow), [0]
                store = scenario.fixture.engine.store
                def hit():
                    cursor[0] += 1
                    if cursor[0] == number:
                        raise Refused('storage_limit', 'Synthetic admission refusal; no transaction started.')
                def ledger(instance, *args, **kwargs):
                    hit()
                    return admit(instance, *args, **kwargs)
                def quota(*args, **kwargs):
                    hit()
                    return retain(*args, **kwargs)
                try:
                    with self.subTest(flow=flow, admission=number):
                        with patch.object(SpaceLedger, 'admit', ledger), patch.object(retention, 'admit', quota):
                            result = scenario.call()
                        self.assertFalse(result['ok'], result)
                        self.assertFalse(store.write_failed, (flow, number))
                        remote = scenario.remote.copy()
                        if store.locked:
                            self.assertTrue(scenario.call()['ok'])
                        result = scenario.fixture.engine.request({'v': 1, 'method': 'call', 'action': 'control_pending', 'arguments': {}})
                        self.assertTrue(result['ok'], result)
                        store.write({}, 'fixture_live_recovery', 'Next local write after restored admission')
                        self.assertIs(scenario.fixture.engine.store, store)
                        self.assertEqual(remote, scenario.remote)
                finally:
                    scenario.close()
            counts[flow] = len(points)
        print('Review26 live admission recovery counts: ' + str(counts), flush=True)
