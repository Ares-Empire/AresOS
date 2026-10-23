import json
import pathlib
import shlex
import subprocess
import sys
import tempfile
import unittest
import zipfile
from unittest.mock import Mock, patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import two_disk_vm as vm
from switch_vm import partition_identity
from prepare_two_disks import verify_loop


class TwoDiskHarnessTest(unittest.TestCase):
    def test_bls_export_is_one_quoted_command_and_parses_real_files(self):
        directory = self.directory / "BLS 'quoted directory"
        directory.mkdir()
        content = 'title Recorded stock\noptions quiet ostree=/ostree/boot.1/fedora/abc/0\n'
        (directory / 'ostree-2-fedora.conf').write_text(content)
        executable, option, program = shlex.split(vm.bls_inventory_command(directory, self.directory))
        self.assertEqual((executable, option), ('python3', '-c'))
        result = subprocess.run([sys.executable, '-c', program], check=True, capture_output=True, text=True)
        entry, = json.loads(result.stdout)
        self.assertEqual(entry['id'], 'ostree-2-fedora')
        self.assertEqual(entry['title'], 'Recorded stock')
        self.assertEqual(entry['content'], content)
        self.assertEqual(entry['deployment'], str((self.directory / 'ostree/boot.1/fedora/abc/0').resolve()))
        (directory / 'ostree-2-fedora.conf').write_text('title Missing deployment\noptions quiet\n')
        self.assertNotEqual(subprocess.run([sys.executable, '-c', program], capture_output=True).returncode, 0)

    def test_installer_transport_is_forwarded_only_in_live_mode_on_host_loopback(self):
        guest = object.__new__(vm.Guest)
        guest.mode = 'live'
        self.assertEqual(guest.network_args(), 'user,model=virtio-net-pci,hostfwd=tcp:127.0.0.1:18080-:8080')
        for mode in ('installed', 'marker-baseline', 'marker-detached'):
            guest.mode = mode
            self.assertEqual(guest.network_args(), 'user,model=virtio-net-pci')

    def test_timed_out_public_command_preserves_only_its_redacted_partial_output(self):
        guest = object.__new__(vm.sw.Guest)
        guest.transcript = 'earlier private authentication\n'
        guest.secrets = ['disposable-secret']
        guest.send = Mock()
        def wait(*args):
            guest.transcript += 'server checkpoint disposable-secret\n'
            raise TimeoutError('fixture deadline')
        guest.wait = wait
        with patch.object(vm.sw, 'EVIDENCE', self.directory):
            with self.assertRaises(TimeoutError):
                guest.command('public', 'fixture')
            self.assertTrue(guest.command_pending)
            self.assertEqual((self.directory / 'public-incomplete.txt').read_text(), 'server checkpoint <redacted>\n')
            with self.assertRaises(TimeoutError):
                guest.command('private', 'fixture', private=True)
            self.assertFalse((self.directory / 'private-incomplete.txt').exists())

    def test_ui_salted_password_hash_is_redacted_without_knowing_its_salt(self):
        for algorithm in ('6', 'y'):
            secret = '$' + algorithm + '$different-salt$' + 'A' * 86
            self.assertEqual(vm.sw.redact('hash="' + secret + '"', []), 'hash="<redacted-password-hash>"')

    def test_recorded_stock_bls_entry_does_not_assume_the_installer_os_name(self):
        stock = 'a' * 64
        for name in ('default', 'bazzite', 'fedora'):
            for index in (1, 2, 3):
                entry = dict(id=f'ostree-{index}-' + name, deployment='/sysroot/ostree/deploy/' + name + '/deploy/' + stock + '.0')
                self.assertEqual(vm.stock_bls_entry([entry], stock), dict(entry, menu_index=index))
                self.assertIsNone(vm.stock_bls_entry([entry, dict(entry)], stock))
                self.assertIsNone(vm.stock_bls_entry([dict(entry, id='ostree-0-' + name)], stock))
                self.assertIsNone(vm.stock_bls_entry([dict(entry, id="ostree-1-invalid'quote")], stock))
                self.assertIsNone(vm.stock_bls_entry([entry], 'b' * 64))

    def test_actual_colorized_iso_help_still_rejects_unsupported_live_kickstart(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        actual = (root / 'os/manifest/ci/11b/probe-3/two-disk/live-cli.txt').read_text(encoding='utf-8')
        self.assertIn('\x1b[1;36m--kickstart', actual)
        with self.assertRaisesRegex(RuntimeError, 'does not support live kickstart'):
            vm.require_supported_live_kickstart(actual)

    def test_failed_diagnostic_cannot_skip_orderly_shutdown_or_suppress_write_failure(self):
        guest = Mock()
        guest.command_pending = False
        guest.process.poll.return_value = None
        guest.command.side_effect = AssertionError('Missing diagnostic process')
        with self.assertRaisesRegex(AssertionError, 'Missing diagnostic'):
            vm.cleanup_live(guest, 'fixture', diagnostics=True)
        guest.poweroff.assert_called_once_with('fixture')
        guest.send.assert_not_called()
        guest.command.side_effect = None
        guest.poweroff.side_effect = AssertionError('PRODUCT FAILURE: protected writes')
        with self.assertRaisesRegex(AssertionError, 'PRODUCT FAILURE'):
            vm.cleanup_live(guest, 'fixture', diagnostics=True)

    def test_target_reset_refuses_an_open_file_and_preserves_it(self):
        target = self.directory / 'target.raw'
        target.write_bytes(b'must remain until closed')
        with patch.object(vm, 'WORK', self.directory), patch.object(vm.subprocess, 'run', return_value=Mock(returncode=0, stdout=b'123')):
            with self.assertRaisesRegex(AssertionError, 'still open'):
                vm.reset_target()
        self.assertEqual(target.read_bytes(), b'must remain until closed')

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
        guest.transcript = ''
        guest.boot_transcript = ''
        guest.authentication_started = False
        guest.console = Mock()
        sequence = []
        def receive(_):
            guest.monitor.events.append(dict(event='SHUTDOWN', data=dict(guest=True, reason='guest-shutdown')))
            sequence.append('guest-shutdown')
            return b'reboot: Power down\n'
        guest.console.recv.side_effect = receive
        guest.writes = lambda stage: sequence.append('final-write-audit')
        def command(name):
            sequence.append(name)
            guest.monitor.events.append(dict(event='SHUTDOWN', data=dict(guest=False, reason='host-qmp-quit')))
        guest.monitor.command.side_effect = command
        guest.process.wait.side_effect = lambda **kwargs: sequence.append('process-exited')
        with patch.object(vm, 'EVIDENCE', self.directory):
            guest.finish_shutdown('fixture', 'guest-shutdown')
        self.assertEqual(sequence, ['guest-shutdown', 'final-write-audit', 'quit', 'process-exited'])
        self.assertIn('Power down', guest.boot_transcript)
        self.assertTrue(guest.stopped_events_verified)
        self.assertEqual(len(guest.stopped_events), 1)
        self.assertEqual(len(guest.monitor.events), 2)

    def test_host_shutdown_cannot_be_accepted_as_orderly_guest_shutdown(self):
        guest = object.__new__(vm.Guest)
        guest.monitor = Mock(events=[dict(event='SHUTDOWN', data=dict(guest=False, reason='host-signal'))])
        guest.writes = Mock()
        with self.assertRaises(AssertionError):
            guest.finish_shutdown('fixture', 'guest-shutdown')
        guest.writes.assert_not_called()

    def test_loop_backing_verification_uses_json_list_mode_and_refuses_wrong_file(self):
        path = self.directory / 'protected.raw'
        response = dict(loopdevices=[{'name': '/dev/loop9', 'back-file': str(path)}])
        with patch('prepare_two_disks.subprocess.check_output', return_value=json.dumps(response).encode()) as command:
            verify_loop('/dev/loop9', path)
            self.assertEqual(command.call_args.args[0], ['losetup', '--list', '--json', '--output', 'NAME,BACK-FILE', '/dev/loop9'])
        response['loopdevices'][0]['back-file'] = str(self.directory / 'wrong.raw')
        with patch('prepare_two_disks.subprocess.check_output', return_value=json.dumps(response).encode()):
            with self.assertRaisesRegex(AssertionError, 'Unexpected loop backing'):
                verify_loop('/dev/loop9', path)

    def test_german_console_input_translates_the_actual_recovery_commands(self):
        self.assertEqual(vm.german_keys('/'), ['shift', '7'])
        self.assertEqual(vm.german_keys('-'), ['slash'])
        self.assertEqual(vm.german_keys('y'), ['z'])
        self.assertEqual(vm.german_keys('z'), ['y'])
        self.assertEqual(vm.german_keys('a'), ['a'])

    def test_kickstart_limits_clear_selection_and_bootloader_to_recorded_target(self):
        for target in ('vda', 'vdb'):
            recipe = vm.kickstart(target, '@HASH@')
            self.assertIn(f'ignoredisk --only-use={target}\n', recipe)
            self.assertIn(f'clearpart --all --initlabel --drives={target}\n', recipe)
            self.assertIn(f'bootloader --boot-drive={target} ', recipe)
            self.assertIn('%include /usr/share/anaconda/interactive-defaults.ks', recipe)
            self.assertNotIn('zerombr', recipe)
        with self.assertRaises(AssertionError):
            vm.kickstart('vda,vdb', '@HASH@')

    def test_actual_iso_help_blocks_unsupported_live_kickstart_before_installation(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        actual = (root / 'os/manifest/ci/11/full-2/two-disk/protected-first-install-cli.txt').read_text(encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, 'does not support live kickstart'):
            vm.require_supported_live_kickstart(actual)
        with self.assertRaises(AssertionError):
            vm.require_supported_live_kickstart('unrelated help')

    def test_iso_contains_parser_modules_but_not_the_assumed_validator_executable(self):
        root = pathlib.Path(__file__).resolve().parents[2]
        with zipfile.ZipFile(root / 'reviews/11-two-disk-rehearsal/artifacts/inspect-2-two-disk-evidence.zip') as archive:
            actual = archive.read('installer/squashfs-files.txt').decode()
        self.assertIn('squashfs-root/usr/lib/python3.14/site-packages/pykickstart/parser.py\n', actual)
        self.assertIn('squashfs-root/usr/lib/python3.14/site-packages/pykickstart/version.py\n', actual)
        self.assertNotIn('squashfs-root/usr/bin/ksvalidator\n', actual)

    def test_bls_ostree_option_never_consumes_the_next_line_or_accepts_ambiguity(self):
        text = 'title Recorded stock\nversion 1\noptions quiet ostree=/ostree/boot.1/default/kernel/0\nlinux /kernel/vmlinuz\n'
        self.assertEqual(vm.bls_identity(text), dict(title='Recorded stock', ostree='/ostree/boot.1/default/kernel/0'))
        for wrong in (text.replace(' ostree=', ' omitted='), text.replace('quiet ', 'quiet ostree=/ostree/other '), text + 'title Duplicate\n'):
            with self.assertRaises(AssertionError):
                vm.bls_identity(wrong)
