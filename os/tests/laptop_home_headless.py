"""Run the real laptop-home window inside a disposable labwc; evaluate test JavaScript in its web view."""

import ctypes
import importlib.machinery
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
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


def load_program():
    loader = importlib.machinery.SourceFileLoader('aresos_laptop_home', str(PROGRAM))
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


class Headless:
    def __init__(self, path, socket_path, *, page=FIXTURE):
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
                        WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_LIBINPUT_NO_DEVICES='1',
                        GDK_BACKEND='wayland', GTK_A11Y='none', LIBGL_ALWAYS_SOFTWARE='1',
                        WEBKIT_DISABLE_DMABUF_RENDERER='1', GSK_RENDERER='cairo',
                        ARESOS_SHELL_SOCKET=str(socket_path), ARESOS_DESKTOP_INSTANCE=INSTANCE, **VENDORS)
        layer_dir = os.environ.get('LAPTOP_HOME_TEST_LAYER_DIR')
        lib_dir = Path(layer_dir).resolve() if layer_dir else Path('/usr/lib64')
        lib = lib_dir / 'libgtk4-layer-shell.so.0'
        self.expect_layer = bool(layer_dir) or lib.is_file()
        overrides = [f'GI_TYPELIB_PATH={lib_dir / "girepository-1.0"}'] if layer_dir else []
        self.command = ['env', *overrides, f'LD_PRELOAD={lib if self.expect_layer else "libm.so.6"}',
                        f'ARESOS_VIEW_TOKEN={TOKEN}', sys.executable,
                        str(Path(__file__).resolve()), str(path), str(page)]
        self.config = config

    def __enter__(self):
        self.log = (self.path / 'log').open('w+')
        self.process = subprocess.Popen(
            ['/usr/bin/dbus-run-session', f'--config-file={self.bus}', '--', '/usr/bin/labwc', '-C', str(self.config),
             '-S', shlex.join(self.command)],
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


def fixture_main(path, page):
    program = load_program()
    libc = ctypes.CDLL(None)
    libc.getenv.argtypes = [ctypes.c_char_p]
    libc.getenv.restype = ctypes.c_char_p
    keys = (b'LD_PRELOAD', b'ARESOS_VIEW_TOKEN')

    def unset():
        return [key.decode() not in os.environ and libc.getenv(key) is None for key in keys]

    before = unset()
    token = program.take_token()
    parent = dict(pid=os.getpid(), before=before, after=unset(),
                  pins=[os.environ.get(key) for key in VENDORS])
    original = program.LaptopHome.create_view

    def create(home):
        original(home)
        parent['ephemeral'] = home.view.get_network_session().is_ephemeral()
        parent['app_id'] = home.window.get_application().get_application_id()
        if home.layer is not None and home.layer.is_layer_window(home.window):
            parent['layer'] = {
                'background': home.layer.get_layer(home.window) == home.layer.Layer.BACKGROUND,
                'on_demand': home.layer.get_keyboard_mode(home.window) == home.layer.KeyboardMode.ON_DEMAND,
                'anchored': all(home.layer.get_anchor(home.window, getattr(home.layer.Edge, edge))
                                for edge in ('TOP', 'BOTTOM', 'LEFT', 'RIGHT')),
                'output': home.layer.get_monitor(home.window).get_connector(),
            }
        parent_path = path / 'parent.tmp'
        parent_path.write_text(json.dumps(parent))
        parent_path.rename(path / 'parent.json')
        allow_foreign = False

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

        # This one test action bypasses production navigation to inspect a document that normally cannot load.
        home.view.connect('decide-policy', decide)
        # Run the harness's handler first; the product handler consumes every decision.
        home.view.disconnect_by_func(home.decide)
        home.view.connect('decide-policy', home.decide)

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

        def check():
            nonlocal allow_foreign
            request = path / 'request.js'
            if not request.exists() or home.view.get_uri() is None:
                return True
            body = request.read_text()
            request.unlink()
            if body == '@foreign':
                allow_foreign = True
                home.view.load_uri(FOREIGN)
                write(value=None)
            elif body == '@window':
                home.window.close()
                write(value={'fullscreen': home.window.is_fullscreen(), 'visible': home.window.get_visible()})
            else:
                home.view.call_async_javascript_function(body, -1, None, None, None, None, finish)
            return True

        home.GLib.timeout_add(25, check)

    def monitor(monitors):
        return next(monitor for monitor in monitors if monitor.get_connector() == 'HEADLESS-1')

    program.LaptopHome.create_view = create
    return program.run(token, root=page, select_monitor=monitor, sample_power=lambda: program.battery(68, True))


if __name__ == '__main__':
    sys.exit(fixture_main(Path(sys.argv[1]), Path(sys.argv[2])))
