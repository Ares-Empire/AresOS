"""Package 27: the release build's diff rules, guard ledger and publish branch."""
import ast
import copy
import json
import os
import pathlib
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import release_diff as rd
import rehearsal_guard as guard


def name_of(nevra):
    """Split NEVRA the way rpm's %{NAME} does for these Fedora names."""
    body = nevra.rsplit('.', 1)[0] if rd.arch(nevra) else nevra
    return re.sub(r'-(?:[0-9]+:)?[^-]+-[^-]+$', '', body)


def lock_nevras(raw):
    return [p['nevra'] for p in json.loads(raw)['packages']]


class PackageDiffTest(unittest.TestCase):
    def setUp(self):
        old_lock = lock_nevras(rd.git_bytes(rd.PREVIOUS_SOURCE, 'os/packages.lock.json'))
        new_lock = lock_nevras((ROOT / 'os/packages.lock.json').read_bytes())
        new_lock.append(json.loads((ROOT / 'os/google-chrome.lock.json').read_text())['nevra'])
        # Release 6's (and so release 13's) retained package list.
        old = (ROOT / 'os/manifest/ci/06c/image-full-1/packages.txt').read_text().split()
        self.old = {n: name_of(n) for n in old}
        added = sorted(set(new_lock) - set(old_lock))
        replaced = {(name_of(n), rd.arch(n)) for n in added}
        new = [n for n in old if (name_of(n), rd.arch(n)) not in replaced] + added
        self.new = {n: name_of(n) for n in new}
        self.old_lock, self.new_lock = old_lock, new_lock

    def test_the_real_lock_change_is_exactly_packages_21s_and_the_renewed_pin(self):
        rows, added, removed = rd.package_diff(self.old, self.new, self.old_lock, self.new_lock)
        self.assertEqual(len(added), 17)  # 16 new lock entries and Chrome
        self.assertIn('google-chrome-stable-157.0.8103.50-1.x86_64', added)
        self.assertIn('xdg-desktop-portal-wlr-0.8.4-1.fc44.x86_64', removed)
        self.assertIn('util-linux-2.41.5-1.fc44.x86_64', removed)
        self.assertEqual(len(removed), 12)
        self.assertTrue(all(row['reason'].startswith('package 21') for row in rows))

    def test_an_unlocked_extra_missing_replacement_or_unknown_name_stops(self):
        extra = dict(self.new, **{'nano-8.0-1.fc44.x86_64': 'nano'})
        with self.assertRaisesRegex(AssertionError, 'added packages differ'):
            rd.package_diff(self.old, extra, self.old_lock, self.new_lock)
        lost = dict(self.new)
        dropped = next(n for n in self.old if n.startswith('foot-'))
        del lost[dropped]
        with self.assertRaisesRegex(AssertionError, 'unexplained package change|without its locked replacement'):
            rd.package_diff(self.old, lost, self.old_lock, self.new_lock)
        with patch.dict(rd.PACKAGE_REASONS, clear=True), self.assertRaisesRegex(AssertionError, 'unexplained package change'):
            rd.package_diff(self.old, self.new, self.old_lock, self.new_lock)


class AccountRulesTest(unittest.TestCase):
    GROUP = b'root:x:0:\nwheel:x:10:ares-recovery\nares:x:1001:\n'
    SHADOW = b'root:!*:20384:0:99999:7:::\nares:!*:20384::::::\n'

    def test_wheel_gains_ares_and_shadow_dates_may_be_the_build_date(self):
        self.assertTrue(rd.accounts_explained('etc/group', self.GROUP, self.GROUP.replace(b'ares-recovery', b'ares,ares-recovery')))
        self.assertTrue(rd.accounts_explained('etc/gshadow-', b'wheel:!::ares-recovery\n', b'wheel:!::ares-recovery,ares\n'))
        self.assertTrue(rd.accounts_explained('etc/shadow', self.SHADOW, self.SHADOW.replace(b'20384', b'20402')))

    def test_every_other_account_change_stops(self):
        for name, old, new in (
                ('etc/group', self.GROUP, self.GROUP.replace(b'ares-recovery', b'ares,ares-recovery,guest')),
                ('etc/group', self.GROUP, self.GROUP.replace(b'wheel:x:10', b'wheel:x:11')),
                ('etc/group', self.GROUP, self.GROUP + b'extra:x:2000:\n'),
                ('etc/shadow', self.SHADOW, self.SHADOW.replace(b'ares:!*', b'ares:$6$hash')),
                ('etc/passwd', b'ares:x:1001:1001::/var/home/ares:/bin/bash\n', b'ares:x:1001:1001::/var/home/ares:/bin/sh\n'),
                ('etc/shadow', self.SHADOW, self.SHADOW.replace(b':99999:', b':1:'))):
            with self.subTest(name=name, new=new):
                self.assertFalse(rd.accounts_explained(name, old, new))

    def test_subids_add_exactly_one_range_for_ares(self):
        self.assertTrue(rd.subids_explained(b'ares-recovery:100000:65536\n', b'ares-recovery:100000:65536\nares:524288:65536\n'))
        self.assertTrue(rd.subids_explained(None, b'ares:524288:65536\n'))
        self.assertFalse(rd.subids_explained(b'', b'ares:524288:65536\nother:1:2\n'))
        self.assertFalse(rd.subids_explained(b'ares:1:2\n', b'ares:1:2\nares:524288:65536\n'))


class PolkitTransformTest(unittest.TestCase):
    SAMPLE = '''<policyconfig>
 <action id="org.freedesktop.Flatpak.app-update">
  <defaults><allow_any>auth_admin_keep</allow_any><allow_inactive>auth_admin_keep</allow_inactive><allow_active>yes</allow_active></defaults>
  <annotate key="org.freedesktop.policykit.imply">org.freedesktop.Flatpak.runtime-install org.freedesktop.Flatpak.runtime-update</annotate>
 </action>
 <action id="org.freedesktop.Flatpak.app-install">
  <defaults><allow_any>auth_admin</allow_any><allow_inactive>auth_self_keep</allow_inactive><allow_active>auth_admin_keep </allow_active></defaults>
 </action>
</policyconfig>
'''

    def test_the_classifier_applies_exactly_build_sh_s_polkit_edits(self):
        script = (ROOT / 'os/build.sh').read_text()
        block = script.split("# every installed default uncached, for every account, and refuse leftovers.\npython3 - <<'PY'\n", 1)[1]
        block = block.split('\nPY\n', 1)[0]
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            actions = pathlib.Path(directory)
            (actions / 'org.freedesktop.Flatpak.policy').write_text(self.SAMPLE, newline='\n')
            other = self.SAMPLE.replace('org.freedesktop.Flatpak.app-update', 'org.example.cached').replace(
                '<annotate key="org.freedesktop.policykit.imply">org.freedesktop.Flatpak.runtime-install org.freedesktop.Flatpak.runtime-update</annotate>', '')
            (actions / 'org.example.policy').write_text(other, newline='\n')
            code = block.replace("pathlib.Path('/usr/share/polkit-1/actions')", 'pathlib.Path(' + repr(str(actions)) + ')')
            self.assertNotEqual(code, block)
            subprocess.run([sys.executable, '-c', code], check=True, capture_output=True)
            for name, original in (('org.freedesktop.Flatpak.policy', self.SAMPLE), ('org.example.policy', other)):
                with self.subTest(name=name):
                    built = (actions / name).read_text()
                    self.assertEqual(rd.polkit_transform(name, original), built)
                    self.assertNotIn('_keep', built)


