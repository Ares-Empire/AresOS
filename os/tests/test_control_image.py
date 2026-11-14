"""Package 18c, Part A: the Control tools in the image (build.sh control, the image checks).

The install map runs for real: `build.sh control-tree` is the same Python as the image build's `control` mode, into a
temporary folder. The image build's own extras (pip, the wheel record, the self-checks) run only in the image build;
their record is checked here with stand-ins for pip's report and the vendored tree.
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

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
    '/usr/libexec/aresos-control/launch.py': ('0644', 'control/launch.py'),
    '/usr/share/aresos/control/user-mcp.json': ('0644', 'control/settings/user-mcp.json'),
}
DERIVED = ('/usr/lib/tmpfiles.d/aresos-control-folders.conf', '/usr/share/aresos/control/proxy.json',
           '/usr/share/aresos/control/service.json')
LINK = ('/etc/systemd/system/multi-user.target.wants/aresos-toold.service', '/usr/lib/systemd/system/aresos-toold.service')


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def heredoc(path, start):
    """The Python of the one heredoc that `start` opens in `path`."""
    text = (ROOT / path).read_text()
    assert text.count(start) == 1, (path, start)
    return text.split(start, 1)[1].split('\nPY\n', 1)[0]


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
        self.assertEqual(result.stdout.splitlines(), [f'CONTROL_INSTALLED {len(record["files"])} files'])
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
        self.assertEqual(differ, sorted(DERIVED))
        # An owner the file policy cannot use, or more than one account, stops the build.
        for broken in (declaration.replace('/var/home/ares', '/home/ares'), declaration + 'u other 1003 - /var/home/other\n',
                       declaration.replace('1001:1001', '999:999')):
            (other / 'config/usr/lib/sysusers.d/aresos.conf').write_text(broken)
            shutil.rmtree(self.work / 'other', ignore_errors=True)
            result, _ = self.tree(os_dir=other, dest=self.work / 'other')
            self.assertNotEqual(result.returncode, 0, broken)

    def test_the_image_build_records_its_commit_wheels_and_vendored_tree(self):
        lock, current = {}, None
        for line in (CONTROL / 'requirements.lock').read_text().splitlines():
            if match := re.match(r'^([A-Za-z0-9._-]+)==(\S+) \\$', line):
                current = (match[1], match[2])
                lock[current] = []
            elif match := re.match(r'^\s+--hash=sha256:([0-9a-f]{64})', line):
                lock[current].append(match[1])
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
        record.update(source_revision=REVISION, wheels=[dict(name='mcp')],
                      vendor={'/usr/lib/aresos-control': dict(mode='0755', sha256=None)})
        code = heredoc('os/ci/check-image.sh', 'python3 - "$out/manifest/control.json" '
                       '"$expected/root/usr/share/aresos/manifest/control.json" "$(git rev-parse HEAD)" <<\'PY\'\n')

        def check(image, revision=REVISION):
            path = self.work / 'image.json'
            path.write_text(json.dumps(image))
            return subprocess.run([sys.executable, '-I', '-c', code, str(path),
                                   str(self.work / 'root/usr/share/aresos/manifest/control.json'), revision],
                                  capture_output=True, text=True, timeout=60)

        result = check(record)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'from {REVISION}, 1 wheels from requirements.lock', result.stdout)
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
