"""Review 13: pending pages retain one fixed page at every history size."""
import gc
import tracemalloc

from aresos_control.common import canonical, digest
from aresos_control.engine import Engine
from support import EngineCase
import test_journal_streaming as streaming


class Pending21(EngineCase):
    def test_review21_1000_and_10000_unknowns_correct_pages_cursor_and_fixed_memory(self):
        metrics = []
        for extra, count in ((1000, 1000), (9000, 10000)):
            streaming.JournalStreaming.seed_history(self, extra, operations=True)
            self.engine = Engine(self.root / 'state', self.root / 'independent')
            for key, op in self.engine.store.iter_items('op:'):
                op['state'] = 'unknown'
                self.engine.store.db.execute('UPDATE kv SET v=? WHERE k=?', (canonical(op), key))
            self.engine.store.db.commit()
            # Exclude one-time Python module imports from response memory.
            self.engine.notices()
            expected = []
            for _, op in self.engine.store.iter_items('op:'):
                expected.append({'operation_id': op['id'], 'app': op['app'], 'state': op['state'], 'reason': op['reason']})
                if len(expected) == 10:
                    break
            gc.collect()
            tracemalloc.start()
            try:
                first = self.engine.pending(args={'limit': 5})
                second = self.engine.pending(args={'limit': 5, 'cursor': first['cursor']})
                peak = tracemalloc.get_traced_memory()[1]
            finally:
                tracemalloc.stop()
            self.assertEqual(first['items'] + second['items'], expected)
            self.assertEqual(first['total'], count)
            self.assertEqual(second['total'], count)
            self.assertTrue(first['cursor'].endswith(':5'))
            self.assertTrue(second['cursor'].endswith(':10'))
            self.assertLess(peak, 1024 * 1024)
            metrics.append(peak)
            op = self.engine.operation(expected[0]['operation_id'])
            op['reason'] = 'Synthetic changed pending state ' + str(count)
            self.engine.store.write({'op:' + op['id']: op}, 'fixture', 'Synthetic change', op['id'])
            result = self.call('control_pending', {'cursor': first['cursor']})
            self.assertEqual(result['error']['code'], 'stale_reference')
        print('Review21 pending peak bytes, 1k/10k unknown operations:', metrics)

    def test_review21_pending_never_reads_approval_description_and_keeps_canonical_cursor(self):
        approval = self.reserve()
        op = self.engine.operation(approval['operation_id'])
        expected = [{'operation_id': op['id'], 'app': op['app'], 'state': op['state'], 'reason': op['reason']}]
        class NoDescription(dict):
            def __getitem__(self, key):
                raise AssertionError('Pending must not construct full descriptions')
        op['approval'] = NoDescription()
        from unittest.mock import patch
        original = self.engine.store.iter_items
        with patch.object(self.engine.store, 'iter_items', side_effect=lambda prefix: iter([('op:' + op['id'], op)])
                          if prefix == 'op:' else original(prefix)):
            result = self.engine.pending(args={'limit': 1})
            self.assertEqual(result['items'], expected)
            self.assertEqual(result['total'], 1)
            self.assertIsNone(result['cursor'])
            cursor = digest(['pending', expected]) + ':0'
            self.assertEqual(self.engine.pending(args={'cursor': cursor})['items'], expected)
