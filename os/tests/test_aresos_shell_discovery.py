"""Package 30 step 1: desktop catalogue and launches, with no real programs or compositor."""
import ast
import dataclasses
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from test_aresos_shell import shell, ROOT, REGISTRY, Base, Proc


FIXTURES = pathlib.Path(__file__).parent / 'fixtures/installed-programs'


class DiscoveryBase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = pathlib.Path(self.temporary.name)
        self.registry = self.root / 'registry'
        self.registry.mkdir()
        self.folders = [self.root / str(n) for n in range(5)]
        for folder in self.folders:
            folder.mkdir()
        # A Flatpak deployment, where exported desktop-file links may point (security review 1, FIX 5).
        self.deployment = self.root / 'flatpak/app'
        self.executables = {'/usr/bin/tool', '/usr/bin/foot', '/usr/bin/btop', '/usr/bin/flatpak',
                            '/usr/bin/bazzite-steam', '/usr/bin/other', '/usr/bin/kwrite'}
        self.logging = mock.patch.object(shell.LOG, 'disabled', False)
        self.logging.start()
        self.addCleanup(self.logging.stop)

    def write(self, name, text=None, folder=0, **values):
        path = self.folders[folder] / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if text is None:
            fields = {'Type': 'Application', 'Name': 'Test Program', 'Exec': '/usr/bin/tool'}
            fields.update(values)
            text = '[Desktop Entry]\n' + ''.join(f'{key}={value}\n' for key, value in fields.items())
        path.write_bytes(text if isinstance(text, bytes) else text.encode())
        return path

    def catalogue(self, registry=None, executable=None):
        return shell.load_catalogue(str(registry or self.registry), entry_dirs=self.folders,
                                    executable=executable or self.executables.__contains__,
                                    deployments=[self.deployment])

    def fixture(self, name, folder=0):
        text = (FIXTURES / name).read_text().replace('@HOME@', str(self.root))
        return self.write(name, text, folder)


