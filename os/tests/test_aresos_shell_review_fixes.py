"""Package 30, review fixes 1, step B: the package review's findings (REVIEW-1.md 1-4, 6, 7).

Everything is synthetic: no real program, window or compositor. Time moves through the tests' own clock.
"""
import json
import os
import pathlib
from unittest import mock

from test_aresos_shell import shell, Base, Conn, REGISTRY, INSTANCE, NONCE, ALL
from test_aresos_shell_discovery import DiscoveryBase


class FlatpakMarkerTest(DiscoveryBase):
    """Finding 6: `@@` is a Flatpak marker only inside a recognised `flatpak run ... --file-forwarding` command."""

    def test_ordinary_programs_keep_literal_markers(self):
        self.write('alone.desktop', Exec='/usr/bin/tool @@')
        self.write('around.desktop', Exec='/usr/bin/tool @@ %f @@')
        self.write('url.desktop', Exec='/usr/bin/tool @@u %u @@ --flag')
        apps, _ = self.catalogue()
        self.assertEqual(apps['alone'].argv, ('/usr/bin/tool', '@@'))
        self.assertEqual(apps['around'].argv, ('/usr/bin/tool', '@@', '@@'))
        self.assertEqual(apps['url'].argv, ('/usr/bin/tool', '@@u', '@@', '--flag'))

    def test_flatpak_without_forwarding_or_with_it_after_the_app_keeps_them_too(self):
        self.write('plain.desktop', Exec='/usr/bin/flatpak run org.example.App @@ %f @@')
        # After the app ID, --file-forwarding is the app's own argument: flatpak forwards nothing.
        self.write('late.desktop', Exec='/usr/bin/flatpak run org.example.App --file-forwarding @@ %f @@')
        apps, _ = self.catalogue()
        self.assertEqual(apps['plain'].argv, ('/usr/bin/flatpak', 'run', 'org.example.App', '@@', '@@'))
        self.assertEqual(apps['late'].argv,
                         ('/usr/bin/flatpak', 'run', 'org.example.App', '--file-forwarding', '@@', '@@'))

    def test_recognised_forwarding_commands_lose_their_markers_both_ways(self):
        self.write('fwd.desktop',
                   Exec='/usr/bin/flatpak run --branch=stable --arch=x86_64 --file-forwarding org.example.App @@u %U @@')
        self.write('bare.desktop', Exec='flatpak run --file-forwarding org.example.App @@ %F @@ --flag')
        apps, _ = self.catalogue()
        self.assertEqual(apps['fwd'].argv, ('/usr/bin/flatpak', 'run', '--branch=stable', '--arch=x86_64',
                                            '--file-forwarding', 'org.example.App'))
        self.assertEqual(apps['bare'].argv[1:], ('run', '--file-forwarding', 'org.example.App', '--flag'))


class FlatpakAppIdTest(DiscoveryBase):
    """Finding 7: without X-Flatpak, a Flatpak's app ID comes from its command, or is left out."""

    def test_app_id_from_the_command_for_details_and_window_identities(self):
        self.write('my-firefox.desktop', Name='Firefox',
                   Exec='/usr/bin/flatpak run --branch=stable --arch=x86_64 --command=firefox --file-forwarding '
                        'org.mozilla.firefox @@u %u @@')
        app = self.catalogue()[0]['my-firefox']
        self.assertEqual(app.exec_name, 'org.mozilla.firefox')
        self.assertEqual(app.app_ids, ('my-firefox', 'org.mozilla.firefox'))
        windows = shell.Windows()
        windows.set_registry({app.id: app})
        windows.new(1)
        windows.app_id(1, 'org.mozilla.firefox')
        windows.done(1)
        self.assertEqual(windows.toplevels[1].owner, 'my-firefox')

    def test_x_flatpak_still_wins_and_flatpak_itself_is_never_an_identity(self):
        self.write('chat.desktop', Exec='/usr/bin/flatpak run org.example.Chat', **{'X-Flatpak': 'org.example.Chat'})
        app = self.catalogue()[0]['chat']
        self.assertEqual(app.exec_name, 'org.example.Chat')
        self.assertEqual(app.app_ids, ('chat', 'org.example.Chat'))

    def test_an_id_that_cannot_be_worked_out_is_left_out_not_invented(self):
        commands = {
            'separate-value': '/usr/bin/flatpak run --runtime org.freedesktop.Platform org.example.Real',
            'command-word': '/usr/bin/flatpak run --command firefox org.mozilla.firefox',
            'not-an-id': '/usr/bin/flatpak run firefox',
            'no-app': '/usr/bin/flatpak run --user',
        }
        for name, command in commands.items():
            self.write(name + '.desktop', Exec=command)
        apps, _ = self.catalogue()
        for name in commands:
            with self.subTest(name):
                self.assertIsNone(apps[name].exec_name)
                self.assertEqual(apps[name].app_ids, (name,))  # only the desktop file's own ID
                self.assertNotIn('exec_name', shell.Helper.app_row(mock_helper(), apps[name], details=True))

    def test_ordinary_programs_keep_their_file_name(self):
        self.write('tool.desktop', Exec='/usr/bin/tool run org.example.App')
        app = self.catalogue()[0]['tool']
        self.assertEqual((app.exec_name, app.app_ids), ('tool', ('tool',)))


