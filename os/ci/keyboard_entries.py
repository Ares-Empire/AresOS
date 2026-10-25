"""Identity-based entry checks for the temporary duplicate stock and final pair."""
import pathlib
import re
import shlex

FIELDS = ('checksum', 'serial', 'osname', 'booted', 'pinned')


def identities(state):
    return [{k: d[k] for k in FIELDS} for d in state['deployments']]


def entry_identity(path):
    path = pathlib.PurePosixPath(path)
    match = re.fullmatch(r'([0-9a-f]{64})\.([0-9]+)', path.name)
    assert match and path.parent.name == 'deploy', 'STOP: unresolved BLS deployment'
    return match[1], int(match[2]), path.parent.parent.name


def key(deployment):
    return tuple(deployment[k] for k in ('checksum', 'serial', 'osname'))


def without_bootlink(args):
    return [a for a in args if not a.startswith('ostree=')]


def entries(snapshot):
    result = {}
    for entry in snapshot['bls']:
        identity = entry_identity(entry['deployment'])
        assert identity not in result, 'STOP: duplicate BLS deployment'
        options = re.findall(r'^options (.+)$', entry['content'], re.M)
        assert len(options) == 1, 'STOP: missing or ambiguous BLS arguments'
        result[identity] = shlex.split(options[0])
    expected = {key(d) for d in snapshot['rpm']['deployments'] if not d.get('staged')}
    assert set(result) == expected, 'STOP: BLS/deployment identity disagreement'
    return result


def unchanged_old(before, after):
    old = [d for d in before['rpm']['deployments'] if not d['booted']]
    a, b = entries(before), entries(after)
    for d in old:
        assert without_bootlink(a[key(d)]) == without_bootlink(b[key(d)]), 'STOP: non-booted stock arguments changed'


def retained_pair(snapshot, stock, release, queued=False):
    """After switch finalization only corrected pinned stock and AresOS may exist."""
    deployments = snapshot['rpm']['deployments']
    assert snapshot['rpm']['transaction'] is None
    assert len(deployments) == 2 and not any(d.get('staged') for d in deployments), 'STOP: unexpected final deployment list; old stock must not survive'
    saved = [d for d in deployments if key(d) == key(stock)]
    assert len(saved) == 1 and saved[0]['pinned'], 'STOP: corrected stock identity/pin lost'
    other, = [d for d in deployments if key(d) != key(stock)]
    assert other['checksum'] != stock['checksum'] and not other['pinned'] and other['container-image-reference-digest'] == release.split('@')[1], 'STOP: unexpected AresOS deployment'
    booted = [d for d in deployments if d['booted']]
    assert len(booted) == 1
    status = snapshot['bootc']['status']
    assert not status.get('staged') and bool(status['rollbackQueued']) == queued
    for name in ('booted', 'rollback'):
        observed = status[name]['ostree']
        matching = [d for d in deployments if key(d) == (observed['checksum'], observed['deploySerial'], observed['stateroot'])]
        assert len(matching) == 1 and matching[0]['pinned'] == status[name]['pinned'], 'STOP: bootc/rpm-ostree disagreement'
        if name == 'booted':
            assert matching[0]['booted']
    return entries(snapshot)
