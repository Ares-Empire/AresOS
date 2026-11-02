"""Real efibootmgr18 capture and binary UEFI edge cases; no EFI access."""
import hashlib
import json
import struct
import subprocess
import unittest
import uuid
from unittest.mock import patch
import test_owner_tools as common

ROOT, owner = common.ROOT, common.owner
FIXTURES = ROOT/'os/tests/fixtures/owner-tools'
GUID = '88420aef-f1fd-4814-8381-339d03f60a65'
END = b'\x7f\xff\x04\0'


def hd(guid=GUID):
    return struct.pack('<BBHIQQ16sBB',4,1,42,1,2048,0x12c000,uuid.UUID(guid).bytes_le,2,2)


def file(path='\\EFI\\fedora\\shimx64.efi'):
    name=(path+'\0').encode('utf-16-le')
    return struct.pack('<BBH',4,4,len(name)+4)+name


def entry(raw, number='000A', text='Arbitrary vendor text {unknown_alias}', active='*'):
    return 'Boot'+number+active+' '+text+'\n      dp: '+raw.hex(' ')+'\n'


class FirmwareTest(unittest.TestCase):
    def setUp(self):
        self.text=(FIXTURES/'efibootmgr18-qualification3.txt').read_text()

    def refuse(self,text,message=None):
        with patch('subprocess.run') as run, patch('subprocess.Popen') as popen, self.assertRaises(owner.Stop) as caught:
            owner.firmware_entry(text,GUID)
        if message:self.assertIn(message,str(caught.exception))
        run.assert_not_called();popen.assert_not_called()

    def test_real_retained_output_aliases_windows_and_fixture_provenance(self):
        for row in json.loads((FIXTURES/'tool-output-sources.json').read_text()):
            self.assertEqual(list(row)[:2],['sha256','path'])
            self.assertEqual(hashlib.sha256((ROOT/row['path']).read_bytes()).hexdigest(),row['sha256'])
        self.assertIn('{auto_created_boot_option}',self.text)
        self.assertIn('Windows Boot Manager',self.text)
        self.assertEqual(owner.firmware_entry(self.text,GUID.upper()),dict(number='000A',label='Bazzite',path='\\EFI\\fedora\\shimx64.efi',esp_guid=GUID))

    def test_rendered_text_and_optional_data_cannot_authorize_or_refuse(self):
        raw=hd()+file()+END
        for text in ('Bazzite\t/File(\\EFI\\fedora\\shimx64.efi)','Vendor\tgarbage','Unknown\tHD(1,GPT,wrong,0,0){arbitrary_alias}',''):
            for data in ('','    data: unparsed vendor data {auto_created_boot_option}\n'):
                self.assertEqual(owner.firmware_entry(entry(raw,text=text)+data,GUID)['number'],'000A')
        other=entry(b'\x04\x06\x14\0'+uuid.UUID(GUID).bytes_le+END,number='0001',text='HD(1,GPT,'+GUID+',0,0)/\\EFI\\fake.efi')
        self.refuse(other,'does not uniquely map')
        self.assertEqual(owner.firmware_entry(other+entry(raw),GUID)['number'],'000A')

    def test_no_byte_rows_never_falls_back_to_either_text_format(self):
        for tail in ('/\\EFI\\fedora\\shimx64.efi','/File(\\EFI\\fedora\\shimx64.efi)'):
            self.refuse('Boot000A* Bazzite\tHD(1,GPT,'+GUID+',0x800,0x12c000)'+tail,'No verbose dp bytes')

    def test_two_target_entries_including_inactive_refuse(self):
        self.refuse(self.text+entry(hd()+file()+END,number='000B',active=' '),'does not uniquely map')
        self.refuse(entry(hd()+file()+END)*2,'Duplicate Boot number')

    def test_non_efi_path_and_other_esp_not_counted(self):
        for raw in (hd()+file('\\OTHER\\boot.efi')+END,hd('20d4509a-0f19-4bc0-8478-2274d7eac018')+file()+END):
            self.refuse(entry(raw),'does not uniquely map')
            self.assertEqual(owner.firmware_entry(self.text+entry(raw,number='00FF'),GUID)['number'],'000A')
        other=hd('20d4509a-0f19-4bc0-8478-2274d7eac018')+b'\x04\x04\x05\0X'+END
        self.assertEqual(owner.firmware_entry(self.text+entry(other,number='00FF'),GUID)['number'],'000A')

    def test_all_node_bounds_and_target_encoding_are_checked(self):
        valid=hd()+file()+END
        cases=[valid[:n] for n in (0,1,3,4,20,41,42,43,len(valid)-1,len(valid)-4)]
        cases += [b'\x04\x01\0\0'+valid[4:],b'\x04\x01\xff\xff'+valid[4:],hd()+file()+END+b'\0',
            hd()+file()+b'\x7f\xfe\x04\0',hd()+b'\x04\x04\x08\0\0\xd8\0\0'+END,
            hd()+b'\x04\x04\x08\0A\0B\0'+END,hd()+file('\\EFI\\..\\bad.efi')+END,
            hd()+file('\\EFI\\bad\0.efi')+END,hd()+hd()+file()+END,hd()+file()+file()+END,
            file()+hd()+END,hd()+file()+b'\x7f\x01\x04\0'+END]
        for raw in cases:
            with self.subTest(hex=raw.hex()):self.refuse(entry(raw))

    def test_gpt_signature_type_and_mixed_endian(self):
        raw=hd()
        self.assertEqual(owner.device_path(raw+file()+END,GUID)['esp_guid'],GUID)
        for node in (raw[:24]+uuid.UUID(GUID).bytes+raw[40:],raw[:40]+b'\x01\x01'):
            self.refuse(entry(node+file()+END),'does not uniquely map')

    def test_wrapped_multiple_dp_lines_and_unknown_vendor_nodes(self):
        raw=hd()+file()+END
        text='Boot000A* Vendor\tWhatever\n      dp: '+raw[:42].hex(' ')+' /\n      dp: '+raw[42:60].hex(' ')+'\n          '+raw[60:].hex(' ')+'\n'
        self.assertEqual(owner.firmware_entry(text,GUID)['number'],'000A')
        vendor=struct.pack('<BBH',3,0xfe,7)+b'abc'
        self.assertEqual(owner.firmware_entry(entry(vendor+raw),GUID)['number'],'000A')

    def test_missing_or_bad_hex_and_unframed_warning_refuse(self):
        for text in (self.text+'Boot00FF* No bytes\n',self.text.replace('04 01 2a 00','04 01 zz 00'),self.text+'warning: skipped variable\n',
                     '      dp: 7f ff 04 00\n','BootOrder: 000A\nBootOrder: 000A\n'+entry(hd()+file()+END)):
            with self.subTest(text=text[:50]):self.refuse(text)

    def test_firmware_warning_retains_stdout_and_stderr(self):
        host=owner.Host();result=subprocess.CompletedProcess([],0,self.text,'Skipping unreadable variable\n')
        with patch.object(owner.shutil,'which',return_value=str(ROOT/'fixture-efibootmgr')),patch.object(owner.subprocess,'run',return_value=result),self.assertRaisesRegex(owner.Stop,'wrote stderr'):
            host.read('efibootmgr','-v')
        self.assertEqual(host.trace[-1]['stdout'],self.text)
        self.assertEqual(host.trace[-1]['stderr'],result.stderr)
        self.assertFalse(host.trace[-1]['mutation'])


if __name__=='__main__':unittest.main()
