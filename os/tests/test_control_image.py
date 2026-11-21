"""Package 18c, Part A: the Control tools in the image (build.sh control, the image checks).

The install map runs for real: `build.sh control-tree` is the same Python as the image build's `control` mode, into a
temporary folder. The image build's own extras (pip, the wheel record, the self-checks) run only in the image build;
their record is checked here with stand-ins for pip's report and the vendored tree.
"""
import base64
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import marshal
import os
import pathlib
import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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
    '/usr/libexec/aresos-control/chrome/host': ('0755', 'control/chrome/packaging/host'),
    '/usr/libexec/aresos-control/chrome/native_host.py': ('0644', 'control/chrome/native_host.py'),
    '/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy':
        ('0644', 'control/chrome/packaging/org.aresos.control.chrome-loosen.policy'),
    '/usr/lib/tmpfiles.d/aresos-control-chrome.conf': ('0644', 'control/chrome/packaging/aresos-control-chrome.tmpfiles'),
    '/usr/libexec/aresos-control/launch.py': ('0644', 'control/launch.py'),
    '/usr/share/aresos/control/user-mcp.json': ('0644', 'control/settings/user-mcp.json'),
}
DERIVED = ('/usr/lib/tmpfiles.d/aresos-control-folders.conf', '/usr/libexec/aresos-control/chrome/build-id.json',
           '/usr/share/aresos/control/proxy.json', '/usr/share/aresos/control/service.json')
