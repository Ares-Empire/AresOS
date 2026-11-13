"""Package 21: the everyday account like Windows, Chrome and daily-use fixes.

Owner, 2026-11-09: `ares` is an administrator behind its own password, Flatpak
and Homebrew work, Claude cannot use admin rights unless he types the password,
and Google Chrome is built into the image. These tests run the real files
without root; the throwaway CI image build checks the built image itself.
"""
import configparser
import hashlib
import importlib.machinery
import json
import os
import pathlib
import re
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'config'


def subids():
    loader = importlib.machinery.SourceFileLoader('aresos_subids', str(CONFIG / 'usr/libexec/aresos-subids'))
    return loader.load_module()


class SubordinateIdsTest(unittest.TestCase):
    def files(self, subuid, subgid):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        etc = pathlib.Path(directory.name)
        (etc / 'subuid').write_text(subuid)
        (etc / 'subgid').write_text(subgid)
        return etc / 'subuid', etc / 'subgid'

    def test_first_free_range_after_the_installer_admin_in_both_files(self):
        module = subids()
        uid, gid = self.files('ares-recovery:524288:65536\n', 'ares-recovery:524288:65536\n')
        self.assertEqual(module.plan(uid, gid), ['--add-subuids', '589824-655359', '--add-subgids', '589824-655359'])

    def test_empty_files_start_at_fedora_minimum(self):
        module = subids()
        uid, gid = self.files('', '')
        self.assertEqual(module.plan(uid, gid), ['--add-subuids', '524288-589823', '--add-subgids', '524288-589823'])

    def test_existing_entries_are_never_changed_and_only_the_missing_file_is_completed(self):
        module = subids()
        uid, gid = self.files('ares:700000:65536\n', '')
        self.assertEqual(module.plan(uid, gid), ['--add-subgids', '524288-589823'])
        uid, gid = self.files('1001:700000:65536\n', 'ares:700000:65536\n')
        self.assertEqual(module.plan(uid, gid), [])

    def test_ranges_avoid_every_overlap_including_unsorted_and_gid_only_entries(self):
        module = subids()
        uid, gid = self.files('b:600000:10\na:524288:65536\n', 'c:589900:100\n')
        start = int(module.plan(uid, gid)[1].split('-')[0])
        for begin, count in ((600000, 10), (524288, 65536), (589900, 100)):
            self.assertFalse(begin < start + module.COUNT and start < begin + count, (begin, count, start))
        self.assertEqual(start, 600010)

    def test_malformed_lines_are_ignored_not_trusted(self):
        module = subids()
        uid, gid = self.files('# comment\nbroken\nares:x:y\n', '')
        self.assertEqual(module.plan(uid, gid)[0], '--add-subuids')


