"""Package 320: run aresos-level and aresos-settings against stand-ins at the image's absolute paths.

Every run happens in a private user, mount and PID namespace (unshare, which CI's runner allows once its AppArmor
switch is off): /usr/bin gets an overlay with stand-in brightnessctl and wpctl, /usr/libexec a tmpfs with the branch's
programs and a stand-in indicator, and /run and /sys/class are hidden, so the owner's session bus, Wayland socket,
system bus and backlight are out of reach. The real device tools never run: the setup refuses to go on unless both
names in /usr/bin are the stand-ins. Each run has a scratch HOME and XDG_RUNTIME_DIR and its own dbus-run-session,
and every process it left ends with the namespace.
"""
import functools
import json
import os
import pathlib
import shutil
import signal
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIBEXEC = ROOT / 'os/config/usr/libexec'
MARK = 'ARESOS-TEST-STAND-IN'

BACKLIGHT = {'class': 'backlight', 'id': 'intel_backlight', 'cur': 48000, 'max': 96000}
LED = {'class': 'leds', 'id': 'input3::capslock', 'cur': 0, 'max': 1}

BRIGHTNESSCTL = r'''#!/usr/bin/python3 -IS
# ARESOS-TEST-STAND-IN: brightnessctl 0.5.1's options, operations and output (its brightnessctl.c), with the devices
# in a state file. Rounding as roundf; exponent 1; --min-value as atol (raw units); no class means every device.
import fcntl, json, math, os, re, sys, time
D = os.environ['STANDIN_DIR']
args = sys.argv[1:]
with open(D + '/calls.jsonl', 'a') as log:
    log.write(json.dumps({'tool': sys.argv[0], 'argv': args, 't': time.monotonic()}) + '\n')
with open(D + '/state.json') as f:
    if any(' '.join(['brightnessctl'] + args).startswith(h) for h in json.load(f).get('hang', [])):
        time.sleep(60)
quiet = mach = False
cls, minimum, ops = None, 0, []
for a in args:
    if a in ('-q', '--quiet'): quiet = True
    elif a in ('-m', '--machine-readable'): mach = True
    elif a.startswith('--class='): cls = a[8:]
    elif a.startswith('--min-value='): minimum = int(re.match(r'-?\d*', a[12:]).group() or 0)
    elif a in ('-n', '--min-value'): minimum = 1
    elif a.startswith('-'): sys.exit('Usage: brightnessctl [options] [operation] [value]')
    else: ops.append(a)
with open(D + '/state.json', 'r+') as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    state = json.load(f)
    devices = [d for d in state['devices'] if cls is None or d['class'] == cls]
    if not devices:
        sys.exit(f"Failed to read any devices of class '{cls}'.\n" if cls else 'Failed to read any devices.\n')
    d = devices[0]
    def info():
        pct = int(math.floor(d['cur'] / d['max'] * 100 + 0.5))
        if mach: print(f"{d['id']},{d['class']},{d['cur']},{pct}%,{d['max']}")
        else: print(f"Device '{d['id']}' of class '{d['class']}':\n\tCurrent brightness: {d['cur']} ({pct}%)\n"
                    f"\tMax brightness: {d['max']}\n")
    op = ops[0][0] if ops else 'i'
    if op == 'm': print(d['max'])
    elif op == 'g': print(d['cur'])
    elif op == 's':
        m = re.fullmatch(r'([+-]?)(\d+)(%?)([+-]?)', ops[1] if len(ops) > 1 else '')
        if not m: sys.exit('Invalid value given')
        sign = m.group(1) or m.group(4)
        val, percent = int(m.group(2)), m.group(3) == '%'
        to_val = lambda p: int(math.floor(p / 100 * d['max'] + 0.5)) if p >= 0 else -int(math.floor(-p / 100 * d['max'] + 0.5))
        if not sign:
            new = to_val(val) if percent else val
        else:
            mod = -val if sign == '-' else val
            if percent:
                mod = to_val(d['cur'] / d['max'] * 100 + mod) - d['cur']
                if val and not mod: mod = 1 if sign == '+' else -1
            new = d['cur'] + mod
        d['cur'] = min(max(new, minimum, 0), d['max'])
        f.seek(0); f.truncate(); json.dump(state, f); f.flush()
        if not quiet: info()
    else: info()
'''

