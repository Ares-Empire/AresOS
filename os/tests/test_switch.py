import copy
import base64
import hashlib
import pathlib
import socket
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
from switch_vm import booted_digest, booted_reference, inspect_transaction, partition_identity, redact, stock_initialization_reboot, wait_for_exit_draining


class SwitchEvidenceTest(unittest.TestCase):
    def transaction(self, rollback=False):
        selected = dict(image=dict(image=dict(image='stock:stable' if rollback else 'release@sha256:bbb'),
                                   imageDigest='sha256:aaa' if rollback else 'sha256:bbb'),
                        ostree=dict(checksum='stock-checksum' if rollback else 'release-checksum'))
        return {'status': dict(booted=dict(ostree=dict(checksum='stock-checksum')),
                               staged=None if rollback else selected,
                               rollback=selected if rollback else None, rollbackQueued=rollback)}

    def test_reboot_inspection_requires_correct_staged_or_queued_identity(self):
        for rollback in (False, True):
            target = 'stock:stable' if rollback else 'release@sha256:bbb'
            args = dict(rollback=rollback, digest='sha256:aaa' if rollback else None)
            status = self.transaction(rollback)
            inspect_transaction(status, target, 'stock-checksum', **args)
            slot = 'rollback' if rollback else 'staged'
            for field in ('reference', 'digest', 'checksum', 'queue', 'missing'):
                wrong = copy.deepcopy(status)
                if field == 'reference':
                    wrong['status'][slot]['image']['image']['image'] = 'wrong'
                elif field == 'digest':
                    wrong['status'][slot]['image']['imageDigest'] = 'wrong'
                elif field == 'checksum':
                    wrong['status']['rollback' if rollback else 'booted']['ostree']['checksum'] = 'wrong'
                elif field == 'queue':
                    wrong['status']['rollbackQueued'] = not rollback
                else:
                    wrong['status'][slot] = None
                with self.subTest(rollback=rollback, field=field), self.assertRaises((AssertionError, TypeError)):
                    inspect_transaction(wrong, target, 'stock-checksum', **args)

    def test_reboot_reader_drains_more_than_socket_capacity_and_answers_terminal_query(self):
        reader, writer = socket.socketpair()
        writer.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4096)
        program = '''import socket, sys
s = socket.socket(fileno=int(sys.argv[1]))
s.sendall(b'x' * 1048576 + b'\\x1b[6n')
assert s.recv(100) == b'\\x1b[24;80R'
s.close()
'''
        process = subprocess.Popen([sys.executable, '-c', program, str(writer.fileno())],
                                   pass_fds=[writer.fileno()])
        writer.close()
        try:
            output = wait_for_exit_draining(reader, process, timeout=10)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(output, b'x' * 1048576 + b'\x1b[6n')
        finally:
            reader.close()
            if process.poll() is None:
                process.kill()
            process.wait()

    def test_reboot_reader_still_rejects_guest_that_does_not_exit_by_deadline(self):
        reader, writer = socket.socketpair()
        process = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        try:
            with self.assertRaises(subprocess.TimeoutExpired):
                wait_for_exit_draining(reader, process, timeout=0.1)
        finally:
            reader.close()
            writer.close()
            process.kill()
            process.wait()

    def export_frame(self, raw):
        return ('\r\nARESOS_EXPORT_START\r\n' + base64.b64encode(raw).decode()
                + '\r\nARESOS_EXPORT_END\r\nARESOS_EXPORT_SHA256 '
                + hashlib.sha256(raw).hexdigest() + '  guest.json\r\n')
    def test_only_orderly_guest_initialization_reset_is_accepted(self):
        reset = [{'event': 'SHUTDOWN', 'data': {'guest': True, 'reason': 'guest-reset'}}]
        console = '[ 157.23] reboot: Restarting system\r\n'
        self.assertTrue(stock_initialization_reboot(console, reset))
        self.assertFalse(stock_initialization_reboot('Kernel panic\n' + console, reset))
        self.assertFalse(stock_initialization_reboot(console, reset + [{'event': 'GUEST_PANICKED'}]))
        self.assertFalse(stock_initialization_reboot('boot failed', reset))
        self.assertFalse(stock_initialization_reboot(console, [{'event': 'SHUTDOWN', 'data': {'guest': False, 'reason': 'host-qmp-quit'}}]))

    def test_duplicate_or_missing_shutdown_cannot_hide_a_boot_loop(self):
        reset = {'event': 'SHUTDOWN', 'data': {'guest': True, 'reason': 'guest-reset'}}
        self.assertFalse(stock_initialization_reboot('reboot: Restarting system', []))
        self.assertFalse(stock_initialization_reboot('reboot: Restarting system', [reset, reset]))

    def test_partition_changes_cannot_hide_behind_identical_mounts(self):
        layout = {'blockdevices': [dict(name='vda1', type='part', start=2048,
                  size=1048576, partuuid='partition-a', parttype='efi', uuid='fs-a'),
                  dict(name='vda', type='disk', size=10000000)]}
        expected = partition_identity(layout)
        for field, changed in [('start', 4096), ('size', 2097152), ('partuuid', 'other'),
                               ('parttype', 'linux'), ('uuid', 'other-fs')]:
            candidate = copy.deepcopy(layout)
            candidate['blockdevices'][0][field] = changed
            self.assertNotEqual(partition_identity(candidate), expected, field)
        candidate = copy.deepcopy(layout)
        candidate['blockdevices'][0]['mountpoints'] = ['/changed-mount']
        self.assertEqual(partition_identity(candidate), expected)
        candidate['blockdevices'].append(dict(name='vda2', type='part', size=1024))
        self.assertNotEqual(partition_identity(candidate), expected)

    def test_recreated_ram_swap_is_not_a_partition_change(self):
        disk = dict(name='vda', type='disk', size=10000000)
        partition = dict(name='vda1', type='part', start=2048, size=1048576,
                         partuuid='partition-a', parttype='efi', uuid='fs-a')
        before = {'blockdevices': [disk, partition, dict(name='zram0', type='disk', size=4096, uuid='swap-a')]}
        after = copy.deepcopy(before)
        after['blockdevices'][-1]['uuid'] = 'swap-b'
        self.assertEqual(partition_identity(before), partition_identity(after))
        after['blockdevices'][1]['start'] = 4096
        self.assertNotEqual(partition_identity(before), partition_identity(after))

    def test_absent_disk_or_partition_table_cannot_pass_comparison(self):
        for devices in ([], [dict(name='zram0', type='disk', size=4096)],
                        [dict(name='vda', type='disk', size=10000000)]):
            with self.subTest(devices=devices), self.assertRaises(AssertionError):
                partition_identity({'blockdevices': devices})

    def test_staged_reference_cannot_be_mistaken_for_booted_release(self):
        status = {'status': {'booted': {'image': {'image': {'image': 'stock@sha256:aaa'}, 'imageDigest': 'sha256:aaa'}},
                             'staged': {'image': {'image': {'image': 'release@sha256:bbb'}, 'imageDigest': 'sha256:bbb'}}}}
        self.assertEqual(booted_reference(status), 'stock@sha256:aaa')
        self.assertEqual(booted_digest(status), 'sha256:aaa')
        status['status']['booted']['image']['image']['image'] = 'stock:stable'
        self.assertEqual(booted_digest(status), 'sha256:aaa')

    def test_credentials_and_encoded_variants_are_redacted(self):
        self.assertEqual(redact('token=secret-token password=secret-password encoded=encoded-secret',
                                ['secret-token', 'secret-password', 'encoded-secret']),
                         'token=<redacted> password=<redacted> encoded=<redacted>')

    def test_serial_json_frame_is_parsed_independently_of_shell_prompt(self):
        from switch_vm import Guest
        import tempfile
        import switch_vm
        guest = object.__new__(Guest)
        guest.command = lambda *_: 'ARESOS_ROOT> ' + self.export_frame(b'{"booted":true}')
        previous = switch_vm.EVIDENCE
        with tempfile.TemporaryDirectory() as directory:
            switch_vm.EVIDENCE = pathlib.Path(directory)
            try:
                self.assertEqual(guest.capture_json('status', ''), {'booted': True})
            finally:
                switch_vm.EVIDENCE = previous

    def test_status_spinner_and_interleaved_kernel_records_preserve_json_bytes(self):
        from serial_console import decode_export
        raw = b'{"status":{"booted":{"imageDigest":"sha256:abc"}}}'
        encoded = base64.b64encode(raw).decode()
        for position in range(len(encoded) + 1):
            frame = self.export_frame(raw).replace(encoded, encoded[:position]
                + '[ 44.481841] EXT4-fs (vda3): re-mounted filesystem\r\n' + encoded[position:])
            progress = '\x1b[2K Waiting for sysroot lock...\r\n'
            self.assertEqual(decode_export(progress + frame), raw)

    def test_corrupt_status_export_cannot_be_accepted_as_state(self):
        from serial_console import decode_export
        frame = self.export_frame(b'{"booted":true}')
        corrupt = frame.replace(base64.b64encode(b'{"booted":true}').decode(),
                                base64.b64encode(b'{"booted":false}').decode())
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            decode_export(corrupt)
