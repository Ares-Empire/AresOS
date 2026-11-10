"""Checked owner commands. Imported by tests without querying or changing a host.

The entry point is root-only. Refusal preflights are read-only; successful
operations and their postconditions are logged separately. Secrets never enter
the diagnostic recorder.
"""
import contextlib
import datetime
import getpass
import hashlib
import io
import importlib.util
import json
import os
import pathlib
import re
import shlex
import shutil
import stat
import subprocess
import sys
import time
import base64
import urllib.request
import urllib.error
import struct
import uuid
import copy
import tempfile

HOME = pathlib.Path('/var/lib/ares')
AUTH = pathlib.Path('/etc/ostree/auth.json')
STOP_RECORDS = HOME / 'diagnostics'
BASE = 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
UPSTREAM = r'(?:ostree-image-signed:docker://|ostree-unverified-registry:)?ghcr\.io/ublue-os/bazzite-nvidia-open(?::[A-Za-z0-9_.-]+|@sha256:[0-9a-f]{64})'
IDENTITY = ('checksum', 'serial', 'osname')
MODIFIED = ('requested-packages', 'requested-base-removals', 'requested-base-local-replacements',
    'requested-base-remote-replacements', 'requested-local-packages', 'requested-local-fileoverride-packages',
    'base-removals', 'base-local-replacements', 'base-remote-replacements', 'packages', 'modules',
    'requested-modules', 'regenerate-initramfs')
RELEASE_REFERENCE = r'ghcr\.io/ares-empire/aresos@sha256:[0-9a-f]{64}'
RELEASE_IDENTITY = r'https://github\.com/Ares-Empire/AresOS/\.github/workflows/[A-Za-z0-9._-]+\.yml@refs/[A-Za-z0-9._/-]+'
# The only installed tools without a release history: package 15f's bundle,
# installed on the laptop on 2026-11-08. Any other history-less bundle STOPs.
LEGACY_TOOLS = ('3ef85c4adab3c8a5daf5bf26c2a40805d24bcb0c17b9327cfc55e7e96aeebefc',)
LOGIN_REFUSAL = ('Registry login missing, expired or unreachable: run sudo /var/lib/ares/at login, '
                 'then run this command again; nothing was changed')
# What update/previous expect the next start to show (records/outcome-pending.json).
OUTCOME = 'outcome-pending'
# One owner command at a time, bootstrap install included; /run is root-only.
LOCK = pathlib.Path('/run/ares-owner.lock')


def boot_id():
    return pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def owner_lock():
    """Hold an exclusive lock for the whole command; a second command STOPs."""
    import fcntl
    descriptor = os.open(str(LOCK), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600)
    try:
        require(stat.S_ISREG(os.fstat(descriptor).st_mode), 'Owner lock is not an ordinary file; get help')
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise Stop('Another owner command is running; let it finish, then run this one again') from None
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


