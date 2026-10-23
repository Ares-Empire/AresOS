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
                        AUTO_BOOT_GUID, load_option, firmware_hardware, firmware_baseline)


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

    def test_auto_removal_requires_the_exact_detached_hardware_not_its_label(self):
        before, after, previous, current = self.historical()
        for still_attached in ('pci:00:03.0', 'pci:00:1f.2/sata:0:65535:0'):
            wrong = copy.deepcopy(current)
            wrong['attached'].append(dict(key=still_attached))
            with self.subTest(device=still_attached), self.assertRaisesRegex(AssertionError, 'detached device'):
                compare_nvram(before, after, before_devices=previous, after_devices=wrong)
        wrong = copy.deepcopy(previous)
        wrong['attached'] = [d for d in wrong['attached'] if d['key'] != 'pci:00:03.0']
        with self.assertRaises(AssertionError):
            compare_nvram(before, after, before_devices=wrong, after_devices=current)

    def test_every_non_exempt_mutation_remains_a_failure(self):
        before, after, previous, current = self.historical()
        for case in ('windows-lost', 'windows-changed', 'windows-auto', 'non-auto-removed', 'unknown-addition', 'guid-extra', 'auto-changed', 'wrong-path'):
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
            elif case == 'auto-changed':
                last['Boot0004'] = dict(first['Boot0004'], attributes=99)
            else:
                raw = bytes.fromhex(first['Boot0004']['hex'])
                raw = raw.replace(b'\x01\x01\x06\0\0\x03', b'\x01\x01\x06\0\0\x02')
                first['Boot0004']['hex'] = raw.hex()
            with self.subTest(case=case), self.assertRaises(AssertionError):
                compare_nvram(first, last, before_devices=previous, after_devices=current)

    def test_auto_addition_requires_attached_device_and_cannot_change_existing_entry(self):
        before, after, previous, current = self.historical()
        restored = copy.deepcopy(after)
        restored['Boot0004'] = before['Boot0004']
        changes = compare_nvram(after, restored, before_devices=current, after_devices=previous)
        self.assertEqual(changes['Boot0004']['firmware_owned']['device'], 'pci:00:03.0')
        with self.assertRaisesRegex(AssertionError, 'attached device'):
            compare_nvram(after, restored, before_devices=current, after_devices=current)

    def test_only_linux_reordering_and_the_target_esp_are_permitted(self):
        before, after, previous, current = self.historical()
        raw = bytes.fromhex(after['BootOrder']['hex'])
        after['BootOrder']['hex'] = (raw[2:4] + raw[:2] + raw[4:]).hex()
        with self.assertRaisesRegex(AssertionError, 'BootOrder changed'):
            compare_nvram(before, after, before_devices=previous, after_devices=current)
        partition = dict(number=1, start_lba=2048, end_lba=4095, guid=str(uuid.uuid4()))
        esp = dict(partition, bytes=2048 * 512)
        linux = copy.deepcopy(before)
        linux['Boot0099'] = dict(attributes=7, hex=boot_entry(partition, 'Fedora', '\\EFI\\fedora\\shimx64.efi').hex())
        linux['BootOrder']['hex'] = '9900' + linux['BootOrder']['hex']
        compare_nvram(before, linux, before_devices=previous, after_devices=previous, target_esp=esp)
        with self.assertRaisesRegex(AssertionError, 'target ESP'):
            compare_nvram(before, linux, before_devices=previous, after_devices=previous,
                          target_esp=dict(esp, guid=str(uuid.uuid4())))

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
        self.assertEqual(set(compare_nvram(before, after)), {'Boot0001', 'BootOrder', 'BootNext'})
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
