"""Fail-closed evidence checks, shared with regression tests."""
import json
import os
import re
from pathlib import Path


def container_identity():
    return {'namespaces': {n: os.readlink('/proc/self/ns/' + n) for n in ('net', 'mnt')},
            'seccomp': [s for s in Path('/proc/self/status').read_text().splitlines()
                        if s.startswith(('Seccomp:', 'Seccomp_filters:'))]}


def validate_identity(identity, container):
    assert int(identity['cap_eff'], 16) == 0, identity
    assert all(identity['namespaces'][n] != container['namespaces'][n] for n in ('net', 'mnt')), identity
    fields = dict(line.split(':', 1) for line in identity['seccomp'])
    outer = dict(line.split(':', 1) for line in container['seccomp'])
    assert int(fields['Seccomp']) == 2, identity
    assert int(fields['Seccomp_filters']) > int(outer.get('Seccomp_filters', '0')), identity


def tool_text(row):
    content = row.get('content', '')
    return content if isinstance(content, str) else '\n'.join(b.get('text', '') for b in content)


def validate_sandbox_result(row, container):
    content = tool_text(row)
    if 'SANDBOX_IDENTITY ' not in content:
        assert row.get('is_error') and any(word in content.lower() for word in
               ('approval', 'asks the person')), 'unexpected Bash result: ' + content
        return None  # An approval denial is retained as unqualified.
    assert not row.get('is_error'), content
    identities = [json.loads(s.split(' ', 1)[1]) for s in content.splitlines()
                  if s.startswith('SANDBOX_IDENTITY ')]
    assert len(identities) == 1, content
    validate_identity(identities[0], container)
    sockets = [json.loads(s.split(' ', 1)[1]) for s in content.splitlines() if s.startswith('SOCKET_STATE ')]
    assert len(sockets) == 2 and {s['family'] for s in sockets} == {'AF_UNIX', 'AF_VSOCK'}, sockets
    assert all(s.get('errno') == 1 and not s.get('created') for s in sockets), sockets
    return identities[0]


def parse_mountinfo(mountinfo):
    mounts = []
    for line in mountinfo.splitlines():
        before, after = line.split(' - ', 1)
        fields, fs = before.split(), after.split()
        assert len(fields) >= 6 and len(fs) == 3, line
        def unescape(value):
            return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), value)
        mounts.append({'id': fields[0], 'parent': fields[1], 'device': fields[2],
                       'root': unescape(fields[3]), 'mount': unescape(fields[4]), 'options': fields[5],
                       'propagation': fields[6:], 'filesystem': fs[0],
                       'source': unescape(fs[1]), 'super_options': fs[2]})
    return mounts


def normalize_mount_path(value):
    value = re.sub(r'(/tmp/claude-10001/-home-assistant-work/)[0-9a-f]{8}'
                   r'(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}(?=/|$)', r'\1<session>', value)
    return re.sub(r'/tmp/claude-http-[0-9a-f]+\.sock', '/tmp/claude-http-<nonce>.sock', value)


def contains_path(parent, path):
    return path == parent or path.startswith(parent.rstrip('/') + '/')


def mount_tree(mountinfo):
    mounts = parse_mountinfo(mountinfo)
    by_id = {m['id']: m for m in mounts}
    assert len(by_id) == len(mounts), 'duplicate mount ID'
    roots = [m for m in mounts if m['parent'] not in by_id or m['parent'] == m['id']]
    assert len(roots) == 1 and roots[0]['mount'] == '/', 'missing/ambiguous mount root'
    root = roots[0]
    children = {m['id']: [] for m in mounts}
    for mount in mounts:
        if mount is not root:
            assert contains_path(by_id[mount['parent']]['mount'], mount['mount']), mount
            children[mount['parent']].append(mount)

    # Canonical traversal maps IDs to tree positions, keeping covered mounts and
    # their descendants. Line order and numeric IDs do not determine visibility.
    seen = set()
    def subtree(mount):
        assert mount['id'] not in seen, 'cycle in mount tree'
        seen.add(mount['id'])
        data = {k: normalize_mount_path(v) if isinstance(v, str) else v
                for k, v in mount.items() if k not in ('id', 'parent')}
        branches = [subtree(child) for child in children[mount['id']]]
        branches.sort(key=lambda branch: branch[3])
        signature = (json.dumps(data, sort_keys=True), tuple(branch[3] for branch in branches))
        return data, branches, mount['id'], signature
    tree = subtree(root)
    assert len(seen) == len(mounts), 'disconnected mount tree'
    canonical = {}
    def number(branch, parent):
        data, branches, raw_id, _ = branch
        identity = len(canonical)
        canonical[raw_id] = dict(data, id=identity, parent=parent)
        for child in branches:
            number(child, identity)
    number(tree, None)
    return root, children, canonical


def mount_view(mountinfo):
    return list(mount_tree(mountinfo)[2].values())


def effective_mount(path, root, children):
    mount = root
    while True:
        candidates = [child for child in children[mount['id']] if contains_path(child['mount'], path)]
        if not candidates:
            return mount
        # Walk path components before following descendants. An overmount at
        # this component covers every deeper child attached to the old parent.
        length = min(len(child['mount']) for child in candidates)
        next_mounts = [child for child in candidates if len(child['mount']) == length]
        assert len(next_mounts) == 1, 'ambiguous sibling mounts at ' + path
        mount = next_mounts[0]


def policy_mounts(mountinfo, settings):
    root, children, canonical = mount_tree(mountinfo)
    result = {}
    for kind in ('denyRead', 'allowRead', 'denyWrite'):
        for value in settings['sandbox']['filesystem'][kind]:
            path = value.replace('~/', '/home/assistant/')
            mount = canonical[effective_mount(path, root, children)['id']]
            hidden = mount['filesystem'] == 'tmpfs' or mount['root'] == '/null'
            result[kind + ':' + value] = {**mount, 'view': 'hidden' if hidden else
                                        'read-only' if 'ro' in (mount['options'] + ',' +
                                                               mount['super_options']).split(',') else 'writable'}
    return result


def observed_processes(path):
    return [json.loads(line.split(' ', 1)[1])[0] for line in path.read_text().splitlines()
            if line.startswith('NATIVE_PROCESS ')]
