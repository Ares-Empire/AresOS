"""Apply the real boot rule to inherited, separately owned Homebrew state.

Owner, 2026-11-09: the daily account uses Homebrew. The prefix stays owned by
the stock UID 1000 administrator for rollback; UID 1001 may read and run it,
never write it, and an earlier image's deny entry is replaced at boot.
"""
import os
import pathlib
import struct
import subprocess
import tempfile
import unittest


RULE = pathlib.Path(__file__).resolve().parents[1] / 'config/usr/lib/tmpfiles.d/aresos-inherited-homebrew.conf'
READ_EXECUTE = 5


class InheritedHomebrewTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = pathlib.Path(self.directory.name)
        self.addCleanup(subprocess.run, ['sudo', '-n', 'chown', '-R',
                                        f'{os.getuid()}:{os.getgid()}', str(self.root)], check=True)
        self.root.chmod(0o755)
        (self.root / 'etc').mkdir()
        (self.root / 'etc/passwd').write_text('ares:x:1001:1001::/var/home/ares:/bin/bash\n')
        (self.root / 'etc/group').write_text('ares:x:1001:\n')
        self.prefix = self.root / 'var/home/linuxbrew'

    def tmpfiles(self, rule=RULE):
        result = subprocess.run(['sudo', '-n', 'systemd-tmpfiles', '--root=' + str(self.root),
                                 '--create', str(rule)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def as_uid(self, uid, *command):
        return subprocess.run(['sudo', '-n', 'setpriv', '--reuid=' + str(uid),
                               '--regid=' + str(uid), '--clear-groups', *map(str, command)],
                              capture_output=True, text=True)

    def installation(self):
        binary = self.prefix / '.linuxbrew/bin/brew'
        binary.parent.mkdir(parents=True)
        binary.write_text('#!/bin/sh\nprintf "INHERITED_BREW_FIXTURE\\n"\n')
        binary.chmod(0o755)
        self.prefix.chmod(0o755)  # as recorded on a real switched system (06c)
        # Match the installed root-owned ancestry. tmpfiles correctly rejects
        # traversal from a non-root owner's parent into another user's tree.
        subprocess.run(['sudo', '-n', 'chown', '0:0', str(self.root),
                        str(self.root / 'var'), str(self.root / 'var/home')], check=True)
        subprocess.run(['sudo', '-n', 'chown', '-R', '1000:1000', str(self.prefix)], check=True)
        return binary

    def acl(self):
        raw = os.getxattr(self.prefix, 'system.posix_acl_access')
        self.assertEqual(struct.unpack('<I', raw[:4]), (2,))
        return {(tag, uid): permission for tag, permission, uid in struct.iter_unpack('<HHI', raw[4:])}

    def assert_daily_reads_and_runs_but_cannot_write(self, binary, contents, owner_before):
        self.assertEqual(self.as_uid(1001, binary).stdout, 'INHERITED_BREW_FIXTURE\n')
        self.assertEqual(self.as_uid(1001, 'test', '-r', binary).returncode, 0)
        self.assertNotEqual(self.as_uid(1001, 'test', '-w', self.prefix).returncode, 0)
        self.assertNotEqual(self.as_uid(1001, 'touch', self.prefix / 'daily-write').returncode, 0)
        self.assertNotEqual(self.as_uid(1001, 'touch', binary.parent / 'daily-write').returncode, 0)
        self.assertEqual(self.as_uid(1000, binary).stdout, 'INHERITED_BREW_FIXTURE\n')
        self.assertEqual(self.as_uid(1000, 'test', '-w', self.prefix).returncode, 0)
        self.assertEqual(self.prefix.stat().st_uid, owner_before)
        self.assertEqual(self.as_uid(1000, 'cat', binary).stdout.encode(), contents)
        self.assertEqual(self.acl()[(2, 1001)], READ_EXECUTE)

    def test_daily_account_reads_and_runs_without_write_and_owner_unchanged_idempotently(self):
        binary = self.installation()
        contents = binary.read_bytes()
        owner_before = self.prefix.stat().st_uid
        for _ in range(2):
            self.tmpfiles()
            self.assert_daily_reads_and_runs_but_cannot_write(binary, contents, owner_before)

    def test_replaces_the_deny_entry_left_by_earlier_images(self):
        binary = self.installation()
        contents = binary.read_bytes()
        earlier = self.root / 'etc/earlier.conf'
        earlier.write_text('a+ /var/home/linuxbrew - - - - u:1001:---\n')
        self.tmpfiles(earlier)
        self.assertEqual(self.acl()[(2, 1001)], 0)
        self.assertNotEqual(self.as_uid(1001, binary).returncode, 0)
        self.tmpfiles()
        self.assert_daily_reads_and_runs_but_cannot_write(binary, contents, 1000)

    def test_preserves_existing_acl_entries_and_restrictive_mask(self):
        binary = self.installation()
        existing = self.root / 'etc/existing.conf'
        existing.write_text('a+ /var/home/linuxbrew - - - - u:1002:rwx,m::r-x\n')
        self.tmpfiles(existing)
        before = self.acl()
        self.tmpfiles()
        after = self.acl()
        self.assertEqual({key: value for key, value in after.items() if key != (2, 1001)}, before)
        self.assertEqual(after[(2, 1001)], READ_EXECUTE)
        self.assertEqual(self.as_uid(1001, binary).returncode, 0)
        self.assertNotEqual(self.as_uid(1001, 'test', '-w', self.prefix).returncode, 0)
        self.assertEqual(self.as_uid(1000, binary).returncode, 0)

    def test_absent_inherited_installation_is_not_created(self):
        self.tmpfiles()
        self.assertFalse(self.prefix.exists())