class DiscoveryTest(DiscoveryBase):
    def test_directories_have_the_required_order_and_xdg_default(self):
        expected = ('/test/home/.local/share/applications',
                    '/test/home/.local/share/flatpak/exports/share/applications',
                    '/var/lib/flatpak/exports/share/applications',
                    '/usr/local/share/applications', '/usr/share/applications')
        self.assertEqual(shell.desktop_directories({'HOME': '/test/home'}), expected)
        for value in ('', 'relative'):
            self.assertEqual(shell.desktop_directories({'HOME': '/test/home', 'XDG_DATA_HOME': value}), expected)
        self.assertEqual(shell.desktop_directories({'HOME': '/test/home', 'XDG_DATA_HOME': '/test/data'}),
                         ('/test/data/applications', *expected[1:]))

    def test_load_uses_the_xdg_directories_when_no_override_is_injected(self):
        home = self.root / 'home'
        target = home / '.local/share/applications'
        target.mkdir(parents=True)
        self.write('mine.desktop').rename(target / 'mine.desktop')
        # Observe defaults without reading the host's system applications.
        original = shell.desktop_files
        seen = []

        def files(folders):
            seen.extend(folders)
            return original(folders[:1])

        with mock.patch.object(shell, 'desktop_files', side_effect=files):
            apps, _ = shell.load_catalogue(str(self.registry), environ={'HOME': str(home)},
                                           executable=self.executables.__contains__)
        self.assertEqual(set(apps), {'mine'})
        self.assertEqual(tuple(seen), shell.desktop_directories({'HOME': str(home)}))

    def test_each_folder_wins_over_all_the_later_folders(self):
        for winner in range(5):
            name = f'precedence{winner}.desktop'
            for folder in range(winner, 5):
                self.write(name, folder=folder, Name=f'Folder {folder}')
        apps, _ = self.catalogue()
        self.assertEqual({key: app.name for key, app in apps.items()},
                         {f'precedence{n}': f'Folder {n}' for n in range(5)})

    def test_hidden_override_removes_an_id_everywhere_and_not_a_neighbour(self):
        self.write('hidden.desktop', '[Desktop Entry]\nHidden=true\n')
        for folder in range(1, 5):
            self.write('hidden.desktop', folder=folder)
        self.write('neighbour.desktop', folder=4)
        self.assertEqual(set(self.catalogue()[0]), {'neighbour'})

    def test_an_unusable_override_never_falls_back_to_a_system_entry(self):
        self.write('nodisplay.desktop', NoDisplay='true')
        self.write('missing.desktop', Exec='/missing/program')
        self.write('broken.desktop', 'not an entry')
        for name in ('nodisplay', 'missing', 'broken'):
            self.write(name + '.desktop', folder=4)
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertEqual(self.catalogue()[0], {})
        self.assertEqual(len(logs.output), 1)

    def test_nested_desktop_ids_and_flatpak_file_symlinks(self):
        self.write('nested/program.desktop', Name='Nested')
        self.write('nested-program.desktop', folder=4, Name='Shadowed')
        target = self.deployment / 'org.example.App/current/active/export/share/applications/exported.desktop'
        target.parent.mkdir(parents=True)
        self.write('temporary.desktop').rename(target)
        (self.folders[1] / 'flatpak.desktop').symlink_to(target)
        # A directory symlink is not an include mechanism, even if it loops back.
        (self.folders[0] / 'loop').symlink_to(self.folders[0], target_is_directory=True)
        apps, _ = self.catalogue()
        self.assertEqual(set(apps), {'nested-program', 'flatpak'})
        self.assertEqual(apps['nested-program'].name, 'Nested')
        self.assertEqual(apps['nested-program'].desktop_entry, 'nested-program.desktop')

    def test_type_exec_and_visibility_filters(self):
        excluded = [dict(Type='Link'), dict(Type='Directory'), dict(Exec=''), dict(Hidden='true'),
                    dict(NoDisplay='true'), dict(OnlyShowIn='KDE;GNOME;'), dict(NotShowIn='KDE;AresOS;'),
                    dict(DBusActivatable='true', Exec=''), dict(Exec='/usr/bin/missing'),
                    dict(TryExec='/missing/tool'), dict(TryExec='missing'), dict(TryExec='relative/tool')]
        for n, fields in enumerate(excluded):
            self.write(f'excluded{n}.desktop', **fields)
        included = [dict(OnlyShowIn='KDE;AresOS;'), dict(NotShowIn='KDE;GNOME;'),
                    dict(DBusActivatable='true'), dict(DBusActivatable='false'), dict(TryExec='tool'),
                    dict(TryExec='/usr/bin/tool'), dict(Hidden='false', NoDisplay='false')]
        for n, fields in enumerate(included):
            self.write(f'included{n}.desktop', **fields)
        self.assertEqual(set(self.catalogue()[0]), {f'included{n}' for n in range(len(included))})

    def test_exec_and_tryexec_require_executable_regular_files(self):
        binary = self.root / 'program'
        binary.write_text('#!/bin/sh\nexit 0\n')
        self.write('test.desktop', Exec=str(binary), TryExec=str(binary))
        self.assertEqual(self.catalogue(executable=shell.executable_file)[0], {})
        binary.chmod(0o700)
        self.assertEqual(set(self.catalogue(executable=shell.executable_file)[0]), {'test'})
        self.write('directory.desktop', Exec=str(self.root))
        self.assertEqual(set(self.catalogue(executable=shell.executable_file)[0]), {'test'})
        self.write('badtry.desktop', TryExec=str(self.root))
        self.assertEqual(set(self.catalogue(executable=shell.executable_file)[0]), {'test'})

    def test_real_fixtures_keep_main_entries_and_discard_flatpak_forwarding(self):
        for name in ('lunarclient.desktop', 'org.mozilla.firefox.desktop', 'com.discordapp.Discord.desktop',
                     'steam.desktop', 'foot.desktop', 'btop.desktop'):
            self.fixture(name)
        lunar = str(self.root / '.local/opt/lunarclient/LunarClient.AppImage')
        self.executables.add(lunar)
        apps, _ = self.catalogue()
        self.assertEqual(set(apps), {'lunarclient', 'org-mozilla-firefox', 'com-discordapp-discord', 'steam', 'foot'})
        self.assertEqual(apps['lunarclient'].argv, (lunar, '--no-sandbox'))
        self.assertEqual(apps['lunarclient'].gpu, 'discrete')
        self.assertEqual(apps['steam'].argv, ('/usr/bin/bazzite-steam',))
        self.assertEqual(apps['steam'].gpu, 'discrete')
        self.assertEqual(apps['org-mozilla-firefox'].name, 'Firefox')
        self.assertEqual(apps['org-mozilla-firefox'].argv,
                         ('/usr/bin/flatpak', 'run', '--branch=stable', '--arch=x86_64', '--command=firefox',
                          '--file-forwarding', 'org.mozilla.firefox'))
        self.assertEqual(apps['com-discordapp-discord'].argv[-1], 'com.discordapp.Discord')
        for app in apps.values():
            self.assertFalse(any(part.startswith('@@') or part.startswith('%') for part in app.argv))

    def test_500_entries_are_capped_including_the_registry_with_one_log(self):
        for n in range(500):
            self.write(f'program{n:03d}.desktop')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            apps, _ = self.catalogue(registry=REGISTRY)
        self.assertEqual(len(apps), shell.MAX_APPS)
        self.assertTrue({'browser', 'terminal', 'notepad'} <= set(apps))
        self.assertEqual(set(apps) - {'browser', 'terminal', 'notepad'},
                         {f'program{n:03d}' for n in range(shell.MAX_APPS - 3)})
        self.assertEqual(len(logs.output), 1)
        self.assertIn('MAX_APPS=256', logs.output[0])

    def test_exactly_the_cap_is_not_reported_as_cut(self):
        with mock.patch.object(shell, 'MAX_APPS', 2), mock.patch.object(shell.LOG, 'warning') as log:
            self.write('a.desktop')
            self.write('b.desktop')
            self.assertEqual(len(self.catalogue()[0]), 2)
        log.assert_not_called()

    def test_revision_is_stable_and_changes_when_launch_or_name_changes(self):
        self.write('one.desktop')
        original = self.catalogue()[1]
        self.assertEqual(self.catalogue()[1], original)
        self.write('one.desktop', Name='Another Name')
        renamed = self.catalogue()[1]
        self.assertNotEqual(renamed, original)
        self.write('one.desktop', Name='Another Name', Exec='/usr/bin/other')
        self.assertNotEqual(self.catalogue()[1], renamed)
        self.assertRegex(original, r'^[a-f0-9]{16}$')


