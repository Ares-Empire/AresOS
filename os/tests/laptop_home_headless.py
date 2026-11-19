"""Run the real laptop-home window inside a disposable labwc, and talk to it through a test-only channel.

The channel exists only in this harness: fixture_main loads the program as a module, hooks its drawing area and
answers requests written as files into the test's private folder. The shipped entry point never creates it.
"""

import ctypes
from contextlib import contextmanager
from datetime import datetime
import importlib.machinery
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import socket
import struct
import subprocess
import sys
import tempfile
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / 'os/config/usr/libexec/aresos-laptop-home'
VENDORS = {
    '__EGL_VENDOR_LIBRARY_FILENAMES': '/usr/share/glvnd/egl_vendor.d/50_mesa.json',
    'VK_DRIVER_FILES': '/usr/share/vulkan/icd.d/intel_icd.x86_64.json',
}
# A painter part the harness can switch off, to show that a paint check catches a wrong painter.
BREAKS = ('background', 'plots', 'idle', 'gold_door', 'frame', 'view_mask', 'fades', 'street_ends')


def load_program(path=PROGRAM):
    loader = importlib.machinery.SourceFileLoader('aresos_laptop_home', str(path))
    module = types.ModuleType(loader.name)
    loader.exec_module(module)
    return module


def wait_for(predicate, duration=12):
    stop = time.monotonic() + duration
    while time.monotonic() < stop:
        if result := predicate():
            return result
        time.sleep(0.025)
    raise AssertionError('timed out waiting for laptop-home test')


def scratch():
    work = ROOT / '.work'
    work.mkdir(exist_ok=True)
    return tempfile.TemporaryDirectory(prefix='lh-', dir=work)


# GitHub's Ubuntu runner has no labwc, no GTK 4 typelibs and maybe no pycairo or bubblewrap: the tests that need them
# skip there. On AresOS everything is present; LAPTOP_HOME_REQUIRE_HEADLESS=1 makes a missing piece fail instead.
REQUIRE = bool(os.environ.get('LAPTOP_HOME_REQUIRE_HEADLESS'))


def needs(available, what):
    """A decorator for a test or test class: run it where available, else skip it (or fail it under REQUIRE)."""
    if available:
        return lambda test: test
    if not REQUIRE:
        return unittest.skip(f'needs {what}')

    def fail(test):
        def missing(case, *_args, **_fields):
            case.fail(f'LAPTOP_HOME_REQUIRE_HEADLESS is set and {what} is missing')

        if isinstance(test, type):
            test.setUp = missing
            return test
        return missing

    return fail


def cairo_available():
    try:
        import cairo  # noqa: F401
    except ImportError:
        return False
    return True


def headless_available():
    try:
        import gi
    except ImportError:
        return False
    try:
        for name, version in (('Gtk', '4.0'), ('Pango', '1.0'), ('PangoCairo', '1.0')):
            gi.require_version(name, version)
    except ValueError:
        return False
    return (cairo_available()
            and all(shutil.which(name, path='/usr/bin') for name in ('labwc', 'dbus-run-session', 'bwrap', 'wlr-randr'))
            and all(Path(path).is_file() for path in VENDORS.values()))


# The headless window tests: labwc, bubblewrap, wlr-randr, the Mesa pins, GTK 4, Pango and pycairo.
needs_headless = needs(headless_available(), 'headless labwc, bwrap, wlr-randr, Mesa pins, GTK 4, Pango and Cairo')


def layer_library():
    """Whether the layer surface can be tested here: the configured extraction, or the installed library."""
    layer_dir = os.environ.get('LAPTOP_HOME_TEST_LAYER_DIR')
    lib_dir = Path(layer_dir) if layer_dir else Path('/usr/lib64')
    return (lib_dir / 'libgtk4-layer-shell.so.0').is_file()


def layer_state(window, layer):
    if layer is None or not layer.is_layer_window(window):
        return None
    return {
        'background': layer.get_layer(window) == layer.Layer.BACKGROUND,
        'on_demand': layer.get_keyboard_mode(window) == layer.KeyboardMode.ON_DEMAND,
        'anchored': all(layer.get_anchor(window, getattr(layer.Edge, edge))
                        for edge in ('TOP', 'BOTTOM', 'LEFT', 'RIGHT')),
        'output': layer.get_monitor(window).get_connector(),
    }


