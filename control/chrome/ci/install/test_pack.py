"""pack.py: the per-build package and the three generated files (brief 18c-b, item 1).

Run: python3 -m unittest discover -s control/chrome/ci/install -p 'test_*.py'
It needs Python's `cryptography` (a distribution package in the container).
The reader below is the test's own, so the packer isn't checked with itself.
No key is ever a fixture: every key here is made in memory by the packer.
"""
import base64
import hashlib
import inspect
import io
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import patch
from xml.etree import ElementTree
import zipfile

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

ROOT = Path(__file__).resolve().parents[4]
PACKAGING = ROOT / 'control/chrome/packaging'
EXTENSION = ROOT / 'control/chrome/extension'
sys.path.insert(0, str(PACKAGING))
import pack

WORK = ROOT / '.work/18c-b-chrome'; WORK.mkdir(parents=True, exist_ok=True)
NAMES = ['extension.crx', 'native-host.json', 'policy.json', 'update.xml']
PRIVATE_MARKER = re.compile(rb'-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----')


def fields(data):
    """A protobuf message of length-delimited fields as [(number, bytes)]."""
    result, offset = [], 0
    def varint():
        nonlocal offset
        value = shift = 0
        while True:
            byte = data[offset]; offset += 1
            value |= (byte & 127) << shift; shift += 7
            if byte < 128: return value
    while offset < len(data):
        tag = varint(); length = varint()
        assert tag & 7 == 2, 'only length-delimited fields are expected'
        result.append((tag >> 3, data[offset:offset + length])); offset += length
    assert offset == len(data)
    return result


def read_crx(package):
    """The parts of a CRX3 file with exactly one RSA proof; fails on anything else."""
    assert package[:4] == b'Cr24' and struct.unpack('<I', package[4:8])[0] == 3
    size = struct.unpack('<I', package[8:12])[0]
    header, archive = fields(package[12:12 + size]), package[12 + size:]
    assert [number for number, _ in header] == [2, 10000], 'one RSA proof, then the signed header data'
    proof = fields(header[0][1])
    assert [number for number, _ in proof] == [1, 2], 'a public key and a signature'
    signed = header[1][1]
    assert [number for number, _ in fields(signed)] == [1]
    return {'public_key': proof[0][1], 'signature': proof[1][1], 'signed': signed, 'crx_id': fields(signed)[0][1], 'archive': archive}


def chrome_id(public_key):
    # install.mjs's idFor, written out again.
    return ''.join('abcdefghijklmnop'[nibble] for byte in hashlib.sha256(public_key).digest()[:16] for nibble in (byte >> 4, byte & 15))


def forms(value):
    """The ways a number's bytes show up in a stored key: raw, hex, base64 and base64url at each alignment."""
    # Without the first byte's digits: a printed number may drop a leading zero.
    digits = value.hex()[2:]
    result = [value, digits.encode(), digits.upper().encode()]
    for encode in (base64.b64encode, base64.urlsafe_b64encode):
        for shift in range(3):
            padded = b'\0' * shift + value
            text = encode(padded[:len(padded) - len(padded) % 3])
            result.append(text[4:] if shift else text)
    return result


