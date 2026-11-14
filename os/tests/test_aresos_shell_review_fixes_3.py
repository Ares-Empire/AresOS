"""Package 30, review fixes 3, step A: a picture pass only when something changed, and one warning when no picture can
be made.

Everything is synthetic: icon folders, desktop entries and the converter's answer (`run` gives a normalized PNG) are
the test's own. The worker's steps run on the test's thread, so a test can count the passes the helper's ticks cause.
"""
import os
import sys
from unittest import mock

from test_aresos_shell import shell, Base, REGISTRY, INSTANCE, NONCE
from test_aresos_shell_icons import IconBase, PNG, NORMAL


def later(path):
    """Moves path's times a second on, as when a file changes some time after the last look (a coarse clock could
    otherwise give a change made within the same tick the old time)."""
    info = os.stat(path)
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 1_000_000_000))


class PicturePassTest(IconBase, Base):
    """Point 1 (OS lead, defect 1): the helper asks every CATALOGUE_CHECK seconds; a pass runs only when the catalogue,
    the icon folders or a chosen picture changed, or when the last pass did not finish."""

    def setUp(self):
        IconBase.setUp(self)
        Base.setUp(self)
        self.entries = self.root / 'applications'
        self.entries.mkdir()
        self.desktop('one', 'app-one')
        self.desktop('two', 'app-two')
        # One picture in /usr/share/icons' stand-in, the other program has none yet.
        self.picture = self.themed(4, size='48x48', name='app-one.png')
        self.index(4, theme='breeze')
        self.convert = mock.patch.object(self.cache, 'run', return_value=NORMAL)
        self.convert.start()
        self.addCleanup(self.convert.stop)
        # The test runs the worker's steps itself.
        self.cache.thread = mock.Mock()
        catalogue = shell.Catalogue(str(REGISTRY), entry_dirs=[self.entries], executable=lambda path: True,
                                    deployments=())
        catalogue.refresh(self.clock())
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal,
                                    registry=(catalogue.apps, catalogue.revision), catalogue=catalogue,
                                    icons=self.cache, clock=self.clock, executable=lambda path: True,
                                    launcher=self.launcher())
        self.addCleanup(self.helper_.watcher.stop)

    def desktop(self, name, icon):
        path = self.entries / f'{name}.desktop'
        path.write_text(f'[Desktop Entry]\nType=Application\nName={name.title()}\nExec=/usr/bin/tool\nIcon={icon}\n')
        later(self.entries)
        return path

    def ticks(self, count):
        """count ticks CATALOGUE_CHECK seconds apart, each request handled by the worker right after its tick; whether
        each request ran a pass."""
        passes = []
        for _ in range(count):
            self.now[0] += shell.CATALOGUE_CHECK
            self.helper_.tick()
            while not self.cache.pending.empty():
                passes.append(self.cache.step(*self.cache.pending.get_nowait()))
        return passes

    def icon(self, app_id):
        return self.helper_.apps[app_id].icon

    def test_an_idle_minute_of_ticks_asks_for_no_pass_after_the_first(self):
        self.assertEqual(self.ticks(20), [True] + [False] * 19)
        self.assertTrue(os.path.isfile(self.icon('one')))
        self.assertIsNone(self.icon('two'))

    def test_a_new_picture_file_asks_for_exactly_one_pass(self):
        self.ticks(2)
        self.assertIsNone(self.icon('two'))
        later(self.themed(4, size='48x48', name='app-two.png').parent)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('two')))

    def test_a_new_picture_in_breezes_own_layout_asks_for_exactly_one_pass(self):
        self.ticks(2)
        later(self.breeze('apps/32', 'app-two.png', PNG).parent)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('two')))

    def test_a_replaced_picture_file_asks_for_exactly_one_pass(self):
        self.ticks(2)
        first = self.icon('one')
        # Rewritten in place: its folder does not change, only the file the last pass chose.
        self.picture.write_bytes(PNG + b'\0')
        later(self.picture)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('one')))
        self.assertNotEqual(self.icon('one'), first)

    def test_a_cleared_picture_cache_asks_for_exactly_one_pass(self):
        self.ticks(2)
        made = self.icon('one')
        os.unlink(made)
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertEqual(self.icon('one'), made)
        self.assertTrue(os.path.isfile(made))

    def test_a_changed_catalogue_asks_for_exactly_one_pass(self):
        self.ticks(2)
        self.desktop('three', 'app-one')
        self.assertEqual(self.ticks(10), [True] + [False] * 9)
        self.assertTrue(os.path.isfile(self.icon('three')))

    def test_a_pass_that_was_cut_short_is_asked_for_again(self):
        self.now[0] += shell.CATALOGUE_CHECK
        self.helper_.tick()
        # The event loop has not taken earlier answers yet: the pass stops at its first picture.
        for _ in range(shell.MAX_APPS * 2):
            self.cache.results.put_nowait(('old', 'one', 'app-one', None))
        self.assertTrue(self.cache.step(*self.cache.pending.get_nowait()))
        self.assertIsNone(self.cache.finished)
        self.assertEqual(self.ticks(5), [True] + [False] * 4)
        self.assertTrue(os.path.isfile(self.icon('one')))


