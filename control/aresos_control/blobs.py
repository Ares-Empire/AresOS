import hashlib
import json
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

    def put(self, data, origin="internal"):
        return self.put_stream([data], len(data), sha256(data), origin)

    def put_stream(self, chunks, size, key, origin="internal"):
        if origin not in {"internal", "composition_part", "draft_body", "draft_html", "quoted_mail", "wire", "caller_import", "export"}:
            raise ValueError("Unknown service blob origin")
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
            # Publish authorization only after the bytes are durable. Missing old or
            # interrupted metadata grants neither download nor caller-import rights.
            origins = self.origins(key) | {origin}
            meta_fd, meta_name = tempfile.mkstemp(prefix=".upload-", dir=self.directory)
            try:
                with os.fdopen(meta_fd, "w") as meta:
                    json.dump(sorted(origins), meta)
                    meta.flush()
                    os.fsync(meta.fileno())
                os.replace(meta_name, self.directory / (".origins-" + key))
                sync_directory(self.directory)
            finally:
                if os.path.exists(meta_name):
                    os.unlink(meta_name)
        finally:
            os.unlink(temporary)
        return key

    def origins(self, key):
        try:
            return set(json.loads((self.directory / (".origins-" + key)).read_text()))
        except (FileNotFoundError, ValueError, TypeError):
            return set()

    def require_origin(self, key, origin):
        data = self.read(key)
        if origin not in self.origins(key):
            raise Refused("file_refused", "Blob is not an owner export." if origin == "export" else "Not a caller-imported blob; import the local file through the proxy.")
        return data

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
