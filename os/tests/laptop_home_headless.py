"""Run the real laptop-home window inside a disposable labwc; evaluate test JavaScript in its web view."""

import ctypes
from contextlib import contextmanager
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

from laptop_home_helper import INSTANCE, TOKEN

ROOT = Path(__file__).resolve().parents[2]
PROGRAM = ROOT / 'os/config/usr/libexec/aresos-laptop-home'
FIXTURE = Path(__file__).with_name('laptop-home-page')
VENDORS = {
    '__EGL_VENDOR_LIBRARY_FILENAMES': '/usr/share/glvnd/egl_vendor.d/50_mesa.json',
    'VK_DRIVER_FILES': '/usr/share/vulkan/icd.d/intel_icd.x86_64.json',
}
FOREIGN = 'aresos-home://page/foreign.html'


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


def headless_available():
    try:
        import gi
    except ImportError:
        return False
    try:
        for name, version in (('Gtk', '4.0'), ('WebKit', '6.0'), ('JavaScriptCore', '6.0'), ('Soup', '3.0')):
            gi.require_version(name, version)
    except ValueError:
        return False
    return (all(shutil.which(name, path='/usr/bin') for name in ('labwc', 'dbus-run-session'))
            and all(Path(path).is_file() for path in VENDORS.values()))


def descendants(pid):
    found = []
    for task in Path(f'/proc/{pid}/task').glob('*/children'):
        try:
            for child in map(int, task.read_text().split()):
                found.append(child)
                found.extend(descendants(child))
        except FileNotFoundError:
            continue
    return set(found)


def engines(pid):
    found = {}
    for child in descendants(pid):
        try:
            command = Path(f'/proc/{child}/cmdline').read_bytes().split(b'\0')[0]
            if b'WebKit' in command and command.endswith(b'Process'):
                found[child] = os.fsdecode(command.rsplit(b'/', 1)[-1])
        except FileNotFoundError:
            continue
    return found


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
    def __init__(self, path, socket_path, *, page=FIXTURE, size=None, script='', font_dir=None, battery=True,
                 legacy_renderers=None, isolate_drm=False, native=False, program=PROGRAM):
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
        # Keep Wayland, home, state and D-Bus isolated. Pin both the compositor and every process it starts.
        self.env = dict(HOME=str(path), PATH='/usr/bin:/bin', XDG_RUNTIME_DIR=str(self.runtime),
                        XDG_STATE_HOME=str(self.state), XDG_CONFIG_HOME=str(config),
                        XDG_DATA_HOME=str(path / '.local/share'), XDG_CACHE_HOME=str(path / '.cache'),
                        TMPDIR=str(self.runtime),
                        WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_LIBINPUT_NO_DEVICES='1',
                        GDK_BACKEND='wayland', GTK_A11Y='none', LIBGL_ALWAYS_SOFTWARE='1',
                        ARESOS_SHELL_SOCKET=str(socket_path), ARESOS_DESKTOP_INSTANCE=INSTANCE, **VENDORS)
        if legacy_renderers is None:
            legacy_renderers = os.environ.get('LAPTOP_HOME_TEST_CURRENT_RENDERERS') != '1'
        self.isolate_drm = isolate_drm or not legacy_renderers
        if legacy_renderers:
            self.env.update(WEBKIT_DISABLE_DMABUF_RENDERER='1', GSK_RENDERER='cairo')
        if font_dir is not None:
            fonts = path / '.local/share/fonts'
            fonts.mkdir(parents=True)
            for font in font_dir.glob('*.ttf'):
                shutil.copyfile(font, fonts / font.name)
        (path / 'setup.json').write_text(json.dumps(dict(size=size, script=script, battery=battery,
                                                        program=str(program.resolve()))))
        layer_dir = os.environ.get('LAPTOP_HOME_TEST_LAYER_DIR')
        lib_dir = Path(layer_dir).resolve() if layer_dir else Path('/usr/lib64')
        lib = lib_dir / 'libgtk4-layer-shell.so.0'
        typelib_dir = lib_dir / 'girepository-1.0'
        if layer_dir and not (lib.is_file() and (typelib_dir / 'Gtk4LayerShell-1.0.typelib').is_file()):
            raise FileNotFoundError('the configured layer library and typelib are required')
        self.expect_layer = lib.is_file()
        overrides = [f'GI_TYPELIB_PATH={typelib_dir}'] if layer_dir else []
        preload = f'LD_PRELOAD={lib if self.expect_layer else "libm.so.6"}'
        if native:
            runner = Path(__file__).with_name('laptop_home_native.py').resolve()
            self.command = ['env', *overrides, preload, sys.executable, str(runner), str(path)]
        else:
            self.command = ['env', *overrides, preload, f'ARESOS_VIEW_TOKEN={TOKEN}', sys.executable,
                            str(Path(__file__).resolve()), str(path), str(page)]
        self.config = config

    def __enter__(self):
        self.log = (self.path / 'log').open('w+')
        isolation = []
        if self.isolate_drm:
            # Mesa can inspect a DRM device even in software mode. Hide the host devices before labwc starts.
            isolation = ['/usr/bin/bwrap', '--die-with-parent', '--ro-bind', '/', '/', '--dev', '/dev',
                         '--proc', '/proc', '--tmpfs', '/tmp', '--bind', str(self.path), str(self.path), '--']
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

    def evaluate(self, body, duration=12):
        result = self.path / 'reply.json'
        result.unlink(missing_ok=True)
        command = self.path / 'request.tmp'
        command.write_text(body)
        command.rename(self.path / 'request.js')
        wait_for(result.exists, duration)
        reply = json.loads(result.read_text())
        if 'error' in reply:
            raise AssertionError(reply['error'])
        return reply['value']

    def parent(self):
        path = self.path / 'parent.json'
        wait_for(path.exists)
        return json.loads(path.read_text())

    def until(self, expression):
        return wait_for(lambda: self.evaluate(f'return Boolean({expression});'))

    def snapshot(self):
        return self.path / self.evaluate('@snapshot')

    @contextmanager
    def virtual_click(self):
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
            keyboard = bind('zwp_virtual_keyboard_manager_v1')
            pointer = bind('zwlr_virtual_pointer_manager_v1')
            client._send(keyboard, 0, struct.pack('=II', seat, client._new('virtual keyboard')))
            device = client._new('virtual pointer')
            client._send(pointer, 0, struct.pack('=II', seat, device))
            client.roundtrip()

            def click():
                now = int(time.monotonic() * 1000) & 0xffffffff
                client._send(device, 1, struct.pack('=5I', now, 50, 50, 100, 100))
                client._send(device, 4)
                for pressed in (1, 0):
                    client._send(device, 2, struct.pack('=III', now, 0x110, pressed))
                    client._send(device, 4)
                client.roundtrip()

            yield click


