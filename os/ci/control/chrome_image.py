"""18c-b's independent image checks; never installed in the production image.

check-image.sh mounts this read-only in its check container. The runner uses
the same streaming key scan for build.log. Only `image` needs cryptography;
`compare` imports the packer's stdlib payload/template readers, never signs.
"""
import base64
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import xml.etree.ElementTree as ET
import zipfile

BUNDLE = '/usr/share/aresos/chrome'
NAMES = ('extension.crx', 'native-host.json', 'policy.json', 'update.xml')
LINKS = {
    '/etc/opt/chrome/policies/managed/aresos.json': BUNDLE + '/policy.json',
    '/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json': BUNDLE + '/native-host.json',
}
ACTION = 'org.aresos.control.chrome-loosen'
PLACEHOLDERS = (b'EXTENSION_ID', b'EXTENSION_VERSION', b'UPDATE_URL', b'CRX_URL')
PRIVATE = re.compile(rb'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fields(data):
    """Read bounded, length-delimited protobuf fields without the packer's code."""
    offset = 0

    def varint():
        nonlocal offset
        value = 0
        for shift in range(0, 70, 7):
            assert offset < len(data), 'truncated protobuf integer'
            byte = data[offset]
            offset += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
        raise AssertionError('oversized protobuf integer')

    result = []
    while offset < len(data):
        tag, size = varint(), varint()
        assert tag & 7 == 2 and offset + size <= len(data), 'invalid protobuf field'
        result.append((tag >> 3, data[offset:offset + size]))
        offset += size
    return result


def crx(data, record):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    assert data[:8] == b'Cr24\x03\0\0\0' and len(data) >= 12, 'not CRX3'
    size = struct.unpack_from('<I', data, 8)[0]
    assert 0 < size < len(data) - 12, 'invalid CRX3 header length'
    header = fields(data[12:12 + size])
    assert [tag for tag, _ in header] == [2, 10000], 'expected exactly one RSA proof'
    proof, signed = fields(header[0][1]), header[1][1]
    assert [tag for tag, _ in proof] == [1, 2], 'expected public key and signature'
    public, signature = (value for _, value in proof)
    key = serialization.load_der_public_key(public)
    assert isinstance(key, rsa.RSAPublicKey) and key.key_size == 2048 and key.public_numbers().e == 65537
    identity = hashlib.sha256(public).digest()[:16]
    assert fields(signed) == [(1, identity)], 'signed ID differs from public key'
    archive = data[12 + size:]
    key.verify(signature, b'CRX3 SignedData\0' + struct.pack('<I', len(signed)) + signed + archive,
               padding.PKCS1v15(), hashes.SHA256())
    extension_id = ''.join('abcdefghijklmnop'[n] for byte in identity for n in (byte >> 4, byte & 15))
    assert record['id'] == extension_id, 'recorded extension ID differs'
    assert record['public_key_sha256'] == digest(public), 'recorded public key differs'
    assert record['crx_sha256'] == digest(data), 'recorded CRX hash differs'
    with zipfile.ZipFile(io.BytesIO(archive)) as packed:
        names = packed.namelist()
        assert names == sorted(set(names)), 'duplicate or unsorted zip members'
        assert all(name and not name.startswith('/') and not {'', '.', '..'} & set(name.split('/')) for name in names)
        assert all(stat.S_ISREG(info.external_attr >> 16) for info in packed.infolist()), 'non-file zip member'
        payload = [{'name': name, 'sha256': digest(packed.read(name))} for name in names]
        assert payload == record['payload'], 'CRX payload differs from record'
        assert json.loads(packed.read('manifest.json'))['version'] == record['version'], 'CRX version differs'
        for name in names:
            assert not PRIVATE.search(packed.read(name)), 'private key marker in CRX payload'
            assert not any(token in packed.read(name) for token in PLACEHOLDERS), 'template token in CRX payload'
    return key.public_numbers().n.to_bytes(256, 'big')


def bundle_content(files, record):
    assert set(files) == set(NAMES), 'unexpected bundle files'
    assert set(record) == {'id', 'version', 'public_key_sha256', 'crx_sha256', 'payload', 'files'}
    assert record['files'] == {BUNDLE + '/' + name: {'mode': '0644', 'sha256': digest(data)}
                               for name, data in files.items()}, 'bundle bytes/modes differ from record'
    for name, data in files.items():
        assert not any(token in data for token in PLACEHOLDERS), f'unrendered template: {name}'
    modulus = crx(files['extension.crx'], record)
    identity, version = record['id'], record['version']
    assert json.loads(files['policy.json']) == {'ExtensionSettings': {identity: {
        'installation_mode': 'force_installed', 'update_url': 'file://' + BUNDLE + '/update.xml',
        'override_update_url': True, 'toolbar_pin': 'force_pinned'}}}, 'unexpected Chrome policy'
    assert json.loads(files['native-host.json']) == {
        'name': 'org.aresos.chrome', 'description': 'AresOS Chrome relay',
        'path': '/usr/libexec/aresos-control/chrome/host', 'type': 'stdio',
        'allowed_origins': ['chrome-extension://' + identity + '/']}, 'unexpected native host manifest'
    ns = '{http://www.google.com/update2/response}'
    update = ET.fromstring(files['update.xml'])
    assert update.tag == ns + 'gupdate' and update.attrib == {'protocol': '2.0'} and len(update) == 1
    app = update[0]
    assert app.tag == ns + 'app' and app.attrib == {'appid': identity} and len(app) == 1
    check = app[0]
    assert check.tag == ns + 'updatecheck' and not len(check) and check.attrib == {
        'codebase': 'file://' + BUNDLE + '/extension.crx', 'version': version}
    return modulus


def forms(value):
    # Trim partial leading/trailing base64 quanta: each form then occurs even
    # when the modulus starts at any offset in a DER key. HEX may be uppercase.
    digits = value.hex()[2:]
    values = {value, digits.encode(), digits.upper().encode()}
    for encode in (base64.b64encode, base64.urlsafe_b64encode):
        for shift in range(3):
            padded = b'\0' * shift + value
            text = encode(padded[:len(padded) - len(padded) % 3])
            values.add(text[4:] if shift else text)
    return sorted(values)


def hits(path, needles, chunk_size=1024 * 1024):
    """All (needle, offset) hits, including raw newlines and chunk boundaries.

    Also search a whitespace-free view for wrapped PEM/base64 or hex dumps.
    The two views are separate: the caller counts the raw CRX occurrence and
    rejects any hit at another path, without double-counting the views.
    """
    overlap = max(map(len, needles)) - 1
    tails, offsets, found = [b'', b''], [0, 0], set()
    with path.open('rb') as stream:
        while chunk := stream.read(chunk_size):
            for view, part in enumerate((chunk, chunk.translate(None, b' \t\r\n\v\f'))):
                block = tails[view] + part
                start = offsets[view] - len(tails[view])
                for index, needle in enumerate(needles):
                    pos = block.find(needle)
                    while pos >= 0:
                        found.add((view, index, start + pos))
                        pos = block.find(needle, pos + 1)
                offsets[view] += len(part)
                tails[view] = block[-overlap:]
    return found


def regular_files(root, excluded=()):
    """No symlink traversal, no ignored read/list failures, no special files."""
    def visit(folder):
        with os.scandir(folder) as entries:
            for entry in entries:
                path = Path(entry.path)
                if path in excluded:
                    continue
                if entry.is_dir(follow_symlinks=False):
                    yield from visit(path)
                elif entry.is_file(follow_symlinks=False):
                    yield path
    yield from visit(root)


def private_markers(path):
    tail = b''
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            data = tail + chunk
            assert not PRIVATE.search(data), f'private key marker: {path}'
            tail = data[-256:]


def owned(path, mode, directory=False):
    info = path.lstat()
    assert (stat.S_ISDIR if directory else stat.S_ISREG)(info.st_mode), path
    assert stat.S_IMODE(info.st_mode) == mode, (str(path), oct(info.st_mode))
    for part in (path, *path.parents):
        info = part.lstat()
        assert (info.st_uid, info.st_gid) == (0, 0) and not info.st_mode & 0o022, part
        assert not stat.S_ISLNK(info.st_mode), part


def image(scan_root):
    record = json.loads(Path('/usr/share/aresos/manifest/control.json').read_bytes())
    extension = record['chrome_extension']
    folder = Path(BUNDLE)
    owned(folder, 0o755, directory=True)
    assert sorted(p.name for p in folder.iterdir()) == sorted(NAMES), 'extra bundle or probe'
    assert sorted(p.name for p in folder.parent.glob('chrome*')) == ['chrome'], 'second Chrome bundle or probe folder'
    for name in NAMES:
        owned(folder / name, 0o644)
    modulus = bundle_content({name: (folder / name).read_bytes() for name in NAMES}, extension)
    assert re.fullmatch('[0-9a-f]{64}', record['chrome_build'])
    assert json.loads(Path('/usr/libexec/aresos-control/chrome/build-id.json').read_bytes()) == {
        'build': record['chrome_build']}
    for name, target in LINKS.items():
        path = Path(name)
        assert path.is_symlink() and os.readlink(path) == target and record['links'][name] == target, name
        assert (path.lstat().st_uid, path.lstat().st_gid) == (0, 0), name
        for parent in path.parents:
            owned(parent, 0o755, directory=True)
    assert sorted(p.name for p in Path('/etc/opt/chrome/policies/managed').iterdir()) == ['aresos.json']
    # Keep the base's KDE host; no probe, second AresOS host or separate policy.
    for path in regular_files(Path('/etc/opt/chrome')):
        assert b'aresos' not in path.read_bytes().lower(), f'additional AresOS policy or host: {path}'
    assert not any(Path('/etc/opt/chrome/policies/recommended').glob('*'))
    code = Path('/usr/libexec/aresos-control/chrome')
    assert sorted(p.name for p in code.iterdir()) == ['build-id.json', 'host', 'native_host.py', 'qualification.json']
    # The caller binds / non-recursively here: podman's /etc/hosts and the
    # checker mount must not hide an image file from either key scan.
    for path in (scan_root / name.lstrip('/') for name in (*record['files'], *extension['files'])):
        private_markers(path)
        assert not any(token in path.read_bytes() for token in PLACEHOLDERS), f'unrendered template: {path}'
    for name in ('tmp', 'var/tmp', 'root'):
        for path in regular_files(scan_root / name):
            private_markers(path)
    needles = forms(modulus)
    matches = {}
    for path in regular_files(scan_root, excluded=tuple(scan_root / name for name in ('proc', 'sys', 'dev'))):
        found = hits(path, needles)
        if found:
            matches['/' + path.relative_to(scan_root).as_posix()] = found
    assert set(matches) == {BUNDLE + '/extension.crx'}, f'public modulus outside CRX: {sorted(matches)}'
    raw_hits = [hit for hit in matches[BUNDLE + '/extension.crx'] if hit[:2] == (0, needles.index(modulus))]
    assert len(raw_hits) == 1, 'modulus must occur exactly once in CRX'
    print('CONTROL_CHROME_PUBLIC_MODULUS', modulus.hex())
    print('CONTROL_CHROME_BUNDLE_PASS', extension['id'], extension['crx_sha256'])
    print('CONTROL_CHROME_KEY_SCAN_PASS')


def compare(image_record, expected, control):
    assert image_record['chrome_build'] == expected['chrome_build'], 'Chrome build differs from checkout'
    assert image_record['links'] == expected['links'], 'Control links differ from checkout'
    spec = importlib.util.spec_from_file_location('chrome_pack', control / 'chrome/packaging/pack.py')
    pack = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pack)
    record = image_record['chrome_extension']
    assert set(record) == {'id', 'version', 'public_key_sha256', 'crx_sha256', 'payload', 'files'}
    assert re.fullmatch('[a-p]{32}', record['id'])
    assert all(re.fullmatch('[0-9a-f]{64}', record[key]) for key in ('public_key_sha256', 'crx_sha256'))
    assert record['payload'] == pack.payload(control / 'chrome/extension'), 'payload differs from checkout'
    assert record['version'] == pack.version(control / 'chrome/extension'), 'version differs from checkout'
    rendered = pack.render(record['id'], record['version'])
    expected_files = {BUNDLE + '/' + name: {'mode': '0644', 'sha256': digest(data)} for name, data in rendered.items()}
    expected_files[BUNDLE + '/extension.crx'] = {'mode': '0644', 'sha256': record['crx_sha256']}
    assert record['files'] == expected_files, 'generated files differ from checkout templates'
    print('CONTROL_CHROME_CHECKOUT_PASS', image_record['chrome_build'], record['id'])


def build_log(checks, log):
    lines = re.findall(r'^CONTROL_CHROME_PUBLIC_MODULUS ([0-9a-f]{512})$', checks.read_text(), re.M)
    assert len(lines) == 1, 'expected one checked public modulus'
    assert not hits(log, forms(bytes.fromhex(lines[0]))), 'public modulus in build log'
    private_markers(log)
    print('CONTROL_CHROME_BUILD_LOG_PASS')


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[1] == 'image':
        image(Path(sys.argv[2]))
    elif len(sys.argv) == 5 and sys.argv[1] == 'compare':
        compare(json.loads(Path(sys.argv[2]).read_bytes()), json.loads(Path(sys.argv[3]).read_bytes()), Path(sys.argv[4]))
    elif len(sys.argv) == 4 and sys.argv[1] == 'build-log':
        build_log(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        raise SystemExit('expected image SCAN_ROOT, compare IMAGE_RECORD EXPECTED_RECORD CONTROL, or build-log CHECKS LOG')
