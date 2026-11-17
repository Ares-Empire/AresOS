"""Package 18c, check 8 (REVIEW-X1 #2): every regular file under some folders searched for byte strings, and an error
for anything that could not be searched, so a scan that couldn't look never passes as clean.

actions.py's passwords() calls scan() as root. FUSE refuses every user but the one who mounted it, root included, so
a FUSE mount under the scanned folders (the document portal's $XDG_RUNTIME_DIR/doc in his session) is left out of
root's walk and walked as its owner instead: `python3 -I tree_scan.py` under runuser, the request on stdin
({"roots": [...], "needles": [hex, ...]}), the result on stdout (paths and needle numbers, never a needle).

One retry, for runtime files only: a file or folder under VANISHING that is gone when the scan reads it (ENOENT: a
running process removed it between the listing and the read) is looked up again. Back again (replaced), it is read
again; still gone, it is skipped and named under "vanished". Anything else that can't be read, a folder that can't
be listed, a vanished path outside VANISHING, or a second failure is an error.
"""
import json
import os
import re
import stat
import sys

# Folders whose files running processes create and remove (systemd, logind, his session, temporary files).
VANISHING = ('/run/', '/tmp/', '/var/tmp/')


def holds(path, needles):
    """Which of the needles (their numbers) the file holds, read in chunks: the Claude Code binary in his home is
    large."""
    found, tail, longest = set(), b'', max(len(needle) for needle in needles)
    with open(path, 'rb') as stream:
        while chunk := stream.read(1 << 20):
            found |= {index for index, needle in enumerate(needles) if needle in tail + chunk}
            tail = chunk[-longest:]
    return found


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


def gone(path, error):
    """The one retry's question: is this a runtime path that a running process removed? Then it is still gone now."""
    if not isinstance(error, FileNotFoundError) or not path.startswith(VANISHING):
        return False
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    return False


def describe(path, error):
    return f'{path}: {type(error).__name__}: {error.strerror or error}'


def scan(roots, needles, prune=()):
    """Every regular file under the roots, without entering the folders in prune (absolute paths).

    Returns files (searched, per root), hits ([path, needle number]), vanished (runtime paths gone twice) and errors
    (what could not be searched)."""
    result = dict(files={}, hits=[], vanished=[], errors=[])
    prune = set(prune)

    def folder_error(error):
        # os.walk's onerror: a folder that could not be listed (the root included).
        if gone(error.filename, error):
            result['vanished'].append(error.filename)
        else:
            result['errors'].append(describe(error.filename, error))

    for root in roots:
        searched = 0
        for folder, folders, names in os.walk(root, onerror=folder_error):
            folders[:] = [name for name in folders if os.path.join(folder, name) not in prune]
            for name in names:
                path = os.path.join(folder, name)
                for attempt in (1, 2):
                    try:
                        if not stat.S_ISREG(os.lstat(path).st_mode):
                            break
                        found = holds(path, needles)
                    except OSError as error:
                        if gone(path, error):
                            result['vanished'].append(path)
                        elif attempt == 1 and isinstance(error, FileNotFoundError) and path.startswith(VANISHING):
                            continue  # replaced between the listing and the read: read the new one
                        else:
                            result['errors'].append(describe(path, error))
                        break
                    searched += 1
                    result['hits'] += [[path, index] for index in sorted(found)]
                    break
        result['files'][root] = searched
    return result


if __name__ == '__main__':
    request = json.loads(sys.stdin.read())
    print(json.dumps(scan(request['roots'], [bytes.fromhex(needle) for needle in request['needles']])))
