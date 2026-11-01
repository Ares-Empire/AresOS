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


class Stop(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Stop(message)


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


def preflight_recovery(state, processes, saved, release, keep=False):
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
    require(not ares['pinned'] and ares['container-image-reference-digest'] == release.split('@')[1]
            and ares['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://') == release,
            'Wrong AresOS target')
    require(booted is (stock if keep else ares),
            'Use keep-stock on booted stock' if not keep else 'keep-stock requires booted saved stock')
    return stock


def qualified_state(state, saved, release):
    booted = agree(state)
    rows = state['rpm']['deployments']
    status = state['bootc']['status']
    stock = [d for d in rows if key(d) == tuple(saved['stock_identity'])]
    require(len(stock) == 1 and stock[0]['pinned'] and all(stock[0][k] == saved['stock'][k]
        for k in ('container-image-reference', 'container-image-reference-digest')), 'Saved stock changed')
    ares = [d for d in rows if d['container-image-reference-digest'] == release.split('@')[1]]
    if not ares:
        require(state == saved['state'], 'Unexpected prepared deployment list/pending state')
        return
    require(len(ares) == 1 and not ares[0]['pinned'] and ares[0]['checksum'] != stock[0]['checksum']
        and ares[0]['container-image-reference'].removeprefix('ostree-unverified-registry:').removeprefix('ostree-image-signed:docker://') == release,
        'Unexpected AresOS identity or origin')
    staged = [d for d in rows if d.get('staged')]
    if staged:
        require(staged == ares and status.get('staged') and not status.get('rollbackQueued')
            and key(booted) == tuple(saved['stock_identity']), 'Unexpected staged switch')
        retained = [d for d in rows if not d.get('staged')]
        require(retained == saved['state']['rpm']['deployments'], 'Switch changed the retained stock list')
    else:
        require(len(rows) == 2 and status.get('staged') is None, 'Final pair has extra/missing deployments')
        if status.get('rollbackQueued'):
            require(booted is ares[0] and status['rollback']['ostree']['checksum'] == stock[0]['checksum']
                and status['rollback']['ostree']['deploySerial'] == stock[0]['serial'], 'Wrong queued rollback')


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
    require(len(matches) == 1, 'Linux firmware entry does not uniquely map to target EFI')
    return matches[0]


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
        qualified_state(state, saved, self.release['reference'])
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
        result = dict(state=state, bls=bls, title=entry[0], flatpak=runtime_state(self.host))
        self.save('title', result)
        return ['stock ' + ' '.join(map(str, saved['stock_identity'])), 'pin yes; transaction idle',
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

    def login(self):
        self.before_switch()
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
        qualified_state(state, self.load('prepared'), self.release['reference'])
        slot = state['bootc']['status']['staged']
        require(slot and slot['image']['image']['image'] == self.release['reference']
            and slot['image']['imageDigest'] == self.release['reference'].split('@')[1]
            and not state['bootc']['status']['rollbackQueued'], 'Staged switch identity mismatch; do not reboot')
        return ['Signed exact release staged', *self.title(), 'Reboot only after saving this refreshed title; F12 then Linux']

    def recover(self, keep=False):
        saved = self.load('prepared')
        disk_record(self.host, self.load('disks'))
        state = observations(self.host)
        preflight_recovery(state, self.processes(), saved, self.release['reference'], keep)
        if keep:
            self.script('default-stock', {'STOCK_CHECKSUM': saved['stock_identity'][0], 'BASE_DIGEST': BASE})
        else:
            self.script('rollback', {'BASE_DIGEST': BASE})
            require(observations(self.host)['bootc']['status']['rollbackQueued'] is True, 'Rollback was not queued; do not reboot')
        after = observations(self.host)
        qualified_state(after, saved, self.release['reference'])
        require(sorted(state['rpm']['deployments'], key=key) == sorted(after['rpm']['deployments'], key=key),
                'Recovery changed deployment identities or flags; do not reboot')
        return ['Saved stock is default' if keep else 'Saved stock rollback queued', *self.title()]

    def reboot(self):
        require(not (self.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        saved = self.load('prepared')
        state = observations(self.host)
        idle(state, self.processes())
        qualified_state(state, saved, self.release['reference'])
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
        qualified_state(state, saved, self.release['reference'])
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
        if state['bootc']['status']['booted']['image']['imageDigest'] == self.release['reference'].split('@')[1]:
            require(self.host.read('id', '-u', 'ares').strip() == '1001' and 'wheel' not in self.host.read('id', '-nG', 'ares').split(),
                'Daily account identity/privilege differs')
            self.host.read('pgrep', '-u', 'ares', '-x', 'labwc')
            self.host.read('pgrep', '-u', 'ares', '-x', 'foot')
        else:
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
            preflight_recovery(state, self.processes(), self.load('prepared'), self.release['reference'])
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
            preflight_recovery(state, self.processes(), saved, self.release['reference'], keep=stock_side)
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


def install(payload, host=None):
    payload = pathlib.Path(payload)
    fingerprint = checked_bundle(payload)
    require(sys.stdin.isatty(), 'Install requires the two independently recorded disk serials')
    target = input('Photographed Crucial serial: ').strip()
    protected = input('Windows baseline Micron serial: ').strip()
    require(target and protected and target != protected, 'Missing or equal disk serials')
    host = host if host is not None else Host()
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
        shutil.copytree(payload, stage, symlinks=False, copy_function=shutil.copy2)
        for p in [stage, *stage.rglob('*')]:
            p.chmod(0o700 if p.is_dir() or p.name == 'at' else 0o600)
            if p.is_file():
                with p.open('rb') as stream: os.fsync(stream.fileno())
        for directory in sorted([stage, *[p for p in stage.rglob('*') if p.is_dir()]], key=lambda p: len(p.parts), reverse=True):
            sync_directory(directory)
        sync_directory(HOME)
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
        'keep-stock', 'export', 'layout', 'reboot', 'check', 'logs'}
    command = sys.argv[1] if len(sys.argv) >= 2 and sys.argv[1] in known else 'invalid'
    # Never record arbitrary argv: an accidentally pasted credential is not a
    # command. Layout choices are the only accepted extra arguments.
    action = [command]
    if command == 'layout' and sys.argv[2:] in ([a] for a in ('proof', 'revert', 'finish', 'abandon')):
        action += sys.argv[2:]
    elif command == 'layout' and sys.argv[2:] in (['begin', p] for p in ('de', 'us', 'us-intl')):
        action += sys.argv[2:]
    result = dict(status='stopped', command=action, manifest=None, trace=host.trace)
    try:
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
                       'layout': lambda: tools.layout(*action[1:]), 'reboot': tools.reboot, 'check': tools.check, 'logs': tools.logs}
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
