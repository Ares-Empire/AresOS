"""Service-owned, owner-readable upload copies; caller paths are never opened here."""
import os
from pathlib import Path
import tempfile
import stat
import time

from ..common import Refused, cleanup, sha256, storage_stream
from ..storage import sync_directory


def prune(chrome, now=None):
    directory = Path(chrome.upload_dir)
    if not directory.exists():
        return
    now = time.time() if now is None else now
    for path in directory.iterdir():
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid():
            raise Refused('refused', 'Unexpected upload retention entry; owner must inspect the service upload directory.')
        if now - info.st_mtime >= 900:
            path.unlink()
    entries = list(directory.iterdir())
    if len(entries) >= 2 or sum(path.stat().st_size for path in entries) > 50 * 1024 * 1024:
        raise Refused('refused', 'Two retained uploads are still in use; wait for expiry or ask the owner to inspect them.')


def release(chrome, path):
    if path is not None:
        with cleanup('Chrome upload copy release'):
            Path(path).unlink(missing_ok=True)
            sync_directory(Path(path).parent)


def copy_for_browser(chrome, file):
    data = chrome.blobs.require_origin(file['sha256'], 'caller_import')
    if len(data) != file['size']:
        raise Refused('stale_approval', 'Imported upload size changed; import and prepare again.')
    directory = Path(chrome.upload_dir)
    prune(chrome)
    chrome.store.ledger.admit(len(data) + 16384)
    directory.mkdir(mode=0o711, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.upload-', dir=directory)
    try:
        with storage_stream(os.fdopen(fd, 'wb')) as stream:
            stream.write(data)
            stream.flush()
            os.fchmod(stream.fileno(), 0o444)
            os.fsync(stream.fileno())
        destination = directory / file['sha256']
        try:
            os.link(temporary, destination)
        except FileExistsError:
            with storage_stream(open(destination, 'rb')) as stream:
                if sha256(stream.read(chrome.blobs.limit + 1)) != file['sha256']:
                    raise Refused('stale_approval', 'Service upload copy changed; owner must inspect it before another upload.')
        sync_directory(directory)
        return data, destination
    finally:
        with cleanup('Chrome upload temporary unlink'):
            os.unlink(temporary)
