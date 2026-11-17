"""Package 18c, check 8 (REVIEW-X1 #2, RECHECK-X1 #2, RECHECK-X2): every regular file under some folders searched for
byte strings, and every path the search learned of accounted for, so a scan that couldn't look never passes as clean.

One record per learned path (RECHECK-X2). The scan learns a path in two ways: a root it is given, and a name a
folder's listing returns. Each record ends in exactly one outcome: searched (a regular file, read to its end), listed
(a folder: its listing read to its end, every name in it a record of its own), not a file (a link, socket, pipe or
device: nothing to search, and never opened; a link is never followed), or an error. scan() builds its whole answer
from the records at the end, so no path can leave the count on the way: whatever is not searched, listed or not a
file is in "errors", or, in root's walk of a FUSE mount, in "refused" (below).

Searched means that file, not another one under its name:
- A name is opened once, as a handle on the file itself (O_PATH, relative to its folder's handle, links not
  followed). Its type is read from that handle and its content through it (/proc/self/fd), so the name cannot come to
  mean another file between the stat and the read, and a file removed meanwhile is still the one searched.
- A listing gives every name an inode number. A file opened under another number than the listing's was put there
  after the listing: an error, never searched in the listed file's place (numbered_otherwise() for mount points and
  FUSE, whose listings number otherwise).
- There is no second try. A name that is gone when it is opened is an error, also when it is back a moment later.

Runtime files: a path under VANISHING that is gone when it is opened (a running process removed it after the listing)
is named under "vanished", and it is an error too (RECHECK-X1 #2): its content was never read, so it may have held
the password. Only a path in MAY_VANISH, each with the reason its content can't hold it, is exempt.

FUSE (RECHECK-X1 #2, RECHECK-X2 #2). actions.py's search_for() calls scan() as root, over everything. A FUSE mount
refuses every user but the one who mounted it unless it was mounted with allow_other, so root walks it first; what
root is refused at or under its mount point (a PermissionError) goes to "refused" with its path and its listing's
number, and search_for() has the mount's owner walk the whole mount: `python3 -I tree_scan.py` under runuser, the
request on stdin ({"roots": [...], "needles": [hex, ...], "cover": [[path, number], ...]}), the answer on stdout
(paths and needle numbers, never a needle). "covered" in that answer names each of root's refused paths the owner's
walk searched, listed or found not to be a file, under the number root's listing gave it; search_for() keeps root's
refusal as an error for every path that is not there.

What this cannot see, and says so:
- A file system that gives a new file the inode number of one just removed (ext4 and XFS do; tmpfs and btrfs, which
  the guest's scanned folders are on, count upwards) hides a file removed and made again between its folder's
  listing and its open. Nothing the kernel reports about a name outlasts the file but that number.
- A FUSE server that sends one number for every name (the document portal) gives its listings nothing to hold a
  file to: there the handle still makes the file opened the file searched, and no more.
- The scan is a walk, not a snapshot: it learns what a folder holds when it lists it. A file removed before that, or
  moved from a folder not yet listed into one already listed, is never learned; each file is searched as it was
  while it was read.
"""
import collections
import errno
import json
import os
import re
import stat
import sys

# Folders whose files running processes create and remove (systemd, logind, his session, temporary files).
VANISHING = ('/run/', '/tmp/', '/var/tmp/')
# Runtime paths that may vanish unread without failing the scan: {exact path: why its content can't hold the
# password}; a folder's entry covers what was in it. None: no control run so far vanished anything. A path is added
# only with its reason, here and in reviews/18c-image-test/PROGRESS.md.
MAY_VANISH = {}

# A record's outcome. The first three leave nothing unsearched. GONE is an error unless MAY_VANISH names the path,
# REFUSED (root's walk only) stands until the mount's owner has covered the path, and anything else is an error.
SEARCHED, LISTED, NOT_A_FILE, GONE, REFUSED, ERROR = 'searched', 'listed', 'not a file', 'gone', 'refused', 'error'
SETTLED = (SEARCHED, LISTED, NOT_A_FILE)