class SupersedeTest(IconBase):
    """Point 1: the helper's next request for the same catalogue never cuts a running pass short; a changed one does."""

    def test_only_a_changed_catalogue_cuts_a_running_pass_short(self):
        self.cache.thread = mock.Mock()
        apps = {key: shell.App(key, key.title(), icon_name='/' + key) for key in ('one', 'two')}

        def convert(source, revision):
            self.cache.request(apps, revision)
            return '/cache' + source

        for revision, complete in (('base', True), ('newer', False)):
            with self.subTest(revision=revision), \
                    mock.patch.object(self.cache, 'convert', side_effect=lambda source: convert(source, revision)):
                self.cache.finished = None
                self.cache.request(apps, 'base')
                self.assertTrue(self.cache.step(*self.cache.pending.get_nowait()))
                self.assertEqual(self.cache.finished is not None, complete)
                # The request made during the pass: nothing changed for the same catalogue, a pass for a new one.
                self.assertEqual(self.cache.step(*self.cache.pending.get_nowait()), not complete)


class MissingToolsTest(IconBase):
    """Point 3 (OS lead): without bwrap, magick or prlimit no picture can be made; one WARNING at start says so."""

    def test_one_warning_at_start_names_what_is_missing_and_no_more_per_picture(self):
        missing = str(self.root / 'missing')
        for tools, named in ((dict(bwrap=missing + '/bwrap'), ['bwrap']),
                             (dict(magick=missing + '/magick', prlimit=missing + '/prlimit'), ['magick', 'prlimit'])):
            with self.subTest(named=named), mock.patch.object(shell.LOG, 'disabled', False), \
                    self.assertLogs(shell.LOG, 'DEBUG') as logs:
                present = dict(bwrap=sys.executable, magick=sys.executable, prlimit=sys.executable)
                cache = shell.IconCache(environ={'HOME': str(self.root), 'XDG_CACHE_HOME': str(self.root / 'cache')},
                                        directories=self.folders, **dict(present, **tools))
                self.addCleanup(cache.stop)
                cache.thread = mock.Mock()
                sources = [self.write(self.root / f'{n}.png', PNG + bytes([n])) for n in range(3)]
                cache.request({str(n): shell.App(str(n), 'P', icon_name=str(path)) for n, path in enumerate(sources)},
                              'base')
                cache.step(*cache.pending.get_nowait())
            warnings = [record.getMessage() for record in logs.records if record.levelname == 'WARNING']
            self.assertEqual(len(warnings), 1, warnings)
            for name in named:
                self.assertIn(f'{missing}/{name}', warnings[0])
            self.assertIn('programs show without pictures', warnings[0])
            # Each picture still fails on its own, quietly.
            self.assertEqual(len([r for r in logs.records if r.levelname == 'DEBUG']), 3)

    def test_no_warning_when_every_tool_is_there(self):
        with mock.patch.object(shell.LOG, 'disabled', False), mock.patch.object(shell.LOG, 'warning') as warning:
            cache = shell.IconCache(environ={'HOME': str(self.root)}, directories=self.folders,
                                    bwrap=sys.executable, magick=sys.executable, prlimit=sys.executable)
            self.addCleanup(cache.stop)
        warning.assert_not_called()


