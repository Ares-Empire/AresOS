"""The AresOS startup cover on its own (package 23b, /usr/libexec/aresos-cover).

What needs a display runs in a headless labwc of its own (WLR_BACKENDS=headless, its own XDG_RUNTIME_DIR, the
image's rc.xml), never on the session the tests run in; those tests are skipped where labwc, grim or GTK 4 are
missing (the hosted runner). The rest needs nothing but Python.

The black screen (package 25, `--black`) runs in the same kind of private compositor, with two headless outputs. The
helper's own window reader (aresos-shell's ForeignToplevels) is connected to that compositor in this process, by an
absolute socket path, so the test sees the black windows as the helper will: one on every output, and never an app.
"""
import importlib.machinery
import math
import os
import pathlib
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
COVER = ROOT / 'os/config/usr/libexec/aresos-cover'
RC_XML = ROOT / 'os/config/usr/share/aresos/labwc/rc.xml'
SHELL = ROOT / 'os/config/usr/libexec/aresos-shell'


def load(name='aresos_cover', path=COVER):
    loader = importlib.machinery.SourceFileLoader(name, str(path))
    module = types.ModuleType(loader.name)
    sys.modules[loader.name] = module  # the helper's dataclasses look their module up
    loader.exec_module(module)
    return module


cover = load()


def gtk4():
    try:
        cover.load_gtk()
        return True
    except (ImportError, ValueError):
        return False


HAS_GTK = sys.platform.startswith('linux') and gtk4()
HEADLESS = HAS_GTK and all(shutil.which(name, path='/usr/bin') for name in ('labwc', 'grim'))
FOOT = shutil.which('foot', path='/usr/bin')


def colour(hex_colour):
    return tuple(int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))


def close(pixel, expected, slack=3):
    return all(abs(a - b) <= slack for a, b in zip(pixel, expected))


class ProgramTest(unittest.TestCase):
    def test_again_changes_only_the_line(self):
        self.assertFalse(cover.parse([]).again)
        self.assertTrue(cover.parse(['--again']).again)
        self.assertEqual(cover.line(False), 'Starting your home screen…')
        self.assertEqual(cover.line(True), 'Starting again…')
        with self.assertRaises(SystemExit):
            cover.parse(['--other'])

    def test_the_limit_is_ten_minutes_and_only_shorter_under_test(self):
        self.assertEqual(cover.LIMIT, 600.0)
        self.assertEqual(cover.parse([]).limit, 600.0)
        self.assertEqual(cover.parse(['--limit', '0.5']).limit, 0.5)
        for value in ('0', '-1', '601', 'nan', 'inf'):
            self.assertEqual(cover.parse(['--limit', value]).limit, 600.0, value)

    def test_look(self):
        self.assertEqual((cover.APP_ID, cover.TITLE), ('aresos.cover', 'AresOS'))
        # Darker at the bottom: the lighter of linux-hub's two colours is on top.
        self.assertEqual((cover.TOP, cover.BOTTOM), ('#1a191e', '#0d0d10'))
        self.assertGreater(sum(colour(cover.TOP)), sum(colour(cover.BOTTOM)))
        self.assertEqual((cover.INK, cover.MUTED), ('#f3f1ea', '#a6a39a'))
        self.assertEqual(cover.rgb('#ff8000'), (1.0, 128 / 255, 0.0))
        # Space Grotesk first, and a generic family Pango falls back to when it is missing.
        self.assertEqual(cover.FAMILY.split(','), ['Space Grotesk', 'sans-serif'])
        self.assertEqual(cover.sizes(720), (60.0, 30.0))
        self.assertEqual(cover.sizes(1080), (90.0, 45.0))
        self.assertTrue(all(math.isfinite(size) and size > 0 for size in cover.sizes(0)))

    def test_the_file_loads_without_gtk(self):
        # The supervisor's tests and the image checks load it as a module: nothing graphical happens on import.
        code = ('import importlib.machinery, sys, types\n'
                f'loader = importlib.machinery.SourceFileLoader("c", {str(COVER)!r})\n'
                'loader.exec_module(types.ModuleType("c"))\n'
                'print("gi" in sys.modules)\n')
        result = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.stdout.strip(), 'False', result.stderr)

    def test_a_script_for_python_with_absolute_paths_only(self):
        text = COVER.read_text()
        self.assertTrue(text.startswith('#!/usr/bin/python3\n'))
        self.assertTrue(os.access(COVER, os.X_OK))
        self.assertNotIn('subprocess', text)
        self.assertIn("window.connect('close-request', lambda _window: True)", text)
        self.assertNotIn('window.fullscreen()', text)

    def test_black_is_a_face_of_its_own_with_its_own_window_rule(self):
        import xml.etree.ElementTree as ET
        self.assertFalse(cover.parse([]).black)
        self.assertTrue(cover.parse(['--black']).black)
        self.assertEqual(cover.parse(['--black', '--limit', '90']).limit, 90.0)
        self.assertEqual(cover.BLACK_APP_ID, 'aresos.black')
        root = ET.parse(RC_XML).getroot()
        rules = [rule for rule in root.iter('windowRule') if rule.get('identifier') == 'aresos.black']
        self.assertEqual(len(rules), 1)
        self.assertEqual(rules[0].get('serverDecoration'), 'no')
        # On top, and no ToggleFullscreen: each black window asks for its own output itself (brief 3.4).
        self.assertEqual([action.get('name') for action in rules[0]], ['ToggleAlwaysOnTop'])
        self.assertIn('window.fullscreen_on_monitor(monitor)', COVER.read_text())
        # The startup cover's rule stays byte for byte as the image checks grep it.
        self.assertIn('<windowRule identifier="aresos.cover" serverDecoration="no"><action name="ToggleFullscreen" />'
                      '<action name="ToggleAlwaysOnTop" /></windowRule>\n', RC_XML.read_text())