def found_in(stream, needles):
    """Which of the needles (their numbers) a stream holds, read to its end in chunks: the Claude Code binary in his
    home is large. A needle may lie across any number of reads, short ones included."""
    found, tail, longest = set(), b'', max(len(needle) for needle in needles)
    while chunk := stream.read(1 << 20):
        window = tail + chunk
        found |= {index for index, needle in enumerate(needles) if needle in window}
        tail = window[-longest:]
    return found


def holds(source, needles):
    """Which of the needles a file holds: its path, or an open descriptor, which is closed."""
    with open(source, 'rb') as stream:
        return found_in(stream, needles)


def unescape(field):
    """A mountinfo path: space, tab, newline and backslash are written as octal escapes."""
    return re.sub(r'\\([0-7]{3})', lambda match: chr(int(match[1], 8)), field)


def fuse_mounts(roots, mountinfo='/proc/self/mountinfo'):
    """[(mount point, file system type, owner uid)] of every FUSE mount at or under one of the roots."""
    found = []
    with open(mountinfo) as lines:
        for line in lines:
            fields = line.split()
            separator = fields.index('-')
            point, kind, options = unescape(fields[4]), fields[separator + 1], fields[separator + 3]
            if kind != 'fuse' and not kind.startswith('fuse.'):
                continue
            if any(point == root or point.startswith(root.rstrip('/') + '/') for root in roots):
                owner = re.search(r'(?:^|,)user_id=(\d+)(?:,|$)', options)
                if owner is None:
                    raise ValueError(f'{point}: a FUSE mount without user_id ({options})')
                found.append((point, kind, int(owner[1])))
    return found


def describe(path, error):
    return f'{path}: {type(error).__name__}: {error.strerror or error}'


def within(path, points):
    """The deepest of the mount points that path is at or under, or None."""
    found = [point for point in points if path == point or path.startswith(point.rstrip('/') + '/')]
    return max(found, key=len, default=None)


def reopened(handle, flags):
    """The file a handle holds, opened for reading: /proc/self/fd names the open file itself, whatever has become of
    its path since."""
    return os.open(f'/proc/self/fd/{handle}', flags | os.O_CLOEXEC)


def listing(handle):
    """{name: the inode number the listing gives it} of the folder a handle holds, read to its end."""
    descriptor = reopened(handle, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with os.scandir(descriptor) as entries:
            names = {entry.name: entry.inode() for entry in entries}
    finally:
        os.close(descriptor)
    # A folder removed meanwhile lists as empty (glibc reads getdents' ENOENT as the end of the folder), and what it
    # held is unread: no links are left to a removed folder.
    if os.fstat(handle).st_nlink == 0:
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT))
    return names


def numbered_otherwise(folder, name, inode, info):
    """Whether this folder's listing numbers the name by something else than the file's own inode number, so that the
    opened file (info) having another number doesn't make it another file. A mount point is listed under the number
    of the folder it covers, a btrfs subvolume under its volume's, and a FUSE server sends what it likes (the
    document portal 4294967295 for every name).

    The listing itself is asked, a second time. If its numbers were the files' own, it would now give the name the
    opened file's number (the handle keeps that number from going to another file), which is not the first
    listing's; only a listing that numbers otherwise gives the first one again. The name must still be the opened
    file afterwards."""
    again = listing(folder).get(name)
    now = os.stat(name, dir_fd=folder, follow_symlinks=False)
    return again == inode and (now.st_dev, now.st_ino) == (info.st_dev, info.st_ino)


class Replaced(Exception):
    """The file opened under a name is not the one its folder's listing named."""


class Record:
    """One path the scan learned: the root it is under, the inode number its folder's listing gave it (None for a
    root, which no listing named) and, once it is read, its outcome (with the reason, when it isn't a good one)."""

    def __init__(self, path, root, inode):
        self.path, self.root, self.inode, self.outcome, self.detail = path, root, inode, None, None