def fixture_main(path, page):
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
    parent = dict(pid=os.getpid(), before=before, after=unset(),
                  drm_hidden=not Path('/dev/dri').exists() and not any(Path('/dev').glob('nvidia*')),
                  pins=[os.environ.get(key) for key in VENDORS])
    original = program.LaptopHome.create_view

    def create(home):
        original(home)
        if setup['script']:
            home.manager.add_script(home.WebKit.UserScript.new(
                setup['script'], home.WebKit.UserContentInjectedFrames.TOP_FRAME,
                home.WebKit.UserScriptInjectionTime.START, [program.PAGE], None))
        parent['ephemeral'] = home.view.get_network_session().is_ephemeral()
        parent['app_id'] = home.window.get_application().get_application_id()
        parent['display'] = os.environ['WAYLAND_DISPLAY']
        if layer := layer_state(home.window, home.layer):
            parent['layer'] = layer
        parent_path = path / 'parent.tmp'
        parent_path.write_text(json.dumps(parent))
        parent_path.rename(path / 'parent.json')
        allow_foreign = False
        other_window = None

        def decide(_view, decision, kind):
            if allow_foreign and kind == home.WebKit.PolicyDecisionType.NAVIGATION_ACTION:
                if decision.get_navigation_action().get_request().get_uri() == FOREIGN:
                    decision.use()
                    return True
            if allow_foreign and kind == home.WebKit.PolicyDecisionType.RESPONSE:
                if decision.get_request().get_uri() == FOREIGN:
                    decision.use()
                    return True
            return False

        def write(**reply):
            tmp = path / 'reply.tmp'
            tmp.write_text(json.dumps(reply))
            tmp.rename(path / 'reply.json')

        def finish(view, result):
            try:
                value = view.call_async_javascript_function_finish(result)
                write(value=None if value.is_undefined() else json.loads(value.to_json(0)))
            except (home.GLib.Error, ValueError, TypeError) as error:
                write(error=str(error))

        def snapshot(view, result):
            try:
                photo = view.get_snapshot_finish(result)
                if not photo.save_to_png(str(path / 'snapshot.png')):
                    raise ValueError('could not save the WebKit snapshot')
                write(value='snapshot.png')
            except (home.GLib.Error, ValueError) as error:
                write(error=str(error))

        def check():
            nonlocal allow_foreign, other_window
            request = path / 'request.js'
            if not request.exists() or home.view.get_uri() is None:
                return True
            body = request.read_text()
            request.unlink()
            if body == '@foreign':
                # Inspect a normally unreachable document without modifying the initial load's policy.
                if not allow_foreign:
                    allow_foreign = True
                    home.view.disconnect_by_func(home.decide)
                    home.view.connect('decide-policy', decide)
                    home.view.connect('decide-policy', home.decide)
                home.view.load_uri(FOREIGN)
                write(value=None)
            elif body == '@window':
                home.window.close()
                write(value={'fullscreen': home.window.is_fullscreen(), 'visible': home.window.get_visible()})
            elif body == '@other-window':
                other_window = home.Gtk.Window(application=home.app)
                other_window.fullscreen()
                other_window.present()
                write(value=None)
            elif body == '@close-other-window':
                other_window.destroy()
                other_window = None
                home.window.get_display().sync()
                write(value=None)
            elif body == '@snapshot':
                home.view.get_snapshot(home.WebKit.SnapshotRegion.VISIBLE, home.WebKit.SnapshotOptions.NONE,
                                       None, snapshot)
            elif body == '@renderer':
                write(value={'gsk': home.window.get_renderer().__gtype__.name,
                             'web_acceleration_policy': home.view.get_settings().get_hardware_acceleration_policy().value_nick})
            else:
                home.view.call_async_javascript_function(body, -1, None, None, None, None, finish)
            return True

        home.GLib.timeout_add(25, check)

    def monitor(monitors):
        return next(monitor for monitor in monitors if monitor.get_connector() == 'HEADLESS-1')

    program.LaptopHome.create_view = create
    power = program.battery(68, True) if setup['battery'] else program.NO_BATTERY
    return program.run(token, root=page, select_monitor=monitor, sample_power=lambda: power)


if __name__ == '__main__':
    sys.exit(fixture_main(Path(sys.argv[1]), Path(sys.argv[2])))