class TerminalShellTest(unittest.TestCase):
    def run_terminal(self, home, terminal):
        env = {'HOME': str(home), 'PATH': os.environ['PATH'], 'TERM': 'dumb'}
        if terminal is not None:
            env['ARESOS_TERMINAL'] = terminal
        return subprocess.run(['bash', '--rcfile', str(CONFIG / 'usr/share/aresos/bashrc'), '-i'],
                              input='printf "USER_RC=%s TERMINAL=%s\\n" "${USER_RC-unset}" "${ARESOS_TERMINAL-unset}"\nexit\n',
                              capture_output=True, text=True, env=env, timeout=30)

    def test_user_bashrc_applies_after_the_banner_and_his_prompt_wins(self):
        with tempfile.TemporaryDirectory() as home:
            pathlib.Path(home, '.bashrc').write_text('USER_RC=applied\nPS1="mine> "\n')
            result = self.run_terminal(home, 'normal')
            self.assertIn('Super+Ctrl+Escape: recovery terminal', result.stdout)
            self.assertIn('USER_RC=applied TERMINAL=unset', result.stdout)
            self.assertIn('mine> ', result.stderr)

    def test_recovery_terminal_never_reads_the_user_bashrc(self):
        with tempfile.TemporaryDirectory() as home:
            pathlib.Path(home, '.bashrc').write_text('USER_RC=applied\n')
            result = self.run_terminal(home, 'recovery')
            self.assertIn('USER_RC=unset TERMINAL=unset', result.stdout)
            self.assertIn('aresos ', result.stderr)

    def test_hub_terminal_is_plain_but_reads_his_bashrc(self):
        # Package 24's Terminal app runs this rcfile without ARESOS_TERMINAL:
        # no banner or AresOS prompt, but his daily PATH and his ~/.bashrc.
        with tempfile.TemporaryDirectory() as home:
            pathlib.Path(home, '.bashrc').write_text('USER_RC=applied\n')
            result = self.run_terminal(home, None)
            self.assertIn('USER_RC=applied TERMINAL=unset', result.stdout)
            self.assertNotIn('Super+Ctrl+Escape', result.stdout)
            self.assertNotIn('aresos ', result.stderr)

    def test_a_broken_user_bashrc_does_not_break_the_shell(self):
        with tempfile.TemporaryDirectory() as home:
            pathlib.Path(home, '.bashrc').write_text('USER_RC=before\nif then fi (\n')
            result = self.run_terminal(home, 'normal')
            self.assertIn('USER_RC=before TERMINAL=unset', result.stdout)
            self.assertIn('syntax error', result.stderr)
            missing = self.run_terminal(home + '/missing', 'normal')
            self.assertIn('USER_RC=unset TERMINAL=unset', missing.stdout)

    def test_terminal_wrapper_marks_only_the_recovery_terminal(self):
        wrapper = (CONFIG / 'usr/bin/aresos-terminal').read_text()
        rc = ET.parse(CONFIG / 'usr/share/aresos/labwc/rc.xml').getroot()
        binds = {b.get('key'): b.find('action').get('command') for b in rc.iter('keybind')}
        self.assertEqual(binds['W-C-Escape'], '/usr/bin/aresos-terminal --recovery')
        self.assertIn('/usr/bin/aresos-terminal &', (CONFIG / 'usr/share/aresos/labwc/autostart').read_text().splitlines())
        self.assertIn("if [[ ${1-} == --recovery ]]; then", wrapper)
        self.assertIn('export ARESOS_TERMINAL=$mode', wrapper)
        self.assertIn('--rcfile /usr/share/aresos/bashrc -i', wrapper)
        exec_line, = [line for line in wrapper.splitlines() if line.startswith('exec ')]
        self.assertTrue(exec_line.startswith('exec /usr/bin/foot --title=AresOS /usr/bin/bash '), exec_line)

    def test_a_broken_foot_first_on_path_is_never_run(self):
        # Review 1: ~/.local/bin heads his PATH, so a broken `foot` there must
        # not take away either terminal. The real wrapper runs; whatever
        # /usr/bin/foot does on this host, the shadowing one must stay unused.
        with tempfile.TemporaryDirectory() as directory:
            shadow = pathlib.Path(directory, 'bin')
            shadow.mkdir()
            marker = pathlib.Path(directory, 'broken-foot-ran')
            (shadow / 'foot').write_text(f'#!/bin/sh\ntouch {marker}\nexit 3\n')
            (shadow / 'foot').chmod(0o755)
            for argument in ([], ['--recovery']):
                with self.subTest(argument=argument):
                    result = subprocess.run(['bash', str(CONFIG / 'usr/bin/aresos-terminal'), *argument],
                                            capture_output=True, text=True, timeout=30,
                                            env={'PATH': f'{shadow}:/usr/bin:/bin', 'HOME': directory})
                    self.assertFalse(marker.exists(), result.stderr)
                    if not os.path.exists('/usr/bin/foot'):
                        self.assertIn('/usr/bin/foot', result.stderr)