class Scan:
    def __init__(self, needles, handover):
        self.needles, self.handover, self.records, self.hits = needles, handover, [], []

    def learn(self, path, root, inode=None):
        record = Record(path, root, inode)
        self.records.append(record)
        return record

    def read(self, record, name, folder=None):
        """Reads what a record names (name, in the folder a handle holds; a root by its path) and gives the record
        its outcome: the one place an outcome is set."""
        assert record.outcome is None, f'{record.path}: read twice'
        try:
            record.outcome = self.search(record, name, folder)
        except Replaced as error:
            record.outcome, record.detail = ERROR, f'{record.path}: {error}'
        except OSError as error:
            if isinstance(error, PermissionError) and within(record.path, self.handover) is not None:
                record.outcome = REFUSED
            elif isinstance(error, FileNotFoundError) and record.path.startswith(VANISHING):
                record.outcome = GONE
            else:
                record.outcome = ERROR
            record.detail = describe(record.path, error)

    def search(self, record, name, folder):
        """The outcome of a path that could be read to its end; OSError or Replaced for one that couldn't."""
        # A root is opened by its path, links followed (/root is one); a listed name never through a link.
        handle = os.open(name, os.O_PATH | os.O_CLOEXEC | (os.O_NOFOLLOW if folder is not None else 0), dir_fd=folder)
        try:
            info = os.fstat(handle)
            if folder is not None and info.st_ino != record.inode \
                    and not numbered_otherwise(folder, name, record.inode, info):
                raise Replaced(f'not the file its folder listed (inode {record.inode} there, {info.st_ino} opened): '
                               'replaced before it was read, so its content is unsearched')
            if stat.S_ISREG(info.st_mode):
                found = holds(reopened(handle, os.O_RDONLY), self.needles)
                self.hits += [[record.path, index] for index in sorted(found)]
                return SEARCHED
            if stat.S_ISDIR(info.st_mode):
                # Every name is a record before the first is read: a walk that stops short leaves them unread.
                children = [(self.learn(os.path.join(record.path, child), record.root, inode), child)
                            for child, inode in sorted(listing(handle).items())]
                for child, child_name in children:
                    self.read(child, child_name, handle)
                return LISTED
            return NOT_A_FILE
        finally:
            os.close(handle)

    def answer(self, roots, cover):
        """The scan's whole answer, made from the records: each is counted, and none can be left out."""
        answer = dict(files={root: 0 for root in roots}, hits=self.hits, vanished=[], errors=[], refused={}, covered={},
                      paths=dict(collections.Counter(record.outcome for record in self.records),
                                 learned=len(self.records)))
        met = collections.defaultdict(list)
        for record in self.records:
            met[record.path].append(record)
            if record.outcome == SEARCHED:
                answer['files'][record.root] += 1
            elif record.outcome == GONE:
                answer['vanished'].append(record.path)
                if record.path not in MAY_VANISH:
                    answer['errors'].append(f'{record.path}: gone before it was read, so its content is unsearched')
            elif record.outcome == REFUSED:
                answer['refused'].setdefault(within(record.path, self.handover), []).append(
                    [record.path, record.inode, record.detail])
            elif record.outcome not in SETTLED:
                answer['errors'].append(record.detail or f'{record.path}: learned and never read')
        # What root was refused: covered only if this walk met that path, under the number root's listing gave it
        # (a root of this walk has none), and searched it, listed it or found it not to be a file.
        for path, inode in cover:
            others = [record.inode for record in met[path]
                      if None not in (inode, record.inode) and record.inode != inode]
            if others:
                answer['errors'].append(f'{path}: not the file root was refused (inode {inode} in root\'s listing, '
                                        f'{others[0]} in this one), so that one is unsearched')
            elif met[path] and all(record.outcome in SETTLED for record in met[path]):
                answer['covered'][path] = met[path][0].outcome
        return answer


def scan(roots, needles, handover=(), cover=()):
    """Every regular file at or under the roots, mount points included.

    Returns files (searched, per root), hits ([path, needle number]), vanished (runtime paths gone when they were
    opened), errors (what could not be searched), paths (how many paths the scan learned, and how many ended in each
    outcome), refused ({mount point: [[path, listing's number, refusal]]}: root refused at or under one of the
    handover points, the FUSE mounts whose owners walk them too) and covered ({path: outcome} for the paths in cover,
    [[path, listing's number]], that this walk searched, listed or found not to be a file)."""
    walk = Scan(needles, handover)
    for root in roots:
        walk.read(walk.learn(root, root), root)
    return walk.answer(roots, cover)


if __name__ == '__main__':
    request = json.loads(sys.stdin.read())
    print(json.dumps(scan(request['roots'], [bytes.fromhex(needle) for needle in request['needles']],
                          cover=request['cover'])))
