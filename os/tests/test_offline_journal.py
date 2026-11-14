import copy
import json
import pathlib
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'ci'))
import offline_journal
from offline_journal import (JOURNAL_PATHS, PARTITION_WAIT_SECONDS, POWER_KEY, SHUTDOWN,
                             OfflineJournalUnavailable, assert_power_key_shutdown, check_offline_poweroff)

PARTITIONS = [f'/dev/nbd0p{number}' for number in range(1, 5)]
# The guest disk's layout: BIOS boot (no filesystem), ESP, /boot, root.
DISK_TYPES = dict(zip(PARTITIONS, (None, 'vfat', 'ext4', 'btrfs')))


def blkid_export(name, kind, number=None):
    """blkid -p -o export on a GPT partition: its own entry always, TYPE only with a signature."""
    number = number or name.rsplit('p', 1)[1]
    lines = [f'DEVNAME={name}'] + ([f'TYPE={kind}'] if kind else []) + [
        'PART_ENTRY_SCHEME=gpt', 'PART_ENTRY_UUID=00000000-0000-0000-0000-00000000000' + number,
        f'PART_ENTRY_NUMBER={number}', 'PART_ENTRY_DISK=43:0']
    return ('\n'.join(lines) + '\n').encode()


class OfflineJournalTest(unittest.TestCase):
    boot = 'a' * 32

    def test_restore_filter_descends_only_toward_persistent_journals(self):
        for prefix in ('/var/log/journal', '/ostree/deploy/default/var/log/journal'):
            parts = prefix.strip('/').split('/')
            paths = ['/'] + ['/' + '/'.join(parts[:index]) for index in range(1, len(parts) + 1)]
            paths += [prefix + '/machine-id/system.journal', prefix + '/machine-id/system@old.journal']
            for path in paths:
                self.assertIsNotNone(re.fullmatch(JOURNAL_PATHS, path), path)
        for path in ('/usr', '/ostree/repo', '/ostree/deploy/default/deploy', '/var/home', '/var/log/audit'):
            self.assertIsNone(re.fullmatch(JOURNAL_PATHS, path), path)

    def records(self):
        records = [
            dict(SYSLOG_IDENTIFIER='aresos-ci', MESSAGE='ARESOS_POWER_KEY_ARMED'),
            dict(_SYSTEMD_UNIT='systemd-logind.service', MESSAGE_ID=POWER_KEY, MESSAGE='Power key pressed short.'),
            dict(_SYSTEMD_UNIT='systemd-logind.service', MESSAGE_ID=SHUTDOWN, SHUTDOWN='power-off'),
            dict(_PID='1', UNIT='systemd-logind.service', JOB_TYPE='stop', JOB_RESULT='done',
                 MESSAGE='Stopped systemd-logind.service - User Login Management.'),
        ]
        for index, record in enumerate(records):
            record.update(_BOOT_ID=self.boot, __MONOTONIC_TIMESTAMP=str(100 + index))
        return records

    def test_ordered_logind_and_manager_records_from_exact_boot_pass(self):
        summary = assert_power_key_shutdown(self.records(), self.boot)
        self.assertEqual(summary['power_key']['MESSAGE_ID'], POWER_KEY)
        self.assertEqual(summary['logind_stopped']['JOB_RESULT'], 'done')

    def test_missing_records_and_other_boot_cannot_pass(self):
        records = self.records()
        for index in range(len(records)):
            with self.subTest(missing=index), self.assertRaises(AssertionError):
                assert_power_key_shutdown(records[:index] + records[index + 1:], self.boot)
        with self.assertRaises(AssertionError):
            assert_power_key_shutdown(records, 'b' * 32)

    def test_old_key_wrong_service_spoofed_text_and_failed_teardown_fail(self):
        for index, changes in [(1, {'__MONOTONIC_TIMESTAMP': '99'}),
                               (1, {'_SYSTEMD_UNIT': 'aresos-ci.service'}),
                               (1, {'MESSAGE_ID': 'untrusted text'}),
                               (2, {'SHUTDOWN': 'reboot'}),
                               (2, {'__MONOTONIC_TIMESTAMP': '99'}),
                               (3, {'JOB_RESULT': 'failed'}), (3, {'_PID': '42'}),
                               (3, {'__MONOTONIC_TIMESTAMP': '99'})]:
            records = copy.deepcopy(self.records())
            records[index].update(changes)
            with self.subTest(changes=changes), self.assertRaises(AssertionError):
                assert_power_key_shutdown(records, self.boot)

    def test_only_unreadable_journal_is_reported_as_hardware_gate(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': ''}):
            evidence = pathlib.Path(directory)
            with patch('offline_journal.read_offline_journal', side_effect=OfflineJournalUnavailable('reader failed')):
                result = check_offline_poweroff(None, None, evidence, self.boot)
                self.assertEqual(result['status'], 'REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE')
                self.assertIn('reader failed', (evidence / 'offline-poweroff-check.json').read_text())
            with patch('offline_journal.read_offline_journal', return_value={'boot_id': self.boot}):
                self.assertEqual(check_offline_poweroff(None, None, evidence, self.boot)['status'], 'passed')
            for error in (AssertionError('missing logind record'), RuntimeError('unexpected reader failure'),
                          OSError('cleanup failure')):
                with self.subTest(error=error), patch('offline_journal.read_offline_journal', side_effect=error):
                    with self.assertRaises(type(error)):
                        check_offline_poweroff(None, None, evidence, self.boot)


class OfflineReaderCommandsTest(unittest.TestCase):
    """Exercise the actual reader/classifier with only its OS commands replaced."""
    boot = OfflineJournalTest.boot

    def exercise(self, failure=None, *, unsupported=True, absent=False, missing_journals=False,
                 missing_boot=False, records=None, timeout=False, mounted=False, missing_podman=False,
                 disk_types=DISK_TYPES, listings=None, udev_types=None, nodes_at=None, gone_after_probe=(),
                 blkid_results=None):
        """disk_types: the filesystem on each partition (None: no signature).
        listings: the partitions each successive lsblk call lists (the last one repeats).
        udev_types: lsblk's FSTYPE per partition; null everywhere by default, as on run 43548237383.
        nodes_at: the fake clock's second at which a partition's node appears (default 0).
        gone_after_probe: partitions whose nodes vanish once blkid has run.
        blkid_results: blkid's raw (exit code, stdout, stderr) per partition instead of a clean probe."""
        listings = listings or [list(disk_types)]
        udev_types, nodes_at, blkid_results = udev_types or {}, nodes_at or {}, blkid_results or {}
        self.argv, self.blkid_at, self.disk_types_evidence = [], [], None
        clock = self.clock = [0.0]
        with tempfile.TemporaryDirectory() as temporary, patch.dict('os.environ', {'GITHUB_STEP_SUMMARY': ''}):
            work = pathlib.Path(temporary)
            evidence = work / 'evidence'
            evidence.mkdir()
            disk = work / 'guest.qcow2'
            disk.touch()
            journal = work / ('offline-root' if mounted else f'offline-restore-{self.boot}') / 'var/log/journal'
            calls = []

            def execute(args, **kwargs):
                args = list(args)
                self.argv.append(args)
                if args[0] == 'podman':
                    entrypoint = args[args.index('--entrypoint') + 1]
                    if entrypoint.endswith('btrfs'):
                        label = ('btrfs-roots' if '--list-roots' in args else 'btrfs-restore'
                                 if 'restore' in args else 'btrfs-check' if 'check' in args else 'btrfs-version')
                    else:
                        label = ('journal-version' if '--version' in args else 'verify' if '--verify' in args
                                 else 'list-boots' if '--list-boots' in args else 'logind'
                                 if '--unit=systemd-logind.service' in args else 'boot-text'
                                 if '--output=short-monotonic' in args else 'boot-json')
                else:
                    label = 'disconnect' if '--disconnect' in args else args[0]
                calls.append(label)
                if missing_podman and args[0] == 'podman':
                    raise FileNotFoundError(2, 'No such file or directory', 'podman')
                if label == failure:
                    if timeout:
                        raise subprocess.TimeoutExpired(args, 120)
                    stderr = (b'stat /usr/bin/btrfs: no such file or directory' if label == 'btrfs-version'
                              else b'stat /usr/bin/journalctl: no such file or directory') if absent else b'real error'
                    return subprocess.CompletedProcess(args, 1, b'', stderr)
                output = b''
                if label == 'mount':
                    if not mounted:
                        return subprocess.CompletedProcess(args, 32, b'', b'mount failed')
                    if not missing_journals:
                        journal.mkdir(parents=True)
                        (journal / 'system.journal').write_bytes(b'journal fixture')
                if label == 'dmesg' and unsupported:
                    output = b"btrfs: Unknown parameter 'nologreplay'"
                elif label == 'lsblk':
                    listed = listings[min(calls.count('lsblk'), len(listings)) - 1]
                    output = json.dumps({'blockdevices': [{'name': '/dev/nbd0', 'fstype': None, 'ro': True, 'children': [
                        {'name': name, 'fstype': udev_types.get(name), 'ro': True} for name in listed]}]}).encode()
                elif label == 'blkid':
                    self.blkid_at.append(clock[0])
                    name = args[-1]
                    return subprocess.CompletedProcess(args, *blkid_results.get(
                        name, (0, blkid_export(name, disk_types.get(name)), b'')))
                elif label == 'blockdev':
                    output = b'1'
                elif label == 'btrfs-roots':
                    output = b'tree key (256 ROOT_ITEM 0)'
                elif label == 'btrfs-restore' and not missing_journals:
                    journal.mkdir(parents=True)
                    (journal / 'system.journal').write_bytes(b'journal fixture')
                elif label == 'find' and not missing_journals:
                    output = str(journal).encode()
                elif label == 'list-boots':
                    output = f'0 {"b" * 32 if missing_boot else self.boot} Thu'.encode()
                elif label == 'boot-json':
                    output = b'\n'.join(json.dumps(r).encode() for r in
                                        (OfflineJournalTest().records() if records is None else records))
                return subprocess.CompletedProcess(args, 0, output, b'')

            self.calls = calls
            try:
                with patch('offline_journal.subprocess.run', side_effect=execute), \
                        patch('pathlib.Path.is_mount', side_effect=[False, mounted]), \
                        patch('offline_journal.block_node', side_effect=lambda name: clock[0] >= nodes_at.get(name, 0)
                              and not (name in gone_after_probe and self.blkid_at)), \
                        patch.object(offline_journal.time, 'monotonic', side_effect=lambda: clock[0]), \
                        patch.object(offline_journal.time, 'sleep',
                                     side_effect=lambda seconds: clock.__setitem__(0, clock[0] + seconds)):
                    return check_offline_poweroff(disk, work, evidence, self.boot)
            finally:
                types = evidence / 'offline-disk-types.json'
                if types.exists():
                    self.disk_types_evidence = json.loads(types.read_text())

    def test_fallback_verifies_before_selecting_exact_boot(self):
        self.assertEqual(self.exercise()['status'], 'passed')
        self.assertLess(self.calls.index('verify'), self.calls.index('list-boots'))
        self.assertLess(self.calls.index('list-boots'), self.calls.index('boot-json'))
        self.assertEqual(self.calls[-1], 'disconnect')

    def test_every_reader_command_error_and_timeout_is_blocking(self):
        for failure in ('qemu-nbd', 'udevadm', 'lsblk', 'blkid', 'blockdev', 'dmesg', 'btrfs-version',
                        'btrfs-check', 'btrfs-roots', 'btrfs-restore', 'find', 'journal-version',
                        'verify', 'list-boots', 'boot-json', 'boot-text', 'logind', 'disconnect'):
            for timeout in (False, True):
                with self.subTest(command=failure, timeout=timeout):
                    with self.assertRaises(subprocess.TimeoutExpired if timeout else AssertionError):
                        self.exercise(failure, timeout=timeout)

    def test_gate_requires_both_explicit_host_limitations(self):
        for reader in ('btrfs-version', 'journal-version'):
            with self.subTest(reader=reader):
                self.assertEqual(self.exercise(reader, absent=True)['status'],
                                 'REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE')
                with self.assertRaises(AssertionError):
                    self.exercise(reader, absent=True, unsupported=False)
                with self.assertRaises(AssertionError):
                    self.exercise(reader, absent=False)
        self.assertEqual(self.exercise(missing_podman=True)['status'],
                         'REPORTED_NOT_BLOCKING_FIRST_HARDWARE_BOOT_GATE')
        with self.assertRaises(FileNotFoundError):
            self.exercise(missing_podman=True, unsupported=False)

    def test_mounted_reader_and_cleanup_failures_are_blocking(self):
        self.assertEqual(self.exercise(mounted=True)['status'], 'passed')
        for command in ('findmnt', 'umount', 'journal-version', 'verify', 'list-boots', 'boot-json'):
            with self.subTest(command=command), self.assertRaises(AssertionError):
                self.exercise(command, mounted=True)
        with self.assertRaises(AssertionError):
            self.exercise('journal-version', mounted=True, absent=True)

    def test_missing_journals_boot_wrong_boot_or_any_required_record_is_blocking(self):
        for options in ({'missing_journals': True}, {'missing_boot': True}, {'records': []},
                        {'records': [dict(r, _BOOT_ID='b' * 32) for r in OfflineJournalTest().records()]},
                        *({'records': OfflineJournalTest().records()[:i] + OfflineJournalTest().records()[i + 1:]}
                          for i in range(4))):
            with self.subTest(options=options), self.assertRaises(AssertionError):
                self.exercise(**options)


class OfflineDiskProbeTest(unittest.TestCase):
    """The Btrfs root comes from blkid -p on the disk, never from udev's FSTYPE cache."""
    boot = OfflineJournalTest.boot
    exercise = OfflineReaderCommandsTest.exercise
    LAYOUT = ', '.join(f'{name}={kind or "none"}' for name, kind in DISK_TYPES.items())

    def probes(self):
        return [args for args in self.argv if args[0] == 'blkid']

    def root_used(self):
        getro, = [args for args in self.argv if args[0] == 'blockdev']
        mount, = [args for args in self.argv if args[0] == 'mount']
        self.assertEqual(getro[-1], mount[-2])
        return getro[-1]

    def assert_stopped_before_mount(self, probed=True):
        self.assertEqual(bool(self.probes()), probed)
        self.assertNotIn('blockdev', self.calls)
        self.assertNotIn('mount', self.calls)
        self.assertEqual(self.calls[-1], 'disconnect')

    def assert_not_ready(self, missing, **options):
        with self.assertRaisesRegex(AssertionError, f'not ready after {PARTITION_WAIT_SECONDS}s') as error:
            self.exercise(**options)
        self.assertEqual(self.clock[0], PARTITION_WAIT_SECONDS)
        self.assertEqual(str(error.exception).split('missing ', 1)[1], repr(missing))
        self.assert_stopped_before_mount(probed=False)
        return str(error.exception)

    def test_root_comes_from_blkid_probe_when_udev_has_no_types(self):
        self.assertEqual(self.exercise()['status'], 'passed')
        self.assertEqual(self.probes(), [['blkid', '-p', '-o', 'export', name] for name in PARTITIONS])
        self.assertEqual(self.root_used(), '/dev/nbd0p4')
        self.assertEqual({name: probe['tags'].get('TYPE') for name, probe in self.disk_types_evidence.items()},
                         DISK_TYPES)
        self.assertLess(self.calls.index('udevadm'), self.calls.index('lsblk'))
        self.assertLess(self.calls.index('lsblk'), self.calls.index('blkid'))
        # Listed again after probing, to prove the set did not change meanwhile.
        self.assertEqual(self.calls[self.calls.index('blkid') + 4], 'lsblk')

    def test_udev_types_are_never_trusted_over_the_disk(self):
        stale = dict(DISK_TYPES, **{'/dev/nbd0p3': 'btrfs', '/dev/nbd0p4': None})
        self.assertEqual(self.exercise(udev_types=stale)['status'], 'passed')
        self.assertEqual(self.root_used(), '/dev/nbd0p4')
        with self.assertRaisesRegex(AssertionError, 'blkid -p read .*/dev/nbd0p4=none'):
            self.exercise(udev_types=DISK_TYPES, disk_types=dict(DISK_TYPES, **{'/dev/nbd0p4': None}))

    def test_late_partition_node_is_waited_for_within_the_bound(self):
        self.assertEqual(self.exercise(nodes_at={'/dev/nbd0p4': 3})['status'], 'passed')
        self.assertGreater(self.calls.count('lsblk'), 2)
        self.assertEqual(self.blkid_at, [3.0] * 4, 'probed before every node existed')

    def test_node_that_never_appears_stops_at_the_bound_without_probing(self):
        self.assert_not_ready(['/dev/nbd0p2'], nodes_at={'/dev/nbd0p2': 60})
        self.assert_not_ready(PARTITIONS, nodes_at={name: 60 for name in PARTITIONS})
        message = self.assert_not_ready(PARTITIONS, listings=[[]])
        self.assertIn('listed []', message)

    def test_shrinking_list_cannot_skip_a_missing_partition(self):
        # The review's case: p2 listed without its node, then no longer listed at all.
        message = self.assert_not_ready(['/dev/nbd0p2'], nodes_at={'/dev/nbd0p2': 60},
                                        listings=[PARTITIONS, [p for p in PARTITIONS if p != '/dev/nbd0p2']])
        self.assertIn("listed ['/dev/nbd0p1', '/dev/nbd0p3', '/dev/nbd0p4']", message)

    def test_incomplete_list_cannot_hide_a_second_btrfs_root(self):
        partial = ['/dev/nbd0p1', '/dev/nbd0p2', '/dev/nbd0p4']
        self.assert_not_ready(['/dev/nbd0p3'], listings=[partial],
                              disk_types=dict(DISK_TYPES, **{'/dev/nbd0p3': 'btrfs'}))

    def test_growing_list_is_probed_only_once_complete(self):
        growing = [PARTITIONS[:1], PARTITIONS[:3], PARTITIONS]
        self.assertEqual(self.exercise(listings=growing)['status'], 'passed')
        self.assertEqual(self.blkid_at, [1.0] * 4)
        self.assertEqual(len(self.probes()), 4)
        # A partition beyond the layout is never ignored.
        message = self.assert_not_ready([], listings=[PARTITIONS + ['/dev/nbd0p5']])
        self.assertIn('/dev/nbd0p5', message)

    def test_partition_set_changing_while_probing_fails(self):
        for options in ({'listings': [PARTITIONS, PARTITIONS[1:]]}, {'gone_after_probe': ['/dev/nbd0p1']}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(AssertionError, 'changed while probing.*/dev/nbd0p1'):
                    self.exercise(**options)
                self.assert_stopped_before_mount()

    def test_zero_or_two_btrfs_roots_fail_naming_every_partition_type(self):
        for kinds in ((None, 'vfat', 'ext4', 'xfs'), (None, 'vfat', 'btrfs', 'btrfs'), ('btrfs', 'vfat', 'ext4', 'btrfs')):
            disk_types = dict(zip(PARTITIONS, kinds))
            with self.subTest(kinds=kinds):
                with self.assertRaises(AssertionError) as error:
                    self.exercise(disk_types=disk_types)
                expected, read = str(error.exception).split('; blkid -p read ')
                self.assertTrue(expected.endswith(self.LAYOUT), expected)
                self.assertEqual(read, ', '.join(f'{name}={kind or "none"}' for name, kind in disk_types.items()))
                self.assert_stopped_before_mount()

    def test_probe_errors_never_read_as_no_filesystem(self):
        root = '/dev/nbd0p4'
        for name, result in (
                # A failed probe prints nothing and exits 2, often without a message,
                # here on the partition that has no filesystem, next to a valid root.
                ('/dev/nbd0p1', (2, b'', b'')),
                ('/dev/nbd0p1', (2, b'', b'blkid: error: /dev/nbd0p1: Input/output error\n')),
                # Exit 2 with output, exit 8 (ambivalent) and other errors, even with the right TYPE.
                (root, (2, blkid_export(root, 'btrfs'), b'')),
                (root, (8, blkid_export(root, 'btrfs'), b'')),
                (root, (1, blkid_export(root, 'btrfs'), b'')),
                # Exit 0 without this partition's own GPT entry.
                (root, (0, b'TYPE=btrfs\n', b'')),
                (root, (0, blkid_export(root, 'btrfs', number='3'), b'')),
                (root, (0, blkid_export(root, 'btrfs').replace(b'SCHEME=gpt', b'SCHEME=dos'), b''))):
            with self.subTest(name=name, result=result):
                with self.assertRaisesRegex(AssertionError, f'blkid -p read .*{name}=unread \\(exit {result[0]}'):
                    self.exercise(blkid_results={name: result})
                self.assertEqual(self.disk_types_evidence[name]['returncode'], result[0])
                self.assert_stopped_before_mount()


if __name__ == '__main__':
    unittest.main()
