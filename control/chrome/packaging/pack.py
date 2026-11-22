"""Pack the extension for one image build: a signed CRX3 and the three files made from its ID.

    python3 control/chrome/packaging/pack.py EXTENSION_FOLDER OUTPUT_FOLDER

writes extension.crx, update.xml, policy.json and native-host.json into
OUTPUT_FOLDER and prints the build's public record as one line of JSON.

Every call makes a new RSA key, signs the package once and forgets the key.
The extension's ID is the hash of the public key, so every build has its own
ID, and the three generated files name it. Nothing keeps a secret: the image
is what the owner trusts, and nothing trusts this key after the build.

The private key stays inside `_sign_with_fresh_key`. It is never returned,
written to a file, printed, logged, or put into the environment or a command
line, and there is no way to pass a key in. Keep it that way: a kept key could
sign a package that Chrome accepts under the same ID.

`payload`, `version` and `render` need only the standard library (the image
check uses them on the runner). Signing needs Python's `cryptography`, which
the image's base has.
"""
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

PACKAGING = Path(__file__).resolve().parent
# Where the image installs the bundle. Chrome reads both addresses from disk.
UPDATE_URL = 'file:///usr/share/aresos/chrome/update.xml'
CRX_URL = 'file:///usr/share/aresos/chrome/extension.crx'
PACKAGE = 'extension.crx'
TEMPLATES = ('update.xml', 'policy.json', 'native-host.json')
PLACEHOLDERS = ('EXTENSION_ID', 'EXTENSION_VERSION', 'UPDATE_URL', 'CRX_URL')
ID = re.compile('[a-p]{32}')
# Chrome's own form: one to four numbers. It goes into update.xml as it stands.
VERSION = re.compile(r'\d{1,5}(\.\d{1,5}){0,3}')


class PackError(ValueError):
    """The folder can't be packed as it is, or the output folder isn't free."""


def _names(folder, prefix=''):
    with os.scandir(folder) as entries:
        for entry in entries:
            name = prefix + entry.name
            # A link could pull a file from outside the reviewed folder into the package.
            if entry.is_symlink():
                raise PackError(name + ': a link; the extension folder may hold only regular files and folders.')
            if entry.is_dir(follow_symlinks=False):
                yield from _names(entry.path, name + '/')
            elif entry.is_file(follow_symlinks=False):
                yield name, entry.path
            else:
                raise PackError(name + ': not a regular file; the extension folder may hold only regular files and folders.')


def _read(name, path):
    try:
        # O_NOFOLLOW and the check on the open file close the gap between listing and reading.
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), 'rb') as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise PackError(name + ': not a regular file.')
            return stream.read()
    except OSError as error:
        raise PackError(f'{name}: {error.strerror or error}') from error


def sources(folder):
    """The folder's files as (name, bytes), sorted by name. Refuses links and special files."""
    try:
        if not stat.S_ISDIR(os.lstat(folder).st_mode):
            raise PackError(f'{folder}: not a folder (a link to one is refused).')
        names = sorted(_names(folder))
    except OSError as error:
        raise PackError(f'{folder}: {error.strerror or error}') from error
    for name, _ in names:
        try:
            name.encode('utf-8')
        except UnicodeError as error:
            raise PackError('A file name in the extension folder is not valid UTF-8.') from error
    return [(name, _read(name, path)) for name, path in names]


