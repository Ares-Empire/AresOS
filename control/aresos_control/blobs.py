import hashlib
import os
from pathlib import Path
import re
import tempfile

from .common import FILE_LIMIT, Refused, sha256
from .storage import sync_directory


class Blobs:
    def __init__(self, directory, limit=FILE_LIMIT):
        self.directory, self.limit = Path(directory), limit
        if type(limit) is not int or limit < 1:
            raise ValueError("File limit must be a positive byte count")
        self.directory.mkdir(exist_ok=True, mode=0o700)
        # An interrupted upload is never a blob; remove its private staging inode.
        for temporary in self.directory.glob(".upload-*"):
            temporary.unlink()

    def put(self, data):
        return self.put_stream([data], len(data), sha256(data))

    def put_stream(self, chunks, size, key):
        if type(size) is not int or not 0 <= size <= self.limit:
            raise Refused("file_refused", "File exceeds the configured per-file limit; choose a smaller file.")
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise Refused("invalid_input", "Not a sha256 blob reference; import the file again.")
        fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=self.directory)
        try:
            count, hashed = 0, hashlib.sha256()
            with os.fdopen(fd, "wb") as stream:
                for data in chunks:
                    count += len(data)
                    if count > size or count > self.limit:
                        raise Refused("file_refused", "Upload exceeds its declared size or configured limit; import refused.")
                    stream.write(data)
                    hashed.update(data)
                if count != size or hashed.hexdigest() != key:
                    raise Refused("stale_reference", "Incomplete upload or hash mismatch; import again.")
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
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise Refused("invalid_input", "Not a sha256 blob reference; import the file again.")
        try:
            fd = os.open(self.directory / key, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                data = stream.read(self.limit + 1)
        except FileNotFoundError as exc:
            raise Refused("stale_reference", "Blob not present after restore; import again and prepare a new operation.") from exc
        if len(data) > self.limit or sha256(data) != key:
            raise Refused("stale_reference", "Immutable blob failed its hash or configured size limit; stop and recover it before preparing again.")
        return data
