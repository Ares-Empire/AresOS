import copy
import json
import pathlib
import struct
import sys
import tempfile
import unittest
import uuid
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from disk_audit import (AUTH_STORE, boot_entry, boot_variables, compare_disk,
                        compare_nvram, entry_target, gpt, protected_writes, set_variable, variables,
                        AUTO_BOOT_GUID, load_option, firmware_hardware, firmware_baseline, nvram_audit)


class DiskAuditTest(unittest.TestCase):
    def historical(self):
        root = pathlib.Path(__file__).resolve().parents[1] / 'manifest/ci/11b/probe-11/two-disk'
        before = boot_variables(root / 'baseline-firmware-vars.fd')
        after = boot_variables(root / 'probe-windows-without-linux-vars.fd')
        self.assertEqual(before, json.loads((root / 'baseline-firmware-nvram.json').read_text()))
        self.assertEqual(after, json.loads((root / 'probe-windows-without-linux-nvram.json').read_text()))
        # Recorded 11b Q35 invocation: storage slots 2/3, DVD ICH9 SATA port 0.
        previous = dict(attached=[dict(key=k) for k in ('pci:00:02.0', 'pci:00:03.0', 'pci:00:1f.2/sata:0:65535:0', 'pci:00:01.0')])
        current = dict(attached=[dict(key=k) for k in ('pci:00:02.0', 'pci:00:01.0')])
        return before, after, previous, current

    def test_probe_11_raw_stores_exempt_exactly_two_device_removals(self):
        before, after, previous, current = self.historical()
        changes = compare_nvram(before, after, before_devices=previous, after_devices=current)
        exemptions = {n: c['firmware_owned']['device'] for n, c in changes.items() if 'firmware_owned' in c}
        self.assertEqual(exemptions, {'Boot0002': 'pci:00:1f.2/sata:0:65535:0', 'Boot0004': 'pci:00:03.0'})
        self.assertEqual(load_option(bytes.fromhex(before['Boot0000']['hex']))['optional'], b'')
        for name in exemptions:
            self.assertEqual(load_option(bytes.fromhex(before[name]['hex']))['optional'], AUTO_BOOT_GUID)

    def test_each_boot_requires_all_remaining_auto_devices_attached_not_a_label(self):
        before, after, previous, current = self.historical()
        for still_attached in ('pci:00:03.0', 'pci:00:1f.2/sata:0:65535:0'):
            wrong = copy.deepcopy(current)
            wrong['attached'].append(dict(key=still_attached))
            # 11e explicitly permits an attached device to lose its auto option.
            with self.subTest(device=still_attached):
                compare_nvram(before, after, before_devices=previous, after_devices=wrong)
        wrong = copy.deepcopy(previous)
        wrong['attached'] = [d for d in wrong['attached'] if d['key'] != 'pci:00:03.0']
        with self.assertRaises(AssertionError):
            compare_nvram(before, after, before_devices=wrong, after_devices=current)

    def test_every_non_exempt_mutation_remains_a_failure(self):
        before, after, previous, current = self.historical()
        for case in ('windows-lost', 'windows-changed', 'windows-auto', 'non-auto-removed', 'unknown-addition', 'guid-extra', 'wrong-path'):
            first, last = copy.deepcopy(before), copy.deepcopy(after)
            if case == 'windows-lost':
                del last['Boot0000']
            elif case in ('windows-changed', 'windows-auto'):
                last['Boot0000']['hex'] += (AUTO_BOOT_GUID if case == 'windows-auto' else b'x').hex()
            elif case == 'non-auto-removed':
                first['Boot0004']['hex'] = first['Boot0004']['hex'][:-32]
            elif case == 'unknown-addition':
                last['Boot0009'] = copy.deepcopy(first['Boot0000'])
            elif case == 'guid-extra':
                first['Boot0004']['hex'] += '00'
            else:
                raw = bytes.fromhex(first['Boot0004']['hex'])
                raw = raw.replace(b'\x01\x01\x06\0\0\x03', b'\x01\x01\x06\0\0\x0a')
                first['Boot0004']['hex'] = raw.hex()
            with self.subTest(case=case), self.assertRaises(AssertionError):
                compare_nvram(first, last, before_devices=previous, after_devices=current)

    def test_auto_addition_requires_attached_device(self):
        before, after, previous, current = self.historical()
        restored = copy.deepcopy(after)
        restored['Boot0004'] = before['Boot0004']
        changes = compare_nvram(after, restored, before_devices=current, after_devices=previous)
        self.assertEqual(changes['Boot0004']['firmware_owned']['device'], 'pci:00:03.0')
        with self.assertRaisesRegex(AssertionError, 'detached or unknown device'):
            compare_nvram(after, restored, before_devices=current, after_devices=current)

    def test_only_target_linux_addition_can_precede_windows_during_install(self):
        before, after, previous, current = self.historical()
        raw = bytes.fromhex(after['BootOrder']['hex'])
        after['BootOrder']['hex'] = (raw[2:4] + raw[:2] + raw[4:]).hex()
        with self.assertRaisesRegex(AssertionError, 'Windows is not first'):
            compare_nvram(before, after, before_devices=previous, after_devices=current)
        partition = dict(number=1, start_lba=2048, end_lba=4095, guid=str(uuid.uuid4()))
        esp = dict(partition, bytes=2048 * 512)
        linux = copy.deepcopy(before)
        linux['Boot0099'] = dict(attributes=7, hex=boot_entry(partition, 'Fedora', '\\EFI\\fedora\\shimx64.efi').hex())
        linux['BootOrder']['hex'] = '9900' + linux['BootOrder']['hex']
        compare_nvram(before, linux, before_devices=previous, after_devices=previous, target_esp=esp, windows_first=False)
        with self.assertRaisesRegex(AssertionError, 'target ESP'):
            compare_nvram(before, linux, before_devices=previous, after_devices=previous,
                          target_esp=dict(esp, guid=str(uuid.uuid4())), windows_first=False)

    def test_real_11d_reverse_stores_record_exactly_three_device_changes(self):
        root = pathlib.Path(__file__).resolve().parents[1] / 'manifest/ci/11d/probe-3/two-disk/protected-second'
        stores = [boot_variables(root / (stage + '-vars.fd')) for stage in
                  ('live-ui-probe', 'probe-windows-without-linux')]
        devices = [json.loads((root / (stage + '-devices.json')).read_text()) for stage in
                   ('live-ui-probe', 'probe-windows-without-linux')]
        result = nvram_audit(*stores, before_devices=devices[0], after_devices=devices[1])
        events = result['firmware_changes']
        self.assertEqual([(e['device'], e['before_option'], e['after_option']) for e in events], [
            ('pci:00:02.0', 'Boot0003', None),
            ('pci:00:03.0', 'Boot0004', 'Boot0002'),
            ('pci:00:1f.2/sata:0:65535:0', 'Boot0002', None)])
        self.assertTrue(events[1]['relabeled'] and events[1]['renumbered'])
        self.assertEqual(len(events), 3)
        self.assertEqual(set(result['firmware_before']), {f'Boot{i:04X}' for i in range(2, 9)})
        self.assertTrue(all(item['device'] == 'pci:00:01.0' for name, item in result['firmware_before'].items()
                            if name in ('Boot0005', 'Boot0006', 'Boot0007', 'Boot0008')))
        self.assertEqual(stores[0]['Boot0000'], stores[1]['Boot0000'])

    def test_11d_first_order_stores_still_record_only_the_two_removals(self):
        root = pathlib.Path(__file__).resolve().parents[1] / 'manifest/ci/11d/probe-3/two-disk'
        stages = ('live-ui-probe', 'probe-windows-without-linux')
        result = nvram_audit(*(boot_variables(root / (s + '-vars.fd')) for s in stages),
            before_devices=json.loads((root / (stages[0] + '-devices.json')).read_text()),
            after_devices=json.loads((root / (stages[1] + '-devices.json')).read_text()))
        self.assertEqual({(e['before_option'], e['after_option']) for e in result['firmware_changes']},
                         {('Boot0002', None), ('Boot0004', None)})

    def test_auto_device_sets_allow_relabels_missing_options_and_order_positions(self):
        before, _, devices, _ = self.historical()
        after = copy.deepcopy(before)
        raw = bytes.fromhex(after['Boot0004']['hex'])
        after['Boot0004']['hex'] = raw.replace('UEFI Misc Device 2'.encode('utf-16le'),
                                              'New firmware label'.encode('utf-16le')).hex()
        order = bytes.fromhex(after['BootOrder']['hex'])
        numbers = list(struct.unpack('<' + 'H' * (len(order) // 2), order))
        fixed = [n for n in numbers if n in (0, 1, 9)]
        auto = [n for n in numbers if n not in fixed]
        after['BootOrder']['hex'] = struct.pack('<' + 'H' * len(numbers), *fixed, *reversed(auto)).hex()
        result = nvram_audit(before, after, before_devices=devices, after_devices=devices)
        self.assertEqual(len(result['firmware_changes']), 1)
        self.assertTrue(result['firmware_changes'][0]['relabeled'])
        self.assertEqual(result['order_before'][0], 'Boot0000')
        self.assertEqual(result['order_after'][0], 'Boot0000')
        for name in result['firmware_after']:
            del after[name]
        after['BootOrder']['hex'] = struct.pack('<HHH', *fixed).hex()
        compare_nvram(before, after, before_devices=devices, after_devices=devices)

    def test_unchanged_auto_options_for_detached_or_unknown_devices_also_fail(self):
        before, _, devices, _ = self.historical()
        for missing in ('pci:00:03.0', 'pci:00:01.0', 'pci:00:1f.2/sata:0:65535:0'):
            wrong = dict(attached=[d for d in devices['attached'] if d['key'] != missing])
            with self.subTest(device=missing), self.assertRaisesRegex(AssertionError, 'detached or unknown device'):
                compare_nvram(before, before, before_devices=devices, after_devices=wrong)
        wrong = copy.deepcopy(before)
        wrong['Boot0007']['hex'] += '00'
        with self.assertRaisesRegex(AssertionError, 'not exactly'):
            compare_nvram(wrong, wrong, before_devices=devices, after_devices=devices)

    def linux_fixture(self):
        before, _, devices, _ = self.historical()
        part = dict(number=1, start_lba=2048, end_lba=4095, guid=str(uuid.uuid4()))
        esp = dict(part, bytes=2048 * 512)
        before['Boot0099'] = dict(attributes=7, hex=boot_entry(part, 'Fedora', '\\EFI\\fedora\\shimx64.efi').hex())
        before['BootOrder']['hex'] += '9900'
        return before, devices, part, esp

    def test_firmware_cannot_take_windows_linux_or_other_fixed_entry_number(self):
        before, devices, _, esp = self.linux_fixture()
        for name in ('Boot0000', 'Boot0099', 'Boot0001'):
            after = copy.deepcopy(before)
            after[name] = before['Boot0004']
            with self.subTest(number=name), self.assertRaises(AssertionError):
                compare_nvram(before, after, before_devices=devices, after_devices=devices, target_esp=esp)

    def test_windows_number_first_and_all_other_fixed_entries_stay_strict(self):
        before, _, devices, _ = self.historical()
        for case in ('renumbered', 'not-first', 'fixed-changed', 'fixed-added', 'fixed-reordered'):
            after = copy.deepcopy(before)
            if case == 'renumbered':
                after['Boot0098'] = after.pop('Boot0000')
                after['BootOrder']['hex'] = '9800' + after['BootOrder']['hex'][4:]
            elif case == 'not-first':
                raw = after['BootOrder']['hex']
                after['BootOrder']['hex'] = raw[4:8] + raw[:4] + raw[8:]
            elif case == 'fixed-changed':
                after['Boot0001']['attributes'] ^= 1
            elif case == 'fixed-added':
                after['Boot0098'] = after['Boot0001']
            else:
                after['BootOrder']['hex'] = after['BootOrder']['hex'].replace('0100', 'ff00').replace('0900', '0100').replace('ff00', '0900')
            with self.subTest(case=case), self.assertRaises(AssertionError):
                compare_nvram(before, after, before_devices=devices, after_devices=devices)

    def test_linux_change_and_recreation_require_only_target_esp_and_fedora_loader(self):
        before, devices, part, esp = self.linux_fixture()
        changed = copy.deepcopy(before)
        changed['Boot0099']['hex'] = boot_entry(part, 'Bazzite', '\\EFI\\fedora\\grubx64.efi').hex()
        compare_nvram(before, changed, before_devices=devices, after_devices=devices, target_esp=esp)
        changed['Boot0098'] = changed.pop('Boot0099')
        changed['BootOrder']['hex'] = changed['BootOrder']['hex'].replace('9900', '9800')
        compare_nvram(before, changed, before_devices=devices, after_devices=devices, target_esp=esp)
        for wrong_part, path in ((dict(part, guid=str(uuid.uuid4())), '\\EFI\\fedora\\shimx64.efi'),
                                 (part, '\\EFI\\Microsoft\\Boot\\bootmgfw.efi')):
            wrong = copy.deepcopy(before)
            wrong['Boot0099']['hex'] = boot_entry(wrong_part, 'Fedora', path).hex()
            with self.assertRaises(AssertionError):
                compare_nvram(before, wrong, before_devices=devices, after_devices=devices, target_esp=esp)
        removed = copy.deepcopy(before)
        del removed['Boot0099']
        removed['BootOrder']['hex'] = removed['BootOrder']['hex'][:-4]
        with self.assertRaisesRegex(AssertionError, 'without target-ESP recreation'):
            compare_nvram(before, removed, before_devices=devices, after_devices=devices, target_esp=esp)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name)

    def store(self):
        path = self.directory / 'vars.fd'
        path.write_bytes(AUTH_STORE + struct.pack('<IBBHI', 4096, 0x5a, 0xfe, 0, 0) + b'\xff' * (4096 - 28))
        return path

    def test_real_edk2_records_replace_deleted_values_and_preserve_windows_payload(self):
        path = self.store()
        partition = dict(number=1, start_lba=2048, end_lba=534527, guid=str(uuid.uuid4()))
        windows = boot_entry(partition)
        set_variable(path, 'Boot0000', windows)
        set_variable(path, 'BootOrder', b'\0\0')
        before = boot_variables(path)
        set_variable(path, 'Boot0001', boot_entry(partition, 'Fedora', '\\EFI\\fedora\\shimx64.efi'))
        set_variable(path, 'BootOrder', b'\x01\0\0\0')
        set_variable(path, 'BootNext', b'\x01\0')
        after = boot_variables(path)
        self.assertEqual(after['Boot0000']['hex'], windows.hex())
        self.assertEqual(after['BootOrder']['hex'], '01000000')
        self.assertEqual(set(compare_nvram(before, after, target_esp=dict(partition, bytes=532480 * 512),
                                         windows_first=False)), {'Boot0001', 'BootOrder', 'BootNext'})
        self.assertEqual(len(variables(path.read_bytes())[0]), 4)

    def test_lost_modified_or_unordered_windows_and_non_linux_addition_fail(self):
        path = self.store()
        part = dict(number=1, start_lba=2048, end_lba=534527, guid=str(uuid.uuid4()))
        set_variable(path, 'Boot0000', boot_entry(part))
        set_variable(path, 'BootOrder', b'\0\0')
        before = boot_variables(path)
        for variant in ('lost', 'changed', 'order', 'other'):
            after = copy.deepcopy(before)
            if variant == 'lost':
                del after['Boot0000']
            elif variant == 'changed':
                after['Boot0000']['hex'] = boot_entry(part, filename='\\EFI\\Boot\\bootx64.efi').hex()
            elif variant == 'order':
                after['BootOrder']['hex'] = '0100'
            else:
                after['Boot0002'] = dict(attributes=7, hex=boot_entry(part, 'Unexpected').hex())
            with self.subTest(variant=variant), self.assertRaises(AssertionError):
                compare_nvram(before, after)

    def test_write_even_if_bytes_later_restored_or_device_missing_is_a_failure(self):
        stats = [dict(device='protected', stats=dict(wr_bytes=0, wr_operations=0))]
        self.assertEqual(protected_writes(stats), dict(wr_bytes=0, wr_operations=0))
        for field in ('wr_bytes', 'wr_operations'):
            changed = copy.deepcopy(stats)
            changed[0]['stats'][field] = 1
            with self.assertRaisesRegex(AssertionError, 'PRODUCT FAILURE'):
                protected_writes(changed)
        for changed in ([], stats + stats):
            with self.assertRaises(AssertionError):
                protected_writes(changed)

    def test_efi_entry_resolves_gpt_partition_guid_boundaries_and_actual_loader(self):
        part = dict(number=1, start_lba=2048, end_lba=534527, guid=str(uuid.uuid4()))
        parsed = entry_target(boot_entry(part))
        self.assertEqual(parsed['partition'], dict(number=1, start_lba=2048, sectors=532480, guid=part['guid']))
        self.assertEqual(parsed['file'], '\\EFI\\Microsoft\\Boot\\bootmgfw.efi')
        raw = boot_entry(part)
        for wrong in (raw[:10], raw[:-4]):
            with self.assertRaises((AssertionError, UnicodeError, struct.error)):
                entry_target(wrong)

    def disk(self):
        path = self.directory / 'protected.raw'
        raw = bytearray(128 * 512)
        table = bytearray(128 * 4)
        table[:16] = uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b').bytes_le
        table[16:32] = uuid.uuid4().bytes_le
        struct.pack_into('<QQQ', table, 32, 8, 119, 0)
        raw[2 * 512:3 * 512] = table
        raw[126 * 512:127 * 512] = table
        guid = uuid.uuid4().bytes_le
        for current, other, entries in ((1, 127, 2), (127, 1, 126)):
            header = bytearray(512)
            struct.pack_into('<8sIIIIQQQQ16sQIII', header, 0, b'EFI PART', 0x10000, 92, 0, 0,
                             current, other, 8, 119, guid, entries, 4, 128, zlib.crc32(table))
            struct.pack_into('<I', header, 16, zlib.crc32(header[:92]))
            raw[current * 512:(current + 1) * 512] = header
        path.write_bytes(raw)
        return path

    def test_gpt_checks_primary_backup_crc_identity_and_exact_boundaries(self):
        path = self.disk()
        parsed = gpt(path)
        self.assertEqual(parsed['partitions'][0]['start_lba'], 8)
        self.assertEqual(parsed['partitions'][0]['end_lba'], 119)
        original = path.read_bytes()
        for offset in (512 + 56, 1024 + 16, 126 * 512 + 32, 127 * 512 + 16):
            changed = bytearray(original)
            changed[offset] ^= 1
            path.write_bytes(changed)
            with self.subTest(offset=offset), self.assertRaises(AssertionError):
                gpt(path)

    def test_any_offline_disk_gpt_or_efi_difference_fails(self):
        before = dict(sha256='whole-disk', gpt=dict(guid='disk', start=2048),
                      efi_files={'fallback': 'hash'}, offline=True)
        compare_disk(before, copy.deepcopy(before))
        for field in ('sha256', 'gpt', 'efi_files', 'offline'):
            after = copy.deepcopy(before)
            after[field] = 'different'
            with self.subTest(field=field), self.assertRaisesRegex(AssertionError, 'PRODUCT FAILURE'):
                compare_disk(before, after)
