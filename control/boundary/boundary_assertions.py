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


def require_source_positive(report):
    required = {'/tmp/claude/source-' + scope + '-hook' for scope in ('user', 'project', 'local')}
    required |= {'/tmp/claude/source-local-status', '/tmp/claude/source-local-key'}
    assert required <= set(report['positive_markers']), report
    assert report['positive_permission'], report


def parse_mountinfo(mountinfo):
    mounts = []
    for line in mountinfo.splitlines():
        before, after = line.split(' - ', 1)
        fields, fs = before.split(), after.split()
        mounts.append({'root': fields[3], 'mount': fields[4], 'options': fields[5],
                       'filesystem': fs[0], 'source': fs[1]})
    return mounts


def mount_view(mountinfo):
    # Session UUIDs and proxy-socket nonces are the only variable path fields.
    # Keep mount destinations, backing roots, modes and filesystem sources.
    def normalize(value):
        value = re.sub(r'(/tmp/claude-10001/-home-assistant-work/)[0-9a-f-]{36}(?=/|$)',
                       r'\1<session>', value)
        return re.sub(r'/tmp/claude-http-[0-9a-f]+\.sock', '/tmp/claude-http-<nonce>.sock', value)
    view = {}
    for mount in parse_mountinfo(mountinfo):
        entry = {k: normalize(v) for k, v in mount.items()}
        view[entry['mount']] = entry
    return view


def policy_mounts(mountinfo, settings):
    # mountinfo retains covered mounts too. At the same destination the later
    # overmount is effective; choosing the first incorrectly reports it writable.
    mounts = {m['mount']: m for m in parse_mountinfo(mountinfo)}
    result = {}
    for kind in ('denyRead', 'allowRead', 'denyWrite'):
        for value in settings['sandbox']['filesystem'][kind]:
            path = value.replace('~/', '/home/assistant/')
            mount = max((m for m in mounts.values() if path == m['mount'] or
                         path.startswith(m['mount'].rstrip('/') + '/')), key=lambda m: len(m['mount']))
            hidden = mount['filesystem'] == 'tmpfs' or mount['root'] == '/null'
            result[kind + ':' + value] = {**mount, 'view': 'hidden' if hidden else
                                        'read-only' if 'ro' in mount['options'].split(',') else 'writable'}
    return result


def observed_processes(path):
    return [json.loads(line.split(' ', 1)[1])[0] for line in path.read_text().splitlines()
            if line.startswith('NATIVE_PROCESS ')]
