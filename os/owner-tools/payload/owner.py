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
import signal
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
def typed(*words):
    """The one place that spells an owner command in a message (os/owner-tools/commands.json is compared with it)."""
    return ' '.join(('sudo', '/var/lib/ares/at', *words))


LOGIN_REFUSAL = ('Registry login missing, expired or unreachable: run ' + typed('login') + ', '
                 'then run this command again; nothing was changed')
# What update/previous expect the next start to show (records/outcome-pending.json).
OUTCOME = 'outcome-pending'
# One owner command at a time, bootstrap install included; /run is root-only.
LOCK = pathlib.Path('/run/ares-owner.lock')
# A release step's own time limit, and how long its process group gets after TERM, then after KILL.
SCRIPT_TIMEOUT = 1800
STOP_GRACE = 15
# The stop routine's other bounds: each status read, the pending cleanup and systemd's reload.
READ_TIMEOUT = 30
CLEANUP_TIMEOUT = 300
RELOAD_TIMEOUT = 120
# update.sh unmasks exactly these two (package 27, JUDGMENT-CALL 11); a stopped update masks them again.
UNITS = pathlib.Path('/etc/systemd/system')
FINALIZERS = ('ostree-finalize-staged.service', 'bootc-finalize-staged.service')


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

    def read(self, *command, allowed=(0,), timeout=READ_TIMEOUT):
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

    def start(self, text, name):
        return Step(text, name)

    def script(self, text, name, mutation=True):
        """Run a release step; any unsuccessful end stops its whole session first (package 27, review 1)."""
        step = self.start(text, name)
        try:
            reason = step.wait(SCRIPT_TIMEOUT)
        except KeyboardInterrupt:
            with Deferred():
                try:
                    gone = step.stop()
                except Exception:
                    gone = False
            self.trace.append(step.record(mutation, 'interrupted', gone))
            raise
        if reason == 'done':
            self.trace.append(step.record(mutation))
            return step.stdout
        with Deferred():
            try:
                gone = step.stop()
            except Exception:
                gone = False
        self.trace.append(step.record(mutation, reason, gone))
        if not gone:
            raise Unstoppable('Shared step ' + name + ' could not be stopped; do not reboot; get help')
        if reason == 'timed out':
            raise Stop('Shared step timed out: ' + name + ' (stopped after ' + str(SCRIPT_TIMEOUT // 60)
                       + ' minutes); preserve diagnostics and do not reboot')
        raise Stop('Shared step failed: ' + name + '; preserve diagnostics and do not reboot')


class Step:
    """A release step (bash -seu) in its own session, so the tool can stop all of it.

    subprocess.run's timeout SIGKILLs only the shell: its EXIT trap never runs and
    bootc goes on (package 27, review 1). Here the tool waits in short slices, so a
    deferred signal is noticed, and stop() ends every process of the session.
    """

    def __init__(self, text, name):
        self.name, self.stdout, self.stderr = name, '', ''
        self.process = subprocess.Popen(['/usr/bin/bash', '-seu'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=dict(os.environ, PATH='/usr/sbin:/usr/bin:/sbin:/bin'),
            start_new_session=True)
        self.session = self.process.pid
        self.text = text

    def wait(self, timeout, signals=None):
        """'done' (exit 0 and nothing of the step left), 'failed', 'timed out' or 'interrupted'."""
        deadline = time.monotonic() + timeout
        while True:
            try:
                out, err = self.process.communicate(self.text, timeout=0.2)
                self.text = None
                self.stdout, self.stderr = out or '', err or ''
                break
            except subprocess.TimeoutExpired:
                self.text = None  # communicate() keeps the output; stop() collects it
            if signals is not None and signals.received:
                return 'interrupted'
            if self.process.poll() is not None:
                break  # the shell ended; a survivor may still hold its pipes
            if time.monotonic() >= deadline:
                return 'timed out'
        alive, unknown = self.members()
        if self.process.returncode != 0 or alive or unknown:
            return 'failed'
        return 'done'

    def members(self):
        """(live processes of the step's session or process group, /proc entries the scan could not read).

        /proc/PID/stat is parsed as bytes after the last ')': a process name is 15 raw bytes
        and may cut a multibyte character (package 27, review 3). A process that vanished
        during the scan is gone; zombies cannot act; anything else unreadable is reported,
        so the caller cannot take an incomplete scan for proof. This never raises.
        """
        alive, unknown = [], []
        try:
            names = [name for name in os.listdir('/proc') if name.isdigit()]
        except Exception:
            return alive, ['/proc']
        for name in names:
            try:
                raw = pathlib.Path('/proc', name, 'stat').read_bytes()
            except (FileNotFoundError, ProcessLookupError):
                continue
            except Exception:
                unknown.append(name)
                continue
            if not raw:
                continue
            try:
                fields = raw.rsplit(b')', 1)[1].split()
                state, group, session = fields[0], int(fields[2]), int(fields[3])
            except Exception:
                unknown.append(name)
                continue
            if state != b'Z' and self.session in (group, session):
                alive.append(int(name))
        return alive, unknown

    def stop(self):
        """TERM, then KILL: the step's process group first, then every other member a scan finds.

        True only once a complete scan finds none. self.left keeps what was still there.
        """
        alive, unknown = [], []
        for signum in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(self.session, signum)
            except (ProcessLookupError, PermissionError):
                pass
            alive, unknown = self.members()
            for pid in alive:
                try:
                    os.kill(pid, signum)
                except (ProcessLookupError, PermissionError):
                    pass
            deadline = time.monotonic() + STOP_GRACE
            while True:
                self.process.poll()
                alive, unknown = self.members()
                if (not alive and not unknown) or time.monotonic() >= deadline:
                    break
                time.sleep(0.05)
            if not alive and not unknown:
                break
        self.left = dict(alive=alive, unreadable=unknown)
        gone = not alive and not unknown
        if gone:
            try:
                out, err = self.process.communicate(timeout=2)
                self.stdout, self.stderr = self.stdout + (out or ''), self.stderr + (err or '')
            except (subprocess.SubprocessError, OSError, ValueError):
                pass
        else:
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                try:
                    stream.close()  # a survivor keeps its own ends
                except (OSError, ValueError, AttributeError):
                    pass
        return gone

    def record(self, mutation, stopped=None, gone=None):
        row = dict(script=self.name, returncode=self.process.returncode, stdout=self.stdout,
                   stderr=self.stderr, mutation=mutation)
        if stopped:
            row.update(stopped=stopped, group_gone=gone)
        return row


class Deferred:
    """While an update step or its stop routine runs, SIGINT, SIGTERM and SIGHUP only note
    themselves: Ctrl+C, a closed window or a kill starts the stop routine, never cuts it short."""

    SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)

    def __enter__(self):
        self.received, self.previous = [], {}
        for signum in self.SIGNALS:
            try:
                self.previous[signum] = signal.signal(signum, self.note)
            except ValueError:
                pass  # only the main thread may set handlers; a test thread runs without them
        return self

    def note(self, signum, frame):
        self.received.append(signum)

    def __exit__(self, *unused):
        for signum, handler in self.previous.items():
            signal.signal(signum, handler)
        return False


def say(line):
    """Print without failing: after a closed window, stdout answers EPIPE or EIO."""
    try:
        print(line, flush=True)
    except (OSError, ValueError):
        pass


class Unstoppable(Stop):
    """A step whose process survived TERM and KILL: nothing may be cleaned up behind it."""

def stop_bound():
    """The stop routine's worst case in seconds: TERM and KILL graces, collecting the output,
    four status reads, the pending cleanup, systemd's reload and two mask checks."""
    return 2 * STOP_GRACE + 2 + 4 * READ_TIMEOUT + CLEANUP_TIMEOUT + RELOAD_TIMEOUT + len(FINALIZERS) * READ_TIMEOUT


def staged(state):
    return bool(state['bootc']['status'].get('staged')) or any(d.get('staged') for d in state['rpm']['deployments'])


def finalizer_masks():
    """The staging finalizers still masked by the image's /dev/null link; update.sh removes exactly these."""
    return [unit for unit in FINALIZERS if (UNITS / unit).is_symlink() and os.readlink(UNITS / unit) == '/dev/null']


def restore_masks(host, removed):
    """Mask again the finalizers this update removed, and prove systemd sees them masked. Idempotent."""
    restored = []
    for unit in removed:
        path = UNITS / unit
        if not path.is_symlink():
            require(not path.exists(), 'Unexpected file in place of the ' + unit + ' mask; do not reboot; get help')
            os.symlink('/dev/null', path)
            restored.append(unit)
        require(os.readlink(path) == '/dev/null', 'The ' + unit + ' mask was changed; do not reboot; get help')
    if restored:
        host.mutate('systemctl', 'daemon-reload', timeout=RELOAD_TIMEOUT)
    for unit in removed:
        require(host.read('systemctl', 'is-enabled', unit, allowed=(0, 1)).strip() == 'masked',
                'The mask of ' + unit + ' could not be restored; do not reboot; get help')
    return restored


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


BAZZITE_WAITING = 'A Bazzite update is waiting. Do not restart: the restart deletes {}. Get help.'
NOT_INSTALLED = 'No AresOS is installed yet: this command works after the first switch; nothing changed'


def unmodified(rows):
    return not any(any(d.get(k) for k in MODIFIED) or d.get('unlocked', 'none') != 'none' for d in rows)


def qualified_state(state, saved, release, history=None):
    """The reviewed deployment sets (package 22c, rule 1); every other list STOPs.

    history lists the known AresOS release references, oldest first, ending
    with the target release. Before the first switch (no installed AresOS)
    only the two states version 2 accepts pass, exactly as before: the
    prepared stock list and the first switch staged. They return None.

    With AresOS installed the set is the saved, pinned stock, one or two known
    AresOS releases and, during an update, the staged target in front of a
    running AresOS that is first. The order of that set is free and any member
    may run: the first deployment starts next, and nothing else follows from
    the order (rule 2). bootc's rollback slot and rollbackQueued are derived
    from the order (status.rs; the probe run 43470161858 showed it at every
    stage), so they are only compared with it and decide nothing. Returns the
    rows by role: stock, ares (installed, in list order), staged, booted.
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
        return None
    staged = [d for d in rows if d.get('staged')]
    installed = [d for d in ares if not d.get('staged')]
    if installed and booted is stock and (staged or status.get('staged')):
        # Rule 10: whatever is staged while stock runs, finalizing it keeps only the new, pinned and
        # booted rows. This comes before every other refusal, so each command says it.
        raise Stop(BAZZITE_WAITING.format('both AresOS releases' if len(installed) > 1 else 'the installed AresOS'))
    for d in ares:
        require(not d['pinned'] and d['checksum'] != stock['checksum']
            and image_reference(d) == known[d['container-image-reference-digest']][1],
            'Unexpected AresOS identity or origin')
    require(len({d['container-image-reference-digest'] for d in ares}) == len(ares), 'Duplicate AresOS release deployment')
    if not installed:
        # The first switch staged, as version 2 accepts it.
        require(booted is stock, 'Unexpected staged update')
        require(staged == ares and ares[0]['container-image-reference-digest'] == target and status.get('staged')
            and not status.get('rollbackQueued'), 'Unexpected staged switch')
        retained = [d for d in rows if not d.get('staged')]
        require(retained == saved['state']['rpm']['deployments'], 'Switch changed the retained stock list')
        return None
    require(all(d is stock or any(d is a for a in ares) for d in rows),
        'Unknown deployment beside AresOS and the saved stock; get help')
    require(len(installed) <= 2, 'More than two AresOS releases are installed; get help')
    require(len(staged) <= 1 and bool(staged) == bool(status.get('staged')), 'Staged observations disagree; get help')
    if staged:
        # An update: the bundle's release staged in front of a running AresOS that is first (rule 6).
        new = staged[0]
        require(new['container-image-reference-digest'] == target and slot_identity(status['staged']) == key(new)
            and not status.get('rollbackQueued') and rows[0] is new and rows[1] is booted and booted is not stock,
            'Unexpected staged update')
        return dict(stock=stock, ares=installed, staged=new, booted=booted, known=known)
    other = next(d for d in rows if d is not booted)
    require(status.get('rollback') and slot_identity(status['rollback']) == key(other)
        and bool(status.get('rollbackQueued')) == (rows[0] is not booted),
        'bootc rollback slot differs from the deployment order; get help')
    return dict(stock=stock, ares=installed, staged=None, booted=booted, known=known)


def role(shape, row):
    """One name per installed system, the same in every line (rule 8): by role, never by a release number."""
    if key(row) == key(shape['stock']):
        return 'plain Bazzite'
    if shape['staged'] is not None and key(row) == key(shape['staged']):
        return 'new AresOS'
    if len(shape['ares']) == 1:
        return 'AresOS'
    rank = lambda d: shape['known'][d['container-image-reference-digest']][0]
    return 'newer AresOS' if rank(row) == max(rank(d) for d in shape['ares']) else 'older AresOS'


def name(shape, row):
    return role(shape, row) + ' ' + row['container-image-reference-digest'].split(':')[1][:12]


JOURNAL = 'change1'
WORDS = ('update', 'previous', 'rollback', 'keep-stock')


def journalled(value):
    """The open journal (records/outcome-pending.json) in version 3's form.

    schema; mode ('staging' or 'reorder'); word; status ('intent' or 'recorded');
    boot (the boot that made the change); reference and digest of the target;
    target and running (identities; a staging intent has no target identity
    yet); before and intended (the deployment list before the change and the
    one it leads to; a staging intent derives the latter in completion());
    staged (a staging record's list until the shutdown). A record without
    schema is version 2's and reads as the change version 2 meant (rule 9); an
    unknown schema is refused with nothing changed.
    """
    require(isinstance(value, dict), 'Invalid change record; get help')
    if 'schema' in value:
        require(value['schema'] == JOURNAL, 'The open change record is of unknown tools (schema '
            + str(value['schema']) + '); nothing changed; install the current tools or get help')
        require(value.get('mode') in ('staging', 'reorder') and value.get('word') in WORDS
            and value.get('status') in ('intent', 'recorded'), 'Invalid change record; get help')
        return value
    require(value.get('status') in ('intent', 'recorded') and value.get('kind') in ('update', 'previous'),
        'Invalid update/previous record; get help')
    before, recorded = value['before'], value['status'] == 'recorded'
    shared = dict(schema=None, word=value['kind'], status=value['status'], boot=value['boot'], reference=value['reference'],
        digest=value['reference'].split('@')[1], running=before[0], before=before)
    if value['kind'] == 'update':
        return dict(shared, mode='staging', target=value['booted'] if recorded else None,
            intended=value['expected'] if recorded else None, staged=value['pending'] if recorded else None)
    target = value['booted'] if recorded else value['target']
    return dict(shared, mode='reorder', target=target, intended=[target, *[k for k in before if k != target]])


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
        """Rule 1's deployment list, then rule 5: the open journal resolved from that list alone."""
        self.shape = qualified_state(state, saved if saved is not None else self.load('prepared'),
            self.release['reference'], self.known())
        return self.outcome(state, retry)

    def note(self, line):
        """A line the command prints before its own result (main prints them, also before a STOP)."""
        if getattr(self, 'notes', None) is None:
            self.notes = []
        self.notes.append(line)

    @staticmethod
    def change(value, capital=False):
        text = {'update': 'update to ', 'previous': 'return to ', 'rollback': 'rollback to ',
                'keep-stock': 'change to '}[value['word']] + value['reference']
        return text[0].upper() + text[1:] if capital else text

    def archive(self, state_name, value):
        """Keep a closed journal under the state it was in; the open one is gone afterwards."""
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
        self.save(stamp + '-outcome-' + state_name, value)
        (self.store / (OUTCOME + '.json')).unlink()
        sync_directory(self.store)

    def outcome(self, state, retry=None):
        """Rule 5: where the journalled change stands. The deployment list decides, not the command
        word and not the running row.

        Every change journals an intent before it and turns it into a record after it. Three facts
        are kept apart: the selection is applied (the list is the intended one), a restart is
        waiting (that, in the boot that made the change, with a target that does not run), and the
        target's boot is confirmed (a later boot runs it). Returns None without a journal, and
        after archiving one whose list is as before the change ('not-applied'), or:

        'retry', 'complete'  only for update, in the boot that wrote a staging intent: stage again
                             from the unchanged list, or record the staging it made. Every other
                             command STOPs there and names update;
        'pending'            in place, waiting for the restart (a staging record needs its staged
                             list still there);
        'applied'            in place in the boot that made it, and the target runs already: no
                             restart is waiting, and no start has been seen since the change;
        'done'               in place after a restart, and the target runs: title confirms it;
        'elsewhere'          in place after a restart, and another installed system runs. Nothing
                             blocks; the record stays open for a later start or a new change.
        An intent whose change is in place becomes the record here, with no second change. Any
        other list STOPs with nothing changed.
        """
        if not (self.store / (OUTCOME + '.json')).exists():
            return None
        raw = self.load(OUTCOME)
        value = journalled(raw)
        rows = state['rpm']['deployments']
        keys, running, waiting = [list(key(d)) for d in rows], list(key(agree(state))), staged(state)
        change, same = self.change(value), value['boot'] == boot_id()
        if value['mode'] == 'staging' and same:
            if value['status'] == 'intent':
                if retry == 'update' and keys == value['before'] and not waiting:
                    return 'retry'
                if retry == 'update' and self.completion(value, state) is not None:
                    return 'complete'
                raise Stop('The ' + change + ' was interrupted before its result was recorded; do not reboot; run '
                    + typed('update') + ' to continue it, or get help: EMERGENCY Failed or bad update')
            require(keys == value['staged'] and waiting, 'The ' + change + ' changed before the restart; do not reboot; get help')
            return 'pending'
        if keys == value['before'] and not waiting:
            self.archive('not-applied', dict(raw, found_state=state))
            self.note(self.change(value, True) + ' was not applied: the deployments are as before it, and nothing is waiting')
            return None
        record = value if value['status'] == 'recorded' else self.completion(value, state)
        if record is None or waiting or keys != record['intended']:
            raise Stop('The ' + change + ' did not finish as recorded (' + ('it is still pending' if waiting else
                'the deployments are neither as before it nor as it intended') + '); do not repeat it; '
                'export records and get help: EMERGENCY Failed or bad update')
        if value['status'] == 'intent':
            self.save(OUTCOME, record)
            self.note('The interrupted ' + change + ' had made its change; it is recorded now')
        if running == record['target']:
            return 'applied' if same else 'done'
        return 'pending' if same else 'elsewhere'

    ARCHIVES = {'done': 'confirmed', 'retry': 'retried', 'applied': 'applied-not-restarted', 'elsewhere': 'in-place-not-started'}

    def intend(self, word, state, settled, target=None):
        """Journal the change durably before it is made. An open record is first archived under the
        state it is in. target is the row to start next; None stages the bundle's release, whose
        identity does not exist yet."""
        if settled in self.ARCHIVES:
            self.archive(self.ARCHIVES[settled], self.load(OUTCOME))
        before = [list(key(d)) for d in state['rpm']['deployments']]
        if target is None:
            reference = self.release['reference']
            extra = dict(mode='staging', reference=reference, digest=reference.split('@')[1], target=None, intended=None)
        else:
            identity = list(key(target))
            extra = dict(mode='reorder', reference=image_reference(target), digest=target['container-image-reference-digest'],
                target=identity, intended=[identity, *[k for k in before if k != identity]])
        self.save(OUTCOME, dict(schema=JOURNAL, word=word, status='intent', boot=boot_id(),
            running=list(key(agree(state))), before=before, **extra))

    def completion(self, intent, state):
        """The record for an intent whose change is in place in state, else None.

        The intended list is built from identities, never from positions. A reorder: the target
        first, the others in their old order. Staging: in the boot that staged, the new release in
        front of the unchanged list; after a restart, the new release, the system that ran and the
        stock (ostree's finalize keeps the new, pinned, booted and merge rows).
        """
        rows = state['rpm']['deployments']
        keys, before = [list(key(d)) for d in rows], intent['before']
        if intent['mode'] == 'reorder':
            return dict(intent, schema=JOURNAL, status='recorded') if keys == intent['intended'] and not staged(state) else None
        new = [d for d in rows if list(key(d)) not in before]
        if len(new) != 1 or new[0]['container-image-reference-digest'] != intent['digest'] or new[0]['pinned']:
            return None
        identity, same = list(key(new[0])), intent['boot'] == boot_id()
        pending = [identity, *before]
        intended = [identity, intent['running'], list(self.load('prepared')['stock_identity'])]
        if not (same and keys == pending and new[0].get('staged') or not same and keys == intended and not staged(state)):
            return None
        return dict(intent, schema=JOURNAL, status='recorded', target=identity, staged=pending, intended=intended)

    def finish(self, state):
        """Turn this command's intent into the full record, or STOP unresolved."""
        intent = journalled(self.load(OUTCOME))
        require(intent['status'] == 'intent', 'Missing change journal; get help')
        record = self.completion(intent, state)
        require(record is not None, 'The ' + self.change(intent) + ' did not make the intended change; do not reboot; get help')
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

    def render(self, name, replacements=None):
        text = (self.payload / 'release' / (name + '.sh')).read_text()
        for parameter, value in (replacements or {}).items():
            text = text.replace('@' + parameter + '@', value)
        require(not re.search('@[A-Z_]+@', text), 'Unresolved release script parameter')
        return text

    def script(self, name, replacements=None):
        return self.host.script(self.render(name, replacements), name)

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

    def standing(self, state, shape, settled, bls):
        """Rule 8, with AresOS installed: which system runs, which starts next, and the boot menu's
        rows for the next start, read from the boot entries by identity. Facts only: a cause is
        named where a record proves one."""
        rows, running, new = state['rpm']['deployments'], shape['booted'], shape['staged']
        label = lambda row: name(shape, row)
        if new is not None:
            after = [new, running, shape['stock']]
            return [label(running) + ' runs; ' + label(new) + ' starts next once the update finishes at shutdown',
                'Boot menu after the update finishes at shutdown (expected): ' + '; '.join(
                    '(ostree:%d) %s%s' % (place, label(row), ', starts next' if place == 0 else '') for place, row in enumerate(after))]
        first = rows[0]
        if first is running:
            lines = [label(running) + (' runs and now starts next; no restart is waiting' if settled == 'applied'
                                       else ' runs and starts next')]
        elif settled == 'pending':
            lines = [label(running) + ' runs; ' + label(first) + ' starts next, after the restart']
        else:
            lines = [label(running) + ' runs; ' + label(first) + ' starts next; this start was not the default']
        entries = {tuple(e['identity']): e['title'] for e in bls}
        menu = []
        for row in rows:
            place = re.search(r'\(ostree:[0-9]+\)', entries[key(row)])
            menu.append((place.group(0) if place else '"' + entries[key(row)] + '"') + ' ' + label(row)
                        + (', starts next' if row is first else ''))
        lines.append('Boot menu at the next start: ' + '; '.join(menu))
        if running is shape['stock']:
            # Rule 10: a warning, never a STOP, so that reboot and the way off stock keep working.
            try:
                paused_state(self.host, self.pause)
            except (Stop, OSError, subprocess.SubprocessError) as error:
                lines.append('WARNING: ' + str(error) + '. Bazzite must not update while AresOS is installed: run '
                    + typed('update') + ' to go back to AresOS, then get help')
        return lines

    def title(self):
        saved = self.load('prepared')
        state = observations(self.host)
        settled = self.qualified(state, saved)
        shape = self.shape
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
        notes = self.standing(state, shape, settled, bls) if shape is not None else []
        if settled is not None:
            value = self.load(OUTCOME)
            change = self.change(journalled(value), True)
            if settled == 'done':
                # A later boot runs the target of the change that is in place: keep it, clear it.
                self.archive('confirmed', dict(value, confirmed_state=state))
                notes.append(change + ' confirmed after the restart')
            elif settled == 'pending':
                notes.append(change + ' is not finished until the restart')
            elif settled == 'elsewhere':
                # A fact, never a failure: the target may have started on a day without a command.
                notes.append(change + ' is in place and has not started yet')
            # 'applied': the first line above says it; no start has been seen, so no confirmation.
        result = dict(state=state, bls=bls, title=entry[0], flatpak=runtime_state(self.host))
        self.save('title', result)
        return [*notes, 'stock ' + ' '.join(map(str, saved['stock_identity'])), 'pin yes; transaction idle',
                'staged ' + str(bool(state['bootc']['status'].get('staged'))) + '; rollback queued ' + str(bool(state['bootc']['status'].get('rollbackQueued'))),
                'title ' + entry[0]['title'], 'Previous title INVALID; use this record until the next reorder',
                'Title is provisional until the next boot; refresh after boot' if state['bootc']['status'].get('staged') else 'Title resolves the exact saved stock serial',
                'Flatpak sync state saved; unfinished sync is expected and does not block']

    def records(self):
        self.survey()
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

    def survey(self, retry=None):
        """What every command that may change the next start reads first: the list accepted by
        rule 1 and the journal resolved by rule 5, before any check of its own."""
        saved = self.load('prepared')
        state = observations(self.host)
        settled = self.qualified(state, saved, retry)
        return state, self.shape, settled

    def may_change(self, state, shape, settled):
        """Rule 3's read-only preflight, shared by the reorder, by staging and by a layout trial's begin."""
        require(shape is not None, NOT_INSTALLED)
        require(not (self.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        idle(state, self.processes())
        disk_record(self.host, self.load('disks'))
        if settled == 'pending':
            raise Stop('The ' + self.change(journalled(self.load(OUTCOME))) + ' waits for the restart: restart first ('
                + typed('reboot') + '), then run this command again; nothing changed')
        require(shape['staged'] is None, 'A staged deployment already exists; do not reboot; get help')
        require(unmodified(shape['ares']), 'Modified AresOS deployment; get help')
        validate_bls(state, resolved_bls())

    def may_stage(self, state, shape, settled):
        """Rule 6: staging only from a running AresOS that is first and whole; never from stock."""
        self.may_change(state, shape, settled)
        booted = shape['booted']
        require(booted is not shape['stock'] and state['rpm']['deployments'][0] is booted,
            'Update stages only from a running AresOS that starts next; get help')
        require(not self.repair_note(booted), "This system's keyboard layout is half written: run "
            + typed('layout', 'abandon') + ' first, then update again; nothing changed')

    def start_next(self, word, state, shape, settled, target):
        """Rule 3, the one reorder: target becomes the first deployment by one `ostree admin
        set-default`. It never creates or removes a deployment and never touches a pin, kernel
        arguments or any /etc. Journalled before, recorded after; returns the state afterwards."""
        self.may_change(state, shape, settled)
        rows, reference = state['rpm']['deployments'], target['container-image-reference']
        require(len([d for d in rows if key(d) == key(target)]) == 1 and re.fullmatch('[A-Za-z0-9:/.@_-]+', reference),
            'Target deployment missing or ambiguous; nothing changed; get help')
        self.intend(word, state, settled, target)
        self.script('start-next', {'CHECKSUM': target['checksum'], 'SERIAL': str(target['serial']),
            'DIGEST': target['container-image-reference-digest'], 'REFERENCE': reference})
        after = observations(self.host)
        qualified_state(after, self.load('prepared'), self.release['reference'], self.known())
        # The same identities and flags, the target first, the others in their old order.
        require(after['rpm']['deployments'] == [target, *[d for d in rows if d is not target]],
            'The reorder changed more than the order; do not reboot; get help')
        validate_bls(after, resolved_bls())
        self.finish(after)
        return after

    def select(self, word, state, shape, settled, target, done):
        """Rule 4: make target the next start. Already first: nothing changes and no journal is written."""
        if state['rpm']['deployments'][0] is target:
            label = name(shape, target)
            return [label[0].upper() + label[1:] + ' already starts next; nothing changed',
                    'It runs now' if target is shape['booted'] else 'It does not run yet: it starts at the next restart']
        self.start_next(word, state, shape, settled, target)
        return [done, *self.title()]

    def login(self):
        # Before the first switch the stock rules apply unchanged; on a
        # running AresOS a login only serves an update that needs a download.
        if agree(observations(self.host))['container-image-reference-digest'] == BASE:
            self.before_switch()
        else:
            state, shape, settled = self.survey(retry='update')
            require(settled != 'complete', 'An interrupted update only needs recording: run update')
            require(shape is not None and not any(d['container-image-reference-digest'] == self.release['reference'].split('@')[1]
                for d in shape['ares']), 'The release of these tools is installed already: ' + typed('update') + ' needs no login')
            self.may_stage(state, shape, settled)
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
        """rollback (on a running AresOS) and keep-stock (on running stock): the pinned stock starts next."""
        state, shape, settled = self.survey()
        require(shape is not None, NOT_INSTALLED)
        on_stock = shape['booted'] is shape['stock']
        if keep != on_stock:
            raise Stop(('Plain Bazzite runs here: use ' + typed('keep-stock') + ' (rollback is for a running AresOS)' if on_stock
                else 'An AresOS runs here: use ' + typed('rollback') + ' (keep-stock is for running plain Bazzite)')
                + '; nothing changed')
        if keep:
            # Rule 10: stock may stay the default only while its own updaters are off.
            try:
                paused_state(self.host, self.pause)
            except Stop as error:
                raise Stop(str(error) + '; nothing changed. Bazzite must not update while AresOS is installed: run '
                    + typed('update') + ' to go back to AresOS, then get help') from None
        return self.select('keep-stock' if keep else 'rollback', state, shape, settled, shape['stock'],
            'Saved stock is default' if keep else 'Saved stock rollback queued')

    def update(self):
        """The newest AresOS starts next (rule 4).

        The bundle's release is installed: the reorder, with no network, login or signature check
        (its digest is the history's). It is not installed and an AresOS runs and is first: verify
        and stage it over the running one, which stays as rollback beside the pinned stock (rule
        6). Otherwise (stock runs, or the running AresOS is not first): the newest installed
        AresOS by reorder, and a line that the bundle's release is newer still. Every refusal
        before the change leaves the system unchanged.
        """
        before, shape, settled = self.survey(retry='update')
        require(shape is not None, 'Update starts only from a running AresOS release; get help')
        target, identity = self.release['reference'], self.release['signature']['identity']
        if settled == 'complete':
            # An interrupted run verified and staged this release; only its record is missing.
            require(journalled(self.load(OUTCOME))['digest'] == target.split('@')[1], 'The interrupted update was for another release; get help')
            record = self.finish(before)
            return ['Interrupted update recorded: ' + record['reference'], *self.title()]
        booted, rows = shape['booted'], before['rpm']['deployments']
        rank = lambda d: shape['known'][d['container-image-reference-digest']][0]
        newest = max(shape['ares'], key=rank)
        if newest['container-image-reference-digest'] == target.split('@')[1]:
            return self.select('update', before, shape, settled, newest, 'Newest AresOS starts next ' + target)
        if booted is shape['stock'] or rows[0] is not booted:
            lines = self.select('update', before, shape, settled, newest, 'Newest installed AresOS starts next ' + image_reference(newest))
            return [*lines, 'The release of these tools is newer still and is not installed (' + target + '): '
                    + ('run ' if newest is booted else 'restart, then run ') + typed('update') + ' again']
        self.may_stage(before, shape, settled)
        stored_login(target)
        require(shutil.which('cosign', path='/usr/sbin:/usr/bin:/sbin:/bin'), 'cosign is missing')
        self.script('verify', {'REFERENCE': target, 'IDENTITY': identity})
        # Verification takes time: every safety check again, immediately before staging.
        again, shape, settled = self.survey(retry='update')
        self.may_stage(again, shape, settled)
        require(again['rpm']['deployments'] == rows, 'Deployments changed during verification; nothing was staged; get help')
        booted = shape['booted']
        removed = finalizer_masks()
        self.intend('update', again, settled)
        # A power loss after staging can reach finalize without the result/record below.
        # Name the deployment it will remove before making that possible.
        for other in (d for d in shape['ares'] if d is not booted):
            say('At shutdown, this update removes ' + role(shape, other) + ' ' + image_reference(other))
        text = self.render('update', {'REFERENCE': target, 'CURRENT': image_reference(booted),
                                      'CURRENT_DIGEST': booted['container-image-reference-digest']})
        # From the start of the step to the end of its stop routine, Ctrl+C, a closed
        # window or a kill only notes itself (package 27, reviews 1 and 2).
        with Deferred() as signals:
            step, reason = None, 'failed'
            try:
                step = self.host.start(text, 'update')
                reason = step.wait(SCRIPT_TIMEOUT, signals)
            except (Exception, KeyboardInterrupt) as error:
                reason = 'failed (' + type(error).__name__ + ')'
            if reason != 'done':
                raise Stop(self.stop_update(step, reason, signals, before, booted, removed, target))
            self.host.trace.append(step.record(True))
        after = observations(self.host)
        qualified_state(after, self.load('prepared'), target, self.known())
        status = after['bootc']['status']
        slot = status['staged']
        require(slot and slot['image']['image']['image'] == target and slot['image']['imageDigest'] == target.split('@')[1]
            and not status['rollbackQueued'] and key(agree(after)) == key(booted), 'Staged update identity mismatch; do not reboot')
        retained = [d for d in after['rpm']['deployments'] if not d.get('staged')]
        require(retained == rows, 'Update changed the retained deployments; do not reboot; get help')
        self.finish(after)
        lines = ['Signed exact release staged ' + target, 'Running release stays as rollback ' + image_reference(booted)]
        for other in (d for d in shape['ares'] if d is not booted):
            # ostree's finalize keeps the new, pinned and booted rows: the other AresOS goes, whichever it is.
            label = role(shape, other)
            lines.append(label[0].upper() + label[1:] + ' ' + image_reference(other)
                + ' is removed when the update finishes at shutdown')
            if rank(booted) < rank(other):
                lines.append("The new release starts with this system's settings (Wi-Fi, passwords, layout), not "
                    + name(shape, other) + "'s")
        return [*lines, *self.title(), 'Reboot only after saving this refreshed title; F12 then Linux']

    def stop_update(self, step, reason, signals, before, booted, removed, target):
        """The one stop routine for every unsuccessful end of the update step: a failed
        shell, the time limit, Ctrl+C, a closed window or a kill (signals stay deferred).

        It ends every process of the step and proves none is left; only then removes a
        staged deployment, and only when it is exactly this update's (reconcile_update);
        in every case tries to mask again the finalizers this run removed and checks it,
        as the last line of defence; and claims a clean stop only when every one of those
        checks passed. Each part is protected, so an error in one never skips the next.
        update.sh's EXIT trap covers its ordinary failures; this runs after it and is
        idempotent. Its waits are bounded (the printed limit is their sum).
        """
        if reason == 'interrupted':
            cause = {signal.SIGINT: 'Ctrl+C', signal.SIGTERM: 'a termination request',
                     signal.SIGHUP: 'the window closing'}.get(signals.received[0], 'a signal')
            reason = 'was interrupted (' + cause + ')'
        say('Stopping the update safely; this takes up to ' + str(-(-stop_bound() // 60))
            + ' minutes. Do not close this window or restart.')
        # Each part is protected on its own (review 3): no error in one may skip the next.
        errors, removed_staging, gone = [], False, step is None
        if step is not None:
            try:
                gone = step.stop()
                if not gone:
                    left = getattr(step, 'left', {})
                    errors.append('a process of the update step survived TERM and KILL, so nothing was deleted'
                                  if left.get('alive') or not left.get('unreadable') else
                                  'the end of the update step could not be proved (unreadable /proc entries), '
                                  'so nothing was deleted')
            except Exception as error:
                errors.append('stopping the update step failed (' + type(error).__name__ + ': ' + str(error)
                              + '), so nothing was deleted')
            try:
                self.host.trace.append(step.record(True, reason, gone))
            except Exception as error:
                errors.append('diagnostics: ' + type(error).__name__ + ': ' + str(error))
        if gone:
            try:
                removed_staging = self.reconcile_update(before, booted, target)
            except Exception as error:
                errors.append('deployments: ' + str(error))
        try:
            restore_masks(self.host, removed)
        except Exception as error:
            errors.append('finalizer masks: ' + str(error))
        if errors:
            return ('The update ' + reason + ', and stopping it did not finish: ' + ' | '.join(errors)
                    + '. Do not reboot; export records and get help')
        return ('The update ' + reason + ' and was stopped safely: '
                + ('its staged release was removed, ' if removed_staging else 'nothing was staged, ')
                + ('the staging finalizers are masked again, ' if removed else '')
                + 'and the running release, its rollback and the pinned stock are unchanged. '
                + 'Nothing changes at the next start; run update again later, or get help')

    def reconcile_update(self, before, booted, target):
        """True if this update's staged release was found and removed; STOP on anything else.

        Nothing is deleted unless both status views agree, no deployment client or
        transaction remains, the running, kept and pinned deployments are exactly as
        before, and the only staged deployment is new, unpinned and this update's target.
        """
        state = observations(self.host)
        running = agree(state)
        idle(state, self.processes())
        require(key(running) == key(booted), 'the running release changed; nothing was deleted')
        rows, status = state['rpm']['deployments'], state['bootc']['status']
        require(not status.get('rollbackQueued'), 'a rollback is queued; nothing was deleted')
        kept = [d for d in rows if not d.get('staged')]
        mine = [d for d in rows if d.get('staged')]
        require(kept == before['rpm']['deployments'], 'the kept deployments changed; nothing was deleted')
        if not mine and not status.get('staged'):
            return False
        digest = target.split('@')[1]
        known = [list(key(d)) for d in before['rpm']['deployments']]
        require(len(mine) == 1 and status.get('staged') is not None and not mine[0]['pinned']
                and mine[0]['container-image-reference-digest'] == digest
                and status['staged']['image']['imageDigest'] == digest and list(key(mine[0])) not in known,
                'a staged deployment this update did not make is present; nothing was deleted')
        # cleanup --pending also removes unpinned rows before the running one: only the staged row may be there.
        require(rows[0] is mine[0] and rows[1] is running,
                'a deployment other than the staged update comes before the running release; nothing was deleted')
        self.host.mutate('rpm-ostree', 'cleanup', '--pending', timeout=CLEANUP_TIMEOUT)
        after = observations(self.host)
        agree(after)
        require(not staged(after) and after['rpm']['deployments'] == before['rpm']['deployments'],
                'the staged update could not be removed')
        return True

    def previous(self):
        """The older of two installed AresOS releases starts next, from every system, stock included."""
        state, shape, settled = self.survey()
        require(shape is not None, NOT_INSTALLED)
        require(len(shape['ares']) == 2, 'Only one AresOS is installed: there is no older one to return to; nothing changed')
        older = min(shape['ares'], key=lambda d: shape['known'][d['container-image-reference-digest']][0])
        return self.select('previous', state, shape, settled, older, 'Previous AresOS queued for the next start ' + image_reference(older))

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
        layout_next = ('; from a fresh physical administrator login run ' + typed('layout', 'abandon')
            + ', then ' + typed('check') + ' again') if (self.store / 'layout-pending.json').exists() else '; get help'
        for code, letter in zip((21, 44), ('z', 'y') if profile == 'de' else ('y', 'z')):
            rows = re.findall(r'^keycode\s+' + str(code) + r'\s*=\s*([^\s]+)', dump, re.M)
            require(len(rows) == 1 and rows[0] in (letter, '+' + letter, 'U+' + format(ord(letter), '04x'), '+U+' + format(ord(letter), '04x')),
                'Loaded console keys differ from system layout' + layout_next)
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

    def repair_notes(self):
        """Rule 7: deployments whose persistent layout an abandoned trial may have left half written."""
        if not (self.store / 'layout-repair.json').exists():
            return []
        value = self.load('layout-repair')
        require(isinstance(value, dict) and value.get('schema') == 'layout-repair1' and isinstance(value.get('notes'), list),
            'Unknown layout repair record; nothing changed; get help')
        return value['notes']

    def repair_note(self, row):
        return [n for n in self.repair_notes() if n['deployment_identity'] == list(key(row))]

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
            state, shape, settled = self.survey()
            self.may_change(state, shape, settled)
            booted = shape['booted']
            require(booted is not shape['stock'], "Plain Bazzite keeps the installer's German layout: no layout trial here; "
                'nothing changed; run ' + typed('update') + ' to go back to AresOS first')
            require(state['rpm']['deployments'][0] is booted, 'This AresOS does not start next: make it the next start first ('
                + typed('update') + ' or ' + typed('previous') + '), then begin the trial; nothing changed')
            require(not self.repair_note(booted), "This system's keyboard layout is half written: run "
                + typed('layout', 'abandon') + ' first; nothing changed')
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
                'Then sudo -k; ' + typed('layout', 'proof'),
                'If typing/login fails: Ctrl+Alt+F3; ' + typed('layout', 'revert')]
        if action == 'abandon':
            # On whichever system runs, stock included. A trial belongs to the deployment it began on.
            state, shape, settled = self.survey()
            require(shape is not None, NOT_INSTALLED)
            idle(state, self.processes())
            require(shape['staged'] is None, 'A staged deployment exists: restart first, then abandon the trial; nothing changed')
            disk_record(self.host, self.load('disks'))
            current = self.session()
            booted, notes, lines = shape['booted'], self.repair_notes(), []
            stock_side = booted is shape['stock']
            mine = [n for n in notes if n['deployment_identity'] == list(key(booted))]
            pending = (self.store / 'layout-pending.json').exists()
            require(pending or mine, 'No layout trial and no half-written layout to abandon on this system; nothing changed')
            if pending:
                value = self.load('layout-pending')
                require(current != value['administrator'] and (current['boot'] != value['administrator']['boot']
                    or current['started_us'] > value['began_us']), 'Abandon requires a fresh physical administrator login')
                finished = self.keyboard()
                persistent_before = copy.deepcopy(finished)
                # Each deployment has its own /etc. Another system keeps its own last
                # finished setting; the trial's settings are never written into it.
                # Runtime-only trials have not changed either /etc.
                if list(key(booted)) == value['deployment_identity']:
                    require(value['old'] in profiles.values() and value['new'] in profiles.values(),
                        'Unsupported recorded layout trial; get help')
                    partial = dict(value['old'], **{k:value['new'][k] for k in ('VConsoleKeymap', 'VConsoleKeymapToggle')})
                    require(finished == value['old'] or value.get('finishing') and (value['proof'] or value.get('finish_proof'))
                        and finished in (partial, value['new']), 'Finished system layout changed during the abandoned trial')
                    if finished != value['old']:
                        self.set_keyboard(value['old'])
                        finished = value['old']
                else:
                    # The running deployment may itself have a repair note from an earlier
                    # trial. Its exact recorded partial setting is repaired below; another
                    # deployment's pending trial must not make that repair unreachable.
                    repairable = any(n['old'] in profiles.values() and finished == dict(n['old'],
                        **{k: n['new'][k] for k in ('VConsoleKeymap', 'VConsoleKeymapToggle')}) for n in mine)
                    require(finished in profiles.values() or repairable, 'Unsupported finished system layout; get help')
                    if value.get('finishing'):
                        # Its finish had begun: that deployment's /etc may be half written, and only it
                        # can be repaired from there. The note stays until layout abandon runs on it.
                        notes.append(dict(deployment_identity=value['deployment_identity'], old=value['old'], new=value['new']))
                        self.save('layout-repair', dict(schema='layout-repair1', notes=notes))
                        lines.append('The trial began on another system and its finish had started: run '
                            + typed('layout', 'abandon') + ' there too, to restore its settings')
                self.trial_keyboard(finished)
                self.save('layout-abandoned', dict(trial=value, administrator=current, restored=finished,
                    persistent_settings_unchanged=self.keyboard() == persistent_before, stock_side=stock_side))
                (self.store / 'layout-pending.json').unlink()
                sync_directory(self.store)
                lines[:0] = ['Last finished console layout restored; abandoned trial cleared',
                    'Last finished persistent layout verified; stock settings preserved']
            for note in mine:
                finished = self.keyboard()
                partial = dict(note['old'], **{k: note['new'][k] for k in ('VConsoleKeymap', 'VConsoleKeymapToggle')})
                require(note['old'] in profiles.values() and finished in (note['old'], partial, note['new']),
                    'Finished system layout changed since the abandoned trial; get help')
                if finished != note['old']:
                    self.set_keyboard(note['old'])
                self.trial_keyboard(note['old'])
                notes = [n for n in notes if n is not note]
                self.save('layout-repair', dict(schema='layout-repair1', notes=notes))
                lines.append("This system's half-written layout is restored to the settings before its trial")
            return [*lines, *self.title()]
        value = self.load('layout-pending')
        current = self.session()
        require(current['boot'] == value['administrator']['boot'], 'Trial crossed a reboot without completing the proof')
        if action == 'revert':
            require(current == value['administrator'], 'Revert from the original open administrator session')
            self.trial_keyboard(value['old'])
            # Revert asks for a new proof, but cannot erase why an interrupted finish
            # was allowed to write /etc. Abandon still needs that evidence to repair it.
            if value.get('finishing') and value['proof']:
                value['finish_proof'] = value['proof']
            value.update(reverted=True, proof=None, began_us=int(time.monotonic() * 1000000))
            self.save('layout-pending', value)
            return ['Old console/X11 settings restored; no reboot', 'Log out tty4; prove a fresh password login using the old layout',
                    'Then sudo -k; ' + typed('layout', 'proof')]
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


TOOLS_JOURNAL = 'tools-update-intent'
# Toolset directories: tools (the first install) or tools-<fingerprint> (every update).
TOOLSET = r'tools|tools-[0-9a-f]{64}'
UPDATE_NAMES = ('diagnostics', 'install-intent.json', 'tools', 'records', 'at', '.at.new', '.tools-held',
                TOOLS_JOURNAL + '.json', '.update-tools', 'retired-tools')
PF_KTHREAD = 0x00200000


def switch_entry(name):
    """Point /var/lib/ares/at at a toolset by one atomic rename; it never dangles."""
    entry, fresh = HOME / 'at', HOME / '.at.new'
    require(not entry.exists() or entry.is_symlink(), 'Unexpected installed entry point; get help')
    fresh.unlink(missing_ok=True)
    fresh.symlink_to(name + '/at')
    fresh.replace(entry)
    sync_directory(HOME)


def entry_toolset():
    """The toolset directory name the entry points at, or None when it is no toolset link."""
    entry = HOME / 'at'
    if not entry.is_symlink():
        return None
    match = re.fullmatch('(' + TOOLSET + ')/at', os.readlink(entry))
    return match.group(1) if match else None


def process_absent(process):
    """Nothing of the thread group can act any more; anything less is doubt.

    A kernel thread (PF_KTHREAD), or every thread of the group exited (Z/X,
    or gone from task/) or past its exit: a thread whose own working directory
    reads as ENOENT has no filesystem context left, which the kernel releases
    after its files and its memory map. A live thread beside an exited leader
    keeps its working directory readable, so the group counts.

    A snapshot of task/ can miss a thread started after it was taken, so the
    group is absent only when a second enumeration, taken after every thread
    of the first was classified, lists exactly the same threads: a thread
    that handed its work to a new one and exited in between shows up there. A
    group that keeps changing is doubt.
    """
    try:
        if int((process / 'stat').read_text().rsplit(')', 1)[1].split()[6]) & PF_KTHREAD:
            return True
        previous = None
        for attempt in range(8):
            tasks = sorted(task.name for task in (process / 'task').iterdir())
            for name in tasks:
                task = process / 'task' / name
                try:
                    if (task / 'stat').read_text().rsplit(')', 1)[1].split()[0] in ('Z', 'X'):
                        continue
                    os.readlink(str(task / 'cwd'))
                except FileNotFoundError:
                    continue  # Exited: released, or no filesystem context left.
                return False
            if tasks == previous:
                return True
            previous = tasks
        return False
    except OSError:
        return not process.exists()


def own_descendant(process):
    """Whether the process descends from this one; stat's parent field is readable by anyone."""
    pid, seen = int(process.name), set()
    while pid > 1 and pid not in seen:
        if pid == os.getpid():
            return True
        seen.add(pid)
        try:
            pid = int((pathlib.Path('/proc') / str(pid) / 'stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            return False
    return False


def installed_commands(home):
    """Processes that may run, read or stand in any copy of the installed tools.

    A process counts if its working directory, an open file, or any argument
    (resolved against its working directory, links followed too) lies in any
    toolset directory (tools/, tools-<fingerprint>/), .tools-held/,
    .update-tools/ or retired-tools/, or is the entry link at. That covers
    every interpreter option and relative path. False positives only refuse.

    Unreadable means in use: any error reading a process's working directory,
    arguments or descriptors counts it, unless process_absent confirms that
    nothing of it can act any more, or the one failing descriptor is closed
    (ENOENT, which the kernel gives for no other reason). Root is never
    refused a read, so as root nothing else is exempt. An unprivileged caller
    (a test) is refused by the kernel's ptrace policy for processes outside
    its own tree; it skips those, which cannot be a root-run owner command of
    the tools it is looking for. Everything it started counts on every error.
    """
    bases = {str(home), os.path.realpath(home)}
    names = re.compile('(' + TOOLSET + r'|\.tools-held|\.update-tools|retired-tools)(/.*)?')

    def inside(path):
        path = os.path.normpath(path.removesuffix(' (deleted)'))
        for base in bases:
            if path == os.path.join(base, 'at'):
                return True
            if path.startswith(base + '/') and names.fullmatch(path[len(base) + 1:]):
                return True
        return False

    found = []
    for process in pathlib.Path('/proc').iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        pid = int(process.name)
        try:
            cwd = os.readlink(str(process / 'cwd'))
            raw = (process / 'cmdline').read_bytes()
            paths = [cwd]
            for descriptor in (process / 'fd').iterdir():
                try:
                    paths.append(os.readlink(str(descriptor)))
                except FileNotFoundError:
                    continue  # This descriptor is closed: absent, not doubt.
        except OSError as error:
            if process_absent(process):
                continue
            if os.geteuid() != 0 and not own_descendant(process):
                continue
            found.append(dict(pid=pid, reason='unreadable: ' + str(error)))
            continue
        for argument in (part.decode(errors='replace') for part in raw.split(b'\0') if part):
            paths.append(argument if os.path.isabs(argument) else os.path.join(cwd, argument))
        if any(inside(path) or path.startswith('/') and inside(os.path.realpath(path)) for path in paths):
            found.append(dict(pid=pid, cwd=cwd, argv=[a.decode(errors='replace') for a in raw.split(b'\0')[:4]]))
    return found


def settle_tools():
    """Recovery first: leave exactly one verified toolset in tools/, then return the journal.

    Every entry into the tools (the bootstrap and each installed command) and
    every refusal or exception of a tools update ends here, before any
    fallible check, so this decides from the tools update journal and the
    files beside it alone. Before publication (phases copy and publish) the
    previous toolset is current: a first-install tools/ held aside goes back
    when it is missing, and the entry is pointed at it again. From
    publication on (the journal at retire or later) the new toolset is
    current and the entry points at it. Anything else lies outside the
    journal's model and STOPs with nothing moved. Returns None when no tools
    update is journalled: the first-install route has its own journal.
    """
    journal = HOME / (TOOLS_JOURNAL + '.json')
    if HOME.is_symlink() or not HOME.is_dir() or not (journal.exists() or journal.is_symlink()):
        return None
    owned_directory(HOME)
    info = journal.lstat()
    require(not journal.is_symlink() and stat.S_ISREG(info.st_mode) and info.st_uid == os.geteuid()
        and stat.S_IMODE(info.st_mode) == 0o600, 'Unsafe tools update journal; get help')
    home = object.__new__(Tools); home.store = HOME
    intent = home.load(TOOLS_JOURNAL)
    require(isinstance(intent, dict) and intent.get('schema') == 'tools-update1'
        and intent.get('phase') in ('copy', 'publish', 'retire', 'records', 'complete')
        and all(isinstance(intent.get(k), str) and re.fullmatch('[0-9a-f]{64}', intent[k]) for k in ('previous', 'manifest'))
        and isinstance(intent.get('previous_directory'), str) and re.fullmatch(TOOLSET, intent['previous_directory'])
        and intent['previous_directory'] in ('tools', 'tools-' + intent['previous']),
        'Invalid tools update journal; get help')

    def verified(path):
        # The copy's fingerprint, or why it is no verified toolset.
        try:
            return checked_bundle(path)
        except Stop as error:
            return 'unverified (' + str(error) + ')'

    held = HOME / '.tools-held'
    if intent['phase'] in ('copy', 'publish'):
        current, expected = intent['previous_directory'], intent['previous']
        if not (HOME / current).exists() and not (HOME / current).is_symlink():
            found = verified(held) if current == 'tools' and held.is_dir() and not held.is_symlink() else 'missing'
            require(found == expected, 'No installed tools and no verified held copy: ' + found + '; get help')
            held.replace(HOME / current)
            sync_directory(HOME)
        else:
            found = verified(HOME / current)
            require(found == expected and not held.exists() and not held.is_symlink(),
                'Installed tools match neither side of the tools update: ' + found + '; get help')
    else:
        current, expected = 'tools-' + intent['manifest'], intent['manifest']
        found = verified(HOME / current)
        require(found == expected, 'Published tools differ: ' + found + '; get help')
    if entry_toolset() != current:
        switch_entry(current)
    return intent


def installed_update(fingerprint):
    """Other tools over a completed installation are an update, never a reinstall.

    The first-install route stays unchanged: no installation, an unfinished
    one, or a rerun of the bundle it was installed from.
    """
    if HOME.is_symlink() or not HOME.is_dir():
        return False
    journal = HOME / (TOOLS_JOURNAL + '.json')
    if journal.exists() or journal.is_symlink():
        return True
    intent = HOME / 'install-intent.json'
    if intent.is_symlink() or not intent.is_file():
        return False
    value = json.loads(intent.read_text())
    return isinstance(value, dict) and value.get('phase') == 'complete' and value.get('manifest') != fingerprint


def update_tools(payload, fingerprint, host, intent):
    """Replace the installed tools with a newer reviewed bundle, keeping records.

    Runs from the bootstrap's verified private copy, like install, after
    settle_tools left one verified toolset current (intent is its journal).
    Older or same-version tools, a release history that does not extend the
    installed one, or a deployment state the new tools would refuse all STOP
    before any write. The old tools move, never get deleted, to
    retired-tools/<manifest>.

    No gap at the entry: the new toolset is copied whole to
    tools-<fingerprint>/ beside the old one, and /var/lib/ares/at is switched
    to it by one atomic rename, so the documented entry always reaches a
    complete, verified toolset. The switch blocks a versioned old toolset (its
    main refuses once the entry moved on); a first-install tools/ is moved
    aside after the switch, because the 15f main refuses outside tools/.
    The deciding checks run under that block; the journal's step to retire is
    the publication. Every refusal or exception of this function ends in
    settle_tools (install wraps it), which puts the previous toolset and the
    entry back before publication; a power cut is settled by the next entry.
    The old tools are retired only after publication.
    """
    require(sys.stdin.isatty(), 'Tools update runs only from the physical recovery console')
    device = tools_stick(host, payload, fingerprint)
    owned_directory(HOME)
    for name in ('records', 'diagnostics', 'retired-tools'):
        if (HOME / name).exists() or (HOME / name).is_symlink():
            owned_directory(HOME / name)
    require(all(p.name in UPDATE_NAMES or re.fullmatch(TOOLSET, p.name)
        or p.name.startswith(('.install-intent.', '.' + TOOLS_JOURNAL + '.')) and p.name.endswith('.new')
        for p in HOME.iterdir()), 'Unexpected installation files; preserve them and get help')
    home = object.__new__(Tools); home.store = HOME
    records = object.__new__(Tools); records.store = HOME / 'records'
    installed = home.load('install-intent')
    require(installed.get('schema') == 'install1' and installed.get('phase') == 'complete', 'Installation is unfinished; get help')
    disk_record(host, records.load('disks'))
    new = lineage(payload)
    staged, held, retired = HOME / '.update-tools', HOME / '.tools-held', HOME / 'retired-tools'
    published = HOME / ('tools-' + fingerprint)

    def system_ready():
        # The new tools must accept today's system before they replace the old ones.
        checker = Tools(payload, host, HOME / 'records')
        require(not (checker.store / 'layout-pending.json').exists(), 'Layout trial is unfinished; prove it or revert first')
        if (checker.store / 'prepare-intent.json').exists():
            require(checker.load('prepare-intent').get('phase') == 'complete', 'Prepare is unfinished; get help')
        state = observations(host)
        idle(state, checker.processes())
        checker.qualified(state)

    def exclusive():
        running = installed_commands(HOME)
        require(not running, 'An owner command of the installed tools is running (pid '
            + ', '.join(str(r['pid']) + (' ' + r['reason'] if 'reason' in r else '') for r in running)
            + '); let it finish, then repeat this bootstrap')

    if intent is None or intent['phase'] == 'complete':
        require(not staged.exists() and not staged.is_symlink() and not held.exists() and not held.is_symlink(),
            'Unjournalled partial tools copy or held tools; preserve them and get help')
        old_name = entry_toolset()
        require(old_name is not None, 'Unexpected installed entry point')
        require(all(p.name == old_name for p in HOME.iterdir() if re.fullmatch(TOOLSET, p.name)),
            'Unexpected toolset directories; preserve them and get help')
        current = HOME / old_name
        require(not current.is_symlink() and current.is_dir(), 'Installed tools are missing; get help')
        private_tree(current)
        old = checked_bundle(current)
        require(old_name in ('tools', 'tools-' + old), 'Installed tools differ from their directory name; get help')
        require(intent is None or intent['manifest'] == old, 'Tools update journal differs from the installed tools; get help')
        if old == fingerprint:
            return ['Tools already installed; nothing changed', 'manifest SHA256 ' + fingerprint]
        old_version, old_history = installed_lineage(current, old)
        require(new['tools_version'] > old_version, 'Installed tools are version ' + str(old_version)
            + '; refusing version ' + str(new['tools_version']) + ' (downgrade or same version)')
        require(extends(old_history, new['releases']), 'Bundle release history does not extend the installed one; get help')
        require(not (retired / old).exists() and not (retired / old).is_symlink(), 'Retired tools already exist; get help')
        require(not published.exists() and not published.is_symlink(), 'Unjournalled new tools directory; preserve it and get help')
        exclusive()
        system_ready()
        intent = dict(schema='tools-update1', previous=old, previous_directory=old_name, manifest=fingerprint,
            previous_version=old_version, tools_version=new['tools_version'], tools_volume_uuid=device['volume']['uuid'], phase='copy')
        home.save(TOOLS_JOURNAL, intent)
    else:
        require(intent['manifest'] == fingerprint and intent.get('tools_volume_uuid') == device['volume']['uuid'],
            'Interrupted tools update does not exactly match this bundle/stick; get help')
        if intent['phase'] in ('copy', 'publish'):
            # A resumed run refuses early too, with the old tools current and usable.
            exclusive()
            system_ready()
    def advance(phase):
        intent['phase'] = phase
        home.save(TOOLS_JOURNAL, intent)
    old, old_name = intent['previous'], intent['previous_directory']
    current = HOME / old_name
    if intent['phase'] == 'copy':
        # The old tools stay current and usable while the new ones are copied whole.
        require(checked_bundle(current) == old and not held.exists() and not held.is_symlink()
            and not (retired / old).exists() and entry_toolset() == old_name, 'Installed tools changed during the update')
        if published.exists() or published.is_symlink():
            require(not published.is_symlink() and published.is_dir() and checked_bundle(published) == fingerprint,
                'Unverified new tools directory; preserve it and get help')
        else:
            discard_partial_copy(staged, payload)
            shutil.copytree(payload, staged, symlinks=False, copy_function=shutil.copy2)
            seal_copy(staged)
            require(checked_bundle(staged) == fingerprint, 'Staged tools differ; preserve diagnostics')
            staged.replace(published)
            sync_directory(HOME)
        advance('publish')
    if intent['phase'] == 'publish':
        # settle_tools left the old tools current and the entry on them.
        require(not current.is_symlink() and checked_bundle(current) == old and not held.exists() and not held.is_symlink()
            and entry_toolset() == old_name, 'Unexpected installed tools before publication; get help')
        require(not published.is_symlink() and published.is_dir() and checked_bundle(published) == fingerprint
            and not staged.exists(), 'New tools differ; get help')
        # Block, with the entry never dangling: switch it to the complete new
        # toolset, then move a first-install tools/ aside (the 15f main refuses
        # outside tools/, so that blocks tools/at and tools/owner.py too; a
        # versioned old toolset refuses by itself once the entry moved on).
        switch_entry('tools-' + fingerprint)
        if old_name == 'tools':
            current.replace(held)
            sync_directory(HOME)
        # Then the deciding checks, under the block, immediately before publication.
        exclusive()
        system_ready()
        advance('retire')
    require(checked_bundle(published) == fingerprint and entry_toolset() == 'tools-' + fingerprint, 'Published tools differ; get help')
    if intent['phase'] == 'retire':
        # Only now, with the new tools published, does the old copy retire.
        source = held if old_name == 'tools' else current
        if source.exists() or source.is_symlink():
            require(source.is_dir() and not source.is_symlink() and checked_bundle(source) == old
                and not (retired / old).exists(), 'Old tools differ; get help')
            if not retired.exists():
                retired.mkdir(mode=0o700)
                sync_directory(HOME)
            owned_directory(retired)
            source.replace(retired / old)
            sync_directory(retired)
            sync_directory(HOME)
        require(checked_bundle(retired / old) == old, 'Retired tools differ; get help')
        # The receipt name is journalled, so a resumed update writes it once.
        intent['receipt'] = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ') + '-tools-update'
        advance('records')
    if intent['phase'] == 'records':
        require(re.fullmatch(r'[0-9]{8}T[0-9]{6}\.[0-9]{6}Z-tools-update', intent.get('receipt', '')), 'Invalid tools update journal')
        if not (records.store / (intent['receipt'] + '.json')).exists():
            records.save(intent['receipt'], dict(status='passed', command=['install'], manifest=fingerprint, previous_manifest=old,
                tools_version=intent['tools_version'], previous_version=intent['previous_version'],
                releases=new['releases'], tools_volume_uuid=device['volume']['uuid'], trace=host.trace))
        advance('complete')
    return ['Tools updated from version ' + str(intent['previous_version']) + ' to ' + str(intent['tools_version']),
            'manifest SHA256 ' + fingerprint, 'Previous tools kept in /var/lib/ares/retired-tools (private)',
            'Release target ' + new['releases'][-1]['reference']]


def install(payload, host=None):
    payload = pathlib.Path(payload)
    # Recovery first, before any check (main settled already; direct callers get the same).
    intent = settle_tools()
    fingerprint = checked_bundle(payload)
    if installed_update(fingerprint):
        try:
            return update_tools(payload, fingerprint, host if host is not None else Host(), intent)
        except BaseException:
            # The one restore path: every refusal or exception of the update ends here.
            settle_tools()
            raise
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
    return ['manifest SHA256 ' + fingerprint, 'Use ' + typed('prepare')]


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
    lock = tools = None
    try:
        # Held until this command ends, so two owner commands never interleave.
        lock = owner_lock()
        # Recovery first: an interrupted tools update is settled before any check.
        settle_tools()
        payload = pathlib.Path(__file__).resolve().parent
        fingerprint = checked_bundle(payload)
        result['manifest'] = fingerprint
        require(command != 'invalid', 'Choose a documented owner command')
        require(len(sys.argv) == 2 or command == 'layout' and action == sys.argv[1:] and len(action) in (2, 3),
            'Unexpected arguments; tokens are accepted only at the hidden login prompt')
        if command == 'install':
            lines = install(payload, host)
        else:
            # A first-install tools/ runs only from there (the 15f tools have the same
            # rule); a versioned toolset runs only while the entry points at it.
            require((payload == HOME / 'tools' or payload == HOME / ('tools-' + fingerprint)) and HOME.stat().st_uid == 0
                    and stat.S_IMODE(HOME.stat().st_mode) == 0o700, 'Run the installed root-only tools')
            require(payload == HOME / 'tools' or entry_toolset() == payload.name, 'These tools are not the installed entry '
                    '(the tools update was undone or superseded); run ' + typed(*action) + ' again')
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
            lines = [*(getattr(tools, 'notes', None) or []), *lines]
            result.update(status='passed', result=lines)
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ')
            tools.save(stamp + '-' + command, result)
    except (Stop, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError, AssertionError, EOFError, KeyboardInterrupt) as error:
        for line in getattr(tools, 'notes', None) or []:
            say(line)  # what rule 5 resolved before the STOP
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
        say('STOP: ' + str(error))
        say('Keep the current administrator session open. Preserve diagnostics; do not reboot or retry a different target. See EMERGENCY / get help.')
        sys.exit(1)