def _payload(files):
    return [{'name': name, 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files]


def payload(folder):
    """Each file the package would hold: its name and SHA-256, sorted by name."""
    return _payload(sources(folder))


def _version(files):
    manifest = dict(files).get('manifest.json')
    if manifest is None:
        raise PackError('manifest.json is missing from the extension folder.')
    try:
        value = json.loads(manifest)['version']
    except (ValueError, KeyError, TypeError) as error:
        raise PackError('manifest.json has no readable version.') from error
    if type(value) is not str or not VERSION.fullmatch(value):
        raise PackError('manifest.json: the version must be one to four numbers with dots between them.')
    return value


def version(folder):
    """The extension's version, from its manifest.json."""
    return _version(sources(folder))


def extension_id(public_key):
    """Chrome's ID for a public key (SubjectPublicKeyInfo, DER), as install.mjs's idFor."""
    return ''.join(chr(97 + (byte >> 4)) + chr(97 + (byte & 15)) for byte in hashlib.sha256(public_key).digest()[:16])


def render(extension_id, version):
    """The three generated files for one ID and version, as {name: bytes}."""
    if type(extension_id) is not str or not ID.fullmatch(extension_id):
        raise PackError('Not an extension ID: 32 letters from a to p.')
    if type(version) is not str or not VERSION.fullmatch(version):
        raise PackError('Not an extension version.')
    values = {'EXTENSION_ID': extension_id, 'EXTENSION_VERSION': version, 'UPDATE_URL': UPDATE_URL, 'CRX_URL': CRX_URL}
    result = {}
    for name in TEMPLATES:
        text = (PACKAGING / name).read_text(encoding='utf-8')
        for placeholder in PLACEHOLDERS:
            text = text.replace(placeholder, values[placeholder])
        if any(placeholder in text for placeholder in PLACEHOLDERS):
            raise PackError(name + ': a placeholder is left after rendering.')
        result[name] = text.encode('utf-8')
    return result


def _zip(files):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            # Fixed time, system and mode: the archive says nothing about the build machine.
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def _varint(value):
    result = bytearray()
    while True:
        byte, value = value & 127, value >> 7
        if not value:
            return bytes(result + bytes([byte]))
        result.append(byte | 128)


def _field(number, value):
    """One length-delimited protobuf field."""
    return _varint(number << 3 | 2) + _varint(len(value)) + value


def _sign_with_fresh_key(archive):
    """Make this build's key, sign the archive once, and return public values only.

    The private key is this function's local and nothing else. It is never
    serialized, so no copy of it exists outside the crypto library's own
    memory, which clears the key when the object is freed.
    """
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa
    except ImportError as error:
        raise PackError("Signing needs Python's cryptography (the image's base has it; "
                        'elsewhere install the distribution package, never a pip one).') from error
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    try:
        public_key = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
        # CRX3: the signed header data carries the 16-byte ID, and the proof signs it with the archive.
        signed = _field(1, hashlib.sha256(public_key).digest()[:16])
        signature = key.sign(b'CRX3 SignedData\0' + struct.pack('<I', len(signed)) + signed + archive,
                             padding.PKCS1v15(), hashes.SHA256())
    finally:
        del key
    return public_key, signed, signature


def pack(folder):
    """Pack `folder` under a fresh key. Returns ({file name: bytes}, the public record)."""
    files = sources(folder)
    number = _version(files)
    archive = _zip(files)
    public_key, signed, signature = _sign_with_fresh_key(archive)
    # The container of install.mjs's pack: one RSA proof (field 2), then the signed header data (field 10000).
    header = _field(2, _field(1, public_key) + _field(2, signature)) + _field(10000, signed)
    package = b'Cr24' + struct.pack('<II', 3, len(header)) + header + archive
    identity = extension_id(public_key)
    record = {'id': identity, 'version': number,
              'public_key_sha256': hashlib.sha256(public_key).hexdigest(),
              'crx_sha256': hashlib.sha256(package).hexdigest(),
              'payload': _payload(files)}
    return {PACKAGE: package, **render(identity, number)}, record


def write(folder, output):
    """Pack `folder` and write the four files into `output`, each 0644. Returns the public record."""
    files, record = pack(folder)
    try:
        os.makedirs(output, mode=0o755, exist_ok=True)
        # One build's files never mix with another's: refuse before writing anything.
        present = sorted(name for name in files if os.path.lexists(os.path.join(output, name)))
        if present:
            raise PackError(f'{output} already holds {", ".join(present)}; pack into a folder without them.')
        for name, data in files.items():
            descriptor = os.open(os.path.join(output, name), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o644)
            with os.fdopen(descriptor, 'wb') as stream:
                os.fchmod(stream.fileno(), 0o644)  # whatever the umask is
                stream.write(data)
    except OSError as error:
        raise PackError(f'{output}: {error.strerror or error}') from error
    return record


def main(arguments):
    if len(arguments) != 2:
        print('Usage: python3 control/chrome/packaging/pack.py EXTENSION_FOLDER OUTPUT_FOLDER', file=sys.stderr)
        return 2
    # A crash while the key exists must not leave this process's memory in a core file.
    import resource
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    try:
        record = write(*arguments)
    except PackError as error:
        print('pack.py: ' + str(error), file=sys.stderr)
        return 1
    print(json.dumps(record, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