class ClassifierTest(unittest.TestCase):
    def tree(self, root, files):
        for rel, value in files.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(value, tuple):
                os.symlink(value[1], path)
            else:
                path.write_bytes(value)
                path.chmod(0o644)  # explicit: an earlier test may have left another umask

    def classifier(self, old, new, base):
        roots = []
        for files in (old, new, base):
            root = pathlib.Path(tempfile.mkdtemp(dir=ROOT / 'os/tests'))
            self.addCleanup(shutil.rmtree, root)
            self.tree(root, files)
            roots.append(root)
        policy = dict(unmasked={'flatpak-system-helper.service'}, executables=rd.CHMOD_0755,
                      old_has_children=lambda rel: False)
        return rd.Classifier(roots, dict(old=[], new=[]), dict(old=set(), new={'/opt/google/chrome/chrome'}), policy), roots

    @unittest.skipIf(os.name == 'nt', 'symlinks and xattrs need Linux')
    def test_build_steps_are_verified_and_anything_else_is_unexplained(self):
        guard_line = rd.BREW_GUARD.encode()
        old = {'etc/profile.d/brew-bash-completion.sh': b'#!/bin/sh\n' + guard_line + b'\necho brew\n',
               'etc/systemd/system/flatpak-system-helper.service': ('link', '/dev/null'),
               'etc/unexplained.conf': b'old\n'}
        new = {'etc/profile.d/brew-bash-completion.sh': b'#!/bin/sh\necho brew\n',
               'usr/bin/google-chrome': ('link', 'google-chrome-stable'),
               'usr/bin/google-chrome-stable': ('link', '/usr/lib/opt/google/chrome/google-chrome'),
               'usr/lib/opt/google/chrome/chrome': b'binary',
               'etc/default/google-chrome': rd.CHROME_DEFAULTS,
               'etc/unexplained.conf': b'new\n'}
        base = {'etc/profile.d/brew-bash-completion.sh': b'#!/bin/sh\necho brew\n'}
        classifier, (o, n, b) = self.classifier(old, new, base)
        for rel in sorted(set(old) | set(new)):
            with self.subTest(rel=rel):
                found = classifier.classify(rel, rd.entry(o, rel), rd.entry(n, rel))
                if rel == 'etc/unexplained.conf':
                    self.assertIsNone(found)
                else:
                    self.assertIsNotNone(found)
                    self.assertEqual(found[0], 'build')
        # A Chrome link to anywhere else, or a profile edit other than the reviewed guard, is unexplained.
        (n / 'usr/bin/google-chrome').unlink(); os.symlink('/tmp/elsewhere', n / 'usr/bin/google-chrome')
        self.assertIsNone(classifier.classify('usr/bin/google-chrome', None, rd.entry(n, 'usr/bin/google-chrome')))
        (o / 'etc/profile.d/brew-bash-completion.sh').write_bytes(b'#!/bin/sh\necho other\necho brew\n')
        rel = 'etc/profile.d/brew-bash-completion.sh'
        self.assertIsNone(classifier.classify(rel, rd.entry(o, rel), rd.entry(n, rel)))

    @unittest.skipIf(os.name == 'nt', 'symlinks and modes need Linux')
    def test_exact_rules_do_not_depend_on_the_process_umask(self):
        # An in-process owner.main() once left umask 077 behind (test_owner_entry).
        mask = os.umask(0o077)
        try:
            self.test_run_two_exact_rules_explain_only_their_exact_paths()
        finally:
            os.umask(mask)

    @unittest.skipIf(os.name == 'nt', 'symlinks and modes need Linux')
    def test_run_two_exact_rules_explain_only_their_exact_paths(self):
        """Run 42817411051's 12 classifier gaps: each rule is exact; near misses stay unexplained."""
        choice = 'usr/share/polkit-1/actions/org.fedoraproject.FirewallD1.desktop.policy.choice'
        link = 'usr/share/polkit-1/actions/org.fedoraproject.FirewallD1.policy'
        policy = PolkitTransformTest.SAMPLE.replace('org.freedesktop.Flatpak.app-update', 'org.fedoraproject.FirewallD1.all')
        transformed = rd.polkit_transform('org.fedoraproject.FirewallD1.policy', policy)
        self.assertNotEqual(policy, transformed)
        old = {choice: policy.encode(), rd.RPM_DATABASE: b'old database', link: ('link', 'org.fedoraproject.FirewallD1.desktop.policy.choice')}
        new = {choice: transformed.encode(), rd.RPM_DATABASE: b'new database', link: ('link', 'org.fedoraproject.FirewallD1.desktop.policy.choice')}
        new.update({path: ('link', target) for path, target in rd.CHROME_NSS_LINKS.items()})
        new['usr/lib/opt/google/chrome/libfoo.so.1d'] = ('link', '/lib64/libfoo.so')
        new['usr/lib/opt/google/chrome/libnss3.so.2d'] = ('link', '/lib64/libnss3.so')
        base = {choice: policy.encode(), link: ('link', 'org.fedoraproject.FirewallD1.desktop.policy.choice')}
        classifier, (o, n, b) = self.classifier(old, new, base)
        # The image's files are root's; this fixture's are the test user's.
        real_entry = rd.entry
        def as_root(root, rel):
            value = real_entry(root, rel)
            if value is not None and (value['uid'], value['gid']) == (os.getuid(), os.getgid()):
                value.update(uid=0, gid=0)
            return value
        self.enterContext(patch.object(rd, 'entry', side_effect=as_root))
        for path in rd.CHROME_DIRECTORIES:
            (n / path).mkdir(parents=True, exist_ok=True); (n / path).chmod(0o755)
        (n / 'usr/share/gnome-control-center/other').mkdir()
        explain = lambda rel: classifier.classify(rel, rd.entry(o, rel), rd.entry(n, rel))
        for rel in [choice, rd.RPM_DATABASE, *rd.CHROME_NSS_LINKS, *rd.CHROME_DIRECTORIES]:
            with self.subTest(explained=rel):
                self.assertIsNotNone(explain(rel))
        self.assertEqual(len(rd.CHROME_NSS_LINKS), 7)
        # Another name, another target, another mode or other bytes: unexplained.
        for rel in ('usr/lib/opt/google/chrome/libfoo.so.1d', 'usr/lib/opt/google/chrome/libnss3.so.2d',
                    'usr/share/gnome-control-center/other'):
            with self.subTest(near_miss=rel):
                self.assertIsNone(explain(rel))
        target = n / 'usr/lib/opt/google/chrome/libnss3.so.1d'
        target.unlink(); os.symlink('/lib64/libnss3.so.2', target)
        self.assertIsNone(explain('usr/lib/opt/google/chrome/libnss3.so.1d'))
        (n / 'usr/share/gnome-control-center/default-apps').chmod(0o700)
        self.assertIsNone(explain('usr/share/gnome-control-center/default-apps'))
        (n / choice).write_bytes(transformed.replace('auth_admin', 'yes').encode())
        self.assertIsNone(explain(choice))
        (n / choice).write_bytes(transformed.encode())
        (n / link).unlink(); os.symlink('org.fedoraproject.FirewallD1.server.policy.choice', n / link)
        self.assertIsNone(explain(choice))
        self.assertEqual(stat.S_IMODE((o / rd.RPM_DATABASE).stat().st_mode), 0o644)
        (n / rd.RPM_DATABASE).chmod(0o600)
        self.assertIsNone(explain(rd.RPM_DATABASE))
        self.assertIsNone(explain('usr/share/rpm/rpmdb.sqlite-shm'))

    @unittest.skipIf(os.name == 'nt', 'modes need Linux')
    def test_no_rule_explains_a_mode_or_owner_change_of_an_existing_directory(self):
        # The run 2 finding: cp -a of os/config gave /etc/sudoers.d the checkout's 0755.
        classifier, (o, n, b) = self.classifier({'etc/sudoers.d/keep': b'x'}, {'etc/sudoers.d/keep': b'x'}, {})
        (o / 'etc/sudoers.d').chmod(0o750); (n / 'etc/sudoers.d').chmod(0o755)
        classifier.config = classifier.config | {'etc/sudoers.d/aresos-everyday'}
        self.assertIsNone(classifier.classify('etc/sudoers.d', rd.entry(o, 'etc/sudoers.d'), rd.entry(n, 'etc/sudoers.d')))

    def test_generated_paths_are_listed_and_units_cannot_be_generated(self):
        classifier = rd.Classifier.__new__(rd.Classifier)
        self.assertEqual(classifier.generated_rule('usr/lib/sysimage/rpm/rpmdb.sqlite', {}, {})[0], 'generated')
        self.assertEqual(classifier.generated_rule('etc/ld.so.cache', {}, {})[0], 'generated')
        self.assertIsNone(classifier.generated_rule('usr/lib/systemd/system/x.service', {}, {}))
        self.assertIsNone(classifier.generated_rule('etc/sudoers.d/x', {}, {}))


