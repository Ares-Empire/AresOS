"""Package 18c, Part A: the Control tools in the image (build.sh control, the image checks).

The install map runs for real: `build.sh control-tree` is the same Python as the image build's `control` mode, into a
temporary folder. The image build's own extras (pip, the wheel record, the self-checks) run only in the image build;
their record is checked here with stand-ins for pip's report and the vendored tree.
"""
import base64
import hashlib
import importlib.util
import json
import marshal
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTROL = ROOT / 'control'
LINUX = sys.platform.startswith('linux')
REVISION = 'cd' * 20
FILES = {
    '/etc/claude-code/CLAUDE.md': ('0644', 'control/settings/CLAUDE.md'),
    '/etc/claude-code/managed-settings.json': ('0644', 'control/settings/managed-settings.draft.json'),
    '/usr/bin/aresos': ('0755', 'control/packaging/aresos'),
    '/usr/bin/aresos-mcp': ('0755', 'control/packaging/aresos-mcp'),
    '/usr/bin/aresos-toold': ('0755', 'control/packaging/aresos-toold'),
    '/usr/lib/systemd/system/aresos-toold.service': ('0644', 'control/packaging/aresos-toold.service'),
    '/usr/lib/sysusers.d/aresos-tools.conf': ('0644', 'control/packaging/aresos-tools.sysusers'),
    '/usr/lib/tmpfiles.d/aresos-tools.conf': ('0644', 'control/packaging/aresos-tools.tmpfiles'),
    '/usr/libexec/aresos-control/chrome/qualification.json': ('0644', 'control/chrome/qualification.json'),
    '/usr/libexec/aresos-control/launch.py': ('0644', 'control/launch.py'),
    '/usr/share/aresos/control/user-mcp.json': ('0644', 'control/settings/user-mcp.json'),
}
DERIVED = ('/usr/lib/tmpfiles.d/aresos-control-folders.conf', '/usr/libexec/aresos-control/chrome/build-id.json',
           '/usr/share/aresos/control/proxy.json', '/usr/share/aresos/control/service.json')
LINK = ('/etc/systemd/system/multi-user.target.wants/aresos-toold.service', '/usr/lib/systemd/system/aresos-toold.service')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def heredoc(path, start):
    """The Python of the one heredoc that `start` opens in `path`."""
    text = (ROOT / path).read_text()
    assert text.count(start) == 1, (path, start)
    return text.split(start, 1)[1].split('\nPY\n', 1)[0]


def lock_pins(path=CONTROL / 'requirements.lock'):
    """requirements.lock as {(name, version): [sha256, ...]} in its own order and spelling."""
    lock, current = {}, None
    for line in pathlib.Path(path).read_text().splitlines():
        if match := re.match(r'^([A-Za-z0-9._-]+)==(\S+) \\$', line):
            current = (match[1], match[2])
            lock[current] = []
        elif match := re.match(r'^\s+--hash=sha256:([0-9a-f]{64})', line):
            lock[current].append(match[1])
    return lock


def tree_files(source):
    return sorted(p for p in (CONTROL / source).rglob('*') if p.is_file() and '__pycache__' not in p.parts)


