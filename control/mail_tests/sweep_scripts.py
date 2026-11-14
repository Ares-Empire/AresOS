"""Replay inputs and an independent guard against ambient sweep values."""
from contextlib import contextmanager, ExitStack
from contextvars import ContextVar
import datetime
import email.utils
import os
from pathlib import Path
import random
import secrets
import tempfile
import time
import uuid
from unittest.mock import patch

from aresos_control.mail import adapter
from aresos_control import files
from aresos_control.blobs import Blobs
from owner_state_oracle.identity import scripted_ids


LEAKS = ContextVar('sweep_ambient_reads', default=())


class AmbientRead(BaseException):
    def __init__(self, source):
        super().__init__(source)
        for leaks in LEAKS.get():
            leaks.append(source)


TIME_FIELDS = {'st_atime', 'st_mtime', 'st_ctime', 'st_birthtime',
               'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns', 'st_birthtime_ns'}


class TimestampStat:
    """Keep real inode/size/mode data; timestamp access needs a separate script."""
    def __init__(self, value, timestamp):
        self.value, self.timestamp = value, timestamp

    def __getattr__(self, name):
        return self.timestamp(name) if name in TIME_FIELDS else getattr(self.value, name)

    def __getitem__(self, index):
        fields = ('st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid', 'st_gid',
                  'st_size', 'st_atime', 'st_mtime', 'st_ctime')
        if isinstance(index, slice):
            return tuple(self[i] for i in range(10)[index])
        return getattr(self, fields[index])

    def __len__(self):
        return 10


def raw_stat(value):
    while isinstance(value, TimestampStat):
        value = value.value
    return value


class Chronology:
    STEP = 10_000  # Above float rounding at this epoch, well below any deadline.

    def __init__(self, seconds):
        self.nanos = int(seconds * 1_000_000_000)

    def read(self):
        self.nanos += self.STEP
        return self.nanos

    def advance(self, seconds):
        if seconds < 0:
            raise ValueError('A scenario cannot move backwards')
        self.nanos += int(seconds * 1_000_000_000)

    @contextmanager
    def jump(self, *, seconds=0, until=0):
        self.advance(seconds)
        self.nanos = max(self.nanos, int(until * 1_000_000_000))
        # Leaving a temporary override restores the advancing source, never an
        # earlier epoch. Later warnings must sort after warnings in this scope.
        yield


@contextmanager
def reject_ambient_sources():
    leaks = []
    token = LEAKS.set((*LEAKS.get(), leaks))
    try:
        with _reject_ambient_sources():
            yield
    finally:
        LEAKS.reset(token)
        # A production finally may preserve a prior storage error over even a
        # BaseException. Remember the read independently and reject on exit.
        if leaks:
            raise AmbientRead(leaks[0])


@contextmanager
def _reject_ambient_sources():
    def reject(source):
        def fail(*args, **kwargs):
            raise AmbientRead(source)
        return fail

    with ExitStack() as stack:
        for name in ('stat', 'lstat', 'fstat'):
            original = getattr(os, name)
            def guarded_stat(*args, _original=original, **kwargs):
                return TimestampStat(_original(*args, **kwargs), reject('file timestamp'))
            stack.enter_context(patch.object(os, name, guarded_stat))
        for name in ('time', 'time_ns'):
            stack.enter_context(patch.object(time, name, reject('time.' + name)))
        for name in ('localtime', 'gmtime', 'strftime', 'ctime', 'asctime'):
            original = getattr(time, name)
            def explicit(*args, _name=name, _original=original, **kwargs):
                index = 1 if _name == 'strftime' else 0
                if len(args) <= index or args[index] is None:
                    raise AmbientRead('time.' + _name)
                return _original(*args, **kwargs)
            stack.enter_context(patch.object(time, name, explicit))

        for name in ('clock_gettime', 'clock_gettime_ns'):
            if not hasattr(time, name):
                continue
            original = getattr(time, name)
            def clock_gettime(clock_id, _original=original):
                if clock_id == time.CLOCK_REALTIME:
                    raise AmbientRead('time.CLOCK_REALTIME')
                return _original(clock_id)
            stack.enter_context(patch.object(time, name, clock_gettime))

        class DateTime(datetime.datetime):
            now = classmethod(reject('datetime.now'))
            utcnow = classmethod(reject('datetime.utcnow'))
            today = classmethod(reject('datetime.today'))

        class Date(datetime.date):
            today = classmethod(reject('date.today'))

        stack.enter_context(patch.object(datetime, 'datetime', DateTime))
        stack.enter_context(patch.object(files, 'datetime', DateTime))
        stack.enter_context(patch.object(datetime, 'date', Date))
        stack.enter_context(patch.object(adapter, 'date', Date))
        for name in ('uuid1', 'uuid4', 'uuid6', 'uuid7', 'uuid8'):
            if not hasattr(uuid, name):
                continue
            stack.enter_context(patch.object(uuid, name, reject('uuid.' + name)))
        # Seeded private Random instances are scripts; the module singleton,
        # unseeded instances and SystemRandom are ambient entropy sources.
        for name in random.__all__:
            if name not in ('Random', 'SystemRandom') and callable(getattr(random, name)):
                stack.enter_context(patch.object(random, name, reject('random.' + name)))
        seed = random.Random.seed
        def explicit_seed(instance, a=None, version=2):
            if a is None:
                raise AmbientRead('random.Random.seed')
            return seed(instance, a, version)
        stack.enter_context(patch.object(random.Random, 'seed', explicit_seed))
        for name in ('random', 'getrandbits', 'randbytes'):
            stack.enter_context(patch.object(random.SystemRandom, name, reject('SystemRandom.' + name)))
        stack.enter_context(patch.object(random, '_urandom', reject('random._urandom')))
        for name in ('choice', 'randbelow', 'randbits', 'token_bytes', 'token_hex', 'token_urlsafe'):
            stack.enter_context(patch.object(secrets, name, reject('secrets.' + name)))
        stack.enter_context(patch.object(os, 'urandom', reject('os.urandom')))
        stack.enter_context(patch.object(tempfile, '_get_candidate_names', reject('tempfile names')))
        stack.enter_context(patch.object(email.utils, 'make_msgid', reject('email.make_msgid')))
        formatdate = email.utils.formatdate
        def explicit_date(timeval=None, *args, **kwargs):
            if timeval is None:
                raise AmbientRead('email.formatdate')
            return formatdate(timeval, *args, **kwargs)
        stack.enter_context(patch.object(email.utils, 'formatdate', explicit_date))
        stack.enter_context(patch.object(adapter, 'formatdate', explicit_date))
        yield


