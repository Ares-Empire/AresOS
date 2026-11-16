"""Package 18c, B2: does any evidence file hold the per-run fixture password, also inside the evidence's archives?

The checks pack their screens, model requests and transcripts into .tar.gz files (os/ci/control/actions.py), so a
search over the files' raw bytes can't see into them (REVIEW-A1 #5). Every file is searched as it is and, when it is
a gzip stream or a tar archive, member by member. An archive that can't be read counts as holding the password: what
can't be searched can't be published.

Used by control_vm.py after check 8 (scan) and by runner.sh stop (the command below), which first redacts the one
log that is allowed to name the password (GreenMail's: it runs with auth disabled and logs the password it was
given) and then requires every other file, Dovecot's log included, to hold it zero times.

    evidence_scan.py [--redact FILE]... [--remove] PASSWORD_FILE EVIDENCE_FOLDER

Prints one JSON summary line; exits 1 when a file holds the password (removed with --remove), 0 otherwise.
Standard library only, so it runs under python3 -I as root on the runner.
"""
import argparse
import gzip
import io
import json
import pathlib
import sys
import tarfile
import zlib

# Archives inside archives: the evidence has none today; a deeper one is searched as raw bytes only.
DEPTH = 3
# What one archive may unpack to (the evidence artifact stays under 180 MB): anything larger is unreadable.
UNPACKED_LIMIT = 512 * 1024 * 1024
GZIP_MAGIC = b'\x1f\x8b'
REDACTED = '[fixture password redacted]'


class Unreadable(Exception):
    """An archive that could not be opened or unpacked within the limit."""


def gunzip(data):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            inner = stream.read(UNPACKED_LIMIT + 1)
    except (OSError, EOFError, zlib.error) as error:
        raise Unreadable(f'gzip: {error}') from error
    if len(inner) > UNPACKED_LIMIT:
        raise Unreadable(f'gzip: more than {UNPACKED_LIMIT} bytes unpacked')
    return inner


def is_tar(data):
    # A plain tar's first header ends with its magic at offset 257; is_tarfile alone also accepts some junk.
    return len(data) >= 512 and data[257:262] == b'ustar' and tarfile.is_tarfile(io.BytesIO(data))


def contents(data, name, depth=0):
    """(name, bytes) of the data itself and, for a gzip stream or a tar archive, of everything inside it."""
    yield name, data
    if depth >= DEPTH:
        return
    if data[:2] == GZIP_MAGIC:
        yield from contents(gunzip(data), f'{name}!gunzip', depth + 1)
    elif is_tar(data):
        unpacked = 0
        try:
            with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
                for member in archive:
                    if not member.isfile():
                        continue
                    unpacked += member.size
                    if unpacked > UNPACKED_LIMIT:
                        raise Unreadable(f'tar: more than {UNPACKED_LIMIT} bytes unpacked')
                    yield from contents(archive.extractfile(member).read(), f'{name}!{member.name}', depth + 1)
        except tarfile.TarError as error:
            raise Unreadable(f'tar: {error}') from error


def scan(folder, secret):
    """Every regular file under folder, searched for secret as it is and inside its archives.

    Returns files (searched), members (inside archives), hits (file or file!member holding it), unreadable (file:
    reason) and holding (the files under folder that hold it or can't be searched, relative, sorted)."""
    assert len(secret) >= 16, 'not a password'
    folder = pathlib.Path(folder)
    files = members = 0
    hits, unreadable, holding = [], [], set()
    for path in sorted(folder.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        files += 1
        name = str(path.relative_to(folder))
        try:
            for inner, data in contents(path.read_bytes(), name):
                members += inner != name
                if secret in data:
                    hits.append(inner)
                    holding.add(name)
        except Unreadable as error:
            unreadable.append(f'{name}: {error}')
            holding.add(name)
    return dict(files=files, members=members, hits=hits, unreadable=unreadable, holding=sorted(holding))


def redact(path, secret):
    """Replace the password in one text file; returns how often it occurred."""
    path = pathlib.Path(path)
    if not path.exists():
        return None
    text = path.read_bytes()
    count = text.count(secret)
    if count:
        path.write_bytes(text.replace(secret, REDACTED.encode()))
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[0])
    parser.add_argument('--redact', action='append', default=[], help='a file allowed to name the password')
    parser.add_argument('--remove', action='store_true', help='delete every file that holds it')
    parser.add_argument('password_file')
    parser.add_argument('folder')
    options = parser.parse_args(argv)
    secret = pathlib.Path(options.password_file).read_bytes().strip()
    redacted = {pathlib.Path(name).name: redact(name, secret) for name in options.redact}
    found = scan(options.folder, secret)
    if options.remove:
        for name in found['holding']:
            (pathlib.Path(options.folder) / name).unlink()
    print(json.dumps(dict(redacted=redacted, removed=found['holding'] if options.remove else [], **found),
                     sort_keys=True))
    return 1 if found['holding'] else 0


if __name__ == '__main__':
    sys.exit(main())