class UntrustedEntriesTest(DiscoveryBase):
    def test_each_unparseable_file_logs_once_and_does_not_hide_healthy_entries(self):
        bad = [b'\x89PNG\0\xffjunk', b'\xff\xfe\x01junk', b'[Desktop Entry\nName=Broken\n',
               b'[Desktop Entry]\nType=Application\nName=Bad\nExec="unterminated\n',
               b'[Desktop Entry]\nType=Application\nName=Bad\nExec=/usr/bin/tool\nExec=/usr/bin/other\n',
               b'[Desktop Entry]\n[Desktop Entry]\n',
               b'[Desktop Entry]\nmissing equals\n',
               b'[Desktop Entry]\nType=Application\nName=Bad\nExec=/usr/bin/tool\nTerminal=yes\n',
               b'[Desktop Entry]\nType=Application\nName=\nExec=/usr/bin/tool\n']
        for n, text in enumerate(bad):
            self.write(f'bad{n}.desktop', text)
        self.write('good.desktop')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            apps, _ = self.catalogue()
        self.assertEqual(set(apps), {'good'})
        self.assertEqual(len(logs.output), len(bad))
        self.assertTrue(all('skipped' in message for message in logs.output))

    def test_utf8_is_decoded_with_replacement(self):
        self.write('replacement.desktop', b'[Desktop Entry]\nType=Application\nName=My \xff App\nExec=/usr/bin/tool\n')
        self.assertEqual(self.catalogue()[0]['replacement'].name, 'My \ufffd App')

    def test_read_size_is_bounded_and_oversized_files_are_skipped(self):
        path = self.write('oversized.desktop', b'x' * (shell.MAX_DESKTOP_ENTRY + 1))
        with mock.patch.object(shell.os, 'fdopen', wraps=os.fdopen) as fdopen:
            with self.assertRaisesRegex(ValueError, '1 MiB'):
                shell.read_desktop_entry(path)
        # Size is rejected before any read.
        self.assertEqual(fdopen.call_count, 1)
        self.write('good.desktop')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertEqual(set(self.catalogue()[0]), {'good'})
        self.assertEqual(len(logs.output), 1)
        start = b'[Desktop Entry]\nType=Application\nName=Exact\nExec=/usr/bin/tool\n#'
        exact = self.write('exact.desktop', start + b'x' * (shell.MAX_DESKTOP_ENTRY - len(start)))
        self.assertEqual(shell.read_desktop_entry(exact)['Name'], 'Exact')

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'Unix FIFO')
    def test_a_fifo_never_blocks_discovery(self):
        os.mkfifo(self.folders[0] / 'pipe.desktop')
        self.write('good.desktop')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertEqual(set(self.catalogue()[0]), {'good'})
        self.assertEqual(len(logs.output), 1)

    def test_only_the_desktop_entry_group_is_used_and_nothing_is_included(self):
        self.write('good.desktop', '[Desktop Entry]\nType=Application\nName=Main\nExec=/usr/bin/tool\n'
                   'X-Include=/some/other/file\n[Desktop Action Run]\nName=Wrong\nExec=/usr/bin/other\n'
                   'Hidden=true\nThis is not parsed as a key\n')
        apps, _ = self.catalogue()
        self.assertEqual(apps['good'].argv, ('/usr/bin/tool',))
        self.assertEqual(apps['good'].name, 'Main')

    def test_shell_syntax_and_unknown_codes_are_rejected_or_passed_literally(self):
        invalid = ['/usr/bin/tool;touch /somewhere', '/usr/bin/tool $HOME', '/usr/bin/tool | other',
                   "sh -c 'echo hello'", '/usr/bin/tool %z', '/usr/bin/tool --name=%c',
                   '/usr/bin/tool "unterminated', '/usr/bin/tool bad\\escape']
        for n, command in enumerate(invalid):
            self.write(f'bad{n}.desktop', Exec=command)
        # Quoted shell metacharacters are ordinary argument bytes; no shell or expansion is involved.
        self.write('literal.desktop', Exec='/usr/bin/tool "$(touch /somewhere); & > *"')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            apps, _ = self.catalogue()
        self.assertEqual(len(logs.output), len(invalid))
        self.assertEqual(set(apps), {'literal'})
        self.assertEqual(apps['literal'].argv, ('/usr/bin/tool', '$(touch /somewhere); & > *'))


