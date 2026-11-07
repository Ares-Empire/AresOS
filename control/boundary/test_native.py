"""Regression mutations for the two REVIEW-2 false-pass findings."""
import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native
from boundary_assertions import validate_sandbox_result, require_source_positive, policy_mounts, mount_view


CONTAINER = {'namespaces': {'net': 'net:[1]', 'mnt': 'mnt:[1]'}, 'cap_eff': '0',
             'seccomp': ['Seccomp: 0', 'Seccomp_filters: 0']}
ISOLATED = {'namespaces': {'net': 'net:[2]', 'mnt': 'mnt:[2]'}, 'cap_eff': '0',
            'seccomp': ['Seccomp: 2', 'Seccomp_filters: 2']}


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


if __name__ == '__main__':
    unittest.main()