class DailyPathTest(unittest.TestCase):
    def profile_path(self, home, uid, shell=('bash', '--noprofile', '--norc', '-l'), arg0=None):
        # The real file calls /usr/bin/id; this copy lets the test choose the UID.
        # A login shell by default; greetd's session wrapper is a plain `sh -c`.
        source = (CONFIG / 'etc/profile.d/aresos.sh').read_text()
        self.assertEqual(source.count('"$(/usr/bin/id -u)"'), 1)
        with tempfile.TemporaryDirectory() as directory:
            copy = pathlib.Path(directory, 'aresos.sh')
            copy.write_text(source.replace('"$(/usr/bin/id -u)"', '"$(id -u)"'))
            script = f'id() {{ echo {uid}; }}\nPATH=/somewhere/else\n. {copy}\nprintf "%s|%s|%s" "$PATH" "${{HOMEBREW_NO_AUTO_UPDATE-}}" "${{_aresos_daily-unset}}"\n'
            result = subprocess.run([*shell, '-c', script, *([arg0] if arg0 else [])], capture_output=True, text=True,
                                    env={'HOME': str(home)}, timeout=30, stdin=subprocess.DEVNULL)
        if '-i' not in shell:
            self.assertEqual(result.stderr, '')
        path, update, helper = result.stdout.split('|')
        self.assertEqual(helper, 'unset')
        return path, update

    def test_daily_path_has_his_tools_first_and_system_before_optional_directories(self):
        with tempfile.TemporaryDirectory() as home:
            path, update = self.profile_path(home, 1001)
            self.assertEqual(update, '1')
            parts = path.split(':')
            self.assertEqual(parts[:5], [home + '/.local/bin', '/usr/local/bin', '/usr/local/sbin', '/usr/bin', '/usr/sbin'])
            exports = pathlib.Path(home, '.local/share/flatpak/exports/bin')
            exports.mkdir(parents=True)
            path, _ = self.profile_path(home, 1001)
            self.assertIn(str(exports), path.split(':'))
            self.assertGreater(path.split(':').index(str(exports)), path.split(':').index('/usr/sbin'))
            for optional in ('/home/linuxbrew/.linuxbrew/bin', '/var/lib/flatpak/exports/bin'):
                self.assertEqual(optional in path.split(':'), os.path.isdir(optional))

    def test_his_interactive_and_login_shells_get_it_but_the_session_wrapper_never(self):
        # Review 5: greetd sources /etc/profile in a non-interactive /bin/sh
        # before /usr/bin/aresos-session; that wrapper keeps the PATH it has.
        with tempfile.TemporaryDirectory() as home:
            daily = home + '/.local/bin'
            for shell, arg0 in ((('bash', '--noprofile', '--norc', '-i'), None), (('sh',), '-sh')):
                with self.subTest(shell=shell, arg0=arg0):
                    self.assertEqual(self.profile_path(home, 1001, shell, arg0)[0].split(':')[0], daily)
            for shell in (('sh',), ('bash', '--noprofile', '--norc')):
                with self.subTest(shell=shell):
                    self.assertEqual(self.profile_path(home, 1001, shell), ('/somewhere/else', '1'))

    def test_other_accounts_keep_their_own_path(self):
        with tempfile.TemporaryDirectory() as home:
            path, update = self.profile_path(home, 1000)
            self.assertEqual((path, update), ('/somewhere/else', '1'))

    def test_session_keeps_the_system_path_and_terminals_add_his_own(self):
        # Review 5: ~/.local/bin heads his PATH, so the session must not
        # depend on it; a normal terminal adds it, the recovery one never does.
        session = (CONFIG / 'usr/bin/aresos-session').read_text()
        self.assertIn('\nexport PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin\n', session)
        self.assertNotIn('profile.d', session.split('export PATH=', 1)[1])
        bashrc = (CONFIG / 'usr/share/aresos/bashrc').read_text()
        normal = bashrc.split('if [ "$_aresos_terminal" != recovery ]; then', 1)[1].split('\nfi\n', 1)[0]
        self.assertIn('. /etc/profile.d/aresos.sh', normal)
        self.assertIn('. "$HOME/.bashrc"', normal)
        self.assertEqual(bashrc.count('/etc/profile.d/aresos.sh'), 2)
        self.assertNotIn('HOMEBREW_NO_INSTALL_FROM_API', (CONFIG / 'etc/profile.d/aresos.sh').read_text())
        self.assertIn('export HOMEBREW_NO_AUTO_UPDATE=1', session)


