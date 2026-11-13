"""Real Git checkout bytes, including the accepted probe33 negative control."""
import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import checkout_sources as checkout

spec = importlib.util.spec_from_file_location('rebind', ROOT / 'reviews/27-first-update-release/rebind.py')
rebind = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebind)

PENDING = ROOT / 'os/manifest/ci/16/pending-rebind.json'


def pending_rebind():
    """Bound files changed after the last VM rehearsal, waiting for the next one.

    Each row records the checkout bytes accepted when the file was set aside,
    so any further change to a waiting file still fails until it is recorded.
    """
    record = json.loads(PENDING.read_text())
    return [dict(sha256=row['sha256'], path=row['path']) for row in record['files']]


def check_waiting(root, union, pending):
    """The waiting list is empty right after a VM rehearsal rebinds, then holds
    one row per bound file changed since, with its new checkout bytes
    (integrator, 2026-11-13). These rules hold at any time, so no bound file
    changes unrecorded.
    """
    waiting = [row['path'] for row in pending]
    walk = {row['path']: row for row in union}
    assert len(waiting) == len(set(waiting)), 'Waiting path listed twice'
    unbound = [path for path in waiting if path not in walk]
    assert not unbound, 'Waiting path is not bound: ' + ', '.join(unbound)
    # Every bound file that is not waiting replays its walk bytes.
    kept = [row for row in union if row['path'] not in waiting]
    checkout.verify(root, kept)
    # Every waiting file matches the bytes recorded for it ...
    if pending:
        checkout.verify(root, pending)
    # ... and differs from its walk bytes.
    for path in waiting:
        try:
            checkout.verify(root, [walk[path]])
        except AssertionError:
            continue
        raise AssertionError('Waiting file still equals its walk bytes: ' + path)


