"""Reproducible fixture identities without changing production ID semantics."""
from contextlib import contextmanager
import hashlib
import random
import uuid
from unittest.mock import patch


@contextmanager
def scripted_ids(scenario):
    # Recovery sorts opaque IDs. Random ordering otherwise moves an injected
    # write to a different operation even when the scenario script is identical.
    generator = random.Random(int.from_bytes(hashlib.sha256(scenario.encode()).digest()))
    with patch.object(uuid, 'uuid4', side_effect=lambda: uuid.UUID(int=generator.getrandbits(128), version=4)):
        yield


def caller_name(flow, point=0, mode='single', cleanup=0, phase='live'):
    # Same width as tempfile's tmp + eight characters: changing record lengths
    # would move SQLite fault boundaries. The tuple encoding is injective.
    kind = {'attachment_export': 1, 'testapp_export': 2, 'export_rollback': 3}[flow]
    if not (0 <= point < 4096 and 0 <= cleanup < 4096 and mode in {'single', 'persistent'} and phase in {'live', 'crash'}):
        raise ValueError('Caller fixture identity exceeds its fixed-width encoding')
    value = (kind << 26) | ((mode == 'persistent') << 25) | ((phase == 'crash') << 24) | (point << 12) | cleanup
    return 'tmp' + format(value, '08x')


def caller_directory(name, cleanups, **kwargs):
    import fcntl
    from pathlib import Path
    import tempfile
    parent = Path(kwargs['dir'])
    # Shared clean cases run in all three workers. Keep their identical path
    # isolated until fixture cleanup; a killed process releases flock itself.
    lock = (parent / ('.owner-state-' + name + '.lock')).open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    cleanups.addCleanup(lock.close)
    target = parent / name
    def create(*args, **options):
        target.mkdir(mode=0o700)
        return str(target)
    # Only this fixture constructor uses the fixed directory. All production
    # temporary files retain the real tempfile implementation.
    with patch.object(tempfile, 'mkdtemp', side_effect=create):
        return tempfile.TemporaryDirectory(**kwargs)
