from email.message import EmailMessage
import struct
import unittest

from aresos_control.common import Refused
from aresos_control.mail.dkim import verify_one_click,txt_answer,canonical_body,canonical_header
from aresos_control.mail.codec import SMTP_POLICY
from dkim_fixture import signed


class DKIM(unittest.TestCase):
    def test_full_signed_headers_verified_but_tampering_ambiguity_partial_or_missing_rejected(self):
        msg = EmailMessage()
        msg['From'] = 'sender@mail.invalid'
        msg['To'] = 'receiver@mail.invalid'
        msg['Subject'] = 'Signed fixture'
        msg['List-Unsubscribe'] = '<https://site.invalid/unsub>'
        msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
        msg.set_content('Signed content')
        raw,key = signed(msg.as_bytes(policy=SMTP_POLICY))
        self.assertEqual(verify_one_click(raw,lambda _: [key])['domain'],'mail.invalid')
        for invalid in [raw.replace(b'Signed content',b'Changed content'),raw.replace(b'site.invalid',b'evil.invalid'),
                        raw.replace(b'a=rsa-sha256;',b'a=rsa-sha256; l=2;'),
                        b'List-Unsubscribe: <https://evil.invalid>\r\n' + raw,
                        raw.split(b'\r\n',1)[1]]:
            with self.subTest(case=invalid[:80]):
                with self.assertRaises(Refused):
                    verify_one_click(invalid,lambda _: [key])
        with self.assertRaises(Refused):
            verify_one_click(raw,lambda _: [b'v=DKIM1; p='])
        with self.assertRaises(Refused):
            verify_one_click(raw,lambda _: [key,key])

    def test_rfc_canonicalization_examples_and_dns_compressed_txt_chunks(self):
        self.assertEqual(canonical_header(b'SUBJect:  A\r\n\t B \t',b'relaxed'),b'subject:A B\r\n')
        self.assertEqual(canonical_body(b' A \t B \t\r\n\r\n',b'relaxed'),b' A B\r\n')
        self.assertEqual(canonical_body(b'\r\n\r\n',b'relaxed'),b'')
        self.assertEqual(canonical_body(b'',b'simple'),b'\r\n')
        name = 'fixture._domainkey.mail.invalid'
        wire = b''.join(bytes([len(s)])+s.encode() for s in name.split('.')) + b'\0'
        question = wire + struct.pack('!HH',16,1)
        value = b'\x07v=DKIM1\x06; p=xx'
        answer = b'\xc0\x0c' + struct.pack('!HHIH',16,1,60,len(value)) + value
        packet = struct.pack('!6H',7,0x8180,1,1,0,0) + question + answer
        self.assertEqual(txt_answer(packet,7,name),[b'v=DKIM1; p=xx'])
        for transaction,target in ((8,name),(7,'other.invalid')):
            with self.assertRaises(ValueError):
                txt_answer(packet,transaction,target)