def mock_helper():
    """Just enough of a Helper for app_row: every program available."""
    class Stub:
        def availability(self, app):
            return (), '~', None
    return Stub()


class LegacyDiscoveredIdTest(Base):
    """Finding 3: a 1.0 client asking for a discovered ID gets exactly the old failed-launch answer and journal entry.

    The expected answers are whole messages, as the pre-package-30 helper (origin/main) produced them for any ID it
    did not know; that path is also unchanged here, so the unknown 'no-such-app' answer must match it too.
    """

    def setUp(self):
        super().setUp()
        folder = os.path.join(self.folder.name, 'entries')
        os.mkdir(folder)
        with open(os.path.join(folder, 'lunarclient.desktop'), 'w') as handle:
            handle.write('[Desktop Entry]\nType=Application\nName=Lunar Client\nExec=/usr/bin/tool\n')
        self.catalogue = shell.Catalogue(str(REGISTRY), entry_dirs=[folder], executable=lambda p: True, deployments=())
        self.catalogue.refresh(self.clock())

    def helper_for(self, journal):
        helper = shell.Helper(str(REGISTRY), INSTANCE, NONCE, journal, registry=(self.catalogue.apps,
                              self.catalogue.revision), catalogue=self.catalogue, launcher=self.launcher(),
                              clock=self.clock, executable=lambda p: True)
        self.addCleanup(helper.watcher.stop)
        return helper

    @staticmethod
    def old_answer(request_id, app_id):
        return {'protocol': 'aresos-shell/1.0', 'id': request_id, 'ok': False, 'request_id': request_id,
                'launch_id': None, 'app_id': app_id, 'state': 'failed', 'error': 'unknown_app',
                'message': 'no reviewed launch definition'}

    def test_whole_answer_journal_entry_and_replays_match_the_old_helper(self):
        helper = self.helper_for(self.journal)
        self.assertTrue(helper.apps['lunarclient'].discovered)
        conn = self.connect(helper)
        for app_id, request_id in (('lunarclient', 'o-1'), ('no-such-app', 'o-2')):
            with self.subTest(app_id):
                self.assertEqual(self.request(helper, conn, 'open_app', request_id, app_id=app_id),
                                 self.old_answer(request_id, app_id))
                self.assertEqual(helper.journal.entries[request_id],
                                 {'app_id': app_id, 'launch_id': None, 'state': 'failed', 'error': 'unknown_app',
                                  'message': 'no reviewed launch definition', 'updated': 100.0})
                with open(self.journal) as handle:
                    self.assertIn(request_id, json.load(handle)['launches'])
                # The same request again: the same answer from the journal; another app: request_id_reused.
                self.assertEqual(self.request(helper, conn, 'open_app', request_id, app_id=app_id),
                                 self.old_answer(request_id, app_id))
                reused = self.request(helper, conn, 'open_app', request_id, app_id='terminal')
                self.assertEqual((reused['ok'], reused['error']), (False, 'request_id_reused'))
        self.popen.assert_not_called()
        # A restarted helper replays the journaled answer, as before.
        again = self.helper_for(self.journal)
        self.assertEqual(self.request(again, self.connect(again), 'open_app', 'o-1', app_id='lunarclient'),
                         self.old_answer('o-1', 'lunarclient'))
        self.popen.assert_not_called()

    def test_a_1_1_launch_is_never_shown_or_repeated_to_a_1_0_client(self):
        helper = self.helper_for(self.journal)
        newer = Conn()
        helper.connected(newer)
        self.request(helper, newer, 'hello', 'h-1', major=1, minor=1, capabilities=ALL, instance=INSTANCE,
                     nonce=NONCE)
        started = self.request(helper, newer, 'open_app', 'o-1', app_id='lunarclient')
        self.assertEqual(started['state'], 'starting')
        older = self.connect(helper)
        self.assertEqual(self.request(helper, older, 'open_app', 'o-1', app_id='lunarclient'),
                         self.old_answer('o-1', 'lunarclient'))
        self.assertEqual(helper.journal.entries['o-1']['state'], 'starting')  # the real launch is untouched
        self.assertEqual(self.popen.call_count, 1)


