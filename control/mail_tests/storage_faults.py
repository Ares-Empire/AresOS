"""Faults at raw file operations and SQLite's actual VFS I/O boundary.

The VFS wraps the runtime SQLite library, including internal statement writes,
rollback journals and the independent index connection. No SQL is simulated.
"""
from contextlib import contextmanager, ExitStack
import builtins
import ctypes as C
import errno
import io
import os
from pathlib import Path
import _sqlite3
from unittest.mock import patch
from aresos_control.common import CLEANUP


ACTIVE = None
EXCLUDED = 0


@contextmanager
def outside_faults():
    global EXCLUDED
    EXCLUDED += 1
    try:
        yield
    finally:
        EXCLUDED -= 1


class Methods(C.Structure):
    _fields_ = [('version', C.c_int), ('calls', C.c_void_p * 18)]


class File(C.Structure):
    _fields_ = [('methods', C.POINTER(Methods))]


class VFS(C.Structure):
    _fields_ = [('version', C.c_int), ('size', C.c_int), ('maxpath', C.c_int),
                ('next', C.c_void_p), ('name', C.c_char_p), ('data', C.c_void_p),
                ('open', C.c_void_p), ('delete', C.c_void_p)]


class SQLiteIO:
    def __init__(self):
        self.lib = C.CDLL(_sqlite3.__file__)
        self.lib.sqlite3_vfs_find.restype = C.POINTER(VFS)
        self.vfs = self.lib.sqlite3_vfs_find(None)
        self.files, self.tables = {}, {}
        self.open_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_void_p, C.POINTER(File), C.c_int, C.c_void_p)
        self.delete_type = C.CFUNCTYPE(C.c_int, C.c_void_p, C.c_char_p, C.c_int)
        self.real_delete = self.delete_type(self.vfs.contents.delete)
        self.close_type = C.CFUNCTYPE(C.c_int, C.POINTER(File))
        self.write_type = C.CFUNCTYPE(C.c_int, C.POINTER(File), C.c_void_p, C.c_int, C.c_int64)
        self.truncate_type = C.CFUNCTYPE(C.c_int, C.POINTER(File), C.c_int64)
        self.sync_type = C.CFUNCTYPE(C.c_int, C.POINTER(File), C.c_int)
        self.real_open = self.open_type(self.vfs.contents.open)
        self.callbacks = [self.close_type(self.close), self.write_type(self.write),
                          self.truncate_type(self.truncate), self.sync_type(self.sync), self.open_type(self.open)]
        self.delete_callback = self.delete_type(self.delete)
        self.vfs.contents.delete = C.cast(self.delete_callback, C.c_void_p).value
        self.vfs.contents.open = C.cast(self.callbacks[-1], C.c_void_p).value

    def hit(self, label):
        if ACTIVE is not None:
            return ACTIVE.hit(label, sqlite=True)
        return 0

    def open(self, vfs, name, file, flags, output):
        path = os.fsdecode(C.string_at(name)) if name else ''
        kind = 'sqlite.index' if 'journal-index.sqlite' in path else 'sqlite.main'
        fault = self.hit(kind + '.create') if flags & 4 else 0
        if fault:
            return fault
        result = self.real_open(vfs, name, file, flags, output)
        if result == 0:
            original = file.contents.methods
            address = C.addressof(original.contents)
            original = C.cast(address, C.POINTER(Methods))
            if address not in self.tables:
                wrapped = Methods.from_buffer_copy(original.contents)
                for index, callback in zip((0, 2, 3, 4), self.callbacks):
                    wrapped.calls[index] = C.cast(callback, C.c_void_p).value
                idle = Methods.from_buffer_copy(original.contents)
                idle.calls[0] = C.cast(self.callbacks[0], C.c_void_p).value
                self.tables[address] = (idle, wrapped)
            self.files[C.addressof(file.contents)] = (original, kind)
            file.contents.methods = C.pointer(self.tables[address][ACTIVE is not None])
        return result

    def activate(self):
        for address, (original, _) in self.files.items():
            tables = self.tables[C.addressof(original.contents)]
            C.cast(address, C.POINTER(File)).contents.methods = C.pointer(tables[ACTIVE is not None])

    def delete(self, vfs, name, sync):
        path = os.fsdecode(name)
        kind = 'sqlite.index' if 'journal-index.sqlite' in path else 'sqlite.main'
        fault = self.hit(kind + '.unlink')
        return fault or self.real_delete(vfs, name, sync)

    def close(self, file):
        original, kind = self.files.pop(C.addressof(file.contents))
        # A simulated failed close must still release the test's descriptor.
        fault = self.hit(kind + '.close')
        result = self.close_type(original.contents.calls[0])(file)
        return fault or result

    def call(self, file, index, kind, callback, *args):
        original, prefix = self.files[C.addressof(file.contents)]
        fault = self.hit(prefix + '.' + kind)
        if fault:
            return fault
        return callback(original.contents.calls[index])(file, *args)

    def write(self, file, buffer, size, offset):
        return self.call(file, 2, 'write', self.write_type, buffer, size, offset)

    def truncate(self, file, size):
        return self.call(file, 3, 'truncate', self.truncate_type, size)

    def sync(self, file, flags):
        return self.call(file, 4, 'fsync', self.sync_type, flags)


