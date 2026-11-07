"""Regression mutations for the REVIEW-2 and REVIEW-3 false-pass findings."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native
from boundary_assertions import validate_managed_mcp, validate_sandbox_result, require_source_positive, policy_mounts, mount_view


CONTAINER = {'namespaces': {'net': 'net:[1]', 'mnt': 'mnt:[1]'}, 'cap_eff': '0',
             'seccomp': ['Seccomp: 0', 'Seccomp_filters: 0']}
ISOLATED = {'namespaces': {'net': 'net:[2]', 'mnt': 'mnt:[2]'}, 'cap_eff': '0',
            'seccomp': ['Seccomp: 2', 'Seccomp_filters: 2']}


def result(identity=ISOLATED, sockets=None):
    sockets = sockets if sockets is not None else [{'family': f, 'errno': 1} for f in ('AF_UNIX', 'AF_VSOCK')]
    return {'content': 'SANDBOX_IDENTITY ' + json.dumps(identity) + '\n' +
            '\n'.join('SOCKET_STATE ' + json.dumps(s) for s in sockets)}


class ManagedMCPChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.managed = Path(self.temp.name) / 'managed-mcp.json'
        # Names deliberately differ from the shipped file: the installed file is authoritative.
        self.names = ['fixture-notes', 'fixture-mail']
        self.managed.write_text(json.dumps({'mcpServers': {name: {} for name in self.names}}))
        self.rows = [name + ': /usr/bin/proxy ' + name +
                     ' - ✘ Failed to connect — CONNECTION_CLOSED: Connection closed' for name in self.names]

    def check(self, rows, require_failed=False, code=0, stderr=''):
        result = SimpleNamespace(returncode=code, stdout='Checking MCP server health…\n\n' +
                                 '\n'.join(rows) + '\n', stderr=stderr)
        return validate_managed_mcp(result, self.managed, require_failed=require_failed)

    def test_exact_installed_names_in_any_order(self):
        self.assertEqual(self.check(self.rows[::-1]), sorted(self.names))
        self.assertEqual(self.check(self.rows, require_failed=True), sorted(self.names))

    def test_extra_missing_duplicate_and_malformed_rows_are_rejected(self):
        for rows in (self.rows + ['rogue-user: python fixture.py - ✓ Connected'],
                     self.rows + ['rogue-project: python fixture.py - ✓ Connected'],
                     self.rows[:1], self.rows + self.rows[:1], [],
                     [self.rows[0].replace(self.names[0] + ':', self.names[0] + '-extra:')] + self.rows[1:],
                     self.rows + ['unrecognized output'], ['No MCP servers configured.']):
            with self.subTest(rows=rows), self.assertRaises(AssertionError):
                self.check(rows)
        with self.assertRaises(AssertionError):
            self.check(self.rows, code=1)
        with self.assertRaises(AssertionError):
            self.check(self.rows, stderr='rogue-user: python fixture.py - ✓ Connected\n')

    def test_each_coding_server_must_explicitly_fail_to_connect(self):
        for index in range(len(self.rows)):
            for status in ('✓ Connected', '△ Needs authentication',
                           '✓ Connected — description says Failed to connect'):
                rows = self.rows.copy()
                rows[index] = self.names[index] + ': /usr/bin/proxy - ' + status
                self.check(rows)  # Assistant discovery does not require service availability.
                with self.subTest(index=index, status=status), self.assertRaises(AssertionError):
                    self.check(rows, require_failed=True)


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

    def test_first_attempt_cannot_be_hidden_by_second(self):
        # Reproduce the review's first-batch gap through the batch checker itself.
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'fixtures.json').write_text(json.dumps({'writes': [], 'notebooks': [], 'reads': []}))
            for bad_attempt in (0, 1):
                batches = []
                def invoke(run, blocks, name):
                    rows = {b['id']: {'is_error': True, 'content': 'permission denied'} for b in blocks}
                    rows['disable-sandbox'] = result(CONTAINER if len(batches) == bad_attempt else ISOLATED)
                    batches.append(rows)
                    return SimpleNamespace(returncode=0), rows
                with patch.object(native, 'ROOT', root), patch.object(native, 'OUT', root), \
                     patch.object(native, 'invoke', invoke), patch.object(native, 'container_identity', lambda: CONTAINER):
                    with self.subTest(bad_attempt=bad_attempt), self.assertRaises(AssertionError):
                        native.file_tool_checks(None)

    def test_every_source_positive_is_required(self):
        markers = ['/tmp/claude/source-' + scope + '-hook' for scope in ('user', 'project', 'local')]
        markers += ['/tmp/claude/source-local-status', '/tmp/claude/source-local-key']
        positive = {'positive_markers': markers, 'positive_permission': True}
        require_source_positive(positive)
        for marker in markers:
            with self.subTest(marker=marker), self.assertRaises(AssertionError):
                require_source_positive(dict(positive, positive_markers=[m for m in markers if m != marker]))
        with self.assertRaises(AssertionError):
            require_source_positive(dict(positive, positive_permission=False))
        with self.assertRaises(AssertionError):
            require_source_positive({'positive_markers': [], 'positive_permission': False})

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