class HintTest(DiscoveryBase):
    """Finding 1: reviewed hints, validated as strictly as registry entries."""

    def hint(self, name, data):
        folder = self.registry / 'hints'
        folder.mkdir(exist_ok=True)
        (folder / name).write_text(data if isinstance(data, str) else json.dumps(data))

    def test_the_image_ships_exactly_the_lunar_and_steam_hints(self):
        hints = shell.load_hints(str(REGISTRY / 'hints'))
        self.assertEqual(hints, {
            'lunarclient.desktop': shell.Hint('lunarclient.desktop', ('com.mojang.minecraft',), ()),
            'steam.desktop': shell.Hint('steam.desktop', (), ('steam_app_',))})

    def test_broken_hints_are_refused_with_a_log_line_each(self):
        good = {'schema': 1, 'desktop_id': 'good.desktop', 'app_ids': ['org.good.Game']}
        broken = {
            'typo': dict(good, app_idz=['x']), 'schema': dict(good, schema=2), 'noid': {'schema': 1, 'app_ids': ['x']},
            'badid': dict(good, desktop_id='../x.desktop'), 'none': {'schema': 1, 'desktop_id': 'none.desktop'},
            'empty': dict(good, app_ids=[]), 'bad-identity': dict(good, app_ids=['has space']),
            'desktop': dict(good, app_ids=['aresos-desktop']), 'desktop-prefix': dict(good, app_ids=[],
                                                                                        app_id_prefixes=['aresos-']),
            'short-prefix': dict(good, app_ids=[], app_id_prefixes=['st_']),
            'no-separator': dict(good, app_ids=[], app_id_prefixes=['steam']),
            'twice': dict(good, app_ids=['a.b', 'a.b']), 'nine': dict(good, app_ids=[f'id{n}' for n in range(9)]),
            'string': dict(good, app_ids='org.good.Game'), 'nan': '{"schema": NaN}', 'garbage': '{not json',
        }
        for name, data in broken.items():
            self.hint(name + '.json', data)
        with self.assertLogs(shell.LOG, level='ERROR') as logs:
            self.assertEqual(shell.load_hints(str(self.registry / 'hints')), {})
        self.assertEqual(len(logs.output), len(broken))

    def test_hints_that_name_one_program_twice_or_could_claim_one_window_are_all_refused(self):
        self.hint('a.json', {'schema': 1, 'desktop_id': 'a.desktop', 'app_ids': ['shared']})
        self.hint('b.json', {'schema': 1, 'desktop_id': 'b.desktop', 'app_ids': ['shared']})
        self.hint('c1.json', {'schema': 1, 'desktop_id': 'c.desktop', 'app_ids': ['c.one']})
        self.hint('c2.json', {'schema': 1, 'desktop_id': 'c.desktop', 'app_ids': ['c.two']})
        self.hint('d.json', {'schema': 1, 'desktop_id': 'd.desktop', 'app_id_prefixes': ['game_']})
        self.hint('e.json', {'schema': 1, 'desktop_id': 'e.desktop', 'app_id_prefixes': ['game_app_']})
        self.hint('f.json', {'schema': 1, 'desktop_id': 'f.desktop', 'app_ids': ['game_f']})
        self.hint('ok.json', {'schema': 1, 'desktop_id': 'ok.desktop', 'app_ids': ['ok.window']})
        with self.assertLogs(shell.LOG, level='ERROR'):
            self.assertEqual(set(shell.load_hints(str(self.registry / 'hints'))), {'ok.desktop'})

    def test_a_hint_beats_discovered_guesses_but_never_a_registry_identity_or_the_desktop(self):
        self.write('lunarclient.desktop', StartupWMClass='lunarclient')
        self.write('mc.desktop', folder=1, StartupWMClass='com.mojang.minecraft')
        self.write('google-chrome.desktop', folder=1)
        for name in ('browser.json', 'notepad.json', 'terminal.json'):
            (self.registry / name).write_text((REGISTRY / name).read_text())
        self.hint('lunar.json', {'schema': 1, 'desktop_id': 'lunarclient.desktop',
                                 'app_ids': ['com.mojang.minecraft', 'aresos.terminal'],
                                 'app_id_prefixes': ['org.kde.']})
        self.hint('chrome.json', {'schema': 1, 'desktop_id': 'google-chrome.desktop', 'app_ids': ['chrome.extra']})
        apps, _ = self.catalogue()
        self.assertEqual(apps['lunarclient'].app_ids, ('lunarclient', 'tool', 'com.mojang.minecraft'))
        self.assertEqual(apps['mc'].app_ids, ('mc',))  # its guess loses to the reviewed hint
        self.assertNotIn('chrome.extra', apps['browser'].app_ids)  # registry entries keep their reviewed identities
        windows = shell.Windows()
        windows.set_registry(apps)
        for handle, (identity, owner) in enumerate((('com.mojang.minecraft', 'lunarclient'),
                                                    ('aresos.terminal', 'terminal'),
                                                    ('org.kde.kwrite', 'notepad'),  # exact beats the prefix
                                                    ('org.kde.dolphin', 'lunarclient'),
                                                    ('aresos-desktop', shell.Windows.SHELL)), 1):
            windows.new(handle)
            windows.app_id(handle, identity)
            windows.done(handle)
            self.assertEqual(windows.toplevels[handle].owner, owner, identity)

    def test_a_hint_for_a_program_that_is_not_installed_changes_nothing(self):
        self.write('other.desktop', StartupWMClass='com.mojang.minecraft')
        self.hint('lunar.json', {'schema': 1, 'desktop_id': 'lunarclient.desktop', 'app_ids': ['com.mojang.minecraft']})
        self.assertEqual(self.catalogue()[0]['other'].app_ids, ('com.mojang.minecraft', 'other', 'tool'))

    def test_a_changed_hint_changes_the_catalogue_and_its_revision(self):
        self.write('lunarclient.desktop')
        catalogue = shell.Catalogue(str(self.registry), entry_dirs=self.folders,
                                    executable=self.executables.__contains__, deployments=[self.deployment])
        catalogue.refresh(0.0)
        before = catalogue.revision
        self.hint('lunar.json', {'schema': 1, 'desktop_id': 'lunarclient.desktop', 'app_ids': ['com.mojang.minecraft']})
        self.assertTrue(catalogue.refresh(shell.CATALOGUE_CHECK))
        self.assertIn('com.mojang.minecraft', catalogue.apps['lunarclient'].app_ids)
        self.assertNotEqual(catalogue.revision, before)