# Keep callbacks alive until every SQLite handle closes, including handles
# created in fixture setup and restart. Only an active scope injects faults.
SQLITE_IO = SQLiteIO()


class OSWrites:
    def __init__(self, fail_at=None, mode='single', cleanup_at=None):
        self.fail_at, self.points, self.failed = fail_at, [], False
        self.mode, self.cleanup_at = mode, cleanup_at
        self.cleanup_points, self.failures = [], []

    def hit(self, label, sqlite=False):
        if EXCLUDED:
            return 0
        self.points.append(label)
        number = len(self.points)
        if CLEANUP.get() is not None or (self.failed and label.rsplit('.', 1)[-1] in {'close', 'unlink', 'rename', 'truncate'}):
            self.cleanup_points.append((number, label, CLEANUP.get() or 'syscall'))
        secondary = number == self.cleanup_at
        if number == self.fail_at or (self.mode == 'persistent' and self.fail_at is not None and number >= self.fail_at) or secondary:
            self.failed = True
            self.failures.append((number, label, 'EIO' if secondary else 'ENOSPC'))
            if sqlite:
                return 10 if secondary else 13  # SQLITE_IOERR / SQLITE_FULL.
            raise OSError(errno.EIO if secondary else errno.ENOSPC, 'Synthetic storage failure at ' + label)
        return 0

    @contextmanager
    def wrap(self, store=None):
        global ACTIVE
        previous, ACTIVE = ACTIVE, self
        SQLITE_IO.activate()
        original_open = builtins.open
        sweep = self
        def label(path):
            return 'journal' if str(path).endswith('operations.jsonl') else 'file'
        class Raw(io.FileIO):
            def close(self):
                if not self.closed:
                    try:
                        sweep.hit(label(self.name) + '.close')
                    finally:
                        super().close()
            def write(self, data):
                sweep.hit(label(self.name) + '.write')
                return super().write(data)
            def truncate(self, size=None):
                sweep.hit(label(self.name) + '.truncate')
                return super().truncate(size)
        def opened(file, mode='r', buffering=-1, encoding=None, errors=None, newline=None,
                   closefd=True, opener=None):
            if any(char in mode for char in 'wax+') and not isinstance(file, int) and not Path(file).exists():
                sweep.hit(label(file) + '.create')
            raw = Raw(file, mode, closefd, opener)
            if buffering == 0:
                return raw
            size = buffering if buffering > 1 else io.DEFAULT_BUFFER_SIZE
            stream = (io.BufferedRandom(raw, size) if '+' in mode else
                      io.BufferedWriter(raw, size) if any(char in mode for char in 'wax') else io.BufferedReader(raw, size))
            return stream if 'b' in mode else io.TextIOWrapper(stream, encoding, errors, newline,
                                                              line_buffering=buffering == 1)
        def os_open(method):
            def call(path, flags, *args, **kwargs):
                unnamed = getattr(os, 'O_TMPFILE', 0)
                if flags & os.O_CREAT or (unnamed and flags & unnamed == unnamed):
                    sweep.hit('file.create')
                return method(path, flags, *args, **kwargs)
            return call
        def operation(method, kind):
            def call(*args, **kwargs):
                sweep.hit(kind)
                return method(*args, **kwargs)
            return call
        try:
            with ExitStack() as stack:
                stack.enter_context(patch('builtins.open', side_effect=opened))
                stack.enter_context(patch('io.open', side_effect=opened))
                stack.enter_context(patch('os.open', side_effect=os_open(os.open)))
                for name, kind in [('fsync', 'file.fsync'), ('link', 'file.link'),
                                   ('replace', 'file.rename'), ('rename', 'file.rename'),
                                   ('ftruncate', 'file.truncate'), ('unlink', 'file.unlink')]:
                    stack.enter_context(patch('os.' + name, side_effect=operation(getattr(os, name), kind)))
                real_close = os.close
                def close(fd):
                    try:
                        sweep.hit('file.close')
                    finally:
                        real_close(fd)
                stack.enter_context(patch('os.close', side_effect=close))
                if store is not None and not isinstance(store.journal, Raw):
                    for name in ('write', 'truncate'):
                        stack.enter_context(patch.object(store.journal, name,
                            side_effect=operation(getattr(store.journal, name), 'journal.' + name)))
                yield
        finally:
            ACTIVE = previous
            SQLITE_IO.activate()