class IDsAndRegistryTest(DiscoveryBase):
    def test_ids_are_normalised_bounded_and_repeatable(self):
        cases = {'org.mozilla.firefox.desktop': 'org-mozilla-firefox', 'lunarclient.desktop': 'lunarclient',
                 'UPPER_And-Other!?.desktop': 'upper_and-other--', 'ü test.desktop': '--test',
                 ('long' * 30) + '.desktop': ('long' * 30)[:64]}
        for filename in cases:
            self.write(filename)
        first, _ = self.catalogue()
        self.assertEqual(set(first), set(cases.values()))
        self.assertEqual(set(first), set(self.catalogue()[0]))
        for app in first.values():
            self.assertRegex(app.id, r'^[a-z0-9_-]{1,64}$')

    def test_name_is_plain_trimmed_printable_and_64_characters(self):
        self.write('plain.desktop', Name='  Plain Name  ', **{'Name[de]': 'Lokalisierter Name'})
        self.write('long.desktop', Name='x' * 70)
        self.write('printable.desktop', Name='a\\tb\\nc\\r\u200bd\x7fe')
        apps, _ = self.catalogue()
        self.assertEqual(apps['plain'].name, 'Plain Name')
        self.assertEqual(apps['long'].name, 'x' * 64)
        self.assertEqual(apps['printable'].name, 'abcde')

    def test_collisions_use_folder_order_then_stable_file_order_and_log(self):
        self.write('org.Test.desktop', folder=0, Name='First Folder')
        self.write('org-test.desktop', folder=1, Name='Later Folder')
        self.write('same-name.desktop', Name='First File')
        self.write('same.Name.desktop', Name='Later File')
        self.write('x' * 65 + '.desktop', Name='First Long')
        self.write('x' * 66 + '.desktop', folder=1, Name='Second Long')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            apps, _ = self.catalogue()
        self.assertEqual({key: app.name for key, app in apps.items()},
                         {'org-test': 'First Folder', 'same-name': 'First File', 'x' * 64: 'First Long'})
        self.assertEqual(len(logs.output), 3)
        self.assertTrue(all('loses app ID' in message for message in logs.output))

    def test_registry_ids_and_replacements_win_even_when_unavailable(self):
        for filename in ('browser.desktop', 'terminal.desktop', 'notepad.desktop', 'google-chrome.desktop',
                         'com.google.Chrome.desktop', 'foot.desktop', 'org.kde.kwrite.desktop'):
            self.write(filename)
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            apps, _ = self.catalogue(registry=REGISTRY)
        self.assertEqual(set(apps), {'browser', 'terminal', 'notepad'})
        self.assertTrue(all(not app.discovered for app in apps.values()))
        self.assertEqual(apps['browser'].argv, ('/usr/bin/google-chrome',))
        self.assertEqual(shell.resolve(apps['browser'], self.executables.__contains__)[2], 'not_installed')
        self.assertEqual(len(logs.output), 3)

    def test_optional_registry_keys_are_strictly_validated(self):
        from test_aresos_shell import entry
        app = shell.parse_entry(entry('reviewed', replaces=['one.desktop', 'two.desktop'], gpu='discrete'))
        self.assertEqual(app.replaces, ('one.desktop', 'two.desktop'))
        self.assertEqual(app.gpu, 'discrete')
        for fields in (dict(replaces='one.desktop'), dict(replaces=[None]), dict(replaces=['../x.desktop']),
                       dict(replaces=['one.desktop'] * (shell.MAX_LIST + 1)), dict(gpu='integrated'),
                       dict(gpu=True), dict(gpu=None)):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                shell.parse_entry(entry('bad', **fields))