from test_aresos_shell_windows import DiscoveredBase  # noqa: E402  (after the Base-only classes above)


class OwnershipBase(DiscoveredBase):
    """The windows tests' programs, plus Steam, with the image's hints; Chrome is the reviewed browser."""

    def start(self, tracked=True, journal=None, windows=None):
        apps, revision = shell.load_registry(REGISTRY)
        apps.update({app_id: self.app(app_id) for app_id in ('lunarclient', 'discord', 'steam')})
        apps = shell.apply_hints(apps, shell.load_hints(str(REGISTRY / 'hints')))
        self.windows = windows or shell.Windows(clock=self.clock)
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, journal or self.journal,
                                    registry=(apps, revision), launcher=self.launcher(), windows=self.windows,
                                    activate=self.activate, clock=self.clock, executable=lambda path: True)
        self.addCleanup(self.helper_.watcher.stop)
        self.conn = self.connect(self.helper_)
        return self.helper_

    def setUp(self):
        super().setUp()
        self.start()
        self.window(1, 'aresos-desktop', active=True)

    def later(self, seconds):
        self.now[0] += seconds
        self.helper_.tick()

    def focus_events(self, since=0):
        return [(e['focus'], e['reason'], e.get('app_id')) for e in self.conn.events('shell_focus')[since:]]


