"""Descriptor-relative access to the bench's owned data trees."""
from contextlib import contextmanager, ExitStack
import errno
import os
from pathlib import Path
import stat

DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
MARKER = '.bench-owned'
STAMP = b'AresOS bench data v1\n'


def absolute(path):
    if path.anchor != '/' or len(path.parts) < 2 or '..' in path.parts:
        raise ValueError('bench data path must be absolute, below / and contain no ..')
    return path


@contextmanager
def open_directory(path, *, create=False):
    absolute(path)
    fd = os.open('/', DIR)
    try:
        for part in path.parts[1:]:
            try:
                next_fd = os.open(part, DIR, dir_fd=fd)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o700, dir_fd=fd)
                next_fd = os.open(part, DIR, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        yield fd
    except OSError as error:
        if error.errno in (errno.ELOOP, errno.ENOTDIR):
            raise ValueError('bench data path is redirected or is not a directory') from error
        raise
    finally:
        os.close(fd)


def existing_parent(path):
    while True:
        try:
            with open_directory(path):
                return path
        except FileNotFoundError:
            path = path.parent


def validate_cache(path):
    with open_directory(existing_parent(absolute(path))) as fd:
        if os.fstat(fd).st_uid != os.getuid():
            raise ValueError('bench cache directory must be owned by the user')
    return path


def mount_id(fd):
    info = Path(f'/proc/self/fdinfo/{fd}').read_text()
    for line in info.splitlines():
        if line.startswith('mnt_id:'):
            return int(line.split()[1])
    raise ValueError('bench data mount could not be verified')


class DataTree:
    def __init__(self, path, mount=mount_id, *, anchor=None):
        self.path = absolute(path)
        self.mount = mount
        self.anchor = absolute(anchor) if anchor is not None else self.path.parent

    def _same_mount(self, parent, fd):
        if os.fstat(parent).st_dev != os.fstat(fd).st_dev or self.mount(parent) != self.mount(fd):
            raise ValueError('mount inside bench data or at deletion root')

    @contextmanager
    def entry(self, parent, name, flags=os.O_PATH | os.O_NOFOLLOW):
        fd = os.open(name, flags, dir_fd=parent)
        try:
            self._same_mount(parent, fd)
            yield fd
        finally:
            os.close(fd)

    def _marker(self, fd, create):
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL if create else os.O_RDONLY
        try:
            marker = os.open(MARKER, flags | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=fd)
        except FileNotFoundError:
            raise ValueError('bench data directory is missing its ownership marker') from None
        with os.fdopen(marker, 'wb' if create else 'rb') as stream:
            self._same_mount(fd, stream.fileno())
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
                raise ValueError('invalid bench ownership marker')
            if create:
                stream.write(STAMP)
                stream.flush()
                os.fsync(stream.fileno())
                os.fsync(fd)
            elif stream.read(len(STAMP) + 1) != STAMP:
                raise ValueError('invalid bench ownership marker')

    @contextmanager
    def root(self, *, create=False):
        with ExitStack() as stack:
            parent = stack.enter_context(open_directory(
                self.anchor, create=create and self.anchor == self.path.parent))
            for part in self.path.parent.relative_to(self.anchor).parts:
                if create:
                    try:
                        os.mkdir(part, mode=0o700, dir_fd=parent)
                    except FileExistsError:
                        pass
                parent = stack.enter_context(self.entry(parent, part, DIR))
            made = False
            if create:
                try:
                    os.mkdir(self.path.name, mode=0o700, dir_fd=parent)
                    made = True
                except FileExistsError:
                    pass
            with self.entry(parent, self.path.name, DIR) as fd:
                if os.fstat(fd).st_uid != os.getuid():
                    raise ValueError('bench data directory must be owned by the user')
                self._marker(fd, made)
                yield parent, fd

    def exists(self):
        try:
            with self.root():
                return True
        except FileNotFoundError:
            return False

    def _blocks(self, fd, seen):
        info = os.fstat(fd)
        if info.st_ino in seen:
            return 0
        seen.add(info.st_ino)
        total = info.st_blocks * 512
        if stat.S_ISDIR(info.st_mode):
            folder = os.open('.', DIR, dir_fd=fd)
            try:
                for name in os.listdir(folder):
                    with self.entry(folder, name) as child:
                        total += self._blocks(child, seen)
            finally:
                os.close(folder)
        return total

    def _delete(self, parent, name, fd):
        if stat.S_ISDIR(os.fstat(fd).st_mode):
            folder = os.open('.', DIR, dir_fd=fd)
            try:
                for child in sorted(os.listdir(folder), key=lambda child: child == MARKER):
                    with self.entry(folder, child) as entry:
                        self._delete(folder, child, entry)
                self._unchanged(parent, name, fd)
                os.rmdir(name, dir_fd=parent)
            finally:
                os.close(folder)
        else:
            self._unchanged(parent, name, fd)
            os.unlink(name, dir_fd=parent)

    @staticmethod
    def _unchanged(parent, name, fd):
        if not os.path.samestat(os.stat(name, dir_fd=parent, follow_symlinks=False), os.fstat(fd)):
            raise ValueError('bench data changed during cleanup')

    @contextmanager
    def target(self, relative):
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('bench data target must be relative and contain no ..')
        with self.root() as (parent, root):
            if not relative.parts:
                yield parent, self.path.name, root
            else:
                with self._target(root, relative.parts) as target:
                    yield target

    @contextmanager
    def _target(self, parent, parts):
        with self.entry(parent, parts[0], DIR if len(parts) > 1 else os.O_PATH | os.O_NOFOLLOW) as fd:
            if len(parts) == 1:
                yield parent, parts[0], fd
            else:
                with self._target(fd, parts[1:]) as target:
                    yield target

    def allocated(self, relative=Path()):
        try:
            with self.target(relative) as (_, _, fd):
                return self._blocks(fd, set())
        except FileNotFoundError:
            return 0

    def remove(self, relative=Path()):
        try:
            with self.target(relative) as (parent, name, fd):
                # Check the entire target before unlinking anything.
                self._blocks(fd, set())
                self._delete(parent, name, fd)
        except FileNotFoundError:
            pass

    def names(self, relative=Path()):
        try:
            with self.target(relative) as (_, _, fd):
                folder = os.open('.', DIR, dir_fd=fd)
                try:
                    return os.listdir(folder)
                finally:
                    os.close(folder)
        except FileNotFoundError:
            return []