class DiscoveredLaunchTest(DiscoveryBase):
    def test_first_word_is_resolved_once_using_only_the_fixed_path(self):
        self.write('bare.desktop', Exec='tool --argument')
        self.write('relative.desktop', Exec='./tool')
        self.write('assignment.desktop', Exec='FOO=bar tool')
        calls = []

        def executable(path):
            calls.append(path)
            return path in self.executables

        apps, _ = self.catalogue(executable=executable)
        self.assertEqual(set(apps), {'bare'})
        self.assertEqual(apps['bare'].argv, ('/usr/bin/tool', '--argument'))
        self.assertEqual(calls[:2], ['/usr/local/bin/tool', '/usr/bin/tool'])
        # A new higher-priority binary cannot change a stored launch definition.
        self.executables.add('/usr/local/bin/tool')
        calls.clear()
        self.assertEqual(shell.resolve(apps['bare'], executable), (['/usr/bin/tool', '--argument'], '~', None))
        self.assertEqual(calls, ['/usr/bin/tool'])
        self.executables.remove('/usr/bin/tool')
        self.assertEqual(shell.resolve(apps['bare'], executable)[2], 'not_installed')

    def test_local_bin_wins_and_absolute_paths_are_kept_as_written(self):
        self.executables.update({'/usr/local/bin/tool', '/opt/my app/program'})
        self.write('bare.desktop', Exec='tool')
        self.write('absolute.desktop', Exec='"/opt/my app/program" --argument')
        apps, _ = self.catalogue()
        self.assertEqual(apps['bare'].argv[0], '/usr/local/bin/tool')
        self.assertEqual(apps['absolute'].argv[0], '/opt/my app/program')

    def test_flatpak_file_and_url_forwarding_markers_are_dropped_as_groups(self):
        # Flatpak writes these markers only with --file-forwarding (review 1, finding 6: only then are they markers).
        for n, codes in enumerate(('@@u %u @@', '@@u %U @@', '@@ %f @@', '@@ %F @@')):
            self.write(f'forward{n}.desktop',
                       Exec=f'/usr/bin/flatpak run --file-forwarding org.example.App {codes} --flag')
        apps, _ = self.catalogue()
        self.assertEqual(len(apps), 4)
        for app in apps.values():
            self.assertEqual(app.argv, ('/usr/bin/flatpak', 'run', '--file-forwarding', 'org.example.App', '--flag'))
        for n, codes in enumerate(('@@u %u', '@@u %f @@', '@@ something @@')):
            self.write(f'bad{n}.desktop', Exec=f'/usr/bin/flatpak run --file-forwarding org.example.App {codes}')
        with self.assertLogs(shell.LOG, level='WARNING') as logs:
            self.assertEqual(set(self.catalogue()[0]), set(apps))
        self.assertEqual(len(logs.output), 3)

    def test_field_codes_keep_the_existing_exec_parser_behaviour(self):
        path = self.write('fields.desktop', Name='Tool Name', Icon='tool-icon',
                          Exec='/usr/bin/tool %i %c %k %f %F %u %U %d %D %n %N %v %m 100%%')
        self.assertEqual(self.catalogue()[0]['fields'].argv,
                         ('/usr/bin/tool', '--icon', 'tool-icon', 'Tool Name', str(path), '100%'))

    def test_path_is_absolute_or_home_and_uses_desktop_string_escapes(self):
        for name, directory in (('absolute', '/srv/my\\snotes'), ('relative', 'relative/path'), ('home', '')):
            self.write(name + '.desktop', Path=directory)
        apps, _ = self.catalogue()
        self.assertEqual({key: app.working_directory for key, app in apps.items()},
                         {'absolute': '/srv/my notes', 'relative': '~', 'home': '~'})

    def test_discovered_launch_uses_its_own_scope_and_app_slice_without_a_shell(self):
        self.write('org.test.Program.desktop', Exec='/usr/bin/tool "a; b & c"', Path='/srv/notes')
        app = self.catalogue()[0]['org-test-program']
        popen = mock.Mock(return_value=Proc())
        launcher = shell.ScopeLauncher(popen=popen, environ={'HOME': '/test/home', 'WAYLAND_DISPLAY': 'test-display',
                                       'ARESOS_LAUNCH_NONCE': 'private', 'ARESOS_DESKTOP_INSTANCE': 'private'})
        argv, directory, reason = shell.resolve(app, self.executables.__contains__)
        self.assertIsNone(reason)
        launcher.spawn(app, argv, directory, 'ab1234')
        command = popen.call_args.args[0]
        self.assertEqual(command, ['/usr/bin/systemd-run', '--user', '--scope', '--quiet', '--collect',
                                  '--slice=app.slice', '--unit=app-aresos-org\\x2dtest\\x2dprogram-ab1234.scope',
                                  '--description=AresOS app: Test Program', '--expand-environment=no', '--',
                                  '/usr/bin/tool', 'a; b & c'])
        options = popen.call_args.kwargs
        self.assertEqual(options['cwd'], '/srv/notes')
        self.assertEqual(options['env'], {'HOME': '/test/home', 'WAYLAND_DISPLAY': 'test-display'})
        self.assertTrue(options['start_new_session'] and options['close_fds'])
        self.assertNotIn('shell', options)

    def test_terminal_programs_have_their_own_app_ids_and_home_working_directory(self):
        # The real btop entry is Hidden=true; this deliberate visible test copy exercises Terminal=true.
        text = (FIXTURES / 'btop.desktop').read_text().replace('Hidden=true', 'Hidden=false')
        self.write('btop.desktop', text)
        self.write('other.desktop', Exec='/usr/bin/other --flag', Terminal='true')
        apps, _ = self.catalogue()
        self.assertEqual(shell.resolve(apps['btop'], self.executables.__contains__),
                         (['/usr/bin/foot', '--app-id=aresos.app.btop', '/usr/bin/btop'], '~', None))
        self.assertEqual(shell.resolve(apps['other'], self.executables.__contains__)[0],
                         ['/usr/bin/foot', '--app-id=aresos.app.other', '/usr/bin/other', '--flag'])
        popen = mock.Mock(return_value=Proc())
        launcher = shell.ScopeLauncher(popen=popen, environ={'HOME': str(self.root)})
        argv, directory, _ = shell.resolve(apps['btop'], self.executables.__contains__)
        launcher.spawn(apps['btop'], argv, directory, 'term123')
        self.assertEqual(popen.call_args.kwargs['cwd'], str(self.root))
        self.assertEqual(popen.call_args.args[0][-3:],
                         ['/usr/bin/foot', '--app-id=aresos.app.btop', '/usr/bin/btop'])
        self.assertIn('--unit=app-aresos-btop-term123.scope', popen.call_args.args[0])

    def test_missing_terminal_is_not_listed_and_disappearing_terminal_is_unavailable(self):
        self.write('terminal.desktop', Terminal='true')
        apps, _ = self.catalogue()
        self.executables.remove('/usr/bin/foot')
        self.assertEqual(self.catalogue()[0], {})
        self.assertEqual(shell.resolve(apps['terminal'], self.executables.__contains__)[2], 'not_installed')


