"""Shared bench disk accounting, write admission and interrupted-phase recovery."""
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat
from time import time
from uuid import uuid4

from laptop import Busy, catch_signals, defer_signals, shared_lock
from store_paths import DataTree, existing_parent, mount_id, validate_cache

GB = 1_000_000_000
CAP = 40 * GB
RESERVE = 20 * GB
IDLE = 7 * 24 * 60 * 60
COORDINATION = 1024 * 1024
FILE_OVERHEAD = 64 * 1024
LIMITS = {
    'image': 7 * GB, 'base-disk': 10 * GB, 'build-store': 17 * GB, 'builder-boot': GB,
    'test-disk': 10 * GB, 'export': 7 * GB, 'builder-scratch': 15 * GB, 'podman-tmp': 17 * GB,
    'evidence': 180_000_000,
}
RETAINED = {
    'image': 'newest image and base disk',
    'build-store': 'build cache, expires after seven idle days',
    'builder-boot': 'one builder boot image for reuse',
}
IMAGE = {'image', 'base-disk'}
RUN_ID = re.compile(r'[0-9a-f]{32}')
FILE_NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,127}')


def space(path):
    info = os.statvfs(path)
    return path.stat().st_dev, info.f_bavail * info.f_frsize, info.f_frsize


def write_record(folder, value):
    fd = os.open('active.tmp', os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=folder)
    with os.fdopen(fd, 'w', encoding='utf-8') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.rename('active.tmp', 'active.json', src_dir_fd=folder, dst_dir_fd=folder)
    os.fsync(folder)


