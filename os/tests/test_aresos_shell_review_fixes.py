"""Package 30, review fixes 1, step B: the package review's findings (REVIEW-1.md 1-4, 6, 7).

Everything is synthetic: no real program, window or compositor. Time moves through the tests' own clock.
"""
import json
import os

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
