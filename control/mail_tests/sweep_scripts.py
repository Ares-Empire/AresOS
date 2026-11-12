"""Replay inputs and an independent guard against ambient sweep values."""
from contextlib import contextmanager, ExitStack
import datetime
import email.utils
import os
import random
import secrets
import tempfile
import time
import uuid
from unittest.mock import patch

from aresos_control.mail import adapter
from aresos_control import files
from owner_state_oracle.identity import scripted_ids


class AmbientRead(BaseException):
    # Production catches Exception to return transport errors. A fixture leak
    # must escape those handlers, including paths that otherwise recover.
    pass


@contextmanager
def reject_ambient_sources():
    def reject(source):
        def fail(*args, **kwargs):
            raise AmbientRead(source)
        return fail

    with ExitStack() as stack:
        for name in ('time', 'time_ns'):
            stack.enter_context(patch.object(time, name, reject('time.' + name)))
        for name in ('localtime', 'gmtime', 'strftime'):
            original = getattr(time, name)
            def explicit(*args, _name=name, _original=original, **kwargs):
                index = 1 if _name == 'strftime' else 0
                if len(args) <= index or args[index] is None:
                    raise AmbientRead('time.' + _name)
                return _original(*args, **kwargs)
            stack.enter_context(patch.object(time, name, explicit))

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


class SweepScripts:
    COMPONENTS = ('clock', 'calendar', 'nanoseconds', 'ids', 'mime', 'paths')

    def __init__(self, scenario, flow):
        self.scenario, self.flow = scenario, flow
        self.reads = set()

    def consumed(self, component, function):
        def read(*args, **kwargs):
            self.reads.add(component)
            return function(*args, **kwargs)
        return read

    def clock(self):
        return patch.object(time, 'time', self.consumed('clock', lambda: self.scenario.fixture_time))

    def nanoseconds(self):
        nanos = int(self.scenario.fixture_time * 1_000_000_000)
        def next_nanos():
            nonlocal nanos
            # Newest-first warning pages must preserve occurrence order, even
            # after a nested expiry clock jumps forward and is restored.
            nanos = max(nanos + 1, int(time.time() * 1_000_000_000))
            return nanos
        return patch.object(time, 'time_ns', self.consumed('nanoseconds', next_nanos))

    @contextmanager
    def ids(self):
        with scripted_ids('inherited-' + self.flow):
            with patch.object(uuid, 'uuid4', self.consumed('ids', uuid.uuid4)):
                yield

    def mime(self):
        generator = random.Random('inherited-mime-' + self.flow)
        return patch.object(random, 'randrange', self.consumed('mime', generator.randrange))

    def paths(self):
        # Separate worker processes share the local test-work directories.
        # PID salts isolate them without changing the eight-character width;
        # every clean/fault replay in a worker restarts the same name sequence.
        generator = random.Random(f'inherited-paths-{self.flow}-{os.getpid()}')
        def names():
            while True:
                yield ''.join(generator.choices(tempfile._RandomNameSequence.characters, k=8))
        sequence = names()
        return patch.object(tempfile, '_get_candidate_names', self.consumed('paths', lambda: sequence))

    @contextmanager
    def calendar(self):
        formatdate = email.utils.formatdate
        def date(timeval=None, *args, **kwargs):
            if timeval is None:
                self.reads.add('calendar')
                timeval = time.time()
            return formatdate(timeval, *args, **kwargs)
        with patch.object(email.utils, 'formatdate', date), patch.object(adapter, 'formatdate', date):
            yield