LINK = ('/etc/systemd/system/multi-user.target.wants/aresos-toold.service', '/usr/lib/systemd/system/aresos-toold.service')
CHROME_LINKS = {
    '/etc/opt/chrome/policies/managed/aresos.json': '/usr/share/aresos/chrome/policy.json',
    '/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome.json': '/usr/share/aresos/chrome/native-host.json',
}


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
        self.assertEqual(record['chrome_build'], build)
        gh = json.loads((ROOT / 'os/gh.lock.json').read_text())
        self.assertEqual(record['gh'], dict(version=gh['nevra'].split('-')[1], binary_sha256=gh['binary_sha256']))
        self.assertNotIn('chrome_extension', record, 'control-tree must not sign a bundle')
        self.assertEqual(list((dest / 'usr/share/aresos/chrome').iterdir()), [])
        self.assertEqual(record['links'], dict([LINK], **CHROME_LINKS))
        for name, target in CHROME_LINKS.items():
            self.assertTrue((dest / name.lstrip('/')).is_symlink())
            self.assertEqual(os.readlink(dest / name.lstrip('/')), target)
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
             '/usr/libexec/aresos-control/generated', '/usr/share/aresos/control', '/usr/share/aresos/chrome',
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
        shutil.copyfile(ROOT / 'os/gh.lock.json', other / 'gh.lock.json')
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
            # -B since the R28 cut's fix (review 11): the interpreter writes no bytecode of its own imports.
            code = heredoc('os/build.sh', 'python3 -B - "$os_dir" "$control_dir" "$dest" $report <<\'PY\'\n')
            env = {'PATH': os.environ.get('PATH', '/usr/bin:/bin'), 'ARESOS_SOURCE_REVISION': revision}
            result = subprocess.run([sys.executable, '-I', '-c', code, str(ROOT / 'os'), str(CONTROL), str(dest),
                                     str(report(items))], capture_output=True, text=True, timeout=60, env=env)
            return result, dest

        pinned = [(name, version, digests[-1]) for (name, version), digests in lock.items()]
        result, dest = run(pinned)
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads((dest / 'usr/share/aresos/manifest/control.json').read_text())
        checker = load_chrome_check()
        extension = record['chrome_extension']
        self.assertIn(f'CONTROL_CHROME_EXTENSION {extension["id"]} {extension["crx_sha256"]}', result.stdout)
        checker.bundle_content({name: (dest / checker.BUNDLE.lstrip('/') / name).read_bytes()
                                for name in checker.NAMES}, extension)
        checker.compare(record, record, CONTROL)
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
        for key, value in (('requirements_lock', '0' * 64), ('chrome_build', '0' * 64), ('gh', {}), ('links', {}), ('directories', {}),
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

        def tampered(change, folder=self.vendor_check.VENDOR):
            """A fresh image with one change made to the tree and recorded, the wheel list untouched."""
            root, record = self.image()
            change(root / folder)
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

        # RECHECK-X1 #1: beside vendor/, in /usr/lib/aresos-control itself. build.sh puts nothing there but vendor/,
        # so a sibling has no source: recorded in the manifest, it still fails.
        def sibling_bytecode(folder):
            source = folder / 'extra.py'
            source.write_text('import os\nos.system("true")\n')
            py_compile.compile(str(source), cfile=str(folder / 'extra.pyc'), doraise=True)
            source.unlink()

        def sibling_folder(folder):
            (folder / 'site').mkdir()
            (folder / 'site/extra.py').write_text('')

        for name, change in (
                ('a sibling source file', lambda folder: (folder / 'extra.py').write_text('import os\n')),
                ('a sibling .pyc', sibling_bytecode),
                ('a sibling folder', sibling_folder)):
            root, record = tampered(change, self.vendor_check.DEPENDENCIES)
            self.assertTrue(any(not path.startswith(f'{vendor}/') and path != vendor
                                and path != '/' + self.vendor_check.DEPENDENCIES for path in record['vendor']), name)
            with self.assertRaisesRegex(self.vendor_check.Mismatch, 'recorded, not derived', msg=name):
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
        line = re.search(r'\n\s*env -i (PATH=\S+) (LANG=\S+) (/usr/bin/python3 -I -B -m compileall -q) \\\n'
                         r'\s*(--invalidation-mode checked-hash) "\$vendor"\n', build)
        self.assertIsNotNone(line, 'the compile step in build.sh')
        # The build adds -B (the R28 cut's fix, review 11): it stops only the interpreter's own import caches;
        # compileall writes the same checked-hash bytecode with or without it, so the check's command omits it.
        self.assertEqual([part for part in f'{line[3]} {line[4]}'.split() if part != '-B'], self.vendor_check.COMPILE)
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


def load_chrome_check():
    spec = importlib.util.spec_from_file_location('chrome_image', ROOT / 'os/ci/control/chrome_image.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ChromeImageTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        self.checker = load_chrome_check()
        spec = importlib.util.spec_from_file_location('chrome_pack', CONTROL / 'chrome/packaging/pack.py')
        self.pack = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.pack)

    def bundle(self):
        files, extension = self.pack.pack(CONTROL / 'chrome/extension')
        extension['files'] = {self.checker.BUNDLE + '/' + name: {'mode': '0644', 'sha256': sha256(data)}
                              for name, data in files.items()}
        return files, extension

    def test_control_tree_hashes_before_generation_and_leaves_sources_byte_identical(self):
        control = self.work / 'source/control'
        shutil.copytree(CONTROL, control, ignore=shutil.ignore_patterns('__pycache__'))
        dest = self.work / 'root'
        # This runs in the actual build subprocess. Generating even a destination
        # file first fails, not just a source edit that later happens to be undone.
        build_py = control / 'chrome/build.py'
        build_py.write_text('from pathlib import Path\nimport os\n'
                            'assert not Path(os.environ["CHROME_ORDER_DEST"]).exists(), "generated before hash"\n'
                            + build_py.read_text())
        before = {str(p.relative_to(control)): p.read_bytes() for p in control.rglob('*') if p.is_file()}
        expected = subprocess.run([sys.executable, '-I', '-B', str(build_py)], capture_output=True, text=True,
                                  check=True, env={**os.environ, 'CHROME_ORDER_DEST': str(dest)}).stdout.strip()
        result = subprocess.run(['bash', str(ROOT / 'os/build.sh'), 'control-tree', str(ROOT / 'os'), str(control), str(dest)],
                                capture_output=True, text=True, env={**os.environ, 'CHROME_ORDER_DEST': str(dest)}, timeout=120)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(before, {str(p.relative_to(control)): p.read_bytes() for p in control.rglob('*') if p.is_file()})
        record = json.loads((dest / 'usr/share/aresos/manifest/control.json').read_bytes())
        self.assertEqual(record['chrome_build'], expected)
        self.assertEqual(json.loads((dest / 'usr/libexec/aresos-control/chrome/build-id.json').read_bytes()), {'build': expected})
        for name in record['files']:
            data = (dest / name.lstrip('/')).read_bytes()
            for token in self.checker.PLACEHOLDERS:
                self.assertNotIn(token, data, name)
        self.assertFalse((dest / 'var').exists())
        self.assertFalse((dest / 'etc/aresos/control/chrome-excluded-sites.json').exists())

    def test_one_packer_call_only_in_image_mode_after_hash_and_no_source_writes(self):
        dest = self.work / 'root'
        report = self.work / 'pip-report.json'
        report.write_text(json.dumps({'install': [
            {'metadata': {'name': name, 'version': version}, 'download_info': {
                'url': f'https://files.invalid/{name}-{version}-py3-none-any.whl',
                'archive_info': {'hashes': {'sha256': digests[0]}}}}
            for (name, version), digests in lock_pins().items()]}))
        code = heredoc('os/build.sh', 'python3 -B - "$os_dir" "$control_dir" "$dest" $report <<\'PY\'\n')
        calls = []
        run = subprocess.run
        before = {str(p.relative_to(CONTROL)): p.read_bytes() for p in CONTROL.rglob('*')
                  if p.is_file() and '__pycache__' not in p.parts}

        def tracked(argv, **kwargs):
            calls.append(argv)
            if argv[3].endswith('/build.py'):
                self.assertFalse(dest.exists(), 'a destination exists before build.py runs')
            return run(argv, **kwargs)

        with patch.object(sys, 'argv', ['-', str(ROOT / 'os'), str(CONTROL), str(dest), str(report)]), \
                patch.dict(os.environ, {'ARESOS_SOURCE_REVISION': REVISION}), patch('subprocess.run', tracked):
            exec(compile(code, 'build.sh control map', 'exec'), {})
        self.assertEqual([pathlib.Path(argv[3]).name for argv in calls], ['build.py', 'pack.py'])
        self.assertEqual(before, {str(p.relative_to(CONTROL)): p.read_bytes() for p in CONTROL.rglob('*')
                                  if p.is_file() and '__pycache__' not in p.parts})
        record = json.loads((dest / 'usr/share/aresos/manifest/control.json').read_bytes())
        self.checker.bundle_content({name: (dest / self.checker.BUNDLE.lstrip('/') / name).read_bytes()
                                    for name in self.checker.NAMES}, record['chrome_extension'])

    def test_independent_reader_rejects_signature_payload_identity_and_policy_mutations(self):
        files, record = self.bundle()
        self.checker.bundle_content(files, record)
        other, _ = self.bundle()
        self.assertNotEqual(files['extension.crx'], other['extension.crx'])
        cases = {
            'broken signature': lambda f, r: f.__setitem__('extension.crx', f['extension.crx'][:-1] + bytes([f['extension.crx'][-1] ^ 1])),
            'foreign CRX': lambda f, r: f.__setitem__('extension.crx', other['extension.crx']),
            'recorded identity': lambda f, r: r.__setitem__('id', 'a' * 32),
            'recorded payload': lambda f, r: r['payload'][0].__setitem__('sha256', '0' * 64),
            'recorded version': lambda f, r: r.__setitem__('version', '99'),
            'wildcard policy': lambda f, r: f.__setitem__('policy.json', b'{"ExtensionSettings":{"*":{}}}'),
            'override removed': lambda f, r: f.__setitem__('policy.json', f['policy.json'].replace(b'"override_update_url":true,', b'')),
            'second origin': lambda f, r: f.__setitem__('native-host.json', f['native-host.json'].replace(b'"]', b'","chrome-extension://aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/"]')),
            'network update': lambda f, r: f.__setitem__('policy.json', f['policy.json'].replace(b'file:///usr/share', b'https://example.invalid')),
            'network CRX': lambda f, r: f.__setitem__('update.xml', f['update.xml'].replace(b'file:///usr/share', b'https://example.invalid')),
            'template left': lambda f, r: f.__setitem__('update.xml', f['update.xml'].replace(r['version'].encode(), b'EXTENSION_VERSION')),
            'extra bundle': lambda f, r: f.__setitem__('probe.crx', b'probe'),
        }
        for name, change in cases.items():
            with self.subTest(name=name):
                f, r = copy.deepcopy(files), copy.deepcopy(record)
                change(f, r)
                self.assertTrue(f != files or r != record, 'mutation did not change anything')
                # Bind the edited bytes too: the independent content checks,
                # not merely a stale hash, must detect these mutations.
                r['files'] = {self.checker.BUNDLE + '/' + key: {'mode': '0644', 'sha256': sha256(data)} for key, data in f.items()}
                r['crx_sha256'] = sha256(f['extension.crx'])
                with self.assertRaises(Exception):
                    self.checker.bundle_content(f, r)

    def test_release_image_rejects_the_test_layers_payload_paths_and_dangling_roots(self):
        root = self.work / 'root'
        files, extension = self.bundle()
        build = 'c' * 64
        record = {'chrome_extension': extension, 'chrome_build': build, 'files': {}, 'links': self.checker.LINKS}
        code = 'usr/libexec/aresos-control/chrome'

        def write(name, data):
            path = root / name.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return path

        for name, data in files.items():
            write(f'{self.checker.BUNDLE}/{name}', data)
        write('usr/share/aresos/manifest/control.json', json.dumps(record).encode())
        write(f'{code}/build-id.json', json.dumps({'build': build}).encode())
        for name in ('host', 'native_host.py', 'qualification.json'):
            write(f'{code}/{name}', b'fixture')
        for name, target in self.checker.LINKS.items():
            path = root / name.lstrip('/')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
        for name in ('tmp', 'var/tmp', 'root'):
            (root / name).mkdir(parents=True)

        def in_image(name):
            path = pathlib.Path(name)
            return path if path.is_relative_to(root) else root / path.relative_to('/')

        other_files, _ = self.bundle()
        with patch.object(self.checker, 'Path', in_image), patch.object(self.checker, 'owned'), \
                patch.object(self.checker, 'owned_link'):
            self.checker.image(root)
            for name, payload in (
                    ('usr/share/aresos-install-test/probe/extension.crx', {'': other_files['extension.crx']}),
                    ('usr/libexec/aresos-install-test/probe-host', {'': b'#!/bin/sh\nexit 0\n'}),
                    ('usr/share/aresos-install-test/bundles/b', other_files)):
                with self.subTest(payload=name):
                    for part, data in payload.items():
                        path = write(f'{name}/{part}' if part else name, data)
                        if name.endswith('/probe-host'):
                            path.chmod(0o755)
                    test_root = pathlib.Path(*pathlib.Path(name).parts[:3])
                    try:
                        with self.assertRaisesRegex(AssertionError, f'test-only Chrome payload root: /{test_root}'):
                            self.checker.image(root)
                    finally:
                        shutil.rmtree(root / test_root)
            for name in ('usr/share/aresos-install-test', 'usr/libexec/aresos-install-test'):
                with self.subTest(dangling=name):
                    path = root / name
                    path.symlink_to('missing')
                    self.assertFalse(path.exists())
                    with self.assertRaisesRegex(AssertionError, f'test-only Chrome payload root: /{name}'):
                        self.checker.image(root)
                    path.unlink()

    def test_checkout_comparison_binds_payload_templates_build_and_links(self):
        _, extension = self.bundle()
        record = {'chrome_build': 'c' * 64, 'links': dict(CHROME_LINKS), 'chrome_extension': extension}
        self.checker.compare(record, record, CONTROL)
        for name, change in (
                ('build', lambda r: r.__setitem__('chrome_build', 'd' * 64)),
                ('link', lambda r: r['links'].__setitem__(next(iter(CHROME_LINKS)), '/tmp/other')),
                ('payload', lambda r: r['chrome_extension']['payload'][0].__setitem__('sha256', '0' * 64)),
                ('version', lambda r: r['chrome_extension'].__setitem__('version', '99')),
                ('mode', lambda r: r['chrome_extension']['files'][self.checker.BUNDLE + '/policy.json'].__setitem__('mode', '0664')),
                ('template', lambda r: r['chrome_extension']['files'][self.checker.BUNDLE + '/policy.json'].__setitem__('sha256', '0' * 64))):
            changed = copy.deepcopy(record)
            change(changed)
            with self.assertRaises(AssertionError, msg=name):
                self.checker.compare(changed, record, CONTROL)

    def test_key_scans_find_newlines_chunk_boundaries_every_encoding_and_pem(self):
        value = bytes(range(256))
        needles = self.checker.forms(value)
        path = self.work / 'scan'
        for name, data in [('raw', value), ('hex', value.hex().encode()), ('HEX', value.hex().upper().encode())] + [
                (f'{encoding}-{alignment}', encode(b'x' * alignment + value + b'y' * 3))
                for encoding, encode in [('base64', base64.b64encode), ('base64url', base64.urlsafe_b64encode)]
                for alignment in range(3)]:
            for wrap in (False, True):
                encoded = b'\n'.join(data[n:n + 64] for n in range(0, len(data), 64)) if wrap and name != 'raw' else data
                path.write_bytes(b'x' * 1023 + encoded + b'z' * 500)
                self.assertTrue(self.checker.hits(path, needles, chunk_size=1024), (name, wrap))
        path.write_bytes(b'no key here')
        self.assertFalse(self.checker.hits(path, needles, chunk_size=1024))
        checks = self.work / 'checks.txt'
        checks.write_text('CONTROL_CHROME_PUBLIC_MODULUS ' + value.hex() + '\n')
        self.checker.build_log(checks, path)
        path.write_bytes(b'x' * 1023 + value + b'\n')
        with self.assertRaisesRegex(AssertionError, 'public modulus in build log'):
            self.checker.build_log(checks, path)
        for kind in (b'', b'RSA ', b'EC ', b'ENCRYPTED '):
            path.write_bytes(b'x' * (1024 * 1024 - 4) + b'-----BEGIN ' + kind + b'PRIVATE KEY-----\n')
            with self.assertRaisesRegex(AssertionError, 'private key marker'):
                self.checker.private_markers(path)
        with self.assertRaises(FileNotFoundError):
            list(self.checker.regular_files(self.work / 'absent'))

    def test_image_and_runner_wire_all_chrome_checks(self):
        image = (ROOT / 'os/ci/image-checks.sh').read_text()
        runner = (ROOT / 'os/ci/check-image.sh').read_text()
        build = (ROOT / 'os/ci/check-build.sh').read_text()
        self.assertIn('python3 -I -B /tmp/aresos-chrome-image-check.py image', image)
        self.assertIn('mount --bind / "$chrome_scan_root"', image)
        self.assertIn('image "$chrome_scan_root"', image)
        self.assertIn('umount "$chrome_scan_root"', image)
        checker = (ROOT / 'os/ci/control/chrome_image.py').read_text()
        self.assertIn('private_scan(scan_root)', checker)
        self.assertIn("regular_files(scan_root, excluded=tuple(scan_root / name for name in ('proc', 'sys', 'dev')))", checker)
        self.assertIn('chrome_image.py:/tmp/aresos-chrome-image-check.py:ro', runner)
        self.assertNotIn('rmdir /etc/opt/chrome/policies', image)
        self.assertIn('pkaction --action-id org.aresos.control.chrome-loosen --verbose', image)
        self.assertEqual(image.count('systemd-tmpfiles --create /usr/lib/tmpfiles.d/aresos-control-chrome.conf'), 2)
        self.assertIn('chrome_image.py compare', runner)
        self.assertIn('chrome_image.py build-log evidence/image/checks.txt evidence/build.log', build)
        self.assertLess(build.index('bash os/ci/check-image.sh'), build.index('chrome_image.py build-log'))
        release_check = 'bash os/ci/check-image.sh localhost/aresos:check "$kind"'
        self.assertEqual(build.count('bash os/ci/check-image.sh'), 1)
        self.assertIn(release_check, build)
        self.assertLess(build.index(release_check), build.index('--tag localhost/aresos:vm'))
        self.assertLess(build.index(release_check), build.index('bash os/ci/control/runner.sh layer'))

    def test_image_metadata_rejects_wrong_mode_owner_group_and_unsafe_parents(self):
        path = self.work / 'record.json'

        def info(mode, uid=0, gid=0):
            return os.stat_result((mode, 0, 0, 1, uid, gid, 0, 0, 0, 0))

        rows = {parent: info(0o040755) for parent in path.parents}
        rows[path] = info(0o100644)
        with patch.object(pathlib.Path, 'lstat', lambda p: rows[p]):
            self.checker.owned(path, 0o644)
            for name, target, changed in (
                    ('file mode', path, info(0o100600)), ('file writable', path, info(0o100666)),
                    ('file owner', path, info(0o100644, uid=1001)), ('file group', path, info(0o100644, gid=250)),
                    ('file link', path, info(0o120777)), ('file is a folder', path, info(0o040644)),
                    ('parent owner', path.parent, info(0o040755, uid=1001)),
                    ('parent group', path.parent, info(0o040755, gid=250)),
                    ('parent writable', path.parent, info(0o040775)), ('parent link', path.parent, info(0o120755))):
                previous = rows[target]
                rows[target] = changed
                with self.assertRaises(AssertionError, msg=name):
                    self.checker.owned(path, 0o644)
                rows[target] = previous

    def test_chrome_links_keep_the_readonly_image_root_and_pin_etc_parents(self):
        def info(mode, uid=0, gid=0):
            return os.stat_result((mode, 0, 0, 1, uid, gid, 0, 0, 0, 0))

        root = pathlib.Path('/')
        for name, target in self.checker.LINKS.items():
            path = pathlib.Path(name)
            rows = {parent: info(0o040755) for parent in path.parents}
            rows[root] = info(0o040555)
            rows[path] = info(0o120777)
            with patch.object(pathlib.Path, 'lstat', lambda p: rows[p]), \
                    patch.object(self.checker.os, 'readlink', return_value=target) as link:
                self.checker.owned_link(path, target)
                for label, changed_path, changed in (
                        ('ordinary file', path, info(0o100644)),
                        ('link owner', path, info(0o120777, uid=1001)),
                        ('link group', path, info(0o120777, gid=250)),
                        ('parent mode', path.parent, info(0o040555)),
                        ('parent writable', path.parent, info(0o040775)),
                        ('root owner', root, info(0o040555, uid=1001)),
                        ('root group', root, info(0o040555, gid=250)),
                        ('root mode', root, info(0o040755)),
                        ('root writable', root, info(0o040575))):
                    previous = rows[changed_path]
                    rows[changed_path] = changed
                    with self.assertRaises(AssertionError, msg=f'{name}: {label}'):
                        self.checker.owned_link(path, target)
                    rows[changed_path] = previous
                link.return_value = '/tmp/another-bundle.json'
                with self.assertRaises(AssertionError):
                    self.checker.owned_link(path, target)


class ChromePrivateScanTest(unittest.TestCase):
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        self.root = self.work / 'image'
        self.root.mkdir()
        self.checker = load_chrome_check()
        self.marker = b'-----BEGIN ' + b'PRIVATE KEY-----\n'
        for name in ('tmp', 'var/tmp', 'root'):
            (self.root / name).mkdir(parents=True)

    def scan(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            evidence = self.checker.private_scan(self.root)
        rows = [json.loads(line.removeprefix('CONTROL_CHROME_SCAN_LINK '))
                for line in output.getvalue().splitlines()]
        self.assertEqual(rows, evidence, 'every link observation is retained in checks.txt')
        return evidence

    def test_linked_folder_with_private_marker_fails_for_each_scan_name(self):
        target = self.root / 'var/scan-content'
        target.mkdir()
        (target / 'key').write_bytes(self.marker)
        for name in ('tmp', 'var/tmp', 'root'):
            with self.subTest(name=name):
                link = self.root / name
                link.rmdir()
                link.symlink_to('scan-content' if name == 'var/tmp' else 'var/scan-content')
                with self.assertRaisesRegex(AssertionError, 'private key marker'):
                    self.scan()
                link.unlink()
                link.mkdir()

    def test_missing_link_target_passes_and_is_recorded_for_each_scan_name(self):
        for name in ('tmp', 'var/tmp', 'root'):
            with self.subTest(name=name):
                link = self.root / name
                link.rmdir()
                target = 'roothome' if name == 'var/tmp' else 'var/roothome'
                link.symlink_to(target)
                self.assertEqual(self.scan(), [dict(path=name, target=target,
                                                   resolved='var/roothome', status='missing')])
                link.unlink()
                link.mkdir()

    def test_absolute_link_uses_image_contents_never_the_host_view(self):
        # Both views exist, entirely in this test's scratch directory. Host
        # Path.resolve() would choose the clean decoy and miss the image key.
        outside = (self.work / 'host-decoy').absolute()
        outside.mkdir()
        target = self.root / outside.as_posix().lstrip('/')
        target.mkdir(parents=True)
        (outside / 'key').write_bytes(b'clean host decoy')
        (target / 'key').write_bytes(self.marker)
        link = self.root / 'root'
        link.rmdir()
        link.symlink_to(outside)
        with self.assertRaisesRegex(AssertionError, 'private key marker'):
            self.scan()
        (target / 'key').write_bytes(b'clean image content')
        (outside / 'key').write_bytes(self.marker)
        rows = self.scan()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['status'], 'present')
        self.assertEqual(rows[0]['resolved'], target.relative_to(self.root).as_posix())

    def test_unreadable_folder_fails_instead_of_becoming_a_missing_target(self):
        target = self.root / 'var/roothome'
        target.mkdir()
        (self.root / 'root').rmdir()
        (self.root / 'root').symlink_to('var/roothome')
        scandir = os.scandir

        def unreadable(path):
            if pathlib.Path(path) == target:
                raise PermissionError('unreadable image folder')
            return scandir(path)

        # Inject the kernel's read error even on CI jobs running as root.
        with patch.object(self.checker.os, 'scandir', unreadable):
            with self.assertRaisesRegex(PermissionError, 'unreadable image folder'):
                self.scan()

    def test_read_and_lstat_errors_and_missing_plain_names_fail(self):
        path = self.root / 'root/file'
        path.write_bytes(b'content')
        with patch.object(pathlib.Path, 'open', side_effect=PermissionError('unreadable image file')):
            with self.assertRaisesRegex(PermissionError, 'unreadable image file'):
                self.scan()
        lstat = pathlib.Path.lstat

        def unreadable(entry, *args, **kwargs):
            if entry == path:
                raise PermissionError('unreadable image metadata')
            return lstat(entry, *args, **kwargs)

        with patch.object(pathlib.Path, 'lstat', unreadable):
            with self.assertRaisesRegex(PermissionError, 'unreadable image metadata'):
                self.scan()
        path.unlink()
        (self.root / 'root').rmdir()
        with self.assertRaises(FileNotFoundError):
            self.scan()

    def test_nested_and_parent_links_are_resolved_inside_the_image(self):
        (self.root / 'var/tmp').rmdir()
        (self.root / 'var').rmdir()
        (self.root / 'storage/tmp').mkdir(parents=True)
        (self.root / 'var').symlink_to('/storage')
        (self.root / 'tmp/nested').symlink_to('/var/secret')
        (self.root / 'storage/secret').write_bytes(self.marker)
        with self.assertRaisesRegex(AssertionError, 'private key marker'):
            self.scan()
        (self.root / 'storage/secret').write_bytes(b'clean')
        self.assertTrue(self.scan())

    def test_parent_traversal_stops_at_image_root(self):
        (self.root / 'root').rmdir()
        (self.root / 'root').symlink_to('../../../../var/tmp')
        (self.root / 'var/tmp/key').write_bytes(self.marker)
        # Scan only root here: scanning var/tmp first would hide an escape bug.
        with self.assertRaisesRegex(AssertionError, 'private key marker'):
            self.checker.private_scan(self.root, names=('root',))

    def test_missing_plain_child_of_existing_link_target_still_fails(self):
        (self.root / 'var/tmp').rmdir()
        (self.root / 'var').rmdir()
        (self.root / 'storage').mkdir()
        (self.root / 'var').symlink_to('/storage')
        with self.assertRaises(FileNotFoundError):
            self.scan()

    def test_link_cycles_and_non_directory_parents_fail(self):
        link = self.root / 'root/loop'
        for target in ('loop', '.', '/root'):
            with self.subTest(target=target):
                link.symlink_to(target)
                with self.assertRaises(OSError):
                    self.scan()
                link.unlink()
        (self.root / 'file').write_bytes(b'ordinary file')
        link.symlink_to('/file/child')
        with self.assertRaises(NotADirectoryError):
            self.scan()


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



class GhImageTest(unittest.TestCase):
    """Exercise the packages step's checks, without importing any host RPM key."""
    def setUp(self):
        self.work = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.work)
        self.code = heredoc('os/build.sh', "python3 - /tmp/aresos /tmp/ares-gh / <<'PY'\n")
        self.ns = {'__name__': 'gh_fixture'}
        exec(compile(self.code, 'build.sh gh', 'exec'), self.ns)
        self.pin = json.loads((ROOT / 'os/gh.lock.json').read_text())
        self.payload_paths = self.pin['payload_paths'].copy()
        self.key = ROOT / 'os' / self.pin['signing_key']['file']
        self.package = self.work / 'gh.rpm'
        self.package.write_bytes(b'fixture rpm')
        self.pin['sha256'] = sha256(self.package.read_bytes())
        self.fingerprint = self.pin['signing_key']['fingerprint']
        self.scripts = ''
        self.nevra = self.pin['nevra']
        self.signature = (str(self.package) + ':\n    Header OpenPGP V4 RSA/SHA512 signature, key fingerprint: '
                          + self.fingerprint + ': OK\n    Header SHA256 digest: OK\n    Payload SHA256 digest: OK\n')
        self.base = 'a' * 40 + ' fixture base key'
        self.added = self.fingerprint + ' fixture signing key'
        self.keys = [self.base]
        self.import_extra = False
        self.leave_key = False
        self.calls = []

    def output(self, *args):
        self.calls.append(args)
        if args == ('rpmkeys', '--list'):
            return '\n'.join(self.keys) + '\n'
        if args[:3] == ('rpmkeys', '--checksig', '--verbose'):
            return self.signature
        if args[:3] == ('rpm', '-qp', '--nosignature'):
            if args[3:5] == ('--qf', '[%{FILENAMES}\n]'):
                return '\n'.join(self.payload_paths) + '\n'
            if '--scripts' in args:
                self.assertIn('--triggers', args)
                self.assertIn('--filetriggers', args)
                return self.scripts
            return self.nevra
        self.fail(f'Unexpected command: {args}')

    def command(self, args, **kwargs):
        self.calls.append(tuple(args))
        if args[:2] == ['rpmkeys', '--import']:
            self.keys.append(self.added)
            if self.import_extra:
                self.keys.append('b' * 40 + ' fixture second imported key')
        elif args[:2] == ['rpmkeys', '--delete']:
            if not self.leave_key:
                self.keys = [row for row in self.keys if row.split()[0] != args[2]]
        elif args[0] == 'curl':
            self.assertIn('--proto-redir', args)
            self.assertEqual(args[args.index('--proto') + 1], '=https')
            pathlib.Path(args[args.index('-o') + 1]).write_bytes(self.package.read_bytes())
        elif args[0] == 'cpio':
            self.assertEqual(args, ['cpio', '--extract', '--to-stdout', '--quiet', './usr/bin/gh'])
            self.assertEqual(self.keys, [self.base], 'key cleanup must precede extraction')
            kwargs['stdout'].write(b'fixture binary')
        else:
            self.fail(f'Unexpected mutation command: {args}')
        return subprocess.CompletedProcess(args, 0)

    @contextlib.contextmanager
    def fixtures(self):
        with patch.dict(self.ns, output=self.output, check_key=lambda *args: None), \
                patch('subprocess.run', self.command):
            yield

    def verify(self):
        with self.fixtures():
            self.ns['verify_rpm'](self.pin, self.key, self.package, self.work)

    def test_lock_shape_order_provenance_and_committed_licence(self):
        pin = json.loads((ROOT / 'os/gh.lock.json').read_text())
        self.assertEqual(list(pin), ['nevra', 'url', 'sha256', 'signing_key', 'binary_sha256', 'license_sha256',
                                    'payload_paths'])
        key = pin['signing_key']
        self.assertEqual(list(key)[:4], ['file', 'source', 'sha256', 'fingerprint'])
        self.assertEqual(key['file'], 'keys/github-cli-rpm.pub')
        for digest in (pin['sha256'], pin['binary_sha256'], pin['license_sha256'], key['sha256'], key['source_sha256']):
            self.assertRegex(digest, r'^[0-9a-f]{64}$')
        self.assertEqual(key['fingerprint'], '7f38bbb59d064dbcb3d84d725612b36462313325')
        self.assertEqual(key['provenance']['published_fingerprints'],
                         ['2c6106201985b60e6c7ac87323f3d4ea75716059', key['fingerprint']])
        self.assertEqual(key['source'], 'https://cli.github.com/packages/githubcli-archive-keyring.asc')
        self.assertTrue(key['provenance']['documentation'].startswith('https://github.com/cli/cli/'))
        self.assertTrue(key['provenance']['confirmation'])
        self.assertEqual(sha256(self.key.read_bytes()), key['sha256'])
        self.assertEqual(sha256((ROOT / 'os/config/usr/share/licenses/gh/LICENSE').read_bytes()), pin['license_sha256'])
        version = re.fullmatch(r'gh-(\d+\.\d+\.\d+)-1.x86_64', pin['nevra']).group(1)
        self.assertEqual(pin['url'], f'https://github.com/cli/cli/releases/download/v{version}/gh_{version}_linux_amd64.rpm')
        self.assertGreaterEqual(tuple(map(int, version.split('.'))), (2, 102, 0))

    def test_committed_key_is_exactly_one_and_second_key_is_refused(self):
        self.ns['check_key'](self.key, self.fingerprint, self.work)
        second = self.work / 'two-keys.pub'
        second.write_bytes(self.key.read_bytes() + (ROOT / 'os/keys/google-linux-signing-key.pub').read_bytes())
        with self.assertRaisesRegex(AssertionError, 'exactly the pinned primary key'):
            self.ns['check_key'](second, self.fingerprint, self.work)
        with self.assertRaisesRegex(AssertionError, 'exactly the pinned primary key'):
            self.ns['check_key'](self.key, '0' * 40, self.work)

    def test_valid_rpm_and_all_imported_keys_are_removed(self):
        self.import_extra = True
        self.verify()
        self.assertEqual(self.keys, [self.base])
        deleted = [c[2] for c in self.calls if c[:2] == ('rpmkeys', '--delete')]
        self.assertEqual(set(deleted), {self.fingerprint, 'b' * 40})

    def test_payload_list_must_equal_the_verified_rpm(self):
        self.payload_paths.append('/usr/share/man/man1/gh-new-command.1')
        with self.assertRaisesRegex(AssertionError, 'RPM payload paths differ from its pin'):
            self.verify()
        self.assertEqual(self.keys, [self.base])

    def check_payload(self):
        code = heredoc('os/ci/image-checks.sh', "# --- gh is one pinned binary, not an installed RPM or a repository.\npython3 - <<'PY'\n")
        code = code.split("# Check gh's own payload; the base may carry similarly named files.\n", 1)[1]
        image = self.work / 'image'
        path_class = pathlib.Path
        stream = io.StringIO()
        with patch('pathlib.Path', side_effect=lambda name: image / path_class(name).relative_to('/')), \
                contextlib.redirect_stdout(stream):
            exec(compile(code, 'image-checks.sh gh payload', 'exec'),
                 dict(pathlib=pathlib, json=json, pin=self.pin, version='fixture'))
        return stream.getvalue()

    def payload_file(self, name):
        path = self.work / 'image' / name.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fixture')
        return path

    def test_image_payload_check_allows_only_the_binary(self):
        self.payload_file('/usr/bin/gh')
        self.assertIn('CONTROL_GH_IMAGE_PASS', self.check_payload())

    def test_image_payload_check_names_each_man_page_or_completion(self):
        names = ('/usr/share/man/man1/gh.1', '/usr/share/bash-completion/completions/gh',
                 '/usr/share/fish/vendor_completions.d/gh.fish', '/usr/share/zsh/site-functions/_gh')
        for name in names:
            with self.subTest(name=name):
                self.assertIn(name, self.pin['payload_paths'])
                path = self.payload_file(name)
                with self.assertRaisesRegex(AssertionError, re.escape(name)):
                    self.check_payload()
                path.unlink()
        for name in names:
            self.payload_file(name)
        with self.assertRaises(AssertionError) as raised:
            self.check_payload()
        for name in names:
            self.assertIn(name, str(raised.exception))

    def test_image_payload_check_refuses_a_dangling_payload_link(self):
        name = '/usr/share/man/man1/gh.1'
        path = self.payload_file(name)
        path.unlink()
        path.symlink_to('missing-target')
        with self.assertRaisesRegex(AssertionError, re.escape(name)):
            self.check_payload()

    def test_image_payload_check_allows_unrelated_base_file_and_logs_old_match(self):
        name = '/usr/share/bash-completion/completions/gh-base-tool'
        self.assertNotIn(name, self.pin['payload_paths'])
        self.payload_file('/usr/bin/gh')
        self.payload_file(name)
        output = self.check_payload()
        self.assertIn('CONTROL_GH_IMAGE_PASS', output)
        self.assertIn('INFO gh legacy name matches=', output)
        self.assertIn('gh-base-tool', output)

    def test_wrong_rpm_hash_and_key_hash_stop_before_import(self):
        for field in ('rpm', 'key'):
            with self.subTest(field=field):
                pin = copy.deepcopy(self.pin)
                if field == 'rpm':
                    self.pin['sha256'] = '0' * 64
                else:
                    self.pin['signing_key']['sha256'] = '0' * 64
                with self.assertRaisesRegex(AssertionError, 'differs from its pin'):
                    self.verify()
                self.assertFalse(any(c[:2] == ('rpmkeys', '--import') for c in self.calls))
                self.pin = pin

    def test_wrong_nevra_and_rpm_with_script_are_refused_before_import(self):
        self.nevra = 'gh-0.0.0-1.x86_64'
        with self.assertRaisesRegex(AssertionError, 'NEVRA'):
            self.verify()
        self.nevra = self.pin['nevra']
        self.scripts = 'postinstall scriptlet (using /bin/sh):\necho fixture\n'
        with self.assertRaisesRegex(AssertionError, 'scripts or triggers'):
            self.verify()
        self.assertFalse(any(c[:2] == ('rpmkeys', '--import') for c in self.calls))

    def test_bad_signature_lines_other_key_and_nonzero_verifier_fail(self):
        good = self.signature
        for bad in (good.replace('digest: OK', 'digest: BAD'),
                    good.replace(self.fingerprint, '0' * 40),
                    good + 'unrecognized diagnostic\n', str(self.package) + ':\n',
                    good.replace('Header OpenPGP', 'Payload OpenPGP')):
            with self.subTest(bad=bad):
                self.signature = bad
                with self.assertRaisesRegex(AssertionError, 'signature|fingerprint'):
                    self.verify()
                self.assertEqual(self.keys, [self.base])
        real = self.output
        def failed(*args):
            if args[:2] == ('rpmkeys', '--checksig'):
                raise subprocess.CalledProcessError(1, args)
            return real(*args)
        with self.fixtures(), patch.dict(self.ns, output=failed):
            with self.assertRaises(subprocess.CalledProcessError):
                self.ns['verify_rpm'](self.pin, self.key, self.package, self.work)
        self.assertEqual(self.keys, [self.base])

    def test_leftover_imported_key_is_refused(self):
        self.leave_key = True
        with self.assertRaisesRegex(AssertionError, 'changed RPM keyring'):
            self.verify()

    def install(self, binary_hash=None, license_hash=None):
        source, dest = self.work / 'os', self.work / 'image'
        source.mkdir(exist_ok=True)
        (source / 'keys').mkdir(exist_ok=True)
        shutil.copyfile(self.key, source / 'keys/github-cli-rpm.pub')
        license = source / 'config/usr/share/licenses/gh/LICENSE'
        license.parent.mkdir(parents=True, exist_ok=True)
        license.write_bytes(b'fixture licence')
        self.pin['binary_sha256'] = binary_hash or sha256(b'fixture binary')
        self.pin['license_sha256'] = license_hash or sha256(license.read_bytes())
        (source / 'gh.lock.json').write_text(json.dumps(self.pin))
        (dest / 'usr/bin').mkdir(parents=True, exist_ok=True)
        (dest / 'usr/share/aresos/manifest').mkdir(parents=True, exist_ok=True)
        self.signature = self.signature.replace(str(self.package), str(self.work / 'download/gh.rpm'))
        class RpmPipe:
            def __init__(pipe, args, **kwargs):
                self.assertEqual(args, ['rpm2cpio', str(self.work / 'download/gh.rpm')])
                pipe.stdout = io.BytesIO(b'fixture cpio')
            def __enter__(pipe): return pipe
            def __exit__(pipe, *args): pipe.stdout.close()
            def wait(pipe): return 0
        with self.fixtures(), patch('subprocess.Popen', RpmPipe), patch('os.chown') as chown:
            self.ns['install_gh'](source, self.work / 'download', dest)
        self.assertEqual(chown.call_args_list[0].args, (dest / 'usr/bin/gh', 0, 0))
        return dest

    def test_extracts_only_binary_and_lock_with_modes_and_cleans_scratch(self):
        dest = self.install()
        self.assertEqual({p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()},
                         {'usr/bin/gh', 'usr/share/aresos/manifest/gh.lock.json'})
        self.assertEqual((dest / 'usr/bin/gh').read_bytes(), b'fixture binary')
        self.assertEqual((dest / 'usr/bin/gh').stat().st_mode & 0o777, 0o755)
        self.assertEqual((dest / 'usr/share/aresos/manifest/gh.lock.json').stat().st_mode & 0o777, 0o644)
        self.assertFalse((self.work / 'download').exists())

    def test_wrong_binary_hash_and_licence_hash_refused(self):
        for kw, message in (({'binary_hash': '0' * 64}, 'gh binary'),
                            ({'license_hash': '0' * 64}, 'gh licence')):
            with self.subTest(kw=kw), self.assertRaisesRegex(AssertionError, message):
                self.install(**kw)
            self.assertFalse((self.work / 'image/usr/bin/gh').exists())
            self.assertFalse((self.work / 'download').exists())

    def test_resolve_is_informational_on_success_failure_and_malformed_reply(self):
        code = heredoc('os/ci/check-resolve.sh', "python3 - /tmp/aresos/gh.lock.json <<'PY' | tee \"$out/gh.txt\" || true\n")
        for response in ('{"tag_name":"v9.8.7"}', '{}', '{', '{"tag_name":"injected\\nline"}', None):
            stream = io.StringIO()
            with patch.object(sys, 'argv', ['-', str(ROOT / 'os/gh.lock.json')]), \
                    patch('subprocess.check_output', return_value=response,
                          side_effect=subprocess.CalledProcessError(22, ['curl']) if response is None else None), \
                    contextlib.redirect_stdout(stream):
                exec(compile(code, 'check-resolve.sh gh', 'exec'), {})
            text = stream.getvalue()
            self.assertEqual(len(text.splitlines()), 1)
            self.assertIn('INFO gh newest=', text)
            self.assertIn('pinned=' + self.pin['nevra'], text)
            self.assertIn('v9.8.7' if response == '{"tag_name":"v9.8.7"}' else 'unavailable (lookup failed)', text)

    def test_packages_key_list_spans_both_imports_and_image_checks_are_wired(self):
        build = (ROOT / 'os/build.sh').read_text()
        before = build.index('rpmkeys --list | sort > /tmp/ares-chrome/keys-before.txt')
        self.assertLess(before, build.index('rpmkeys --import /tmp/aresos/keys/google-linux-signing-key.pub'))
        self.assertLess(build.index(self.code), build.index('cmp /tmp/ares-chrome/keys-before.txt /tmp/ares-chrome/keys-final.txt'))
        self.assertIn("'Installed gh binary differs from control.json'", build)
        image = (ROOT / 'os/ci/image-checks.sh').read_text()
        for token in ('CONTROL_GH_IMAGE_PASS', "['rpm', '-q', 'gh']", 'license_sha256', "['runuser', '-u', 'ares', '--']"):
            self.assertIn(token, image)
        check = (ROOT / 'os/ci/check-image.sh').read_text()
        comparison = 'cmp os/gh.lock.json "$out/manifest/gh.lock.json"'
        self.assertIn(comparison, check)
        (self.work / 'os').mkdir()
        reviewed = self.work / 'os/gh.lock.json'
        shutil.copyfile(ROOT / 'os/gh.lock.json', reviewed)
        shipped = self.work / 'out/manifest/gh.lock.json'
        shipped.parent.mkdir(parents=True)
        shipped.write_bytes(reviewed.read_bytes())
        def compare():
            return subprocess.run(['bash', '-c', comparison], cwd=self.work,
                                  env={**os.environ, 'out': 'out'}, capture_output=True).returncode
        self.assertEqual(compare(), 0)
        shipped.write_bytes(reviewed.read_bytes() + b'\n')
        self.assertNotEqual(compare(), 0, 'even JSON-equivalent changes must fail the byte comparison')
        shipped.unlink()
        self.assertNotEqual(compare(), 0, 'a missing image lock must fail')
        self.assertIn("'chrome_build', 'gh'):", check)
        self.assertIn('CONTROL_GH_CHECKOUT_PASS', check)

if __name__ == '__main__':
    unittest.main()
