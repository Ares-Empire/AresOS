"""Real Git checkout bytes, including the accepted probe33 negative control."""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import re
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
STATUS = ROOT / 'docs/INSTALL-STATUS.md'
SUMS = ROOT / 'os/owner-tools/payload/SHA256SUMS'
# A status row that rests on a VM rehearsal the laptop has not run yet (packages 22c and 22d).
REHEARSED = 'VM REHEARSAL PASSED; NOT ON THE LAPTOP'
# While such a row stands, only these may wait (package 22c's review 8, finding 3). A tool, release
# script, guide, harness or anything else bound that waits is something the rehearsal did not run.
MAY_WAIT = ('os/tests/', '.github/workflows/')
# The field of each rehearsal's result (its run's *-rehearsal-result.json) that names the tools it rehearsed.
REHEARSED_TOOLS = {'22c': 'tools_version_3', '22d': 'tools'}


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


def rehearsed_rows(status):
    """{package: row} for each row of docs/INSTALL-STATUS.md whose status cell says REHEARSED."""
    rows = {}
    for line in status.splitlines():
        cells = line.split('|')
        if len(cells) < 5 or REHEARSED not in cells[2]:
            continue
        package = re.findall(r'\(package ([0-9]+[a-z]*)\)', cells[1])
        assert len(package) == 1, f'A status row says {REHEARSED} but names no single package: {cells[1].strip()}'
        rows[package[0]] = line
    return rows


def active_record(root):
    """The source-bindings.json whose tables checkout.active_tables returns: the newest rehearsal's."""
    tables = checkout.active_tables(root)
    records = [json.loads(path.read_text()) for path in sorted((root / 'os/manifest/ci').glob('*/source-bindings.json'))]
    found = [record for record in records if [(t['name'], t['sources']) for t in record['tables']] == tables]
    assert len(found) == 1, f'{len(found)} binding records hold the active tables, not one'
    return found[0]


def rehearsal_result(root, run):
    """The committed result of rehearsal run <run>: reviews/<package>/runs/<mode>-<run>/<mode>-rehearsal-result.json."""
    found = sorted((root / 'reviews').glob(f'*/runs/*-{run}/*-rehearsal-result.json'))
    assert len(found) == 1, f'Rehearsal run {run} has {len(found)} committed results, not one'
    return json.loads(found[0].read_text())


