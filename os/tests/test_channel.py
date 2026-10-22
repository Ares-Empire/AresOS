import base64
import pathlib
import socket
import sys
import threading
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from channel import Frames, MAX_FRAME, export_bytes, frame, import_bytes
from qmp import QMP, assert_guest_poweroff


class ChannelTest(unittest.TestCase):
    def test_fragmented_and_coalesced_frames_at_every_boundary(self):
        first, second = {'ready': True}, {'output': 'µ\nterminal escapes: \x1b[6n'}
        wire = frame(first) + frame(second)
        for split in range(1, len(wire)):
            with self.subTest(split=split):
                chunks = iter((wire[:split], wire[split:]))
                incoming = Frames(lambda size: next(chunks, b''))
                self.assertEqual(incoming.receive(), first)
                self.assertEqual(incoming.receive(), second)

    def test_incomplete_and_oversized_frames_fail(self):
        chunks = iter((b'{"ready":', b''))
        with self.assertRaises(EOFError):
            Frames(lambda size: next(chunks)).receive()
        with self.assertRaises(ValueError):
            Frames(lambda size: b'x' * (MAX_FRAME + 1)).receive()
        with self.assertRaises(ValueError):
            frame({'output': 'x' * MAX_FRAME})

    def test_raw_exports_preserve_bytes_and_reject_corruption(self):
        raw = b'{\n  "raw": "spacing preserved"\n}\n'
        encoded = export_bytes(raw)
        self.assertEqual(import_bytes(encoded), raw)
        encoded['base64'] = base64.b64encode(raw + b' ').decode()
        with self.assertRaisesRegex(ValueError, 'checksum'):
            import_bytes(encoded)
        encoded['base64'] = '!invalid!'
        with self.assertRaises(ValueError):
            import_bytes(encoded)


class QMPTest(unittest.TestCase):
    shutdown = dict(event='SHUTDOWN', data=dict(guest=True, reason='guest-shutdown'))

    def test_events_before_and_after_command_reply_are_retained(self):
        client, server = socket.socketpair()

        def guest():
            with server:
                server.sendall(frame({'QMP': {}}))
                request = Frames(server.recv).receive()
                self.assertEqual(request['execute'], 'system_powerdown')
                server.sendall(frame({'event': 'POWERDOWN'}) + frame({'return': {}, 'id': request['id']}))
                server.sendall(frame(self.shutdown))

        worker = threading.Thread(target=guest)
        worker.start()
        with client:
            qmp = QMP(client)
            self.assertEqual(qmp.command('system_powerdown'), {})
            worker.join(timeout=5)
            qmp.reader.join(timeout=5)
            self.assertFalse(qmp.reader.is_alive())
            self.assertEqual([event['event'] for event in qmp.events], ['POWERDOWN', 'SHUTDOWN'])
            self.assertEqual(assert_guest_poweroff(qmp.events), self.shutdown)

    def test_host_exit_reset_suspend_and_missing_shutdown_are_rejected(self):
        bad = [[], [dict(event='SHUTDOWN', data=dict(guest=False, reason='host-qmp-quit'))],
               [dict(event='SHUTDOWN', data=dict(guest=True, reason='guest-reset'))],
               [self.shutdown, self.shutdown]]
        bad += [[self.shutdown, {'event': event}] for event in ('RESET', 'SUSPEND', 'GUEST_PANICKED')]
        for events in bad:
            with self.subTest(events=events), self.assertRaises(AssertionError):
                assert_guest_poweroff(events)


if __name__ == '__main__':
    unittest.main()