@unittest.skipUnless(LINUX, 'runs build.sh control-tree')
class InstallMapTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)

    def tree(self, os_dir=ROOT / 'os', control=CONTROL, dest=None):
        dest = dest or self.work / 'root'
        result = subprocess.run(['bash', str(ROOT / 'os/build.sh'), 'control-tree', str(os_dir), str(control), str(dest)],
                                capture_output=True, text=True, timeout=120)
        return result, dest

    def record(self, dest):
        return json.loads((dest / 'usr/share/aresos/manifest/control.json').read_text())

    def test_the_install_map_puts_every_file_where_the_launcher_and_the_unit_look(self):
        result, dest = self.tree()
        self.assertEqual(result.returncode, 0, result.stderr)
        record = self.record(dest)
        build = subprocess.run([sys.executable, '-I', '-B', str(CONTROL / 'chrome/build.py')], capture_output=True,
                               text=True, check=True).stdout.strip()
        self.assertEqual(result.stdout.splitlines(), [f'CONTROL_CHROME_BUILD {build}',
                                                      f'CONTROL_INSTALLED {len(record["files"])} files'])
        # The Chrome adapter reads its build from this file when the service starts (the image has no build.py).
        self.assertEqual((dest / 'usr/libexec/aresos-control/chrome/build-id.json').read_text(),
                         '{"build":"%s"}\n' % build)
        self.assertEqual(record['format'], 1)
        self.assertEqual(record['requirements_lock'], sha256((CONTROL / 'requirements.lock').read_bytes()))
        self.assertEqual(record['links'], dict([LINK]))
        self.assertEqual(os.readlink(dest / LINK[0].lstrip('/')), LINK[1])
        expected = {name: dict(mode=mode, sha256=sha256((ROOT / source).read_bytes()), source=source)
                    for name, (mode, source) in FILES.items()}
        for source, target in (('aresos_control', '/usr/libexec/aresos-control/aresos_control'),
                               ('generated', '/usr/libexec/aresos-control/generated')):
            for path in tree_files(source):
                rel = path.relative_to(CONTROL / source).as_posix()
                expected[f'{target}/{rel}'] = dict(mode='0644', sha256=sha256(path.read_bytes()),
                                                   source=f'control/{source}/{rel}')
        derived = {name: record['files'].pop(name) for name in DERIVED}
        self.assertEqual(record['files'], expected)
        self.assertEqual({row['mode'] for row in derived.values()}, {'0644'})
        for name, row in {**expected, **derived}.items():
            path = dest / name.lstrip('/')
            self.assertFalse(path.is_symlink(), name)
            self.assertEqual(f'{path.stat().st_mode & 0o7777:04o}', row['mode'], name)
            self.assertEqual(sha256(path.read_bytes()), row['sha256'], name)
        self.assertEqual(set(record['directories'].values()), {'0755'})
        self.assertEqual(sorted(record['directories']), sorted(
            ['/etc/claude-code', '/usr/libexec/aresos-control', '/usr/libexec/aresos-control/aresos_control',
             '/usr/libexec/aresos-control/chrome',
             '/usr/libexec/aresos-control/generated', '/usr/share/aresos/control',
             *{'/usr/libexec/aresos-control/aresos_control/' + p.parent.relative_to(CONTROL / 'aresos_control').as_posix()
               for p in tree_files('aresos_control') if p.parent != CONTROL / 'aresos_control'}]))
        # No exclusive MCP file, no Python bytecode from the checkout, nothing under his home.
        self.assertFalse((dest / 'etc/claude-code/managed-mcp.json').exists())
        self.assertEqual([p for p in dest.rglob('*') if '__pycache__' in p.parts], [])
        self.assertFalse((dest / 'var').exists())
        # The map installs nothing twice: a second run into the same folder stops.
        again, _ = self.tree(dest=dest)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('exists already', again.stderr)

    def test_the_paths_are_the_launchers_the_daemons_and_the_units(self):
        launch = (CONTROL / 'launch.py').read_text()
        constants = dict(re.findall(r'^(PREFIX|VENDOR|CONFIG) = Path\("([^"]+)"\)$', launch, re.M))
        self.assertEqual(constants, {'PREFIX': '/usr/libexec/aresos-control', 'VENDOR': '/usr/lib/aresos-control/vendor',
                                     'CONFIG': '/usr/share/aresos/control'})
        build = (ROOT / 'os/build.sh').read_text()
        self.assertIn("CODE, VENDOR, CONFIG = 'usr/libexec/aresos-control', 'usr/lib/aresos-control/vendor', "
                      "'usr/share/aresos/control'\n", build)
        self.assertIn('vendor=/usr/lib/aresos-control/vendor\n', build)
        daemon = (CONTROL / 'aresos_control/daemon.py').read_text()
        self.assertIn('parser.add_argument("--config", default="/usr/share/aresos/control/service.json")', daemon)
        launcher = '/usr/bin/python3 -I -S /usr/libexec/aresos-control/launch.py'
        for name in ('aresos', 'aresos-mcp', 'aresos-toold', 'aresos-toold.service'):
            self.assertIn(launcher, (CONTROL / 'packaging' / name).read_text(), name)
        # The Chrome adapter reads its two startup files from chrome/ beside aresos_control/ (the install map's CODE).
        adapter = (CONTROL / 'aresos_control/chrome/adapter.py').read_text()
        self.assertIn('RUNTIME = Path(__file__).resolve().parents[2]\n', adapter)
        for name in ('build-id.json', 'qualification.json'):
            self.assertIn(f"RUNTIME / 'chrome' / '{name}'", adapter)
        for server in json.loads((CONTROL / 'settings/user-mcp.json').read_text()).values():
            self.assertIn('/usr/libexec/aresos-control/launch.py', server['args'])
        for event in json.loads((CONTROL / 'settings/managed-settings.draft.json').read_text())['hooks'].values():
            self.assertIn('/usr/libexec/aresos-control/launch.py hook ', event[0]['hooks'][0]['command'])

    def test_the_config_follows_the_images_account_declaration(self):
        result, dest = self.tree()
        self.assertEqual(result.returncode, 0, result.stderr)
        share = dest / 'usr/share/aresos/control'
        for name, values in (('service.json', dict(owner_uid=1001)),
                             ('proxy.json', dict(home='/var/home/ares',
                                                 folders=['/var/home/ares/Downloads', '/var/home/ares/Documents']))):
            draft = json.loads((CONTROL / 'settings' / name).read_text())
            del draft['_comment']
            text = (share / name).read_text()
            self.assertEqual(text, json.dumps({**draft, **values}, indent=2) + '\n', name)
        folders = (dest / 'usr/lib/tmpfiles.d/aresos-control-folders.conf').read_text().splitlines()
        self.assertEqual([line for line in folders if not line.startswith('#')],
                         ['d /var/home/ares/Downloads :0700 :ares :ares -', 'd /var/home/ares/Documents :0700 :ares :ares -'])
        # Another declared account changes every derived value and nothing else.
        other = self.work / 'os'
        (other / 'config/usr/lib/sysusers.d').mkdir(parents=True)
        declaration = (ROOT / 'os/config/usr/lib/sysusers.d/aresos.conf').read_text()
        (other / 'config/usr/lib/sysusers.d/aresos.conf').write_text(
            declaration.replace('1001', '1002').replace(' ares ', ' pat ').replace('/var/home/ares', '/var/home/pat'))
        result, changed = self.tree(os_dir=other, dest=self.work / 'other')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads((changed / 'usr/share/aresos/control/service.json').read_text())['owner_uid'], 1002)
        proxy = json.loads((changed / 'usr/share/aresos/control/proxy.json').read_text())
        self.assertEqual((proxy['home'], proxy['folders']),
                         ('/var/home/pat', ['/var/home/pat/Downloads', '/var/home/pat/Documents']))
        self.assertIn('d /var/home/pat/Documents :0700 :pat :pat -',
                      (changed / 'usr/lib/tmpfiles.d/aresos-control-folders.conf').read_text())
        same, changed_record = self.record(dest), self.record(changed)
        differ = sorted(name for name in same['files'] if same['files'][name] != changed_record['files'][name])
        # Chrome's build-id.json is derived from control/ alone, not from the account.
        self.assertEqual(differ, sorted(name for name in DERIVED if not name.endswith('/chrome/build-id.json')))
        # An owner the file policy cannot use, or more than one account, stops the build.
        for broken in (declaration.replace('/var/home/ares', '/home/ares'), declaration + 'u other 1003 - /var/home/other\n',
                       declaration.replace('1001:1001', '999:999')):
            (other / 'config/usr/lib/sysusers.d/aresos.conf').write_text(broken)
            shutil.rmtree(self.work / 'other', ignore_errors=True)
            result, _ = self.tree(os_dir=other, dest=self.work / 'other')
            self.assertNotEqual(result.returncode, 0, broken)

    def test_the_image_build_records_its_commit_wheels_and_vendored_tree(self):
        lock = lock_pins()
        self.assertGreater(len(lock), 20)

        def report(items):
            path = self.work / f'report-{len(list(self.work.iterdir()))}.json'
            path.write_text(json.dumps({'install': [
                {'metadata': {'name': name.replace('-', '_'), 'version': version},
                 'download_info': {'url': f'https://files.example/{name}-{version}-py3-none-any.whl',
                                   'archive_info': {'hashes': {'sha256': digest}}}}
                for name, version, digest in items]}))
            return path

        def run(items, revision=REVISION):
            dest = pathlib.Path(tempfile.mkdtemp(dir=self.work))
            vendor = dest / 'usr/lib/aresos-control/vendor'
            (vendor / 'mcp').mkdir(parents=True)
            (vendor / 'mcp/__init__.py').write_text('# stand-in')
            (vendor / 'mcp/__init__.py').chmod(0o664)
            (vendor / 'bin').mkdir()
            (vendor / 'bin/mcp').write_text('#!/usr/bin/python3\n')
            (vendor / 'bin/mcp').chmod(0o775)
            code = heredoc('os/build.sh', 'python3 - "$os_dir" "$control_dir" "$dest" $report <<\'PY\'\n')
            env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'ARESOS_SOURCE_REVISION': revision}
            result = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT / 'os'), str(CONTROL), str(dest),
                                     str(report(items))], capture_output=True, text=True, timeout=60, env=env)
            return result, dest

        pinned = [(name, version, digests[-1]) for (name, version), digests in lock.items()]
        result, dest = run(pinned)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((dest / 'usr/share/aresos/manifest/control.json').read_text())
        self.assertEqual(record['source_revision'], REVISION)
        self.assertEqual([(w['name'], w['version'], w['sha256']) for w in record['wheels']],
                         sorted((name.lower(), version, digest) for name, version, digest in pinned))
        vendor = '/usr/lib/aresos-control/vendor'
        self.assertEqual(record['vendor'], {
            '/usr/lib/aresos-control': dict(mode='0755', sha256=None), vendor: dict(mode='0755', sha256=None),
            f'{vendor}/bin': dict(mode='0755', sha256=None),
            f'{vendor}/bin/mcp': dict(mode='0755', sha256=sha256(b'#!/usr/bin/python3\n')),
            f'{vendor}/mcp': dict(mode='0755', sha256=None),
            f'{vendor}/mcp/__init__.py': dict(mode='0644', sha256=sha256(b'# stand-in'))})
        self.assertEqual((dest / vendor.lstrip('/') / 'mcp/__init__.py').stat().st_mode & 0o777, 0o644)
        self.assertIn(f', {len(pinned)} wheels, 6 vendored paths from {REVISION}', result.stdout)
        # A wheel the lock does not pin, a missing one, or no exact commit stops the build.
        for items, revision in ((pinned[:-1] + [(*pinned[-1][:2], 'f' * 64)], REVISION), (pinned[1:], REVISION),
                                (pinned + [('extra', '1.0', 'e' * 64)], REVISION), (pinned, 'unrecorded')):
            result, _ = run(items, revision)
            self.assertNotEqual(result.returncode, 0, (items[-1], revision))