# Flows whose journal stamp changes on every stat, so Chrome's committed
# projection misses its cache and re-reads the journal at each call site. One
# small flow keeps that cache-miss path under faults; every other flow stamps
# the journal like production's cache key and re-reads it only after it changed.
PER_STAT_JOURNAL_FLOWS = frozenset({'cancel'})


class SweepScripts:
    SOURCES = {'clock': r'^time\.time$', 'nanoseconds': r'^time\.time_ns$',
               'localtime': r'^time\.localtime$', 'gmtime': r'^time\.gmtime$',
               'strftime': r'^time\.strftime$', 'formatdate': r'^email\.formatdate$',
               'datetime': r'^datetime\.', 'date': r'^date\.today$',
               'timestamps': r'^file timestamp', 'ids': r'^uuid\.uuid4$',
               'mime': r'^random\.randrange$', 'paths': r'^tempfile names$'}
    COMPONENTS = tuple(SOURCES)

    def __init__(self, scenario, flow):
        self.scenario, self.flow = scenario, flow
        self.chronology = Chronology(scenario.fixture_time)
        self.reads, self.phase_reads = set(), {}
        self.phase = 'setup'
        self.contexts, self.stamps = {}, {}
        self.journal_per_stat = flow in PER_STAT_JOURNAL_FLOWS
        self.journal_stamp = None

    @contextmanager
    def install(self):
        with ExitStack() as stack:
            for component in self.COMPONENTS:
                context = self.contexts[component] = ExitStack()
                stack.callback(context.close)
                context.enter_context(getattr(self, component)())
            yield

    @contextmanager
    def omit(self, component):
        self.contexts[component].close()
        try:
            yield
        finally:
            self.contexts[component].enter_context(getattr(self, component)())

    def consumed(self, component, function):
        def read(*args, **kwargs):
            self.reads.add(component)
            self.phase_reads.setdefault(self.phase, set()).add(component)
            return function(*args, **kwargs)
        return read

    def clock(self):
        return patch.object(time, 'time', self.consumed('clock', lambda: self.chronology.read() / 1_000_000_000))

    def nanoseconds(self):
        return patch.object(time, 'time_ns', self.consumed('nanoseconds', self.chronology.read))

    @contextmanager
    def ids(self):
        with scripted_ids('inherited-' + self.flow):
            with patch.object(uuid, 'uuid4', self.consumed('ids', uuid.uuid4)):
                yield

    def mime(self):
        generator = random.Random('inherited-mime-' + self.flow)
        return patch.object(random, 'randrange', self.consumed('mime', generator.randrange))

    def paths(self):
        # Every replay in a worker restarts the same eight-character names.
        generator = random.Random(f'inherited-paths-{self.flow}-{os.getpid()}')
        def names():
            while True:
                yield ''.join(generator.choices(tempfile._RandomNameSequence.characters, k=8))
        sequence = names()
        return patch.object(tempfile, '_get_candidate_names', self.consumed('paths', lambda: sequence))

    def localtime(self):
        explicit = time.gmtime
        def localtime(seconds=None):
            if seconds is None:
                seconds = self.consumed('localtime', self.chronology.read)() / 1_000_000_000
            return explicit(seconds)
        return patch.object(time, 'localtime', localtime)

    def gmtime(self):
        explicit = time.gmtime
        def gmtime(seconds=None):
            if seconds is None:
                seconds = self.consumed('gmtime', self.chronology.read)() / 1_000_000_000
            return explicit(seconds)
        return patch.object(time, 'gmtime', gmtime)

    def strftime(self):
        explicit, gmtime = time.strftime, time.gmtime
        def strftime(format, stamp=None):
            if stamp is None:
                stamp = gmtime(self.consumed('strftime', self.chronology.read)() / 1_000_000_000)
            return explicit(format, stamp)
        return patch.object(time, 'strftime', strftime)

    @contextmanager
    def formatdate(self):
        explicit = email.utils.formatdate
        def date(timeval=None, *args, **kwargs):
            if timeval is None:
                timeval = self.consumed('formatdate', self.chronology.read)() / 1_000_000_000
            return explicit(timeval, *args, **kwargs)
        with patch.object(email.utils, 'formatdate', date), patch.object(adapter, 'formatdate', date):
            yield

    @contextmanager
    def datetime(self):
        script, base = self, datetime.datetime
        class DateTime(base):
            @classmethod
            def now(cls, tz=None):
                stamp = script.consumed('datetime', script.chronology.read)() / 1_000_000_000
                value = cls.fromtimestamp(stamp, tz or datetime.timezone.utc)
                return value if tz else value.replace(tzinfo=None)

            @classmethod
            def utcnow(cls):
                return cls.now()

            @classmethod
            def today(cls):
                return cls.now()
        with patch.object(datetime, 'datetime', DateTime), patch.object(files, 'datetime', DateTime):
            yield

    @contextmanager
    def date(self):
        script, base = self, datetime.date
        class Date(base):
            @classmethod
            def today(cls):
                stamp = script.consumed('date', script.chronology.read)() / 1_000_000_000
                return cls(*time.gmtime(stamp)[:3])
        with patch.object(datetime, 'date', Date), patch.object(adapter, 'date', Date):
            yield

    @contextmanager
    def timestamps(self):
        stat, put = os.stat, Blobs.put_stream
        def fingerprint(value):
            # Recovery removes surviving upload hardlinks, changing ctime
            # without changing the immutable blob's bytes or modification age.
            return (value.st_dev, value.st_ino, value.st_mtime_ns)

        def timestamp(value, name, path):
            fixture = getattr(self.scenario, 'fixture', None)
            root = getattr(fixture, 'root', None)
            engine = getattr(fixture, 'engine', None)
            if root is not None and engine is not None and path is not None and path in {
                    root / 'state/control.sqlite', root / 'state/control.sqlite-journal',
                    engine.store.evidence_dir / 'operations.jsonl'}:
                # The independent Driver uses these only as a decode-cache key.
                # A fresh logical revision forces a real decode; no kernel time
                # enters its record, and no same-size commit can be hidden.
                stamp = self.consumed('timestamps', self.chronology.read)()
                if path == engine.store.evidence_dir / 'operations.jsonl' and not self.journal_per_stat:
                    # Chrome's projection keys its cache on (inode, size, mtime).
                    # The journal only grows or truncates back after a failed
                    # append, so its stamp changes exactly when production's
                    # mtime would: when inode or size differ from the last stat.
                    # The Driver still decodes every time (the database stamps
                    # above stay fresh per stat).
                    raw = raw_stat(value)
                    identity = (raw.st_dev, raw.st_ino, raw.st_size)
                    if self.journal_stamp is None or self.journal_stamp[0] != identity:
                        self.journal_stamp = (identity, stamp)
                    stamp = self.journal_stamp[1]
                return stamp if name.endswith('_ns') else stamp / 1_000_000_000
            value = raw_stat(value)
            stamp = self.stamps.get(fingerprint(value))
            if stamp is None:
                raise AmbientRead('file timestamp: unregistered or changed inode')
            self.consumed('timestamps', self.chronology.read)()
            return stamp if name.endswith('_ns') else stamp / 1_000_000_000

        def published(blobs, chunks, size, key, origin='internal'):
            stamp = self.chronology.read()
            try:
                return put(blobs, chunks, size, key, origin)
            finally:
                # Also register any real surviving publication after a fault.
                # No unlink, sync, write or fault site is replaced or bypassed.
                for name in (key, '.origins-' + key):
                    try:
                        value = raw_stat(stat(blobs.directory / name))
                    except FileNotFoundError:
                        continue
                    self.stamps.setdefault(fingerprint(value), stamp)

        with ExitStack() as stack:
            stack.enter_context(patch.object(Blobs, 'put_stream', published))
            for name in ('stat', 'lstat', 'fstat'):
                original = getattr(os, name)
                def scripted_stat(*args, _original=original, **kwargs):
                    value = _original(*args, **kwargs)
                    path = Path(args[0]) if args and not isinstance(args[0], int) else None
                    return TimestampStat(value, lambda field: timestamp(value, field, path))
                stack.enter_context(patch.object(os, name, scripted_stat))
            yield