class GuardLedgerTest(unittest.TestCase):
    def setUp(self):
        guard.configure('27')
        self.addCleanup(guard.configure, '11c')

    def test_package27_allows_one_release_one_checks_run_and_three_rehearsals(self):
        self.assertEqual(guard.SETTINGS['dispatch_caps'], {'release-27': 5, 'checks': 1, 'update': 3})
        self.assertEqual(guard.SETTINGS['publish_cap'], 1)
        self.assertEqual(guard.BRANCH, 'pkg/27-first-update-release')
        workflow = (ROOT / '.github/workflows/os-image.yml').read_text()
        for kind, title in guard.SETTINGS['titles'].items():
            self.assertIn(title.split(' (')[0], workflow)
        runs = []
        job = dict(name='Package 27 release build, image diff, VM and publish', conclusion='failure', steps='not a list')

        def api(path):
            return dict(workflow_runs=runs) if path.startswith('actions/runs?') else dict(total_count=1, jobs=[job])
        base = dict(event='workflow_dispatch', head_sha='a' * 40, run_attempt=1, status='completed',
                    conclusion='failure', created_at='2026-11-10T01:00:00Z')
        with patch.object(guard, 'api', side_effect=api):
            runs.append(dict(base, id=1, display_title='Package 27 image release'))
            with self.assertRaisesRegex(AssertionError, 'malformed job steps'):
                guard.budget(0)
            job['steps'] = []
            result = guard.budget(0)
            # An unaccountable job is charged its whole timeout.
            self.assertEqual(result['consumed_minutes'], 180)
            runs.append(dict(base, id=2, display_title='Package 27 image release'))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-27'], 2)
            runs.append(dict(base, id=3, display_title='Package 27 image release'))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-27'], 3)
            runs.append(dict(base, id=4, display_title='Package 27 image release'))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-27'], 4)
            runs.append(dict(base, id=5, display_title='Package 27 image release'))
            self.assertEqual(guard.budget(0)['dispatch_counts']['release-27'], 5)
            runs.append(dict(base, id=6, display_title='Package 27 image release'))
            with self.assertRaisesRegex(AssertionError, 'release-27 dispatch allowance exhausted|exceeds 1200'):
                guard.budget(0)
            for _ in range(5): runs.pop()
            for number in range(3):
                runs.append(dict(base, id=10 + number, display_title='Two-disk rehearsal (update)'))
            self.assertEqual(guard.budget(0)['dispatch_counts']['update'], 3)
            runs.append(dict(base, id=20, display_title='Two-disk rehearsal (update)'))
            with self.assertRaisesRegex(AssertionError, 'update dispatch allowance exhausted|exceeds 1200'):
                guard.budget(0)

    def test_update_rehearsal_defers_native_proof_only_for_its_own_budget_step(self):
        self.assertEqual(guard.native_gate('update', 'probe-budget-ci', dict(runs=[]), 'a' * 40)['status'], 'pending')
        with self.assertRaisesRegex(AssertionError, 'no current probe native preflight'):
            guard.native_gate('update', 'ci', dict(runs=[]), 'a' * 40)