class Headless:
    def __init__(self, path, socket_path, *, look='day', size='1920x1080', font_dir=None, battery=True,
                 program=PROGRAM, prototype=False, broken=None, clock=None, redraw=False, layer=None):
        """layer: True needs the layer surface, False runs the fallback window, None takes what is installed."""
        self.path = path
        self.runtime = path / 'run'
        self.runtime.mkdir(mode=0o700)
        self.state = path / 'state'
        self.home_path = self.state / 'aresos/laptop-home/home.json'
        config = path / 'config'
        config.mkdir()
        (config / 'rc.xml').write_text('<labwc_config/>')
        self.bus = config / 'bus.conf'
        self.bus.write_text("""<busconfig>
          <type>session</type>
          <listen>unix:tmpdir=RUNTIME</listen>
          <policy context="default">
            <allow send_destination="*"/>
            <allow receive_sender="*"/>
            <allow own="*"/>
          </policy>
        </busconfig>""".replace('RUNTIME', str(self.runtime)))
        # Imported here, on the test's side only: the program's process (fixture_main) must not carry the stand-in's
        # modules (hashlib, socketserver; about 2 MiB), or the memory measurement would count them.
        from laptop_home_helper import INSTANCE, TOKEN

        # Keep Wayland, home, data, cache, state and D-Bus private. The program sets its renderer itself.
        self.env = dict(HOME=str(path), PATH='/usr/bin:/bin', XDG_RUNTIME_DIR=str(self.runtime),
                        XDG_STATE_HOME=str(self.state), XDG_CONFIG_HOME=str(config),
                        XDG_DATA_HOME=str(path / '.local/share'), XDG_CACHE_HOME=str(path / '.cache'),
                        TMPDIR=str(self.runtime),
                        WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_LIBINPUT_NO_DEVICES='1',
                        GDK_BACKEND='wayland', GTK_A11Y='none', LIBGL_ALWAYS_SOFTWARE='1',
                        ARESOS_SHELL_SOCKET=str(socket_path), ARESOS_DESKTOP_INSTANCE=INSTANCE, **VENDORS)
        if font_dir is not None:
            fonts = path / '.local/share/fonts'
            fonts.mkdir(parents=True)
            for font in font_dir.glob('*.ttf'):
                shutil.copyfile(font, fonts / font.name)
        if broken is not None and broken not in BREAKS:
            raise ValueError(f'unknown painter part {broken}')
        (path / 'setup.json').write_text(json.dumps(dict(size=size, battery=battery, look=look, broken=broken,
                                                        clock=clock, redraw=redraw, layer=layer,
                                                        program=str(Path(program).resolve()))))
        layer_dir = os.environ.get('LAPTOP_HOME_TEST_LAYER_DIR')
        lib_dir = Path(layer_dir).resolve() if layer_dir else Path('/usr/lib64')
        lib = lib_dir / 'libgtk4-layer-shell.so.0'
        typelib_dir = lib_dir / 'girepository-1.0'
        if layer_dir and not (lib.is_file() and (typelib_dir / 'Gtk4LayerShell-1.0.typelib').is_file()):
            raise FileNotFoundError('the configured layer library and typelib are required')
        if layer and not lib.is_file():
            raise FileNotFoundError('the layer surface needs gtk4-layer-shell or LAPTOP_HOME_TEST_LAYER_DIR')
        self.expect_layer = lib.is_file() and layer is not False
        overrides = [f'GI_TYPELIB_PATH={typelib_dir}'] if layer_dir and self.expect_layer else []
        # The fixture's own paths, bound back after the host's /run is hidden (in case one lies under it).
        self.fixture_paths = [path, *([lib_dir] if layer_dir and self.expect_layer else [])]
        preload = f'LD_PRELOAD={lib if self.expect_layer else "libm.so.6"}'
        if prototype:
            # 53e's bare GTK 4 and Cairo block town, the control for memory measurements.
            runner = Path(__file__).with_name('laptop_home_native.py').resolve()
            self.command = ['env', *overrides, preload, sys.executable, str(runner), str(path)]
        else:
            self.command = ['env', *overrides, preload, f'ARESOS_VIEW_TOKEN={TOKEN}', sys.executable,
                            str(Path(__file__).resolve()), str(path)]
        self.config = config

    def __enter__(self):
        self.log = (self.path / 'log').open('w+')
        # Mesa can inspect a DRM device even in software mode. Hide the host's devices before labwc starts, and
        # keep abstract sockets (labwc's Xwayland, D-Bus) in a network namespace of their own.
        # The host's /run (the owner's Wayland and D-Bus sockets, the system bus) is hidden as well; only this test's
        # own folders come back (REVIEW-1 finding 9).
        isolation = ['/usr/bin/bwrap', '--die-with-parent', '--unshare-net', '--ro-bind', '/', '/', '--dev', '/dev',
                     '--proc', '/proc', '--tmpfs', '/tmp', '--tmpfs', '/run']
        for folder in self.fixture_paths:
            isolation += ['--bind' if folder == self.path else '--ro-bind', str(folder), str(folder)]
        isolation.append('--')
        self.process = subprocess.Popen(
            [*isolation, '/usr/bin/dbus-run-session', f'--config-file={self.bus}', '--',
             '/usr/bin/labwc', '-C', str(self.config), '-S', shlex.join(self.command)],
            env=self.env, stdin=subprocess.DEVNULL, stdout=self.log, stderr=self.log, start_new_session=True)
        return self

    def __exit__(self, exc_type, *_):
        try:
            pid_file = self.path / 'parent.json'
            if pid_file.exists() and self.process.poll() is None:
                try:
                    os.kill(json.loads(pid_file.read_text())['pid'], signal.SIGTERM)
                except ProcessLookupError:
                    pass
            try:
                self.process.wait(5)
            except subprocess.TimeoutExpired:
                os.killpg(self.process.pid, signal.SIGKILL)
                self.process.wait(5)
            if exc_type is not None:
                self.log.seek(0)
                print(self.log.read(), file=sys.stderr)
        finally:
            self.log.close()

    def request(self, op, duration=12, **fields):
        result = self.path / 'reply.json'
        result.unlink(missing_ok=True)
        command = self.path / 'request.tmp'
        command.write_text(json.dumps(dict(op=op, **fields)))
        command.rename(self.path / 'request.json')
        wait_for(result.exists, duration)
        reply = json.loads(result.read_text())
        if 'error' in reply:
            raise AssertionError(reply['error'])
        return reply['value']

    def parent(self):
        path = self.path / 'parent.json'
        wait_for(path.exists)
        return json.loads(path.read_text())

    def model(self):
        return self.request('model')

    def until(self, predicate, duration=12):
        def ready():
            scene = self.model()
            return scene if predicate(scene) else None

        return wait_for(ready, duration)

    def picture(self, **state):
        """The painter's 1920 x 1080 picture, rendered inside the program; state is injected first."""
        return self.path / self.request('picture', state=state)

    def key(self, *keys):
        return [self.request('key', key=key) for key in keys]

    def type(self, text):
        return self.key(*text)

    def click(self, x, y):
        return self.request('click', x=x, y=y)

    @contextmanager
    def virtual_input(self, layout='de'):
        """labwc's virtual pointer and keyboard on this test's display. The keyboard carries an xkb keymap for the
        layout, so text goes through the program's input method as a real keyboard's would."""
        from test_aresos_shell import shell

        # Bind only to the display started in this test's private runtime directory.
        display = self.runtime / Path(self.parent()['display']).name
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect(str(display))
            client = shell.ForeignToplevels(sock, None)
            client.roundtrip()

            def bind(interface):
                name = next(n for n, (kind, _) in client.globals.items() if kind == interface)
                obj = client._new(interface)
                client._send(client.registry, 0, struct.pack('=I', name) + client.string(interface)
                             + struct.pack('=II', 1, obj))
                return obj

            seat = bind('wl_seat')
            keyboards = bind('zwp_virtual_keyboard_manager_v1')
            pointer = bind('zwlr_virtual_pointer_manager_v1')
            keyboard = client._new('virtual keyboard')
            client._send(keyboards, 0, struct.pack('=II', seat, keyboard))
            device = client._new('virtual pointer')
            client._send(pointer, 0, struct.pack('=II', seat, device))
            # keymap(format xkb_v1, fd, size): the descriptor travels beside the message.
            keymap = KEYMAP.replace('LAYOUT', layout).encode() + b'\0'
            fd = os.memfd_create('keymap')
            try:
                os.write(fd, keymap)
                sock.sendmsg([struct.pack('=IIII', keyboard, (16 << 16) | 0, 1, len(keymap))],
                             [(socket.SOL_SOCKET, socket.SCM_RIGHTS, struct.pack('i', fd))])
            finally:
                os.close(fd)
            client.roundtrip()
            codes = {**EVDEV, **(QWERTZ if layout == 'de' else {})}

            def click(x=960, y=540):
                now = int(time.monotonic() * 1000) & 0xffffffff
                client._send(device, 1, struct.pack('=5I', now, round(x), round(y), 1920, 1080))
                client._send(device, 4)
                for pressed in (1, 0):
                    client._send(device, 2, struct.pack('=III', now, 0x110, pressed))
                    client._send(device, 4)
                client.roundtrip()

            def press(*keys):
                """Each key is a character on the layout or an xkb key name (Return, Escape, dead_circumflex)."""
                for key in keys:
                    for state in (1, 0):
                        now = int(time.monotonic() * 1000) & 0xffffffff
                        client._send(keyboard, 1, struct.pack('=III', now, codes[key], state))
                    client.roundtrip()
                    time.sleep(0.02)

            yield types.SimpleNamespace(click=click, press=press, type=lambda text: press(*text))

    @contextmanager
    def virtual_click(self):
        with self.virtual_input() as device:
            yield device.click


