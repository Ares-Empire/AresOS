"""Package 18c, B2: does any evidence file hold the per-run fixture password, also inside the evidence's archives?

The checks pack their screens, model requests and transcripts into .tar.gz files (os/ci/control/actions.py), so a
search over the files' raw bytes can't see into them (REVIEW-A1 #5). Every file is searched as it is and, when it is
a gzip stream or a tar archive, member by member. An archive that can't be read counts as holding the password: what
can't be searched can't be published. That includes (REVIEW-X1 #3) a gzip stream or tar archive nested deeper than
DEPTH, a tar whose headers stop before its end (a bad checksum, a truncated header: tarfile ends such an archive
quietly), and data in a compressed or archive format this scan doesn't unpack (xz, bzip2, zstd, lz4, zip, 7z).

A tar is any data whose first block tarfile reads as a header (RECHECK-X1 #3): tarfile reads V7 tars, which carry no
magic, and a ustar header with other version bytes, so the magic alone missed archives it can read. A first block
with the POSIX or GNU magic is a tar too, so a damaged one is unreadable rather than searched as plain bytes. Every
member tarfile hands out as a file is searched: regular files, and members of a type it doesn't know, which it
treats as regular files.

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
import re
import sys
import tarfile
import zlib

# Archives inside archives: the evidence has none today (a .tar.gz is two levels, gzip then tar); anything still
# compressed or archived below this depth is unreadable, never searched as raw bytes only.
DEPTH = 3
# What one archive may unpack to (the evidence artifact stays under 180 MB): anything larger is unreadable.
UNPACKED_LIMIT = 512 * 1024 * 1024
GZIP_MAGIC = b'\x1f\x8b'
# A POSIX or GNU tar header's magic at offset 257, which a header with a bad checksum still has: POSIX's "ustar\0"
# whatever its two version bytes (tarfile reads "01" as well as "00"), GNU's "ustar  \0". Each holds a NUL, so no
# text line does.
TAR_MAGICS = (tarfile.POSIX_MAGIC[:6], tarfile.GNU_MAGIC)
# Formats this scan recognises but doesn't unpack: their content would only be searched compressed.
NOT_UNPACKED = [(re.compile(rb'\xfd7zXZ\x00'), 'xz'), (re.compile(rb'BZh[1-9](1AY&SY|\x17rE8P\x90)'), 'bzip2'),
                (re.compile(rb'\x28\xb5\x2f\xfd'), 'zstd'), (re.compile(rb'\x04\x22\x4d\x18'), 'lz4'),
                (re.compile(rb'PK(\x03\x04|\x05\x06|\x07\x08)'), 'zip'), (re.compile(rb"7z\xbc\xaf'\x1c"), '7z')]
REDACTED = '[fixture password redacted]'


class Unreadable(Exception):
    """An archive that could not be opened, unpacked within the limit, or searched to its end."""


def gunzip(data):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            inner = stream.read(UNPACKED_LIMIT + 1)
    except (OSError, EOFError, zlib.error) as error:
        raise Unreadable(f'gzip: {error}') from error
    if len(inner) > UNPACKED_LIMIT:
        raise Unreadable(f'gzip: more than {UNPACKED_LIMIT} bytes unpacked')
    return inner


def tar_header(block):
    """Does tarfile read this first block as a header? Its own test: the checksum, and numbers where numbers go."""
    try:
        tarfile.TarInfo.frombuf(block, 'utf-8', 'surrogateescape')
    except tarfile.HeaderError:
        return False
    return True


def kind(data):
    """'gzip', 'tar', the name of a format this scan doesn't unpack, or None for data to search as it is."""
    if data[:2] == GZIP_MAGIC:
        return 'gzip'
    if data.startswith(TAR_MAGICS, 257) or tar_header(data[:tarfile.BLOCKSIZE]):
        return 'tar'
    return next((name for pattern, name in NOT_UNPACKED if pattern.match(data)), None)


def untar(data, name, depth):
    """Every regular member of a tar archive; the archive must parse to its end, where only zero blocks follow."""
    unpacked = 0
    try:
        with tarfile.open(fileobj=io.BytesIO(data), mode='r:') as archive:
            for member in archive:
                # What extractfile() hands out as a file: a regular one, or one of a type tarfile doesn't know.
                if not member.isfile() and member.type in tarfile.SUPPORTED_TYPES:
                    continue
                unpacked += member.size
                if unpacked > UNPACKED_LIMIT:
                    raise Unreadable(f'tar: more than {UNPACKED_LIMIT} bytes unpacked')
                yield from contents(archive.extractfile(member).read(), f'{name}!{member.name}', depth + 1)
            # tarfile stops at the first header it can't read past the first one, as if the archive ended there.
            if data[archive.offset:].strip(b'\0'):
                raise Unreadable(f'tar: a header at byte {archive.offset} could not be read; the rest is unsearched')
    except tarfile.TarError as error:
        raise Unreadable(f'tar: {error}') from error


def contents(data, name, depth=0):
    """(name, bytes) of the data itself and, for a gzip stream or a tar archive, of everything inside it."""
    yield name, data
    found = kind(data)
    if found is None:
        return
    if depth >= DEPTH:
        raise Unreadable(f'{found} nested deeper than {DEPTH} levels')
    if found == 'gzip':
        yield from contents(gunzip(data), f'{name}!gunzip', depth + 1)
    elif found == 'tar':
        yield from untar(data, name, depth)
    else:
        raise Unreadable(f'{found} data, which this scan does not unpack')


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
