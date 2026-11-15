"""Real Git checkout bytes, including the accepted probe33 negative control."""
import contextlib
import hashlib
import importlib.util
import io
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


def pending_removed():
    """Bound files deleted since the last VM rehearsal (22c's three old payload scripts)."""
    return json.loads(PENDING.read_text()).get('removed', [])


def check_waiting(root, union, pending, removed=()):
    """The waiting list is empty right after a VM rehearsal rebinds, then holds
    one row per bound file changed since, with its new checkout bytes
    (integrator, 2026-11-13), and the path of each bound file deleted since.
    These rules hold at any time, so no bound file changes or goes unrecorded.
    """
    waiting = [row['path'] for row in pending]
    walk = {row['path']: row for row in union}
    assert len(waiting) == len(set(waiting)), 'Waiting path listed twice'
    assert len(removed) == len(set(removed)) and not set(removed) & set(waiting), 'Removed path listed twice'
    unbound = [path for path in [*waiting, *removed] if path not in walk]
    assert not unbound, 'Waiting path is not bound: ' + ', '.join(unbound)
    present = [path for path in removed if (pathlib.Path(root) / path).exists() or (pathlib.Path(root) / path).is_symlink()]
    assert not present, 'Removed path still exists: ' + ', '.join(present)
    # Every bound file that is neither waiting nor removed replays its walk bytes.
    kept = [row for row in union if row['path'] not in waiting and row['path'] not in removed]
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
        # Each VM rehearsal rebinds the tables of the one before it (27 after 16,
        # 22c after 27); until it records them, the earlier ones stay current.
        package=next(p for p in ('22c','27','16') if (ROOT/'os/manifest/ci'/p/'source-bindings.json').exists())
        folder=ROOT/'os/manifest/ci'/package
        walk=json.loads((folder/'host-walk.json').read_text())
        record=json.loads((folder/'source-bindings.json').read_text())
        self.assertEqual(record['package'],package)
        self.assertEqual(walk['status'],'passed')
        self.assertFalse(walk['stick_across_reboot'])
        self.assertEqual(walk['sources'],record['tables'][0]['sources'])
        self.assertIn('os/tests/test_owner_staged_release.py',{row['path'] for row in walk['sources']})
        if package!='16':
            earlier={'27':'16','22c':'27'}[package]
            old=json.loads((ROOT/'os/manifest/ci'/earlier/'source-bindings.json').read_text())
            self.assertEqual([t['name'].replace('package'+earlier,'package'+package) for t in old['tables'][1:]],
                             [t['name'] for t in record['tables'][1:]])
            # A bound file deleted in between is named in that rebind's history entry (22c: two payload scripts).
            history=json.loads(PENDING.read_text())['rebound']
            gone={path for entry in history if entry['walk']==f'os/manifest/ci/{package}/source-bindings.json'
                  for path in entry.get('removed',[])}
            for before,after in zip(old['tables'][1:],record['tables'][1:]):
                self.assertEqual([r['path'] for r in before['sources'] if r['path'] not in gone],[r['path'] for r in after['sources']])
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
        check_waiting(ROOT, union, pending_rebind(), pending_removed())
        # The recording tool finds exactly the rows the list holds.
        self.assertEqual(rebind.changed(), pending_rebind())
        self.assertEqual(rebind.removed(), pending_removed())
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
            # A deleted bound file is listed by path (22c), never silently dropped.
            (root / 'c.sh').unlink()
            with self.assertRaisesRegex(AssertionError, 'Missing or linked source: c.sh'):
                check_waiting(root, union, pending)
            check_waiting(root, union, pending, ['c.sh'])
            removed_cases = {
                'a removed path that still exists': (['a.sh'], 'still exists: a.sh'),
                'a removed path that is not bound': (['c.sh', 'e.sh'], 'not bound: e.sh'),
                'a removed path that is also waiting': (['c.sh', 'b.sh'], 'Removed path listed twice'),
                'a removed path listed twice': (['c.sh', 'c.sh'], 'Removed path listed twice'),
            }
            for label, (removed, message) in removed_cases.items():
                with self.subTest(label), self.assertRaisesRegex(AssertionError, message):
                    check_waiting(root, union, pending, removed)

    def test_a_later_rehearsals_record_step_rebinds_moves_what_waited_and_leaves_pending_working(self):
        """Brief 22c, D: `rebind.py rebind <package>`, here on a small repository of its own."""
        def write(path, value):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, indent=2) + '\n')
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as temporary:
            root = pathlib.Path(temporary)
            (root / '.gitattributes').write_bytes(b'* text=auto eol=lf\n*.ps1 text eol=crlf\n')
            for name in ('a.sh', 'b.sh', 'c.sh', 'd.ps1', 'walk.py'):
                (root / name).write_bytes(name.encode() + b'\n')
            ci = root / 'os/manifest/ci'
            first = checkout.records(root, ['a.sh', 'b.sh', 'c.sh', 'd.ps1'])
            write(ci / '27/source-bindings.json', dict(package='27', tables=[
                dict(name='package27 host walk', sources=first[:2]), dict(name='package27 rebind of x', sources=first[1:])]))
            # Since then: b.sh changed, c.sh was deleted, and the next package's walk also reads walk.py.
            (root / 'b.sh').write_bytes(b'b changed\n')
            (root / 'c.sh').unlink()
            waiting = dict(status='waiting for the next VM rehearsal', walk='os/manifest/ci/27/source-bindings.json',
                           changes=['b.sh changed', 'c.sh left the payload'], files=checkout.records(root, ['b.sh']),
                           unwalked_commands=[], rebound=[dict(status='earlier', walk='os/manifest/ci/27/source-bindings.json')],
                           removed=['c.sh'])
            write(ci / '16/pending-rebind.json', waiting)
            self.assertEqual((rebind.changed(root), rebind.removed(root)), (waiting['files'], ['c.sh']))
            walked = checkout.records(root, ['a.sh', 'b.sh', 'walk.py'])
            write(ci / '22c/host-walk.json', dict(status='passed', sources=walked))
            # What owner_vm.bound_sources records in the run: the walk's sources, then the earlier tables' files that remain.
            evidence = root / '22c-bound-sources.json'
            bound = dict(package='22c', commit='c' * 40, tables=[dict(name='package22c host walk', sources=walked),
                dict(name='package22c rebind of x', sources=checkout.records(root, ['b.sh', 'd.ps1']))])
            target = ci / '22c/source-bindings.json'
            refusals = {'another package': (dict(bound, package='27'), None),
                        'a row that is not the checkout': (dict(bound, tables=[bound['tables'][0], dict(bound['tables'][1],
                            sources=[dict(bound['tables'][1]['sources'][0], sha256='0' * 64), bound['tables'][1]['sources'][1]])]), 'binding mismatch|Conflicting'),
                        'a walk table that is not the host walk': (dict(bound, tables=[dict(bound['tables'][0], sources=walked[:2]),
                            bound['tables'][1]]), 'other sources than the host walk'),
                        'a bound file dropped without being listed': (dict(bound, tables=[bound['tables'][0],
                            dict(bound['tables'][1], sources=bound['tables'][1]['sources'][:1])]), 'without being listed as removed, or a listed one is still bound: d.ps1')}
            for label, (value, message) in refusals.items():
                write(evidence, value)
                with self.subTest(label), self.assertRaisesRegex(AssertionError, message or ''):
                    rebind.rebind('22c', evidence, '777', root)
                self.assertFalse(target.exists())
                self.assertEqual(json.loads((ci / '16/pending-rebind.json').read_text()), waiting)
            write(evidence, bound)
            with contextlib.redirect_stdout(io.StringIO()):
                rebind.rebind('22c', evidence, '777', root)
            link = 'https://github.com/Ares-Empire/AresOS/actions/runs/777'
            record = json.loads(target.read_text())
            self.assertEqual((record['package'], record['run'], record['commit'], record['tables']), ('22c', link, 'c' * 40, bound['tables']))
            # These are the active tables now, and every row replays the checkout (the CRLF-declared one too).
            self.assertEqual(checkout.active_tables(root), [(t['name'], t['sources']) for t in bound['tables']])
            after = json.loads((ci / '16/pending-rebind.json').read_text())
            self.assertEqual((after['files'], after['changes'], after['removed']), ([], [], []))
            self.assertEqual((after['status'], after['walk']), ("rebound by package 22c's rehearsal", 'os/manifest/ci/22c/source-bindings.json'))
            self.assertEqual(after['rebound'], [waiting['rebound'][0], dict(status="rebound by package 22c's rehearsal",
                waited_for='os/manifest/ci/27/source-bindings.json', walk='os/manifest/ci/22c/source-bindings.json',
                changes=waiting['changes'], files=['b.sh'], removed=['c.sh'], rebound_by=link)])
            self.assertEqual(after['unwalked_commands'], [])
            check_waiting(root, checkout.merge(checkout.active_tables(root)), [], [])
            # The list works on for the next package: a bound file changed after the record waits again.
            (root / 'walk.py').write_bytes(b'walk changed\n')
            self.assertEqual((rebind.changed(root), rebind.removed(root)), (checkout.records(root, ['walk.py']), []))
            # A second record for the same package refuses.
            with self.assertRaisesRegex(AssertionError, 'recorded its bindings already'):
                rebind.rebind('22c', evidence, '778', root)

    def test_exact_dda72ed_record_refuses_with_its_unchanged_crlf_declared_source(self):
        old = json.loads((ROOT / 'os/tests/fixtures/owner-tools/14zzd-checkout-sources.json').read_text())
        self.assertEqual(old['commit'], 'dda72ed8a5bdb038d953f950f76c66fc37297115')
        self.assertEqual(len(old['sources']), 195)
        row = next(row for row in old['sources'] if row['path'] == 'os/tests/owner-tools.Tests.ps1')
        raw = (ROOT / row['path']).read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
        # 22c took these two scripts out of the owner payload (os/release keeps them); the
        # record still refuses on its CRLF-declared row among the files that remain.
        gone = [r['path'] for r in old['sources'] if not (ROOT / r['path']).is_file()]
        self.assertEqual(gone, ['os/owner-tools/payload/release/default-stock.sh', 'os/owner-tools/payload/release/rollback.sh'])
        with self.assertRaisesRegex(AssertionError, 'os/tests/owner-tools.Tests.ps1'):
            checkout.verify(ROOT, [r for r in old['sources'] if r['path'] not in gone])

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
