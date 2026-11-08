"""Review 11: verified disk indexes retain constant Python memory across history."""
from contextlib import closing
import gc
import json
import sqlite3
import time
import tracemalloc
from unittest.mock import patch

from aresos_control.common import Refused, canonical, digest
from aresos_control.engine import Engine
from support import EngineCase


class JournalStreaming(EngineCase):
    def seed_history(self, count, operations=False):
        """Offline fixture: valid chain + matching SQLite head, no durability claim."""
        store = self.engine.store
        sequence, previous, generation = len(store.events), store.events[-1]['hash'], store.generation
        self.engine.close()
        with open(self.root / 'independent/operations.jsonl', 'ab') as journal, \
             closing(sqlite3.connect(self.root / 'state/control.sqlite')) as db:
            for number in range(sequence + 1, sequence + count + 1):
                record = {'format': 2, 'seq': number, 'previous': previous, 'time': time.time(),
                          'generation': generation, 'operations': []}
                if operations:
                    record['operations'] = [{'id': generation + ':' + f'{number:032x}', 'generation': generation,
                        'input_hash': '0' * 64, 'description': {'action': 'testapp_send', 'subject': 'Synthetic ' + 'x' * 256},
                        'state': 'done'}]
                    compact = record['operations'][0]
                    operation = {**compact, 'app': 'testapp', 'action': 'testapp_send',
                                 'approval': {'operation_id': compact['id'], 'description': compact['description']},
                                 'payload': {'text': 'Synthetic retained composition ' + 'x' * 512},
                                 'stages': {}, 'reason': 'Synthetic completed operation', 'expires': 0}
                    db.execute('INSERT INTO kv VALUES (?,?)', ('op:' + compact['id'], canonical(operation)))
                record['hash'] = digest(record)
                event = {'seq': number, 'time': record['time'], 'action': 'fixture', 'summary': 'Synthetic audit',
                         'outcome': 'done', 'operation_id': None, 'set': {}, 'record': record}
                journal.write((canonical(record) + '\n' + canonical({'commit': number, 'hash': record['hash']}) + '\n').encode())
                db.execute('INSERT INTO events VALUES (?,?)', (number, canonical(event)))
                previous = record['hash']
            db.execute('UPDATE head SET seq=?,hash=? WHERE id=1', (sequence + count, previous))
            db.commit()

    def measured_restart(self):
        gc.collect()
        tracemalloc.start()
        try:
            # Boundary installation reads have their own fixed 6 MiB buffer;
            # measure the journal lifecycle, including all Store startup work.
            with patch('aresos_control.engine.Boundary', return_value=self.engine.boundary):
                self.engine = Engine(self.root / 'state', self.root / 'independent')
            gc.collect()
            retained, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        return retained, peak

    def test_review19_startup_retained_and_peak_memory_bounded_for_1000_and_10000_unique_operations(self):
        metrics = []
        for extra in (1000, 9000):
            self.seed_history(extra, operations=True)
            retained, peak = self.measured_restart()
            metrics.append((retained, peak))
            self.assertLess(retained, 512 * 1024)
            self.assertLess(peak, 2 * 1024 * 1024)
            count = self.engine.store.index.execute('SELECT count(*) FROM latest').fetchone()[0]
            self.assertEqual(count, 1000 if extra == 1000 else 10000)
            gc.collect()
            tracemalloc.start()
            try:
                self.assertEqual(sum(1 for _ in self.engine.store.events), len(self.engine.store.events))
                self.assertEqual(sum(1 for _ in self.engine.store.iter_audit()), len(self.engine.store.events))
                response = self.call('control_log', {'limit': 2})
                self.assertTrue(response['ok'], response)
                page = response['data']
                self.assertEqual(len(page['items']), 2)
                self.assertEqual(page['total'], len(self.engine.store.events))
                self.assertLess(tracemalloc.get_traced_memory()[1], 2 * 1024 * 1024)
            finally:
                tracemalloc.stop()
        print('Review19 journal memory (retained, peak bytes), 1k/10k unique operations:', metrics)

    def test_review19_stream_verification_detects_middle_corruption_torn_tail_and_whole_suffix_truncation(self):
        self.seed_history(2000)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.engine.close()
        path = self.root / 'independent/operations.jsonl'
        original = path.read_bytes()
        rows = original.splitlines(keepends=True)
        damaged = rows.copy()
        event = json.loads(damaged[len(rows) // 2])
        event['generation'] = 'f' * 32
        damaged[len(rows) // 2] = (canonical(event) + '\n').encode()
        for raw, code in ((b''.join(damaged), 'evidence_corrupt'), (original[:-1], 'evidence_corrupt'),
                          (b''.join(rows[:-2]), 'evidence_mismatch')):
            path.write_bytes(raw)
            with self.assertRaises(Refused) as error:
                Engine(self.root / 'state', self.root / 'independent')
            self.assertEqual(error.exception.code, code)
        path.write_bytes(original)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertFalse(self.engine.store.locked)

    def test_review19_large_restart_rebuilds_untrusted_index_detects_restore_and_refuses_replay(self):
        closed = self.reserve()
        self.data('testapp_send', closed)
        self.seed_history(3000)
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        backup = sqlite3.connect(self.root / 'backup.sqlite')
        self.engine.store.db.backup(backup)
        backup.close()
        pending = self.reserve(subject='After older backup')
        self.seed_history(3000)
        # The derived index is not authority, even if its last row is altered.
        with closing(sqlite3.connect(self.root / 'independent/journal-index.sqlite')) as index:
            index.execute('DELETE FROM latest')
            index.execute("UPDATE records SET hash='untrusted'")
            index.commit()
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.engine.close()
        (self.root / 'independent/journal-index.sqlite').write_bytes(b'Invalid disposable index')
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        before = self.engine.receiver.evidence(closed['operation_id'])
        self.data('testapp_send', closed)
        self.assertEqual(self.engine.receiver.evidence(closed['operation_id']), before)
        self.engine.close()
        (self.root / 'state/control.sqlite').write_bytes((self.root / 'backup.sqlite').read_bytes())
        self.engine = Engine(self.root / 'state', self.root / 'independent')
        self.assertTrue(self.engine.store.locked)
        self.assertEqual(self.call('testapp_send', closed)['error']['code'], 'restore_required')
        restored = self.data('control_restore_confirm', {'confirm': 'invalidate earlier approvals'}, admin=True)
        self.assertIn(pending['operation_id'], restored['unknown'])
        self.restart()
        for approval in (closed, pending):
            self.assertFalse(self.call('testapp_send', approval)['ok'])
        self.assertEqual(self.engine.receiver.evidence(closed['operation_id']), before)

    def test_review19_streamed_log_pages_keep_all_entries_and_refuse_cursor_after_change(self):
        for _ in range(25):
            self.engine.store.write({}, 'fixture', 'Synthetic log entry')
        expected = [event['seq'] for event in self.engine.store.iter_audit()]
        seen, args = [], {'limit': 3}
        while True:
            result = self.data('control_log', args)
            seen.extend(event['seq'] for event in result['items'])
            self.assertEqual(result['total'], len(expected))
            if not result['cursor']:
                break
            args['cursor'] = result['cursor']
        self.assertEqual(seen, expected)
        cursor = self.data('control_log', {'limit': 1})['cursor']
        self.engine.store.write({}, 'fixture', 'Log changed')
        self.assertEqual(self.call('control_log', {'cursor': cursor})['error']['code'], 'stale_reference')
