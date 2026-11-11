"""Local candidate checks, distinct from the stage-3 acceptance/oracle suite.

Run while STORAGE-S3-REDESIGN.patch is applied. These independently compare the
compact reference contract, not public wording or complete owner-visible sets.
"""
import argparse
from contextlib import nullcontext
import copy
import hashlib
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from aresos_control.common import Refused
from aresos_control.engine import Engine
from owner_state_oracle.records import decode
from storage_faults import OSWrites, outside_faults
from test_owner_state_sweep import OwnerScenario, FLOWS, EXTRA


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def expected(rows):
    # Written independently from the candidate's documented field table.
    result = {}
    state_order = ('reserved', 'submitting', 'started', 'unknown', 'partial',
                   'done', 'failed', 'refused', 'open', 'checked', 'saved')
    direct = {'id': 'i', 'app': 'a', 'source_key': 'k', 'evidence_fingerprint': 'f', 'repair_of': 'r'}
    flags = {'notice': 'n', 'ack': 'x', 'check_open': 'o', 'onboarded': 'b', 'ready': 'y', 'context_version': 'v'}
    hashed = {'context': 'c', 'stages': 't', 'reason': 'q', 'warning_checks': 'w',
              'sent_copy_check': 'j', 'roles_before': 'l', 'qualification': 'u', 'untrusted_content': 'd'}
    for key, row in rows.items():
        if key in {'generation', 'restore_pending'}:
            result[key] = {'v': row}
        elif key.startswith(('op:', 'intent:', 'export:', 'notice:', 'mail:filing:',
                             'mail:rename:', 'mail:account:', 'archived:', 'archive:')):
            fact = {code: row[name] for name, code in direct.items() if name in row}
            fact.update({code: int(row[name]) for name, code in flags.items() if name in row})
            fact.update({code: fingerprint(row[name]) for name, code in hashed.items() if name in row})
            if 'state' in row:
                fact['s'] = state_order.index(row['state'])
            if 'expires' in row:
                fact['e'] = row['expires']
            if not key.startswith(('op:', 'intent:', 'notice:')):
                fact['h'] = fingerprint(row)
            result[key] = fact
    return result


