"""Package 320's nine checks against the shipped keys, programs and labwc."""
from collections import Counter
from contextlib import contextmanager
import fcntl
from functools import lru_cache
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import select
import subprocess
import sys
import time
import traceback

from PIL import Image, ImageChops

sys.path[:0] = ['/harness', '/harness/os/tests']
from level_sandbox import BACKLIGHT, LED
import pixels

EV = Path('/evidence')
RUNTIME = Path(os.environ['XDG_RUNTIME_DIR'])
CONFIG = Path(os.environ['XDG_CONFIG_HOME'])
STANDINS = Path(os.environ['STANDIN_DIR'])
STATE = STANDINS / 'state.json'
SETTINGS = CONFIG / 'aresos/settings.json'
LIB = Path('/usr/lib64/libgtk4-layer-shell.so.0')
TYPELIB = Path('/usr/lib64/girepository-1.0/Gtk4LayerShell-1.0.typelib')
INDICATOR = Path('/usr/libexec/aresos-indicator')
LEVEL = '/usr/libexec/aresos-level'
WLH = '/opt/harness/bin/wl-harness'
WAYLAND = 'wayland-0'
LEFT, RIGHT = 'HEADLESS-1', 'HEADLESS-2'
W, H = 1000, 640
WORLD = (32, 64, 96)
# Linux input event codes, mapped through the virtual keyboard's evdev keymap.
KEY = dict(brightness_up=225, brightness_down=224, volume_up=115, volume_down=114, mute=113, mic_mute=248)
START_LINE = 'aresos-indicator: started'

loader = importlib.machinery.SourceFileLoader('shell', '/harness/os/config/usr/libexec/aresos-shell')
shell = importlib.util.module_from_spec(importlib.util.spec_from_loader(loader.name, loader))
sys.modules[loader.name] = shell
loader.exec_module(shell)


class PlacementError(AssertionError):
    """The brief reserves compositor placement decisions for the lead."""


def run(*command, env=None, timeout=5, check=True):
    result = subprocess.run(command, env=env, capture_output=True, timeout=timeout)
    if check and result.returncode:
        raise AssertionError(f'{command[0]} exited {result.returncode}: {result.stderr.decode(errors="replace")}')
    return result


def until(predicate, description, timeout=4, interval=0.015):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if result := predicate():
            return result
        time.sleep(interval)
    raise AssertionError(f'timed out waiting for {description}')


def state():
    with STATE.open() as handle:
        fcntl.flock(handle, fcntl.LOCK_SH)
        return json.load(handle)


def reset_devices(**changes):
    normal = dict(devices=[BACKLIGHT, LED], sink=dict(volume=0.62, mute=False), source=dict(volume=1.0, mute=False))
    STATE.write_text(json.dumps(normal | changes))


def calls():
    file = STANDINS / 'calls.jsonl'
    return [json.loads(line) for line in file.read_text().splitlines()] if file.exists() else []


def sink_calls():
    return [row for row in calls() if row['tool'] == '/usr/bin/wpctl' and row['argv'][0] == 'set-volume']


def graph(label):
    nodes = []
    if label:
        nodes = [
            dict(props={'metadata.name': 'default'},
                 metadata=[dict(subject=0, key='default.audio.sink', value=dict(name='fixture.sink'))]),
            dict(type='PipeWire:Interface:Node',
                 info=dict(props={'node.name': 'fixture.sink', 'media.class': 'Audio/Sink',
                                  'device.id': 10, 'card.profile.device': 0})),
        ]
        device, params = {'device.api': 'alsa'}, {}
        if label in ('Speakers', 'Headphones'):
            params['Route'] = [dict(direction='Output', device=0, name='analog-output-' + label.lower(),
                                    info=[1, 'port.type', label.lower()])]
        else:
            device = {'device.api': 'bluez5', 'device.alias': label}
        nodes.append(dict(id=10, type='PipeWire:Interface:Device', info=dict(props=device, params=params)))
    path = STANDINS / 'graph.json'
    path.with_suffix('.new').write_text(json.dumps(nodes))
    path.with_suffix('.new').rename(path)


