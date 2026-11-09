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


class DailyPathTest(unittest.TestCase):
    def profile_path(self, home, uid):
        script = f'id() {{ echo {uid}; }}\nPATH=/somewhere/else\n. {CONFIG / "etc/profile.d/aresos.sh"}\nprintf "%s|%s" "$PATH" "${{HOMEBREW_NO_AUTO_UPDATE-}}"\n'
        result = subprocess.run(['bash', '--noprofile', '--norc', '-c', script], capture_output=True, text=True,
                                env={'HOME': str(home)}, timeout=30)
        self.assertEqual(result.stderr, '')
        return result.stdout.split('|')

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

    def test_other_accounts_keep_their_own_path(self):
        with tempfile.TemporaryDirectory() as home:
            path, update = self.profile_path(home, 1000)
            self.assertEqual((path, update), ('/somewhere/else', '1'))

    def test_session_uses_the_same_profile_and_homebrew_api_install_is_not_disabled(self):
        self.assertIn('. /etc/profile.d/aresos.sh', (CONFIG / 'usr/bin/aresos-session').read_text())
        self.assertNotIn('HOMEBREW_NO_INSTALL_FROM_API', (CONFIG / 'etc/profile.d/aresos.sh').read_text())


class PolicyFilesTest(unittest.TestCase):
    def test_sysusers_adds_wheel_and_sudo_remembers_passwords_per_parent_process(self):
        lines = [l for l in (CONFIG / 'usr/lib/sysusers.d/aresos.conf').read_text().splitlines()
                 if l and not l.startswith('#')]
        self.assertEqual(lines, ['g ares 1001', 'u ares 1001:1001 "AresOS daily session" /var/home/ares /bin/bash',
                                 'm ares wheel'])
        sudoers = [l for l in (CONFIG / 'etc/sudoers.d/aresos-everyday').read_text().splitlines()
                   if l and not l.startswith('#')]
        self.assertEqual(sudoers, ['Defaults:ares timestamp_type=ppid'])

    def test_polkit_rule_denies_os_changes_and_asks_for_upstream_wheel_grants(self):
        rule = (CONFIG / 'usr/share/polkit-1/rules.d/00-aresos-maintenance.rules').read_text()
        for prefix in ('org.projectatomic.rpmostree1.', 'org.freedesktop.sysupdate1.', 'org.freedesktop.fwupd.',
                       'org.bazzite.'):
            self.assertIn(f'action.id.indexOf("{prefix}") == 0', rule)
        listed = re.search(r'var aresosPasswordActions = \[(.*?)\];', rule, re.S).group(1)
        actions = re.findall(r'"([^"]+)"', listed)
        self.assertEqual(actions, sorted(actions))
        for action in ('org.freedesktop.Flatpak.app-install', 'org.gtk.vfs.file-operations-helper',
                       'org.freedesktop.NetworkManager.settings.modify.system'):
            self.assertIn(action, actions)
        self.assertNotIn('manage-unit-files', rule)
        self.assertIn('return polkit.Result.AUTH_ADMIN_KEEP;', rule)
        self.assertNotIn('Result.YES', rule)

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


if __name__ == '__main__':
    unittest.main()