KEYMAP = """xkb_keymap {
  xkb_keycodes { include "evdev+aliases(qwertz)" };
  xkb_types { include "complete" };
  xkb_compat { include "complete" };
  xkb_symbols { include "pc+LAYOUT+inet(evdev)" };
  xkb_geometry { include "pc(pc105)" };
};"""
# Linux input codes of the keys the tests press; the letters as on a US keyboard, QWERTZ swaps y and z.
EVDEV = {**dict(zip('1234567890', range(2, 12))), **dict(zip('qwertyuiop', range(16, 26))),
         **dict(zip('asdfghjkl', range(30, 39))), **dict(zip('zxcvbnm', range(44, 51))),
         'Escape': 1, 'BackSpace': 14, 'Return': 28, 'dead_circumflex': 41, 'Up': 103, 'Left': 105, 'Right': 106,
         'Down': 108}
QWERTZ = {'y': 44, 'z': 21}


def summary(scene):
    houses = [house for street in scene['streets'] for house in street['houses']]
    return dict(houses=len(houses), lit=sorted(house['id'] for house in houses if house['running']),
                online=scene['online'], hint=scene['finder']['hint'])


def install_channel(program, home, path, setup):
    """Answer the test's requests on the GTK thread, through the program's own handlers."""
    GLib, cairo, town = home.gui.GLib, home.gui.cairo, home.town
    counters = dict(draws=0, frames=0, ticks=0, reasons={}, first=None, trims_armed=0)
    original_draw, original_redraw, original_tick, original_after = home.draw, home.redraw, home.tick, home.after
    other_window = None
    clock = None

    def draw(area, cr, width, height):
        counters['draws'] += 1
        original_draw(area, cr, width, height)
        if counters['first'] is None:
            counters['first'] = summary(town.scene())

    def redraw(reason):
        counters['reasons'][reason] = counters['reasons'].get(reason, 0) + 1
        original_redraw(reason)

    def tick(area, frame_clock):
        # The program's own tick callback: start_motion adds self.tick, which is this wrapper from here on.
        counters['ticks'] += 1
        return original_tick(area, frame_clock)

    def after(milliseconds, callback):
        # The program arms its heap trim through after(); count each arming (REVIEW-2 finding 4).
        if callback == home.settled:
            counters['trims_armed'] += 1
        return original_after(milliseconds, callback)

    home.redraw = redraw
    home.tick = tick
    home.after = after
    home.area.set_draw_func(draw)

    def write(**reply):
        tmp = path / 'reply.tmp'
        tmp.write_text(json.dumps(reply))
        tmp.rename(path / 'reply.json')

    def inject(state):
        for name, value in state.items():
            if name == 'opening':
                value = set(value)
            if not hasattr(town, name):
                raise ValueError(f'unknown town state {name}')
            setattr(town, name, value)

    def model():
        scene = town.scene()
        scene.pop('logos')
        return scene

    def handle(request):
        nonlocal other_window
        op = request['op']
        if op == 'model':
            return model()
        if op == 'set':
            inject(request['state'])
            if request.get('refresh'):
                town.refresh()
            else:
                home.redraw('test')
            return model()
        if op == 'picture':
            inject(request['state'])
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, program.WIDTH, program.HEIGHT)
            home.painter.paint(cairo.Context(surface), program.build_scene(town.inputs((program.WIDTH,
                                                                                        program.HEIGHT))))
            surface.write_to_png(str(path / 'picture.png'))
            return 'picture.png'
        if op == 'key':
            return town.key(request['key'])
        if op == 'click':
            return town.click(request['x'], request['y'])
        if op == 'blur':
            town.blur()
            return None
        if op == 'counters':
            return dict(counters, trim_pending=home.trim_timer is not None)
        if op == 'redraw':
            home.redraw(request['reason'])   # as the clock's minute or a star's twinkle asks
            return None
        if op == 'renderer':
            return home.window.get_renderer().__gtype__.name
        if op == 'surface':
            return {'layer': layer_state(home.window, home.gui.layer), 'fullscreen': home.window.is_fullscreen()}
        if op == 'window':
            home.window.close()
            return {'fullscreen': home.window.is_fullscreen(), 'visible': home.window.get_visible()}
        if op == 'other-window':
            other_window = home.gui.Gtk.Window(application=home.app)
            other_window.fullscreen()
            other_window.present()
            return None
        if op == 'close-other-window':
            other_window.destroy()
            other_window = None
            home.window.get_display().sync()
            return None
        raise ValueError(f'unknown request {op}')

    def check():
        nonlocal clock
        if clock is None and (frame_clock := home.window.get_frame_clock()) is not None:
            clock = frame_clock

            def painted(_clock):
                counters['frames'] += 1

            clock.connect('after-paint', painted)
        request = path / 'request.json'
        if not request.exists():
            return True
        body = json.loads(request.read_text())
        request.unlink()
        if body['op'] == 'bridge-open':
            # The old page's aresosHome.open(): the program's opening path without the town's own checks.
            home.open_app(body['id'], lambda result: write(value=result))
            return True
        try:
            write(value=handle(body))
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            write(error=f'{type(error).__name__}: {error}')
        return True

    GLib.timeout_add(25, check)


