"""Shared bench disk accounting, write admission and interrupted-phase recovery."""
from collections import defaultdict
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
from time import time
from uuid import uuid4

from laptop import Busy, catch_signals, defer_signals, shared_lock

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


def directory(path):
    """Allow absent roots, but never follow a redirected store or evidence path."""
    if path.resolve() != path:
        raise ValueError('bench data path is redirected')
    if path.exists() and not path.is_dir():
        raise ValueError('bench data path is not a directory')
    return path


def existing_parent(path):
    while not path.exists():
        path = path.parent
    return path


def space(path):
    info = os.statvfs(path)
    return path.stat().st_dev, info.f_bavail * info.f_frsize, info.f_frsize


def allocated(root):
    """Sum allocated blocks, including directory entries, without crossing a mount or following links."""
    paths = [root]
    device = root.lstat().st_dev
    seen = set()
    total = 0
    while paths:
        path = paths.pop()
        info = path.lstat()
        if info.st_dev != device:
            raise ValueError('mount inside bench data')
        if info.st_ino in seen:
            continue
        seen.add(info.st_ino)
        total += info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            paths.extend(path.iterdir())
    return total


def remove(path):
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        allocated(path)  # Refuse nested mounts before descending for deletion.
        shutil.rmtree(path)


def write_record(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_record(path):
    if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 16 * 1024:
        raise ValueError('invalid bench record')
    return json.loads(path.read_text(encoding='utf-8'))


def worktree_key(worktree):
    return hashlib.sha256(os.fsencode(worktree)).hexdigest()


class Store:
    def __init__(self, root, worktree, lock, *, disk_space=space, clock=time, cap=CAP, reserve=RESERVE):
        self.root = root
        self.worktree = worktree
        self.lock = lock
        self.disk_space = disk_space
        self.clock = clock
        self.cap = cap
        self.reserve = reserve
        self.active = root / 'active.json'

    def worktrees(self):
        roots = {}
        for record in directory(self.root).glob('worktree-*.json'):
            worktree = Path(read_record(record))
            key = worktree_key(worktree)
            if not worktree.is_absolute() or record.name != f'worktree-{key}.json':
                raise ValueError('invalid bench evidence registration')
            evidence = directory(worktree / '.work/bench')
            roots[key] = evidence
        return roots

    def evidence(self):
        roots = set(self.worktrees().values())
        roots.add(directory(self.worktree / '.work/bench'))
        return sorted(root for root in roots if root.exists())

    def usage(self, omit=()):
        by_device = defaultdict(int)
        for root in (directory(self.root), *self.evidence()):
            if root.exists():
                dev = self.disk_space(root)[0]
                by_device[dev] += allocated(root)
        for path in omit:
            if path.exists():
                by_device[self.disk_space(path)[0]] -= allocated(path)
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

    def _path(self, kind):
        return self.root / 'image' / kind if kind in IMAGE else self.root / kind

    def _recover(self, *, success=False, keep_evidence=False):
        if not self.active.exists() and not self.active.is_symlink():
            return
        record = read_record(self.active)
        kinds = record['writes']
        if not isinstance(kinds, list) or any(kind not in LIMITS for kind in kinds):
            raise ValueError('invalid bench phase record')
        if IMAGE.intersection(kinds) and not success:
            remove(self.root / 'image')
        for kind in kinds:
            if kind == 'evidence':
                run = record['run']
                evidence = self.worktrees()[record['worktree']]
                if not RUN_ID.fullmatch(run):
                    raise ValueError('invalid bench evidence run')
                run_path = directory(evidence / run)
                if keep_evidence and run_path.exists():
                    for partial in run_path.glob('.*.partial'):
                        remove(partial)
                else:
                    remove(run_path)
            elif kind not in IMAGE and (kind not in RETAINED or not success):
                remove(self._path(kind))
        self.active.unlink()

    def _prepare(self):
        self._recover()
        if self.root.exists():
            for temporary in self.root.glob('*.tmp'):
                temporary.unlink()
        build = directory(self._path('build-store'))
        if build.exists() and self.clock() - build.stat().st_mtime >= IDLE:
            remove(build)

    def expire(self):
        with catch_signals(), shared_lock(self.lock):
            directory(self.root)
            with defer_signals():
                self._prepare()

    def clean(self):
        with catch_signals(), shared_lock(self.lock):
            directory(self.root)
            with defer_signals():
                for evidence in self.evidence():
                    remove(evidence)
                remove(self.root)

    def status(self):
        kept = [(kind, rationale) for kind, rationale in RETAINED.items() if (self.root / kind).exists()]
        evidence = self.evidence()
        for root in evidence:
            if root.exists():
                kept.append(('evidence', 'five most recent runs across worktrees'))
                break
        return self.usage(), kept, self.active.is_file()

    @contextmanager
    def phase(self, peaks, *, start_check=lambda: None, use_build_store=False):
        """Admit the sum of all coexisting output peaks before creating writable paths."""
        peaks = dict(peaks)
        if not peaks or any(kind not in LIMITS or type(peak) is not int or not 0 < peak <= LIMITS[kind]
                            for kind, peak in peaks.items()):
            raise ValueError('invalid bench phase peaks')
        with catch_signals(), shared_lock(self.lock):
            start_check()
            directory(self.root)
            self._prepare()
            key = worktree_key(self.worktree)
            run = uuid4().hex
            paths = {kind: self._path(kind) for kind in peaks}
            if 'evidence' in paths:
                paths['evidence'] = directory(self.worktree / '.work/bench') / run
            replace = {self.root / 'image' for kind in peaks if kind in IMAGE}
            replace.update(paths[kind] for kind in ('build-store', 'builder-boot') if kind in peaks)
            targets = [(self.root, 0), *((path, peaks[kind]) for kind, path in paths.items())]
            # Check the cap after replacement, and require free space without speculative reclaim credit.
            self.admit(targets, omit=replace)
            for old in replace:
                remove(old)
            self.admit(targets)
            self.root.mkdir(parents=True, exist_ok=True)
            if 'evidence' in paths:
                registry = self.root / f'worktree-{key}.json'
                if not registry.exists():
                    write_record(registry, str(self.worktree))
            write_record(self.active, {'writes': list(peaks), 'worktree': key, 'run': run})
            phase = Phase(paths, peaks, self.disk_space, self.reserve)
            success = False
            try:
                for path in paths.values():
                    directory(path).mkdir(parents=True)
                yield phase
                success = True
            finally:
                with defer_signals():
                    phase.close()
                    self._recover(success=success, keep_evidence=True)
                    if use_build_store or (success and 'build-store' in peaks):
                        build = directory(self._path('build-store'))
                        if build.is_dir():
                            now = self.clock()
                            os.utime(build, (now, now))
                    self._trim_evidence()

    def _trim_evidence(self):
        runs = [directory(run) for root in self.evidence() for run in root.iterdir()
                if RUN_ID.fullmatch(run.name)]
        runs.sort(key=lambda run: run.stat().st_mtime_ns, reverse=True)
        for run in runs[5:]:
            remove(run)


class Phase:
    def __init__(self, paths, peaks, disk_space, reserve):
        self._paths = paths
        self._remaining = peaks
        self._disk_space = disk_space
        self._reserve = reserve
        self._open = True

    def close(self):
        self._open = False

    def write(self, kind, name, data, *, offset=0):
        """Write one bounded file; offset permits a sparse prefix without charging its apparent length."""
        if not self._open:
            raise ValueError('bench phase has ended')
        if not FILE_NAME.fullmatch(name) or type(data) is not bytes or type(offset) is not int or offset < 0:
            raise ValueError('invalid bench output')
        folder = self._paths[kind]
        _, free, block = self._disk_space(folder)
        blocks = ((offset % block + len(data) + block - 1) // block) if data else 0
        charge = blocks * block + FILE_OVERHEAD
        if self._remaining[kind] < charge:
            raise Busy(f'{kind} write would exceed its phase peak')
        if free - charge < self._reserve:
            raise Busy(f'{kind} write would leave less than 20 GB free')
        output = folder / name
        if output.exists() or output.is_symlink():
            raise ValueError('bench output already exists')
        if kind == 'builder-boot' and any(folder.iterdir()):
            raise ValueError('a builder boot image is already present')
        partial = folder / f'.{name}.partial'
        self._remaining[kind] -= charge
        with partial.open('xb') as stream:
            stream.seek(offset)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        partial.replace(output)
        return output