class AptPatienceTest(unittest.TestCase):
    def test_only_the_release_job_waits_longer_for_the_snapshot_mirror(self):
        import yaml
        jobs = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)['jobs']
        step = lambda job: next(s for s in jobs[job]['steps'] if s.get('name', '').startswith('Install pinned'))
        release = step('release-27')
        self.assertEqual(release['timeout-minutes'], '40')
        self.assertEqual(release['env'], {'ARESOS_APT_RETRIES': '5', 'ARESOS_APT_TIMEOUT': '60'})
        # Package 21's reviewed check build keeps its step as reviewed.
        check = step('check-build')
        self.assertEqual(check['timeout-minutes'], '20')
        self.assertNotIn('env', check)
        script = (ROOT / 'os/ci/install-tools.sh').read_text()
        self.assertIn('retries=${ARESOS_APT_RETRIES:-3}', script)
        self.assertIn('-o Acquire::Retries="$retries"', script)
        self.assertIn('options+=(-o Acquire::http::Timeout="$ARESOS_APT_TIMEOUT" -o Acquire::https::Timeout="$ARESOS_APT_TIMEOUT")', script)
        self.assertNotIn('Acquire::Retries=3', script)

    def test_the_update_rehearsal_waits_as_long_and_other_rehearsals_keep_theirs(self):
        import yaml
        job = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)['jobs']['rehearsal']
        install, = [s for s in job['steps'] if s.get('name') == 'Install pinned rehearsal tools on disposable runner']
        self.assertEqual(sorted(install['env']), ['ARESOS_APT_RETRIES', 'ARESOS_APT_TIMEOUT'])
        self.assertIn('bash os/ci/install-tools.sh', install['run'])

        def value(text, mode):
            expression = re.fullmatch(r'\$\{\{(.*)\}\}', text.strip()).group(1)
            return eval(expression.replace('inputs.rehearsal', repr(mode)).replace('&&', ' and ').replace('||', ' or '),
                        {'__builtins__': {}}, {})
        # The same patience as the release job for package 27's update rehearsal...
        self.assertEqual([value(install[k], 'update') for k in ('timeout-minutes',)] +
                         [value(install['env'][k], 'update') for k in ('ARESOS_APT_RETRIES', 'ARESOS_APT_TIMEOUT')],
                         [40, '5', '60'])
        # ...and every other rehearsal keeps 20 minutes, three retries and apt's own timeouts.
        for mode in ('inspect', 'fixture', 'probe', 'part-b', 'keyboard', 'owner-tools'):
            self.assertEqual([value(install['timeout-minutes'], mode), value(install['env']['ARESOS_APT_RETRIES'], mode),
                              value(install['env']['ARESOS_APT_TIMEOUT'], mode)], [20, '', ''])
        script = (ROOT / 'os/ci/install-tools.sh').read_text()
        self.assertIn('retries=${ARESOS_APT_RETRIES:-3}', script)
        self.assertIn('if [[ -n ${ARESOS_APT_TIMEOUT:-} ]]; then', script)

    @unittest.skipIf(os.name == 'nt' or shutil.which('bash') is None, 'needs a Linux bash')
    def test_apt_patience_values_must_be_numbers(self):
        script = (ROOT / 'os/ci/install-tools.sh').read_text().split('sudo apt-get', 1)[0]
        script = script.replace('jq -r .repository os/ci/toolchain.json', 'echo http://example.invalid')
        script = script.replace("jq -r '.suites[]' os/ci/toolchain.json", 'echo noble')
        script += 'printf "%s' + chr(92) + 'n" "${options[@]}"' + chr(10)
        with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
            run = lambda **env: subprocess.run(['bash', '-c', script], cwd=directory, capture_output=True, text=True,
                                               env=dict(os.environ, **env))
            self.assertIn('Acquire::Retries=3', run().stdout)
            # Other rehearsals get the variables empty: the shared defaults stay.
            empty = run(ARESOS_APT_RETRIES='', ARESOS_APT_TIMEOUT='')
            self.assertEqual(empty.returncode, 0)
            self.assertIn('Acquire::Retries=3', empty.stdout)
            self.assertNotIn('Timeout', empty.stdout)
            good = run(ARESOS_APT_RETRIES='5', ARESOS_APT_TIMEOUT='60').stdout
            self.assertIn('Acquire::Retries=5', good)
            self.assertIn('Acquire::https::Timeout=60', good)
            for env in (dict(ARESOS_APT_RETRIES='5;x'), dict(ARESOS_APT_TIMEOUT='60 -o x')):
                with self.subTest(env=env):
                    self.assertNotEqual(run(**env).returncode, 0)