def check_rehearsed_rows(status, waiting, active, result_of, payload):
    """A status row that says REHEARSED promises the laptop what that VM rehearsal ran (package 22c's
    review 8, finding 3). While one stands, no file waits on the list but test files and the CI workflow,
    and the newest rehearsal (the one whose bindings are active) rehearsed exactly the payload's tools.
    Every such row names one rehearsal run and the tools fingerprint its result names, so 22c's row is
    held like 22d's; only the newest rehearsal's row is held to the payload, since the later rehearsal
    took over from the earlier one (22c's version 3 never goes on the laptop; 22d's version 4 does).

    status: docs/INSTALL-STATUS.md's text; waiting: the list's paths (files and removed); active: the
    active bindings' record; result_of(run id): that run's committed result; payload: sha256(SHA256SUMS).
    """
    rows = rehearsed_rows(status)
    if not rows:
        return
    move_on = (f'Rehearse again (a VM run of the route, then its record step), or move the row on: it may say '
               f'"{REHEARSED}" only while the laptop would get exactly what that rehearsal ran')
    says = f"docs/INSTALL-STATUS.md's row for package {{}} says {REHEARSED}"
    unrehearsed = [path for path in waiting if not path.startswith(MAY_WAIT)]
    assert not unrehearsed, (
        (says.format(*rows) if len(rows) == 1 else f"docs/INSTALL-STATUS.md's rows for packages "
         f"{' and '.join(sorted(rows))} say {REHEARSED}") + f', but these bound files changed since the last VM rehearsal '
        f'({active["run"]}) and wait on os/manifest/ci/16/pending-rebind.json: {", ".join(unrehearsed)}. While '
        f'such a row stands only test files and the CI workflow may wait. {move_on}.')
    for package, row in rows.items():
        runs = re.findall(r'\[rehearsal run (\d+)\]', row)
        assert len(runs) == 1, says.format(package) + f' but names {len(runs)} "[rehearsal run <id>]" links, not one'
        assert package in REHEARSED_TOOLS, says.format(package) + (
            ': add the field of its result that names the tools it rehearsed to REHEARSED_TOOLS (test_checkout_sources.py)')
        result = result_of(runs[0])
        field = REHEARSED_TOOLS[package]
        assert field in result, says.format(package) + f', but the result of run {runs[0]} names no {field}'
        rehearsed = result[field]
        assert result['status'] == 'passed', says.format(package) + f', but run {runs[0]} did not pass'
        named = re.findall(r'Tools fingerprint `([0-9a-f]{8,64})', row)
        assert len(named) == 1 and rehearsed.startswith(named[0]), says.format(package) + (
            f' and names tools fingerprint {named}, but its run {runs[0]} rehearsed {rehearsed}')
        if package != active['package']:
            continue
        assert active['run'].endswith('/' + runs[0]) and result['commit'] == active['commit'], says.format(package) + (
            f' with run {runs[0]} on {result["commit"]}, but the active bindings are run {active["run"]} on {active["commit"]}')
        assert rehearsed == payload, says.format(package) + (
            f', but the tools changed since: run {runs[0]} rehearsed tools fingerprint {rehearsed}, and '
            f'os/owner-tools/payload/SHA256SUMS now hashes to {payload}. {move_on}.')


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

    def test_a_row_that_says_vm_rehearsal_passed_holds_only_what_the_rehearsal_ran(self):
        # Package 22c's review 8, finding 3: until the laptop runs it, no tool or guide change hides on the list.
        check_rehearsed_rows(STATUS.read_text(), [row['path'] for row in pending_rebind()] + pending_removed(),
                             active_record(ROOT), lambda run: rehearsal_result(ROOT, run),
                             hashlib.sha256(SUMS.read_bytes()).hexdigest())

    def test_a_rehearsed_row_refuses_waiting_tools_or_guides_and_other_tools(self):
        payload, older = 'd' * 64, 'a' * 64
        def row(package, run, fingerprint, status=REHEARSED):
            return (f'| Route (package {package}) | **BUILT AND REVIEWED; {status}** | **x** | Tools fingerprint '
                    f'`{fingerprint}` ... passed in [rehearsal run {run}](https://github.com/x/actions/runs/{run}) |')
        status = '\n'.join(['| What | Status | Scope | Notes |', '| --- | --- | --- | --- |',
                            row('22c', 1, older[:8] + '…'), row('22d', 2, payload)])
        active = dict(package='22d', run='https://github.com/x/actions/runs/2', commit='c' * 40)
        results = {'1': dict(status='passed', commit='b' * 40, tools_version_3=older),
                   '2': dict(status='passed', commit='c' * 40, tools=payload)}
        waiting = ['os/tests/test_owner_path.py', '.github/workflows/os-image.yml']
        self.assertEqual(set(rehearsed_rows(status)), {'22c', '22d'})
        check_rehearsed_rows(status, waiting, active, results.get, payload)
        say = 'docs/INSTALL-STATUS.md.s rows for packages 22c and 22d say ' + REHEARSED
        cases = {
            'a tool waits': (status, waiting + ['os/owner-tools/owner.py'], results, payload, say + '.*owner.py.*Rehearse again'),
            'a guide waits': (status, waiting + ['docs/INSTALL.md'], results, payload, say + '.*docs/INSTALL.md'),
            'a release script waits': (status, waiting + ['os/release/switch.sh'], results, payload, 'os/release/switch.sh'),
            'the harness waits': (status, waiting + ['os/ci/owner_vm.py'], results, payload, 'os/ci/owner_vm.py'),
            'other tools than the rehearsal ran': (status, waiting, results, 'e' * 64,
                                                   'the tools changed since: run 2 rehearsed tools fingerprint d{64}, and '
                                                   'os/owner-tools/payload/SHA256SUMS now hashes to e{64}.*move the row on'),
            'a row naming other tools than its run': (status.replace(older[:8], 'f' * 8), waiting, results, payload,
                                                      'package 22c says.*names tools fingerprint'),
            'a row naming another run than the active bindings': (status.replace('rehearsal run 2]', 'rehearsal run 1]'),
                waiting, dict(results, **{'1': dict(results['1'], tools=payload)}), payload, 'the active bindings are run'),
            'a run that did not pass': (status, waiting, dict(results, **{'1': dict(results['1'], status='failed')}),
                                        payload, 'run 1 did not pass'),
            'a row without its package': (status.replace('(package 22c)', ''), waiting, results, payload, 'names no single package'),
            'a result without the tools it rehearsed': (status, waiting, dict(results, **{'2': {
                key: value for key, value in results['2'].items() if key != 'tools'}}), payload, 'run 2 names no tools'),
        }
        for label, (text, paths, found, sums, message) in cases.items():
            with self.subTest(label), self.assertRaisesRegex(AssertionError, message):
                check_rehearsed_rows(text, paths, active, found.get, sums)
        # Once the rows move on (the laptop runs it), later tool and guide changes may wait again.
        moved = status.replace(REHEARSED, 'VM REHEARSAL PASSED; ON THE LAPTOP 2026-11-20')
        self.assertEqual(rehearsed_rows(moved), {})
        check_rehearsed_rows(moved, waiting + ['os/owner-tools/owner.py', 'docs/INSTALL.md'], active, results.get, 'e' * 64)

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
