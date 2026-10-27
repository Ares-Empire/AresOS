"""Pinned formatter grammar and retained load-option inputs; no EFI access."""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import uuid
import unittest
from unittest.mock import patch

import test_owner_tools as common

ROOT, owner = common.ROOT, common.owner
sys.path.insert(0, str(ROOT/'os/ci'))
from owner_devices import fixture_firmware

FIXTURES = ROOT/'os/tests/fixtures/owner-tools'
GUID = '4fb134e0-52b2-413d-a5e0-d83b1dec6ffe'


class FirmwareTest(unittest.TestCase):
    def setUp(self):
        self.text = (FIXTURES/'efibootmgr18-efivar39.txt').read_text()

    def refuse(self, text):
        with patch('subprocess.run') as run, patch('subprocess.Popen') as popen, \
             self.assertRaises((owner.Stop, ValueError)):
            owner.firmware_entry(text, GUID)
        run.assert_not_called(); popen.assert_not_called()

    def test_reconstructed_retained_option_and_every_fixture_hash_are_bound(self):
        sources = json.loads((FIXTURES/'tool-output-sources.json').read_text())
        for row in sources:
            self.assertEqual(list(row)[:2], ['sha256', 'path'])
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(), row['sha256'])
        result = owner.firmware_entry(self.text, GUID.upper())
        self.assertEqual(result['number'], '000A')
        self.assertEqual(result['path'], '\\EFI\\fedora\\shimx64.efi')

    def test_legacy_file_wrapper_active_inactive_and_hex_case(self):
        line = self.text.splitlines()[0]
        legacy = line.replace('/\\EFI\\fedora\\shimx64.efi', '/File(\\EFI\\fedora\\shimx64.efi)')
        for text in (line, legacy, legacy.replace('Boot000A*', 'Boot000A '),
                     self.text.replace(GUID, GUID.upper())):
            self.assertEqual(owner.firmware_entry(text, GUID)['number'], '000A')

    def test_firmware_warning_stops_and_retains_raw_stdout_and_stderr(self):
        host = owner.Host()
        result = subprocess.CompletedProcess([], 0, self.text, 'Skipping unreadable variable\n')
        with patch.object(owner.shutil,'which',return_value='/usr/bin/efibootmgr'), \
             patch.object(owner.subprocess,'run',return_value=result), self.assertRaisesRegex(owner.Stop,'wrote stderr'):
            host.read('efibootmgr','-v')
        self.assertEqual(host.trace[-1]['stdout'], self.text)
        self.assertEqual(host.trace[-1]['stderr'], result.stderr)
        self.assertFalse(host.trace[-1]['mutation'])

    def test_real_source_native_fixture_and_unrelated_firmware_options(self):
        windows = fixture_firmware('10000001-1111-2222-3333-444444444444').replace('Boot0001', 'Boot0000').replace('Fixture Linux', 'Windows Boot Manager')
        # Source format for a non-HD OVMF option with its 16-byte automatic GUID.
        fv = b'\x04\x06\x14\0'+uuid.UUID('7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1').bytes_le
        other = ('Boot0002* UiApp\tFvFile(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1){8108ac4e-9f11-4d59-850e-e21a522c59b2}\n      dp: '
            +fv.hex(' ')+' / 7f ff 04 00\n    data: 4e ac 08 81 11 9f 59 4d 85 0e e2 1a 52 2c 59 b2\n')
        text = 'BootCurrent: 000A\nTimeout: 1 seconds\nBootOrder: 0000,000A,0002\n'+windows+self.text+other
        self.assertEqual(owner.firmware_entry(text, GUID)['number'], '000A')

    def test_optional_data_never_becomes_an_hd_or_file_node(self):
        optional = b'HD(1,GPT,'+GUID.encode()+b',0x800,0x10)/File(\\EFI\\fake.efi)'
        lines = self.text.splitlines()
        text = lines[0]+optional.decode()+'\n'+lines[1]+'\n    data: '+optional.hex(' ')+'\n'
        self.assertEqual(owner.firmware_entry(text, GUID)['number'], '000A')
        # With no byte boundary this is ambiguous; without an HD node it can
        # never be accepted merely because OptionalData contains the GUID.
        self.refuse(lines[0]+optional.decode())
        self.refuse('Boot000A* Fake\tFvFile(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)'+optional.decode())

    def test_legacy_shim_optional_data_is_separate_and_binary_is_hex(self):
        lines = self.text.splitlines()
        legacy = lines[0].replace('/\\EFI\\fedora\\shimx64.efi', '/File(\\EFI\\fedora\\shimx64.efi)')
        data = ('\\grubx64.efi\0').encode('utf-16-le')
        text = legacy+' File(.\\grubx64.efi)\n'+lines[1]+'\n    data: '+data.hex(' ')+'\n'
        self.assertEqual(owner.firmware_entry(text, GUID)['number'], '000A')
        text = lines[0]+'00ff\n'+lines[1]+'\n    data: 00 ff\n'
        self.assertEqual(owner.firmware_entry(text, GUID)['number'], '000A')

    def test_every_ambiguity_unknown_grammar_or_disagreement_refuses(self):
        line, byte_line = self.text.splitlines()
        wrong = '10000001-1111-2222-3333-444444444444'
        examples = [self.text.replace(GUID, wrong), self.text+self.text,
            self.text+self.text.replace('Boot000A', 'Boot000B'),
            line.replace('\t', ' '), line.replace('Boot000A', 'Boot000AA'),
            line.replace('/\\EFI\\', '/Unexpected(\\EFI\\'),
            line.replace('HD(', 'Unknown('),
            line.replace('/\\EFI\\', '/File(\\EFI\\'),
            line.replace('/\\EFI\\', '/\\OTHER\\'),
            line.replace('/\\EFI\\', '/\\EFI\\..\\'),
            line.replace('0x800', '2048'), line.replace('GPT', 'MBR'),
            line+' garbage', line+'\nwarning: skipped an unreadable variable',
            self.text.replace('04 01 2a 00', '04 01 29 00'),
            self.text.replace('\\shimx64.efi', '\\other.efi'),
            'Boot000A* Hidden HD\tFvFile(7cb8bdc9-f8eb-4f34-aaea-3ee4af6516a1)\n'+byte_line+'\n'+self.text.replace('Boot000A', 'Boot000B'),
            self.text+'    data: ff\n', self.text+byte_line+'\n',
            'BootOrder: 000A\nBootOrder: 000A\n'+self.text,
            line.replace('Bazzite', 'HD(1,GPT,'+GUID+',0x800,0x10)').replace(GUID, wrong),
            line.replace('/\\EFI\\', '/HD(1,GPT,'+GUID+',0x800,0x10)/\\EFI\\')]
        for text in examples:
            with self.subTest(text=text): self.refuse(text)


if __name__ == '__main__': unittest.main()
