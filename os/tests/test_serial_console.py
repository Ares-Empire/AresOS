import base64
import fcntl
import hashlib
import os
import pathlib
import pty
import select
import subprocess
import sys
import termios
import time
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from serial_console import TerminalReplies, decode_export, encode_command


class SerialExportTest(unittest.TestCase):
    raw = b'[{"scope":"system","name":"example.service","state":"masked"}]\n'

    def frame(self, payload):
        digest = hashlib.sha256(self.raw).hexdigest()
        return f'\r\nARESOS_EXPORT_START\r\n{payload}\r\nARESOS_EXPORT_END\r\nARESOS_EXPORT_SHA256 {digest}  /run/inventory.json\r\n'

    def test_kernel_record_at_every_payload_boundary_preserves_bytes(self):
        encoded = base64.b64encode(self.raw).decode()
        kernel = '[   63.397535] clocksource: Long readout interval, skipping watchdog check\r\n'
        for split in range(len(encoded) + 1):
            with self.subTest(split=split):
                self.assertEqual(decode_export(self.frame(encoded[:split] + kernel + encoded[split:])), self.raw)

    def test_wrapped_crlf_export_preserves_raw_json(self):
        encoded = base64.b64encode(self.raw).decode()
        wrapped = '\r\n'.join(encoded[n:n + 20] for n in range(0, len(encoded), 20))
        self.assertEqual(decode_export(self.frame(wrapped)), self.raw)

    def test_corruption_and_incomplete_frames_are_rejected(self):
        corrupted = base64.b64encode(self.raw.replace(b'masked', b'active')).decode()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            decode_export(self.frame(corrupted))
        with self.assertRaisesRegex(ValueError, 'Missing complete'):
            decode_export('\nARESOS_EXPORT_START\n' + base64.b64encode(self.raw).decode())


class SerialTerminalTest(unittest.TestCase):
    def test_queries_split_at_every_socket_boundary(self):
        cases = [(b'\x1b[6n', b'\x1b[24;80R'),
                 (b'\x1b]11;?\x1b\\', b'\x1b]11;rgb:0000/0000/0000\x1b\\'),
                 (b'\x1b]10;?\x07', b'\x1b]10;rgb:ffff/ffff/ffff\x1b\\'),
                 # systemd 259's terminfo query (XTGETTCAP "name"); answered "not supported".
                 (b'\x1bP+q6E616D65\x1b\\', b'\x1bP0+r\x1b\\')]
        for query, reply in cases:
            for split in range(len(query) + 1):
                with self.subTest(query=query, split=split):
                    terminal = TerminalReplies()
                    self.assertEqual(terminal.feed(query[:split]) + terminal.feed(query[split:]), reply)
                    self.assertEqual(terminal.feed(b'next output'), b'')
                    self.assertEqual(sum(terminal.counts.values()), 1)

    def test_repeated_queries_answered_once_each(self):
        terminal = TerminalReplies()
        output = b'\x1b]11;?\x1b\\\x1b[6n' * 3
        replies = b''.join(terminal.feed(bytes([byte])) for byte in output)
        self.assertEqual(replies, (b'\x1b]11;rgb:0000/0000/0000\x1b\\\x1b[24;80R') * 3)
        self.assertEqual(terminal.counts, {'color-11': 3, 'cursor-position': 3})

    def test_systemd_terminfo_query_between_size_probes_is_answered_in_order(self):
        # As rehearsal runs 6 and 12 logged it: the XTGETTCAP query, then DSR, cursor move, DSR.
        output = (b'\x1bP+q6E616D65\x1b\\NET: Registered PF_VSOCK protocol family\r\n'
                  b'\x1b[6n\x1b[32766;32766H\x1b[6n')
        for split in range(len(output) + 1):
            with self.subTest(split=split):
                terminal = TerminalReplies()
                replies = terminal.feed(output[:split]) + terminal.feed(output[split:])
                self.assertEqual(replies, b'\x1bP0+r\x1b\\' + b'\x1b[24;80R' * 2)
                self.assertEqual(terminal.counts, {'terminfo': 1, 'cursor-position': 2})

    def test_several_terminfo_queries_in_one_read_each_get_one_answer(self):
        terminal = TerminalReplies()
        replies = terminal.feed(b'\x1bP+q6E616D65\x1b\\\x1b[6n\x1bP+q544e\x1b\\\x1bP+q\x1b\\')
        self.assertEqual(replies, b'\x1bP0+r\x1b\\\x1b[24;80R\x1bP0+r\x1b\\\x1bP0+r\x1b\\')
        self.assertEqual(terminal.counts, {'terminfo': 3, 'cursor-position': 1})
        # Other DCS strings are not queries and get nothing.
        self.assertEqual(terminal.feed(b'\x1bP$qm\x1b\\\x1bPq#0;2;0;0;0\x1b\\'), b'')

    def test_shell_text_and_other_escape_sequences_do_not_receive_input(self):
        terminal = TerminalReplies()
        self.assertEqual(terminal.feed(b'login: Password: root@bazzite:~# ARESOS_SERIAL_READY:0\x1b[0m'), b'')
        self.assertEqual(terminal.counts, {})

    def test_boot_log_retention_is_bounded_without_losing_partial_query(self):
        terminal = TerminalReplies()
        self.assertEqual(terminal.feed(b'x' * 100000 + b'\x1b]12;?\x1b'), b'')
        self.assertLessEqual(len(terminal.pending), 64)
        self.assertEqual(terminal.feed(b'\\'), b'\x1b]12;rgb:ffff/ffff/ffff\x1b\\')


class SerialCommandTest(unittest.TestCase):
    def exchange(self, script, status):
        master, slave = pty.openpty()

        def controlling_terminal():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)

        process = subprocess.Popen(['bash', '--noprofile', '--norc', '-i'],
                                   stdin=slave, stdout=slave, stderr=slave,
                                   preexec_fn=controlling_terminal,
                                   env={**os.environ, 'TERM': 'dumb', 'PS1': '', 'PS2': ''})
        os.close(slave)
        os.set_blocking(master, False)
        pending = encode_command(script).encode()
        output = b''
        marker = f'ARESOS_CMD_DONE:{status}'.encode()
        deadline = time.monotonic() + 10
        try:
            while time.monotonic() < deadline:
                readable, writable, _ = select.select([master], [master] if pending else [], [], 0.1)
                if writable:
                    written = os.write(master, pending[:1024])
                    pending = pending[written:]
                if readable:
                    output += os.read(master, 65536)
                    if marker in output:
                        return output
            self.fail(f'No completion marker after real PTY execution: {output!r}')
        finally:
            process.kill()
            process.wait()
            os.close(master)

    def test_guest_tty_reader_cannot_consume_completion_command(self):
        output = self.exchange('''python3 - <<'PY'
import os
import select
import time
fd = os.open('/dev/tty', os.O_RDONLY | os.O_NONBLOCK)
time.sleep(0.2)
while select.select([fd], [], [], 0)[0]:
    os.read(fd, 4096)
os.close(fd)
print('TTY_READER_FINISHED')
PY
''', 0)
        self.assertIn(b'TTY_READER_FINISHED', output)

    def test_long_script_survives_canonical_tty_line_limit(self):
        script = '#' + 'x' * 12000 + "\nprintf 'LONG_%s\\n' PAYLOAD\n"
        self.assertTrue(all(len(line) < 4096 for line in encode_command(script).splitlines()))
        self.assertIn(b'LONG_PAYLOAD', self.exchange(script, 0))

    def test_nonzero_guest_exit_is_preserved(self):
        self.exchange('exit 7', 7)