class StartupPathTest(unittest.TestCase):
    """Review 5: every command that starts the session or a terminal is absolute."""

    def test_session_terminal_and_keyboard_helper_run_absolute_commands_only(self):
        session = (CONFIG / 'usr/bin/aresos-session').read_text()
        command = session.split('\nexec ', 1)[1].replace('\\\n', ' ').split()
        self.assertEqual(command, ['/usr/libexec/aresos-keyboard', '/usr/bin/dbus-run-session',
                                   '--dbus-daemon=/usr/bin/dbus-daemon', '--', '/usr/bin/labwc', '--config-dir',
                                   '/usr/share/aresos/labwc'])
        terminal = (CONFIG / 'usr/bin/aresos-terminal').read_text()
        self.assertIn('\nexec /usr/bin/foot --title=AresOS /usr/bin/bash --rcfile /usr/share/aresos/bashrc -i\n',
                      terminal)
        keyboard = (CONFIG / 'usr/libexec/aresos-keyboard').read_text()
        self.assertIn("'/usr/bin/busctl', '--system'", keyboard)
        self.assertIn("assert sys.argv[1].startswith('/'), 'The compositor command must be an absolute path'",
                      keyboard)
        self.assertIn('os.execve(sys.argv[1], sys.argv[1:],', keyboard)
        self.assertNotIn('execvp', keyboard)
        for line in (CONFIG / 'usr/share/aresos/labwc/autostart').read_text().splitlines():
            if line and not line.startswith('#'):
                self.assertTrue(line.startswith('/'), line)
        rc = ET.parse(CONFIG / 'usr/share/aresos/labwc/rc.xml').getroot()
        for action in rc.iter('action'):
            if action.get('name') == 'Execute':
                self.assertTrue(action.get('command').startswith('/'), action.get('command'))

    def test_brew_and_subids_helpers_run_absolute_commands(self):
        brew = (CONFIG / 'usr/bin/brew').read_text()
        for command in ('/usr/bin/stat -L', '/usr/bin/id -u', '/usr/bin/getent passwd', '/usr/bin/cut -d:',
                        'exec /usr/bin/sudo -u', '/usr/bin/env HOMEBREW_NO_AUTO_UPDATE=1'):
            self.assertIn(command, brew)
        self.assertIn("command = ['/usr/sbin/usermod', *arguments, USER]",
                      (CONFIG / 'usr/libexec/aresos-subids').read_text())

    def test_app_helper_and_its_apps_run_absolute_commands(self):
        # Package 24's helper runs under the session's system PATH: its own
        # commands and every app it starts are absolute, and the hub's
        # Terminal gets the AresOS rcfile, so his daily PATH, as a plain terminal.
        helper = (CONFIG / 'usr/libexec/aresos-shell').read_text()
        self.assertTrue(helper.startswith('#!/usr/bin/python3\n'))
        self.assertIn("SYSTEMD_RUN = '/usr/bin/systemd-run'", helper)
        self.assertIn("SYSTEMCTL = '/usr/bin/systemctl'", helper)
        apps = {path.stem: json.loads(path.read_text()) for path in (CONFIG / 'usr/share/aresos/apps').glob('*.json')}
        self.assertEqual(set(apps), {'browser', 'notepad', 'terminal'})
        for app in apps.values():
            self.assertTrue(app['argv'][0].startswith('/usr/bin/'), app)
        self.assertEqual(apps['terminal']['argv'], ['/usr/bin/foot', '--app-id=aresos.terminal', '/usr/bin/bash',
                                                    '--rcfile', '/usr/share/aresos/bashrc', '-i'])

    def test_ci_vm_layer_shadows_every_startup_command(self):
        # The VM boot plants broken copies of these first on his PATH before
        # greetd starts; checks.py requires that none of them ran.
        names = (ROOT / 'ci/overlay/shadow-names.txt').read_text().split()
        for name in ('sh', 'bash', 'dbus-run-session', 'dbus-daemon', 'labwc', 'busctl', 'foot', 'id',
                     'aresos-terminal'):
            self.assertIn(name, names)
        containerfile = (ROOT / 'ci/overlay/Containerfile').read_text()
        self.assertIn('/usr/lib/systemd/system/greetd.service.wants/aresos-ci-shadow-path.service', containerfile)
        unit = (ROOT / 'ci/overlay/shadow-path.service').read_text()
        self.assertIn('Before=greetd.service', unit)
        checks = (ROOT / 'ci/overlay/checks.py').read_text()
        self.assertIn("assert not ran.exists(), ('a shadowing program ran', ran.read_text())", checks)
        # And a probe last in /etc/profile.d shows greetd's wrapper keeps the system PATH.
        self.assertIn('/etc/profile.d/zz-aresos-ci-profile-path.sh', containerfile)
        self.assertIn("('session wrapper got the daily PATH', lines)", checks)
        # Review 6: a missing probe, or one without a wrapper record, fails.
        self.assertIn("assert probe.is_file(), 'the profile probe recorded nothing'", checks)
        self.assertIn("assert wrappers, ('no non-interactive, non-login profile run (greetd wrapper) recorded', lines)",
                      checks)


