import os
from pathlib import Path
import re
import tempfile

from .common import FILE_LIMIT, Refused, sha256
from .storage import sync_directory


class Blobs:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(exist_ok=True, mode=0o700)

    def put(self, data):
        if len(data) > FILE_LIMIT:
            raise Refused("invalid_input", "File exceeds 1 MiB; choose a smaller file.")
        key = sha256(data)
        fd, temporary = tempfile.mkstemp(dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fchmod(stream.fileno(), 0o400)
                os.fsync(stream.fileno())
            try:
                os.link(temporary, self.directory / key)
            except FileExistsError:
                self.read(key)
            sync_directory(self.directory)
        finally:
            os.unlink(temporary)
        return key

    def read(self, key):
        if not re.fullmatch(r"[0-9a-f]{64}", key):
            raise Refused("invalid_input", "Not a sha256 blob reference; import the file again.")
        try:
            fd = os.open(self.directory / key, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                data = stream.read(FILE_LIMIT + 1)
        except FileNotFoundError as exc:
            raise Refused("stale_reference", "Blob not present after restore; import again and prepare a new operation.") from exc
        if len(data) > FILE_LIMIT or sha256(data) != key:
            raise Refused("stale_reference", "Immutable blob failed its hash; stop and recover it before preparing again.")
        return data
