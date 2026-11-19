"""Package 25, the guardian: the helper's `windows` report for the supervisor, and the black screen as the helper
sees it (brief 3.4, the lead's fix 4). Everything runs in this process: synthetic windows, and a list or a pipe of
this test's own in place of the supervisor's status pipe. Nothing here talks to a compositor.
"""
import importlib.machinery
import json
import os
import pathlib
import select
import sys
import types
import xml.etree.ElementTree as ET

from test_aresos_shell import shell, Base, REGISTRY, INSTANCE, NONCE

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'os/config'
DESKTOP, BLACK, MAIL, OTHER = 1, 2, 3, 4


def load(name, path):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = types.ModuleType(loader.name)
    sys.modules[loader.name] = module
    loader.exec_module(module)
    return module


class WindowsBase(Base):
    def setUp(self):
        super().setUp()
        self.lines = []
        self.takes = True
        self.minimized = []

    def status(self, **fields):
        """The status pipe: a list of what was written. While `takes` is false the pipe is full: the line is lost."""
        if not self.takes:
            return False
        self.lines.append(json.loads(json.dumps(fields)))
        return True

    def start(self, tracked=True, before=None):
        self.windows = shell.Windows(clock=self.clock) if tracked else None
        if before is not None:
            before()
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, launcher=self.launcher(),
                                    windows=self.windows, activate=self.activate if tracked else None,
                                    minimize=self.minimized.append if tracked else None, clock=self.clock,
                                    executable=lambda path: True, status=self.status)
        self.addCleanup(self.helper_.watcher.stop)
        return self.helper_

    def window(self, handle, app_id, activated=False, changed=True, **state):
        self.windows.new(handle)
        self.windows.app_id(handle, app_id)
        self.windows.state(handle, activated, **state)
        self.windows.done(handle)
        if changed:
            self.helper_.windows_changed()

    def reports(self):
        return [(line['count'], line['names']) for line in self.lines if line['event'] == 'windows']