def number(value):
    return value.to_bytes((value.bit_length() + 7) // 8, 'big')


def tree(folder):
    return {str(path.relative_to(folder)): path.read_bytes() for path in sorted(Path(folder).rglob('*')) if path.is_file()}


class Scratch(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=WORK)
        self.work = Path(self.temp.name)
        self.addCleanup(self.temp.cleanup)

    def extension(self, files=None):
        folder = self.work / 'extension'; folder.mkdir()
        for name, data in (files or {'manifest.json': b'{"manifest_version":3,"name":"Synthetic","version":"2.5.0.7"}',
                                     'background.js': b'// nothing\n', 'pages/one.html': b'<p>one</p>\n', 'pages/deep/two.js': bytes(range(256))}).items():
            (folder / name).parent.mkdir(parents=True, exist_ok=True)
            (folder / name).write_bytes(data)
        return folder


class Package(Scratch):
    def test_the_package_is_crx3_signed_by_its_own_key_under_the_id_of_that_key(self):
        files, record = pack.pack(EXTENSION)
        self.assertEqual(sorted(files), NAMES)
        crx = read_crx(files['extension.crx'])
        key = serialization.load_der_public_key(crx['public_key'])
        self.assertIsInstance(key, rsa.RSAPublicKey)
        self.assertEqual((key.key_size, key.public_numbers().e), (2048, 65537))
        signed = b'CRX3 SignedData\0' + struct.pack('<I', len(crx['signed'])) + crx['signed'] + crx['archive']
        key.verify(crx['signature'], signed, padding.PKCS1v15(), hashes.SHA256())  # raises on a bad signature
        self.assertEqual(crx['crx_id'], hashlib.sha256(crx['public_key']).digest()[:16])
        self.assertEqual(record['id'], chrome_id(crx['public_key']))
        self.assertRegex(record['id'], '^[a-p]{32}$')
        self.assertEqual(record['public_key_sha256'], hashlib.sha256(crx['public_key']).hexdigest())
        self.assertEqual(record['crx_sha256'], hashlib.sha256(files['extension.crx']).hexdigest())
        self.assertEqual(sorted(record), ['crx_sha256', 'id', 'payload', 'public_key_sha256', 'version'])
        # One changed byte of the archive no longer verifies: the signature covers the files.
        with self.assertRaises(Exception):
            key.verify(crx['signature'], signed[:-1] + bytes([signed[-1] ^ 1]), padding.PKCS1v15(), hashes.SHA256())

    def test_the_packed_files_equal_the_sources_byte_for_byte(self):
        for folder in [EXTENSION, self.extension()]:
            with self.subTest(folder=folder.name):
                files, record = pack.pack(folder)
                expected = tree(folder)
                with zipfile.ZipFile(io.BytesIO(read_crx(files['extension.crx'])['archive'])) as archive:
                    self.assertIsNone(archive.testzip())
                    self.assertEqual(archive.namelist(), sorted(expected))
                    self.assertEqual({name: archive.read(name) for name in archive.namelist()}, expected)
                    self.assertEqual({info.date_time for info in archive.infolist()}, {(1980, 1, 1, 0, 0, 0)})
                self.assertEqual(record['payload'], [{'name': name, 'sha256': hashlib.sha256(expected[name]).hexdigest()} for name in sorted(expected)])
                self.assertEqual(record['payload'], pack.payload(folder))
                self.assertEqual(record['version'], json.loads(expected['manifest.json'])['version'])
                self.assertEqual(record['version'], pack.version(folder))

    def test_two_calls_give_two_identities_for_the_same_files(self):
        (first, one), (second, two) = pack.pack(EXTENSION), pack.pack(EXTENSION)
        self.assertNotEqual(one['id'], two['id'])
        self.assertNotEqual(one['public_key_sha256'], two['public_key_sha256'])
        self.assertNotEqual(first['extension.crx'], second['extension.crx'])
        self.assertEqual(one['payload'], two['payload'])
        self.assertEqual(read_crx(first['extension.crx'])['archive'], read_crx(second['extension.crx'])['archive'])

    def test_the_generated_files_name_one_id_and_nothing_else(self):
        files, record = pack.pack(self.extension())
        identity = record['id']
        self.assertEqual(json.loads(files['policy.json']), {'ExtensionSettings': {identity: {
            'installation_mode': 'force_installed', 'update_url': 'file:///usr/share/aresos/chrome/update.xml',
            'override_update_url': True, 'toolbar_pin': 'force_pinned'}}})
        self.assertEqual(json.loads(files['native-host.json']), {
            'name': 'org.aresos.chrome', 'description': 'AresOS Chrome relay', 'path': '/usr/libexec/aresos-control/chrome/host',
            'type': 'stdio', 'allowed_origins': [f'chrome-extension://{identity}/']})
        update = ElementTree.fromstring(files['update.xml'])
        space = '{http://www.google.com/update2/response}'
        self.assertEqual((update.tag, update.attrib), (space + 'gupdate', {'protocol': '2.0'}))
        self.assertEqual([(app.tag, app.attrib) for app in update], [(space + 'app', {'appid': identity})])
        self.assertEqual([(check.tag, check.attrib) for check in update[0]], [(space + 'updatecheck', {
            'codebase': 'file:///usr/share/aresos/chrome/extension.crx', 'version': '2.5.0.7'})])
        generated = {name: data for name, data in files.items() if name != 'extension.crx'}
        # What the image check compares: the templates rendered again with the recorded ID.
        self.assertEqual(generated, pack.render(identity, record['version']))
        for name, data in generated.items():
            with self.subTest(name=name):
                self.assertEqual(data.count(identity.encode()), 1)
                self.assertEqual(re.findall(rb'[a-p]{32}', data), [identity.encode()])
                for placeholder in [b'EXTENSION_ID', b'EXTENSION_VERSION', b'UPDATE_URL', b'CRX_URL']:
                    self.assertNotIn(placeholder, data)

    def test_render_refuses_what_is_not_an_id_or_a_version(self):
        for identity, version in [('a' * 31, '1.0'), ('q' * 32, '1.0'), ('a' * 32 + '"', '1.0'), ('a' * 32, '1.0"/><x a="'), ('a' * 32, ''), ('a' * 32, '1.2.3.4.5'), (None, '1')]:
            with self.subTest(identity=identity, version=version), self.assertRaises(pack.PackError):
                pack.render(identity, version)

    def test_a_link_or_a_special_file_in_the_folder_is_refused(self):
        outside = self.work / 'outside.js'; outside.write_bytes(b'// not reviewed\n')
        def link_to_file(folder): (folder / 'extra.js').symlink_to(outside)
        def link_to_folder(folder): (folder / 'more').symlink_to(self.work, target_is_directory=True)
        def link_inside(folder): (folder / 'pages/again.html').symlink_to('one.html')
        def dangling(folder): (folder / 'gone.js').symlink_to(self.work / 'missing')
        def pipe(folder): os.mkfifo(folder / 'pages/pipe')
        for change in [link_to_file, link_to_folder, link_inside, dangling, pipe]:
            with self.subTest(change=change.__name__):
                folder = self.extension()
                try:
                    pack.pack(folder)  # packs before the change
                    change(folder)
                    for call in [pack.pack, pack.payload, pack.version]:
                        with self.assertRaises(pack.PackError):
                            call(folder)
                    with self.assertRaises(pack.PackError):
                        pack.write(folder, self.work / 'out')
                    self.assertFalse((self.work / 'out').exists())
                finally:
                    subprocess.run(['rm', '-rf', str(folder)], check=True)
        folder = self.extension()
        (self.work / 'alias').symlink_to(folder, target_is_directory=True)
        for target in [self.work / 'alias', self.work / 'missing', outside]:
            with self.subTest(target=target.name), self.assertRaises(pack.PackError):
                pack.pack(target)

    def test_a_folder_without_a_usable_manifest_is_refused(self):
        for manifest in [None, b'not json', b'[]', b'{"name":"x"}', b'{"version":1}', b'{"version":"1.0-beta"}', b'{"version":"1.0\\" codebase=\\"x"}']:
            with self.subTest(manifest=manifest):
                folder = self.extension({'background.js': b'//\n', **({} if manifest is None else {'manifest.json': manifest})})
                try:
                    with self.assertRaises(pack.PackError):
                        pack.pack(folder)
                finally:
                    subprocess.run(['rm', '-rf', str(folder)], check=True)


class NoKeyLeft(Scratch):
    def test_there_is_no_way_to_pass_a_key_in(self):
        self.assertEqual(list(inspect.signature(pack.pack).parameters), ['folder'])
        self.assertEqual(list(inspect.signature(pack.write).parameters), ['folder', 'output'])
        self.assertEqual(list(inspect.signature(pack._sign_with_fresh_key).parameters), ['archive'])

    def test_signing_does_not_open_any_named_file_for_writing(self):
        # Audit hooks live for the life of the interpreter, so scope this one to a child.
        program = textwrap.dedent('''\
            import os
            import sys

            sys.path.insert(0, sys.argv[1])
            import pack

            writes = []
            write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC

            def audit(event, args):
                if event == 'open':
                    path, _, flags = args
                    if not isinstance(path, int) and flags & write_flags:
                        writes.append(path)

            sys.addaudithook(audit)
            pack._sign_with_fresh_key(b'synthetic archive')
            assert not writes, 'named file opened for writing while signing'
        ''')
        done = subprocess.run([sys.executable, '-I', '-B', '-c', program, str(PACKAGING)],
                              cwd=self.work, env={**os.environ, 'TMPDIR': str(self.work)},
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(done.returncode, 0, done.stderr)

    def test_no_private_key_in_what_is_returned_written_or_left_behind(self):
        made = []
        generate = rsa.generate_private_key
        def spy(*args, **kwargs):
            made.append(generate(*args, **kwargs)); return made[-1]
        temporary = self.work / 'tmp'; temporary.mkdir()
        output = self.work / 'out'
        folder = self.extension()
        before = tree(self.work)
        with patch.object(rsa, 'generate_private_key', spy), patch.object(tempfile, 'tempdir', str(temporary)), patch.dict(os.environ, {'TMPDIR': str(temporary)}):
            environment = dict(os.environ)
            files, record = pack.pack(folder)
            written = pack.write(folder, output)
            self.assertEqual(dict(os.environ), environment)
        self.assertEqual(len(made), 2, 'one fresh key for each call')
        self.assertEqual(list(temporary.iterdir()), [])
        self.assertEqual(sorted(path.name for path in output.iterdir()), NAMES)
        self.assertEqual({path.name: path.stat().st_mode & 0o7777 for path in output.iterdir()}, dict.fromkeys(NAMES, 0o644))
        # Nothing appeared beside the output folder, and the sources are untouched.
        self.assertEqual({name: data for name, data in tree(self.work).items() if not name.startswith('out/')}, before)
        returned = json.dumps(record).encode() + b''.join(files.values()) + repr((files, record)).encode()
        on_disk = json.dumps(written).encode() + b''.join(tree(self.work).values())
        for where, haystack in [('a returned value', returned), ('a file', on_disk)]:
            self.assertIsNone(PRIVATE_MARKER.search(haystack), 'A private-key marker is in ' + where)
            for key in made:
                secret = key.private_numbers()
                for part in [secret.p, secret.q, secret.d, secret.dmp1, secret.dmq1, secret.iqmp]:
                    # Never print the number: the message names the place only.
                    self.assertFalse(any(form in haystack or form in haystack.replace(b'\n', b'') for form in forms(number(part))),
                                     'Part of a private key is in ' + where)
        # The scan can see a key: the public modulus is in each package, once, and nowhere else.
        for key, package, others in [(made[0], files['extension.crx'], [data for name, data in files.items() if name != 'extension.crx']),
                                     (made[1], (output / 'extension.crx').read_bytes(), [(output / name).read_bytes() for name in NAMES[1:]])]:
            modulus = number(key.public_key().public_numbers().n)
            self.assertEqual(package.count(modulus), 1)
            self.assertEqual(sum(form in package for form in forms(modulus)), 1)
            for other in others:
                self.assertFalse(any(form in other for form in forms(modulus)))

    def test_the_command_writes_four_files_and_prints_only_the_public_record(self):
        temporary = self.work / 'tmp'; temporary.mkdir()
        current = self.work / 'cwd'; current.mkdir()
        output = self.work / 'out'
        environment = {'PATH': '/usr/bin:/bin', 'TMPDIR': str(temporary), 'HOME': str(current), 'PYTHONDONTWRITEBYTECODE': '1'}
        def run(*arguments):
            return subprocess.run([sys.executable, str(PACKAGING / 'pack.py'), *arguments], cwd=current, env=environment, capture_output=True, timeout=120)
        done = run(str(EXTENSION), str(output))
        self.assertEqual((done.returncode, done.stderr), (0, b''))
        self.assertEqual(done.stdout.count(b'\n'), 1)
        record = json.loads(done.stdout)
        self.assertEqual(sorted(record), ['crx_sha256', 'id', 'payload', 'public_key_sha256', 'version'])
        self.assertEqual(sorted(path.name for path in output.iterdir()), NAMES)
        self.assertEqual({path.name: path.stat().st_mode & 0o7777 for path in output.iterdir()}, dict.fromkeys(NAMES, 0o644))
        self.assertEqual(list(temporary.iterdir()) + list(current.iterdir()), [])
        package = (output / 'extension.crx').read_bytes()
        crx = read_crx(package)
        self.assertEqual(record['crx_sha256'], hashlib.sha256(package).hexdigest())
        self.assertEqual(record['id'], chrome_id(crx['public_key']))
        self.assertEqual(json.loads((output / 'policy.json').read_bytes())['ExtensionSettings'].keys(), {record['id']})
        everything = done.stdout + b''.join(tree(self.work).values())
        self.assertIsNone(PRIVATE_MARKER.search(everything))
        modulus = number(serialization.load_der_public_key(crx['public_key']).public_numbers().n)
        self.assertEqual(sum(everything.count(form) for form in forms(modulus)), 1, 'the public modulus is in the package and nowhere else')
        # A second build never mixes with the first, and a wrong call packs nothing.
        again = run(str(EXTENSION), str(output))
        self.assertEqual((again.returncode, again.stdout), (1, b''))
        self.assertIn(b'already holds', again.stderr)
        self.assertEqual((output / 'extension.crx').read_bytes(), package)
        for arguments in [(), (str(EXTENSION),), (str(EXTENSION), str(self.work / 'other'), 'key.pem')]:
            wrong = run(*arguments)
            self.assertEqual((wrong.returncode, wrong.stdout), (2, b''))
        self.assertFalse((self.work / 'other').exists())


if __name__ == '__main__':
    unittest.main()