@unittest.skipUnless(LINUX, 'runs the check heredocs')
class ImageCheckTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)

    def test_check_image_holds_the_record_to_this_checkout(self):
        subprocess.run(['bash', str(ROOT / 'os/build.sh'), 'control-tree', str(ROOT / 'os'), str(CONTROL),
                        str(self.work / 'root')], check=True, capture_output=True, timeout=120)
        record = json.loads((self.work / 'root/usr/share/aresos/manifest/control.json').read_text())
        # The wheels as build.sh records them: normalized names, pip's file name and the SHA-256 it installed.
        wheels = [dict(name=re.sub(r'[-_.]+', '-', name).lower(), version=version, sha256=digests[0],
                       file=f'{name.replace("-", "_")}-{version}-py3-none-any.whl')
                  for (name, version), digests in lock_pins().items()]
        record.update(source_revision=REVISION, wheels=wheels,
                      vendor={'/usr/lib/aresos-control': dict(mode='0755', sha256=None)})
        code = heredoc('os/ci/check-image.sh', 'python3 - "$out/manifest/control.json" '
                       '"$expected/root/usr/share/aresos/manifest/control.json" "$(git rev-parse HEAD)" \\\n'
                       '    control/requirements.lock <<\'PY\'\n')

        def check(image, revision=REVISION, lock=CONTROL / 'requirements.lock'):
            path = self.work / 'image.json'
            path.write_text(json.dumps(image))
            return subprocess.run([sys.executable, '-I', '-c', code, str(path),
                                   str(self.work / 'root/usr/share/aresos/manifest/control.json'), revision,
                                   str(lock)], capture_output=True, text=True, timeout=60)

        result = check(record)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'from {REVISION}, {len(wheels)} wheels from requirements.lock', result.stdout)
        # REVIEW-A1 #6: the wheels against the checkout's lock, apart from the build's own check. A wheel missing,
        # one the lock doesn't pin, another version, a hash the lock doesn't hold, a wheel twice or no wheel file.
        for name, changed in (('missing', wheels[1:]), ('extra', wheels + [dict(wheels[0], name='extra')]),
                              ('version', [dict(wheels[0], version='0.0.0')] + wheels[1:]),
                              ('hash', [dict(wheels[0], sha256='f' * 64)] + wheels[1:]),
                              ('twice', wheels + [wheels[0]]),
                              ('not a wheel', [dict(wheels[0], file='mcp-2.3.0.tar.gz')] + wheels[1:])):
            result = check(dict(record, wheels=changed))
            self.assertNotEqual(result.returncode, 0, name)
            self.assertNotIn('Control in the image is this checkout', result.stdout, name)
        # A lock line the parser doesn't know stops the check instead of skipping a pin.
        odd = self.work / 'odd.lock'
        odd.write_text((CONTROL / 'requirements.lock').read_text() + 'extra==1.0 ; python_version > "3"\n')
        self.assertNotEqual(check(record, lock=odd).returncode, 0)
        self.assertNotEqual(check(record, 'ef' * 20).returncode, 0)
        changed = json.loads(json.dumps(record))
        changed['files']['/usr/share/aresos/control/service.json']['sha256'] = '0' * 64
        result = check(changed)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("control.json files differs at: ['/usr/share/aresos/control/service.json']", result.stderr)
        for key, value in (('requirements_lock', '0' * 64), ('links', {}), ('directories', {}),
                           ('vendor', {'/usr/lib/python3.14/site-packages/mcp': dict(mode='0755', sha256=None)})):
            self.assertNotEqual(check(dict(record, **{key: value})).returncode, 0, key)
        extra = json.loads(json.dumps(record))
        extra['files']['/etc/claude-code/managed-mcp.json'] = dict(mode='0644', sha256='0' * 64, source=None)
        self.assertNotEqual(check(extra).returncode, 0)

    @unittest.skipUnless(shutil.which('openssl'), 'needs openssl')
    def test_the_fixture_scan_finds_a_fixture_ca_or_hosts_line_and_nothing_else(self):
        code = heredoc('os/ci/image-checks.sh', 'python3 - "$image_root" "$planted" <<\'PY\'\n')

        def root(name, hosts='127.0.0.1 localhost\n', subjects=('/CN=Some Root CA',), anchor=None):
            top = self.work / name
            bundle = top / 'etc/pki/ca-trust/extracted/pem'
            bundle.mkdir(parents=True)
            (top / 'etc/hosts').write_text(hosts)
            pems = [self.certificate(subject) for subject in subjects]
            (bundle / 'tls-ca-bundle.pem').write_bytes(b''.join(pems))
            if anchor:
                (top / 'etc/pki/ca-trust/source/anchors').mkdir(parents=True)
                (top / 'etc/pki/ca-trust/source/anchors/ci.pem').write_bytes(self.certificate(anchor))
            return top

        planted = root('planted', hosts='10.0.2.2 greenmail dovecot\n', subjects=(), anchor='/CN=mail-fixture.invalid')

        def scan(image):
            return subprocess.run([sys.executable, '-I', '-c', code, str(image), str(planted)],
                                  capture_output=True, text=True, timeout=120)

        clean = scan(root('clean', hosts='127.0.0.1 localhost\n# 10.0.2.2 greenmail (a comment)\n'))
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertIn('NO_FIXTURE_TRACES', clean.stdout)
        for name, kwargs in (('hosts-address', dict(hosts='10.0.2.2 mail\n')),
                             ('hosts-name', dict(hosts='192.0.2.1 dovecot\n')),
                             ('anchor', dict(anchor='/CN=AresOS CI fixture CA')),
                             ('bundle', dict(subjects=('/CN=Some Root CA', '/CN=mail-fixture.invalid')))):
            self.assertNotEqual(scan(root(name, **kwargs)).returncode, 0, name)

    def certificate(self, subject):
        key = self.work / 'key.pem'
        return subprocess.run(['openssl', 'req', '-x509', '-newkey', 'ec', '-pkeyopt', 'ec_paramgen_curve:prime256v1',
                               '-nodes', '-keyout', str(key), '-days', '1', '-subj', subject],
                              check=True, capture_output=True, timeout=60).stdout