WPCTL = r'''#!/usr/bin/python3 -IS
# ARESOS-TEST-STAND-IN: wpctl's get-volume, set-volume and set-mute as WirePlumber 0.5's wpctl.c prints and computes
# them (a delta adds to the volume, below 0 is 0, --limit caps; no default node is a "Translate ID error").
import fcntl, json, os, re, sys, time
D = os.environ['STANDIN_DIR']
args = sys.argv[1:]
with open(D + '/calls.jsonl', 'a') as log:
    log.write(json.dumps({'tool': sys.argv[0], 'argv': args, 't': time.monotonic()}) + '\n')
with open(D + '/state.json') as f:
    if any(' '.join(['wpctl'] + args).startswith(h) for h in json.load(f).get('hang', [])):
        with open(D + '/read-blocked', 'w') as ready:
            print(os.getpid(), file=ready)
        time.sleep(60)
limit = 0.0
if '--limit' in args:
    i = args.index('--limit'); limit = float(args[i + 1]); del args[i:i + 2]
nodes = {'@DEFAULT_AUDIO_SINK@': 'sink', '@DEFAULT_AUDIO_SOURCE@': 'source'}
with open(D + '/state.json', 'r+') as f:
    fcntl.flock(f, fcntl.LOCK_EX)
    state = json.load(f)
    node = state.get(nodes.get(args[1])) if len(args) > 1 else None
    if node is None:
        sys.stderr.write("Translate ID error: '-1' is not a valid ID (returned by default-nodes-api)\n\n")
        sys.exit(0 if args[0] == 'get-volume' else 3)
    if args[0] == 'get-volume':
        print('Volume: %.2f%s' % (node['volume'], ' [MUTED]' if node['mute'] else ''))
    elif args[0] == 'set-volume':
        m = re.fullmatch(r'(\d*\.?\d*)(%?)([-+]?)', args[2])
        vol = float(m.group(1)) / (100 if m.group(2) else 1)
        if m.group(3) == '-': vol = -vol
        if m.group(3): vol += node['volume']
        vol = max(vol, 0.0)
        if limit > 0 and vol > limit: vol = limit
        node['volume'] = round(vol, 6)
    elif args[0] == 'set-mute':
        node['mute'] = (not node['mute']) if args[2] == 'toggle' else args[2] == '1'
    f.seek(0); f.truncate(); json.dump(state, f); f.flush()
'''

INDICATOR = r'''#!/usr/bin/python3 -I
# ARESOS-TEST-STAND-IN: the indicator's bus side only. It notes its start (arguments, LD_PRELOAD, open files) and
# every Show; 'crash' exits at once, 'never-own' never takes the name, 'serve' owns aresos.indicator and answers
# (or not, with silent), after own_delay seconds, and ends after idle seconds without a call.
import json, os, signal, sys, time
D = os.environ['STANDIN_DIR']
cfg = json.load(open(D + '/indicator.json'))
def note(kind, **fields):
    with open(D + '/indicator.jsonl', 'a') as log:
        log.write(json.dumps({'kind': kind, 'pid': os.getpid(), 't': time.monotonic(), **fields}) + '\n')
files = []
for fd in os.listdir('/proc/self/fd'):
    try: files.append(os.readlink('/proc/self/fd/' + fd))
    except OSError: pass
note('start', argv=sys.argv[1:], preload=os.environ.get('LD_PRELOAD'), files=files)
def term(*_):
    note('term'); os._exit(0)
signal.signal(signal.SIGTERM, term)
if cfg['mode'] == 'crash':
    sys.exit(3)
if cfg['mode'] == 'never-own':
    while True: time.sleep(1)
import gi
gi.require_version('Gio', '2.0')
from gi.repository import Gio, GLib
seq, action, reading = sys.argv[1:4]
note('show', sequence=int(seq), action=action, reading=reading, via='argv')
XML = ('<node><interface name="aresos.Indicator"><method name="Show"><arg name="sequence" type="t" direction="in"/>'
       '<arg name="action" type="s" direction="in"/><arg name="reading" type="s" direction="in"/></method>'
       '</interface></node>')
last, held, loop = [time.monotonic()], [], GLib.MainLoop()
bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
time.sleep(cfg.get('own_delay', 0))
def call(connection, sender, path, interface, method, parameters, invocation):
    s, a, r = parameters.unpack()
    note('show', sequence=s, action=a, reading=r, via='bus')
    last[0] = time.monotonic()
    if cfg.get('silent'): held.append(invocation)
    else: invocation.return_value(None)
bus.register_object('/aresos/indicator', Gio.DBusNodeInfo.new_for_xml(XML).interfaces[0], call, None, None)
def acquired(*_): note('owned')
def lost(*_): note('lost'); loop.quit()
Gio.bus_own_name_on_connection(bus, 'aresos.indicator', Gio.BusNameOwnerFlags.DO_NOT_QUEUE, acquired, lost)
def idle():
    if time.monotonic() - last[0] > cfg.get('idle', 20): loop.quit()
    return True
GLib.timeout_add(100, idle)
loop.run()
note('exit')
'''