class PolicyFilesTest(unittest.TestCase):
    def test_sysusers_adds_wheel_and_sudo_asks_for_the_password_every_time(self):
        lines = [l for l in (CONFIG / 'usr/lib/sysusers.d/aresos.conf').read_text().splitlines()
                 if l and not l.startswith('#')]
        self.assertEqual(lines, ['g ares 1001', 'u ares 1001:1001 "AresOS daily session" /var/home/ares /bin/bash',
                                 'm ares wheel'])
        sudoers = [l for l in (CONFIG / 'etc/sudoers.d/aresos-everyday').read_text().splitlines()
                   if l and not l.startswith('#')]
        self.assertEqual(sudoers, ['Defaults:ares timestamp_timeout=0'])

    def test_polkit_rule_denies_os_changes_and_asks_for_upstream_wheel_grants(self):
        rule = (CONFIG / 'usr/share/polkit-1/rules.d/00-aresos-maintenance.rules').read_text()
        for prefix in ('org.projectatomic.rpmostree1.', 'org.freedesktop.sysupdate1.', 'org.freedesktop.fwupd.',
                       'org.bazzite.'):
            self.assertIn(f'action.id.indexOf("{prefix}") == 0', rule)
        # Review 2: upstream wheel grants get each action's own uncached
        # default for ares, per session kind [remote, inactive, active].
        listed = re.search(r'var aresosWheelGrantDefaults = \{(.*?)\};', rule, re.S).group(1)
        grants = {name: values.split('", "') for name, values in re.findall(r'"([^"]+)": \["([^\]]+)"\]', listed)}
        self.assertEqual(list(grants), sorted(grants))
        self.assertEqual(grants['org.gtk.vfs.file-operations-helper'], ['no', 'no', 'auth_admin'])
        for action in ('org.freedesktop.Flatpak.app-install', 'org.freedesktop.NetworkManager.settings.modify.system'):
            self.assertEqual(grants[action], ['auth_admin'] * 3)
        self.assertFalse(any(value.endswith('_keep') for values in grants.values() for value in values))
        self.assertIn('return !subject.local ? defaults[0] : (subject.active ? defaults[2] : defaults[1]);', rule)
        # TuneD: everything except read-only queries is denied (a profile can
        # change kernel arguments through TuneD's bootloader plugin).
        read_only = re.findall(r'"([^"]+)"', re.search(r'var aresosTunedReadOnly = \[(.*?)\];', rule, re.S).group(1))
        self.assertNotIn('com.redhat.tuned.switch_profile', read_only)
        self.assertNotIn('com.redhat.tuned.auto_profile', read_only)
        self.assertIn('(action.id.indexOf("com.redhat.tuned.") == 0 && aresosTunedReadOnly.indexOf(action.id) < 0)', rule)
        # Review 1: logind's next-boot and firmware-setup choices (and modem
        # firmware) are open to any active session by default; deny them to
        # ares outright, with or without wheel. Ordinary power actions stay.
        denied = re.findall(r'"([^"]+)"', re.search(r'var aresosDeniedActions = \[(.*?)\];', rule, re.S).group(1))
        self.assertEqual(denied, ['org.freedesktop.ModemManager1.Firmware',
                                  'org.freedesktop.login1.set-reboot-parameter',
                                  'org.freedesktop.login1.set-reboot-to-boot-loader-entry',
                                  'org.freedesktop.login1.set-reboot-to-boot-loader-menu',
                                  'org.freedesktop.login1.set-reboot-to-firmware-setup'])
        self.assertIn('aresosDeniedActions.indexOf(action.id) >= 0 ||\n', rule)
        self.assertIn('aresosTunedReadOnly.indexOf(action.id) < 0)) {\n        return polkit.Result.NO;', rule)
        review = json.loads((ROOT / 'ci/polkit-review.json').read_text())
        self.assertEqual(review['denied_actions'], denied)
        self.assertEqual(review['tuned_read_only'], read_only)
        self.assertEqual(review['expected']['com.redhat.tuned.switch_profile'], {'rule': 'no', 'without_wheel': 'no'})
        self.assertTrue(all(reason.strip() for reason in review['passwordless'].values()))
        self.assertFalse(set(review['passwordless']) & (set(denied) | {'com.redhat.tuned.switch_profile'}))
        for power in ('power-off', 'reboot', 'suspend'):
            self.assertNotIn(f'org.freedesktop.login1.{power}"', rule)
            self.assertEqual(review['expected'][f'org.freedesktop.login1.{power}'], {'rule': None, 'effective': 'yes'})
        self.assertNotIn('manage-unit-files', rule)
        self.assertNotIn('_KEEP', rule)
        self.assertNotIn('Result.YES', rule)

    def test_build_drops_only_the_runtime_install_implication_of_flatpak_app_update(self):
        # Review 3: polkitd grants an implied action when the subject has the
        # implying one outright, so the passwordless app-update installed runtimes.
        # Review 4: the build accepts exactly the reviewed targets, nothing else.
        build = (ROOT / 'build.sh').read_text()
        statement = "flatpak = actions / 'org.freedesktop.Flatpak.policy'"
        block = build.split(statement, 1)[1].split('\nPY\n', 1)[0]
        code = compile('import re\n' + statement + block, 'build.sh', 'exec')
        imply = '<annotate key="org.freedesktop.policykit.imply">{}</annotate>'
        install, update = 'org.freedesktop.Flatpak.runtime-install', 'org.freedesktop.Flatpak.runtime-update'

        def policy(targets):
            return ('<action id="org.freedesktop.Flatpak.app-install">' +
                    imply.format('org.freedesktop.Flatpak.app-update ' + install + ' ' + update) +
                    '</action>\n<action id="org.freedesktop.Flatpak.app-update"><defaults/>' +
                    imply.format(targets) + '</action>\n<action id="' + update + '"/>\n')

        def run(targets):
            with tempfile.TemporaryDirectory() as directory:
                path = pathlib.Path(directory, 'org.freedesktop.Flatpak.policy')
                path.write_text(policy(targets))
                exec(code, {'actions': pathlib.Path(directory), 'print': lambda *a: None})
                return path.read_text()

        # Exactly the reviewed targets: only runtime-install goes, the rest of
        # the file is untouched.
        self.assertEqual(run(install + ' ' + update), policy(update))
        # Added, removed, reordered, repeated or missing targets stop the build.
        for targets in (install + ' ' + update + ' org.freedesktop.Flatpak.app-install',
                        install + ' ' + update + ' org.freedesktop.systemd1.manage-units',
                        install, update, update + ' ' + install, install + ' ' + install + ' ' + update, ''):
            with self.subTest(targets=targets), self.assertRaisesRegex(SystemExit, 'review required'):
                run(targets)
        self.assertIn("reviewed = ['org.freedesktop.Flatpak.runtime-install', 'org.freedesktop.Flatpak.runtime-update']",
                      block)
        self.assertIn("raise SystemExit('Flatpak app-update implication edit did not leave exactly runtime-update')", block)

    def test_build_makes_every_polkit_default_uncached_and_refuses_leftovers(self):
        build = (ROOT / 'build.sh').read_text()
        self.assertIn(r"cached = re.compile(r'(<allow_(?:any|inactive|active)>\s*)auth_(admin|self)_keep(\s*</allow_)')", build)
        self.assertIn(r"new, count = cached.subn(r'\1auth_\2\3', text)", build)
        # The same rewrite on a sample: every cached default, nothing else.
        rewrite = re.compile(r'(<allow_(?:any|inactive|active)>\s*)auth_(admin|self)_keep(\s*</allow_)')
        sample = ('<allow_any>auth_admin_keep</allow_any><allow_inactive>auth_self_keep</allow_inactive>'
                  '<allow_active>yes</allow_active><description>auth_admin_keep</description>')
        self.assertEqual(rewrite.subn(r'\1auth_\2\3', sample),
                         ('<allow_any>auth_admin</allow_any><allow_inactive>auth_self</allow_inactive>'
                          '<allow_active>yes</allow_active><description>auth_admin_keep</description>', 2))
        self.assertIn("raise SystemExit(f'polkit defaults still cached in {left} (changed {changed})')", build)

    def test_flatpak_helpers_are_reviewed_while_automatic_updaters_stay_masked(self):
        system = (ROOT / 'policy/masked-system-units.txt').read_text().splitlines()
        user = (ROOT / 'policy/masked-user-units.txt').read_text().splitlines()
        allow = json.loads((ROOT / 'policy/updater-allowlist.json').read_text())
        for unit in ('flatpak-system-helper.service', 'flatpak-portal.service', 'flatpak-session-helper.service'):
            self.assertNotIn(unit, system + user)
            self.assertIn(unit, allow)
        for unit in ('flatpak-system-update.timer', 'flatpak-system-update.service', 'uupd.timer',
                     'rpm-ostreed-automatic.timer', 'bootc-fetch-apply-updates.timer', 'fwupd-refresh.timer',
                     'brew-update.timer', 'brew-upgrade.timer'):
            self.assertIn(unit, system)
        for unit in ('flatpak-update.timer', 'brew-update.timer', 'brew-upgrade.timer', 'uupd.timer'):
            self.assertIn(unit, user)

    def test_build_keeps_os_updaters_root_only_and_refuses_passwordless_sudo(self):
        build = (ROOT / 'build.sh').read_text()
        loop = re.search(r'for command in ([^;]+); do\n    path=\$\(command -v', build).group(1).split()
        self.assertEqual(loop, ['uupd', 'ujust', 'topgrade', 'bazzite-updater', 'bazzite-portal', 'bazaar',
                                'plasma-discover', 'gnome-software'])
        self.assertIn("raise SystemExit('Passwordless sudo rule needs review: '", build)
        self.assertIn('visudo --check', build)
        self.assertIn('systemctl enable aresos-subids.service', build)

    def test_subids_service_runs_before_logins(self):
        unit = configparser.ConfigParser()
        unit.read(CONFIG / 'usr/lib/systemd/system/aresos-subids.service')
        self.assertEqual(unit['Service']['ExecStart'], '/usr/libexec/aresos-subids')
        self.assertEqual(unit['Service']['Type'], 'oneshot')
        self.assertIn('systemd-user-sessions.service', unit['Unit']['Before'])
        self.assertEqual(unit['Install']['WantedBy'], 'multi-user.target')