class ProjectionCandidate(unittest.TestCase):
    comparisons = 0
    cases = []
    failed_sql_reads = 0

    def assert_agrees(self, scenario, label):
        f = scenario.fixture
        with outside_faults():
            record = decode(f.root / 'state', f.root / 'evidence')
            actual = dict(f.engine.store.owner_projection.iter_items())
        self.assertEqual(expected(record.rows), actual, label)
        self.comparisons += 1

    def test_archive_keeps_unresolved_work_checks_and_unacknowledged_warnings(self):
        s = OwnerScenario('fixture')
        try:
            store = s.fixture.engine.store
            rows = {
                'intent:open': {'id': 'recovery-open', 'app': 'mail', 'state': 'started', 'context_version': 1},
                'mail:filing:check': {'id': 'check', 'state': 'done', 'check_open': True},
                'mail:filing:warning': {'id': 'warning', 'state': 'done'},
                'notice:warning': {'id': 'warning', 'app': 'mail', 'state': 'partial', 'ack': False,
                    'source_key': 'mail:filing:warning', 'untrusted_content': {'reason': 'Synthetic warning'}},
                'notice:acknowledged': {'id': 'acknowledged', 'app': 'mail', 'state': 'partial', 'ack': True,
                    'untrusted_content': {'reason': 'Synthetic acknowledged warning'}},
            }
            store.write(rows, 'fixture', 'Synthetic lifecycle inputs')
            store.owner_projection.compact()
            live = {key for _, data, _, _ in store.owner_projection._records(store.owner_projection.path) for key in data}
            self.assertTrue(set(rows) - {'notice:acknowledged'} <= live)
            self.assertNotIn('notice:acknowledged', live)
            self.assert_agrees(s, 'archive pinned keys')
            # Repeated archive is idempotent; it creates no duplicate history.
            sizes = {p.name: p.stat().st_size for p in store.owner_projection.directory.glob('*.bin')}
            store.owner_projection.compact()
            self.assertEqual(sizes, {p.name: p.stat().st_size for p in store.owner_projection.directory.glob('*.bin')})
        finally:
            s.close()

    def test_one_and_thousand_terminal_send_records_leave_same_live_size(self):
        s = OwnerScenario('fixture')
        try:
            store = s.fixture.engine.store
            def row(number):
                identity = store.generation + ':' + format(number, '032x')
                return {'id': identity, 'generation': store.generation, 'input_hash': fingerprint(number),
                    'app': 'mail', 'action': 'mail_send', 'state': 'done', 'expires': 0,
                    'approval': {'description': {'action': 'mail_send'}}, 'payload': {},
                    'context_version': 1, 'context': {'command': 'DATA', 'account': 'box'},
                    'stages': {'smtp_data': 'accepted:250', 'sent_copy': 'done'},
                    'reason': 'Synthetic finished send', 'notice': True, 'ack': True,
                    'sent_copy_check': {'state': 'checked', 'clean': True}}
            first = row(1)
            store.write({'op:' + first['id']: first}, 'fixture', 'One finished acknowledged send record')
            store.owner_projection.compact()
            one = store.owner_projection.path.stat().st_size
            rows = [row(n) for n in range(2, 1002)]
            store.write({'op:' + r['id']: r for r in rows}, 'fixture', 'One thousand finished acknowledged send records')
            store.owner_projection.compact()
            self.assertEqual(one, store.owner_projection.path.stat().st_size)
            self.assert_agrees(s, '1001 terminal records, including retired history')
            print('ARCHIVE size bound:', one, 'bytes after one and after 1001 synthetic terminal send records', flush=True)
        finally:
            s.close()

    def test_projection_reads_need_neither_sqlite_connection_nor_index(self):
        s = OwnerScenario('send_duplicate')
        try:
            s.call()
            self.assert_agrees(s, 'before failed SELECT')
            store = s.fixture.engine.store
            before = dict(store.owner_projection.iter_items())
            class FailedRead:
                def execute(self, *args):
                    raise sqlite3.OperationalError('Synthetic failed rollback: database or disk is full')
            with patch.object(store, 'db', FailedRead()), patch.object(store, 'index', FailedRead()):
                self.assertEqual(before, dict(store.owner_projection.iter_items()))
            s.fixture.engine.close()
            s.bind(Engine(s.fixture.root / 'state', s.fixture.root / 'evidence'))
            self.assert_agrees(s, 'after restart')
        finally:
            s.close()

    def test_changed_committed_payload_is_rejected(self):
        s = OwnerScenario('send')
        try:
            s.call()
            store = s.fixture.engine.store
            raw = bytearray(store.owner_projection.path.read_bytes())
            raw[24] ^= 1
            store.owner_projection.path.write_bytes(raw)
            with self.assertRaises(Refused) as refusal:
                list(store.owner_projection.iter_items())
            self.assertEqual('evidence_corrupt', refusal.exception.code)
        finally:
            s.close()

    def test_missing_projection_update_is_caught_by_agreement(self):
        s = OwnerScenario('fixture')
        try:
            store = s.fixture.engine.store
            with patch.object(store.owner_projection, 'prepare'):
                store.write({'intent:omitted': {'id': 'recovery-omitted', 'app': 'mail', 'state': 'started'}},
                            'fixture', 'Planted missing projection update')
            with self.assertRaises(AssertionError):
                self.assert_agrees(s, 'the missing source must fail')
        finally:
            s.close()

    def run_case(self, flow, number=None, mode='single', cleanup=None, crash=False):
        s = OwnerScenario(flow)
        try:
            fault = OSWrites(number, mode=mode, cleanup_at=cleanup)
            with fault.wrap(None if flow.startswith('restart_') else s.fixture.engine.store):
                reply = s.call()
            if number is not None:
                self.assertTrue(fault.failed, (flow, number))
            f = s.fixture
            label = (flow, mode, number, cleanup, crash)
            if flow.startswith('restart_') and number is not None and not reply['ok']:
                s.bind(Engine(f.root / 'state', f.root / 'evidence'))
            if crash:
                with tempfile.TemporaryDirectory(prefix='projection-crash-', dir=f.root) as temporary:
                    saved = Path(temporary)
                    for name in ('state', 'evidence'):
                        shutil.copytree(f.root / name, saved / name)
                    f.engine.close()
                    for name in ('state', 'evidence'):
                        shutil.rmtree(f.root / name)
                        shutil.copytree(saved / name, f.root / name)
                s.bind(Engine(f.root / 'state', f.root / 'evidence'))
            if mode == 'persistent':
                exhausted = OSWrites(1, mode='persistent')
                with exhausted.wrap(f.engine.store):
                    try:
                        f.engine.store.db.execute('SELECT k,v FROM kv').fetchall()
                    except sqlite3.Error as exc:
                        self.failed_sql_reads += 1
                        print('SQLITE READ FAILED', label, type(exc).__name__, str(exc), flush=True)
                    self.assert_agrees(s, (label, 'persistent, before restoring space'))
            self.assert_agrees(s, (label, 'space restored'))
            self.cases.append(label)
            return fault.points, fault.cleanup_points
        finally:
            s.close()

    def test_every_flow_and_mode_sample(self):
        # These are representative sites, not the exhaustive stage-3 sweep.
        for flow in FLOWS + EXTRA:
            points = None
            with self.subTest(flow=flow, mode='fault-free'):
                points, _ = self.run_case(flow)
            if points is None:
                continue  # This flow's failed assertion is already reported.
            eligible = [n for n, label in enumerate(points, 1) if not label.endswith('.close')]
            writes = [n for n in eligible if points[n - 1] == 'sqlite.main.write']
            for point in sorted({writes[0], writes[-1]} if writes else {eligible[0]}):
                cleanups = []
                for mode in ('single', 'persistent'):
                    with self.subTest(flow=flow, point=point, mode=mode, phase='live'):
                        _, observed = self.run_case(flow, point, mode)
                        if mode == 'single':
                            cleanups = observed
                    with self.subTest(flow=flow, point=point, mode=mode, phase='crash'):
                        self.run_case(flow, point, mode, crash=True)
                with self.subTest(flow=flow, point=point, mode='cleanup-pair-discovery'):
                    secondary = next((n for n, _, _ in cleanups if n > point), None)
                    self.assertIsNotNone(secondary, flow)
                if secondary is not None:
                    with self.subTest(flow=flow, point=point, mode='cleanup-pair'):
                        self.run_case(flow, point, cleanup=secondary)
                    with self.subTest(flow=flow, point=point, mode='cleanup-pair', phase='crash'):
                        self.run_case(flow, point, cleanup=secondary, crash=True)
                print('AGREEMENT attempted flow', flow, 'sample fault', point, points[point - 1], flush=True)
        print('AGREEMENT sampled scenario count', len(self.cases), flush=True)
        print('AGREEMENT actual SQLite read failures', self.failed_sql_reads, flush=True)
        print('AGREEMENT successful compact comparisons', self.comparisons, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--local-policy', action='store_true')
    args, remaining = parser.parse_known_args()
    policy = SourceFileLoader('projection_local_policy', str(Path(__file__).with_name('STORAGE-S3-LOCAL-POLICY.py'))).load_module() if args.local_policy else None
    with policy.local_policy() if policy else nullcontext():
        unittest.main(argv=[__file__, *remaining], verbosity=2)
