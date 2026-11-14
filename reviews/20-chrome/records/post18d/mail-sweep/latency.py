"""Mail per-call latency through the real Engine, at 0/1000/4000 retained operations.

Same method as Chrome's latency check (control/chrome/ci/latency-*.py): many
calls per call type and history phase, median and p95 (nearest rank), with the
history grown inside one live engine from copies of a real completed operation.
Mail needs no server: the unchanged test fixtures' in-memory IMAP stands in.

Run with cwd = <worktree>/control/mail_tests and
PYTHONPATH=<worktree>/control:<worktree>/control/mail_tests:<this directory>.
Usage: latency.py OUT.json plain|instrumented [samples]
  plain         times engine.request only; storage_faults is never imported.
  instrumented  also counts every OS/SQLite write, close and journal read per
                call with the sweep's own OSWrites hooks (no fault injected).
"""
import copy
import json
import math
import os
import statistics
import sys
import tempfile
from contextlib import contextmanager, nullcontext
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import hostenv
hostenv.install()
from aresos_control.engine import Engine
from aresos_control.mail.roles import resolve
from aresos_control.mail.transport import folders
from support import WORK
from test_review_fixes_11 import MemoryIMAP

HISTORIES = (0, 1000, 4000)
WARMUP = 5
CALLS = ('search', 'read', 'file', 'compose', 'prepare_send', 'expiry')


class StableIMAP(MemoryIMAP):
    """MemoryIMAP without its test-only role flip on MOVE/COPY."""
    def __init__(self, count, mid):
        super().__init__(count, mid)
        self.roles['Pool'] = []
        self.boxes['Pool'] = {}
        self.validities['Pool'] = len(self.validities) + 1

    def uid(self, command, *args):
        if command in ('MOVE', 'COPY'):
            box = self.boxes[self.selected]
            uid, target = int(args[0]), args[1].strip('"')
            destination = max(self.boxes[target], default=0) + 1
            self.boxes[target][destination] = box[uid]
            if command == 'MOVE':
                del box[uid]
            self.copyuid = f'{self.validities[target]} {uid} {destination}'.encode()
            return 'OK', [b'Filed']
        return super().uid(command, *args)


def p95(values):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(.95 * len(values)) - 1)]