LEVEL = '''#!/usr/bin/bash
# ARESOS-TEST-STAND-IN: records how aresos-settings called aresos-level.
printf '%s\\n' "$*" >> "$STANDIN_DIR/level.log"
'''

SETUP = r'''set -euo pipefail
S=$1
mount -t tmpfs -o mode=0755 pkg320 "$S/mnt"
mkdir "$S/mnt/bin" "$S/mnt/bin.work"
cp -p "$S/standins/brightnessctl" "$S/standins/wpctl" "$S/mnt/bin/"
mount -t overlay pkg320-bin -o "lowerdir=/usr/bin,upperdir=$S/mnt/bin,workdir=$S/mnt/bin.work,userxattr" /usr/bin
if [[ -e $S/lib/libgtk4-layer-shell.so.0 ]]; then
    mkdir "$S/mnt/lib" "$S/mnt/lib.work"
    cp -p "$S/lib/libgtk4-layer-shell.so.0" "$S/mnt/lib/"
    mount -t overlay pkg320-lib -o "lowerdir=/usr/lib64,upperdir=$S/mnt/lib,workdir=$S/mnt/lib.work,userxattr" /usr/lib64
fi
mount -t tmpfs -o mode=0755 pkg320-libexec /usr/libexec
cp -p "$S"/libexec/* /usr/libexec/ 2> /dev/null || true
mount -t tmpfs pkg320-run /run
mount -t tmpfs pkg320-sys /sys/class
# The gate: nothing runs unless both device tools are the stand-ins.
grep -q ARESOS-TEST-STAND-IN /usr/bin/brightnessctl
grep -q ARESOS-TEST-STAND-IN /usr/bin/wpctl
exec /usr/bin/dbus-run-session --config-file="$S/bus.conf" --dbus-daemon=/usr/bin/dbus-daemon -- \
    /usr/bin/bash "$S/scenario.sh"
'''

# Helpers every scenario can use. settle waits until no key script or notifier runs.
PRELUDE = r'''L=/usr/libexec/aresos-level
R=$XDG_RUNTIME_DIR
now() { local t=$EPOCHREALTIME; echo $((10#${t//[.,]/} / 1000)); }
settle() {
    local end=$((SECONDS + ${1:-20}))
    while /usr/bin/pgrep -f /usr/libexec/aresos-level > /dev/null; do
        if ((SECONDS >= end)); then echo SETTLE-TIMEOUT; return 1; fi
        /usr/bin/sleep 0.05
    done
}
mark() { printf '{"mark": "%s"}\n' "$1" >> "$STANDIN_DIR/calls.jsonl"; }
alive() {
    local p
    for p in $(/usr/bin/pgrep -f /usr/libexec/aresos-indicator); do
        /usr/bin/grep -q '^State:.*Z' "/proc/$p/status" 2> /dev/null || echo "ALIVE $p"
    done
}
'''

BUS = '''<busconfig>
  <type>session</type>
  <listen>unix:tmpdir={runtime}</listen>
  <policy context="default"><allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/></policy>
</busconfig>
'''


def short_tmp():
    # A bus socket path must stay under 108 bytes, and /run is hidden in the namespace.
    for base in ('/tmp', '/var/tmp', tempfile.gettempdir()):
        if os.path.isdir(base) and os.access(base, os.W_OK) and not base.startswith(('/run', '/sys', '/usr')):
            return pathlib.Path(tempfile.mkdtemp(prefix='pkg320-', dir=base))
    raise RuntimeError('no short writable temporary folder')


def find_libm():
    for path in ('/usr/lib64/libm.so.6', '/lib/x86_64-linux-gnu/libm.so.6', '/usr/lib/x86_64-linux-gnu/libm.so.6'):
        if os.path.isfile(path):
            return path
    return None


