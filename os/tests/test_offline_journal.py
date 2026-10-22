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
from offline_journal import (JOURNAL_PATHS, POWER_KEY, SHUTDOWN, OfflineJournalUnavailable,
                             assert_power_key_shutdown, check_offline_poweroff)


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
                 missing_boot=False, records=None, timeout=False, mounted=False, missing_podman=False):
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
                    output = json.dumps({'blockdevices': [{'children': [{'name': '/dev/nbd0p4', 'fstype': 'btrfs'}]}]}).encode()
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
            with patch('offline_journal.subprocess.run', side_effect=execute), \
                    patch('pathlib.Path.is_mount', side_effect=[False, mounted]):
                return check_offline_poweroff(disk, work, evidence, self.boot)

    def test_fallback_verifies_before_selecting_exact_boot(self):
        self.assertEqual(self.exercise()['status'], 'passed')
        self.assertLess(self.calls.index('verify'), self.calls.index('list-boots'))
        self.assertLess(self.calls.index('list-boots'), self.calls.index('boot-json'))
        self.assertEqual(self.calls[-1], 'disconnect')

    def test_every_reader_command_error_and_timeout_is_blocking(self):
        for failure in ('qemu-nbd', 'udevadm', 'lsblk', 'blockdev', 'dmesg', 'btrfs-version',
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


if __name__ == '__main__':
    unittest.main()