class GraphicsTest(DiscoveryBase):
    def test_each_gpu_hint_selects_discrete_and_category_matching_is_exact(self):
        fields = [dict(PrefersNonDefaultGPU='true'), dict(**{'X-KDE-RunOnDiscreteGpu': 'true'}),
                  dict(Categories='Network;Game;'), dict(Categories='GameUtility;'),
                  dict(PrefersNonDefaultGPU='false', Categories='game;')]
        for n, values in enumerate(fields):
            self.write(f'gpu{n}.desktop', **values)
        apps, _ = self.catalogue()
        self.assertEqual([apps[f'gpu{n}'].gpu for n in range(len(fields))],
                         ['discrete', 'discrete', 'discrete', None, None])

    def test_every_launch_drops_inherited_gpu_keys_then_only_discrete_adds_the_three(self):
        self.write('normal.desktop')
        self.write('game.desktop', Categories='Game;')
        apps, _ = self.catalogue()
        registry, _ = shell.load_registry(str(REGISTRY))
        inherited = {'HOME': str(self.root), 'PATH': '/test/path', 'WAYLAND_DISPLAY': 'test-display',
                     **{key: 'inherited' for key in shell.GPU_KEYS},
                     **{key: 'private' for key in shell.PRIVATE_ENVIRONMENT}}
        base = {'HOME': str(self.root), 'PATH': '/test/path', 'WAYLAND_DISPLAY': 'test-display'}
        for app in [*apps.values(), *registry.values(), dataclasses.replace(registry['browser'], gpu='discrete')]:
            for present in (False, True):
                with self.subTest(app=app.id, gpu=app.gpu, nvidia=present):
                    popen = mock.Mock(return_value=Proc())
                    driver = mock.Mock(return_value=present)
                    launcher = shell.ScopeLauncher(popen=popen, environ=inherited, nvidia=driver)
                    launcher.spawn(app, list(app.argv), '~', 'gpu123')
                    expected = base | (shell.NVIDIA_OFFLOAD if app.gpu == 'discrete' and present else {})
                    self.assertEqual(popen.call_args.kwargs['env'], expected)
                    self.assertEqual(driver.call_count, int(app.gpu == 'discrete'))
        self.assertTrue(all(value == 'inherited' for key, value in inherited.items() if key in shell.GPU_KEYS))

    def test_gpu_constants_match_the_supervisor_and_java_wrapper(self):
        def constant(path, name):
            for node in ast.parse(path.read_text()).body:
                if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in node.targets):
                    return ast.literal_eval(node.value)
            self.fail(f'{name} missing from {path.name}')

        folder = ROOT / 'os/config/usr/libexec'
        self.assertEqual(shell.NVIDIA_OFFLOAD, constant(folder / 'aresos-desktop', 'NVIDIA_OFFLOAD'))
        self.assertEqual(set(shell.GPU_KEYS), set(constant(folder / 'aresos-desktop-java', 'GPU_KEYS')))
        self.assertEqual(shell.NVIDIA_OFFLOAD, {'__NV_PRIME_RENDER_OFFLOAD': '1',
                                               '__GLX_VENDOR_LIBRARY_NAME': 'nvidia',
                                               '__VK_LAYER_NV_optimus': 'NVIDIA_only'})

    def test_nvidia_presence_requires_a_driver_gpu_listing(self):
        self.assertFalse(shell.nvidia_present(str(self.root)))
        folder = self.root / 'proc/driver/nvidia/gpus'
        folder.mkdir(parents=True)
        self.assertFalse(shell.nvidia_present(str(self.root)))
        (folder / '0000:01:00.0').mkdir()
        self.assertTrue(shell.nvidia_present(str(self.root)))
        with mock.patch.object(shell.os, 'listdir', side_effect=PermissionError):
            self.assertFalse(shell.nvidia_present(str(self.root)))


