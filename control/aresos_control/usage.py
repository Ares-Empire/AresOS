"""Quiet unless used (owner, #254): which Claude Code sessions used the AresOS tools.

The MCP proxy (one per session, running as the owner, started by Claude Code) marks its parent, the Claude Code
process, before it returns a result that names an operation. While the service can't be reached, the Stop hook looks
for a mark of one of its own ancestors: Claude Code 2.1.319 starts both from the same process (pinned by the
interactive boundary suite). A mark is an empty file named `<pid>-<start>`; the start time (field 22 of
/proc/<pid>/stat) keeps a reused PID from inheriting a mark. The owner's /run/user/<uid> is a tmpfs, so marks vanish
at logout. The uid, not XDG_RUNTIME_DIR, names it: the managed commands run under `env -i`.

One notice per outage (lead, 2026-11-15): when the Stop hook tells a marked session that the tools are not running,
it leaves a second empty file `<pid>-<start>.told` beside the mark; later stops stay quiet while it exists. The next
hook that reaches the service removes it, so a later outage tells the session again.
"""
import os
from pathlib import Path
import stat

RUN = Path('/run/user')
PROC = Path('/proc')
FOLDERS = ('aresos-control', 'used')
LEVELS = 4
TOLD = '.told'
# Keys in a result's data that name an operation: its id, or an approval that reserved one.
NAMING = {'operation_id', 'approval'}


class Unreadable(Exception):
    """The marks or the process tree could not be read; the reader then assumes a mark."""


def process(pid, proc=PROC):
    """(start time, parent pid) of a live process."""
    data = (proc / str(pid) / 'stat').read_bytes()
    # The command name may contain spaces and brackets; fields resume after the last ')' (field 3 on).
    fields = data[data.rindex(b')') + 2:].split()
    return int(fields[19]), int(fields[1])


def names_operation(effect, result):
    """True when a non-read tool result names an operation: an operation id, an approval, or an unknown outcome."""
    if effect == 'read' or type(result) is not dict:
        return False
    if result.get('error', {}).get('code') == 'unknown':
        return True
    found, stack = False, [result.get('data')]
    while stack and not found:
        value = stack.pop()
        if isinstance(value, dict):
            found = bool(NAMING & value.keys())
            stack.extend(value.values())
        elif isinstance(value, list):
            stack.extend(value)
    return found


def _open_folder(name, parent_fd, uid, create):
    """A private folder of `uid`, never through a link: 0700, owned by uid."""
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent_fd)
        except FileExistsError:
            pass
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
    try:
        info = os.fstat(fd)
        if info.st_uid != uid or stat.S_IMODE(info.st_mode) & 0o077:
            raise Unreadable(f'{name}: not a private folder of uid {uid}')
    except BaseException:
        os.close(fd)
        raise
    return fd


def _marks(uid, run, create):
    """The `used` folder's descriptor; FileNotFoundError when it doesn't exist (and create is False)."""
    fd = os.open(str(run / str(uid)), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        if os.fstat(fd).st_uid != uid:
            raise Unreadable(f'{run / str(uid)}: not owned by uid {uid}')
        for name in FOLDERS:
            child = _open_folder(name, fd, uid, create)
            os.close(fd)
            fd = child
    except BaseException:
        os.close(fd)
        raise
    return fd


def _create(name, folder):
    """An empty 0600 file in the marks folder, never through a link."""
    os.close(os.open(name, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=folder))


def _plain(name, folder):
    """True when `name` is a plain file in the folder, False when it doesn't exist; raises otherwise (also for a link)."""
    try:
        info = os.stat(name, dir_fd=folder, follow_symlinks=False)
    except FileNotFoundError:
        return False
    if not stat.S_ISREG(info.st_mode):
        raise Unreadable(f'{name}: not a plain file')
    return True


def _session(folder, pid, proc):
    """The mark (`<pid>-<start>`) of the nearest marked ancestor, up to four levels, never PID 1; None when unmarked."""
    for _ in range(LEVELS):
        if pid <= 1:
            break
        start, parent = process(pid, proc)
        key = f'{pid}-{start}'
        if _plain(key, folder):
            return key
        pid = parent
    return None


def mark(pid=None, uid=None, run=RUN, proc=PROC):
    """Mark the Claude Code process (the proxy's parent) as having used the tools. Raises on any failure."""
    pid = os.getppid() if pid is None else pid
    uid = os.getuid() if uid is None else uid
    start, _ = process(pid, proc)
    folder = _marks(uid, run, create=True)
    try:
        _create(f'{pid}-{start}', folder)
    finally:
        os.close(folder)


def used(pid=None, uid=None, run=RUN, proc=PROC):
    """True when one of the hook's ancestors (up to four levels, never PID 1) has a mark, or anything can't be read.

    No marks folder at all is a clear "no": nothing in this login ever marked a session.
    """
    pid = os.getppid() if pid is None else pid
    uid = os.getuid() if uid is None else uid
    try:
        try:
            folder = _marks(uid, run, create=False)
        except FileNotFoundError:
            return False
        try:
            return _session(folder, pid, proc) is not None
        finally:
            os.close(folder)
    except Exception:
        return True


def notice(pid=None, uid=None, run=RUN, proc=PROC):
    """Whether the Stop hook tells this session now that the tools are not running: once per outage.

    A session that used the tools (as `used`) is told unless its `.told` file is there; telling it creates that file.
    A `.told` file that can't be written still tells (better twice than never); one that can't be read (other than
    missing) counts as not told. Marks that can't be read tell at every stop: no session is known to record it for.
    """
    pid = os.getppid() if pid is None else pid
    uid = os.getuid() if uid is None else uid
    try:
        folder = _marks(uid, run, create=False)
    except FileNotFoundError:
        return False
    except Exception:
        return True
    try:
        try:
            key = _session(folder, pid, proc)
        except Exception:
            return True
        if key is None:
            return False
        try:
            if _plain(key + TOLD, folder):
                return False
        except Exception:
            pass
        try:
            _create(key + TOLD, folder)
        except Exception:
            pass
        return True
    finally:
        os.close(folder)


def reached(pid=None, uid=None, run=RUN, proc=PROC):
    """A hook reached the service: remove this session's `.told` file so a later outage tells it again. Never raises."""
    pid = os.getppid() if pid is None else pid
    uid = os.getuid() if uid is None else uid
    try:
        folder = _marks(uid, run, create=False)
    except Exception:
        return
    try:
        key = _session(folder, pid, proc)
        if key is not None:
            os.unlink(key + TOLD, dir_fd=folder)
    except Exception:
        pass
    finally:
        os.close(folder)