class PublishBranchTest(unittest.TestCase):
    @unittest.skipIf(os.name == 'nt' or shutil.which('bash') is None, 'needs a Linux bash')
    def test_only_the_two_release_branches_may_publish(self):
        env = dict(os.environ, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_REPOSITORY='Ares-Empire/AresOS',
                   GITHUB_REF_NAME='pkg/23-minecraft-starts', PATH=os.environ.get('PATH', ''))
        result = subprocess.run(['bash', 'os/ci/publish.sh'], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Refusing to publish from pkg/23-minecraft-starts', result.stderr)
        text = (ROOT / 'os/ci/publish.sh').read_text()
        self.assertIn('pkg/27-first-update-release) release=27 ;;', text)
        self.assertLess(text.index('esac'), text.index('rehearsal_guard.py publish-ci'))


class VerifyRelease27Test(unittest.TestCase):
    """verify_release.py binds release 27 to its source trees and its own release job."""
    TREES = {path: format(n, '040x') for n, path in enumerate(sorted(['os/Containerfile', 'os/.containerignore', 'os/build.sh',
        'os/packages.lock.json', 'os/google-chrome.lock.json', 'os/config', 'os/policy', 'os/manifest/base.json',
        'os/keys', 'os/tests/audit.py']), 1)}

    def verify(self, release=None, job='Package 27 release build, image diff, VM and publish', head=None, trees=None):
        import ast, contextlib, io
        source = 'b' * 40
        release = release or dict(reference='ghcr.io/ares-empire/aresos@sha256:' + '27' * 32, source_commit=source,
            visibility='private', base=json.loads((ROOT / 'os/manifest/base.json').read_text())['reference'],
            run='https://github.com/Ares-Empire/AresOS/actions/runs/42807087845',
            signature=dict(method='cosign keyless', issuer='https://token.actions.githubusercontent.com',
                identity='https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/pkg/27-first-update-release'),
            image_diff=dict(status='passed', unexplained=[]), job_token_read=dict(status='passed', owner_token_used=False),
            source_trees=trees if trees is not None else [dict(tree=tree, path=path) for path, tree in self.TREES.items()])
        head = dict(self.TREES, **(head or {}))
        run = dict(head_sha=source, path='.github/workflows/os-image.yml', head_branch='pkg/27-first-update-release',
                   event='workflow_dispatch', display_title='Package 27 image release', run_attempt=1)
        prefix = 'repos/Ares-Empire/AresOS/actions/runs/42807087845'

        def output(command, **kwargs):
            if command == ['git', 'rev-parse', '--is-shallow-repository']:
                return b'false\n'
            if command[:2] == ['git', 'rev-parse']:
                return (head[command[2].removeprefix('HEAD:')] + '\n').encode()
            self.assertEqual(command[:2], ['gh', 'api'])
            return json.dumps(run if command[2] == prefix else dict(total_count=1, jobs=[dict(name=job, conclusion='success')])).encode()
        original = pathlib.Path.read_text
        read = lambda path, *a, **k: json.dumps(release) if path.as_posix() == 'evidence/release.json' else original(path, *a, **k)
        path = ROOT / 'os/ci/verify_release.py'
        with patch.object(sys, 'argv', ['verify_release.py', '42807087845']), \
             patch.dict(os.environ, GITHUB_REPOSITORY='Ares-Empire/AresOS'), patch('pathlib.Path.read_text', read), \
             patch('subprocess.check_output', side_effect=output), patch('subprocess.run') as git, \
             contextlib.redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as done:
            exec(compile(ast.parse(path.read_text()), str(path), 'exec'), {'__name__': '__main__'})
        git.assert_not_called()  # no fetch or ancestry: a squash merge keeps the trees
        return done.exception.code

    def test_release27_passes_on_its_own_trees_and_job(self):
        self.assertEqual(self.verify(), 0)

    def test_tree_rows_put_the_object_id_before_the_path(self):
        record = json.loads((ROOT / 'os/manifest/releases/27.json').read_text())
        self.assertTrue(record['source_trees'] and all(list(row) == ['tree', 'path'] for row in record['source_trees']))
        with self.assertRaises(AssertionError):
            self.verify(trees=dict(self.TREES))

    def test_a_changed_runtime_tree_another_job_or_identity_refuses(self):
        with self.assertRaisesRegex(AssertionError, 'payload changed: os/config'):
            self.verify(head={'os/config': 'f' * 40})
        with self.assertRaisesRegex(AssertionError, 'must have succeeded'):
            self.verify(job='image')
        with self.assertRaises(AssertionError):
            self.verify(release=dict(reference='ghcr.io/ares-empire/aresos@sha256:' + '27' * 32, source_commit='b' * 40,
                visibility='private', base=json.loads((ROOT / 'os/manifest/base.json').read_text())['reference'],
                run='https://github.com/Ares-Empire/AresOS/actions/runs/42807087845',
                signature=dict(method='cosign keyless', issuer='https://token.actions.githubusercontent.com',
                    identity='https://github.com/Ares-Empire/AresOS/.github/workflows/os-image.yml@refs/heads/main'),
                image_diff=dict(status='passed', unexplained=[]), job_token_read=dict(status='passed', owner_token_used=False),
                source_trees=[dict(tree=tree, path=path) for path, tree in self.TREES.items()]))


class PolkitSweepTest(unittest.TestCase):
    """The update rehearsal asks polkitd about every action for his desktop session."""

    def setUp(self):
        import owner_vm
        self.vm = owner_vm
        self.reviewed = sorted(json.loads((ROOT / 'os/ci/polkit-review.json').read_text())['passwordless'])

    def sweep(self, **changes):
        value = dict(session_active='yes', session_remote='no', session_scope=True, actions=700,
                     answers={'0': 100, '1': 300, '2': 300}, passwordless=self.reviewed[:100])
        value.update(changes)
        guest = Mock()
        guest.capture_json.return_value = value
        with patch.object(self.vm.td, 'save') as save:
            result = self.vm.polkit_sweep(guest, 'release-27')
        name, script = guest.capture_json.call_args.args
        self.assertEqual(name, 'release-27-polkit')
        self.assertIn('pkcheck', script)
        save.assert_called_once_with('release-27-polkit-sweep', value)
        return result

    def test_the_guest_program_parses(self):
        import ast
        ast.parse(self.vm.POLKIT)

    def test_reviewed_passwordless_actions_pass(self):
        self.assertEqual(self.sweep()['actions'], 700)

    def test_a_passwordless_action_beyond_the_review_stops(self):
        with self.assertRaisesRegex(AssertionError, 'beyond the reviewed list: org.freedesktop.Flatpak.app-install'):
            self.sweep(passwordless=self.reviewed[:3] + ['org.freedesktop.Flatpak.app-install'])

    def test_an_inactive_or_remote_session_or_other_scope_stops(self):
        for changes in (dict(session_active='no'), dict(session_remote='yes'), dict(session_scope=False)):
            with self.subTest(**changes), self.assertRaisesRegex(AssertionError, 'active local desktop session'):
                self.sweep(**changes)

    def test_an_unanswered_action_stops(self):
        for changes in (dict(answers={'0': 1, '127': 1}), dict(answers={'3': 1}), dict(actions=0)):
            with self.subTest(**changes), self.assertRaisesRegex(AssertionError, 'did not answer every action'):
                self.sweep(**changes)


class DispatchMatrixTest(unittest.TestCase):
    def test_package27_runs_only_its_release_checks_and_update_rehearsal(self):
        import yaml
        from test_owner_staged_release import condition
        workflow = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        branch = {'github.ref_name': 'pkg/27-first-update-release'}
        for mode in ('', 'inspect', 'fixture', 'probe', 'part-b', 'keyboard', 'owner-tools', 'update'):
            for name, job in workflow['jobs'].items():
                with self.subTest(mode=mode, job=name):
                    self.assertEqual(condition(job['if'], mode=mode, **branch), name == 'rehearsal' and mode == 'update')
        for name, job in workflow['jobs'].items():
            with self.subTest(release=name):
                self.assertEqual(condition(job['if'], mode='', **branch, **{'inputs.release_27': True}), name == 'release-27')
                self.assertEqual(condition(job['if'], mode='', **branch, **{'inputs.checks_only': True}), name == 'regressions')
                self.assertFalse(condition(job['if'], mode='update', **branch, **{'inputs.release_27': True}))
        # No other branch can use the update rehearsal or the release-27 job.
        for name, job in workflow['jobs'].items():
            with self.subTest(other=name):
                self.assertFalse(condition(job['if'], mode='update', **{'github.ref_name': 'pkg/23-minecraft-starts'}))
                self.assertFalse(condition(job['if'], mode='', **{'github.ref_name': 'main', 'inputs.release_27': True})
                                 and name == 'release-27')


UPDATE_REF = 'pkg/27-first-update-release'
# GitHub's own variables for an update dispatch on the package 27 branch.
UPDATE_GITHUB = dict(GITHUB_REF_NAME=UPDATE_REF, GITHUB_EVENT_NAME='workflow_dispatch', GITHUB_ACTIONS='true',
                     GITHUB_REPOSITORY='Ares-Empire/AresOS', GITHUB_SHA='a' * 40, GITHUB_RUN_ID='1', GITHUB_RUN_ATTEMPT='1')
UPDATE_INPUTS = {'github.ref_name': UPDATE_REF, 'github.event_name': 'workflow_dispatch', 'inputs.rehearsal': 'update',
                 'inputs.checks_only': False, 'inputs.release_13': False, 'inputs.release_27': False,
                 'inputs.check_build': '', 'inputs.switch_from_run': '', 'inputs.probe_run': ''}
UNKNOWN = object()


def workflow_expression(expression):
    """A workflow expression's value for an update dispatch on the package 27 branch."""
    expression = re.sub(r'\bsecrets\.\w+', repr('secret'), expression)
    for name, value in UPDATE_INPUTS.items():
        expression = expression.replace(name, repr(value))
    for call, value in (('always()', 'True'), ('success()', 'True'), ('cancelled()', 'False'), ('failure()', 'False')):
        expression = expression.replace(call, value)
    expression = expression.replace('&&', ' and ').replace('||', ' or ')
    expression = re.sub(r'!(?!=)', ' not ', expression)
    return eval(expression, {'__builtins__': {}}, {})


def workflow_text(value):
    """Text as the runner renders it: each ${{ }} replaced by its string."""
    def render(match):
        result = workflow_expression(match.group(1))
        return ('true' if result else 'false') if isinstance(result, bool) else str(result)
    return re.sub(r'\$\{\{(.*?)\}\}', render, value, flags=re.S)


def constant(value):
    """A value an ast.Constant can hold (lists as tuples), or UNKNOWN."""
    if isinstance(value, (list, tuple)):
        items = tuple(constant(item) for item in value)
        return UNKNOWN if any(item is UNKNOWN for item in items) else items
    return value if value is None or isinstance(value, (str, int, float, bool)) else UNKNOWN


class GateScan:
    """The environment and argument gates a script surely reaches, evaluated for one step.

    Starting from the script's top-level code (as `__main__`), it follows the
    functions that code calls, in this module or in an os/ci module it
    imports, and runs the top level of each imported module (an imported
    module's `__main__` block is skipped). Code runs **surely** when every
    branch above it is known to run:
    - an `if` whose test depends only on os.environ, sys.argv and names bound
      from them is followed into the branch that runs, and stays sure;
    - any other `if`, a loop body or an `except` handler is unsure;
    - a function is sure only when sure code calls it by name; anything else
      it is merely referenced by (a callback, a dict of commands, a method of
      an unresolved object) is followed as unsure.
    In sure code, every `assert` and `observations.check` condition that
    depends only on those values is evaluated; for `a and b` each part counts
    on its own. Unsure code is followed for what it calls but its gates are
    not judged, so a gate for another package's branch cannot fail the scan.
    """
    ALLOWED = (ast.Expression, ast.Constant, ast.Tuple, ast.List, ast.Set, ast.BoolOp, ast.And, ast.Or, ast.Compare,
               ast.Eq, ast.NotEq, ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.UnaryOp, ast.Not, ast.Load)
    DEFINITIONS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    UNSURE_EXPRESSIONS = (ast.IfExp, ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)

    def __init__(self, environment, argv, sources=None):
        self.environment, self.argv, self.sources = environment, list(argv), sources
        self.modules, self.globals, self.done, self.results = {}, {}, set(), []

    def run(self, script):
        self.load(script, '__main__')
        return self.results

    def text(self, path):
        return self.sources[path] if self.sources is not None else (ROOT / path).read_text(encoding='utf-8')

    def source(self, module):
        path = 'os/ci/' + module.split('.')[0] + '.py'
        known = path in self.sources if self.sources is not None else (ROOT / path).exists()
        return path if known else None

    def module(self, path):
        if path not in self.modules:
            tree = ast.parse(self.text(path))
            definitions = {s.name: s for s in tree.body if isinstance(s, self.DEFINITIONS)}
            aliases = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if self.source(alias.name):
                            aliases[alias.asname or alias.name] = (self.source(alias.name), None)
                elif isinstance(node, ast.ImportFrom) and node.module and not node.level and self.source(node.module):
                    for alias in node.names:
                        aliases[alias.asname or alias.name] = (self.source(node.module), alias.name)
            self.modules[path] = (tree, definitions, aliases)
        return self.modules[path]

    def load(self, path, name=None):
        """Run a module's top level once, as on import (surely: importing runs it)."""
        if ('module', path) in self.done:
            return
        self.done.add(('module', path))
        tree, _, _ = self.module(path)
        self.globals[path] = {'__name__': name or pathlib.Path(path).stem}
        self.visit(path, tree.body, self.globals[path], sure=True, top=True)

    def definition(self, path, name, sure):
        """A function that code calls (sure) or names (unsure); for a class, its methods."""
        _, definitions, _ = self.module(path)
        if name not in definitions or ('definition', path, name, sure) in self.done:
            return
        self.done.add(('definition', path, name, sure))
        self.load(path)
        node = definitions[name]
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                body = item.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) else [item]
                # Constructing the class runs __init__; other methods run on objects we do not follow.
                self.visit(path, body, self.globals[path], sure=sure and getattr(item, 'name', '') == '__init__')
        else:
            self.visit(path, node.body, self.globals[path], sure=sure)

    def resolve(self, path, node):
        """The (module, name) a Name or module.attribute refers to, or None."""
        _, definitions, aliases = self.module(path)
        if isinstance(node, ast.Name):
            if node.id in definitions:
                return path, node.id
            if node.id in aliases and aliases[node.id][1] is not None:
                return aliases[node.id]
        if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                and node.value.id in aliases and aliases[node.value.id][1] is None):
            return aliases[node.value.id][0], node.attr
        return None

    def sure_calls(self, node):
        """Calls in an expression that run whenever the expression does."""
        if isinstance(node, self.UNSURE_EXPRESSIONS):
            return
        if isinstance(node, ast.BoolOp):
            yield from self.sure_calls(node.values[0])
            return
        if isinstance(node, ast.Call):
            yield node
        for child in ast.iter_child_nodes(node):
            yield from self.sure_calls(child)

    def reach(self, path, node, sure):
        called = {id(call.func) for call in self.sure_calls(node)} if sure else set()
        for reference in ast.walk(node):
            target = self.resolve(path, reference) if isinstance(reference, (ast.Name, ast.Attribute)) else None
            if target is not None and not (isinstance(reference, ast.Name) and not isinstance(reference.ctx, ast.Load)):
                self.definition(*target, sure=id(reference) in called)

    def read(self, node):
        """The value of an environment or argument read, or UNKNOWN."""
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            if ast.unparse(node.value) == 'os.environ' and isinstance(node.slice.value, str):
                return self.environment.get(node.slice.value)
            if ast.unparse(node.value) == 'sys.argv' and isinstance(node.slice.value, int):
                index = node.slice.value
                return self.argv[index] if -len(self.argv) <= index < len(self.argv) else None
        if isinstance(node, ast.Subscript) and ast.unparse(node.value) == 'sys.argv' and isinstance(node.slice, ast.Slice):
            bounds = [part.value if isinstance(part, ast.Constant) else UNKNOWN if part is not None else None
                      for part in (node.slice.lower, node.slice.upper, node.slice.step)]
            return UNKNOWN if any(bound is UNKNOWN for bound in bounds) else tuple(self.argv[slice(*bounds)])
        if (isinstance(node, ast.Call) and ast.unparse(node.func) in ('os.environ.get', 'os.getenv')
                and node.args and isinstance(node.args[0], ast.Constant) and not node.keywords):
            default = node.args[1] if len(node.args) > 1 else ast.Constant(None)
            if isinstance(default, ast.Constant):
                return self.environment.get(node.args[0].value, default.value)
        return UNKNOWN

    def evaluate(self, node, names):
        """(value, derived): UNKNOWN unless the node depends only on reads and names bound from them."""
        scan, derived = self, []

        class Bind(ast.NodeTransformer):
            def bound(self, node):
                value = constant(scan.read(node))
                if value is UNKNOWN:
                    return self.generic_visit(node)
                derived.append(True)
                return ast.Constant(value)
            visit_Subscript = visit_Call = bound

            def visit_Name(self, node):
                if node.id in names:
                    derived.append(True)
                    return ast.Constant(names[node.id])
                return node

        expression = ast.fix_missing_locations(ast.Expression(Bind().visit(copy.deepcopy(node))))
        if not all(isinstance(part, self.ALLOWED) for part in ast.walk(expression)):
            return UNKNOWN, False
        return eval(compile(expression, '<gate>', 'eval'), {'__builtins__': {}}), bool(derived)

    def gate(self, path, test, names, line):
        parts = test.values if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.And) else [test]
        for part in parts:
            value, derived = self.evaluate(part, names)
            if value is not UNKNOWN and derived:
                self.results.append((path, line, ast.unparse(part), bool(value)))

    def bind(self, target, value, names):
        if isinstance(target, ast.Name):
            names.pop(target.id, None)
            if value is not UNKNOWN:
                names[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            values = value if isinstance(value, tuple) and len(value) == len(target.elts) else [UNKNOWN] * len(target.elts)
            for element, item in zip(target.elts, values):
                self.bind(element, item, names)
        else:
            for node in ast.walk(target):
                if isinstance(node, ast.Name):
                    names.pop(node.id, None)

    def visit(self, path, body, names, sure, top=False):
        names = names if top else dict(names)
        for statement in body:
            if isinstance(statement, self.DEFINITIONS):
                for expression in statement.decorator_list + getattr(statement, 'bases', []):
                    self.reach(path, expression, sure)
                if not top and not isinstance(statement, ast.ClassDef):
                    self.visit(path, statement.body, names, sure=False)
                continue
            if isinstance(statement, ast.If):
                test, derived = self.evaluate(statement.test, names)
                if test is not UNKNOWN and (derived or isinstance(statement.test, ast.Constant)):
                    self.visit(path, statement.body if test else statement.orelse, names, sure, top)
                    continue
            if isinstance(statement, (ast.Import, ast.ImportFrom)):
                modules = ([alias.name for alias in statement.names] if isinstance(statement, ast.Import)
                           else [statement.module] if statement.module and not statement.level else [])
                for module in filter(self.source, modules):
                    self.load(self.source(module))
            compound = any(isinstance(getattr(statement, field, None), list) for field in ('body', 'orelse', 'finalbody'))
            headers = ([getattr(statement, field) for field in ('test', 'iter', 'subject') if hasattr(statement, field)]
                       + [item.context_expr for item in getattr(statement, 'items', [])]) if compound else [statement]
            for header in headers:
                self.reach(path, header, sure)
            if sure and isinstance(statement, ast.Assert):
                self.gate(path, statement.test, names, statement.lineno)
            elif sure and not compound:
                for node in self.sure_calls(statement):
                    if isinstance(node.func, ast.Attribute) and node.func.attr == 'check' and node.args:
                        self.gate(path, node.args[0], names, node.lineno)
            if isinstance(statement, ast.Assign):
                value, derived = self.evaluate(statement.value, names)
                for target in statement.targets:
                    self.bind(target, constant(value) if derived else UNKNOWN, names)
            else:
                # Any other rebinding (augmented, loop or with targets) forgets the name.
                targets = [getattr(statement, 'target', None)] + [i.optional_vars for i in getattr(statement, 'items', [])]
                for target in filter(None, targets):
                    self.bind(target, UNKNOWN, names)
            # A with or try body runs surely; an unknown if, a loop and an except handler do not.
            body_sure = sure and isinstance(statement, (ast.With, ast.AsyncWith, ast.Try))
            for field, field_sure in (('body', body_sure), ('orelse', False), ('finalbody', sure)):
                if isinstance(getattr(statement, field, None), list):
                    self.visit(path, getattr(statement, field), names, field_sure, top)
            for handler in getattr(statement, 'handlers', []):
                self.visit(path, handler.body, names, False, top)


def shell_condition(text, environment):
    """True, False or None (unknown) for `test A = B` / `test A != B` chains joined by || and &&."""
    def word(token):
        value = re.sub(r'\$\{?(\w+)\}?', lambda m: environment.get(m.group(1), ''), token)
        return None if '$' in value or '`' in value else value

    def test(part):
        try:
            tokens = shlex.split(part.strip())
        except ValueError:
            return None
        if tokens[:1] == ['['] and tokens[-1:] == [']']:
            tokens = ['test'] + tokens[1:-1]
        if len(tokens) != 4 or tokens[0] != 'test' or tokens[2] not in ('=', '!='):
            return None
        left, right = word(tokens[1]), word(tokens[3])
        if left is None or right is None:
            return None
        return (left == right) == (tokens[2] == '=')

    result = False
    for alternative in text.split('||'):
        values = [test(part) for part in alternative.split('&&')]
        both = None if None in values and False not in values else all(values)
        if both is True:
            return True
        if both is None:
            result = None
    return result


def shell_lines(run, environment):
    """The lines of a step's run script that can execute for this environment.

    Follows `if/elif/else/fi` over `test` comparisons of literals and
    variables (shell_condition); a branch with an unknown condition counts as
    possibly running. Heredoc bodies are data, not commands.
    """
    stack, heredoc = [], None
    for line in run.splitlines():
        stripped = line.strip()
        if heredoc is not None:
            heredoc = None if stripped == heredoc else heredoc
            continue
        active = all(level['active'] for level in stack)
        match = re.fullmatch(r'(if|elif) (.*); then', stripped)
        if match:
            if match.group(1) == 'if':
                stack.append(dict(parent=active, taken=False, active=False))
            level = stack[-1]
            condition = shell_condition(match.group(2), environment)
            level['active'] = level['parent'] and not level['taken'] and condition is not False
            level['taken'] = level['taken'] or condition is True
            continue
        if stripped == 'else':
            stack[-1]['active'] = stack[-1]['parent'] and not stack[-1]['taken']
            continue
        if stripped == 'fi':
            stack.pop()
            continue
        if active:
            yield line
        opened = re.search(r"<<-?\s*'?(\w+)'?\s*$", line)
        if opened:
            heredoc = opened.group(1)


def step_runs(step, environment):
    """Each os/ci Python script a step can run: its path, argv and `env -u` removals."""
    for line in shell_lines(workflow_text(step['run']), environment):
        for match in re.finditer(r'\bos/ci/[\w/-]+\.py\b', line):
            try:
                words = shlex.split(line[match.start():])
            except ValueError:
                words = line[match.start():].split()
            argv = [match.group(0)]
            for word in words[1:]:
                if re.match(r'(\d*[<>]|[;&|])', word):
                    break
                argv.append(word)
            yield match.group(0), argv, re.findall(r'\benv -u (\w+)', line[:match.start()])


def package_sets(path):
    """Each `REHEARSAL_PACKAGE in <set>` comparison in a module, with the set's value (or None)."""
    tree = ast.parse((ROOT / path).read_text(encoding='utf-8'))
    constants = {}
    for statement in tree.body:
        if isinstance(statement, ast.Assign) and len(statement.targets) == 1 and isinstance(statement.targets[0], ast.Name):
            try:
                constants[statement.targets[0].id] = eval(compile(ast.Expression(statement.value), path, 'eval'),
                                                          {'__builtins__': {}}, dict(constants))
            except Exception:
                pass
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.In, ast.NotIn))
                and re.fullmatch(r"os\.environ(\.get\('REHEARSAL_PACKAGE'.*\)|\['REHEARSAL_PACKAGE'\])", ast.unparse(node.left))):
            try:
                value = eval(compile(ast.Expression(node.comparators[0]), path, 'eval'), {'__builtins__': {}}, dict(constants))
            except Exception:
                value = None
            yield node.lineno, value