def processes(program, *, include_zombies=False):
    found = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            args = (proc / 'cmdline').read_bytes().split(b'\0')
            if os.fsencode(program) not in args[1:2]:
                continue
            if include_zombies or (proc / 'stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z':
                found.append(int(proc.name))
        except ProcessLookupError:
            continue
        except FileNotFoundError:
            continue
    return found


def has_owner():
    return run('/usr/bin/gdbus', 'call', '--session', '--timeout', '1', '--dest', 'org.freedesktop.DBus',
               '--object-path', '/org/freedesktop/DBus', '--method', 'org.freedesktop.DBus.NameHasOwner',
               'aresos.indicator').stdout.strip() == b'(true,)'


def show(seq, action, reading):
    run('/usr/bin/gdbus', 'call', '--session', '--timeout', '1', '--dest', 'aresos.indicator',
        '--object-path', '/aresos/indicator', '--method', 'aresos.Indicator.Show',
        f'uint64 {seq}', f"'{action}'", f"'{reading}'")


class Toplevels(shell.Windows):
    def __init__(self):
        super().__init__()
        self.announced = []

    def new(self, handle):
        self.announced.append(handle)
        super().new(handle)


class Session:
    def __init__(self, number, *, width=W, height=H):
        self.number = number
        self.children = []
        self.log_path = EV / f'{number:02}-labwc.log'
        self.env = dict(os.environ, WAYLAND_DISPLAY=WAYLAND)
        self.count = 0
        self.phase = 0
        self.width = width
        self.height = height

    def __enter__(self):
        self.log_path.write_text('')
        return self

    def __exit__(self, *_):
        self.stop()

    def spawn(self, command, *, env, log, pipes=False, stdin=False):
        with log.open('ab') as handle:
            proc = subprocess.Popen(command, env=env, stdin=subprocess.PIPE if pipes or stdin else subprocess.DEVNULL,
                                    stdout=subprocess.PIPE if pipes else handle, stderr=handle)
        self.children.append(proc)
        return proc

    def start_compositor(self, *, delay=0, idle=16000, config=CONFIG / 'labwc', verbose=False):
        self.phase += 1
        env = dict(self.env, WLR_BACKENDS='headless', WLR_RENDERER='pixman', WLR_HEADLESS_OUTPUTS='2',
                   WLR_LIBINPUT_NO_DEVICES='1', LABWC_UPDATE_ACTIVATION_ENV='0',
                   ARESOS_INDICATOR_TEST_EDP=RIGHT, ARESOS_INDICATOR_TEST_IDLE_MS=str(idle),
                   ARESOS_INDICATOR_TEST_START_DELAY_MS=str(delay))
        env.pop('WAYLAND_DISPLAY')
        argv = ['/usr/bin/labwc', '-C', str(config)]
        if verbose:
            argv.append('-V')
        labwc = self.spawn(argv, env=env, log=self.log_path)
        until(lambda: (RUNTIME / WAYLAND).is_socket(), 'private labwc', timeout=8)
        assert labwc.poll() is None, 'private labwc exited'
        self.outputs = {LEFT: 0, RIGHT: self.width}
        self.arrange_outputs()
        layout = {output['name']: output for output in json.loads(self.randr('--json')) if output['enabled']}
        assert {name: (info['position'], info['scale']) for name, info in layout.items()} == {
            LEFT: ({'x': 0, 'y': 0}, 1.0), RIGHT: ({'x': self.width, 'y': 0}, 1.0)}
        self.pointer = self.device('pointer')
        self.keyboard = self.device('keyboard')
        self.goto(LEFT, self.width // 2, self.height // 2)
        return labwc

    def observe_toplevels(self):
        self.toplevels = Toplevels()
        self.observer = shell.ForeignToplevels.connect(self.toplevels, self.env)
        self.observer.sock.settimeout(3)

    def start(self, *, lock=False, delay=0, idle=16000, config=CONFIG / 'labwc'):
        labwc = self.start_compositor(config=config, delay=delay, idle=idle)
        suffix = f'-{self.phase}' if self.phase > 1 else ''
        self.world_path = EV / f'{self.number:02}-world{suffix}.log'
        argv = [WLH, 'window'] + (['--lock'] if lock else [])
        self.world = self.spawn(argv, env=self.env, log=self.world_path, stdin=lock)
        until(lambda: 'KBD_ENTER' in self.world_lines(), 'world keyboard focus')
        until(lambda: any(line.startswith('ENTER ') for line in self.world_lines()), 'world pointer focus')
        if lock:
            until(lambda: 'LOCKED' in self.world_lines(), 'compositor pointer lock')
        self.observe_toplevels()
        def world_announced():
            self.observer.roundtrip()
            return self.toplevels.announced
        until(world_announced, 'world toplevel announcement')
        assert len(self.toplevels.announced) == 1, self.toplevels.announced
        self.baselines = {name: self.grab(name) for name in self.outputs}
        assert self.baselines[LEFT].getpixel((W // 2, H // 2)) == WORLD, 'fullscreen stand-in is not on the left'
        assert 'Updating dbus execution environment' not in self.log()
        for proc in (labwc, self.pointer, self.keyboard, self.world):
            fields = dict(item.split(b'=', 1) for item in Path(f'/proc/{proc.pid}/environ').read_bytes().split(b'\0')
                          if b'=' in item)
            for key in ('HOME', 'XDG_RUNTIME_DIR', 'DBUS_SESSION_BUS_ADDRESS'):
                assert fields[key.encode()] == self.env[key].encode(), (proc.pid, key)
            assert fields.get(b'WAYLAND_DISPLAY') == (None if proc is labwc else WAYLAND.encode())
            assert b'DISPLAY' not in fields

    def stop(self):
        if hasattr(self, 'observer'):
            self.observer.sock.close()
            del self.observer
        # The children can still finish their notification before the compositor is stopped.
        until(lambda: not processes(LEVEL), 'key scripts and notifiers to drain', timeout=12)
        for pid in processes(INDICATOR):
            try:
                os.kill(pid, 15)
            except ProcessLookupError:
                pass
        for proc in reversed(self.children):
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(3)
        self.children.clear()
        until(lambda: not has_owner(), 'indicator D-Bus name to disappear')

    def randr(self, *args):
        return run('/usr/bin/wlr-randr', *args, env=self.env).stdout

    def arrange_outputs(self):
        mode = f'{self.width}x{self.height}'
        self.randr('--output', LEFT, '--on', '--custom-mode', mode, '--scale', '1', '--pos', '0,0',
                   '--output', RIGHT, '--on', '--custom-mode', mode, '--scale', '1', '--pos', f'{self.width},0')

    def device(self, kind):
        proc = self.spawn([WLH, 'input', kind], env=self.env, log=self.log_path, pipes=True)
        assert self.answer(proc) == b'READY', f'{kind} device failed'
        return proc

    @staticmethod
    def answer(proc):
        assert select.select([proc.stdout], [], [], 3)[0], 'virtual input did not answer'
        return proc.stdout.readline().strip()

    @staticmethod
    def send(proc, command):
        proc.stdin.write((command + '\n').encode())
        proc.stdin.flush()

    def input(self, proc, command):
        self.send(proc, command)
        assert self.answer(proc) == b'OK', command

    def key(self, name, down):
        self.input(self.keyboard, f'key {KEY.get(name, name)} {int(down)}')

    def tap(self, name):
        self.key(name, True)
        self.key(name, False)

    def goto(self, name, x, y):
        self.input(self.pointer, f'abs {self.outputs[name] + x} {y} {2 * self.width} {self.height}')

    def log(self):
        return self.log_path.read_text(errors='replace')

    def launches(self):
        return self.log().splitlines().count(START_LINE)

    def world_lines(self):
        return self.world_path.read_text().splitlines()

    def grab(self, name):
        out = run('/usr/bin/grim', '-o', name, '-', env=self.env, timeout=3).stdout
        with Image.open(io.BytesIO(out)) as image:
            return image.convert('RGB')

    def frame(self, name):
        image = self.grab(name)
        return image, ImageChops.difference(image, self.baselines[name]).getbbox()

    def plate(self, *, output=LEFT, width=None, scale=3, place='top', capture=None):
        # Inspect both outputs when waiting for placement and stop as soon as the wrong one shows.
        def active():
            for name in self.outputs:
                frame, box = self.frame(name)
                if box and name != output:
                    if capture:
                        frame.save(EV / (capture + '-wrong-output.png'))
                    raise PlacementError(f'expected the plate on {output}, labwc mapped it on {name} at {box}')
                if box and name == output:
                    other = [other for other in self.outputs if other != name and self.frame(other)[1]]
                    if other:
                        raise PlacementError(f'plate visible on {name} and {other}')
                    return frame, box
            return None

        image, box = until(active, 'a visible plate')
        if capture:
            image.save(EV / (capture + '.png'))
        if width is not None:
            expected_y = 8 * scale if place == 'top' else H - (64 + 30) * scale
            # An odd plate width on an even output can centre on either of the two adjacent pixels.
            left, top, right, bottom = box
            assert (right - left, bottom - top, top) == (width, 30 * scale, expected_y), box
            assert abs(left + right - W) <= 1, box
        return image.crop(box), box

    def gone(self, output=LEFT, timeout=3):
        until(lambda: not self.frame(output)[1], 'plate to disappear', timeout=timeout)
        return time.monotonic()

    def check(self, condition, message):
        assert condition, message
        self.count += 1
        print(f'PASS {self.number}.{self.count} {message}', flush=True)


def settings(**values):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(dict(version=1, **values)))


def idle_keys():
    until(lambda: not processes(LEVEL), 'key scripts and notifiers to finish', timeout=8)


@lru_cache(maxsize=21)
def bar_at(value):
    bar = pixels.reference(pixels.level(value, label=''), 3).convert('RGB')
    return bar.crop((28 * 3, 18 * 3, 171 * 3, 26 * 3))


def rendered_level(image):
    # Compare the actual slot and all twenty steps, independently of the labels.
    for value in range(0, 101, 5):
        box = (28 * 3, 18 * 3, 171 * 3, 26 * 3)
        if image.size == (525, 90) and ImageChops.difference(image.crop(box), bar_at(value)).getbbox() is None:
            return value
    return None


def expect_level(app, value, **kwargs):
    def visible():
        image, box = app.frame(kwargs.get('output', LEFT))
        return box and rendered_level(image.crop(box)) == value
    until(visible, f'bar to reach {value}%')
    return app.plate(width=525, **kwargs)[0]


def test1(app):
    reset_devices(sink=dict(volume=0.60, mute=False))
    app.start(lock=True)
    mark = len(app.world_lines())
    app.tap('volume_up')
    first, _ = app.plate(width=525, capture='01-pointer-lock')
    app.check(rendered_level(first) == 65, 'the 65% plate is visible while the compositor lock is active')
    for _ in range(4):
        app.tap(30)
        app.input(app.pointer, 'rel 10 5')
    app.tap('volume_up')
    expect_level(app, 70, capture='01-pointer-lock-update')
    for _ in range(4):
        app.tap(31)
        app.input(app.pointer, 'rel 10 5')
    app.gone()
    app.tap(32)
    app.input(app.pointer, 'rel 10 5')
    until(lambda: app.world_lines()[mark:].count('REL 10.00 5.00') == 9, 'all relative motion')
    events = Counter(app.world_lines()[mark:])
    app.check(all(events[f'KEY {key} {down}'] == count for key, count in ((30, 4), (31, 4), (32, 1))
                  for down in (0, 1)), '9 key presses and 9 releases reached the locked world')
    app.check(events['REL 10.00 5.00'] == 9 and not any(line.startswith('MOTION ') for line in events),
              '9 unaccelerated deltas (90, 45), zero absolute motions while locked')
    app.check(not (events.keys() & {'UNLOCKED', 'LEAVE', 'KBD_LEAVE'}),
              'zero unlocks, pointer leaves or keyboard leaves across show, update and hide')


def test2(app):
    app.start(lock=True)
    app.send(app.world, 'release')
    until(lambda: 'RELEASED' in app.world_lines(), 'client releasing its constraint')
    app.tap('volume_up')
    _, box = app.plate(width=525, capture='02-above-fullscreen')
    x, y = (box[0] + box[2]) // 2, (box[1] + box[3]) // 2
    mark = len(app.world_lines())
    app.goto(LEFT, x, y)
    app.input(app.pointer, 'btn 272 1')
    app.input(app.pointer, 'btn 272 0')
    until(lambda: 'BUTTON 272 0' in app.world_lines()[mark:], 'click release in the world')
    events = app.world_lines()[mark:]
    app.check(all(line in events for line in (f'MOTION {x:.1f} {y:.1f}', 'BUTTON 272 1', 'BUTTON 272 0')),
              f'the fullscreen stand-in received the click at ({x}, {y}) under the visible plate')
    app.check(app.frame(LEFT)[1] == box, 'the plate stayed visible above the fullscreen window during the click')


@contextmanager
def moved(*paths):
    saved = [(path, path.with_name(path.name + '.harness')) for path in paths]
    for path, backup in saved:
        path.rename(backup)
    try:
        yield
    finally:
        for path, backup in reversed(saved):
            path.unlink(missing_ok=True)
            backup.rename(path)


def six_keys(app, failure):
    reset_devices(sink=dict(volume=0.45, mute=True))
    wanted = [
        ('brightness_up', lambda s: s['devices'][0]['cur'] == 52800),
        ('brightness_down', lambda s: s['devices'][0]['cur'] == 48000),
        ('volume_up', lambda s: s['sink'] == dict(volume=0.50, mute=False)),
        ('volume_down', lambda s: s['sink'] == dict(volume=0.45, mute=False)),
        ('mute', lambda s: s['sink']['mute']),
        ('mic_mute', lambda s: s['source']['mute']),
    ]
    for key, changed in wanted:
        app.tap(key)
        until(lambda: changed(state()), f'{failure} {key} device change')
        idle_keys()
    app.observer.roundtrip()
    app.check(len(app.toplevels.announced) == 1 and not has_owner() and all(not app.frame(o)[1] for o in app.outputs),
              f'{failure}: all six keys changed the fixture, zero plates and zero new toplevels')


def test3(app):
    app.start()
    mark = len(app.world_lines())
    with moved(INDICATOR):
        six_keys(app, 'program removed')
    INDICATOR.chmod(0o644)
    try:
        six_keys(app, 'program nonexecutable')
    finally:
        INDICATOR.chmod(0o755)
    with moved(INDICATOR):
        INDICATOR.write_text('#!/usr/bin/python3\nraise RuntimeError("synthetic crash at startup")\n')
        INDICATOR.chmod(0o755)
        six_keys(app, 'program crashed')
    with moved(LIB, TYPELIB):
        six_keys(app, 'library absent')
    app.check(app.log().count('aresos-indicator: cannot start') == 6, 'absent layer library logged one program error per launch')

    def xwayland():
        return next(iter(Path('/tmp/.X11-unix').glob('X[0-9]*')), None)
    display = until(xwayland, 'private Xwayland socket')
    env = dict(app.env, GDK_BACKEND='x11', DISPLAY=':' + display.name[1:], LD_PRELOAD=str(LIB),
               GSK_RENDERER='cairo', GDK_DISABLE='gl,vulkan')
    probe = """
import gi
for name, version in [('Gtk4LayerShell', '1.0'), ('Gtk', '4.0'), ('GdkX11', '4.0')]:
    gi.require_version(name, version)
from gi.repository import Gdk, GdkX11, Gtk, Gtk4LayerShell
assert Gtk.init_check() and isinstance(Gdk.Display.get_default(), GdkX11.X11Display)
assert not Gtk4LayerShell.is_supported()
"""
    run('/usr/bin/python3', '-c', probe, env=env)
    failed = run(str(INDICATOR), '1', 'show-volume', '62', env=env, check=False)
    (EV / '03-xwayland-indicator.log').write_bytes(failed.stderr)
    app.observer.roundtrip()
    app.check(failed.returncode == 1 and failed.stderr.decode().splitlines()
              == [START_LINE, 'aresos-indicator: the compositor has no usable layer-shell protocol'],
              'loadable real layer library without the protocol logged its entry and one error, then exited 1')
    app.check(len(app.toplevels.announced) == 1 and 'KBD_LEAVE' not in app.world_lines()[mark:]
              and not has_owner() and all(not app.frame(o)[1] for o in app.outputs),
              'zero new toplevels, plates or keyboard leaves through all failure cases')


def repeat(app):
    """Use labwc's repeat when it handles the virtual keyboard. Otherwise inject 25 presses/s."""
    begin = time.monotonic()
    mark = len(sink_calls())
    app.key('volume_down', True)
    observations = []
    frames = []
    while time.monotonic() < begin + 1.06:
        image, box = app.frame(LEFT)
        if box:
            observations.append(rendered_level(image.crop(box)))
            frames.append(image)
        time.sleep(0.02)
    app.key('volume_down', False)
    ended = time.monotonic()
    idle_keys()
    repeated = len(sink_calls()) - mark
    if repeated <= 1:
        app.gone()
        reset_devices(sink=dict(volume=1.0, mute=False))
        observations, frames = [], []
        mark = len(sink_calls())
        begin = time.monotonic()
        for index in range(14):
            time.sleep(max(0, begin + index * 0.04 - time.monotonic()))
            app.tap('volume_down')
            if index in (3, 7, 11):
                image, box = app.frame(LEFT)
                if box:
                    observations.append(rendered_level(image.crop(box)))
                    frames.append(image)
        ended = time.monotonic()
        mode = '14 separate presses at 25/s (labwc did not repeat the virtual hold)'
    else:
        mode = 'labwc repeated one held virtual key'
    for index, image in enumerate(frames):
        if index == 0 or observations[index] != observations[index - 1]:
            image.save(EV / f'{app.number:02}-repeat-{index:02}.png')
    marks = [row['t'] for row in sink_calls()[mark:]]
    return mode, observations, begin, ended, marks


def test4(app):
    reset_devices(sink=dict(volume=1.0, mute=False))
    app.start()
    mode, observations, _, released, marks = repeat(app)
    final = round(state()['sink']['volume'] * 100)
    app.check(len(marks) >= 8 and final == max(0, 100 - 5 * len(marks)), f'{mode}: {len(marks)} changes, final {final}%')
    rate = (len(marks) - 2) / (marks[-1] - marks[1]) if 'held virtual' in mode else (len(marks) - 1) / (marks[-1] - marks[0])
    initial_ms = (marks[1] - marks[0]) * 1000
    app.check(20 <= rate <= 30, f'repeat cadence {rate:.1f} changes/s, first interval {initial_ms:.0f} ms')
    seen = [value for value in observations if value is not None]
    app.check(len(set(seen)) >= 2 and seen == sorted(seen, reverse=True), f'visible bar traversed levels {sorted(set(seen), reverse=True)}')
    expect_level(app, final, capture='04-final-repeat-level')
    app.check(len(processes(INDICATOR)) == 1 and app.launches() == 1 and not processes(LEVEL),
              'one program and one start line, all key scripts and notifiers finished')
    wait = app.gone() - released
    app.check(1.30 <= wait <= 1.85, f'plate vanished {wait:.3f} s after release')


def test5(app):
    app.start()
    cases = [
        ('no-backlight', 'brightness_up', {'devices': [LED]},
         pixels.message('sun', 'Brightness', 'not available here', off=True)),
        ('screen-off', 'brightness_up', {},
         pixels.message('sun', 'Laptop screen', 'is off', off=True)),
        ('no-sound', 'volume_up', {'sink': None},
         pixels.message('speaker', 'Sound', 'no output found', off=True)),
        ('no-microphone', 'mic_mute', {'source': None},
         pixels.message('microphone', 'Microphone', 'none found', off=True)),
    ]
    for name, key, devices, want in cases:
        if name == 'screen-off':
            app.randr('--output', RIGHT, '--off')
            app.outputs.pop(RIGHT)
            enabled = [output['name'] for output in json.loads(app.randr('--json')) if output['enabled']]
            assert enabled == [LEFT], enabled
        reset_devices(**devices)
        app.tap(key)
        image, _ = app.plate(capture=f'05-{name}')
        shifts = pixels.exact(image, want, 3, fit_message=True)
        app.check(True, f'{name}: visible {want["label"]!r} / {want["status"]!r} and grey icon (shifts: {shifts or "none"})')
        idle_keys()
        if name == 'no-backlight':
            app.check(state()['devices'] == [LED], 'the LED-only fixture did not change')
        if name == 'screen-off':
            app.check(state()['devices'][0]['cur'] == 52800, 'the backlight exists and changed while its output was off')
        app.gone()


def test6(app):
    app.start(lock=True)
    app.send(app.world, 'release')
    until(lambda: 'RELEASED' in app.world_lines(), 'client releasing its constraint')
    for output in (LEFT, RIGHT):
        app.goto(output, W // 2, H // 2)
        app.tap('volume_up')
        app.plate(output=output, width=525, capture=f'06-volume-{output.lower()}')
        app.check(True, f'unnamed volume layer appeared on the pointer output {output}')
        app.gone(output)
        app.tap('mic_mute')
        app.plate(output=output, capture=f'06-mic-{output.lower()}')
        app.check(True, f'unnamed microphone layer appeared on the pointer output {output}')
        app.gone(output)
    app.goto(LEFT, W // 2, H // 2)
    app.tap('brightness_up')
    app.plate(output=RIGHT, width=525, capture='06-brightness-edp')
    app.check(True, f'brightness appeared on named laptop output {RIGHT} with the pointer on {LEFT}')


def test7(app):
    app.start()
    app.tap('volume_up')
    app.plate(width=525, capture='07-default')
    app.check(not SETTINGS.exists(), 'no file gives 525 x 90 at top centre, 24 px from the top')
    app.gone()
    for size, scale in (('small', 2), ('large', 4)):
        settings(**{'indicator-place': 'bottom', 'indicator-size': size})
        app.tap('volume_down')
        app.plate(width=175 * scale, scale=scale, place='bottom', capture=f'07-bottom-{size}')
        app.check(True, f'{size} from the file gives {175 * scale} x {30 * scale} with {64 * scale} px bottom clearance')
        app.gone()
    SETTINGS.write_text('{')
    mark = len(app.log())
    app.tap('volume_up')
    app.plate(width=525, capture='07-broken-default')
    messages = [line for line in app.log()[mark:].splitlines() if line.startswith('aresos-settings: ')]
    app.check(len(messages) == 1, f'broken JSON gave default geometry and one line: {messages}')
    app.gone()

    settings(**{'indicator-place': 'top', 'indicator-size': 'medium'})
    for name, value, size, scale, place in (
        ('indicator-place', 'bottom', 525, 3, 'bottom'),
        ('indicator-size', 'large', 700, 4, 'bottom'),
    ):
        mark = len(calls())
        old = state()['sink']
        run('/usr/libexec/aresos-settings', 'set', name, value, env=app.env)
        crop, _ = app.plate(width=size, scale=scale, place=place, capture=f'07-preview-{name}')
        pixels.exact(crop, pixels.level(round(old['volume'] * 100)), scale)
        idle_keys()
        preview_calls = calls()[mark:]
        app.check(state()['sink'] == old and len(preview_calls) == 1 and preview_calls[0]['argv'] == [
            'get-volume', '@DEFAULT_AUDIO_SINK@'], f'set {name} previewed the current volume with one read and no change')
        app.gone()

    references = []
    for look in 'ABC':
        settings(look=look)
        reset_devices(sink=dict(volume=0.67, mute=False))
        app.tap('volume_down')
        image, _ = app.plate(width=525, capture=f'07-looks-{look.lower()}')
        references.append(image.tobytes())
        if look != 'C':
            app.gone()
    app.check(references.count(references[0]) == 3, 'settings A, B and C produced identical Look A pixels')


def test8(app):
    app.start()
    for size, scale in (('small', 2), ('medium', 3), ('large', 4)):
        for label, test_label in (('Speakers', 'speakers'), ('Headphones', 'headphones'), ('Ж', 'fallback')):
            reset_devices(sink=dict(volume=0.67, mute=False))
            graph(label)
            settings(**{'indicator-size': size})
            app.tap('volume_down')
            crop, _ = app.plate(width=175 * scale, scale=scale, capture=f'08-{scale}x-{test_label}')
            if label == 'Ж':
                ink = pixels.fallback(crop, scale)
                app.check(True, f'{scale}x Cyrillic fallback: {ink} foreground pixels in the pack ink colour')
            else:
                shifts = pixels.exact(crop, pixels.level(62, label), scale)
                app.check(True, f'{scale}x {label}: all opaque pixels match, glyph shifts {shifts or "none"}')
            app.gone()


def cold(app, repeat_mode):
    mark = app.launches()
    reset_devices(sink=dict(volume=1.0, mute=False))
    start = time.monotonic()
    if repeat_mode:
        app.key('volume_down', True)
    else:
        app.tap('volume_down')
        app.tap('volume_down')
    app.plate(width=525, capture='09-cold-held' if repeat_mode else '09-cold-pair')
    latency = time.monotonic() - start
    if repeat_mode:
        time.sleep(max(0, start + 0.91 - time.monotonic()))
        app.key('volume_down', False)
    idle_keys()
    final = round(state()['sink']['volume'] * 100)
    assert final <= 90, f'only one key action from cold, final {final}%'
    expect_level(app, final)
    app.check(app.launches() - mark == 1 and len(processes(INDICATOR)) == 1,
              f'{("held key" if repeat_mode else "two quick presses")} from cold: one start line, one process, '
              f'first visible frame within {latency * 1000:.0f} ms of the first press, final {final}%')


def check_reap_order(app, trace, launch_lock, child):
    # Match the notifier that opened the launch file and the descriptor flock actually locked.
    # Other processes close inherited copies of the same descriptor.
    lines = trace.read_text()
    lock_fd = rf'\d+<{re.escape(str(launch_lock))}>'
    notifier = re.search(rf'(?m)^(\d+) +\S+ openat\(.* = {lock_fd}$', lines)
    acquired = re.search(rf'(?m)\bflock\(({lock_fd}), LOCK_EX\) += 0$', lines)
    assert notifier and acquired, f'missing launch lock acquisition in {trace.name}'
    fd = re.escape(acquired[1])
    prefix = rf'^{notifier[1]} +\S+ '
    reap = re.search(rf'(?m){prefix}wait4\(.* = {child}$', lines)
    release = re.search(rf'(?m)(?:{prefix}close\({fd}\)|\bflock\({lock_fd}, LOCK_UN\)) += 0$', lines)
    assert reap and release, f'missing reap of PID {child} or launch lock release in {trace.name}'
    app.check(reap.start() < release.start(),
              f'PID {child} must be reaped before the launch lock is released in {trace.name}')


def test9(app):
    app.start(idle=2350)
    cold(app, False)
    until(lambda: not has_owner() and not processes(INDICATOR), 'idle exit', timeout=3)
    app.check(True, 'the program exited after the shortened idle interval and released its name')
    cold(app, True)
    show(1002, 'show-volume', '65')
    expect_level(app, 65)
    show(1001, 'show-volume', '25')
    time.sleep(0.20)
    crop, _ = app.plate(width=525, capture='09-newer-wins')
    app.check(rendered_level(crop) == 65, 'newer 65% survived the older 25% Show delivered afterwards')
    app.stop()

    trace = EV / '09-launch.strace'
    config = RUNTIME / 'traced-labwc'
    config.mkdir()
    binding = f'{LEVEL} volume-down'
    rc = (CONFIG / 'labwc/rc.xml').read_text()
    (config / 'rc.xml').write_text(rc.replace(binding, f'/usr/bin/strace -f -ttt -y -z '
                                              f'-e trace=openat,flock,close,wait4 -o {trace} {binding}', 1))
    app.start(delay=6500, config=config)
    reset_devices(sink=dict(volume=1.0, mute=False))
    mark = len(app.log())
    launches = app.launches()
    start = time.monotonic()
    app.tap('volume_down')
    until(lambda: 'waiting before taking the bus name (test)' in app.log()[mark:], 'delayed program pre-registration')
    first, = processes(INDICATOR)
    app.check(state()['sink']['volume'] == 0.95 and not has_owner(),
              'the key changed the level while the delayed program was waiting to register')
    launch_lock = RUNTIME / 'aresos-indicator.launch'
    with launch_lock.open() as handle:
        # Be the sole waiter so a second notifier cannot hide the first lock handoff.
        fd = handle.fileno()
        subprocess.run(['/usr/bin/flock', '-w', '7', str(fd)], pass_fds=(fd,), check=True, timeout=8)
        elapsed = time.monotonic() - start
        assert 5.0 <= elapsed < 5.5, f'launch lock handed off after {elapsed:.3f} s, expected 5.0–5.5 s'
    idle_keys()
    timed = app.log()[mark:].count('did not take its bus name within 5 s and was ended')
    app.check(app.launches() - launches == timed == 1 and not has_owner() and not processes(INDICATOR)
              and not app.frame(LEFT)[1],
              f'one termination, lock handed off after {elapsed:.3f} s with no survivor, owner or plate')
    check_reap_order(app, trace, launch_lock, first)


def check_bus():
    address = os.environ['DBUS_SESSION_BUS_ADDRESS']
    assert address.startswith(f'unix:path={RUNTIME}/'), 'session bus outside the scratch runtime'
    assert Path(address.split(',', 1)[0].removeprefix('unix:path=')).is_socket()
    assert not has_owner()
    print('PASS private dbus-run-session bus in the scratch runtime', flush=True)


def main():
    check_bus()
    failed = False
    for number, test in enumerate((test1, test2, test3, test4, test5, test6, test7, test8, test9), 1):
        SETTINGS.unlink(missing_ok=True)
        (STANDINS / 'calls.jsonl').unlink(missing_ok=True)
        reset_devices()
        graph(None)
        app = Session(number)
        try:
            with app:
                test(app)
        except PlacementError as error:
            print(f'STOP test {number} after {app.count} checks: {error}', flush=True)
            return 2
        except Exception:
            failed = True
            print(f'FAIL test {number} after {app.count} checks:\n{traceback.format_exc()}', flush=True)
        else:
            print(f'PASS test {number}: {app.count} checks', flush=True)
    return int(failed)


if __name__ == '__main__':
    with (EV / 'results.txt').open('w') as output:
        sys.stdout = output
        sys.exit(main())
