"""Opt-in attribution experiments (environment flags). Off by default.

NO_HEADER_INDEX=1    skip the optional operation_headers index (bc738001/ae0047d8).
REAL_JOURNAL_STAT=1  key Chrome's committed projection cache on the journal's real
                     (inode, size, mtime), as production does, instead of the
                     sweep's always-advancing scripted timestamps (main 15880c62).
CACHED_BUILD=1       give the Chrome adapter its build hash, as an installed
                     build-id.json does in production, instead of hashing every
                     runtime file at each Engine start (test checkout only).
Flags that name code absent at a commit are ignored there.
"""
import os


def apply():
    applied = []
    if os.environ.get('NO_HEADER_INDEX'):
        from aresos_control.storage import Store
        if hasattr(Store, '_index_operation_headers'):
            Store._index_operation_headers = lambda self: None
            applied.append('NO_HEADER_INDEX')
    try:
        from aresos_control.chrome.committed import Projection
        from aresos_control.chrome import adapter
    except ImportError:
        return applied
    if os.environ.get('REAL_JOURNAL_STAT'):
        real_stat, sync = os.stat, Projection.sync
        def real_sync(self):
            info = real_stat(self.store.evidence_dir / 'operations.jsonl')
            signature = (info.st_ino, info.st_size, info.st_mtime_ns)
            if getattr(self, '_real_signature', None) == signature and self.signature is not None:
                return
            sync(self)
            self._real_signature = signature
        Projection.sync = real_sync
        applied.append('REAL_JOURNAL_STAT')
    if os.environ.get('CACHED_BUILD'):
        import importlib.util
        spec = importlib.util.spec_from_file_location('aresos_chrome_build', adapter.RUNTIME / 'chrome' / 'build.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        adapter.Chrome.__init__.__defaults__ = (module.build_hash(), None)
        applied.append('CACHED_BUILD')
    return applied