class HintedOwnershipTest(OwnershipBase):
    """Finding 1's scenarios, each with time moving and its closing consequences."""

    def test_lunar_with_chrome_open(self):
        self.open('browser', 'o-c')
        self.window(2, 'google-chrome', active=True)
        self.later(5)
        self.open('lunarclient', 'o-l')
        self.window(3, 'lunarclient', active=True)
        self.later(4)
        self.window(4, 'com.mojang.minecraft', active=True)
        self.assertEqual(self.windows.toplevels[4].owner, 'lunarclient')
        self.later(2)
        self.close(3)  # the launcher goes away while the game runs
        self.later(shell.HANDOFF * 4)
        self.assertEqual(self.activations, [])
        self.assertEqual((self.state('o-l'), self.state('o-c')), ('focused', 'background'))
        self.later(60)
        self.close(4)
        self.assertEqual(self.activations, [])  # the close waits out the hand-over interval
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual(self.activations, [1])
        self.assertEqual((self.state('o-l'), self.state('o-c')), ('closed', 'background'))
        self.assertEqual(self.focus_events()[-1], ('foreground', 'app_closed', 'lunarclient'))

    def lunar_started(self):
        self.open('lunarclient', 'o-l')
        self.window(3, 'lunarclient', active=True)
        self.later(3)

    def game_closes_and_the_hub_returns(self, activations):
        self.later(30)
        self.close(4)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual(self.activations, activations)
        self.assertEqual(self.state('o-l'), 'closed')
        self.assertEqual(self.helper_.shell, 'foreground')

    def test_launcher_closed_shortly_before_the_game_appears(self):
        self.lunar_started()
        self.close(3)
        self.later(shell.HANDOFF / 2)
        self.window(4, 'com.mojang.minecraft', active=True)
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-l')), ([], 'focused'))
        self.game_closes_and_the_hub_returns([1])

    def test_launcher_closed_long_before_the_game_appears(self):
        self.lunar_started()
        self.close(3)
        self.later(shell.HANDOFF + 0.01)  # nothing of Lunar's is open: an honest return
        self.assertEqual((self.activations, self.state('o-l')), ([1], 'closed'))
        self.focus(1)
        self.later(5)
        self.window(4, 'com.mojang.minecraft', active=True)  # the compositor gives the game the focus
        self.assertEqual(self.focus_events()[-1], ('background', 'app_activated', 'lunarclient'))
        self.assertEqual(self.state('o-l'), 'closed')  # a final launch stays final
        self.game_closes_and_the_hub_returns([1, 1])

    def test_launcher_closed_in_the_same_compositor_batch_as_the_game_appears(self):
        self.lunar_started()
        self.windows.gone(3)
        self.windows.new(4)
        self.windows.app_id(4, 'com.mojang.minecraft')
        self.windows.state(4, True)
        self.windows.done(4)
        self.helper_.windows_changed()
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-l')), ([], 'focused'))
        self.assertEqual(self.helper_.handles['o-l'], {4})
        self.game_closes_and_the_hub_returns([1])

    def test_launcher_closed_after_the_game_appears(self):
        self.lunar_started()
        self.window(4, 'com.mojang.minecraft', active=True)
        self.later(10)
        self.close(3)
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-l')), ([], 'focused'))
        self.game_closes_and_the_hub_returns([1])

    def test_discord_resident_without_a_window_while_an_unrelated_window_opens(self):
        self.open('discord', 'o-d')
        unit = self.helper_.journal.entries['o-d']['unit']
        self.active_units.add(unit)  # Discord stays resident in its scope
        self.window(2, 'discord', active=True)
        self.later(5)
        self.close(2)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual((self.state('o-d'), self.activations), ('closed', [1]))
        self.focus(1)
        self.scope_pass(self.helper_)
        self.later(5)
        states = len(self.conn.events('app_state'))
        self.window(5, 'org.example.Unrelated', active=True)
        self.assertIsNone(self.windows.toplevels[5].owner)
        self.assertEqual(self.focus_events()[-1], ('background', 'other_window', None))
        # A second click hands over to the resident Discord; the unrelated window must not confirm it.
        self.open('discord', 'o-d2')
        self.helper_.processes['o-d2'].code = 0
        self.later(shell.WINDOW_TIMEOUT + 1)
        self.scope_pass(self.helper_)
        self.assertEqual(self.state('o-d2'), 'starting')
        self.close(5)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual(self.activations, [1])  # closing a window nobody owns returns nobody
        self.assertEqual(self.conn.events('app_state')[states:], [])  # it changed no launch
        self.window(6, 'discord', active=True)
        self.assertEqual(self.state('o-d2'), 'focused')
        self.later(5)
        self.close(6)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual((self.state('o-d2'), self.activations), ('closed', [1, 1]))

    def test_steam_with_a_game_window(self):
        self.open('steam', 'o-s')
        self.window(2, 'steam', active=True)
        self.later(20)
        self.window(3, 'steam_app_1086940', active=True)
        self.window(7, 'steam_app_')  # the bare prefix is no game's identity
        self.assertEqual(self.windows.toplevels[3].owner, 'steam')
        self.assertIsNone(self.windows.toplevels[7].owner)
        self.close(7)
        self.later(5)
        self.close(2)  # Steam's own window closes; its game keeps it open
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-s')), ([], 'focused'))
        self.later(600)
        self.close(3)
        self.later(shell.HANDOFF + 0.01)
        self.assertEqual((self.activations, self.state('o-s')), ([1], 'closed'))
        self.assertEqual(self.focus_events()[-1], ('foreground', 'app_closed', 'steam'))

    def test_an_unowned_window_in_front_keeps_the_hub_away_until_the_compositor_gives_it(self):
        self.open('lunarclient', 'o-l')
        self.window(3, 'lunarclient', active=True)
        self.window(5, 'java-unknown')
        self.later(5)
        self.close(3)
        self.focus(5)  # the compositor's pick: the window nobody owns
        self.later(shell.HANDOFF * 4)
        self.assertEqual((self.activations, self.state('o-l'), self.helper_.shell), ([], 'closed', 'background'))
        self.focus(1)  # the compositor gives the hub the focus itself
        self.assertEqual(self.focus_events()[-1], ('foreground', 'desktop_activated', None))

    def test_registry_apps_still_return_when_their_last_window_closes_beside_an_unowned_window(self):
        # Nothing changes for the three reviewed apps: their own return rule does not look at other windows.
        self.window(5, 'java-unknown')
        self.open('notepad', 'o-n')
        self.window(2, 'org.kde.kwrite', active=True)
        self.later(5)
        self.close(2)
        self.assertEqual((self.activations, self.state('o-n')), ([1], 'closed'))