def load_vendor_check():
    spec = importlib.util.spec_from_file_location('vendor_check_for_test', ROOT / 'os/ci/control/vendor_check.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def wheel(folder, name, version, files, entry_points=None, unlisted=()):
    """A wheel as a build backend writes one: its files, METADATA, WHEEL, entry_points.txt and RECORD. files maps a
    member to its bytes, or to (bytes, zip mode). Members named in unlisted stay out of its RECORD."""
    info = f'{name}-{version}.dist-info'
    members = {path: value if isinstance(value, tuple) else (value, 0o100644) for path, value in files.items()}
    members[f'{info}/METADATA'] = (f'Metadata-Version: 2.1\nName: {name}\nVersion: {version}\n'.encode(), 0o100644)
    members[f'{info}/WHEEL'] = (b'Wheel-Version: 1.0\nGenerator: test\nRoot-Is-Purelib: true\nTag: py3-none-any\n',
                                0o100644)
    if entry_points:
        members[f'{info}/entry_points.txt'] = (entry_points.encode(), 0o100644)
    record = ''.join(f'{path},sha256={base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")},'
                     f'{len(data)}\n' for path, (data, _) in members.items() if path not in unlisted)
    members[f'{info}/RECORD'] = ((record + f'{info}/RECORD,,\n').encode(), 0o100644)
    path = pathlib.Path(folder) / f'{name}-{version}-py3-none-any.whl'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as archive:
        for member, (data, mode) in members.items():
            entry = zipfile.ZipInfo(member, date_time=(2026, 1, 1, 0, 0, 0))
            entry.external_attr = mode << 16
            archive.writestr(entry, data)
    return dict(name=name, version=version, file=path.name, sha256=sha256(path.read_bytes()))


@unittest.skipUnless(LINUX, 'compiles and installs into temporary folders')
class VendorTreeTest(unittest.TestCase):
    """REVIEW-X1 #1: the vendored tree and its record are what the locked wheels install, apart from the build."""

    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        self.vendor_check = load_vendor_check()
        self.wheels = self.work / 'wheels'
        self.wheels.mkdir()
        self.recorded = [
            wheel(self.wheels, 'demo', '1.0', {
                'demo/__init__.py': b'NAMES = frozenset({"a", "b", "c"})\n',
                'demo/cli.py': b'def main():\n    return 0\n',
                'demo/_native.so': (b'\x7fELF stand-in', 0o100755)},
                entry_points='[console_scripts]\ndemo = demo.cli:main [extra]\n\n[demo.plugins]\nx = demo:NAMES\n',
                unlisted=('demo/cli.py',)),
            wheel(self.wheels, 'other', '2.0', {'other.py': b'VALUE = 1\n'})]

    def image(self):
        """A root as the image build leaves it: the tree installed, compiled in place, recorded by build.sh's rule."""
        root = pathlib.Path(tempfile.mkdtemp(dir=self.work))
        record = dict(wheels=self.recorded)
        self.vendor_check.install(self.vendor_check.expected_sources(record, self.wheels),
                                  root / self.vendor_check.VENDOR, sys.executable)
        return root, dict(record, vendor=self.vendor_check.tree_map(root))

    def check(self, root, record):
        return self.vendor_check.check(record, self.wheels, root, sys.executable)

    def test_the_record_must_be_what_the_locked_wheels_install(self):
        root, record = self.image()
        vendor = '/' + self.vendor_check.VENDOR
        self.assertLessEqual({f'{vendor}/demo/__init__.py', f'{vendor}/bin/demo', f'{vendor}/demo/_native.so',
                              f'{vendor}/demo-1.0.dist-info/INSTALLER', f'{vendor}/demo-1.0.dist-info/REQUESTED',
                              f'{vendor}/demo-1.0.dist-info/RECORD', f'{vendor}/other.py'}, set(record['vendor']))
        self.assertEqual(record['vendor'][f'{vendor}/demo/_native.so']['mode'], '0755')
        self.assertEqual(record['vendor'][f'{vendor}/bin/demo']['mode'], '0755')
        self.assertTrue(any(name.endswith('.pyc') for name in record['vendor']))
        found = self.check(root, record)
        self.assertEqual((found['wheels'], found['paths']), (2, len(record['vendor'])))
        script = (root / self.vendor_check.VENDOR / 'bin/demo').read_text()
        self.assertEqual(script.splitlines()[:3], ['#!/usr/bin/python3', 'import sys', 'from demo.cli import main'])

        def tampered(change):
            """A fresh image with one change made to the tree and recorded, the wheel list untouched."""
            root, record = self.image()
            change(root / self.vendor_check.VENDOR)
            return root, dict(record, vendor=self.vendor_check.tree_map(root))

        def pyc_with_other_code(folder):
            # A checked-hash header that names the right source, followed by other code.
            pyc = next((folder / 'demo/__pycache__').glob('cli.*.pyc'))
            code = compile('import os\nos.system("true")\n', str(folder / 'demo/cli.py'), 'exec')
            pyc.write_bytes(pyc.read_bytes()[:16] + marshal.dumps(code))

        def record_row_dropped(folder):
            path = folder / 'other-2.0.dist-info/RECORD'
            path.write_bytes(b''.join(path.read_bytes().splitlines(keepends=True)[1:]))

        # The regression: one vendored file and its record changed, every wheel still the lock's.
        for name, change in (
                ('a source changed', lambda folder: (folder / 'demo/cli.py').write_text('def main():\n    return 1\n')),
                ('bytecode with other code', pyc_with_other_code),
                ('a file added', lambda folder: (folder / 'demo/extra.py').write_text('')),
                ('direct_url.json', lambda folder: (folder / 'demo-1.0.dist-info/direct_url.json').write_text('{}')),
                ('a mode', lambda folder: (folder / 'other.py').chmod(0o755)),
                ('a generated script', lambda folder: (folder / 'bin/demo').write_text('#!/bin/sh\n')),
                ('INSTALLER', lambda folder: (folder / 'demo-1.0.dist-info/INSTALLER').write_text('uv\n')),
                ('a RECORD row', record_row_dropped),
                ('a file removed', lambda folder: (folder / 'other.py').unlink())):
            root, record = tampered(change)
            with self.assertRaisesRegex(self.vendor_check.Mismatch, 'not what the locked wheels install', msg=name):
                self.check(root, record)
        # The image's tree differs from its record (image-checks.sh's finding, seen here too).
        root, record = self.image()
        (root / self.vendor_check.VENDOR / 'other.py').write_text('VALUE = 2\n')
        with self.assertRaisesRegex(self.vendor_check.Mismatch, 'the image differs from its record'):
            self.check(root, record)
        # A wheel whose bytes are not the recorded SHA-256.
        root, record = self.image()
        bad = dict(record, wheels=[dict(self.recorded[0], sha256='0' * 64), self.recorded[1]])
        with self.assertRaisesRegex(self.vendor_check.Mismatch, 'not the recorded SHA-256'):
            self.check(root, bad)

    @unittest.skipIf(os.path.exists('/run/.containerenv'), 'inside a container')
    def test_it_replaces_the_real_vendor_folder_only_in_a_container(self):
        with self.assertRaises(SystemExit):
            self.vendor_check.check(dict(wheels=self.recorded, vendor={}), self.wheels)

    def test_a_wheel_without_a_rule_stops_the_check(self):
        cases = {
            'a .data folder': dict(files={'demo-1.0.data/scripts/run': b'#!python\n'}),
            'gui_scripts': dict(files={'demo/__init__.py': b''}, entry_points='[gui_scripts]\ndemo = demo:main\n'),
            "pip's own entry point": dict(files={'pip/__init__.py': b''}, entry_points='[console_scripts]\npip = pip:main\n'),
            'a link': dict(files={'demo/link': (b'/etc/passwd', 0o120777)}),
            'a member outside its folder': dict(files={'../escape.py': b''}),
            'a generated file in the wheel': dict(files={'demo-1.0.dist-info/INSTALLER': b'pip\n'}),
        }
        for name, case in cases.items():
            folder = self.work / name.replace(' ', '-').replace("'", '')
            folder.mkdir()
            recorded = wheel(folder, 'demo', '1.0', **case)
            with self.assertRaises(self.vendor_check.Mismatch, msg=name):
                self.vendor_check.expected_sources(dict(wheels=[recorded]), folder)
        folder = self.work / 'two-write-one'
        folder.mkdir()
        both = [wheel(folder, 'demo', '1.0', {'shared.py': b'A = 1\n'}),
                wheel(folder, 'other', '2.0', {'shared.py': b'A = 2\n'})]
        with self.assertRaisesRegex(self.vendor_check.Mismatch, 'shared.py: written by'):
            self.vendor_check.expected_sources(dict(wheels=both), folder)

    @unittest.skipUnless(subprocess.run([sys.executable, '-m', 'pip', '--version'], capture_output=True).returncode == 0,
                         'needs pip')
    def test_the_rules_are_what_pip_writes(self):
        # pip --target --no-compile as the build runs it, from these wheels and without an index: every file pip
        # writes (RECORD, INSTALLER, REQUESTED, modes, a file the wheel's RECORD doesn't list) is the derived one. The
        # console script template is pip 26's (the image's); this runner's pip may be older, so the script is left
        # to the image build's own comparison.
        no_scripts = self.work / 'no-scripts'
        no_scripts.mkdir()
        recorded = [wheel(no_scripts, 'demo', '1.0', {
            'demo/__init__.py': b'NAMES = frozenset({"a", "b"})\n', 'demo/cli.py': b'def main():\n    return 0\n',
            'demo/_native.so': (b'\x7fELF stand-in', 0o100755), 'demo/data.bin': (b'\0\1', 0o644)},
            unlisted=('demo/cli.py',)), wheel(no_scripts, 'other', '2.0', {'other.py': b'VALUE = 1\n'})]
        target = self.work / 'pip' / self.vendor_check.VENDOR
        result = subprocess.run(
            [sys.executable, '-I', '-m', 'pip', 'install', '--quiet', '--disable-pip-version-check', '--no-cache-dir',
             '--no-compile', '--no-index', '--find-links', str(no_scripts), '--only-binary=:all:', '--target',
             str(target), 'demo==1.0', 'other==2.0'], capture_output=True, text=True, timeout=300,
            env={'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': str(self.work)})
        self.assertEqual(result.returncode, 0, result.stderr)
        derived = self.work / 'derived' / self.vendor_check.VENDOR
        sources = self.vendor_check.expected_sources(dict(wheels=recorded), no_scripts)
        for name, (data, mode) in sources.items():
            (derived / name).parent.mkdir(parents=True, exist_ok=True)
            (derived / name).write_bytes(data)
            (derived / name).chmod(mode)
        self.assertEqual(self.vendor_check.tree_map(self.work / 'pip'), self.vendor_check.tree_map(self.work / 'derived'))

    def test_the_compile_step_and_the_image_check_are_the_builds(self):
        build = (ROOT / 'os/build.sh').read_text()
        line = re.search(r'\n\s*env -i (PATH=\S+) (LANG=\S+) (/usr/bin/python3 -I -m compileall -q) \\\n'
                         r'\s*(--invalidation-mode checked-hash) "\$vendor"\n', build)
        self.assertIsNotNone(line, 'the compile step in build.sh')
        self.assertEqual(f'{line[3]} {line[4]}'.split(), self.vendor_check.COMPILE)
        self.assertEqual(dict(item.split('=', 1) for item in line.group(1, 2)), self.vendor_check.COMPILE_ENV)
        self.assertIn('vendor=/usr/lib/aresos-control/vendor\n', build)
        self.assertEqual(self.vendor_check.VENDOR, 'usr/lib/aresos-control/vendor')
        check = (ROOT / 'os/ci/check-image.sh').read_text()
        block = check[check.index('# REVIEW-X1 #1'):check.index('echo CHECK_BUILD_PASSED')]
        order = [block.index(text) for text in (
            'vendor_check.py fetch "$out/manifest/control.json"', '--network=none --entrypoint /usr/bin/bash "$image"',
            'vendor_check.py check /tmp/vendor-check/control.json /tmp/vendor-check/wheels',
            "grep -q '^CONTROL_VENDOR_FROM_WHEELS '")]
        self.assertEqual(order, sorted(order))
        # After the record is held to the checkout and its lock.
        self.assertLess(check.index("raise SystemExit(\"The image's wheels are not this checkout's requirements.lock\")"),
                        check.index('# REVIEW-X1 #1'))

    def test_the_wheels_come_from_pypi_by_name_with_the_recorded_hash(self):
        record = dict(wheels=self.recorded)
        blobs = {item['file']: (self.wheels / item['file']).read_bytes() for item in self.recorded}

        def index(override=None):
            def get(url):
                if url.startswith('https://pypi.org/pypi/'):
                    name, version = url.split('/')[4:6]
                    item = next(item for item in self.recorded if (item['name'], item['version']) == (name, version))
                    entry = dict(filename=item['file'], digests=dict(sha256=item['sha256']),
                                 url=f'https://files.pythonhosted.org/packages/xx/{item["file"]}')
                    return json.dumps(dict(urls=[dict(entry, **(override or {}))])).encode()
                self.assertTrue(url.startswith('https://files.pythonhosted.org/packages/xx/'), url)
                return blobs[url.rsplit('/', 1)[1]]
            return get

        folder = self.work / 'fetched'
        folder.mkdir()
        self.assertEqual(self.vendor_check.fetch(record, folder, index()), sum(map(len, blobs.values())))
        self.assertEqual({path.name: path.read_bytes() for path in folder.iterdir()}, blobs)
        for name, get in (('another hash on the index', index(dict(digests=dict(sha256='0' * 64)))),
                          ('another host', index(dict(url='https://example.invalid/demo-1.0-py3-none-any.whl'))),
                          ('no such file', index(dict(filename='demo-1.0-py3-none-manylinux.whl')))):
            with self.assertRaises(self.vendor_check.Mismatch, msg=name):
                self.vendor_check.fetch(record, folder, get)
        blobs[self.recorded[0]['file']] = b'other bytes'
        with self.assertRaisesRegex(self.vendor_check.Mismatch, 'the download is not the recorded SHA-256'):
            self.vendor_check.fetch(record, folder, index())
        with self.assertRaisesRegex(self.vendor_check.Mismatch, 'not a wheel file name'):
            self.vendor_check.fetch(dict(wheels=[dict(self.recorded[0], file='../demo.whl')]), folder, index())


class ServiceUserTest(unittest.TestCase):
    """Agreed change 5: one fixed number, unused by Fedora's static block and the image's own declarations."""

    def test_the_number_is_outside_fedoras_static_block_and_the_images_own(self):
        line = (CONTROL / 'packaging/aresos-tools.sysusers').read_text().splitlines()[-1].split()
        number = int(line[2])
        self.assertEqual(number, 250)
        # Fedora's setup package assigns 0 to 200 statically; systemd-sysusers and useradd -r allocate the dynamic
        # system range from 999 downward (on the laptop, 2026-11-14, down to 957).
        self.assertTrue(200 < number < 900)
        used = set()
        for path in (ROOT / 'os/config/usr/lib/sysusers.d').glob('*.conf'):
            for fields in (line.split() for line in path.read_text().splitlines() if line[:1] in ('u', 'g')):
                used.update(int(n) for n in re.findall(r'\d+', fields[2]))
        self.assertNotIn(number, used)

    @unittest.skipUnless(shutil.which('systemd-sysusers'), 'needs systemd-sysusers')
    def test_sysusers_creates_the_user_and_its_group_with_that_number(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            (root / 'etc').mkdir()
            # The base's static and dynamic system accounts, as on the laptop, and the daily account.
            dynamic = range(957, 1000)
            (root / 'etc/passwd').write_text('root:x:0:0:root:/root:/bin/bash\n' + ''.join(
                f'system{n}:x:{n}:{n}::/:/usr/sbin/nologin\n' for n in (*range(1, 195), *dynamic)) +
                'ares:x:1001:1001::/var/home/ares:/bin/bash\n')
            (root / 'etc/group').write_text('root:x:0:\n' + ''.join(f'system{n}:x:{n}:\n' for n in (*range(1, 195), *dynamic))
                                            + 'ares:x:1001:\n')
            (root / 'etc/shadow').write_text('root:!:::::::\n')
            (root / 'etc/gshadow').write_text('root:::\n')
            result = subprocess.run(['systemd-sysusers', '--dry-run', f'--root={folder}',
                                     str(CONTROL / 'packaging/aresos-tools.sysusers')],
                                    capture_output=True, text=True, timeout=60)
            if result.returncode and 'dry-run' in result.stderr:
                self.skipTest('systemd-sysusers without --dry-run')
            self.assertEqual(result.returncode, 0, result.stderr)
            output = result.stdout + result.stderr
            self.assertIn("Creating group 'aresos-tools' with GID 250.", output)
            self.assertIn("Creating user 'aresos-tools' (AresOS tool service) with UID 250 and GID 250.", output)


class ContainerfileTest(unittest.TestCase):
    def test_control_comes_from_the_source_stage_and_installs_before_configure(self):
        containerfile = (ROOT / 'os/Containerfile').read_text()
        final = containerfile.split('FROM packages AS aresos', 1)[1]
        copy = final.index('COPY --from=source /source/control /tmp/aresos/control\n')
        config = final.index('cp -a /tmp/aresos/config/. /')
        control = final.index('bash /tmp/aresos/build.sh control && \\\n')
        self.assertLess(copy, config)
        self.assertLess(config, control)
        self.assertLess(control, final.index('bash /tmp/aresos/build.sh configure'))
        # One way in, from the build commit: no other stage or build context copies control/.
        self.assertEqual([line for line in containerfile.splitlines() if line.startswith('COPY') and 'control' in line],
                         ['COPY --from=source /source/control /tmp/aresos/control'])
        self.assertFalse((ROOT / 'os/control').exists(), 'the os/ build context must not carry a second control/')
        build = (ROOT / 'os/build.sh').read_text()
        self.assertIn('"AresOS-$revision/control"', build.split('if [[ $1 == source ]]', 1)[1].split('\nfi\n', 1)[0])


if __name__ == '__main__':
    unittest.main()