class WindowsReportTest(WindowsBase):
    def test_it_says_the_count_once_at_start_and_at_each_change(self):
        helper = self.start()
        self.assertEqual(self.lines, [{'event': 'windows', 'count': 0, 'names': []}])
        self.window(MAIL, 'org.kde.kwrite')
        name = helper.apps[self.windows.toplevels[MAIL].owner].name
        self.assertEqual(self.reports()[1:], [(1, [name])])  # the program's name, as the supervisor's message says it
        # Coalesced as apps_running is: news that changes nothing writes nothing.
        self.windows.state(MAIL, True, maximized=True)
        self.windows.done(MAIL)
        helper.windows_changed()
        helper.tick()
        self.assertEqual(len(self.reports()), 2)
        # A window nobody owns is an app window too (Prism's own, a program outside the registry): by its app_id.
        self.window(OTHER, 'org.prismlauncher.PrismLauncher')
        self.assertEqual(self.reports()[-1], (2, sorted([name, 'org.prismlauncher.PrismLauncher'])))
        self.windows.gone(MAIL)
        self.windows.gone(OTHER)
        helper.windows_changed()
        self.assertEqual(self.reports()[-1], (0, []))
        self.assertEqual(len(self.reports()), 4)

    def test_every_window_counts_but_the_desktops_the_covers_and_the_message_window(self):
        self.start()
        for handle, app_id in ((DESKTOP, 'aresos-desktop'), (10, 'aresos.cover'), (11, 'aresos.black'),
                               (12, 'aresos.desktop')):
            self.window(handle, app_id)
        self.assertEqual(self.reports(), [(0, [])])
        # Minimized ones included, and the recovery terminal as any other window.
        self.window(MAIL, 'org.kde.kwrite', minimized=True)
        self.window(OTHER, 'foot')
        self.assertEqual(self.reports()[-1][0], 2)
        self.assertEqual(len(self.windows.app_windows()), 2)

    def test_a_window_counts_only_once_the_compositor_has_said_what_it_is(self):
        helper = self.start()
        # The black screen's window before its app_id is known must not count: that would take it down again.
        self.windows.new(BLACK)
        helper.windows_changed()
        self.windows.app_id(BLACK, 'aresos.black')
        helper.windows_changed()
        self.windows.state(BLACK, True, fullscreen=True)
        self.windows.done(BLACK)
        helper.windows_changed()
        self.assertEqual(self.reports(), [(0, [])])
        self.windows.new(MAIL)
        self.windows.app_id(MAIL, 'org.kde.kwrite')
        helper.windows_changed()
        self.assertEqual(self.reports(), [(0, [])])
        self.windows.done(MAIL)
        helper.windows_changed()
        self.assertEqual(self.reports()[-1][0], 1)

    def test_windows_that_were_there_before_the_helper_are_in_its_first_report(self):
        def before():
            for handle, app_id in ((DESKTOP, 'aresos-desktop'), (MAIL, 'org.kde.kwrite')):
                self.windows.new(handle)
                self.windows.app_id(handle, app_id)
                self.windows.done(handle)
        self.start(before=before)
        self.assertEqual([count for count, _ in self.reports()], [1])

    def test_without_window_tracking_the_count_is_not_known(self):
        helper = self.start(tracked=False)
        self.assertEqual(self.lines, [{'event': 'windows', 'count': None, 'names': []}])
        helper.tick()
        self.assertEqual(len(self.lines), 1)

    def test_a_line_the_full_pipe_dropped_is_written_again(self):
        helper = self.start()
        self.takes = False
        self.window(MAIL, 'org.kde.kwrite')
        self.assertEqual(self.reports(), [(0, [])])
        helper.tick()
        self.assertEqual(self.reports(), [(0, [])])
        self.takes = True
        helper.tick()  # no compositor news is needed for it
        self.assertEqual(self.reports()[-1][0], 1)
        helper.tick()
        self.assertEqual(len(self.reports()), 2)

    def test_the_real_pipe_says_when_it_dropped_a_line(self):
        read, write = os.pipe()
        self.addCleanup(os.close, read)
        pipe = shell.StatusPipe(write)
        self.assertIs(pipe(event='windows', count=0, names=[]), True)
        while pipe(event='windows', count=0, names=[]):  # fill it with lines of the same size
            pass
        self.assertIs(pipe(event='windows', count=1, names=['Mail']), False)  # full: dropped, and it says so
        while select.select([read], [], [], 0)[0]:
            os.read(read, 65536)
        self.assertIs(pipe(event='windows', count=1, names=['Mail']), True)
        os.close(write)
        # A closed pipe switches reporting off: nothing to write again, and the helper never stops for it.
        self.assertIsNot(pipe(event='windows', count=2, names=[]), False)
        self.assertIsNone(pipe.fd)
        self.assertIsNot(pipe(event='windows', count=2, names=[]), False)

    def test_names_are_short_printable_and_few_so_the_line_arrives_whole(self):
        self.start()
        for handle in range(100, 164):
            self.window(handle, f'\x1b[31m{handle}-' + 'ü' * 200 + '\n', changed=False)
        self.helper_.windows_changed()
        count, names = self.reports()[-1]
        self.assertEqual((count, len(names)), (64, shell.WINDOW_NAMES))
        for name in names:
            self.assertLessEqual(len(name), shell.WINDOW_NAME_CHARS)
            self.assertTrue(name.isprintable() and name.startswith('[31m1'), name)
        # The pipe carries JSON with every non-ASCII character escaped: still far below PIPE_BUF.
        line = json.dumps(dict(event='windows', count=count, names=names), sort_keys=True) + '\n'
        self.assertLess(len(line.encode()), select.PIPE_BUF // 2)

    def test_the_supervisor_reads_what_the_helper_writes(self):
        desktop = load('aresos_desktop_for_shell', CONFIG / 'usr/libexec/aresos-desktop')
        self.addCleanup(sys.modules.pop, 'aresos_desktop_for_shell', None)
        hidden = []
        supervisor = types.SimpleNamespace(windows=None, hide_black=hidden.append)
        self.start()
        desktop.Supervisor.on_windows(supervisor, self.lines[-1])
        self.assertEqual((supervisor.windows, hidden), ([], []))
        self.window(MAIL, 'org.kde.kwrite')
        self.window(OTHER, 'foot')
        desktop.Supervisor.on_windows(supervisor, self.lines[-1])
        self.assertEqual(sorted(supervisor.windows), sorted(self.reports()[-1][1]))
        self.assertEqual(len(hidden), 1)  # an app window is open now: a black screen would end
        self.helper_.windows = None  # tracking is lost
        self.helper_.report_windows()
        desktop.Supervisor.on_windows(supervisor, self.lines[-1])
        self.assertIsNone(supervisor.windows)

    def test_the_names_the_three_programs_share(self):
        desktop = load('aresos_desktop_for_shell', CONFIG / 'usr/libexec/aresos-desktop')
        self.addCleanup(sys.modules.pop, 'aresos_desktop_for_shell', None)
        cover = load('aresos_cover_for_shell', CONFIG / 'usr/libexec/aresos-cover')
        self.addCleanup(sys.modules.pop, 'aresos_cover_for_shell', None)
        self.assertEqual(shell.COVER_APP_IDS, {cover.APP_ID, cover.BLACK_APP_ID})
        self.assertIn(f'--app-id={shell.MESSAGE_WINDOW_APP_ID}', desktop.VIEW_COMMAND)
        rules = {rule.get('identifier') for rule in
                 ET.parse(CONFIG / 'usr/share/aresos/labwc/rc.xml').getroot().iter('windowRule')}
        self.assertLessEqual(shell.COVER_APP_IDS | shell.DESKTOP_APP_IDS, rules)
        # The supervisor's gate for the game never reaches an app the helper starts.
        self.assertIn(desktop.LIFECYCLE_GATE, shell.PRIVATE_ENVIRONMENT)
        self.assertEqual((desktop.COVER, desktop.LID_BLOCK), ('/usr/libexec/aresos-cover', 'handle-lid-switch:sleep'))


class BlackScreenTest(WindowsBase):
    def test_the_black_screen_is_never_an_app_never_covers_the_world_and_is_never_minimized(self):
        helper = self.start()
        self.window(DESKTOP, 'aresos-desktop', True, maximized=True)
        # The black screen maps fullscreen and on top and takes the focus, as the startup cover does.
        self.windows.state(DESKTOP, False, maximized=True)
        self.windows.done(DESKTOP)
        self.window(BLACK, 'aresos.black', True, fullscreen=True)
        self.assertEqual((self.windows.app_windows(), self.windows.covering()), ([], []))
        self.assertIsNone(self.windows.toplevels[BLACK].owner)
        # The stop is called off: the black screen goes, and the world gets the focus back.
        self.windows.gone(BLACK)
        self.windows.state(DESKTOP, True, maximized=True)
        self.windows.done(DESKTOP)
        helper.windows_changed()
        # While it is up and the world is activated under it, nothing is minimized either.
        self.window(BLACK, 'aresos.black', False, fullscreen=True)
        self.windows.state(DESKTOP, False, maximized=True)
        self.windows.done(DESKTOP)
        self.windows.state(BLACK, True, fullscreen=True)
        self.windows.done(BLACK)
        helper.windows_changed()
        self.windows.state(BLACK, False, fullscreen=True)
        self.windows.done(BLACK)
        self.windows.state(DESKTOP, True, maximized=True)
        self.windows.done(DESKTOP)
        helper.windows_changed()
        self.assertEqual((self.minimized, self.reports()), ([], [(0, [])]))


if __name__ == '__main__':
    import unittest
    unittest.main()