def fixture_main(path):
    setup = json.loads((path / 'setup.json').read_text())
    if setup['size']:
        subprocess.run(['/usr/bin/wlr-randr', '--output', 'HEADLESS-1', '--custom-mode', setup['size']], check=True)
    program = load_program(setup['program'])
    libc = ctypes.CDLL(None)
    libc.getenv.argtypes = [ctypes.c_char_p]
    libc.getenv.restype = ctypes.c_char_p
    keys = (b'LD_PRELOAD', b'ARESOS_VIEW_TOKEN')

    def unset():
        return [key.decode() not in os.environ and libc.getenv(key) is None for key in keys]

    before = unset()
    token = program.take_token()
    runtime = Path(os.environ['XDG_RUNTIME_DIR'])
    parent = dict(pid=os.getpid(), before=before, after=unset(),
                  drm_hidden=not Path('/dev/dri').exists() and not any(Path('/dev').glob('nvidia*')),
                  pins=[os.environ.get(key) for key in VENDORS],
                  # What this process sees of /run: the host's is hidden, only the fixture's own folders remain.
                  run=sorted(os.listdir('/run')), helper_socket=Path(os.environ['ARESOS_SHELL_SOCKET']).exists())
    if setup['layer'] is False:
        load_gui = program.load_gui
        program.load_gui = lambda: load_gui()._replace(layer=None)   # as when the layer library is not installed
    if broken := setup['broken']:
        if broken == 'idle':
            program.idle_colour = lambda colour, _look: colour
        elif broken == 'view_mask':
            program.Painter.view_mask = lambda _painter, cr, _street: cr.paint()   # the view without its fade
        else:
            setattr(program.Painter, broken, lambda *_args, **_fields: None)
    original = program.LaptopHome.create_area

    def create(home):
        original(home)
        if setup['clock']:
            fixed = datetime.fromisoformat(setup['clock'])
            home.town.now = lambda: fixed
        parent['app_id'] = home.app.get_application_id()
        parent['display'] = os.environ['WAYLAND_DISPLAY']
        parent['display_reachable'] = (runtime / parent['display']).exists()
        parent['environment'] = {key: os.environ.get(key) for key in ('GDK_DISABLE', 'GSK_RENDERER')}
        if layer := layer_state(home.window, home.gui.layer):
            parent['layer'] = layer
        parent_path = path / 'parent.tmp'
        parent_path.write_text(json.dumps(parent))
        parent_path.rename(path / 'parent.json')
        install_channel(program, home, path, setup)

    def monitor(monitors):
        return next(monitor for monitor in monitors if monitor.get_connector() == 'HEADLESS-1')

    program.LaptopHome.create_area = create
    power = program.battery(68, True) if setup['battery'] else program.NO_BATTERY
    return program.run(token, select_monitor=monitor, sample_power=lambda: power, look=setup['look'])


if __name__ == '__main__':
    sys.exit(fixture_main(Path(sys.argv[1])))