from test_aresos_shell_windows import DiscoveredBase  # noqa: E402  (after the Base-only classes above)


class FlatpakScopeTest(DiscoveredBase):
    """Step B (OS lead): `flatpak run` moves itself into its own app-flatpak-... scope, so the scope the helper made
    is gone before the first scope check. The launch rests on the live process and the window's identity; the laptop's
    headless check starts KCalc's real Flatpak entry the same way (check_aresos_shell_headless.py, third case)."""

    def setUp(self):
        super().setUp()
        # KCalc's exported entry as Flatpak writes it: no StartupWMClass, the app ID in X-Flatpak and in its command.
        entry = {'Type': 'Application', 'Name': 'KCalc', 'X-Flatpak': 'org.kde.kcalc',
                 'Exec': '/usr/bin/flatpak run --branch=stable --arch=x86_64 --command=kcalc org.kde.kcalc'}
        flatpak = shell.discovered_app('org.kde.kcalc.desktop', '/test/org.kde.kcalc.desktop', entry, lambda p: True)
        self.assertEqual((flatpak.id, flatpak.app_ids), ('org-kde-kcalc', ('org.kde.kcalc',)))
        apps, revision = shell.load_registry(REGISTRY)
        apps[flatpak.id] = flatpak
        self.windows = shell.Windows(clock=self.clock)
        self.helper_ = shell.Helper(str(REGISTRY), INSTANCE, NONCE, self.journal, registry=(apps, revision),
                                    launcher=self.launcher(), windows=self.windows, activate=self.activate,
                                    clock=self.clock, executable=lambda path: True)
        self.addCleanup(self.helper_.watcher.stop)
        self.conn = self.connect(self.helper_)
        self.window(1, 'aresos-desktop', active=True)

    def passes(self, seconds):
        """The scope checks of that many seconds; the helper's scope is never listed (active_units stays empty)."""
        for _ in range(int(seconds / shell.SCOPE_CHECK)):
            self.now[0] += shell.SCOPE_CHECK
            self.scope_pass(self.helper_)

    def test_the_launch_lives_on_its_process_and_window_while_its_scope_is_empty(self):
        self.assertTrue(self.open('org-kde-kcalc')['ok'])
        process = self.helper_.processes['o-1']
        self.passes(shell.WINDOW_TIMEOUT / 2)  # flatpak run is still setting up its sandbox
        self.assertEqual(self.state(), 'starting')
        self.window(2, 'org.kde.kcalc', active=True)
        self.assertEqual(self.state(), 'focused')
        self.passes(shell.WINDOW_TIMEOUT * 4)  # an empty scope neither closes nor fails it
        self.assertEqual((self.state(), self.activations, self.helper_.shell), ('focused', [], 'background'))
        self.close(2)
        self.expire_close()
        self.assertEqual((self.state(), self.activations), ('closed', [1]))
        self.assertEqual(self.conn.events('shell_focus')[-1]['reason'], 'app_closed')
        process.code = 0  # flatpak run ends with its program
        self.passes(shell.SCOPE_CHECK)
        self.assertEqual((self.helper_.processes, self.helper_.discovered_scopes, self.state()), ({}, {}, 'closed'))
        self.assertEqual([e['state'] for e in self.conn.events('app_state')], ['focused', 'closed'])

    def test_without_a_window_it_waits_for_the_process_then_fails_once(self):
        self.assertTrue(self.open('org-kde-kcalc')['ok'])
        self.passes(shell.WINDOW_TIMEOUT * 3)  # the live process keeps the launch waiting past the window wait
        self.assertEqual(self.state(), 'starting')
        self.helper_.processes['o-1'].code = 0
        self.passes(shell.WINDOW_TIMEOUT * 2)
        self.assertEqual([(e['state'], e.get('error')) for e in self.conn.events('app_state')], [('failed', 'no_window')])