class LegacyWindowsTest(Base):
    """Finding 2: with a 1.0 desktop only the registry's identities own windows and trigger returns, also after a
    reconnect. The catalogue is built as production builds it (build(): Discovery over real folders)."""

    def setUp(self):
        super().setUp()
        self.root = pathlib.Path(self.folder.name)
        self.folders = [self.root / str(n) for n in range(5)]
        for folder in self.folders:
            folder.mkdir()
        # Firefox installed, started by hand from the terminal (build() checks executables for real).
        (self.folders[0] / 'firefox.desktop').write_text(
            '[Desktop Entry]\nType=Application\nName=Firefox\nExec=/usr/bin/true\nStartupWMClass=firefox\n')
        self.compositor = []

        def connect(windows, environ):
            self.compositor.append(windows)
            return mock.Mock(activate=self.activate)

        with mock.patch.object(shell, 'desktop_directories', return_value=tuple(map(str, self.folders))), \
                mock.patch.object(shell, 'IconCache', return_value=mock.Mock(**{
                    'take.side_effect': lambda apps, revision: (apps, shell.icons_revision(apps, revision))})):
            self.current, _ = shell.build(str(REGISTRY), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                                          clock=self.clock, connect=connect, environ={'HOME': str(self.root)})
        self.addCleanup(self.current.catalogue.stop)
        self.addCleanup(self.current.watcher.stop)
        self.windows = self.compositor[0]
        self.assertTrue(self.current.apps['firefox'].discovered)

    def window(self, handle, identity, active):
        self.windows.new(handle)
        self.windows.app_id(handle, identity)
        if active:
            for other in self.windows.toplevels.values():
                if other.ready:
                    self.windows.state(other.handle, False)
                    self.windows.done(other.handle)
        self.windows.state(handle, active)
        self.windows.done(handle)
        self.current.windows_changed()

    def focus(self, handle):
        for toplevel in self.windows.toplevels.values():
            self.windows.state(toplevel.handle, toplevel.handle == handle)
            self.windows.done(toplevel.handle)
        self.current.windows_changed()

    def firefox_opens_and_closes_over_the_terminal(self, handle):
        self.window(handle, 'firefox', active=True)
        self.now[0] += 20
        self.current.tick()
        self.windows.gone(handle)
        self.focus(3)  # the compositor's own pick
        for _ in range(3):
            self.now[0] += shell.HANDOFF
            self.current.tick()
        return self.windows

    def hello(self, minor):
        conn = Conn()
        self.current.connected(conn)
        reply = self.request(self.current, conn, 'hello', 'h-1', major=1, minor=minor, capabilities=ALL,
                             instance=INSTANCE, nonce=NONCE)
        self.assertEqual(reply['minor'], minor)
        self.current.tick()
        return conn

    def test_a_1_0_desktop_keeps_todays_window_behaviour_across_reconnects(self):
        conn = self.hello(0)
        self.window(1, 'aresos-desktop', active=True)
        self.request(self.current, conn, 'open_app', 'o-t', app_id='terminal')
        self.window(3, 'aresos.terminal', active=True)
        for round, handle in enumerate((10, 11, 12)):
            with self.subTest(round=round):
                self.firefox_opens_and_closes_over_the_terminal(handle)
                self.assertEqual(self.activations, [])
                self.assertEqual(self.current.shell, 'background')
                self.assertEqual(self.current.journal.entries['o-t']['state'], 'focused')
                self.assertFalse([e for e in conn.events('shell_focus') if e.get('app_id') == 'firefox'])
            if round == 0:
                self.current.disconnected(conn)  # the next round runs with no desktop connected
            elif round == 1:
                conn = self.hello(0)  # the mod reconnects, still speaking 1.0
        # The 1.0 desktop's terminal still returns it when the terminal closes.
        self.windows.gone(3)
        self.current.windows_changed()
        self.assertEqual(self.activations, [1])
        self.assertEqual(self.current.journal.entries['o-t']['state'], 'closed')

    def test_a_1_1_desktop_owns_discovered_windows_and_a_1_0_reconnect_gives_them_up(self):
        self.hello(1)
        self.window(1, 'aresos-desktop', active=True)
        self.window(3, 'aresos.terminal', active=False)
        self.window(10, 'firefox', active=True)
        self.assertEqual(self.windows.toplevels[10].owner, 'firefox')
        self.hello(0)
        self.assertIsNone(self.windows.toplevels[10].owner)
        self.windows.gone(10)
        self.focus(3)
        self.now[0] += shell.HANDOFF * 3
        self.current.tick()
        self.assertEqual(self.activations, [])
        self.hello(1)
        self.window(11, 'firefox', active=True)
        self.assertEqual(self.windows.toplevels[11].owner, 'firefox')
        self.windows.gone(11)
        self.focus(3)
        self.now[0] += shell.HANDOFF + 0.01
        self.current.tick()
        self.assertEqual(self.activations, [1])  # a 1.1 desktop gets the discovered program's return