class CheckoutSourcesTest(unittest.TestCase):
    def test_current_receipts_agree_and_package14_stays_historical(self):
        # Package 27's rehearsal rebinds package 16's tables; until it records
        # them, package 16's stay current.
        package='27' if (ROOT/'os/manifest/ci/27/source-bindings.json').exists() else '16'
        folder=ROOT/'os/manifest/ci'/package
        walk=json.loads((folder/'host-walk.json').read_text())
        record=json.loads((folder/'source-bindings.json').read_text())
        self.assertEqual(record['package'],package)
        self.assertEqual(walk['status'],'passed')
        self.assertFalse(walk['stick_across_reboot'])
        self.assertEqual(walk['sources'],record['tables'][0]['sources'])
        self.assertIn('os/tests/test_owner_staged_release.py',{row['path'] for row in walk['sources']})
        if package=='27':
            old=json.loads((ROOT/'os/manifest/ci/16/source-bindings.json').read_text())
            self.assertEqual([t['name'].replace('package16','package27') for t in old['tables'][1:]],
                             [t['name'] for t in record['tables'][1:]])
            for before,after in zip(old['tables'][1:],record['tables'][1:]):
                self.assertEqual([r['path'] for r in before['sources']],[r['path'] for r in after['sources']])
        legacy=json.loads((ROOT/'os/manifest/ci/14/host-walk/result.json').read_text())
        self.assertNotEqual(walk['sources'],legacy['sources'])
        self.assertTrue(legacy['current_verification'].startswith('os/manifest/ci/14/'))

    def test_every_active_source_binding_replays_checkout_including_crlf(self):
        tables = checkout.active_tables(ROOT)
        self.assertGreaterEqual(len(tables), 4)
        union = checkout.merge(tables)
        # Every bound file replays its walk bytes, except files set aside until
        # the next VM rehearsal rebinds them (first the owner, 2026-11-08; the
        # list reopened after package 27's rehearsal by the integrator,
        # 2026-11-13). Those differ from the walk and match the bytes recorded.
        check_waiting(ROOT, union, pending_rebind())
        # The recording tool finds exactly the rows the list holds.
        self.assertEqual(rebind.changed(), pending_rebind())
        rows = tables[0][1]
        powershell = next(row for row in rows if row['path'] == 'os/tests/owner-tools.Tests.ps1')
        raw = (ROOT / powershell['path']).read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(powershell['sha256'], hashlib.sha256(raw.replace(b'\n', b'\r\n')).hexdigest())
        self.assertNotEqual(powershell['sha256'], hashlib.sha256(raw).hexdigest())

    def test_waiting_list_refuses_every_unrecorded_or_stale_change(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            (root / '.gitattributes').write_bytes(b'* text=auto eol=lf\n')
            for name in ('a.sh', 'b.sh', 'c.sh', 'd.sh'):
                (root / name).write_bytes(name.encode() + b'\n')
            union = checkout.records(root, ['.gitattributes', 'a.sh', 'b.sh', 'c.sh'])
            check_waiting(root, union, [])
            (root / 'b.sh').write_bytes(b'b changed\n')
            pending = checkout.records(root, ['b.sh'])
            check_waiting(root, union, pending)
            cases = {
                'a waiting file changed again without its row': ('b.sh', None, 'binding mismatch: b.sh'),
                'a listed file that still equals its walk bytes': (None, checkout.records(root, ['a.sh']),
                                                                   'still equals its walk bytes: a.sh'),
                'a listed path that is not bound': (None, checkout.records(root, ['d.sh']), 'not bound: d.sh'),
                'a bound file changed without a row': ('c.sh', None, 'binding mismatch: c.sh'),
                'a path listed twice': (None, pending, 'listed twice'),
            }
            for label, (changed, extra, message) in cases.items():
                before = {name: (root / name).read_bytes() for name in ('b.sh', 'c.sh')}
                if changed:
                    (root / changed).write_bytes(b'changed again\n')
                with self.subTest(label), self.assertRaisesRegex(AssertionError, message):
                    check_waiting(root, union, pending + (extra or []))
                for name, raw in before.items():
                    (root / name).write_bytes(raw)
            check_waiting(root, union, pending)

    def test_exact_dda72ed_record_refuses_with_its_unchanged_crlf_declared_source(self):
        old = json.loads((ROOT / 'os/tests/fixtures/owner-tools/14zzd-checkout-sources.json').read_text())
        self.assertEqual(old['commit'], 'dda72ed8a5bdb038d953f950f76c66fc37297115')
        self.assertEqual(len(old['sources']), 195)
        row = next(row for row in old['sources'] if row['path'] == 'os/tests/owner-tools.Tests.ps1')
        raw = (ROOT / row['path']).read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
        with self.assertRaisesRegex(AssertionError, 'os/tests/owner-tools.Tests.ps1'):
            checkout.verify(ROOT, old['sources'])

    def test_real_git_filters_lf_crlf_binary_and_refuses_missing_or_unsafe_sources(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            (root / '.gitattributes').write_bytes(b'* text=auto eol=lf\n*.ps1 text eol=crlf\n*.bin binary\n')
            files = {'a.sh': b'a\r\nb\r\n', 'a.ps1': b'a\nb\n', 'a.bin': b'\x00a\r\nb\n'}
            for name, raw in files.items(): (root / name).write_bytes(raw)
            rows = checkout.records(root, files)
            expected = {'a.sh': b'a\nb\n', 'a.ps1': b'a\r\nb\r\n', 'a.bin': files['a.bin']}
            self.assertEqual(rows, [dict(sha256=hashlib.sha256(raw).hexdigest(), path=name) for name, raw in expected.items()])
            self.assertEqual(checkout.verify(root, rows), 3)
            (root / 'a.sh').write_bytes(b'changed\n')
            with self.assertRaisesRegex(AssertionError, 'a.sh'): checkout.verify(root, rows)
            for names in (['absent'], ['../outside'], ['/absolute'], ['C:/outside'], ['a.ps1', 'a.ps1']):
                with self.subTest(names=names), self.assertRaises(AssertionError): checkout.records(root, names)
            with self.assertRaisesRegex(AssertionError, 'Conflicting checkout record'):
                checkout.merge([('first', rows), ('second', [dict(rows[0], sha256='0' * 64)])])
            with self.assertRaisesRegex(AssertionError, 'duplicate source'):
                checkout.merge([('duplicate', rows + rows[:1])])


if __name__ == '__main__': unittest.main()