class Stop(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


def unique_pairs(pairs):
    # Reject duplicate JSON keys, rather than silently accepting the last one.
    result = {}
    for name, value in pairs:
        require(name not in result, 'Duplicate JSON key: ' + str(name))
        result[name] = value
    return result


def image_reference(deployment):
    return deployment['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://')


def lineage(root):
    """The bundle's tools version and its append-only AresOS release records.

    Records are oldest first; the last one is the bundle's target and must be
    release.json's exact reference and signature identity. Each record states
    its own daily-account rule; nothing is inferred from a missing value.
    """
    root = pathlib.Path(root)
    value = json.loads((root / 'history.json').read_text(), object_pairs_hook=unique_pairs)
    require(isinstance(value, dict) and list(value) == ['tools_version', 'releases'], 'Invalid tools history fields')
    version, rows = value['tools_version'], value['releases']
    require(type(version) is int and version >= 2, 'Invalid tools version')
    require(isinstance(rows, list) and rows, 'Empty release history')
    for row in rows:
        require(isinstance(row, dict) and list(row) == ['reference', 'identity', 'daily_wheel'], 'Invalid release record fields')
        require(isinstance(row['reference'], str) and re.fullmatch(RELEASE_REFERENCE, row['reference'])
            and isinstance(row['identity'], str) and re.fullmatch(RELEASE_IDENTITY, row['identity'])
            and type(row['daily_wheel']) is bool, 'Invalid release record')
    digests = [row['reference'].split('@')[1] for row in rows]
    require(len(set(digests)) == len(digests) and BASE not in digests, 'Duplicate or stock release in history')
    release = json.loads((root / 'release.json').read_text())
    require(release['reference'] == rows[-1]['reference'] and release['signature']['identity'] == rows[-1]['identity'],
        'Release target differs from the newest history record')
    return dict(tools_version=version, releases=rows)


def installed_lineage(root, fingerprint):
    """Read an installed bundle's history as data; its code is never run."""
    if (pathlib.Path(root) / 'history.json').exists():
        value = lineage(root)
        return value['tools_version'], value['releases']
    require(fingerprint in LEGACY_TOOLS, 'Installed tools have no release history and are not the known 15f tools; get help')
    release = json.loads((pathlib.Path(root) / 'release.json').read_text())
    # Version 1 knew one release and enforced its rule in check: the daily
    # account is never in wheel. A newer history must keep exactly that.
    return 1, [dict(reference=release['reference'], identity=release['signature']['identity'], daily_wheel=False)]


def extends(old, new):
    return len(new) >= len(old) and all(a['reference'] == b['reference'] and a['identity'] == b['identity']
        and a['daily_wheel'] is b['daily_wheel'] for a, b in zip(old, new))


def login_properties(host, session, names, message):
    # loginctl takes one literal selector per option, unlike systemctl.
    output = host.read('loginctl', 'show-session', session,
        *['--property=' + name for name in names])
    rows = [line.split('=', 1) for line in output.splitlines()]
    require(len(rows) == len(names) and all(len(row) == 2 for row in rows)
        and {row[0] for row in rows} == set(names), message)
    return dict(rows)


def key(deployment):
    checksum, serial, stateroot = (deployment[k] for k in IDENTITY)
    require(re.fullmatch('[0-9a-f]{64}', checksum) and type(serial) is int and serial >= 0
            and re.fullmatch('[a-zA-Z0-9_-]+', stateroot), 'Incomplete deployment identity')
    return checksum, serial, stateroot


def checked_bundle(root):
    root = pathlib.Path(root)
    require(not root.is_symlink() and root.is_dir(), 'Bundle root is missing or a link')
    raw = (root / 'SHA256.json').read_bytes()
    # Reject duplicate JSON keys, rather than silently accepting the last one.
    def unique(pairs):
        result = {}
        for name, value in pairs:
            require(name not in result, 'Duplicate manifest entry')
            result[name] = value
        return result
    rows = json.loads(raw, object_pairs_hook=unique)
    require(isinstance(rows, list), 'Manifest must be a hash-before-path list')
    entries = {}
    for row in rows:
        require(isinstance(row, dict) and list(row) == ['sha256', 'path'], 'Invalid manifest fields/order')
        name, digest = row['path'], row['sha256']
        require(isinstance(name, str) and re.fullmatch('[a-zA-Z0-9._/-]+', name)
                and not name.startswith('/') and '..' not in name.split('/')
                and isinstance(digest, str) and re.fullmatch('[0-9a-f]{64}', digest), 'Invalid manifest entry')
        require(name not in entries, 'Duplicate manifest path')
        entries[name] = digest
    require({'at', 'owner.py', 'release.json'} <= entries.keys(), 'Incomplete manifest')
    actual = set()
    for path in root.rglob('*'):
        require(not path.is_symlink(), 'Bundle contains a link')
        if path.is_file():
            actual.add(path.relative_to(root).as_posix())
    require(actual == set(entries) | {'SHA256.json', 'SHA256SUMS'}, 'Partial bundle or unexpected file')
    for name, digest in entries.items():
        require(hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, 'Bundle hash mismatch: ' + name)
    sums = ''.join(digest + '  ' + name + '\n' for name, digest in entries.items())
    sums += hashlib.sha256(raw).hexdigest() + '  SHA256.json\n'
    require((root / 'SHA256SUMS').read_bytes() == sums.encode(), 'System-tool manifest differs')
    return hashlib.sha256(sums.encode()).hexdigest()


def private_tree(root):
    for path in [root, *root.rglob('*')]:
        info = path.lstat()
        require(not path.is_symlink() and info.st_uid == 0 and not info.st_mode & 0o077,
                'Installed tools/records are not root-only: ' + path.name)
        require(path.is_dir() or path.is_file(), 'Unexpected installed file type')


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def owned_directory(path):
    info = path.lstat()
    require(not path.is_symlink() and stat.S_ISDIR(info.st_mode)
        and info.st_uid == os.geteuid() and stat.S_IMODE(info.st_mode) == 0o700,
        'Unsafe private setup directory: ' + path.name)


def program(root, name, marker):
    text = (root / 'release' / (name + '.sh')).read_text()
    body = text.split("<<'" + marker + "'\n", 1)[1].split('\n' + marker, 1)[0]
    scope = {'__name__': 'owner_shared_step'}
    exec(compile(body, name + '.sh', 'exec'), scope)
    return scope


class Host:
    def __init__(self):
        self.trace = []

    def read(self, *command, allowed=(0,), timeout=30):
        path = shutil.which(command[0], path='/usr/sbin:/usr/bin:/sbin:/bin')
        require(path and pathlib.Path(path).is_absolute(), 'Required tool missing: ' + command[0])
        result = subprocess.run([path, *command[1:]], text=True, capture_output=True, timeout=timeout)
        self.trace.append(dict(command=list(command), returncode=result.returncode,
                               stdout=result.stdout, stderr=result.stderr, mutation=False))
        require(result.returncode in allowed, 'Read failed: ' + ' '.join(command))
        if command == ('efibootmgr', '-v'):
            require(not result.stderr, 'Firmware read wrote stderr; preserve private diagnostics')
        return result.stdout

    def json(self, *command):
        return json.loads(self.read(*command))

    def mutate(self, *command, timeout=1800):
        path = shutil.which(command[0], path='/usr/sbin:/usr/bin:/sbin:/bin')
        require(path and pathlib.Path(path).is_absolute(), 'Required tool missing: ' + command[0])
        result = subprocess.run([path, *command[1:]], text=True, capture_output=True, timeout=timeout)
        self.trace.append(dict(command=list(command), returncode=result.returncode,
                               stdout=result.stdout, stderr=result.stderr, mutation=True))
        require(result.returncode == 0, 'Operation failed: ' + command[0] + '; do not reboot')

    def script(self, text, name, mutation=True):
        result = subprocess.run(['/usr/bin/bash', '-seu'], input=text, text=True, capture_output=True, timeout=1800,
            env=dict(os.environ, PATH='/usr/sbin:/usr/bin:/sbin:/bin'))
        self.trace.append(dict(script=name, returncode=result.returncode, stdout=result.stdout,
                               stderr=result.stderr, mutation=mutation))
        require(result.returncode == 0, 'Shared step failed: ' + name + '; preserve diagnostics and do not reboot')
        return result.stdout


def observations(host):
    return dict(rpm=host.json('rpm-ostree', 'status', '--json'), bootc=host.json('bootc', 'status', '--json'))


def agree(state):
    rows = state['rpm']['deployments']
    require(rows and len({key(d) for d in rows}) == len(rows), 'Duplicate deployment identity')
    require(all(type(d['booted']) is bool and type(d['pinned']) is bool for d in rows), 'Invalid deployment flags')
    booted = [d for d in rows if d['booted']]
    require(len(booted) == 1, 'Expected exactly one booted deployment')
    status = state['bootc']['status']
    require(status.get('booted') is not None, 'bootc booted identity missing')
    for name in ('booted', 'staged', 'rollback'):
        slot = status.get(name)
        if slot is None:
            continue
        triple = (slot['ostree']['checksum'], slot['ostree']['deploySerial'], slot['ostree']['stateroot'])
        matches = [d for d in rows if key(d) == triple]
        require(len(matches) == 1, 'bootc/rpm-ostree ' + name + ' identity disagreement')
        d, = matches
        require(slot['pinned'] == d['pinned'] and slot['image']['imageDigest'] == d['container-image-reference-digest'],
                'bootc/rpm-ostree pin or digest disagreement')
        reference = d['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://')
        require(slot['image']['image']['image'] == reference, 'bootc/rpm-ostree reference disagreement')
        require((name == 'booted') == d['booted'], 'bootc booted flag disagreement')
        if name == 'staged':
            require(d.get('staged') is True, 'bootc staged flag disagreement')
    return booted[0]


def deployment_client(process):
    return not (process['excluded_as_daemon'] is True
                or process.get('excluded_as_system_helper', False) is True)


def idle(state, processes):
    require('transaction' in state['rpm'] and state['rpm']['transaction'] is None, 'Deployment transaction active or unknown')
    require(not any(deployment_client(p) for p in processes), 'rpm-ostree/bootc/ostree client active')


def preflight_prepare(state, processes, saved=None, updater_names=()):
    stock = agree(state)
    owned = [p for p in processes if deployment_client(p)]
    def updater_owned(p):
        return any('/system.slice/' + name + '/' in p.get('cgroup', '') + '/'
                   or ('/system.slice/' + name + '\n') in p.get('cgroup', '') for name in updater_names)
    if owned and all(updater_owned(p) for p in owned) and saved is None:
        require('transaction' in state['rpm'], 'Cannot inspect updater transaction')
    else:
        idle(state, processes)
    status = state['bootc']['status']
    require(not status.get('rollbackQueued'), 'Rollback queued')
    require(stock['container-image-reference-digest'] == BASE and re.fullmatch(UPSTREAM, stock['container-image-reference']), 'Wrong booted stock image')
    if saved is not None:
        require(key(stock) == tuple(saved['stock_identity']) and stock['pinned'], 'Prepared stock identity or pin changed')
        require(state == saved['state'], 'Prepared deployment list/pin/pending state changed')
        return stock
    staged = [d for d in state['rpm']['deployments'] if d.get('staged')]
    require(len(staged) <= 1 and bool(staged) == bool(status.get('staged')), 'Staged observations disagree')
    if staged:
        d, = staged
        require(not d['booted'] and not d['pinned'] and re.fullmatch(UPSTREAM, d.get('container-image-reference', ''))
                and re.fullmatch('sha256:[0-9a-f]{64}', d.get('container-image-reference-digest', '')), 'Foreign or unsafe staged update')
    retained = [d for d in state['rpm']['deployments'] if not d.get('staged')]
    require(1 <= len(retained) <= 2 and retained[0] is stock, 'Expected booted default and one or two stock serials')
    for d in retained:
        require(not d['pinned'] and d['checksum'] == stock['checksum'] and d['osname'] == stock['osname']
                and d['container-image-reference'] == stock['container-image-reference']
                and d['container-image-reference-digest'] == BASE, 'Unexpected stock serial/origin/pin')
        require(not any(d.get(k) for k in MODIFIED) and d.get('unlocked', 'none') == 'none', 'Modified stock deployment')
    return stock


def known_releases(release, history):
    """Known AresOS references, oldest first; the target is always the last."""
    known = list(history) if history is not None else [release]
    require(known and known[-1] == release and len(set(known)) == len(known)
        and all(isinstance(r, str) and '@sha256:' in r for r in known), 'Release history/target mismatch')
    return {r.split('@')[1]: (i, r) for i, r in enumerate(known)}


def preflight_recovery(state, processes, saved, release, keep=False, history=None):
    known = known_releases(release, history)
    booted = agree(state)
    idle(state, processes)
    require(keep or booted['container-image-reference-digest'] != BASE, 'Use keep-stock on booted stock; rollback would select the other deployment')
    status = state['bootc']['status']
    rows = state['rpm']['deployments']
    require(not status.get('rollbackQueued') and not status.get('staged') and not any(d.get('staged') for d in rows), 'Pending deployment or rollback')
    require(len(rows) == 2, 'Expected exact stock/AresOS pair')
    matches = [d for d in rows if key(d) == tuple(saved['stock_identity'])]
    require(len(matches) == 1, 'Saved stock checksum/serial/stateroot missing')
    stock, = matches
    old = saved['stock']
    require(stock['pinned'] and all(stock[k] == old[k] for k in ('container-image-reference', 'container-image-reference-digest')),
            'Saved stock pin/reference/digest changed')
    ares, = [d for d in rows if d is not stock]
    digest = ares['container-image-reference-digest']
    require(not ares['pinned'] and digest in known and image_reference(ares) == known[digest][1],
            'Wrong AresOS target')
    require(booted is (stock if keep else ares),
            'Use keep-stock on booted stock' if not keep else 'keep-stock requires booted saved stock')
    return stock


def slot_identity(slot):
    return (slot['ostree']['checksum'], slot['ostree']['deploySerial'], slot['ostree']['stateroot'])


def qualified_state(state, saved, release, history=None):
    """Accept only the reviewed deployment lists; refuse every other shape.

    history lists the known AresOS release references, oldest first, ending
    with the target release. Without it only the target is known (the shapes
    before package 22). The shapes are: the prepared stock list, the first
    switch staged, the AresOS/stock pair (optionally a queued stock rollback),
    an update staged over a running AresOS, and afterwards two AresOS releases
    plus the pinned stock (optionally a queued return to the previous one).
    """
    known = known_releases(release, history)
    target = release.split('@')[1]
    booted = agree(state)
    rows = state['rpm']['deployments']
    status = state['bootc']['status']
    stock = [d for d in rows if key(d) == tuple(saved['stock_identity'])]
    require(len(stock) == 1 and stock[0]['pinned'] and all(stock[0][k] == saved['stock'][k]
        for k in ('container-image-reference', 'container-image-reference-digest')), 'Saved stock changed')
    stock = stock[0]
    ares = [d for d in rows if d['container-image-reference-digest'] in known]
    if not ares:
        require(state == saved['state'], 'Unexpected prepared deployment list/pending state')
        return
    for d in ares:
        require(not d['pinned'] and d['checksum'] != stock['checksum']
            and image_reference(d) == known[d['container-image-reference-digest']][1],
            'Unexpected AresOS identity or origin')
    require(len({d['container-image-reference-digest'] for d in ares}) == len(ares), 'Duplicate AresOS release deployment')
    is_ares = lambda row: any(row is d for d in ares)
    staged = [d for d in rows if d.get('staged')]
    if staged and booted is stock:
        require(staged == ares and ares[0]['container-image-reference-digest'] == target and status.get('staged')
            and not status.get('rollbackQueued'), 'Unexpected staged switch')
        retained = [d for d in rows if not d.get('staged')]
        require(retained == saved['state']['rpm']['deployments'], 'Switch changed the retained stock list')
        return
    if staged:
        # An update: the newest release staged over a running, older release,
        # with the pinned stock last and at most one older AresOS between.
        retained = [d for d in rows if not d.get('staged')]
        require(len(staged) == 1 and staged[0]['container-image-reference-digest'] == target and is_ares(staged[0])
            and status.get('staged') and slot_identity(status['staged']) == key(staged[0])
            and not status.get('rollbackQueued') and is_ares(booted)
            and known[booted['container-image-reference-digest']][0] < known[target][0], 'Unexpected staged update')
        require(rows[0] is staged[0] and len(retained) in (2, 3) and retained[0] is booted and retained[-1] is stock
            and all(is_ares(d) for d in retained[1:-1]), 'Unexpected deployments beside a staged update')
        return
    require(status.get('staged') is None, 'Final deployments have a pending stage')
    if len(rows) == 2:
        if status.get('rollbackQueued'):
            require(booted is ares[0] and status['rollback']['ostree']['checksum'] == stock['checksum']
                and status['rollback']['ostree']['deploySerial'] == stock['serial'], 'Wrong queued rollback')
        return
    require(len(rows) == 3 and len(ares) == 2 and rows[-1] is stock, 'Final pair has extra/missing deployments')
    require(is_ares(booted), 'Stock is booted beside two AresOS releases; get help')
    other, = [d for d in ares if d is not booted]
    require(status.get('rollback') and slot_identity(status['rollback']) == key(other), 'Wrong AresOS rollback deployment')
    if status.get('rollbackQueued'):
        require(rows[0] is other and rows[1] is booted, 'Wrong queued return to the previous AresOS')
    else:
        require(rows[0] is booted and rows[1] is other, 'The running AresOS is not the default')


def setup_identity(record):
    return {name: record[name] for name in ('target', 'protected', 'partitions', 'esp_guid')}


def prepare_resume(intent, state, bls, args, fingerprint, disks):
    """Only the exact effects of the journalled step may differ on resumption."""
    require(intent['schema'] == 'prepare1' and intent['manifest'] == fingerprint
        and intent['disks'] == disks and intent['phase'] in ('pause', 'cleanup', 'keyboard', 'pin', 'records', 'complete'),
        'Interrupted prepare intent differs; preserve diagnostics and get help')
    phase = intent['phase']
    initial = intent['initial']
    stock = agree(state)
    require(list(key(stock)) == intent['stock_identity'], 'Interrupted prepare stock identity differs')
    idle(state, []) if phase != 'pause' else None
    candidate = copy.deepcopy(state)
    original = copy.deepcopy(initial)
    if phase != 'pause':
        require(candidate['rpm']['transaction'] is None, 'Interrupted prepare has a transaction')
    else:
        require(candidate['rpm']['transaction'] in (None, original['rpm']['transaction']), 'Interrupted pause transaction differs')
    candidate['rpm']['transaction'] = original['rpm']['transaction'] = None
    if phase in ('pin', 'records', 'complete'):
        require(stock['pinned'] or phase == 'pin', 'Interrupted pin lost the stock pin')
        for row in candidate['rpm']['deployments']:
            if key(row) == key(stock): row['pinned'] = False
        for slot in candidate['bootc']['status'].values():
            if isinstance(slot, dict) and slot.get('ostree') == state['bootc']['status']['booted']['ostree']:
                slot['pinned'] = False
    cleaned = copy.deepcopy(original)
    cleaned['rpm']['deployments'] = [d for d in cleaned['rpm']['deployments'] if not d.get('staged')]
    cleaned['bootc']['status']['staged'] = None
    allowed = [original] if phase == 'pause' else [original, cleaned] if phase == 'cleanup' else [cleaned]
    require(candidate in allowed, 'Interrupted prepare deployment list/pin/pending state differs')
    unchanged_old(initial, intent['before_bls'], bls)
    before_entry, = [e for e in intent['before_bls'] if e['identity'] == intent['stock_identity']]
    current_entry, = [e for e in bls if e['identity'] == intent['stock_identity']]
    require([a for a in args if a.startswith('ostree=')] == [a for a in bls_arguments(current_entry) if a.startswith('ostree=')],
        'Interrupted prepare default bootlink differs from the resolved stock entry')
    repair_key = lambda a: re.match(r'(?:rd\.)?vconsole\.keymap(?:[._]toggle)?(?:=|$)', a)
    strip = lambda words: [a for a in words if not a.startswith('ostree=')]
    original_args = strip(intent['original_kargs'])
    corrected = [a for a in original_args if not repair_key(a)]
    allowed_args = [original_args] if phase in ('pause', 'cleanup') else [original_args, corrected] if phase == 'keyboard' else [corrected]
    require(strip(args) in allowed_args and strip(bls_arguments(current_entry)) in allowed_args
        and current_entry['title'] == before_entry['title'], 'Interrupted prepare boot arguments/title differ')


def resolved_bls():
    result = []
    for path in sorted(pathlib.Path('/boot/loader/entries').glob('*.conf')):
        text = path.read_text()
        titles = re.findall(r'^title (.+)$', text, re.M)
        options = re.findall(r'^options (.+)$', text, re.M)
        require(len(titles) == len(options) == 1, 'Missing or ambiguous BLS title/options')
        targets = [a[7:] for a in shlex.split(options[0]) if a.startswith('ostree=')]
        require(len(targets) == 1 and targets[0].startswith('/ostree/'), 'Unresolved BLS target')
        target = (pathlib.Path('/sysroot') / targets[0].lstrip('/')).resolve(strict=True)
        match = re.fullmatch(r'([0-9a-f]{64})\.([0-9]+)', target.name)
        require(match and target.parent.name == 'deploy', 'Invalid BLS deployment path')
        result.append(dict(file=str(path), content=text, title=titles[0], target=str(target),
                           identity=[match[1], int(match[2]), target.parent.parent.name]))
    require(result, 'No BLS entries')
    return result


def validate_bls(state, bls):
    expected = {key(d) for d in state['rpm']['deployments'] if not d.get('staged')}
    observed = [tuple(entry['identity']) for entry in bls]
    require(len(observed) == len(set(observed)) and set(observed) == expected, 'Whole BLS/deployment identity list differs')


def bls_arguments(entry):
    rows = re.findall(r'^options (.+)$', entry['content'], re.M)
    require(len(rows) == 1, 'Missing or duplicate BLS options')
    return shlex.split(rows[0])


def unchanged_old(state, before, after):
    for d in state['rpm']['deployments']:
        if d['booted'] or d.get('staged'):
            continue
        entries = []
        for bls in (before, after):
            matched = [e for e in bls if tuple(e['identity']) == key(d)]
            require(len(matched) == 1, 'Untouched old stock BLS identity missing')
            entries.append([a for a in bls_arguments(matched[0]) if not a.startswith('ostree=')])
        require(entries[0] == entries[1], 'Non-booted stock arguments changed')


def keyboard_entries(state, saved, bls):
    validate_bls(state, bls)
    old = {key(d) for d in saved['state']['rpm']['deployments'] if not d['booted']}
    result = []
    for e in bls:
        if tuple(e['identity']) in old:
            require(state == saved['state'], 'Old stock survived beyond the prepared stock state')
            unchanged_old(state, saved['before_bls'], bls)
        else:
            result.append(e)
    return result


def paused_state(host, pause):
    result = {}
    for scope, prefix, names in (('system', [], pause['SYSTEM']), ('global-user', ['--global'], pause['USER'])):
        listing = host.read('systemctl', *prefix, '--no-pager', '--no-legend', 'list-unit-files')
        files = {p[0]: p[1] for line in listing.splitlines() if len(p := line.split()) >= 2}
        present = [name for name in names if name in files]
        if scope == 'system':
            require({'uupd.service', 'uupd.timer'} <= set(present), 'Stock updater units missing')
        for name in present:
            if name.endswith('.timer'):
                require(files[name] in ('disabled', 'masked'), 'OS updater timer is not persistently disabled: ' + name)
            if scope == 'system':
                fields = dict(line.split('=', 1) for line in host.read('systemctl', '--no-pager', 'show', name,
                    '--property=LoadState,ActiveState,SubState').splitlines() if '=' in line)
                require(fields.get('LoadState') in ('loaded', 'masked') and fields.get('ActiveState') in ('inactive', 'failed'),
                        'OS updater is active or cannot be inspected: ' + name)
        result[scope] = {name: files[name] for name in present}
    for bus in pathlib.Path('/run/user').glob('*/bus'):
        uid = bus.parent.name
        require(uid.isdigit(), 'Unknown user manager')
        user = host.read('getent', 'passwd', uid).split(':', 1)[0]
        for name in pause['USER']:
            fields = dict(line.split('=', 1) for line in host.read('runuser', '-u', user, '--', 'env',
                'XDG_RUNTIME_DIR=/run/user/' + uid, 'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/' + uid + '/bus',
                'systemctl', '--user', 'show', name, '--property=LoadState,ActiveState').splitlines() if '=' in line)
            require(fields.get('LoadState') in ('not-found', 'loaded', 'masked') and fields.get('ActiveState') in ('inactive', 'failed'),
                    'User updater manager is active or uninspectable')
    return result


def runtime_state(host):
    # check is observational: its status is 0 when missing, 1 when installed.
    # Conditions are false with virtual graphics. Never start/stop/wait for it.
    result = {}
    for name, command in (
        ('unit', ('systemctl', 'show', 'ublue-nvidia-flatpak-runtime-sync.service',
            '--property=LoadState,ActiveState,SubState,Result,ConditionResult,ExecMainStatus')),
        ('check', ('/usr/libexec/ublue-nvidia-flatpak-runtime-sync', 'check')),
        ('runtime_ids', ('flatpak', 'list', '--system', '--runtime', '--columns=application'))):
        try:
            result[name] = dict(output=host.read(*command, allowed=(0, 1)), returncode=host.trace[-1]['returncode'])
        except (Stop, OSError, subprocess.SubprocessError) as error:
            result[name] = dict(observed=False, error=str(error))
    result['nvidia_module_present'] = pathlib.Path('/sys/module/nvidia/version').exists()
    return result


def account(host):
    require(host.read('id', '-u', 'ares-recovery').strip() == '1000', 'ares-recovery must be UID 1000')
    require('wheel' in host.read('id', '-nG', 'ares-recovery').split(), 'Recovery administrator is not in wheel')
    require(not host.read('getent', 'passwd', 'ares', allowed=(0, 2)).strip()
            and not host.read('getent', 'passwd', '1001', allowed=(0, 2)).strip(), 'Daily account/UID 1001 already exists')


def authentication():
    require(not AUTH.is_symlink() and not AUTH.parent.is_symlink() and AUTH.is_file(),
            'Private login is missing or a link; run login first')
    require(AUTH.stat().st_uid == 0 and stat.S_IMODE(AUTH.stat().st_mode) == 0o600
            and AUTH.parent.stat().st_uid == 0 and not AUTH.parent.stat().st_mode & 0o022,
            'Private credential ownership/mode incorrect; get help')


def validate_login(username, secret, reference):
    image, digest = reference.removeprefix('ghcr.io/').split('@')
    basic = base64.b64encode((username + ':' + secret).encode()).decode()
    try:
        request = urllib.request.Request('https://ghcr.io/token?service=ghcr.io&scope=repository:' + image + ':pull',
            headers={'Authorization': 'Basic ' + basic})
        with urllib.request.urlopen(request, timeout=45) as response:
            value = json.load(response)
        bearer = value.get('token') or value.get('access_token')
        require(isinstance(bearer, str) and bearer, 'Registry did not grant read access')
        request = urllib.request.Request('https://ghcr.io/v2/' + image + '/manifests/' + digest,
            headers={'Authorization': 'Bearer ' + bearer,
                     'Accept': 'application/vnd.oci.image.manifest.v1+json,application/vnd.docker.distribution.manifest.v2+json'})
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read(8 * 1024 * 1024 + 1)
        require(len(raw) <= 8 * 1024 * 1024 and 'sha256:' + hashlib.sha256(raw).hexdigest() == digest,
                'Registry returned a different release manifest')
    except (urllib.error.URLError, OSError, ValueError, KeyError) as error:
        # Never include a request/header/token or underlying authentication error.
        raise Stop('Private release read failed; check read:packages permission/expiry and network; no credential was written') from None


def stored_login(reference):
    """The saved registry login must read the target manifest; it is never recorded.

    A missing, expired or unusable login is a refusal that points to login.
    Wrong ownership or mode is not a login problem and keeps its own message.
    """
    if not AUTH.exists() and not AUTH.is_symlink():
        raise Stop(LOGIN_REFUSAL)
    authentication()
    username = secret = None
    try:
        try:
            value = json.loads(AUTH.read_text())
            encoded = value['auths']['ghcr.io']['auth']
            username, secret = base64.b64decode(encoded, validate=True).decode().split(':', 1)
            require(re.fullmatch('[a-zA-Z0-9-]+', username) and secret, LOGIN_REFUSAL)
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            raise Stop(LOGIN_REFUSAL) from None
        try:
            validate_login(username, secret, reference)
        except (Stop, AttributeError, TypeError):
            raise Stop(LOGIN_REFUSAL) from None
    finally:
        del username, secret


def media_module(payload=None):
    path = (pathlib.Path(payload) if payload is not None else pathlib.Path(__file__).resolve().parent) / 'media.py'
    spec = importlib.util.spec_from_file_location('ares_owner_media', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def mount_record(host, selector, path):
    value = host.json('findmnt', '--json', '--list', selector, str(path), '--output', 'SOURCE,TARGET,FSTYPE')
    message = 'Unexpected findmnt list shape or mount identity: ' + str(path)
    require(isinstance(value, dict) and isinstance(value.get('filesystems'), list), message)
    rows = value['filesystems']
    require(len(rows) == 1 and isinstance(rows[0], dict), message)
    row, = rows
    require('children' not in row and all(isinstance(row.get(k), str) and row[k] for k in ('source', 'target', 'fstype')),
            message)
    require(selector != '--mountpoint' or row['target'] == str(path), message)
    return row


def device_path(raw, esp_guid):
    """Classify binary UEFI nodes; formatted names/OptionalData are not input.

    UEFI 2.10, 10.3.1 and 10.3.5: little-endian node lengths, HD's GUID
    uses EFI mixed endian, and FilePath is NUL-terminated UTF-16LE. Unknown
    hardware/vendor nodes are skipped by length, never by their rendered name.
    """
    message = 'Malformed EFI device path; preserve private diagnostics'
    nodes, disks, offset = [], [], 0
    while offset < len(raw):
        require(len(raw) - offset >= 4, message)
        kind, subtype, length = struct.unpack_from('<BBH', raw, offset)
        require(4 <= length <= len(raw) - offset, message)
        node = raw[offset:offset + length]
        nodes.append((kind, subtype, node))
        offset += length
        if (kind, subtype) == (4, 1):
            # Without the complete HD signature this entry cannot be excluded.
            require(length == 42, message)
            part, start, size = struct.unpack_from('<IQQ', node, 4)
            disks.append(dict(partition=part, start=start, size=size,
                guid=str(uuid.UUID(bytes_le=node[24:40])), format=node[40], signature_type=node[41]))
        if kind == 0x7f:
            require(subtype in (1, 0xff) and length == 4, message)
            if subtype == 0xff:
                require(offset == len(raw), message)
    require(nodes and nodes[-1][:2] == (0x7f, 0xff), message)
    targets = [d for d in disks if d['format'] == d['signature_type'] == 2 and d['guid'] == esp_guid.lower()]
    if not targets:
        # File encoding and optional data on another disk/firmware/network
        # option cannot authorize, or prevent, the target's classification.
        return None
    require(len(disks) == len(targets) == 1 and targets[0]['partition'] > 0 and targets[0]['size'] > 0, message)
    require(not any(k == 0x7f and s == 1 for k, s, _ in nodes), message)
    files = [node for k, s, node in nodes if (k, s) == (4, 4)]
    require(len(files) == 1, message)
    node, = files
    require(len(node) >= 6 and len(node) % 2 == 0 and node[-2:] == b'\0\0', message)
    try:
        path = node[4:-2].decode('utf-16-le')
    except UnicodeDecodeError:
        raise Stop(message) from None
    require('\0' not in path, message)
    if not path.lower().startswith('\\efi\\'):
        return None
    require(len(path) > 5 and not any(c in path for c in '\r\n\t/')
        and all(p not in ('', '.', '..') for p in path.split('\\')[1:]), message)
    hd_index = next(i for i, (k, s, _) in enumerate(nodes) if (k, s) == (4, 1))
    file_index = next(i for i, (k, s, _) in enumerate(nodes) if (k, s) == (4, 4))
    require(hd_index < file_index < len(nodes) - 1, message)
    return dict(path=path, esp_guid=targets[0]['guid'])


INSTALLER_LOADER = '\\efi\\fedora\\shimx64.efi'
FIRMWARE_ALIAS_LOADER = '\\efi\\fedora\\shim.efi'


def firmware_entry(text, esp_guid):
    """Read efibootmgr18 verbose bytes. Text is display/diagnostics only."""
    message = 'Unexpected efibootmgr entry framing; preserve private diagnostics'
    require(isinstance(esp_guid, str) and re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', esp_guid),
            'Missing target EFI GUID')
    entries, headers, mode = [], set(), None
    for line in text.splitlines():
        match = re.fullmatch(r'Boot([0-9a-fA-F]{4})([* ]) ([^\r\n]*)', line)
        if match:
            number, active, display = match.groups()
            require(number.upper() not in {e['number'] for e in entries}, 'Duplicate Boot number; ' + message)
            entries.append(dict(number=number.upper(), label=display.split('\t', 1)[0], dp=[]))
            mode = None
            continue
        match = re.fullmatch(r'\s+(dp|data):\s*(.*)', line)
        if match:
            require(entries, message)
            mode, value = match.groups()
            if mode == 'dp':
                entries[-1]['dp'].append(value)
            continue
        if line[:1].isspace() and mode in ('dp', 'data'):
            if mode == 'dp': entries[-1]['dp'].append(line.strip())
            continue
        match = re.fullmatch(r'(BootCurrent|BootNext): [0-9A-Fa-f]{4}|(BootOrder): [0-9A-Fa-f]{4}(?:,[0-9A-Fa-f]{4})*|(Timeout): [0-9]+ seconds', line)
        require(match is not None, message)
        name = line.split(':', 1)[0]
        require(name not in headers, message)
        headers.add(name)
        mode = None
    require(any(e['dp'] for e in entries), 'No verbose dp bytes; preserve private diagnostics; no text fallback')
    matches = []
    for entry in entries:
        require(entry['dp'], 'Missing verbose dp bytes for Boot' + entry['number'] + '; preserve private diagnostics')
        hex_text = ' '.join(entry['dp']).replace('/', ' ')
        require(re.fullmatch(r'\s*[0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*\s*', hex_text), message)
        decoded = device_path(bytes.fromhex(hex_text), esp_guid)
        if decoded is not None:
            matches.append(dict(number=entry['number'], label=entry['label'], **decoded))
    # Lenovo's firmware (LOQ 15IRH8) adds its own entry for the target ESP's
    # \EFI\fedora\shim.efi at every start and recreates it when deleted (owner
    # install, 2026-11-08). It starts Fedora's shim on the same target ESP, so
    # at most one such alias is set aside by its device path alone; labels and
    # optional data still decide nothing. Exactly one other entry must remain,
    # and beside an alias it must be the installer's own shimx64 entry.
    aliases = [m for m in matches if m['path'].lower() == FIRMWARE_ALIAS_LOADER]
    entries = [m for m in matches if m not in aliases]
    require(len(entries) == 1 and len(aliases) <= 1
            and (not aliases or entries[0]['path'].lower() == INSTALLER_LOADER),
            'Linux firmware entry does not uniquely map to target EFI')
    return entries[0]


def disk_record(host, expected):
    tree = media_module().block_tree(host, require, '--bytes', '--output',
        'PATH,TYPE,MODEL,SERIAL,SIZE,PTUUID,PARTUUID,PARTTYPE,START,LOG-SEC,MOUNTPOINTS')
    disks = tree['blockdevices']
    selected = []
    for role in ('target', 'protected'):
        matches = [d for d in disks if d['type'] == 'disk' and str(d.get('serial', '')).strip() == expected[role]]
        require(len(matches) == 1, 'Wrong or ambiguous ' + role + ' disk serial')
        selected.append(matches[0])
    require(selected[0] is not selected[1], 'Target equals protected disk')
    def flatten(d):
        return [d] + [node for child in d.get('children', []) for node in flatten(child)]
    require(not any(any(p for p in d.get('mountpoints', []) if p) for d in flatten(selected[1])), 'Protected disk is mounted')
    target_nodes = flatten(selected[0])
    esp = mount_record(host, '--mountpoint', '/boot/efi')
    require(esp['source'] in [d['path'] for d in target_nodes], 'Linux EFI is not on target')
    guid = next(d['partuuid'] for d in target_nodes if d['path'] == esp['source'])
    require(guid and re.fullmatch('[0-9a-fA-F-]{36}', guid), 'Missing target EFI GUID')
    for mount in ('/boot', '/sysroot'):
        value = mount_record(host, '--mountpoint', mount)
        require(value['source'].split('[', 1)[0] in [d['path'] for d in target_nodes], 'Linux mount is not on target: ' + mount)
    firmware = host.read('efibootmgr', '-v')
    firmware_entry(firmware, guid)
    return dict(disks=tree, target=selected[0], protected=selected[1], esp_guid=guid, firmware=firmware,
        partitions={d['path']: host.json('sfdisk', '--json', d['path']) for d in selected})


PHYSICAL_LOGIN = 'Use a physical tty3/tty4 recovery login'


def logind_scope(text):
    sessions = []
    for line in text.splitlines():
        fields = line.split(':', 2)
        require(len(fields) == 3 and fields[0].isdigit() and fields[2].startswith('/'), PHYSICAL_LOGIN)
        sessions.extend(re.findall(r'(?:^|/)session-([A-Za-z0-9_-]+)\.scope(?=/|$)', fields[2]))
    require(len(sessions) == 1, PHYSICAL_LOGIN)
    return sessions[0]


def process_terminal(pid):
    path = pathlib.Path('/proc') / str(pid) / 'stat'
    raw = path.read_text()
    fields = raw.rsplit(')', 1)[1].split()
    require(len(fields) >= 20 and int(raw.split(' ', 1)[0]) == pid, PHYSICAL_LOGIN)
    return dict(pid=pid, comm=raw.split('(', 1)[1].rsplit(')', 1)[0],
        ppid=int(fields[1]), session=int(fields[3]), tty=int(fields[4]) & 0xffffffff,
        start=fields[19], exe=os.readlink(str(path.with_name('exe'))))


def terminal_number(path):
    device = os.stat(path).st_rdev
    minor = os.minor(device)
    return (minor & 255) | (os.major(device) << 8) | ((minor & ~255) << 12)


def physical_stdin(tty, name):
    physical = terminal_number('/dev/' + tty)
    if name == '/dev/' + tty:
        require(process_terminal(os.getpid())['tty'] == physical, PHYSICAL_LOGIN)
        return
    require(re.fullmatch(r'/dev/pts/[0-9]+', name), PHYSICAL_LOGIN)
    pts = terminal_number(name)
    pid, chain, seen = os.getpid(), [], set()
    def sudo(row):
        return row['comm'] == 'sudo' and row['exe'] == '/usr/bin/sudo'
    for _ in range(128):
        require(pid > 1 and pid not in seen, PHYSICAL_LOGIN)
        seen.add(pid)
        row = process_terminal(pid)
        chain.append(row)
        if row['tty'] == physical:
            require(sudo(row) and chain[0]['tty'] == pts, PHYSICAL_LOGIN)
            # Validate outside-in: only a sudo frontend may introduce a new
            # pts, first seen at its direct monitor child/session leader.
            ordered = list(reversed(chain))
            terminals, hops = {physical}, 0
            for parent, child in zip(ordered, ordered[1:]):
                if child['tty'] == parent['tty']:
                    require(child['session'] == parent['session'], PHYSICAL_LOGIN)
                else:
                    require(sudo(parent) and sudo(child) and child['session'] == child['pid']
                        and 136 <= (child['tty'] >> 8) & 0xfff <= 143
                        and child['tty'] not in terminals, PHYSICAL_LOGIN)
                    terminals.add(child['tty'])
                    hops += 1
                    require(hops <= 3, PHYSICAL_LOGIN)
            require(hops >= 1, PHYSICAL_LOGIN)
            require(all(process_terminal(r['pid']) == r for r in chain), PHYSICAL_LOGIN)
            return
        python = (re.fullmatch(r'/usr/bin/python3(?:\.[0-9]+)?', row['exe'])
            and row['comm'] in ('python3', os.path.basename(row['exe'])))
        require(136 <= (row['tty'] >> 8) & 0xfff <= 143
            and (python or row['exe'] in ('/usr/bin/bash', '/usr/bin/sudo')
            and row['comm'] == os.path.basename(row['exe'])), PHYSICAL_LOGIN)
        pid = row['ppid']
    raise Stop(PHYSICAL_LOGIN)


class Tools:
    def __init__(self, payload, host, store):
        self.payload, self.host, self.store = pathlib.Path(payload), host, pathlib.Path(store)
        self.release = json.loads((self.payload / 'release.json').read_text())
        self.pause = program(self.payload, 'pause-stock-updates', 'PAUSE_STOCK')

    def processes(self):
        processes = self.pause['deployment_processes']()
        self.host.trace.append(dict(observation='deployment-processes', processes=processes, mutation=False))
        return processes

    def lineage(self):
        # Read lazily: diagnostic recorders are built without __init__.
        value = getattr(self, '_lineage', None)
        if value is None:
            value = lineage(self.payload)
            require(value['releases'][-1]['reference'] == self.release['reference'], 'Release target differs from history')
            self._lineage = value
        return value

    def known(self):
        return [row['reference'] for row in self.lineage()['releases']]

    def qualified(self, state, saved=None, retry=None):
        """The reviewed shapes, and any update/previous result the last start owes."""
        qualified_state(state, saved if saved is not None else self.load('prepared'), self.release['reference'], self.known())
        return self.outcome(state, retry)

    def outcome(self, state, retry=None):
        """Compare the system with the journalled update/previous.

        update and previous journal an intent before they change anything and
        turn it into a record once the change is verified. An intent is never
        a confirmation: only the same command may continue it, by redoing the
        change from the unchanged list ('retry') or by recording a change it
        already made ('complete'); everything else STOPs.

        With a record, before the restart (same boot) the exact staged or
        queued list must still be there: 'pending'. After it, only the
        recorded booted release in the recorded order with nothing pending is
        'done'. An unchanged pre-change list may be retried by the same
        command ('retry'). Any other result STOPs, so check/title/records
        never confirm a failure.
        """
        if not (self.store / (OUTCOME + '.json')).exists():
            return None
        value = self.load(OUTCOME)
        require(value.get('status') in ('intent', 'recorded') and value.get('kind') in ('update', 'previous'),
            'Invalid update/previous record; get help')
        rows, status = state['rpm']['deployments'], state['bootc']['status']
        keys, booted = [list(key(d)) for d in rows], list(key(agree(state)))
        waiting = bool(status.get('staged')) or any(d.get('staged') for d in rows) or bool(status.get('rollbackQueued'))
        change = ('update to ' if value['kind'] == 'update' else 'return to ') + value['reference']
        if value['status'] == 'intent':
            if retry == value['kind']:
                if keys == value['before'] and booted == value['before'][0] and not waiting:
                    return 'retry'
                if self.completion(value, state) is not None:
                    return 'complete'
            raise Stop('The ' + change + ' was interrupted before its result was recorded; do not reboot; '
                'export records and get help: EMERGENCY Failed or bad update')
        if value['boot'] == boot_id():
            require(keys == value['pending'] and waiting, 'The ' + change + ' changed before the restart; do not reboot; get help')
            return 'pending'
        if keys == value['expected'] and booted == value['booted'] and not waiting:
            return 'done'
        if retry == value['kind'] and keys == value['before'] and booted == value['before'][0] and not waiting:
            return 'retry'
        raise Stop('The ' + change + ' did not finish at the restart (' + ('it is still pending' if waiting else
            'another deployment runs') + '); do not repeat it; export records and get help: EMERGENCY Failed or bad update')

    def intend(self, kind, before, reference, target, settled):
        """Journal the change durably before it is made; a superseded record is kept."""
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        if settled in ('done', 'retry'):
            self.save(stamp + '-outcome-' + ('confirmed' if settled == 'done' else 'retried'), self.load(OUTCOME))
        self.save(OUTCOME, dict(kind=kind, status='intent', boot=boot_id(), reference=reference,
            digest=reference.split('@')[1], target=target, before=[list(key(d)) for d in before['rpm']['deployments']]))

    def completion(self, intent, state):
        """The full record if state is exactly the intended change, else None.

        update: the target release staged over the unchanged list (same boot),
        or booted after the restart with the running one as rollback and the
        stock last. previous: the queued order (same boot), or the previous
        release booted in that order after the restart.
        """
        rows, status = state['rpm']['deployments'], state['bootc']['status']
        keys, booted = [list(key(d)) for d in rows], agree(state)
        before, same = intent['before'], intent['boot'] == boot_id()
        staged = [d for d in rows if d.get('staged')]
        if intent['kind'] == 'update':
            if same and len(staged) == 1 and not status.get('rollbackQueued'):
                new = staged[0]
                good = keys[1:] == before and list(key(booted)) == before[0]
            elif not same and not staged and not status.get('rollbackQueued'):
                new = booted
                good = keys == [list(key(booted)), before[0], before[-1]]
            else:
                return None
            if not (good and new['container-image-reference-digest'] == intent['digest'] and not new['pinned']
                    and list(key(new)) not in before):
                return None
            pending = keys if same else [list(key(new)), *before]
            expected = [list(key(new)), before[0], before[-1]]
        else:
            order = [before[1], before[0], before[2]] if len(before) == 3 else None
            if not (order and intent['target'] == before[1] and keys == order and not staged):
                return None
            if same:
                if not (status.get('rollbackQueued') and list(key(booted)) == before[0]):
                    return None
            elif status.get('rollbackQueued') or list(key(booted)) != before[1]:
                return None
            new, pending, expected = rows[0], order, order
        return dict(kind=intent['kind'], status='recorded', boot=intent['boot'], reference=image_reference(new),
            booted=list(key(new)), before=before, pending=pending, expected=expected)

    def finish(self, kind, state):
        """Turn this command's intent into the full record, or STOP unresolved."""
        intent = self.load(OUTCOME)
        require(intent.get('status') == 'intent' and intent.get('kind') == kind, 'Missing ' + kind + ' journal; get help')
        record = self.completion(intent, state)
        require(record is not None, 'The ' + kind + ' did not make the intended change; do not reboot; get help')
        self.save(OUTCOME, record)
        return record

    def load(self, name):
        path = self.store / (name + '.json')
        require(path.is_file() and not path.is_symlink(), 'Missing private ' + name + ' record')
        return json.loads(path.read_text())

    def save(self, name, value):
        path = self.store / (name + '.json')
        descriptor, name = tempfile.mkstemp(prefix='.' + name + '.', suffix='.new', dir=self.store)
        temporary = pathlib.Path(name)
        try:
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                json.dump(value, stream, indent=2)
                stream.write('\n')
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(path)
            sync_directory(self.store)
        finally:
            temporary.unlink(missing_ok=True)

    def script(self, name, replacements=None):
        text = (self.payload / 'release' / (name + '.sh')).read_text()
        for parameter, value in (replacements or {}).items():
            text = text.replace('@' + parameter + '@', value)
        require(not re.search('@[A-Z_]+@', text), 'Unresolved release script parameter')
        return self.host.script(text, name)

    def pin_step(self, cleanup_only):
        body = (self.payload / 'release/pin-stock.sh').read_text().split("<<'PIN_STOCK'\n", 1)[1].split('\nPIN_STOCK', 1)[0]
        source = "__name__ = 'owner_shared_step'\n" + body + '\npin_stock(cleanup_only=' + repr(cleanup_only) + ')\n'
        self.host.script("python3 - <<'OWNER_PIN'\n" + source + '\nOWNER_PIN\n', 'cleanup' if cleanup_only else 'pin')

    def prepare(self):
        expected = self.load('disks')
        disks = setup_identity(disk_record(self.host, expected))
        state = observations(self.host)
        saved = self.load('prepared') if (self.store / 'prepared.json').exists() else None
        intent = self.load('prepare-intent') if (self.store / 'prepare-intent.json').exists() else None
        processes = self.processes()
        stock = agree(state) if intent and not saved else preflight_prepare(state, processes, saved, self.pause['SYSTEM'])
        account(self.host)
        before_bls = resolved_bls()
        validate_bls(state, before_bls)
        repair = program(self.payload, 'system-keyboard', 'SYSTEM_KEYBOARD')
        args = repair['arguments'](self.host.read('rpm-ostree', 'kargs').strip())
        require(args and any(a.startswith('ostree=') for a in args), 'Missing boot target in kernel arguments')
        deferred = runtime_state(self.host)
        if saved:
            require(before_bls == saved['bls'], 'Prepared BLS state changed')
            require(not any(repair['keymap_argument'](a) for a in args), 'Prepared keymap override returned')
            paused_state(self.host, self.pause)
            if intent and intent['phase'] != 'complete':
                prepare_resume(intent, state, before_bls, args, checked_bundle(self.payload), disks)
                intent['phase'] = 'complete'
                self.save('prepare-intent', intent)
            self.host.trace.append(dict(flatpak=deferred))
            return ['Already prepared; no OS mutations', 'stock ' + ' '.join(map(str, key(stock))), 'Flatpak state recorded; it does not block']
        if intent:
            prepare_resume(intent, state, before_bls, args, checked_bundle(self.payload), disks)
            if intent['phase'] != 'pause': idle(state, processes)
            else: preflight_prepare(state, processes, updater_names=self.pause['SYSTEM'])
        else:
            intent = dict(schema='prepare1', manifest=checked_bundle(self.payload), disks=disks,
                initial=state, stock_identity=list(key(stock)), before_bls=before_bls,
                original_kargs=args, phase='pause')
            # Durable intent precedes every shared step, including the pause.
            self.save('prepare-intent', intent)
        def advance(phase):
            intent['phase'] = phase
            self.save('prepare-intent', intent)
        # Existing shared scripts retain their own immediate safety checks.
        if intent['phase'] == 'pause':
            self.script('pause-stock-updates')
            advance('cleanup')
        if intent['phase'] == 'cleanup':
            self.pin_step(True)
            advance('keyboard')
        if intent['phase'] == 'keyboard':
            self.script('system-keyboard')
            advance('pin')
        if intent['phase'] == 'pin':
            if not agree(observations(self.host))['pinned']:
                self.pin_step(False)
            advance('records')
        after = observations(self.host)
        now = agree(after)
        require(key(now) == key(stock) and now['pinned'], 'Prepared stock identity/pin changed')
        idle(after, self.processes())
        bls = resolved_bls()
        validate_bls(after, bls)
        unchanged_old(intent['initial'], intent['before_bls'], bls)
        self.save('prepared', dict(stock_identity=list(key(now)), stock=now, state=after,
            bls=bls, flatpak=deferred, updaters=paused_state(self.host, self.pause), before_bls=intent['before_bls']))
        advance('complete')
        return ['stock ' + ' '.join(map(str, key(now))), 'pin yes; pending none; updaters paused',
                'Flatpak state recorded; network may now be enabled']

    def title(self):
        saved = self.load('prepared')
        state = observations(self.host)
        settled = self.qualified(state, saved)
        idle(state, self.processes())
        matches = [d for d in state['rpm']['deployments'] if key(d) == tuple(saved['stock_identity'])]
        require(len(matches) == 1 and matches[0]['pinned'] and
            all(matches[0][k] == saved['stock'][k] for k in ('container-image-reference', 'container-image-reference-digest')), 'Saved stock identity/pin/origin changed')
        bls = resolved_bls()
        validate_bls(state, bls)
        entry = [e for e in bls if e['identity'] == saved['stock_identity']]
        require(len(entry) == 1, 'Saved stock BLS target missing or ambiguous')
        if not (self.store / 'network-verified.json').exists():
            require(state == saved['state'] and bls == saved['bls'], 'Deployment list/pin/pending/BLS changed after prepare')
            self.save('network-verified', dict(state=state, bls=bls, flatpak=runtime_state(self.host)))
        notes = []
        if settled is not None:
            value = self.load(OUTCOME)
            change = ('Update to ' if value['kind'] == 'update' else 'Return to ') + value['reference']
            if settled == 'done':
                # The restart gave exactly the recorded result: keep it, clear it.
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
                self.save(stamp + '-outcome-confirmed', dict(value, confirmed_state=state))
                (self.store / (OUTCOME + '.json')).unlink()
                sync_directory(self.store)
                notes.append(change + ' confirmed after the restart')
            else:
                notes.append(change + ' is not finished until the restart')
        result = dict(state=state, bls=bls, title=entry[0], flatpak=runtime_state(self.host))
        self.save('title', result)
        return [*notes, 'stock ' + ' '.join(map(str, saved['stock_identity'])), 'pin yes; transaction idle',
                'staged ' + str(bool(state['bootc']['status'].get('staged'))) + '; rollback queued ' + str(bool(state['bootc']['status'].get('rollbackQueued'))),
                'title ' + entry[0]['title'], 'Previous title INVALID; use this record until the next reorder',
                'Title is provisional until the next boot; refresh after boot' if state['bootc']['status'].get('staged') else 'Title resolves the exact saved stock serial',
                'Flatpak sync state saved; unfinished sync is expected and does not block']

    def records(self):
        record = disk_record(self.host, self.load('disks'))
        self.save('record-c', record)
        return ['target ' + record['target']['path'] + ' serial ' + str(record['target']['serial']),
                'EFI PARTUUID ' + record['esp_guid'], *self.title()]

    def before_switch(self):
        saved = self.load('prepared')
        state = observations(self.host)
        stock = agree(state)
        idle(state, self.processes())
        require(key(stock) == tuple(saved['stock_identity']) and stock['pinned'], 'Not booted saved pinned stock')
        require(state == saved['state'] and resolved_bls() == saved['bls'], 'Stock list/pin/pending/BLS changed before switch')
        require((self.store / 'network-verified.json').exists(), 'Run title after enabling the network first')
        disk_record(self.host, self.load('disks'))
        account(self.host)
        paused_state(self.host, self.pause)
        return state

    def before_update(self):
        """Read-only: a running AresOS that may stage the bundle's newer release."""
        require(not (self.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        saved = self.load('prepared')
        disk_record(self.host, self.load('disks'))
        state = observations(self.host)
        idle(state, self.processes())
        settled = self.qualified(state, saved, retry='update')
        booted = agree(state)
        if settled == 'complete':
            return state, booted, settled
        rows, status = state['rpm']['deployments'], state['bootc']['status']
        require(not status.get('staged') and not any(d.get('staged') for d in rows), 'A staged deployment already exists; do not reboot; get help')
        require(not status.get('rollbackQueued'), 'A rollback is queued; do not update; get help')
        known = known_releases(self.release['reference'], self.known())
        digest, target = booted['container-image-reference-digest'], self.release['reference'].split('@')[1]
        # No downgrade can pass: the target is the history's newest record, and
        # a running release newer than these tools is unknown to them and STOPs.
        require(digest in known, 'Update starts only from a running AresOS release; get help')
        require(digest != target, 'This release is already running; nothing to update')
        require(not any(d['container-image-reference-digest'] == target for d in rows), 'Target release is already deployed; get help')
        for d in rows:
            if d['container-image-reference-digest'] != BASE:
                require(not any(d.get(k) for k in MODIFIED) and d.get('unlocked', 'none') == 'none', 'Modified AresOS deployment; get help')
        validate_bls(state, resolved_bls())
        return state, booted, settled

    def login(self):
        # Before the first switch the stock rules apply unchanged; on a
        # running AresOS a login only serves an update to the bundle's release.
        if agree(observations(self.host))['container-image-reference-digest'] == BASE:
            self.before_switch()
        else:
            require(self.before_update()[2] != 'complete', 'An interrupted update only needs recording: run update')
        require(sys.stdin.isatty(), 'Login requires a real hidden terminal prompt')
        podman = shutil.which('podman', path='/usr/bin:/usr/sbin')
        require(podman and pathlib.Path(podman).is_absolute(), 'podman is missing')
        auth = AUTH
        require(not auth.is_symlink() and not auth.parent.is_symlink(), 'Credential path is a link')
        if auth.parent.exists():
            require(auth.parent.stat().st_uid == 0 and not auth.parent.stat().st_mode & 0o022, 'Credential directory is not root-controlled')
        if auth.exists():
            require(auth.is_file() and auth.stat().st_uid == 0 and stat.S_IMODE(auth.stat().st_mode) == 0o600, 'Existing credential ownership/mode incorrect')
        username = input('GitHub username: ').strip()
        require(re.fullmatch('[a-zA-Z0-9-]+', username), 'Invalid GitHub username')
        secret = getpass.getpass('Read-only token (hidden): ')
        require(secret and '\n' not in secret and '\r' not in secret, 'Invalid token input')
        validate_login(username, secret, self.release['reference'])
        auth.parent.mkdir(mode=0o700, exist_ok=True)
        # Never capture or retain podman's output, even on an authentication error.
        result = subprocess.run([podman, 'login', '--authfile', str(auth), '--username', username,
            '--password-stdin', 'ghcr.io'], input=secret.encode(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
        del secret
        require(result.returncode == 0, 'Registry login failed; recheck token scope/expiry; no reboot')
        auth.chmod(0o600)
        require(auth.stat().st_uid == 0 and stat.S_IMODE(auth.stat().st_mode) == 0o600, 'Credential ownership/mode incorrect')
        return ['Private registry login succeeded; token excluded from diagnostics']

    def verify(self):
        self.before_switch()
        authentication()
        require(shutil.which('cosign', path='/usr/sbin:/usr/bin:/sbin:/bin'), 'cosign is missing')
        self.script('verify', {'REFERENCE': self.release['reference'], 'IDENTITY': self.release['signature']['identity']})
        self.save('verified', dict(reference=self.release['reference'], prepared=self.load('prepared')['stock_identity']))
        return ['signature verified ' + self.release['reference']]

    def switch(self):
        before = self.before_switch()
        authentication()
        require(self.load('verified') == dict(reference=self.release['reference'], prepared=self.load('prepared')['stock_identity']), 'Verify this exact release first')
        self.script('switch', {'REFERENCE': self.release['reference']})
        state = observations(self.host)
        self.qualified(state)
        slot = state['bootc']['status']['staged']
        require(slot and slot['image']['image']['image'] == self.release['reference']
            and slot['image']['imageDigest'] == self.release['reference'].split('@')[1]
            and not state['bootc']['status']['rollbackQueued'], 'Staged switch identity mismatch; do not reboot')
        return ['Signed exact release staged', *self.title(), 'Reboot only after saving this refreshed title; F12 then Linux']

    def recover(self, keep=False):
        saved = self.load('prepared')
        disk_record(self.host, self.load('disks'))
        state = observations(self.host)
        preflight_recovery(state, self.processes(), saved, self.release['reference'], keep, self.known())
        self.outcome(state)
        if keep:
            self.script('default-stock', {'STOCK_CHECKSUM': saved['stock_identity'][0], 'BASE_DIGEST': BASE})
        else:
            self.script('rollback', {'BASE_DIGEST': BASE})
            require(observations(self.host)['bootc']['status']['rollbackQueued'] is True, 'Rollback was not queued; do not reboot')
        after = observations(self.host)
        self.qualified(after, saved)
        require(sorted(state['rpm']['deployments'], key=key) == sorted(after['rpm']['deployments'], key=key),
                'Recovery changed deployment identities or flags; do not reboot')
        return ['Saved stock is default' if keep else 'Saved stock rollback queued', *self.title()]

    def update(self):
        """Verify and stage the bundle's newer signed release over the running one.

        The running AresOS stays as rollback and the pinned stock stays as it
        is. Every refusal before the staging step leaves the system unchanged.
        """
        before, booted, settled = self.before_update()
        target, identity = self.release['reference'], self.release['signature']['identity']
        if settled == 'complete':
            # An interrupted run verified and staged this release; only its record is missing.
            require(self.load(OUTCOME)['reference'] == target, 'The interrupted update was for another release; get help')
            record = self.finish('update', before)
            return ['Interrupted update recorded: ' + record['reference'], *self.title()]
        stored_login(target)
        require(shutil.which('cosign', path='/usr/sbin:/usr/bin:/sbin:/bin'), 'cosign is missing')
        self.script('verify', {'REFERENCE': target, 'IDENTITY': identity})
        # Verification takes time: every safety check again, immediately before staging.
        again, _, _ = self.before_update()
        require(again['rpm']['deployments'] == before['rpm']['deployments'],
            'Deployments changed during verification; nothing was staged; get help')
        self.intend('update', before, target, None, settled)
        self.script('update', {'REFERENCE': target, 'CURRENT': image_reference(booted),
                               'CURRENT_DIGEST': booted['container-image-reference-digest']})
        after = observations(self.host)
        qualified_state(after, self.load('prepared'), target, self.known())
        status = after['bootc']['status']
        slot = status['staged']
        require(slot and slot['image']['image']['image'] == target and slot['image']['imageDigest'] == target.split('@')[1]
            and not status['rollbackQueued'] and key(agree(after)) == key(booted), 'Staged update identity mismatch; do not reboot')
        retained = [d for d in after['rpm']['deployments'] if not d.get('staged')]
        require(retained == before['rpm']['deployments'], 'Update changed the retained deployments; do not reboot; get help')
        self.finish('update', after)
        lines = ['Signed exact release staged ' + target, 'Running release stays as rollback ' + image_reference(booted)]
        if len(retained) == 3:
            lines.append('Older AresOS ' + image_reference(retained[1]) + ' is removed when the update finishes at shutdown')
        return [*lines, *self.title(), 'Reboot only after saving this refreshed title; F12 then Linux']

    def previous(self):
        """Queue the previous AresOS release after an update; the stock pin stays."""
        require(not (self.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        saved = self.load('prepared')
        disk_record(self.host, self.load('disks'))
        state = observations(self.host)
        idle(state, self.processes())
        settled = self.qualified(state, saved, retry='previous')
        if settled == 'complete':
            record = self.finish('previous', state)
            return ['Interrupted return recorded: ' + record['reference'], *self.title()]
        rows, status = state['rpm']['deployments'], state['bootc']['status']
        require(not status.get('staged') and not status.get('rollbackQueued'), 'Pending deployment or queued rollback; get help')
        booted = agree(state)
        known = known_releases(self.release['reference'], self.known())
        require(len(rows) == 3 and booted['container-image-reference-digest'] in known,
            'No previous AresOS beside the running one; nothing to return to')
        other = rows[1]
        require(known[other['container-image-reference-digest']][0] < known[booted['container-image-reference-digest']][0],
            'The other AresOS is newer; previous only returns from an update')
        self.intend('previous', state, image_reference(other), list(key(other)), settled)
        self.script('previous', {'PREVIOUS': image_reference(other), 'PREVIOUS_DIGEST': other['container-image-reference-digest'],
                                 'PREVIOUS_CHECKSUM': other['checksum']})
        after = observations(self.host)
        require(after['bootc']['status']['rollbackQueued'] is True, 'Return was not queued; do not reboot')
        qualified_state(after, saved, self.release['reference'], self.known())
        require(sorted(rows, key=key) == sorted(after['rpm']['deployments'], key=key),
            'Return changed deployment identities or flags; do not reboot')
        self.finish('previous', after)
        return ['Previous AresOS queued for the next start ' + image_reference(other), *self.title()]

    def reboot(self):
        require(not (self.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        saved = self.load('prepared')
        state = observations(self.host)
        idle(state, self.processes())
        self.qualified(state, saved)
        title = self.load('title')
        require(title['state'] == state and title['bls'] == resolved_bls(), 'Title is stale; run title and save it before reboot')
        media = media_module(self.payload)
        require(media.find(self.host, require) is None, 'Tools stick is still attached; export, unplug, then retry reboot')
        disk_record(self.host, self.load('disks'))
        self.host.mutate('systemctl', 'reboot')
        return ['Reboot requested; Windows stays default; F12 then Linux for one Linux start']

    def check(self):
        saved = self.load('prepared')
        state = observations(self.host)
        idle(state, self.processes())
        self.qualified(state, saved)
        disk_record(self.host, self.load('disks'))
        settings = self.keyboard()
        dump = self.host.read('dumpkeys', '-C', '/dev/tty3', '--keys-only')
        profile = settings['VConsoleKeymap']
        require(profile in ('de', 'us', 'us-intl'), 'Unsupported loaded keyboard profile; get help')
        for code, letter in zip((21, 44), ('z', 'y') if profile == 'de' else ('y', 'z')):
            rows = re.findall(r'^keycode\s+' + str(code) + r'\s*=\s*([^\s]+)', dump, re.M)
            require(len(rows) == 1 and rows[0] in (letter, '+' + letter, 'U+' + format(ord(letter), '04x'), '+U+' + format(ord(letter), '04x')),
                'Loaded console keys differ from system layout')
        cmdline = pathlib.Path('/proc/cmdline').read_text().split()
        bls = resolved_bls()
        options = [bls_arguments(e) for e in keyboard_entries(state, saved, bls)]
        require(not any(re.match(r'(?:rd\.)?vconsole\.keymap(?:[._]toggle)?(?:=|$)', a) for args in [cmdline, *options] for a in args),
            'A booted or retained keymap override remains')
        booted = state['bootc']['status']['booted']['image']['imageDigest']
        records = {row['reference'].split('@')[1]: row for row in self.lineage()['releases']}
        if booted in records:
            # Each release's own record says whether ares is an administrator;
            # exactly that answer is required, never either.
            wheel = records[booted]['daily_wheel']
            require(self.host.read('id', '-u', 'ares').strip() == '1001'
                and ('wheel' in self.host.read('id', '-nG', 'ares').split()) is wheel,
                'Daily account identity/privilege differs from this release record')
            self.host.read('pgrep', '-u', 'ares', '-x', 'labwc')
            self.host.read('pgrep', '-u', 'ares', '-x', 'foot')
        else:
            require(booted == BASE, 'Unknown booted image; get help')
            self.script('stock-session')
        return ['System console ' + profile + '; X11 ' + settings['X11Layout'] + ' variant ' + settings['X11Variant'],
                'Loaded y/z map, cmdline and all retained BLS maps passed', *self.title(),
                'Also prove yz-/!ü by physical typing in the console and labwc terminal']

    def logs(self):
        self.host.read('journalctl', '-b', '-1', '-u', 'systemd-logind.service',
            '--lines=200', '--output=json', '--no-pager')
        return ['Previous boot logind diagnostics saved privately (at most 200 records)',
                'This does not prove a physical power-button event; the laptop gate remains open']

    def export(self):
        media = media_module(self.payload)
        return media.export(self.host, self.store, checked_bundle(self.payload), checked_bundle, require)

    def keyboard(self):
        values = self.host.json('busctl', '--system', '--json=short', 'call',
            'org.freedesktop.locale1', '/org/freedesktop/locale1', 'org.freedesktop.DBus.Properties',
            'GetAll', 's', 'org.freedesktop.locale1')['data'][0]
        return {name: values[name]['data'] for name in ('VConsoleKeymap', 'VConsoleKeymapToggle', 'X11Layout', 'X11Model', 'X11Variant', 'X11Options')}

    def set_keyboard(self, values):
        self.host.mutate('localectl', '--no-convert', 'set-keymap', values['VConsoleKeymap'], values['VConsoleKeymapToggle'])
        self.host.mutate('localectl', '--no-convert', 'set-x11-keymap',
            *[values[k] for k in ('X11Layout', 'X11Model', 'X11Variant', 'X11Options')])
        require(self.keyboard() == values, 'Keyboard setting did not round-trip')

    def trial_keyboard(self, values):
        require(values['VConsoleKeymap'] in ('de', 'us', 'us-intl') and not values['VConsoleKeymapToggle'],
            'Unsupported finished console map; get help before a trial')
        # loadkeys changes the kernel console map, not localed or /etc. A
        # reboot therefore always reloads the last finished system setting.
        self.host.mutate('loadkeys', '-C', '/dev/tty3', '--', values['VConsoleKeymap'])

    def session(self):
        require(sys.stdin.isatty(), PHYSICAL_LOGIN)
        require(pathlib.Path('/proc/self/loginuid').read_text().strip() == '1000', 'Use ares-recovery, authenticated with its password')
        try:
            session = logind_scope(pathlib.Path('/proc/self/cgroup').read_text())
            audit = pathlib.Path('/proc/self/sessionid').read_text().strip()
            require(audit.isdigit() and 0 <= int(audit) < 4294967295, PHYSICAL_LOGIN)
        except (OSError, ValueError, IndexError):
            raise Stop(PHYSICAL_LOGIN) from None
        sessions = self.host.json('loginctl', 'list-sessions', '--json=short')
        require(isinstance(sessions, list) and all(isinstance(s, dict)
            and {'session', 'tty', 'user', 'uid'} <= s.keys() for s in sessions), PHYSICAL_LOGIN)
        matching = [s for s in sessions if str(s['session']) == session and s['tty'] in ('tty3', 'tty4')
            and s['user'] == 'ares-recovery' and s['uid'] == 1000]
        require(len(matching) == 1, 'Cannot identify this physical recovery session')
        tty = matching[0]['tty']
        identity = login_properties(self.host, session, ('Id', 'TTY', 'Audit', 'Scope'), PHYSICAL_LOGIN)
        require(identity == dict(Id=session, TTY=tty, Audit=audit, Scope='session-' + session + '.scope'), PHYSICAL_LOGIN)
        details = login_properties(self.host, session, ('TimestampMonotonic',),
            'Cannot read recovery login time')['TimestampMonotonic']
        require(details.isdigit(), 'Cannot read recovery login time')
        facts = login_properties(self.host, session, ('Service', 'Type', 'Remote', 'Name', 'User'),
            'Proof is not a local physical recovery login')
        require(facts == dict(Service='login', Type='tty', Remote='no', Name='ares-recovery', User='1000'),
            'Proof is not a local physical recovery login')
        try:
            physical_stdin(tty, os.ttyname(0))
            require(logind_scope(pathlib.Path('/proc/self/cgroup').read_text()) == session
                and pathlib.Path('/proc/self/sessionid').read_text().strip() == audit, PHYSICAL_LOGIN)
        except (OSError, ValueError, IndexError):
            raise Stop(PHYSICAL_LOGIN) from None
        return dict(tty=tty, session=str(matching[0]['session']), started_us=int(details),
            boot=pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip())

    def layout(self, action, profile=None):
        profiles = {
            'de': dict(VConsoleKeymap='de', VConsoleKeymapToggle='', X11Layout='de', X11Model='pc105', X11Variant='', X11Options=''),
            'us': dict(VConsoleKeymap='us', VConsoleKeymapToggle='', X11Layout='us', X11Model='pc105', X11Variant='', X11Options=''),
            'us-intl': dict(VConsoleKeymap='us-intl', VConsoleKeymapToggle='', X11Layout='us', X11Model='pc105', X11Variant='intl', X11Options='')}
        require(action == 'begin' and profile in profiles or action in ('proof', 'revert', 'finish', 'abandon') and profile is None,
                'Choose begin with a profile, or proof/revert/finish/abandon without extra arguments')
        if action == 'begin':
            require(profile in profiles, 'Choose de, us or us-intl')
            state = observations(self.host)
            preflight_recovery(state, self.processes(), self.load('prepared'), self.release['reference'], history=self.known())
            self.outcome(state)
            disk_record(self.host, self.load('disks'))
            session = self.session()
            old = self.keyboard()
            require(old in profiles.values(), 'Unsupported finished system layout; get help')
            require(old != profiles[profile], 'Layout already selected; no change needed')
            pending = self.store / 'layout-pending.json'
            require(not pending.exists(), 'Finish or revert the pending layout trial first')
            value = dict(old=old, new=profiles[profile], administrator=session, deployment_identity=list(key(agree(state))),
                began_us=int(time.monotonic() * 1000000), proof=None)
            self.save('layout-pending', value)
            try:
                self.trial_keyboard(value['new'])
            except (Stop, OSError, subprocess.SubprocessError):
                self.trial_keyboard(old)
                value['reverted'] = True
                self.save('layout-pending', value)
                raise Stop('Layout change failed; old settings restored. Keep this session open; do not reboot')
            return ['Console-only trial; system/greeter layout stays finished until layout finish',
                'Keep this administrator console OPEN; reboot is not authorized',
                'Ctrl+Alt+F4: fresh ares-recovery password login in the new layout',
                'Then sudo -k; sudo /var/lib/ares/at layout proof',
                'If typing/login fails: Ctrl+Alt+F3; sudo /var/lib/ares/at layout revert']
        value = self.load('layout-pending')
        current = self.session()
        if action == 'abandon':
            state = observations(self.host)
            saved = self.load('prepared')
            booted = agree(state)
            stock_side = booted['container-image-reference-digest'] == BASE
            preflight_recovery(state, self.processes(), saved, self.release['reference'], keep=stock_side, history=self.known())
            self.outcome(state)
            disk_record(self.host, self.load('disks'))
            require(current != value['administrator'] and (current['boot'] != value['administrator']['boot']
                or current['started_us'] > value['began_us']), 'Abandon requires a fresh physical administrator login')
            finished = self.keyboard()
            persistent_before = copy.deepcopy(finished)
            # Each deployment has its own /etc. Retained stock keeps its own
            # last finished (installer) setting; never write AresOS settings
            # into it. Runtime-only trials have not changed either /etc.
            if list(key(booted)) == value['deployment_identity']:
                require(value['old'] in profiles.values() and value['new'] in profiles.values(),
                    'Unsupported recorded layout trial; get help')
                partial = dict(value['old'], **{k:value['new'][k] for k in ('VConsoleKeymap', 'VConsoleKeymapToggle')})
                require(finished == value['old'] or value.get('finishing') and value['proof']
                    and finished in (partial, value['new']), 'Finished system layout changed during the abandoned trial')
                if finished != value['old']:
                    self.set_keyboard(value['old'])
                    finished = value['old']
            else:
                require(stock_side, 'Abandoned trial belongs to another deployment')
                require(finished in profiles.values(), 'Unsupported finished system layout; get help')
            self.trial_keyboard(finished)
            self.save('layout-abandoned', dict(trial=value, administrator=current, restored=finished,
                persistent_settings_unchanged=self.keyboard() == persistent_before, stock_side=stock_side))
            (self.store / 'layout-pending.json').unlink()
            sync_directory(self.store)
            return ['Last finished console layout restored; abandoned trial cleared',
                'Last finished persistent layout verified; stock settings preserved', *self.title()]
        require(current['boot'] == value['administrator']['boot'], 'Trial crossed a reboot without completing the proof')
        if action == 'revert':
            require(current == value['administrator'], 'Revert from the original open administrator session')
            self.trial_keyboard(value['old'])
            value.update(reverted=True, proof=None, began_us=int(time.monotonic() * 1000000))
            self.save('layout-pending', value)
            return ['Old console/X11 settings restored; no reboot', 'Log out tty4; prove a fresh password login using the old layout',
                    'Then sudo -k; sudo /var/lib/ares/at layout proof']
        if action == 'proof':
            require(current['session'] != value['administrator']['session']
                and current['tty'] != value['administrator']['tty'] and current['started_us'] > value['began_us'],
                'Proof requires a fresh second-console password login after the change/revert')
            expected = value['old'] if value.get('reverted') else value['new']
            require(self.keyboard() == value['old'], 'Finished system settings changed during the trial')
            dump = self.host.read('dumpkeys', '-C', '/dev/' + current['tty'], '--keys-only')
            for code, letter in zip((21, 44), ('z', 'y') if expected['VConsoleKeymap'] == 'de' else ('y', 'z')):
                rows = re.findall(r'^keycode\s+' + str(code) + r'\s*=\s*([^\s]+)', dump, re.M)
                require(len(rows) == 1 and rows[0] in (letter, '+' + letter, 'U+' + format(ord(letter), '04x'), '+U+' + format(ord(letter), '04x')),
                    'New console map was not actually loaded; revert before reboot')
            require(input('Physically type yz-/!ü then Return: ') == 'yz-/!ü', 'Physical typing differs; return to the first console and revert')
            value['proof'] = current
            self.save('layout-pending', value)
            return ['Fresh second-console login and physical typing passed', 'Return to the original console; use layout finish']
        require(action == 'finish' and profile is None, 'Choose begin, proof, revert or finish')
        require(current == value['administrator'] and value['proof'], 'Keep the original session open and complete the second-console proof first')
        require(self.keyboard() == value['old'], 'Finished system settings changed after proof')
        title = self.title()
        # Persist only after the new console password and typing have passed.
        # Until this explicit finish action, both boot/greeter files stay old.
        if not value.get('reverted'):
            value['finishing'] = True
            self.save('layout-pending', value)
            try:
                self.set_keyboard(value['new'])
            except (Stop, OSError, subprocess.SubprocessError):
                self.set_keyboard(value['old'])
                raise Stop('Layout finish failed; old settings restored. Keep this session open; use fresh-login abandon if needed')
        self.save('layout-completed', value)
        (self.store / 'layout-pending.json').unlink()
        sync_directory(self.store)
        return ['Layout trial completed; fresh login/typing proof saved', *title,
                'Reboot is now permitted. Windows stays default; use F12 then Linux',
                'After boot check loaded console keys and physical typing in the labwc terminal']


def tools_stick(host, payload, fingerprint):
    media = media_module(payload)
    device = media.find(host, require)
    require(device is not None, 'Tools USB label not found')
    # The trusted bootstrap executes a private copy. Its original remains on
    # the uniquely identified, read-only-mounted stick until install returns.
    mounts = [m for m in device['volume']['mountpoints'] if m]
    require(len(mounts) == 1, 'Tools USB must have one read-only bootstrap mount')
    source = pathlib.Path(mounts[0]) / 'ares-tools'
    mounted = mount_record(host, '--target', source)
    require(mounted['source'] == device['volume']['path'] and
        mounted['fstype'] == 'exfat' and pathlib.Path(mounted['target']) / 'ares-tools' == source,
        'Bundle is not on the labelled removable tools USB')
    require(checked_bundle(source) == fingerprint, 'Private bootstrap copy differs from the tools USB')
    return device


def discard_partial_copy(stage, payload):
    if stage.exists() or stage.is_symlink():
        require(not stage.is_symlink() and stage.is_dir() and stage.stat().st_uid == os.geteuid(), 'Unsafe partial payload directory')
        expected_files = {p.relative_to(payload).as_posix(): p for p in payload.rglob('*') if p.is_file()}
        # Clean only this journal's private, structurally exact partial
        # copy. Never recurse through a link or delete an unknown path.
        for p in stage.rglob('*'):
            relative = p.relative_to(stage).as_posix()
            require(not p.is_symlink() and p.stat().st_uid == os.geteuid()
                and (p.is_dir() and any(n.startswith(relative + '/') for n in expected_files)
                or p.is_file() and relative in expected_files
                and expected_files[relative].read_bytes().startswith(p.read_bytes())), 'Unrecognized partial payload; preserve it')
        for p in sorted(stage.rglob('*'), key=lambda p: len(p.parts), reverse=True):
            require(p.resolve().is_relative_to(HOME.resolve()), 'Partial-copy cleanup escaped installation')
            p.rmdir() if p.is_dir() else p.unlink()
        stage.rmdir()


def seal_copy(stage):
    for p in [stage, *stage.rglob('*')]:
        p.chmod(0o700 if p.is_dir() or p.name == 'at' else 0o600)
        if p.is_file():
            with p.open('rb') as stream: os.fsync(stream.fileno())
    for directory in sorted([stage, *[p for p in stage.rglob('*') if p.is_dir()]], key=lambda p: len(p.parts), reverse=True):
        sync_directory(directory)
    sync_directory(HOME)


UPDATE_NAMES = ('diagnostics', 'install-intent.json', 'tools', 'records', 'at', '.at-held',
                'tools-update-intent.json', '.update-tools', 'retired-tools')


def installed_commands(home):
    """Running commands of the installed tools, found by their real entry chain.

    sudo starts /var/lib/ares/at through its #!/usr/bin/bash line, and that
    script execs /usr/bin/python3 -I -B <resolved tools>/owner.py. The 15f
    tools take no lock, so both stages are matched by their exact paths.
    """
    real = pathlib.Path(os.path.realpath(home))
    wrappers = {str(home / 'at'), str(home / 'tools/at'), str(real / 'at'), str(real / 'tools/at')}
    entries = {str(home / 'tools/owner.py'), str(real / 'tools/owner.py')}
    found = []
    for process in pathlib.Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            raw = (process / 'cmdline').read_bytes().split(b'\0')
            exe = os.readlink(str(process / 'exe'))
        except OSError:
            # A process that ended or a kernel thread cannot run owner code.
            continue
        argv = [part.decode(errors='replace') for part in (raw[:-1] if raw and raw[-1] == b'' else raw)]
        name = os.path.basename(exe.removesuffix(' (deleted)'))
        if (name.startswith('python3') and argv[1:3] == ['-I', '-B'] and len(argv) > 3 and argv[3] in entries
                or name == 'bash' and len(argv) > 1 and argv[1] in wrappers):
            found.append(dict(pid=int(process.name), exe=exe, argv=argv[:4]))
    return found


def installed_update(fingerprint):
    """Other tools over a completed installation are an update, never a reinstall.

    The first-install route stays unchanged: no installation, an unfinished
    one, or a rerun of the bundle it was installed from.
    """
    if HOME.is_symlink() or not HOME.is_dir():
        return False
    journal = HOME / 'tools-update-intent.json'
    if journal.exists() or journal.is_symlink():
        return True
    intent = HOME / 'install-intent.json'
    if intent.is_symlink() or not intent.is_file():
        return False
    value = json.loads(intent.read_text())
    return isinstance(value, dict) and value.get('phase') == 'complete' and value.get('manifest') != fingerprint


def update_tools(payload, fingerprint, host):
    """Replace the installed tools with a newer reviewed bundle, keeping records.

    Runs from the bootstrap's verified private copy, like install. Older or
    same-version tools, a release history that does not extend the installed
    one, or a deployment state the new tools would refuse all STOP before any
    write. The old tools move, never get deleted, to retired-tools/<manifest>.
    """
    require(sys.stdin.isatty(), 'Tools update runs only from the physical recovery console')
    device = tools_stick(host, payload, fingerprint)
    owned_directory(HOME)
    for name in ('records', 'diagnostics', 'retired-tools'):
        if (HOME / name).exists() or (HOME / name).is_symlink():
            owned_directory(HOME / name)
    require(all(p.name in UPDATE_NAMES or p.name.startswith(('.install-intent.', '.tools-update-intent.'))
        and p.name.endswith('.new') for p in HOME.iterdir()), 'Unexpected installation files; preserve them and get help')
    home = object.__new__(Tools); home.store = HOME
    records = object.__new__(Tools); records.store = HOME / 'records'
    installed = home.load('install-intent')
    require(installed.get('schema') == 'install1' and installed.get('phase') == 'complete', 'Installation is unfinished; get help')
    disk_record(host, records.load('disks'))
    # While the tools are replaced the documented entry is renamed aside, so
    # no command of the old tools can start; it returns before completion.
    entry, held_entry = HOME / 'at', HOME / '.at-held'
    links = [p for p in (entry, held_entry) if p.exists() or p.is_symlink()]
    require(len(links) == 1 and links[0].is_symlink() and os.readlink(links[0]) == 'tools/at', 'Unexpected installed entry point')
    new = lineage(payload)

    def hold_entry():
        if entry.is_symlink():
            entry.replace(held_entry)
            sync_directory(HOME)

    def release_entry():
        if held_entry.is_symlink():
            require(not entry.exists() and not entry.is_symlink(), 'Unexpected installed entry point')
            held_entry.replace(entry)
            sync_directory(HOME)

    def exclusive():
        running = installed_commands(HOME)
        if running:
            release_entry()
            raise Stop('An owner command of the installed tools is running (pid ' + ', '.join(str(r['pid']) for r in running)
                + '); let it finish, then repeat this bootstrap')

    def system_ready():
        # The new tools must accept today's system before, and whenever an
        # interrupted update resumes, the copy or swap that replaces the old.
        checker = Tools(payload, host, HOME / 'records')
        require(not (checker.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        if (checker.store / 'prepare-intent.json').exists():
            require(checker.load('prepare-intent').get('phase') == 'complete', 'Prepare is unfinished; get help')
        state = observations(host)
        idle(state, checker.processes())
        checker.qualified(state)

    current, staged, retired = HOME / 'tools', HOME / '.update-tools', HOME / 'retired-tools'
    journal = HOME / 'tools-update-intent.json'
    intent = home.load('tools-update-intent') if journal.exists() or journal.is_symlink() else None
    if intent is None or intent.get('phase') == 'complete':
        require(not staged.exists() and not staged.is_symlink(), 'Unjournalled partial tools copy; preserve it and get help')
        require(not current.is_symlink() and current.is_dir(), 'Installed tools are missing; get help')
        private_tree(current)
        old = checked_bundle(current)
        require(intent is None or intent.get('manifest') == old, 'Tools update journal differs from the installed tools; get help')
        if old == fingerprint:
            require(entry.is_symlink(), 'Unexpected installed entry point')
            return ['Tools already installed; nothing changed', 'manifest SHA256 ' + fingerprint]
        old_version, old_history = installed_lineage(current, old)
        require(new['tools_version'] > old_version, 'Installed tools are version ' + str(old_version)
            + '; refusing version ' + str(new['tools_version']) + ' (downgrade or same version)')
        require(extends(old_history, new['releases']), 'Bundle release history does not extend the installed one; get help')
        require(not (retired / old).exists() and not (retired / old).is_symlink(), 'Retired tools already exist; get help')
        system_ready()
        exclusive()
        intent = dict(schema='tools-update1', previous=old, manifest=fingerprint, previous_version=old_version,
            tools_version=new['tools_version'], tools_volume_uuid=device['volume']['uuid'], phase='copy')
        home.save('tools-update-intent', intent)
    else:
        require(intent.get('schema') == 'tools-update1' and intent.get('manifest') == fingerprint
            and intent.get('tools_volume_uuid') == device['volume']['uuid']
            and intent.get('phase') in ('copy', 'swap', 'records'),
            'Interrupted tools update does not exactly match this bundle/stick; get help')
        system_ready()
        exclusive()
    # Hold the entry, then look again: a command started in between is found.
    hold_entry()
    exclusive()
    def advance(phase):
        intent['phase'] = phase
        home.save('tools-update-intent', intent)
    old, held = intent['previous'], retired / intent['previous']
    if intent['phase'] == 'copy':
        require(checked_bundle(current) == old and not held.exists(), 'Installed tools changed during the update')
        discard_partial_copy(staged, payload)
        shutil.copytree(payload, staged, symlinks=False, copy_function=shutil.copy2)
        seal_copy(staged)
        require(checked_bundle(staged) == fingerprint, 'Staged tools differ; preserve diagnostics')
        advance('swap')
    if intent['phase'] == 'swap':
        if staged.exists() or staged.is_symlink():
            require(not staged.is_symlink() and checked_bundle(staged) == fingerprint, 'Staged tools differ; get help')
            if current.exists() or current.is_symlink():
                require(not current.is_symlink() and checked_bundle(current) == old and not held.exists(),
                    'Unexpected installed tools during the swap; get help')
                exclusive()
                if not retired.exists():
                    retired.mkdir(mode=0o700)
                    sync_directory(HOME)
                owned_directory(retired)
                current.replace(held)
                sync_directory(retired)
                sync_directory(HOME)
            require(not current.exists() and checked_bundle(held) == old, 'Retired tools differ; get help')
            staged.replace(current)
            sync_directory(HOME)
        require(not staged.exists() and checked_bundle(current) == fingerprint and checked_bundle(held) == old,
            'Tools swap is ambiguous; get help')
        # The receipt name is journalled, so a resumed update writes it once.
        intent['receipt'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-tools-update'
        advance('records')
    if intent['phase'] == 'records':
        require(checked_bundle(current) == fingerprint, 'Published tools differ')
        require(re.fullmatch(r'[0-9]{8}T[0-9]{6}\.[0-9]{6}Z-tools-update', intent.get('receipt', '')), 'Invalid tools update journal')
        if not (records.store / (intent['receipt'] + '.json')).exists():
            records.save(intent['receipt'], dict(status='passed', command=['install'], manifest=fingerprint, previous_manifest=old,
                tools_version=intent['tools_version'], previous_version=intent['previous_version'],
                releases=new['releases'], tools_volume_uuid=device['volume']['uuid'], trace=host.trace))
        release_entry()
        advance('complete')
    return ['Tools updated from version ' + str(intent['previous_version']) + ' to ' + str(intent['tools_version']),
            'manifest SHA256 ' + fingerprint, 'Previous tools kept in /var/lib/ares/retired-tools (private)',
            'Release target ' + new['releases'][-1]['reference']]


def install(payload, host=None):
    payload = pathlib.Path(payload)
    fingerprint = checked_bundle(payload)
    if installed_update(fingerprint):
        return update_tools(payload, fingerprint, host if host is not None else Host())
    require(sys.stdin.isatty(), 'Install requires the two independently recorded disk serials')
    target = input('Photographed Crucial serial: ').strip()
    protected = input('Windows baseline Micron serial: ').strip()
    require(target and protected and target != protected, 'Missing or equal disk serials')
    host = host if host is not None else Host()
    device = tools_stick(host, payload, fingerprint)
    expected = dict(target=target, protected=protected)
    identity = setup_identity(disk_record(host, expected))
    # No writes until every bundle/destination/disk preflight has passed.
    require(not HOME.is_symlink(), 'Installation root is a link')
    if not HOME.exists():
        HOME.mkdir(mode=0o700)
        sync_directory(HOME.parent)
    owned_directory(HOME)
    if (HOME / 'diagnostics').exists() or (HOME / 'diagnostics').is_symlink():
        owned_directory(HOME / 'diagnostics')
    recorder = object.__new__(Tools)
    recorder.store = HOME
    intent_path = HOME / 'install-intent.json'
    stage, destination = HOME / '.install-tools', HOME / 'tools'
    if intent_path.exists():
        require(not intent_path.is_symlink() and stat.S_IMODE(intent_path.stat().st_mode) == 0o600
            and intent_path.stat().st_uid == os.geteuid(), 'Unsafe installation intent')
        intent = recorder.load('install-intent')
        require(intent['schema'] == 'install1' and intent['manifest'] == fingerprint
            and intent['disks'] == expected and intent['identity'] == identity
            and intent['tools_volume_uuid'] == device['volume']['uuid']
            and intent['phase'] in ('copy', 'records', 'publish', 'entry', 'complete'),
            'Interrupted install does not exactly match this bundle/disks/stick')
    else:
        require(all(p.name == 'diagnostics' or p.name.startswith('.install-intent.') and p.name.endswith('.new')
            for p in HOME.iterdir()), 'Unjournalled partial installation; preserve it and get help')
        intent = dict(schema='install1', manifest=fingerprint, disks=expected, identity=identity,
            tools_volume_uuid=device['volume']['uuid'], phase='copy')
        recorder.save('install-intent', intent)
    require(all(p.name in ('diagnostics', 'install-intent.json', '.install-tools', 'tools', 'records', 'at')
        or p.name.startswith('.install-intent.') and p.name.endswith('.new') for p in HOME.iterdir()),
        'Unexpected installation files; preserve them and get help')
    def advance(phase):
        intent['phase'] = phase
        recorder.save('install-intent', intent)
    if intent['phase'] == 'copy':
        require(not destination.exists() and not destination.is_symlink(), 'Unexpected published tools during copy')
        discard_partial_copy(stage, payload)
        shutil.copytree(payload, stage, symlinks=False, copy_function=shutil.copy2)
        seal_copy(stage)
        require(checked_bundle(stage) == fingerprint, 'Staged bundle differs; preserve diagnostics')
        advance('records')
    if intent['phase'] == 'records':
        require(checked_bundle(stage) == fingerprint and not destination.exists(), 'Interrupted staged payload differs')
        records = HOME / 'records'
        require(not records.is_symlink(), 'Records directory is a link')
        records.mkdir(mode=0o700, exist_ok=True)
        owned_directory(records)
        require(all(p.name in ('disks.json', 'installation.json') or p.name.startswith('.') and p.name.endswith('.new')
            for p in records.iterdir()), 'Unexpected partial-install records')
        private = object.__new__(Tools); private.store = records
        for name, value in [('disks', expected), ('installation', dict(status='passed', command=['install'],
                manifest=fingerprint, tools_volume_uuid=device['volume']['uuid'], identity=identity, trace=host.trace))]:
            if (records / (name + '.json')).exists():
                old = private.load(name)
                require({k:v for k,v in old.items() if k != 'trace'} == {k:v for k,v in value.items() if k != 'trace'},
                    'Interrupted install record differs')
            else:
                private.save(name, value)
        advance('publish')
    if intent['phase'] == 'publish':
        if destination.exists():
            require(not stage.exists() and checked_bundle(destination) == fingerprint, 'Ambiguous published payload')
        else:
            require(checked_bundle(stage) == fingerprint, 'Unverified staged tools')
            stage.replace(destination)
            sync_directory(HOME)
        advance('entry')
    require(checked_bundle(destination) == fingerprint and not stage.exists(), 'Published installation differs')
    records = object.__new__(Tools); records.store = HOME / 'records'
    require(records.load('disks') == expected and records.load('installation')['manifest'] == fingerprint,
        'Published installation records differ')
    entry = HOME / 'at'
    if entry.exists() or entry.is_symlink():
        require(entry.is_symlink() and os.readlink(entry) == 'tools/at', 'Unexpected installed entry point')
    if intent['phase'] == 'entry':
        advance('complete')
    if entry.exists() or entry.is_symlink():
        require(entry.is_symlink() and os.readlink(entry) == 'tools/at', 'Unexpected installed entry point')
    else:
        entry.symlink_to('tools/at')
        sync_directory(HOME)
    records.save(datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-install',
        dict(status='passed', command=['install'], manifest=fingerprint, trace=host.trace,
            tools_volume_uuid=device['volume']['uuid']))
    return ['manifest SHA256 ' + fingerprint, 'Use sudo /var/lib/ares/at prepare']


def refusal_record(host, result):
    # A failed install has no HOME yet. Only private diagnostics may be written
    # on refusal; never begin/correct an installation to make a recorder exist.
    try:
        firmware = host.read('efibootmgr', '-v')
        result['firmware'] = dict(stdout=firmware, observed=True)
    except (Stop, OSError, ValueError, subprocess.SubprocessError) as error:
        attempted = [r for r in host.trace if r.get('command') == ['efibootmgr', '-v']]
        result['firmware'] = dict(observed=False, error=str(error), attempts=attempted)
    if STOP_RECORDS.parent == HOME and not HOME.exists():
        parent = HOME.parent.lstat()
        require(not HOME.parent.is_symlink() and stat.S_ISDIR(parent.st_mode)
            and parent.st_uid == 0 and not parent.st_mode & 0o022, 'Unsafe diagnostic storage parent')
        HOME.mkdir(mode=0o700)
        sync_directory(HOME.parent)
    parent = STOP_RECORDS.parent.lstat()
    require(not STOP_RECORDS.parent.is_symlink() and stat.S_ISDIR(parent.st_mode)
        and parent.st_uid == 0 and not parent.st_mode & 0o022, 'Unsafe private diagnostic parent')
    STOP_RECORDS.mkdir(mode=0o700, exist_ok=True)
    info = STOP_RECORDS.lstat()
    require(not STOP_RECORDS.is_symlink() and stat.S_ISDIR(info.st_mode)
        and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == 0o700, 'Unsafe private diagnostic directory')
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
    # Reuse the atomic, exclusive, mode-0600 JSON writer without constructing
    # Tools (which would require a successful installation).
    recorder = object.__new__(Tools)
    recorder.store = STOP_RECORDS
    recorder.save(stamp + '-' + result['command'][0], result)
    print('Full diagnostics: ' + str(STOP_RECORDS) + ' (private)')


def main():
    os.umask(0o077)
    require(os.geteuid() == 0, 'Use sudo from the authenticated ares-recovery session')
    host = Host()
    known = {'install', 'prepare', 'records', 'title', 'login', 'verify', 'switch', 'rollback',
        'keep-stock', 'export', 'layout', 'reboot', 'check', 'logs', 'update', 'previous'}
    command = sys.argv[1] if len(sys.argv) >= 2 and sys.argv[1] in known else 'invalid'
    # Never record arbitrary argv: an accidentally pasted credential is not a
    # command. Layout choices are the only accepted extra arguments.
    action = [command]
    if command == 'layout' and sys.argv[2:] in ([a] for a in ('proof', 'revert', 'finish', 'abandon')):
        action += sys.argv[2:]
    elif command == 'layout' and sys.argv[2:] in (['begin', p] for p in ('de', 'us', 'us-intl')):
        action += sys.argv[2:]
    result = dict(status='stopped', command=action, manifest=None, trace=host.trace)
    lock = None
    try:
        # Held until this command ends, so two owner commands never interleave.
        lock = owner_lock()
        payload = pathlib.Path(__file__).resolve().parent
        fingerprint = checked_bundle(payload)
        result['manifest'] = fingerprint
        require(command != 'invalid', 'Choose a documented owner command')
        require(len(sys.argv) == 2 or command == 'layout' and action == sys.argv[1:] and len(action) in (2, 3),
            'Unexpected arguments; tokens are accepted only at the hidden login prompt')
        if command == 'install':
            lines = install(payload, host)
        else:
            require(payload == HOME / 'tools' and HOME.stat().st_uid == 0
                    and stat.S_IMODE(HOME.stat().st_mode) == 0o700, 'Run the installed root-only tools')
            private_tree(payload)
            private_tree(HOME / 'records')
            if STOP_RECORDS.exists():
                private_tree(STOP_RECORDS)
            tools = Tools(payload, host, HOME / 'records')
            methods = {'prepare': tools.prepare, 'records': tools.records, 'title': tools.title,
                       'login': tools.login, 'verify': tools.verify, 'switch': tools.switch,
                       'rollback': tools.recover, 'keep-stock': lambda: tools.recover(True), 'export': tools.export,
                       'layout': lambda: tools.layout(*action[1:]), 'reboot': tools.reboot, 'check': tools.check, 'logs': tools.logs,
                       'update': tools.update, 'previous': tools.previous}
            lines = methods[command]()
            result.update(status='passed', result=lines)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            tools.save(stamp + '-' + command, result)
    except (Stop, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, AssertionError, EOFError, KeyboardInterrupt) as error:
        result['status'] = 'stopped'
        result['error'] = str(error) if not isinstance(error, (EOFError, KeyboardInterrupt)) else 'Input ended or interrupted'
        try:
            refusal_record(host, result)
        except (Stop, OSError, ValueError, subprocess.SubprocessError) as diagnostic_error:
            print('STOP: private diagnostics could not be saved: ' + str(diagnostic_error))
        raise
    finally:
        if lock is not None:
            os.close(lock)
    print('PASS ' + ' '.join(sys.argv[1:]))
    print('\n'.join(lines))
    print('Full diagnostics: /var/lib/ares/records (private)')


if __name__ == '__main__':
    try:
        main()
    except (Stop, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, AssertionError, EOFError, KeyboardInterrupt) as error:
        print('STOP: ' + str(error))
        print('Keep the current administrator session open. Preserve diagnostics; do not reboot or retry a different target. See EMERGENCY / get help.')
        sys.exit(1)
