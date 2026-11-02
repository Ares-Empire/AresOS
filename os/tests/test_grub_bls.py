import copy
import json
import pathlib
import sys
import unittest
from unittest.mock import Mock, call, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
from grub_bls import stock_bls_entry, StockSelectionError, confirm_menu_ocr
import two_disk_vm as vm


class GrubSelectionTest(unittest.TestCase):
    def setUp(self):
        self.entries = json.loads((ROOT / 'os/manifest/ci/11k/full-5/two-disk/protected-second/b-bls-entries.json').read_text())
        self.stock = 'aa669eff4ea5c1f97c6c816c8d5d2abb5314e9afa3b966c0100e3e65f8040c71'

    def test_retained_bare_entries_select_unique_stock_at_position_one(self):
        selected = stock_bls_entry(self.entries, self.stock)
        self.assertEqual((selected['id'], selected['menu_index']), ('ostree-1', 1))
        self.assertEqual(selected['menu_ids'][0], 'ostree-2')
        self.assertEqual(selected['menu_titles'][0], 'Bazzite (ostree:0)')

    def test_filename_number_never_becomes_the_menu_position(self):
        entries = copy.deepcopy(self.entries)
        entries[0]['id'] = 'ostree-3'
        entries[0]['content'] = entries[0]['content'].replace('version 2', 'version 3')
        entries[1]['id'] = 'ostree-2'
        entries[1]['content'] = entries[1]['content'].replace('version 1', 'version 2')
        third = dict(id='ostree-1', title='Bazzite (ostree:2)', deployment='/sysroot/ostree/deploy/default/deploy/' + 'b' * 64 + '.0',
                     content='title Bazzite (ostree:2)\nversion 1\n')
        selected = stock_bls_entry([third, *entries], self.stock)
        self.assertEqual((selected['id'], selected['menu_index']), ('ostree-2', 1))

    def test_zero_two_and_substring_checksum_matches_stop_with_specific_reasons(self):
        for entries, checksum, reason in ((self.entries, 'b' * 64, 'No BLS entry'),
                ([*self.entries, dict(self.entries[1])], self.stock, 'Several BLS entries'),
                ([dict(self.entries[1], deployment=self.entries[1]['deployment'] + 'untrusted')], self.stock, 'No BLS entry')):
            with self.subTest(reason=reason), self.assertRaisesRegex(StockSelectionError, reason):
                stock_bls_entry(entries, checksum)

    def test_version_title_and_status_order_disagreement_stop(self):
        for field, value in (('id', 'ostree-42'), ('content', self.entries[1]['content'].replace('version 1', 'version 2')),
                             ('title', 'Bazzite (ostree:0)')):
            entries = copy.deepcopy(self.entries); entries[1][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(StockSelectionError, 'position disagreement'):
                stock_bls_entry(entries, self.stock)
        with self.assertRaisesRegex(StockSelectionError, 'deployment index differs'):
            stock_bls_entry(self.entries, self.stock, [dict(checksum=self.stock), dict(checksum='b' * 64)])

    def test_ocr_disagreement_sends_no_menu_key_and_correct_lines_select_stock(self):
        backup = stock_bls_entry(self.entries, self.stock)
        right = 'GNU GRUB\n *Bazzite (ostree:0)\n  Bazzite (ostree:1)\n UEFI Firmware Settings\n'
        guest = Mock()
        for wrong in (right.replace('ostree:0', 'ostree:2'), 'Bazzite (ostree:1)\nBazzite (ostree:0)', 'GNU GRUB\nBazzite (ostree:0)'):
            with patch.object(vm, 'save'), self.assertRaisesRegex(StockSelectionError, 'OCR position disagreement'):
                vm.select_grub_menu(guest, backup, wrong)
            guest.keys.assert_not_called()
        with patch.object(vm, 'save'):
            vm.select_grub_menu(guest, backup, right)
        self.assertEqual(guest.keys.call_args_list, [call(['home']), call(['down']), call(['ret'])])
        self.assertTrue(confirm_menu_ocr(right, backup)['before_any_selection_key'])

    def test_owner_switch_block_is_exact_release_script(self):
        reference = json.loads((ROOT / 'os/manifest/release.json').read_text())['reference']
        script = (ROOT / 'os/release/switch.sh').read_text().replace('@REFERENCE@', reference).strip()
        docs = (ROOT / 'docs/INSTALL.md').read_text(encoding='utf-8')
        self.assertEqual(docs.count('```bash\nsudo /var/lib/ares/at switch\n```'), 1)
        self.assertEqual((ROOT/'os/owner-tools/payload/release/switch.sh').read_bytes(), (ROOT/'os/release/switch.sh').read_bytes())
        self.assertIn('rollbackQueued', script)
        self.assertIn('getent passwd 1001', script)


if __name__ == '__main__':
    unittest.main()