class DesktopDefaultsTest(unittest.TestCase):
    def test_foot_default_font_is_readable_and_a_user_file_replaces_it(self):
        foot = configparser.ConfigParser()
        foot.read(CONFIG / 'etc/xdg/foot/foot.ini')
        self.assertEqual(foot['main']['font'], 'monospace:size=16')
        self.assertEqual(foot.sections(), ['main'])

    def test_brightness_volume_and_mic_keys_use_tools_in_the_image(self):
        rc = ET.parse(CONFIG / 'usr/share/aresos/labwc/rc.xml').getroot()
        binds = {b.get('key'): b.find('action').get('command') for b in rc.iter('keybind')}
        self.assertEqual(binds['XF86MonBrightnessUp'], '/usr/bin/brightnessctl --quiet set 5%+')
        self.assertEqual(binds['XF86MonBrightnessDown'], '/usr/bin/brightnessctl --quiet --min-value=1 set 5%-')
        self.assertEqual(binds['XF86AudioRaiseVolume'], '/usr/bin/wpctl set-volume --limit 1.0 @DEFAULT_AUDIO_SINK@ 5%+')
        self.assertEqual(binds['XF86AudioLowerVolume'], '/usr/bin/wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-')
        self.assertEqual(binds['XF86AudioMute'], '/usr/bin/wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle')
        self.assertEqual(binds['XF86AudioMicMute'], '/usr/bin/wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle')

    def test_polkit_agent_starts_before_the_terminal(self):
        lines = [l for l in (CONFIG / 'usr/share/aresos/labwc/autostart').read_text().splitlines()
                 if l and not l.startswith('#')]
        self.assertEqual(lines, ['/usr/libexec/kf6/polkit-kde-authentication-agent-1 &', '/usr/bin/aresos-terminal &'])

    def test_links_open_in_chrome_unless_the_user_chooses_otherwise(self):
        defaults = configparser.ConfigParser(delimiters=('=',))
        defaults.optionxform = str
        defaults.read(CONFIG / 'usr/share/applications/aresos-mimeapps.list')
        for mime in ('x-scheme-handler/http', 'x-scheme-handler/https', 'text/html', 'application/xhtml+xml'):
            self.assertEqual(defaults['Default Applications'][mime], 'google-chrome.desktop')