class OwnerHarnessPackagesTest(unittest.TestCase):
    """Package 27's update rehearsal runs in package 14's owner VM harness, so it takes the harness's branches.

    Run 42933781975 stopped at the installer: installer_webui.start() opened
    the virtio-serial WebUI transport only for packages 14 and 16, so nothing
    answered on host port 18080.
    """

    def test_every_package_set_naming_14_or_16_also_names_27(self):
        checked = []
        for path in sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'os/ci').glob('*.py')):
            for line, value in package_sets(path):
                self.assertIsNotNone(value, f'{path}:{line}: package set not readable')
                if {'14', '16'} & set(value):
                    checked.append(f'{path}:{line}')
                    self.assertIn('27', value, f'{path}:{line}: {value}')
        self.assertGreaterEqual(len(checked), 7, checked)

    def run_as(self, package, call):
        import installer_webui
        guest = Mock()
        with patch.dict(os.environ, REHEARSAL_PACKAGE=package), patch.object(installer_webui, 'read_keyboard'):
            call(installer_webui, guest)
        return guest.mock_calls

    def test_the_installer_drives_package_27_exactly_like_package_14(self):
        for call in (lambda module, guest: module.start(guest, 'install'),
                     lambda module, guest: module.readback(guest, 'install', '/dev/vda', '/dev/vdb')):
            self.assertEqual(self.run_as('27', call), self.run_as('14', call))
        # The WebUI transport is what run 42933781975 lacked.
        self.assertIn(unittest.mock.call.start_offline_webui_transport(),
                      self.run_as('27', lambda module, guest: module.start(guest, 'install')))