class Sandbox:
    """One scratch tree; run() may be called several times, each in a fresh namespace and bus."""

    def __init__(self, *, devices=(BACKLIGHT, LED), sink=None, source=None, hang=(), indicator=None,
                 level='real', settings=True, layer_library=False):
        """indicator: None (missing), 'not-executable', 'crash', 'never-own', or a dict for 'serve' with
        own_delay, silent and idle. level: 'real', 'stand-in' or None."""
        self.path = short_tmp()
        self.state_dir = self.path / 'state'
        self.home = self.path / 'home'
        self.runtime = self.path / 'run'
        for folder in (self.state_dir, self.home, self.path / 'mnt', self.path / 'standins', self.path / 'libexec'):
            folder.mkdir()
        self.runtime.mkdir(mode=0o700)
        (self.path / 'bus.conf').write_text(BUS.format(runtime=self.runtime))
        (self.path / 'setup.sh').write_text(SETUP)
        self.write_state(devices=list(devices), sink={'volume': 0.40, 'mute': False} if sink is None else sink,
                         source={'volume': 1.0, 'mute': False} if source is None else source, hang=list(hang))
        for name, text in (('brightnessctl', BRIGHTNESSCTL), ('wpctl', WPCTL)):
            self.put(self.path / 'standins' / name, text)
        libexec = self.path / 'libexec'
        if level == 'real':
            shutil.copy(LIBEXEC / 'aresos-level', libexec / 'aresos-level')
            (libexec / 'aresos-level').chmod(0o755)
        elif level == 'stand-in':
            self.put(libexec / 'aresos-level', LEVEL)
        if settings:
            shutil.copy(LIBEXEC / 'aresos-settings', libexec / 'aresos-settings')
            (libexec / 'aresos-settings').chmod(0o755)
        if indicator is not None:
            mode = indicator if isinstance(indicator, str) else 'serve'
            config = dict(indicator) if isinstance(indicator, dict) else {}
            config['mode'] = 'crash' if mode == 'not-executable' else mode
            (self.state_dir / 'indicator.json').write_text(json.dumps(config))
            self.put(libexec / 'aresos-indicator', INDICATOR, mode=0o644 if mode == 'not-executable' else 0o755)
        if layer_library:
            (self.path / 'lib').mkdir()
            shutil.copy(find_libm(), self.path / 'lib/libgtk4-layer-shell.so.0')

    @staticmethod
    def put(path, text, mode=0o755):
        path.write_text(text)
        path.chmod(mode)

    def write_state(self, **state):
        (self.state_dir / 'state.json').write_text(json.dumps(state))

    def state(self):
        return json.loads((self.state_dir / 'state.json').read_text())

    def calls(self):
        """The device tools' calls as 'path argv…' strings, with {'mark': name} rows kept as '== name'."""
        path = self.state_dir / 'calls.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [f"== {row['mark']}" if 'mark' in row else ' '.join([row['tool'], *row['argv']]) for row in rows]

    def events(self, kind=None):
        path = self.state_dir / 'indicator.jsonl'
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        return [row for row in rows if kind is None or row['kind'] == kind]

    def run(self, scenario, timeout=90, env=None):
        (self.path / 'scenario.sh').write_text(PRELUDE + scenario)
        environment = {'PATH': '/usr/bin:/bin', 'HOME': str(self.home), 'XDG_RUNTIME_DIR': str(self.runtime),
                       'STANDIN_DIR': str(self.state_dir), 'LANG': 'C.UTF-8',
                       'DBUS_SYSTEM_BUS_ADDRESS': 'unix:path=/nonexistent/system_bus_socket', **(env or {})}
        process = subprocess.Popen(
            ['/usr/bin/unshare', '--user', '--map-root-user', '--mount', '--propagation', 'private', '--pid',
             '--fork', '--mount-proc', '--kill-child', '/usr/bin/bash', str(self.path / 'setup.sh'), str(self.path)],
            env=environment, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True)
        try:
            out, err = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            out, err = process.communicate()
            raise AssertionError(f'the scenario did not end in {timeout} s\n{out}\n{err}')
        return subprocess.CompletedProcess(process.args, process.returncode, out, err)

    def close(self):
        shutil.rmtree(self.path, ignore_errors=True)


@functools.lru_cache(maxsize=None)
def unavailable():
    """Why the sandbox cannot run here, or None."""
    for tool in ('/usr/bin/unshare', '/usr/bin/dbus-run-session', '/usr/bin/dbus-daemon', '/usr/bin/flock',
                 '/usr/bin/timeout', '/usr/bin/setsid', '/usr/bin/pgrep', '/usr/bin/gdbus', '/usr/bin/python3'):
        if not os.access(tool, os.X_OK):
            return f'{tool} is missing'
    box = Sandbox(level=None, settings=False)
    try:
        result = box.run('echo READY\n', timeout=30)
    finally:
        box.close()
    if result.returncode != 0 or 'READY' not in result.stdout:
        return f'the private namespace did not start: {result.stderr.strip()[-300:]}'
    return None


@functools.lru_cache(maxsize=None)
def gio_missing():
    """Why the stand-in indicator cannot serve the bus here (PyGObject's Gio for /usr/bin/python3), or None."""
    result = subprocess.run(['/usr/bin/python3', '-I', '-c', 'import gi; gi.require_version("Gio", "2.0"); '
                             'from gi.repository import Gio'], capture_output=True)
    return None if result.returncode == 0 else 'PyGObject (Gio) is missing for /usr/bin/python3'
