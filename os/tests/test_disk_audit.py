import copy
import pathlib
import struct
import sys
import tempfile
import unittest
import uuid
import zlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from disk_audit import (AUTH_STORE, boot_entry, boot_variables, compare_disk,
                        compare_nvram, entry_target, gpt, protected_writes, set_variable, variables)


class DiskAuditTest(unittest.TestCase):
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