class UpdateJobGatesTest(unittest.TestCase):
    """Every script the update rehearsal job runs accepts the environment that job gives it.

    Run 42924871252 stopped in its capability step: owner_capabilities.py still
    allowed only the probe and owner-tools modes. For each step of the
    rehearsal job that runs for an update dispatch on the package 27 branch,
    this takes the environment the step really gets (workflow, job and step
    env, GitHub's own variables, `env -u` on the line) and the script's own
    arguments, and evaluates every environment or argument gate the script
    reaches (GateScan). The VM step's scripts are included.
    """

    def update_steps(self):
        import yaml
        workflow = yaml.load((ROOT / '.github/workflows/os-image.yml').read_text(), Loader=yaml.BaseLoader)
        job = workflow['jobs']['rehearsal']
        self.assertTrue(workflow_expression(job['if']))
        merged = {**workflow.get('env', {}), **job.get('env', {})}
        base = dict(UPDATE_GITHUB, **{k: workflow_text(v) for k, v in merged.items()})
        self.assertEqual(base['REHEARSAL_PACKAGE'], '27')
        for step in job['steps']:
            if 'run' in step and workflow_expression(step.get('if', 'success()')):
                yield step, dict(base, **{k: workflow_text(v) for k, v in step.get('env', {}).items()})

    def scan(self):
        failures, evaluated = [], set()
        for step, environment in self.update_steps():
            for script, argv, removed in step_runs(step, environment):
                for path, line, text, passed in GateScan({k: v for k, v in environment.items() if k not in removed},
                                                         argv).run(script):
                    evaluated.add(path)
                    if not passed:
                        failures.append(f"{step['name']}: {path}:{line}: {text}")
        return failures, evaluated

    def test_every_update_step_script_accepts_the_update_environment(self):
        failures, evaluated = self.scan()
        self.assertEqual(failures, [])
        # The scan really reached the gates of the job's native scripts.
        self.assertLessEqual({'os/ci/owner_capabilities.py', 'os/ci/owner_devices.py', 'os/ci/owner_media.py',
                              'os/ci/registry_auth.py', 'os/ci/rehearsal_guard.py'}, evaluated)

    def test_the_scan_follows_only_reached_code(self):
        sources = {
            'os/ci/fixture.py': (
                "import os, sys\n"
                "import helper\n"
                "def other():\n"
                "    assert os.environ['REHEARSAL_MODE'] == 'probe'\n"
                "def main():\n"
                "    mode, = sys.argv[1:]\n"
                "    if os.environ.get('REHEARSAL_PACKAGE') == '13':\n"
                "        other()\n"
                "    assert os.environ.get('REHEARSAL_MODE') in ('probe', 'owner-tools')\n"
                "    assert os.geteuid() == 0 and mode == 'update'\n"
                "    helper.require()\n"
                "if __name__ == '__main__':\n"
                "    main()\n"),
            'os/ci/helper.py': (
                "import os\n"
                "nodes = []\n"
                "def require():\n"
                "    assert os.environ.get('REHEARSAL_PACKAGE') in ('14', '27')\n"
                "    assert nodes\n"
                "def unused():\n"
                "    assert os.environ.get('REHEARSAL_PACKAGE') == '16'\n"
                "if __name__ == '__main__':\n"
                "    assert os.environ.get('REHEARSAL_MODE') == 'probe'\n"),
        }
        results = GateScan(dict(REHEARSAL_MODE='update', REHEARSAL_PACKAGE='27'), ['os/ci/fixture.py', 'update'],
                           sources).run('os/ci/fixture.py')
        self.assertEqual([(path, line, passed) for path, line, _, passed in results],
                         [('os/ci/fixture.py', 9, False), ('os/ci/fixture.py', 10, True), ('os/ci/helper.py', 4, True)])

    def test_the_step_scripts_and_their_arguments_come_from_the_job(self):
        runs = {(script, tuple(argv[1:])) for step, environment in self.update_steps()
                for script, argv, _ in step_runs(step, environment)}
        for expected in (('os/ci/owner_capabilities.py', ()), ('os/ci/rehearsal_guard.py', ('probe-budget-ci', '300')),
                         ('os/ci/rehearsal_guard.py', ('ci', '300')), ('os/ci/registry_auth.py', ('create',)),
                         ('os/ci/owner_devices.py', ()), ('os/ci/owner_vm.py', ('update',))):
            self.assertIn(expected, runs)
        # The VM step's shell branches for other packages do not run.
        self.assertFalse({script for script, _ in runs} & {'os/ci/keyboard_vm.py', 'os/ci/two_disk_vm.py'})

    def test_shell_branches_follow_the_environment(self):
        run = '\n'.join([
            'a',
            "if test '$REHEARSAL_PACKAGE' = 13; then", '  b',
            'elif test "$REHEARSAL_PACKAGE" = 14 || test "$REHEARSAL_PACKAGE" = 27; then', "  c <<'PY'", 'fi', 'PY',
            'elif test "$(cat x)" = y; then', '  d',
            'else', '  e', 'fi',
            'if command -v x; then', '  f', 'fi'])
        self.assertEqual([line.strip() for line in shell_lines(run, dict(REHEARSAL_PACKAGE='27'))],
                         ['a', "c <<'PY'", 'f'])
        self.assertEqual([line.strip() for line in shell_lines(run, dict(REHEARSAL_PACKAGE='16'))], ['a', 'd', 'e', 'f'])


if __name__ == '__main__':
    unittest.main()