@unittest.skipUnless(HAS_GTK, 'GTK 4 through gi')
class NoDisplayTest(unittest.TestCase):
    def test_without_a_display_it_ends_at_once(self):
        with tempfile.TemporaryDirectory() as runtime:
            os.chmod(runtime, 0o700)
            env = {'HOME': runtime, 'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': runtime}
            result = subprocess.run([str(COVER)], env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                    text=True, timeout=30)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertIn('no display', result.stderr)


class Headless(unittest.TestCase):
    """A headless labwc of its own under the image's rc.xml, with OUTPUTS screens."""
    OUTPUTS = 1

    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = pathlib.Path(folder.name)
        runtime, config = self.root / 'run', self.root / 'config'
        runtime.mkdir(mode=0o700)
        config.mkdir()
        # Only rc.xml: no autostart, so nothing but what a test starts runs in this compositor.
        shutil.copy(RC_XML, config / 'rc.xml')
        # Never the session these tests run in: a clean environment and the headless backend.
        self.env = {'HOME': str(self.root), 'PATH': '/usr/bin:/bin', 'XDG_RUNTIME_DIR': str(runtime)}
        self.labwc = subprocess.Popen(['/usr/bin/labwc', '-C', str(config)],
                                      env=dict(self.env, WLR_BACKENDS='headless', WLR_RENDERER='pixman',
                                               WLR_LIBINPUT_NO_DEVICES='1',
                                               WLR_HEADLESS_OUTPUTS=str(self.OUTPUTS)),
                                      stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                      stderr=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(self.end, self.labwc)
        deadline = time.monotonic() + 15
        while not (runtime / 'wayland-0').exists():
            if self.labwc.poll() is not None or time.monotonic() > deadline:
                self.skipTest('the headless labwc did not start here')
            time.sleep(0.05)
        self.env.update(WAYLAND_DISPLAY='wayland-0', GDK_BACKEND='wayland')

    def end(self, process):
        if process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(10)

    def start(self, *args):
        process = subprocess.Popen([str(COVER), *args], env=self.env, stdin=subprocess.DEVNULL,
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.addCleanup(self.end, process)
        return process

    def screenshot(self, name):
        path = self.root / f'{name}.ppm'
        subprocess.run(['/usr/bin/grim', '-t', 'ppm', str(path)], env=self.env, check=True, timeout=30,
                       stdin=subprocess.DEVNULL, capture_output=True)
        return Picture(path)


@unittest.skipUnless(HEADLESS, 'a headless labwc, grim and GTK 4 (AresOS; not the hosted runner)')
class HeadlessLabwcTest(Headless):
    """The real cover under the image's rc.xml in a headless labwc of its own."""

    def covered(self, name):
        """The screen once the cover is up: both corners carry its gradient (fullscreen, nothing above)."""
        deadline = time.monotonic() + 20
        while True:
            picture = self.screenshot(name)
            if (close(picture.pixel(0, 0), colour(cover.TOP))
                    and close(picture.pixel(picture.width - 1, picture.height - 1), colour(cover.BOTTOM))):
                return picture
            if time.monotonic() > deadline:
                self.fail(f'no cover on the screen: corners {picture.pixel(0, 0)} '
                          f'{picture.pixel(picture.width - 1, picture.height - 1)}')
            time.sleep(0.2)

    def test_fullscreen_on_top_borderless_and_sigterm_ends_it(self):
        process = self.start()
        picture = self.covered('cover')
        width, height = picture.width, picture.height
        for x, y, expected in ((0, 0, cover.TOP), (width - 1, 0, cover.TOP), (0, height - 1, cover.BOTTOM),
                               (width - 1, height - 1, cover.BOTTOM)):
            self.assertTrue(close(picture.pixel(x, y), colour(expected)), (x, y, picture.pixel(x, y)))
        # The word in the middle, in its ink colour; the line under it, in the muted one.
        title_size, line_size = cover.sizes(height)
        middle = picture.row(height // 2)
        self.assertTrue(any(close(pixel, colour(cover.INK), 6) for pixel in middle))
        below = [pixel for y in range(int(height / 2 + title_size / 2), int(height / 2 + title_size + 2 * line_size))
                 for pixel in picture.row(y)]
        self.assertTrue(any(close(pixel, colour(cover.MUTED), 6) for pixel in below))
        self.assertFalse(any(close(pixel, colour(cover.INK), 6) for pixel in below))
        if shutil.which('foot', path='/usr/bin'):
            # A window that opens later (Minecraft, Prism) stays below it.
            foot = subprocess.Popen(['/usr/bin/foot', '-o', 'colors.background=ff0000', 'sleep', '30'], env=self.env,
                                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    start_new_session=True)
            self.addCleanup(self.end, foot)
            time.sleep(2)
            self.assertIsNone(foot.poll())
            self.covered('cover-with-foot')
        started = time.monotonic()
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(5), 0)
        self.assertLess(time.monotonic() - started, 2.0)
        after = self.screenshot('after')
        self.assertFalse(close(after.pixel(0, 0), colour(cover.TOP)) and close(
            after.pixel(width - 1, height - 1), colour(cover.BOTTOM)), 'the cover is still on the screen')

    def test_again_draws_its_own_line_under_the_same_word(self):
        first = self.start()
        one = self.covered('first')
        first.send_signal(signal.SIGTERM)
        self.assertEqual(first.wait(5), 0)
        self.start('--again')
        time.sleep(0.5)
        two = self.covered('again')
        title_size, line_size = cover.sizes(one.height)
        title_rows = range(int(one.height / 2 - title_size / 2), int(one.height / 2 + title_size / 2))
        line_rows = range(int(one.height / 2 + title_size / 2), int(one.height / 2 + title_size + 2 * line_size))
        self.assertEqual([one.row(y) for y in title_rows], [two.row(y) for y in title_rows])
        self.assertNotEqual([one.row(y) for y in line_rows], [two.row(y) for y in line_rows])

    def test_it_ends_by_itself_after_its_limit(self):
        process = self.start('--limit', '1.5')
        self.covered('limited')
        self.assertEqual(process.wait(15), 0)


@unittest.skipUnless(HEADLESS and FOOT, 'a headless labwc, grim, foot and GTK 4 (AresOS; not the hosted runner)')
class BlackTest(Headless):
    """`--black` (package 25, brief 3.4) on two screens, read through the helper's own window reader."""
    OUTPUTS = 2

    def setUp(self):
        super().setUp()
        self.shell = load('aresos_shell_for_cover', SHELL)
        self.addCleanup(sys.modules.pop, 'aresos_shell_for_cover', None)
        self.windows = self.shell.Windows()
        # In this process, and only ever on the private compositor: its socket by absolute path.
        self.client = self.shell.ForeignToplevels.connect(
            self.windows, {'WAYLAND_DISPLAY': str(self.root / 'run' / 'wayland-0')})
        self.addCleanup(self.client.sock.close)

    def seen(self, condition, what, timeout=20):
        deadline = time.monotonic() + timeout
        while True:
            self.client.readable()
            if condition():
                return
            if time.monotonic() > deadline:
                self.fail(f'{what}: the compositor shows '
                          f'{[(t.app_id, t.fullscreen, sorted(t.outputs)) for t in self.windows.toplevels.values()]}')
            time.sleep(0.05)

    def blacks(self):
        return [t for t in self.windows.toplevels.values() if t.ready and t.app_id == cover.BLACK_APP_ID]

    def apps(self):
        return sorted(t.app_id for t in self.windows.app_windows())

    def foot(self):
        process = subprocess.Popen([FOOT, '-o', 'colors.background=ff0000', 'sleep', '60'], env=self.env,
                                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                   start_new_session=True)
        self.addCleanup(self.end, process)
        return process

    def black(self, name, timeout=20):
        """Whether every pixel of every screen is black, once the picture has had time to settle."""
        deadline = time.monotonic() + timeout
        while True:
            picture = self.screenshot(name)
            if picture.data.count(b'\0') == len(picture.data):
                return picture
            if time.monotonic() > deadline:
                return None
            time.sleep(0.2)

    def test_plain_black_on_every_screen_never_an_app_and_sigterm_ends_it(self):
        self.foot()
        self.seen(lambda: self.apps() == ['foot'], 'an app window before the black screen')
        before = self.screenshot('before')
        self.assertNotEqual(before.data.count(b'\0'), len(before.data))  # there is something to hide
        process = self.start('--black')
        # One window on every screen, each fullscreen on a screen of its own.
        self.seen(lambda: len(self.blacks()) == 2 and all(t.fullscreen and len(t.outputs) == 1 for t in self.blacks())
                  and len(frozenset().union(*(t.outputs for t in self.blacks()))) == 2, 'a black window per screen')
        picture = self.black('black')
        self.assertIsNotNone(picture, 'the screens are not black')
        self.assertGreater(picture.width, before.width // 2)  # the picture holds both screens
        # The helper never counts it as an app window: counting it would take the black screen down again.
        self.assertEqual(self.apps(), ['foot'])
        # A window that opens later stays below it, and is counted.
        self.foot()
        self.seen(lambda: self.apps() == ['foot', 'foot'], 'the second app window')
        time.sleep(1)
        self.assertIsNotNone(self.black('black-with-foot', timeout=0), 'a later window shows above the black screen')
        started = time.monotonic()
        process.send_signal(signal.SIGTERM)
        self.assertEqual(process.wait(5), 0)
        self.assertLess(time.monotonic() - started, 2.0)
        self.seen(lambda: not self.blacks(), 'the black windows are gone')
        self.assertIsNone(self.black('after', timeout=1), 'the screens are still black')

    def test_it_ends_by_itself_after_its_limit(self):
        process = self.start('--black', '--limit', '1.5')
        self.seen(lambda: len(self.blacks()) == 2, 'a black window per screen')
        self.assertEqual(process.wait(15), 0)


class Picture:
    """A binary PPM (P6) as grim writes it; enough to read pixels without an imaging library."""

    def __init__(self, path):
        data = pathlib.Path(path).read_bytes()
        fields, offset = [], 0
        while len(fields) < 4:
            while data[offset:offset + 1].isspace():
                offset += 1
            if data[offset:offset + 1] == b'#':
                offset = data.index(b'\n', offset) + 1
                continue
            end = offset
            while not data[end:end + 1].isspace():
                end += 1
            fields.append(data[offset:end])
            offset = end
        assert fields[0] == b'P6' and fields[3] == b'255', fields
        self.width, self.height = int(fields[1]), int(fields[2])
        self.data = data[offset + 1:]

    def pixel(self, x, y):
        start = (y * self.width + x) * 3
        return tuple(self.data[start:start + 3])

    def row(self, y):
        start = y * self.width * 3
        line = self.data[start:start + self.width * 3]
        return [tuple(line[i:i + 3]) for i in range(0, len(line), 3)]


if __name__ == '__main__':
    unittest.main()
