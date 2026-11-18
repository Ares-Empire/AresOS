"""Release numbers are reference-bound data; compatibility never rewrites installed bundles."""
import contextlib
import copy
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import test_owner_update as base

ROOT, owner = base.ROOT, base.owner


def unnumbered(rows):
    return [{k: v for k, v in row.items() if k != 'number'} for row in rows]


class ReleaseNumbersTest(unittest.TestCase):
    def test_every_release_record_and_history_entry_has_its_own_integer_number(self):
        records = {}
        for path in (ROOT / 'os/manifest/releases').glob('*.json'):
            record = json.loads(path.read_text())
            self.assertIs(type(record['number']), int)
            self.assertEqual(record['number'], int(path.stem))
            records[record['reference']] = record
        value = owner.lineage(base.PAYLOAD)
        self.assertEqual(value['tools_version'], 6)
        for row in value['releases']:
            self.assertEqual(row['number'], records[row['reference']]['number'])
            self.assertEqual(row['identity'], records[row['reference']]['signature']['identity'])
        target = json.loads((base.PAYLOAD / 'release.json').read_text())
        self.assertEqual(target, json.loads((ROOT / 'os/manifest/release.json').read_text()))
        self.assertEqual((target['reference'], target['number']),
                         (value['releases'][-1]['reference'], value['releases'][-1]['number']))

    def test_old_unnumbered_histories_including_a_third_release_match_exactly(self):
        # Three entries model the future v5 laptop history without inventing an R28 record.
        for rows in (base.H13, base.H21, base.H30):
            with self.subTest(count=len(rows)), tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as folder:
                path = pathlib.Path(folder) / 'installed'
                old = unnumbered(rows)
                fingerprint = base.write_bundle(path, base.history(old, 5), old[-1])
                before = {p.relative_to(path): p.read_bytes() for p in path.rglob('*') if p.is_file()}
                version, read = owner.installed_lineage(path, fingerprint)
                self.assertEqual((version, read), (5, old))
                self.assertTrue(owner.extends(read, rows))
                self.assertTrue(owner.extends(read, [*rows, base.record(base.R99, True)]))
                for name, changed in (
                    ('reordered', list(reversed(rows))),
                    ('truncated', rows[:-1]),
                    ('reference', [dict(rows[0], reference=base.R99), *rows[1:]]),
                    ('identity', [dict(rows[0], identity=base.IDENTITY), *rows[1:]]),
                    ('daily account', [dict(rows[0], daily_wheel=True), *rows[1:]])):
                    with self.subTest(change=name):
                        if name == 'reordered' and len(rows) == 1:
                            continue
                        self.assertFalse(owner.extends(read, changed))
                self.assertEqual({p.relative_to(path): p.read_bytes() for p in path.rglob('*') if p.is_file()}, before)
                with self.assertRaises(owner.Stop):
                    owner.lineage(path)  # Compatibility is for installed data only.

    def test_missing_invalid_or_conflicting_new_numbers_refuse_before_any_install_change(self):
        cases = []
        for number in (None, True, '21', 0, -1):
            rows = copy.deepcopy(base.H21)
            if number is None:
                rows[0].pop('number')
            else:
                rows[0]['number'] = number
            cases.append((str(number), rows, rows[-1]))
        cases += [('duplicate', [base.H21[0], dict(base.H21[1], number=13)], dict(base.H21[1], number=13)),
                  ('target conflict', base.H21, dict(base.H21[-1], number=30)),
                  ('target missing', base.H21, unnumbered(base.H21)[-1]),
                  ('target boolean', base.H21, dict(base.H21[-1], number=True))]
        for name, rows, target in cases:
            with self.subTest(name=name):
                harness = base.ToolsUpdateTest()
                with harness.installation(stick=(base.history(rows, 6), target), source='folder') as (home, run, fingerprint, old, host):
                    before = harness.snapshot(home)
                    with self.assertRaises(owner.Stop):
                        run()
                    self.assertEqual(harness.snapshot(home), before)
                    self.assertFalse(any(r.get('mutation') for r in host.trace))
        # This check happens before even the first-install console prompts or destination creation.
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as folder:
            path = pathlib.Path(folder)
            target = unnumbered(base.H21)[-1]
            base.write_bundle(path / 'new', base.history(unnumbered(base.H21), 6), target)
            with patch.object(owner, 'HOME', path / 'absent'), patch.object(owner, 'settle_tools'), \
                    patch('builtins.input', side_effect=AssertionError('prompted before validating numbers')), self.assertRaises(owner.Stop):
                owner.install(path / 'new', source='stick')
            self.assertFalse((path / 'absent').exists())

    def test_numbered_installed_history_cannot_change_or_lose_its_numbers(self):
        for row in (dict(base.H13[0], number=12), unnumbered(base.H13)[0]):
            self.assertFalse(owner.extends(base.H13, [row, base.H21[-1]]))
        harness = base.ToolsUpdateTest()
        with harness.installation(installed=(base.history(base.H13, 5), base.H13[-1]),
                stick=(base.history([dict(base.H13[0], number=12), base.H21[-1]], 6), base.H21[-1]),
                source='folder') as (home, run, fingerprint, old, host):
            before = harness.snapshot(home)
            with self.assertRaisesRegex(owner.Stop, 'does not extend'):
                run()
            self.assertEqual(harness.snapshot(home), before)

    def test_unnumbered_installed_tools_upgrade_without_changing_their_retired_bytes(self):
        harness = base.ToolsUpdateTest()
        old_rows = unnumbered(base.H21)
        with harness.installation(installed=(base.history(old_rows, 5), old_rows[-1]),
                stick=(base.history(base.H30, 6), base.H30[-1]), state=base.updated(), source='folder') as (home, run, fingerprint, old, host):
            original = (home / 'tools/history.json').read_bytes()
            run()
            self.assertEqual((home / 'retired-tools' / old / 'history.json').read_bytes(), original)
            self.assertEqual(owner.lineage(home / ('tools-' + fingerprint))['releases'], base.H30)

    def test_numbered_names_and_both_fallbacks_do_not_expand_accepted_deployments(self):
        with base.route(base.pair()) as (tools, host, store):
            self.assertEqual(tools.release_name(base.release_row(base.R13)), 'AresOS 13')
            self.assertEqual(tools.release_name(base.stock_row()), 'plain Bazzite')
            self.assertEqual(tools.release_name(base.release_row(base.R99)), 'Unrecognised system ' + '99' * 6 + ' (version unknown)')
            # A familiar digest with the wrong reference is not a number match.
            bad = base.release_row(base.R13)
            bad['container-image-reference'] = 'ghcr.io/other/aresos@' + base.R13.split('@')[1]
            self.assertEqual(tools.release_name(bad), 'Unrecognised system ' + base.R13.split(':')[-1][:12] + ' (version unknown)')
            host.state = base.pair(base.R99)
            with self.assertRaises(owner.Stop), contextlib.redirect_stdout(io.StringIO()):
                tools.newest()
            self.assertFalse(host.changes)

    def test_version4_refuses_newest_before_running_any_handler(self):
        code = subprocess.check_output(['git', 'show', '7dd5588c:os/owner-tools/payload/owner.py'], cwd=ROOT)
        old = types.ModuleType('owner_v4')
        old.__file__ = str(base.PAYLOAD / 'owner.py')
        exec(compile(code, 'v4-owner.py', 'exec'), old.__dict__)
        with patch.object(old.os, 'geteuid', return_value=0), patch.object(old, 'owner_lock', return_value=None), \
                patch.object(old, 'settle_tools'), patch.object(old, 'checked_bundle', return_value='a' * 64), \
                patch.object(old, 'refusal_record'), patch.object(sys, 'argv', ['owner.py', 'newest']), \
                self.assertRaisesRegex(old.Stop, '^Choose a documented owner command$'):
            old.main()


if __name__ == '__main__':
    unittest.main()