def read_record(tree):
    with tree.root() as (_, folder):
        with tree.entry(folder, 'active.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK) as fd:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_size > 16 * 1024:
                raise ValueError('invalid bench phase record')
            record = json.loads(os.read(fd, 16 * 1024 + 1))
    if not isinstance(record, dict) or record.keys() != {'writes'}:
        raise ValueError('invalid bench phase record')
    writes = record['writes']
    if (not isinstance(writes, list) or
            any(not isinstance(kind, str) or kind not in LIMITS or kind == 'evidence' for kind in writes)):
        raise ValueError('invalid bench phase record')
    if len(set(writes)) != len(writes):
        raise ValueError('duplicate writes in bench phase record')
    return writes


class Store:
    def __init__(self, root, worktree, lock, *, disk_space=space, clock=time, cap=CAP, reserve=RESERVE,
                 mount=mount_id):
        self.root = root
        self.worktree = worktree
        self.lock = lock
        self.disk_space = disk_space
        self.clock = clock
        self.cap = cap
        self.reserve = reserve
        self.active = root / 'active.json'
        self.data = DataTree(root, mount)
        self.evidence = DataTree(worktree / '.work/bench', mount)

    def usage(self, omit=()):
        by_device = defaultdict(int)
        for tree in (self.data, self.evidence):
            if tree.exists():
                by_device[self.disk_space(tree.path)[0]] += tree.allocated()
        for path in omit:
            by_device[self.disk_space(existing_parent(path))[0]] -= self.data.allocated(path.relative_to(self.root))
        return by_device

    def admit(self, targets, omit=()):
        usage = self.usage(omit)
        if sum(usage.values()) > self.cap:
            raise Busy('bench store exceeds the 40 GB cap')
        needs, free = {}, {}
        for path, peak in targets:
            device, available, _ = self.disk_space(existing_parent(path))
            needs[device] = needs.get(device, COORDINATION) + peak
            free[device] = min(free.get(device, available), available)
        if sum(usage.values()) + sum(needs.values()) > self.cap:
            raise Busy('disk phase would exceed the 40 GB bench cap')
        if any(free[device] - peak < self.reserve for device, peak in needs.items()):
            raise Busy('disk phase would leave less than 20 GB free on a filesystem')

    @staticmethod
    def _relative(kind):
        return Path('image', kind) if kind in IMAGE else Path(kind)

    def _recover(self, *, success=False):
        try:
            kinds = read_record(self.data)
        except FileNotFoundError:
            return
        if IMAGE.intersection(kinds) and not success:
            self.data.remove(Path('image'))
        for kind in kinds:
            if kind not in IMAGE and (kind not in RETAINED or not success):
                self.data.remove(self._relative(kind))
        self.data.remove(Path('active.json'))

    def _runs(self):
        return [Path(name) for name in self.evidence.names() if RUN_ID.fullmatch(name)]

    def _sweep_evidence(self):
        for run in self._runs():
            for name in self.evidence.names(run):
                if name.startswith('.') and name.endswith('.partial') and FILE_NAME.fullmatch(name[1:-8]):
                    self.evidence.remove(run / name)

    def _prepare(self):
        self._recover()
        self.data.remove(Path('active.tmp'))
        self._sweep_evidence()
        try:
            with self.data.target(Path('build-store')) as (_, _, fd):
                info = os.fstat(fd)
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError('invalid bench build store')
                expired = self.clock() - info.st_mtime >= IDLE
        except FileNotFoundError:
            expired = False
        if expired:
            self.data.remove(Path('build-store'))

    def expire(self):
        with catch_signals(), shared_lock(self.lock), defer_signals():
            self._prepare()
            self._trim_evidence()

    def clean(self):
        with catch_signals(), shared_lock(self.lock), defer_signals():
            self.data.allocated()
            self.evidence.allocated()
            self.evidence.remove()
            self.data.remove()

    def status(self):
        names = self.data.names()
        kept = [(kind, reason) for kind, reason in RETAINED.items() if kind in names]
        if self.evidence.exists():
            kept.append(('evidence', 'five most recent runs in this worktree'))
        return self.usage(), kept, 'active.json' in names

    @contextmanager
    def phase(self, peaks, *, start_check=lambda: None, use_build_store=False):
        """Admit the sum of all coexisting output peaks before creating writable paths."""
        peaks = dict(peaks)
        if not peaks or any(kind not in LIMITS or type(peak) is not int or not 0 < peak <= LIMITS[kind]
                            for kind, peak in peaks.items()):
            raise ValueError('invalid bench phase peaks')
        with catch_signals(), shared_lock(self.lock):
            start_check()
            self._prepare()
            paths = {kind: self.root / self._relative(kind) for kind in peaks}
            if 'evidence' in paths:
                paths['evidence'] = self.evidence.path / uuid4().hex
            replace = {self.root / 'image' for kind in peaks if kind in IMAGE}
            replace.update(paths[kind] for kind in ('build-store', 'builder-boot') if kind in peaks)
            targets = [(self.root, 0), *((path, peaks[kind]) for kind, path in paths.items())]
            self.admit(targets, omit=replace)
            for old in replace:
                self.data.remove(old.relative_to(self.root))
            self.admit(targets)
            validate_cache(self.root.parent)
            with defer_signals():
                with self.data.root(create=True) as (_, folder):
                    write_record(folder, {'writes': [kind for kind in peaks if kind != 'evidence']})
                if 'evidence' in paths:
                    with self.evidence.root(create=True):
                        pass
            phase = Phase(paths, peaks, self)
            success = False
            try:
                for path in paths.values():
                    path.mkdir(mode=0o700, parents=True)
                yield phase
                success = True
            finally:
                with defer_signals():
                    phase.close()
                    self._recover(success=success)
                    self._sweep_evidence()
                    if use_build_store or (success and 'build-store' in peaks):
                        self._touch_build()
                    self._trim_evidence()

    def _touch_build(self):
        try:
            with self.data.target(Path('build-store')) as (parent, name, _):
                now = self.clock()
                os.utime(name, (now, now), dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass

    def _trim_evidence(self):
        runs = []
        for run in self._runs():
            with self.evidence.target(run) as (_, _, fd):
                info = os.fstat(fd)
                if not stat.S_ISDIR(info.st_mode):
                    raise ValueError('invalid bench evidence run')
                runs.append((info.st_mtime_ns, run))
        for _, run in sorted(runs, reverse=True)[5:]:
            self.evidence.remove(run)


@dataclass(frozen=True)
class FixedDisk:
    kind: str
    name: str
    size: int


@dataclass(frozen=True)
class PolledDirectory:
    kind: str
    name: str
    peak: int
    margin: int


@dataclass(frozen=True)
class BoundedCommand:
    argv: tuple
    files: tuple
    file_limit: int


class Phase:
    def __init__(self, paths, peaks, store):
        self._paths = paths
        self._remaining = peaks
        self._store = store
        self._open = True
        self._command = None
        self._polled = {}

    def close(self):
        self._open = False

    def destination(self, kind, name):
        if not self._open:
            raise ValueError('bench phase has ended')
        if not isinstance(name, str) or not FILE_NAME.fullmatch(name):
            raise ValueError('invalid bench output')
        return self._paths[kind] / name

    def _charge(self, kind, amount):
        if self._remaining[kind] < amount:
            raise Busy(f'{kind} write would exceed its phase peak')
        _, free, _ = self._store.disk_space(self._paths[kind])
        if free - amount < self._store.reserve:
            raise Busy(f'{kind} write would leave less than 20 GB free')
        self._remaining[kind] -= amount

    def write(self, kind, name, data, *, offset=0):
        """Write one bounded file; offset permits a sparse prefix without charging its apparent length."""
        if type(data) is not bytes or type(offset) is not int or offset < 0:
            raise ValueError('invalid bench output')
        output = self.destination(kind, name)
        _, _, block = self._store.disk_space(output.parent)
        blocks = ((offset % block + len(data) + block - 1) // block) if data else 0
        self._charge(kind, blocks * block + FILE_OVERHEAD)
        if output.exists() or output.is_symlink():
            raise ValueError('bench output already exists')
        if kind == 'builder-boot' and any(output.parent.iterdir()):
            raise ValueError('a builder boot image is already present')
        partial = output.with_name(f'.{name}.partial')
        with partial.open('xb') as stream:
            stream.seek(offset)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        partial.replace(output)
        return output

    def command(self, argv, *, outputs=()):
        """Supply a closed list of private regular files. The workload cannot create any others."""
        if (not self._open or self._command is not None or not isinstance(argv, (list, tuple)) or
                not argv or any(not isinstance(arg, str) or '\0' in arg for arg in argv) or not argv[0]):
            raise ValueError('invalid bench workload command')
        outputs = tuple(outputs)
        files, limits, charges = [], [], []
        for output in outputs:
            if not isinstance(output, (FixedDisk, PolledDirectory)):
                raise ValueError('unbounded bench workload output')
            path = self.destination(output.kind, output.name)
            _, _, block = self._store.disk_space(path.parent)
            size = output.size if isinstance(output, FixedDisk) else 0
            if isinstance(output, FixedDisk):
                if type(size) is not int or size <= 0:
                    raise ValueError('invalid fixed disk size')
                limit = size
                charge = ((size + block - 1) // block) * block + FILE_OVERHEAD
            else:
                if (type(output.peak) is not int or type(output.margin) is not int or
                        output.peak <= 0 or output.margin < FILE_OVERHEAD + block or output.kind in self._polled):
                    raise ValueError('invalid polled directory peak or margin')
                charge = output.peak + output.margin
                limit = ((charge - FILE_OVERHEAD) // block) * block
                if path.parent.stat().st_blocks * 512 + FILE_OVERHEAD > output.margin:
                    raise ValueError('polled directory margin cannot fit its metadata')
                limit -= block
                if limit < output.peak:
                    raise ValueError('polled directory margin cannot fit its block rounding')
                self._polled[output.kind] = output.peak
            self._charge(output.kind, charge)
            charges.append((path.parent, charge))
            if output.kind == 'builder-boot' and any(path.parent.iterdir()):
                raise ValueError('a builder boot image is already present')
            with path.open('xb') as stream:
                stream.truncate(size)
            files.append(path)
            limits.append(limit)
        file_limit = min(limits, default=0)
        if any(isinstance(output, FixedDisk) and output.size > file_limit for output in outputs):
            raise ValueError('fixed disks must fit the command file ceiling')
        if charges:
            self._store.admit(charges)
        self._command = BoundedCommand(tuple(argv), tuple(files), file_limit)
        return self._command

    def workload(self, result):
        if self._command is None or result is not self._command:
            raise ValueError('unbounded bench workload command')
        return self._command

    def disk_reason(self):
        for kind, peak in self._polled.items():
            path = self._paths[kind]
            tree = self._store.evidence if kind == 'evidence' else self._store.data
            if tree.allocated(path.relative_to(tree.path)) >= peak:
                return f'{kind} reached its phase peak'
        return None
