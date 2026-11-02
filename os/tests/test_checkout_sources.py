"""Real Git checkout bytes, including the accepted probe33 negative control."""
import hashlib
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import checkout_sources as checkout


class CheckoutSourcesTest(unittest.TestCase):
    def test_package16_receipts_agree_and_package14_stays_historical(self):
        folder=ROOT/'os/manifest/ci/16'
        walk=json.loads((folder/'host-walk.json').read_text())
        record=json.loads((folder/'source-bindings.json').read_text())
        self.assertEqual(record['package'],'16')
        self.assertEqual(walk['status'],'passed')
        self.assertFalse(walk['stick_across_reboot'])
        self.assertEqual(walk['sources'],record['tables'][0]['sources'])
        self.assertIn('os/tests/test_owner_staged_release.py',{row['path'] for row in walk['sources']})
        legacy=json.loads((ROOT/'os/manifest/ci/14/host-walk/result.json').read_text())
        self.assertNotEqual(walk['sources'],legacy['sources'])
        self.assertTrue(legacy['current_verification'].startswith('os/manifest/ci/14/'))

    def test_every_active_source_binding_replays_checkout_including_crlf(self):
        tables = checkout.active_tables(ROOT)
        self.assertGreaterEqual(len(tables), 4)
        union = checkout.merge(tables)
        self.assertEqual(checkout.verify(ROOT, union), len(union))
        rows = tables[0][1]
        powershell = next(row for row in rows if row['path'] == 'os/tests/owner-tools.Tests.ps1')
        raw = (ROOT / powershell['path']).read_bytes().replace(b'\r\n', b'\n')
        self.assertEqual(powershell['sha256'], hashlib.sha256(raw.replace(b'\n', b'\r\n')).hexdigest())
        self.assertNotEqual(powershell['sha256'], hashlib.sha256(raw).hexdigest())

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
