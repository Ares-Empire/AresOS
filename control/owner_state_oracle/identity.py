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
