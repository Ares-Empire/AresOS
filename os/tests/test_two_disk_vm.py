import json
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import two_disk_vm as vm
from switch_vm import partition_identity


class TwoDiskHarnessTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        self.directory = pathlib.Path(self.temp.name).resolve()

    def test_real_target_identity_handles_reversed_enumeration_and_ignores_protected_disk(self):
        layout = dict(blockdevices=[dict(name='vdb', type='disk', size=49),
            dict(name='vdb1', type='part', size=1, start=2048, partuuid='target'),
            dict(name='vda', type='disk', size=50),
            dict(name='vda1', type='part', size=2, start=2048, partuuid='protected')])
        observed = partition_identity(layout, 'vdb')
        self.assertEqual([row[0] for row in observed], ['vdb', 'vdb1'])
        with self.assertRaises(AssertionError):
            partition_identity(layout, 'vdc')

    def test_two_writable_file_disks_in_both_orders_and_protected_only_for_detach(self):
        for name in ('protected.raw', 'target.raw'):
            (self.directory / name).write_bytes(b'fixture')
        guest = object.__new__(vm.Guest)
        guest.mode = 'installed'
        with patch.object(vm, 'WORK', self.directory):
            for order, first in (('protected-first', 'protected'), ('protected-second', 'target')):
                guest.order = order
                args = guest.disk_args(self.directory / 'target.raw')
                drives = [args[i + 1] for i, v in enumerate(args) if v == '-drive']
                self.assertEqual(len(drives), 2)
                self.assertIn(f'id={first}', drives[0])
                self.assertFalse(any('readonly' in drive for drive in drives))
            guest.mode = 'marker-detached'
            args = guest.disk_args(self.directory / 'target.raw')
            self.assertIn('id=protected', ' '.join(args))
            self.assertNotIn('target.raw', ' '.join(args))

    def test_final_write_counter_is_taken_after_guest_shutdown_before_qemu_exit(self):
        guest = object.__new__(vm.Guest)
        guest.monitor = Mock(events=[])
        guest.process = Mock(returncode=0)
        guest.replies = Mock()
        guest.replies.feed.return_value = b''
        guest.secrets = []
        guest.console = Mock()
        sequence = []
        def receive(_):
            guest.monitor.events.append(dict(event='SHUTDOWN', data=dict(guest=True, reason='guest-shutdown')))
            sequence.append('guest-shutdown')
            return b'reboot: Power down\n'
        guest.console.recv.side_effect = receive
        guest.writes = lambda stage: sequence.append('final-write-audit')
        guest.monitor.command.side_effect = lambda command: sequence.append(command)
        guest.process.wait.side_effect = lambda **kwargs: sequence.append('process-exited')
        with patch.object(vm, 'EVIDENCE', self.directory):
            guest.finish_shutdown('fixture', 'guest-shutdown')
        self.assertEqual(sequence, ['guest-shutdown', 'final-write-audit', 'quit', 'process-exited'])

    def test_host_shutdown_cannot_be_accepted_as_orderly_guest_shutdown(self):
        guest = object.__new__(vm.Guest)
        guest.monitor = Mock(events=[dict(event='SHUTDOWN', data=dict(guest=False, reason='host-signal'))])
        guest.writes = Mock()
        with self.assertRaises(AssertionError):
            guest.finish_shutdown('fixture', 'guest-shutdown')
        guest.writes.assert_not_called()