class Bench:
    def __init__(self, root, instrumented):
        self.instrumented = instrumented
        self.engine = Engine(root / 'state', root / 'evidence')
        self.mail = self.engine.adapters['mail']
        self.imap = StableIMAP(40, b'<latency@mail.invalid>')
        @contextmanager
        def imap(account):
            yield self.imap
        self.patcher = patch.object(self.mail.transport, 'imap', imap)
        self.patcher.start()
        account = {'id': 'box', 'addresses': ['owner@example.com'], 'ready': True,
                   'capabilities': list(self.imap.capabilities), 'smtp_capabilities': [], 'sent_policy': 'client',
                   'safe_folder_delete': True, 'format': 'plain', 'signature': '', **resolve(folders(self.imap))}
        self.engine.store.write({'mail:account:box': account}, 'fixture', 'Synthetic latency account')
        self.io = None
        if instrumented:
            import storage_faults
            self.OSWrites = storage_faults.OSWrites

    def request(self, action, arguments):
        result = self.engine.request({'v': 1, 'method': 'call', 'action': action, 'arguments': arguments})
        if not result['ok']:
            raise RuntimeError((action, result['error']))
        return result['data']

    def reference(self, folder, uid):
        return {'account': 'box', 'folder': folder, 'uidvalidity': self.imap.validities[folder],
                'uid': uid, 'message_id': self.imap.mid}

    def compose_args(self):
        return {'account': 'box', 'to': ['Anna Example <anna@example.com>'], 'subject': 'Latency', 'text': 'one\ntwo\n'}

    def completed_send(self):
        composition = self.request('mail_compose', self.compose_args())
        approval = self.request('mail_prepare_send', {k: composition[k] for k in ('composition_id', 'composition_hash')})['approval']
        def smtp(operation, composition, raw, stage):
            stage('smtp_data', 'accepted:250')
            return 'done', 'Synthetic DATA accepted'
        def append(account, folder, raw, flags):
            return {'uid': 1}
        with patch.object(self.mail, 'send_smtp', side_effect=smtp), patch.object(self.mail, 'append', side_effect=append):
            operation = self.request('mail_send', approval)['operation']
        stored = self.engine.store.get('op:' + operation['id'])
        assert stored['state'] == 'done', stored['state']
        return stored

    def grow(self, template, start, stop):
        # Disposable timing input only, shaped like Chrome's latency fixture.
        store = self.engine.store
        for first in range(start, stop, 32):
            changes = {}
            for index in range(first, min(first + 32, stop)):
                operation = copy.deepcopy(template)
                operation.update(id=store.generation + ':latency-history-' + str(index),
                                 reason='Synthetic completed timing history; nothing submitted')
                changes['op:' + operation['id']] = operation
            store.write(changes, 'mail_latency_fixture', 'Synthetic completed timing history; not acceptance')

    def timed(self, call):
        counter = self.OSWrites() if self.instrumented else None
        with counter.wrap(self.engine.store) if counter else nullcontext():
            started = perf_counter()
            call()
            elapsed = (perf_counter() - started) * 1000
        return elapsed, (counter.points if counter else None)

    def phase(self, samples):
        pool = iter(range(1, 10_000))
        for uid in range(1, WARMUP + samples + 1):
            self.imap.boxes['Pool'][uid] = self.imap.raw
        # Each call type gets its own warm-up and samples; arguments are fixed
        # so both commits do exactly the same Mail work.
        def search():
            self.request('mail_search', {'account': 'box', 'folders': ['Source'], 'limit': 20})
        def read():
            self.request('mail_read', {'reference': self.reference('Source', 1)})
        def file():
            self.request('mail_move', {'references': [self.reference('Pool', next(pool))], 'target': 'Target'})
        compositions = []
        def compose():
            compositions.append(self.request('mail_compose', self.compose_args()))
        prepared = []
        def prepare():
            composition = compositions.pop()
            prepared.append(self.request('mail_prepare_send', {k: composition[k] for k in ('composition_id', 'composition_hash')})['approval']['operation_id'])
        def expiry():
            self.engine.expire()
        result = {}
        for name, call in (('search', search), ('read', read), ('file', file), ('compose', compose),
                           ('prepare_send', prepare), ('expiry', expiry)):
            rows = [self.timed(call) for _ in range(WARMUP + samples)][WARMUP:]
            times = [elapsed for elapsed, _ in rows]
            entry = {'samples': len(times), 'median_ms': round(statistics.median(times), 3), 'p95_ms': round(p95(times), 3)}
            if self.instrumented:
                points = [points for _, points in rows]
                labels = sorted({label for p in points for label in p})
                entry['io_per_call_median'] = {label: statistics.median(p.count(label) for p in points) for label in labels}
                entry['io_points_per_call_median'] = statistics.median(len(p) for p in points)
            result[name] = entry
        # Leave no open reservations behind for the next history phase.
        for operation_id in prepared:
            self.request('mail_operation_cancel', {'operation_id': operation_id})
        # Untimed housekeeping: drop the phase's compositions (only cancelled
        # operations refer to them), as expiry would after 24 hours, so the
        # 128-composition working limit never shapes a later phase.
        store = self.engine.store
        store.write({key: None for key, _ in store.items('mail:composition:')}, 'mail_latency_fixture',
                    'Synthetic latency compositions removed between phases')
        return result

    def close(self):
        self.patcher.stop()
        self.engine.close()


def main():
    out, profile = Path(sys.argv[1]), sys.argv[2]
    samples = int(sys.argv[3]) if len(sys.argv) > 3 else 50
    assert profile in {'plain', 'instrumented'}
    assert profile == 'instrumented' or 'storage_faults' not in sys.modules
    with tempfile.TemporaryDirectory(dir=WORK) as temporary:
        bench = Bench(Path(temporary), profile == 'instrumented')
        try:
            template = bench.completed_send()
            phases, grown = {}, 0
            for history in HISTORIES:
                bench.grow(template, grown, history)
                grown = history
                phases[str(history)] = bench.phase(samples)
                print(history, {k: (v['median_ms'], v['p95_ms']) for k, v in phases[str(history)].items()}, flush=True)
            journal = (bench.engine.store.evidence_dir / 'operations.jsonl').stat().st_size
        finally:
            bench.close()
    out.write_text(json.dumps({'profile': profile, 'samples_per_call': samples, 'warmup': WARMUP,
                               'histories': list(HISTORIES), 'journal_bytes_at_end': journal, 'phases': phases},
                              indent=1, sort_keys=True))


if __name__ == '__main__':
    main()
