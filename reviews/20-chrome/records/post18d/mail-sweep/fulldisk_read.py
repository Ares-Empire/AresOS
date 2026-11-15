"""Read-only Mail calls on a full disk, at several retained-operation counts.

Every space-allocating write (file/SQLite create or write, including SQLite's
temporary sort files) fails with ENOSPC through the sweep's own OSWrites hooks;
closes still succeed. Also records the query plan and time of the pending scan.
Usage: fulldisk_read.py OUT.json [history ...]
"""
import json
import statistics
import sys
import tempfile
from pathlib import Path
from time import perf_counter

import latency
import storage_faults

QUERY = "SELECT k,v FROM kv INDEXED BY operation_headers WHERE substr(k,1,3)='op:' AND json_extract(v,'$.app') IS NOT 'chrome' ORDER BY k"


class FullDisk(storage_faults.OSWrites):
    def hit(self, label, sqlite=False):
        if storage_faults.EXCLUDED:
            return 0
        self.points.append(label)
        if label.rsplit('.', 1)[-1] in {'write', 'create'}:
            self.failed = True
            self.failures.append((len(self.points), label, 'ENOSPC'))
            if sqlite:
                return 13  # SQLITE_FULL
            raise OSError(28, 'Synthetic full disk at ' + label)
        return 0


def probe(history):
    with tempfile.TemporaryDirectory(dir=latency.WORK) as temporary:
        bench = latency.Bench(Path(temporary), False)
        try:
            bench.grow(bench.completed_send(), 0, history)
            engine, entry = bench.engine, {}
            try:
                entry['pending_scan_plan'] = [row[-1] for row in engine.store.db.execute('EXPLAIN QUERY PLAN ' + QUERY)]
            except Exception as exc:
                entry['pending_scan_plan'] = 'not on this commit: ' + str(exc)
            for action, args in (('mail_read', {'reference': bench.reference('Source', 1)}),
                                 ('mail_search', {'account': 'box', 'folders': ['Source'], 'limit': 20})):
                disk = FullDisk()
                with disk.wrap(engine.store):
                    result = engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': args})
                entry[action] = {'ok': result['ok'], 'error': result.get('error', {}).get('code'),
                                 'points': len(disk.points), 'first_failure': disk.failures[:1]}
                engine.store.write_failed = False
            store = engine.store
            if getattr(store, 'operation_headers', False):
                # Same scan with and without the forced index (diagnosis only).
                def scan(forced):
                    store.operation_headers = forced
                    runs = []
                    for _ in range(7):
                        started = perf_counter()
                        sum(1 for _ in store.iter_operations(exclude_app='chrome'))
                        runs.append((perf_counter() - started) * 1000)
                    return round(statistics.median(runs), 2)
                entry['pending_scan_ms'] = {'forced_index': scan(True), 'primary_key_order': scan(False)}
                store.operation_headers = True
            return entry
        finally:
            bench.close()


def main():
    histories = [int(value) for value in sys.argv[2:]] or [0, 300, 500, 700, 1000, 4000]
    report = {str(history): probe(history) for history in histories}
    Path(sys.argv[1]).write_text(json.dumps(report, indent=1, sort_keys=True))
    for history, entry in report.items():
        print(history, {k: (v['ok'], v['error'], v['points']) for k, v in entry.items() if k.startswith('mail_')})


if __name__ == '__main__':
    main()
