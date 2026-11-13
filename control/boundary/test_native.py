"""Regression mutations for the REVIEW-2 and REVIEW-3 false-pass findings."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import native
from boundary_assertions import validate_sandbox_result, policy_mounts, mount_view


CONTAINER = {'namespaces': {'net': 'net:[1]', 'mnt': 'mnt:[1]'}, 'cap_eff': '0',
             'seccomp': ['Seccomp: 0', 'Seccomp_filters: 0']}
ISOLATED = {'namespaces': {'net': 'net:[2]', 'mnt': 'mnt:[2]'}, 'cap_eff': '0',
            'seccomp': ['Seccomp: 2', 'Seccomp_filters: 2']}


class NativePolicyFixture(unittest.TestCase):
    def test_synthetic_env_and_grants_restore_on_session_exception(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            policy = root / 'managed-settings.json'
            original = json.dumps({'permissions': {'ask': ['mcp__testapp__send']}, 'hooks': {}}).encode()
            policy.write_bytes(original)
            with patch.multiple(native, ROOT=root, OUT=root, POLICY=policy), \
                 patch.object(native, 'ThreadingHTTPServer', return_value=Mock()), \
                 patch.object(native.threading, 'Thread', return_value=Mock()):
                with self.assertRaisesRegex(RuntimeError, 'Synthetic interrupted session'):
                    with native.Session([], 'fixture', grants=('/usr/bin/python3 -I boundary-hostile.py',)):
                        installed = json.loads(policy.read_bytes())
                        self.assertEqual(installed['permissions']['ask'], ['mcp__testapp__send'])
                        self.assertEqual(installed['permissions']['allow'], ['Bash(/usr/bin/python3 -I boundary-hostile.py)'])
                        self.assertNotIn('sandbox', installed)
                        raise RuntimeError('Synthetic interrupted session')
            self.assertEqual(policy.read_bytes(), original)


def result(identity=ISOLATED, sockets=None):
    sockets = sockets if sockets is not None else [{'family': f, 'errno': 1} for f in ('AF_UNIX', 'AF_VSOCK')]
    return {'content': 'SANDBOX_IDENTITY ' + json.dumps(identity) + '\n' +
            '\n'.join('SOCKET_STATE ' + json.dumps(s) for s in sockets)}


class EvidenceChecks(unittest.TestCase):
    def test_isolated_execution_and_explicit_denial(self):
        self.assertEqual(validate_sandbox_result(result(), CONTAINER), ISOLATED)
        self.assertIsNone(validate_sandbox_result({'is_error': True, 'content': 'requires approval'}, CONTAINER))

    def test_unsandboxed_execution_is_rejected(self):
        with self.assertRaises(AssertionError):
            validate_sandbox_result(result(CONTAINER, [{'family': f, 'created': True}
                                     for f in ('AF_UNIX', 'AF_VSOCK')]), CONTAINER)

    def test_each_identity_and_socket_failure_is_rejected(self):
        for namespace in ('net', 'mnt'):
            identity = copy.deepcopy(ISOLATED)
            identity['namespaces'][namespace] = CONTAINER['namespaces'][namespace]
            with self.subTest(namespace=namespace), self.assertRaises(AssertionError):
                validate_sandbox_result(result(identity), CONTAINER)
        for seccomp in (['Seccomp: 0', 'Seccomp_filters: 2'], ['Seccomp: 2', 'Seccomp_filters: 0'], ['Seccomp: 2']):
            with self.subTest(seccomp=seccomp), self.assertRaises((AssertionError, KeyError)):
                validate_sandbox_result(result(dict(ISOLATED, seccomp=seccomp)), CONTAINER)
        for family in ('AF_UNIX', 'AF_VSOCK'):
            sockets = [{'family': f, 'errno': 1 if f != family else 13} for f in ('AF_UNIX', 'AF_VSOCK')]
            with self.subTest(family=family), self.assertRaises(AssertionError):
                validate_sandbox_result(result(sockets=sockets), CONTAINER)

    def test_filter_count_must_exceed_container(self):
        with self.assertRaises(AssertionError):
            validate_sandbox_result(result(), dict(CONTAINER, seccomp=['Seccomp: 2', 'Seccomp_filters: 2']))
        with self.assertRaises(AssertionError):
            validate_sandbox_result(result(dict(ISOLATED, cap_eff='80000')), CONTAINER)

    def test_effective_overmount_wins_and_view_keeps_access_mode(self):
        mounts = ('1 0 0:1 / / ro - overlay overlay rw\n'
                  '2 1 0:1 /work /work rw - overlay overlay rw\n'
                  '3 2 0:1 /work /work ro - overlay overlay rw\n')
        settings = {'sandbox': {'filesystem': {'denyRead': [], 'allowRead': ['/work'], 'denyWrite': ['/work']}}}
        self.assertEqual(policy_mounts(mounts, settings)['denyWrite:/work']['view'], 'read-only')
        self.assertNotEqual(mount_view(mounts), mount_view(mounts.replace('3 2 0:1 /work /work ro',
                                                                                  '3 2 0:1 /work /work rw')))

    def test_reparented_read_only_mount_under_covered_parent_is_detected(self):
        # REVIEW-3: every field except the read-only work mount's parent stays
        # identical. The old destination-only comparison accepted this escape.
        mounts = ('1 0 0:1 / / ro - overlay overlay rw\n'
                  '2 1 0:1 /work /home/work rw - overlay overlay rw\n'
                  '3 2 0:1 /work /home/work rw - overlay overlay rw\n'
                  '4 1 0:2 / /home rw - tmpfs tmpfs rw\n'
                  '5 4 0:1 /work /home/work rw - overlay overlay rw\n'
                  '6 5 0:1 /work /home/work rw - overlay overlay rw\n'
                  '7 6 0:1 /work /home/work ro - overlay overlay rw\n')
        changed = mounts.replace('7 6 ', '7 3 ')
        settings = {'sandbox': {'filesystem': {'denyRead': [], 'allowRead': ['/home/work'],
                                              'denyWrite': ['/home/work/new/file']}}}
        self.assertNotEqual(mount_view(mounts), mount_view(changed))
        self.assertEqual(policy_mounts(mounts, settings)['allowRead:/home/work']['view'], 'read-only')
        self.assertEqual(policy_mounts(changed, settings)['allowRead:/home/work']['view'], 'writable')
        self.assertEqual(policy_mounts(changed, settings)['denyWrite:/home/work/new/file']['view'], 'writable')

    def test_writable_overmount_covers_read_only_policy_path_in_any_line_order(self):
        lines = ['1 0 0:1 / / ro - overlay overlay rw',
                 '2 1 0:1 /work /work ro - overlay overlay rw',
                 '3 2 0:1 /work /work rw - overlay overlay rw']
        settings = {'sandbox': {'filesystem': {'denyRead': [], 'allowRead': [], 'denyWrite': ['/work']}}}
        for order in (lines, lines[::-1], [lines[2], lines[0], lines[1]]):
            with self.subTest(order=order):
                self.assertEqual(policy_mounts('\n'.join(order), settings)['denyWrite:/work']['view'], 'writable')
                self.assertEqual(mount_view('\n'.join(order)), mount_view('\n'.join(lines)))

    def test_full_tree_preserves_covered_mounts_propagation_and_super_options(self):
        mounts = ('1 0 0:1 / / ro shared:9 - overlay overlay rw\n'
                  '2 1 0:2 / /work ro master:9 - tmpfs tmpfs rw,size=4k\n'
                  '3 2 0:1 /work /work rw - overlay overlay rw\n')
        for changed in (mounts.replace('2 1 0:2 / /work ro', '2 1 0:2 / /work rw'),
                        mounts.replace('master:9', 'master:8'), mounts.replace('shared:9', 'shared:8'),
                        mounts.replace('size=4k', 'size=8k'), mounts.replace('0:2', '0:3'),
                        mounts.replace('/work /work rw', '/other /work rw'),
                        mounts.replace('- tmpfs tmpfs', '- tmpfs other'),
                        mounts.replace('- tmpfs tmpfs', '- ramfs tmpfs'),
                        mounts.replace('2 1 0:2 / /work ro master:9 - tmpfs tmpfs rw,size=4k\n', '').replace('3 2 ', '3 1 ')):
            with self.subTest(changed=changed):
                self.assertNotEqual(mount_view(mounts), mount_view(changed))

    def test_only_session_fields_and_id_numbering_are_normalized(self):
        mounts = ('1 0 0:1 / / ro - overlay overlay rw\n'
                  '2 1 0:1 /tmp/claude-10001/-home-assistant-work/12345678-1234-1234-1234-123456789abc '
                  '/session ro - overlay overlay rw\n'
                  '3 1 0:1 /tmp/claude-http-abcd.sock /proxy ro - overlay overlay rw\n')
        renumbered = mounts.replace('1 0 ', '90 89 ').replace('2 1 ', '12 90 ').replace('3 1 ', '11 90 ')
        changed = renumbered.replace('12345678-1234-1234-1234-123456789abc',
                                     'abcdef12-abcd-abcd-abcd-abcdef123456').replace('http-abcd.sock', 'http-1234.sock')
        self.assertEqual(mount_view(mounts), mount_view(changed))
        self.assertNotEqual(mount_view(mounts), mount_view(mounts.replace('/session', '/other')))

    def test_mount_path_escapes_superblock_read_only_and_invalid_trees(self):
        mounts = ('1 0 0:1 / / rw - overlay overlay rw\n'
                  '2 1 0:2 /work /work\\040space rw - ext4 /dev/root ro\n')
        settings = {'sandbox': {'filesystem': {'denyRead': [], 'allowRead': [],
                                              'denyWrite': ['/work space/file']}}}
        self.assertEqual(policy_mounts(mounts, settings)['denyWrite:/work space/file']['view'], 'read-only')
        for changed in (mounts + mounts.splitlines()[0], mounts.replace('2 1 ', '2 2 '),
                        mounts.replace('2 1 ', '2 3 ')):
            with self.subTest(changed=changed), self.assertRaises(AssertionError):
                mount_view(changed)


if __name__ == '__main__':
    unittest.main()