class CompatibilityTest(Base):
    def test_discovery_is_not_exposed_to_1_0_listing_or_launches(self):
        folder = pathlib.Path(self.folder.name) / 'entries'
        folder.mkdir()
        (folder / 'lunarclient.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Lunar Client\nExec=/usr/bin/tool\n')
        catalogue = shell.Catalogue(str(REGISTRY), entry_dirs=[folder], executable=lambda p: True)
        catalogue.refresh(self.clock())
        helper = shell.Helper(str(REGISTRY), 'desk-1', 'test-nonce-0123456789abcdef', self.journal,
                              registry=(catalogue.apps, catalogue.revision), catalogue=catalogue,
                              launcher=self.launcher(), clock=self.clock, executable=lambda p: True)
        self.addCleanup(helper.watcher.stop)
        self.assertIn('lunarclient', helper.apps)
        conn = self.connect(helper)
        listing = self.request(helper, conn, 'list_apps')
        self.assertEqual(listing['revision'], shell.load_registry(str(REGISTRY))[1])
        self.assertEqual({app['id'] for app in listing['apps']}, {'browser', 'terminal', 'notepad'})
        self.assertTrue(all(set(app) == {'id', 'name', 'available', 'reason'} for app in listing['apps']))
        reply = self.request(helper, conn, 'open_app', 'discover-1', app_id='lunarclient')
        self.assertEqual(reply['error'], 'unknown_app')
        self.popen.assert_not_called()


if __name__ == '__main__':
    unittest.main()
