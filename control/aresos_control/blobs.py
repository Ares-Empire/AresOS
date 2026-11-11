import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from contextlib import contextmanager

from . import retention
from .common import FILE_LIMIT, Refused, storage_stream, cleanup, sha256, storage_refusal
from .storage import sync_directory
from .space import SpaceLedger


class Blobs:
    def __init__(self, directory, limit=FILE_LIMIT, ensure_writable=lambda: None, ledger=None):
        self.ensure_writable = ensure_writable
        self._staged = None
        self.directory, self.limit = Path(directory), limit
        self.ledger = ledger or SpaceLedger((self.directory,))
        if type(limit) is not int or limit < 1:
            raise ValueError("File limit must be a positive byte count")
        if not self.directory.exists():
            self.ledger.admit(8192)
        self.directory.mkdir(exist_ok=True, mode=0o700)
        # An interrupted upload is never a blob; remove its private staging inode.
        for temporary in self.directory.glob(".upload-*"):
            temporary.unlink()

    @contextmanager
    def staging(self):
        if self._staged is not None:
            raise ValueError('Nested blob staging is unsupported')
        self._staged = {}
        try:
            yield
        finally:
            self._staged = None

    def commit_staged(self):
        staged = self._staged
        rows = [p for p in self.directory.iterdir() if re.fullmatch(r'[0-9a-f]{64}', p.name)]
        added = {k: v for k, v in staged.items() if not (self.directory / k).exists()}
        if (len(rows) + len(added) > retention.BLOB_COUNT or
                sum(p.stat().st_size for p in rows) + sum(len(v[0]) for v in added.values()) > retention.BLOB_BYTES):
            retention.refuse('Private blobs in ' + self.directory.name, retention.BLOB_COUNT, retention.BLOB_BYTES)
        self.ledger.admit(sum(len(v[0]) for v in added.values()) + 8192 * len(added))
        self._staged = None
        try:
            for data, origins in staged.values():
                for origin in origins:
                    self.put(data, origin)
        finally:
            self._staged = staged

    def put(self, data, origin="internal"):
        self.ensure_writable()
        if self._staged is not None:
            if len(data) > self.limit:
                raise Refused('file_refused', 'File exceeds the configured per-file limit.')
            key = sha256(data)
            self._staged.setdefault(key, (data, set()))[1].add(origin)
            return key
        return self.put_stream([data], len(data), sha256(data), origin)

    def put_stream(self, chunks, size, key, origin="internal"):
        self.ensure_writable()
        if origin not in {"internal", "composition_part", "draft_body", "draft_html", "quoted_mail", "wire", "caller_import", "export"}:
            raise ValueError("Unknown service blob origin")
        if type(size) is not int or not 0 <= size <= self.limit:
            raise Refused("file_refused", "File exceeds the configured per-file limit; choose a smaller file.")
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise Refused("invalid_input", "Not a sha256 blob reference; import the file again.")
        self.admit(size, key)
        self.ledger.admit(size + 8192)
        temporary, published = None, False
        try:
            fd, temporary = tempfile.mkstemp(prefix=".upload-", dir=self.directory)
            count, hashed = 0, hashlib.sha256()
            with storage_stream(os.fdopen(fd, "wb")) as stream:
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
                published = True
            except FileExistsError:
                self.read(key)
            sync_directory(self.directory)
            # Publish authorization only after the bytes are durable. Missing old or
            # interrupted metadata grants neither download nor caller-import rights.
            origins = self.origins(key) | {origin}
            meta_fd, meta_name = tempfile.mkstemp(prefix=".upload-", dir=self.directory)
            try:
                with storage_stream(os.fdopen(meta_fd, "w")) as meta:
                    json.dump(sorted(origins), meta)
                    meta.flush()
                    os.fsync(meta.fileno())
                os.replace(meta_name, self.directory / (".origins-" + key))
                sync_directory(self.directory)
            finally:
                with cleanup('blob origin temporary unlink'):
                    if os.path.exists(meta_name):
                        os.unlink(meta_name)
        except BaseException as exc:
            with cleanup('blob publication rollback', exc):
                if published:
                    (self.directory / key).unlink(missing_ok=True)
                    (self.directory / ('.origins-' + key)).unlink(missing_ok=True)
                    sync_directory(self.directory)
            storage = storage_refusal(exc)
            if isinstance(exc, OSError):
                raise storage or Refused('storage_limit', 'Disk full or private blob write failed; no partial blob retained. Free storage before retrying.') from exc
            raise
        finally:
            with cleanup('blob temporary unlink'):
                if temporary is not None:
                    os.unlink(temporary)
        return key

    def admit(self, size, key):
        self.ensure_writable()
        rows = [p for p in self.directory.iterdir() if re.fullmatch(r'[0-9a-f]{64}', p.name)]
        if (self.directory / key).exists():
            return
        if len(rows) + 1 > retention.BLOB_COUNT or sum(p.stat().st_size for p in rows) + size > retention.BLOB_BYTES:
            retention.refuse('Private blobs in ' + self.directory.name, retention.BLOB_COUNT, retention.BLOB_BYTES)

    def expire(self, pinned, now, ttl, check_only=False):
        self.ensure_writable()
        # Unlinking only frees blocks; still account for filesystem metadata.
        candidates = [path for path in self.directory.iterdir()
                      if re.fullmatch(r'[0-9a-f]{64}', path.name) and path.name not in pinned
                      and now - path.stat().st_mtime >= ttl]
        if check_only:
            return bool(candidates)
        if candidates:
            self.ledger.admit(8192)
        changed = False
        for path in candidates:
            path.unlink()
            (self.directory / ('.origins-' + path.name)).unlink(missing_ok=True)
            changed = True
        if changed:
            sync_directory(self.directory)
        return changed

    def origins(self, key):
        staged = self._staged.get(key) if self._staged is not None else None
        try:
            return set(json.loads((self.directory / (".origins-" + key)).read_text())) | (staged[1] if staged else set())
        except (FileNotFoundError, ValueError, TypeError):
            return staged[1] if staged else set()

    def require_origin(self, key, origin):
        data = self.read(key)
        if origin not in self.origins(key):
            raise Refused("file_refused", "Blob is not an owner export." if origin == "export" else "Not a caller-imported blob; import the local file through the proxy.")
        return data

    def read(self, key):
        if not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key):
            raise Refused("invalid_input", "Not a sha256 blob reference; import the file again.")
        if self._staged is not None and key in self._staged:
            return self._staged[key][0]
        try:
            fd = os.open(self.directory / key, os.O_RDONLY | os.O_NOFOLLOW)
            with storage_stream(os.fdopen(fd, "rb")) as stream:
                data = stream.read(self.limit + 1)
        except FileNotFoundError as exc:
            raise Refused("stale_reference", "Blob not present after restore; import again and prepare a new operation.") from exc
        if len(data) > self.limit or sha256(data) != key:
            raise Refused("stale_reference", "Immutable blob failed its hash or configured size limit; stop and recover it before preparing again.")
        return data