class GoogleChromePinTest(unittest.TestCase):
    def test_pin_names_one_exact_rpm_and_googles_committed_key(self):
        pin = json.loads((ROOT / 'google-chrome.lock.json').read_text())
        self.assertRegex(pin['nevra'], r'^google-chrome-stable-\d+(\.\d+){3}-\d+\.x86_64$')
        self.assertEqual(pin['url'], 'https://dl.google.com/linux/chrome/rpm/stable/x86_64/' + pin['nevra'] + '.rpm')
        self.assertRegex(pin['sha256'], r'^[0-9a-f]{64}$')
        key = ROOT / pin['signing_key']['file']
        self.assertEqual(hashlib.sha256(key.read_bytes()).hexdigest(), pin['signing_key']['sha256'])
        self.assertTrue(key.read_text().startswith('-----BEGIN PGP PUBLIC KEY BLOCK-----'))
        self.assertEqual(pin['signing_key']['fingerprint'], 'eb4c1bfd4f042f6dddccec917721f63bd38b4796')

    def test_build_verifies_the_pin_and_leaves_no_repository_cron_or_var_copy(self):
        build = (ROOT / 'build.sh').read_text()
        for needle in ("'Google Chrome RPM differs from its pin'", "'Google signing key differs from its pin'",
                       'key fingerprint: $chrome_key: OK$', 'repo_add_once="false"',
                       '--setopt=localpkg_gpgcheck=True install -y \\\n        /tmp/ares-rpms/*.rpm /tmp/ares-chrome/google-chrome.rpm',
                       'mv /var/opt/google /usr/lib/opt/google', 'rmdir /var/opt',
                       'ln -sfn /usr/lib/opt/google/chrome/google-chrome /usr/bin/google-chrome-stable',
                       'rm -f /etc/cron.daily/google-chrome', "echo 'Google Chrome added a package repository' >&2"):
            self.assertIn(needle, build)
        tmpfiles = (CONFIG / 'usr/lib/tmpfiles.d/aresos-google-chrome.conf').read_text().splitlines()
        self.assertIn('L /var/opt/google - - - - /usr/lib/opt/google', tmpfiles)

    def test_fedora_lock_adds_the_tools_and_chromes_only_fedora_dependency(self):
        names = {re.sub(r'-(\d+:)?[^-]+-[^-]+$', '', row['nevra'])
                 for row in json.loads((ROOT / 'packages.lock.json').read_text())['packages']}
        self.assertTrue({'util-linux-script', 'qrencode', 'brightnessctl', 'liberation-fonts-all'} <= names, names)
        self.assertFalse(any(name.startswith(('kernel', 'nvidia', 'kmod-nvidia', 'akmod-nvidia')) for name in names))



class SudoersDirectoryTest(unittest.TestCase):
    """Package 27: copying os/config must not leave /etc/sudoers.d world-readable."""

    def test_build_restores_the_root_only_sudoers_directory_after_the_config_copy(self):
        script = (ROOT / 'build.sh').read_text()
        configure = script.split('if [[ $1 == packages ]]; then', 1)[1].split('\nfi\n', 1)[1]
        self.assertIn('chown root:root /etc/sudoers.d\nchmod 0750 /etc/sudoers.d\n', configure)
        # The configure step runs after the Containerfile's `cp -a .../config/. /`.
        containerfile = (ROOT / 'Containerfile').read_text()
        self.assertLess(containerfile.index('cp -a /tmp/aresos/config/. /'), containerfile.index('build.sh configure'))
        checks = (ROOT / 'ci/image-checks.sh').read_text()
        self.assertIn("test \"$(stat -c '%a %u %g' /etc/sudoers.d)\" = '750 0 0'", checks)
        self.assertTrue((CONFIG / 'etc/sudoers.d').is_dir())

if __name__ == '__main__':
    unittest.main()
