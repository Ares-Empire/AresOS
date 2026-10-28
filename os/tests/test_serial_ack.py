"""Actual wait/parser and Bash/PTY transport; no privileged host operation."""
import base64
import hashlib
import json
import pathlib
import re
import socket
import sys
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import serial_console as console
import serial_transport as transport
import switch_vm as sw
from serial_pty import Fixture

NONCE = '0123456789abcdef'
KERNEL = '[   58.604886] async_tx: api initialized (async)\r\n'


class Socket:
    def __init__(self, chunks): self.chunks, self.sent = list(chunks), []
    def recv(self, count):
        if self.chunks: return self.chunks.pop(0)
        raise socket.timeout()
    def sendall(self, data): self.sent.append(data)


def guest(chunks=(), buffer=''):
    g = object.__new__(sw.Guest)
    g.console = Socket(chunks); g.buffer = buffer; g.transcript = ''; g.boot_transcript = ''
    g.authentication_started = True; g.replies = console.TerminalReplies()
    return g


class AckTest(unittest.TestCase):
    def test_exact_probe18_interleave_is_filtered_without_legacy_protocol_fallback(self):
        value = json.loads((ROOT/'os/tests/fixtures/owner-console/14zj-probe18-ack.json').read_text())
        raw = value['exact_nonsecret_ack_span']
        old = r'\r?\nARESOS_STAGE_' + value['nonce'] + r':10:(\d+)\r?\n'
        self.assertIsNone(re.search(old, raw))
        clean, match = console.serial_search(old, raw)
        self.assertEqual(match[1], '0'); self.assertNotIn('async_tx', clean)
        ack = transport.Ack(value['nonce'], value['phase'], value['index'])
        self.assertIsNone(ack.search(raw))  # No production acceptance of legacy ACKs.
        new = raw.replace('ARESOS_STAGE_'+value['nonce']+':10:0',
            'ARESOS_ACK:'+value['nonce']+':syntax:10:0:END')
        self.assertEqual(guest([new.encode()]).wait(ack, .1), console.strip_kernel_lines(new).rstrip('\r\n'))

    def test_kernel_at_every_ack_byte_boundary_and_socket_split_preserves_exact_fields(self):
        marker = f'ARESOS_ACK:{NONCE}:syntax:10:0:END'
        ack = transport.Ack(NONCE, 'syntax', 10)
        for index in range(len(marker)+1):
            with self.subTest(index=index):
                raw = marker[:index]+KERNEL+marker[index:]
                self.assertEqual(guest([raw.encode()]).wait(ack, .1), marker)
        raw = marker[:21]+KERNEL+marker[21:]
        for index in range(len(raw)+1):
            with self.subTest(socket_split=index):
                chunks = [v.encode() for v in (raw[:index],raw[index:]) if v]
                self.assertEqual(guest(chunks).wait(ack, .1), marker)

    def test_truncated_kernel_never_grants_ack_or_completion_and_wait_is_bounded(self):
        marker = f'ARESOS_ACK:{NONCE}:chunk:2:0:END'
        for text in (marker+KERNEL.rstrip('\r\n'), marker[:20]+KERNEL.rstrip('\r\n')+marker[20:]):
            with self.subTest(text=text):
                with self.assertRaises(console.IncompleteKernelLine): console.strip_kernel_lines(text)
                g=guest([text.encode()])
                with self.assertRaises(TimeoutError): g.wait(transport.Ack(NONCE,'chunk',2), .02)
                self.assertEqual(g.console.sent, [])
        with self.assertRaises(console.IncompleteKernelLine):
            console.command_status('\nARESOS_CMD_DONE:0\n'+KERNEL.rstrip('\r\n'))

    def test_duplicate_mismatch_out_of_order_and_noncanonical_status_stop(self):
        marker = f'ARESOS_ACK:{NONCE}:chunk:2:0:END'
        cases = [marker+marker, marker+'ARESOS_ACK:',
            marker.replace(NONCE, 'f'*16), marker.replace(':chunk:',':syntax:'),
            marker.replace(':2:0:', ':3:0:'), marker.replace(':2:0:', ':02:0:'),
            marker.replace(':0:END', ':00:END'), marker.replace(':0:END', ':256:END'),
            marker.replace(':0:END', ':0garbage:END')]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(AssertionError):
                guest([text.encode()]).wait(transport.Ack(NONCE,'chunk',2), .1)
        g=guest(buffer=marker)
        with self.assertRaisesRegex(AssertionError, 'duplicate'): g.send('MUST_NOT_SEND\n')
        self.assertEqual(g.console.sent, [])

    def test_all_other_serial_markers_use_the_same_incremental_filter(self):
        for marker in ('\nARESOS_CMD_DONE:0\n','\nARESOS_READY\n','\nARESOS_ROOT_READY\n',
                'ARESOS_PROMPT> ', 'ARESOS_SUDO_PASSWORD:', 'login: ', 'Password: ', 'ARESOS_JOURNAL_READY'):
            for index in range(len(marker)+1):
                raw=marker[:index]+KERNEL+marker[index:]
                g=guest([raw.encode()])
                self.assertEqual(g.wait(re.escape(marker), .1), marker)
        self.assertEqual(console.command_status('\nARESOS_CMD_DO'+KERNEL+'NE:7\n'),7)
        with self.assertRaises(AssertionError): console.command_status('\nARESOS_CMD_DONE:0\n\nARESOS_CMD_DONE:0\n')

    def test_export_checksum_remains_required_and_partial_kernel_is_not_discarded(self):
        raw=b'{"fixture":true}\n';encoded=base64.b64encode(raw).decode()
        frame='\nARESOS_EXPORT_START\n'+encoded+'\nARESOS_EXPORT_END\nARESOS_EXPORT_SHA256 '+hashlib.sha256(raw).hexdigest()+'  guest.json\n'
        for marker in ('ARESOS_EXPORT_START','ARESOS_EXPORT_END','ARESOS_EXPORT_SHA256'):
            for index in range(len(marker)+1):
                point=frame.index(marker)+index
                self.assertEqual(console.decode_export(frame[:point]+KERNEL+frame[point:]),raw)
        with self.assertRaises(console.IncompleteKernelLine): console.decode_export(frame+KERNEL.rstrip('\r\n'))
        with self.assertRaisesRegex(ValueError,'checksum'): console.decode_export(frame.replace(encoded,base64.b64encode(b'bad').decode()))

    def test_real_bash_staging_and_hidden_resync_survive_interleaved_records(self):
        with Fixture() as f:
            receive=f.serial.recv
            def interrupted(count):
                raw=receive(count)
                raw=re.sub(rb'(ARESOS_ACK:[0-9a-f]{16}:[a-z]+:[0-9]+:[0-9]+:END)',
                    lambda m:m[0][:19]+KERNEL.encode()+m[0][19:],raw)
                return raw.replace(b'ARESOS_CMD_DONE:',b'ARESOS_CMD_DO'+KERNEL.encode()+b'NE:')
            f.serial.recv=interrupted
            source=sw.framed('#'+'x'*300+'\nprintf \'{"fixture":true}\'')
            self.assertEqual(f.guest.capture_json('interleaved',source),dict(fixture=True))
            value=f.guest.resync_after_hidden('interleaved-resync')
            self.assertTrue(value['prior_completion_observed'] and value['serial_input_flushed'])
            self.assertEqual(list(f.stage.iterdir()),[])
            proof=json.loads((f.evidence/'interleaved-transport.json').read_text())
            self.assertTrue(proof['verified']);self.assertTrue(all(v['status']=='passed' for v in proof['steps']))

    def test_duplicate_real_ack_stops_without_executing_or_retrying(self):
        with Fixture() as f:
            receive=f.serial.recv
            def duplicate(count):
                raw=receive(count)
                return re.sub(rb'(ARESOS_ACK:[0-9a-f]{16}:chunk:2:0:END)',lambda m:m[0]+m[0],raw)
            f.serial.recv=duplicate
            with self.assertRaisesRegex(AssertionError,'Duplicate'):
                f.guest.command('duplicate','#'+'x'*300+'\nprintf MUST_NOT_RUN',timeout=2)
            self.assertFalse(any(b'bash "$_ares_stage/script" </dev/null' in v for v in f.serial.sent))
            self.assertEqual(sum(b'base64 -d >>' in v for v in f.serial.sent),1)
        with Fixture() as f:
            marker=f'ARESOS_ACK:{NONCE}:syntax:10:0:END'
            f.guest.buffer=marker
            with self.assertRaisesRegex(AssertionError,'duplicate'):
                f.guest.command('buffered-duplicate','#'+'x'*300+'\nprintf MUST_NOT_RUN',timeout=2)
            self.assertEqual(f.serial.sent,[])
            self.assertEqual((f.evidence/'buffered-duplicate-incomplete.txt').read_text(),marker)


if __name__ == '__main__': unittest.main()
