"""The install proof on a real Chrome (brief 18c-b, item 2).

Runs as root in the CI container of control/chrome/ci/Dockerfile and nowhere
else. It lays the browser side out as the image does (the four files under
/usr/share/aresos/chrome, the two links in /etc, the real launcher), starts
CI's stand-in service and the pinned Chrome the way browser.mjs starts it
(sandbox on, no debugging port, no --load-extension), and asks Chrome
questions through a probe extension and its own native host.

Five cases, each with its PASS line; the last line is
CONTROL_CHROME_INSTALL_PROOF_PASSED. Evidence goes to /out/install.
"""
import grp
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import pwd
import re
import shutil
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
import traceback

if sys.platform != 'linux' or os.environ.get('GITHUB_ACTIONS') != 'true' or not Path('/.dockerenv').exists() or os.geteuid() != 0:
    raise SystemExit('The install proof runs only as root in a GitHub Linux container')

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path[:0] = [str(ROOT / 'control/chrome/packaging'), str(HERE), str(ROOT / 'control')]
import netlog
import pack
from aresos_control.chrome.exclusions import SETTING

OWNER, TOOLS = 'owner', 'aresos-tools'
OUT = Path('/out/install')
WORK = Path('/var/lib/aresos-install-test')
RUN = Path('/run/aresos-install-test')
# The image's layout ("Agree" in the brief).
BUNDLE = Path('/usr/share/aresos/chrome')
NAMES = ('extension.crx', 'update.xml', 'policy.json', 'native-host.json')
POLICIES = Path('/etc/opt/chrome/policies/managed')
HOSTS = Path('/etc/opt/chrome/native-messaging-hosts')
HOST_MANIFEST = HOSTS / 'org.aresos.chrome.json'
LINKS = {POLICIES / 'aresos.json': '/usr/share/aresos/chrome/policy.json',
         HOST_MANIFEST: '/usr/share/aresos/chrome/native-host.json'}
LAUNCHER = Path('/usr/libexec/aresos-control/chrome')
HOST_PROCESS = '/usr/libexec/aresos-control/chrome/native_host.py'
# Test only: the probe, its own file: address, its own policy file and host.
PROBE_FILES = Path('/usr/share/aresos-install-test/probe')
PROBE_HOST = Path('/usr/libexec/aresos-install-test/probe-host')
PROBE_NAME = 'org.aresos.install_probe'
PROBE_POLICY = POLICIES / 'aresos-install-probe.json'
PORT = 18766
ADDRESS = f'http://localhost:{PORT}'
# As browser.mjs starts Chrome, without its fixture host rule.
CHROME_FLAGS = ['--no-first-run', '--no-default-browser-check', '--password-store=basic', '--start-maximized',
                '--gtk-version=3', '--enable-logging=stderr', '--disable-background-mode']
NEVER = ('--no-sandbox', '--remote-debugging', '--load-extension', '--disable-extensions-except')
REFUSED = 'Access to the specified native messaging host is forbidden.'
CANNOT_MODIFY = 'cannot be modified by user'
STARTED = time.monotonic()


class Failure(Exception):
    """A check of the proof did not hold."""


def log(*parts):
    print(f'[proof {time.monotonic() - STARTED:7.1f}s]', *parts, flush=True)


def expect(condition, message):
    if not condition:
        raise Failure(message)


def eventually(check, label, timeout=30, interval=0.2):
    end, error = time.monotonic() + timeout, None
    while True:
        try:
            value = check()
            if value:
                return value
        except Failure as caught:
            error = caught
        if time.monotonic() > end:
            raise Failure(f'{label}: not within {timeout}s' + (f' ({error})' if error else ''))
        time.sleep(interval)


def account(name):
    entry = pwd.getpwnam(name)
    return {'user': entry.pw_uid, 'group': entry.pw_gid, 'extra_groups': []}


def owner_environment():
    return {'HOME': '/home/owner', 'USER': OWNER, 'LOGNAME': OWNER, 'LANG': 'C.UTF-8', 'GITHUB_ACTIONS': 'true',
            'PATH': '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'}


def origin(bundle):
    return f"chrome-extension://{bundle['id']}/"


def extension_folders(profile):
    """The extension IDs Chrome keeps unpacked in this profile."""
    folder = profile / 'Default/Extensions'
    return sorted(entry.name for entry in folder.iterdir() if re.fullmatch('[a-p]{32}', entry.name)) if folder.is_dir() else []


def preference_ids(profile):
    """The extension IDs in the profile's preference files, read after Chrome has exited."""
    found = set()
    for name in ('Preferences', 'Secure Preferences'):
        try:
            data = json.loads((profile / 'Default' / name).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        found |= set((data.get('extensions') or {}).get('settings') or {})
    return found


def host_processes():
    """(pid, parent, uid) of every running copy of our native host."""
    listing = subprocess.run(['ps', '-eo', 'pid=,ppid=,uid=,args='], capture_output=True, text=True, check=True).stdout
    return [tuple(map(int, line.split()[:3])) for line in listing.splitlines() if HOST_PROCESS in line]


def service_peers():
    """The connections the kernel shows on the service's chrome.sock."""
    listing = subprocess.run(['ss', '-x', '-a', '-n'], capture_output=True, text=True, check=True).stdout
    return [line for line in listing.splitlines() if '/run/aresos-tools/chrome.sock' in line and 'ESTAB' in line]


class Pages:
    """The test's own server: the probe's update address and an ordinary page."""

    def __init__(self, probe):
        self.hits, self.lock = [], threading.Lock()
        update = ('<?xml version="1.0" encoding="UTF-8"?>\n<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">'
                  f'<app appid="{probe["id"]}"><updatecheck codebase="{ADDRESS}/probe/extension.crx" version="{probe["version"]}" />'
                  '</app></gupdate>\n').encode()
        pages = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_):
                pass

            def do_GET(self):
                with pages.lock:
                    pages.hits.append((time.monotonic(), self.path))
                if self.path.startswith('/probe/update.xml'):
                    body, kind = update, 'application/xml'
                elif self.path.startswith('/browse'):
                    body, kind = b'<!doctype html><title>Install proof</title><p>An ordinary page.</p>', 'text/html'
                else:
                    self.send_error(404)
                    return
                self.send_response(200)
                self.send_header('Content-Type', kind)
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.end_headers()
                self.wfile.write(body)

        self.server = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def seen(self, text, since=0.0):
        with self.lock:
            return [path for at, path in self.hits if at >= since and text in path]


class ProbeLink:
    """The check's end of the probe's native host: questions out, answers back."""

    def __init__(self):
        path = RUN / 'probe.sock'
        self.server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server.bind(str(path))
        os.chmod(path, 0o666)
        self.server.listen(8)
        self.state = threading.Condition()
        self.connection = self.greeting = None
        self.replies, self.counter = {}, 0
        threading.Thread(target=self._accept, daemon=True).start()

    def _accept(self):
        while True:
            connection, _ = self.server.accept()
            threading.Thread(target=self._read, args=(connection,), daemon=True).start()

    def _read(self, connection):
        buffer = b''
        try:
            while True:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                buffer += chunk
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    message = json.loads(line)
                    with self.state:
                        if message.get('event') == 'hello':
                            self.connection, self.greeting = connection, message
                        elif 'id' in message:
                            self.replies[message['id']] = message
                        self.state.notify_all()
        except (OSError, ValueError):
            pass
        finally:
            with self.state:
                if self.connection is connection:
                    self.connection = self.greeting = None
                self.state.notify_all()
            connection.close()

    def hello(self):
        with self.state:
            return self.greeting

    def call(self, operation, timeout=15, **arguments):
        with self.state:
            if self.connection is None:
                raise Failure(f'the probe is not connected (asking {operation})')
            self.counter += 1
            identity = self.counter
            self.connection.sendall(json.dumps({'id': identity, 'op': operation, 'args': arguments}).encode() + b'\n')
            end = time.monotonic() + timeout
            while identity not in self.replies:
                remaining = end - time.monotonic()
                if remaining <= 0 or self.connection is None:
                    raise Failure(f'the probe did not answer {operation}')
                self.state.wait(remaining)
            return self.replies.pop(identity)


class Chrome:
    def __init__(self, session, profile, label, number, extra, url):
        self.profile, self.label = profile, label
        self.arguments = [f'--user-data-dir={profile}', *CHROME_FLAGS, *extra, url]
        expect(not any(argument.startswith(NEVER) for argument in self.arguments), 'a forbidden Chrome flag')
        self.log_path = OUT / f'chrome-{number:02d}-{label}.txt'
        self.log = open(self.log_path, 'wb')
        self.started = time.monotonic()
        self.process = subprocess.Popen(['qualification-chrome', *self.arguments], **account(OWNER), env=session, cwd='/home/owner',
                                        stdin=subprocess.DEVNULL, stdout=self.log, stderr=subprocess.STDOUT)


class Proof:
    def __init__(self):
        self.chrome = self.service = self.session = None
        self.launches = 0
        self.results, self.setup = {}, {}
        self.install_seconds = 10.0

    # --- setup -------------------------------------------------------------------------------------------------

    def prepare(self):
        os.chmod('/out', 0o777)
        OUT.mkdir(parents=True, exist_ok=True)
        os.chmod(OUT, 0o777)
        for folder in (WORK, RUN, WORK / 'profiles'):
            folder.mkdir(parents=True, exist_ok=True)
            os.chmod(folder, 0o755)
        shutil.chown(WORK / 'profiles', OWNER, OWNER)
        lock = json.loads((HERE / 'chrome.lock.json').read_text())
        version = subprocess.run(['qualification-chrome', '--version'], capture_output=True, text=True, check=True).stdout.strip()
        log('Chrome:', version)
        expect(version.split()[-1] == lock['version'], f"the container's Chrome is {version}, the pin says {lock['version']}")
        # "No network": no address but loopback's and no default route (the workflow runs the container with --network none).
        show = lambda *arguments: subprocess.run(['ip', *arguments], capture_output=True, text=True, check=True).stdout
        self.setup = {'chrome': version, 'addresses_on': sorted({line.split()[1] for line in show('-o', 'addr', 'show').splitlines()}),
                      'default_routes': (show('route', 'show', 'default') + show('-6', 'route', 'show', 'default')).split()}
        # The real launcher and relay, as the image installs them (the base container writes a shorter launcher).
        LAUNCHER.mkdir(parents=True, exist_ok=True)
        for source, name, mode in ((ROOT / 'control/chrome/packaging/host', 'host', 0o755),
                                   (ROOT / 'control/chrome/native_host.py', 'native_host.py', 0o644)):
            shutil.copyfile(source, LAUNCHER / name)
            os.chmod(LAUNCHER / name, mode)
        # A valid made-up list where the service reads it: root's file, the service's group may read.
        setting = Path(SETTING)
        setting.parent.mkdir(parents=True, exist_ok=True)
        os.chmod(setting.parent, 0o755)
        setting.write_text(json.dumps({'format': 1, 'hosts': ['excluded.invalid']}))
        os.chown(setting, 0, grp.getgrnam(TOOLS).gr_gid)
        os.chmod(setting, 0o640)
        for folder in (POLICIES, HOSTS, BUNDLE):
            folder.mkdir(parents=True, exist_ok=True)
        for link, target in LINKS.items():
            os.symlink(target, link)
        # Three bundles of the same sources, each from one call of pack.py as the image build makes it.
        self.bundles = {name: self.pack(name) for name in 'abc'}
        expect(len({bundle['id'] for bundle in self.bundles.values()}) == 3, 'three calls of pack.py give three IDs')
        self.probe = self.make_probe()
        (OUT / 'bundles.json').write_text(json.dumps({'probe': self.probe['id'], **{
            name: {key: bundle[key] for key in ('id', 'version', 'public_key_sha256', 'crx_sha256')} for name, bundle in self.bundles.items()}}, indent=1))
        self.pages = Pages(self.probe)
        self.link = ProbeLink()
        self.start_service()
        self.start_session()

    def pack(self, name):
        folder = WORK / 'bundles' / name
        done = subprocess.run([sys.executable, '-I', '-B', str(ROOT / 'control/chrome/packaging/pack.py'),
                               str(ROOT / 'control/chrome/extension'), str(folder)], capture_output=True, text=True)
        expect(done.returncode == 0, 'pack.py failed: ' + done.stderr[-400:])
        record = json.loads(done.stdout)
        log('bundle', name, record['id'])
        return {'name': name, 'folder': folder, **record}

    def make_probe(self):
        manifest = json.loads((HERE / 'probe/manifest.json').read_text())
        expect(manifest['update_url'] == ADDRESS + '/probe/update.xml', "the probe's update address is the test's own server")
        files, record = pack.pack(HERE / 'probe')  # its own key, made and forgotten like ours
        PROBE_FILES.mkdir(parents=True)
        (PROBE_FILES / 'extension.crx').write_bytes(files['extension.crx'])
        (PROBE_FILES / 'update.xml').write_text(
            '<?xml version="1.0" encoding="UTF-8"?>\n<gupdate xmlns="http://www.google.com/update2/response" protocol="2.0">'
            f'<app appid="{record["id"]}"><updatecheck codebase="file://{PROBE_FILES}/extension.crx" version="{record["version"]}" /></app></gupdate>\n')
        # A policy file of its own with this one key: Chrome takes each key from one file, so a second
        # ExtensionSettings here would replace ours or be ignored.
        PROBE_POLICY.write_text(json.dumps({'ExtensionInstallForcelist': [f'{record["id"]};file://{PROBE_FILES}/update.xml']}))
        PROBE_HOST.parent.mkdir(parents=True)
        shutil.copyfile(HERE / 'probe_host.py', PROBE_HOST)
        os.chmod(PROBE_HOST, 0o755)
        (HOSTS / (PROBE_NAME + '.json')).write_text(json.dumps({
            'name': PROBE_NAME, 'description': 'Test-only host of the install probe', 'path': str(PROBE_HOST), 'type': 'stdio',
            'allowed_origins': [f'chrome-extension://{record["id"]}/']}))
        log('probe', record['id'])
        return record

    def start_service(self):
        # CI's stand-in service, as it is and as run.sh starts it.
        environment = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'PYTHONPATH': str(ROOT / 'control'), 'PYTHONDONTWRITEBYTECODE': '1',
                       'GITHUB_ACTIONS': 'true', 'FIXTURE_LOG_DIR': str(OUT), 'HOME': '/home/' + TOOLS}
        self.service = subprocess.Popen([sys.executable, 'control/chrome/ci/service.py'], **account(TOOLS), env=environment, cwd=ROOT,
                                        stdin=subprocess.DEVNULL, stdout=open(OUT / 'service.txt', 'wb'), stderr=subprocess.STDOUT)
        eventually(lambda: Path('/run/aresos-tools/act.sock').is_socket() and Path('/run/aresos-tools/chrome.sock').is_socket(),
                   "the service's sockets", 30)

    def start_session(self):
        # One display, session bus and window manager for every Chrome start, as run.sh gives browser.mjs.
        record = WORK / 'profiles/session.env'
        script = ('env | grep -E "^(DISPLAY|XAUTHORITY|DBUS_SESSION_BUS_ADDRESS)=" > "$1.new" && mv "$1.new" "$1"; '
                  'openbox > /out/install/openbox.txt 2>&1 & exec sleep infinity')
        self.session = subprocess.Popen(['dbus-run-session', '--', 'xvfb-run', '-a', '-s', '-screen 0 1440x1000x24',
                                         'bash', '-c', script, 'session', str(record)], **account(OWNER), env=owner_environment(),
                                        cwd='/home/owner', stdin=subprocess.DEVNULL, stdout=open(OUT / 'session.txt', 'wb'),
                                        stderr=subprocess.STDOUT, start_new_session=True)
        eventually(record.exists, 'the display session', 30)
        values = dict(line.split('=', 1) for line in record.read_text().splitlines())
        expect({'DISPLAY', 'XAUTHORITY', 'DBUS_SESSION_BUS_ADDRESS'} <= set(values), f'the session has a display and a bus: {sorted(values)}')
        self.environment = {**owner_environment(), **values}
        time.sleep(1)  # the window manager

    # --- the image's files --------------------------------------------------------------------------------------

    def place(self, bundle, policy=None):
        """Put one bundle's four files where the image has them; `policy` replaces the policy for a control run."""
        for name in NAMES:
            (BUNDLE / name).unlink(missing_ok=True)
        for name in NAMES:
            shutil.copyfile(bundle['folder'] / name, BUNDLE / name)
            os.chmod(BUNDLE / name, 0o644)
        if policy is not None:
            (BUNDLE / 'policy.json').write_text(json.dumps(policy))

    def package(self, content):
        target = BUNDLE / 'extension.crx'
        target.unlink(missing_ok=True)
        if content is not None:
            target.write_bytes(content)
            os.chmod(target, 0o644)

    def policy(self, bundle):
        return json.loads(pack.render(bundle['id'], bundle['version'])['policy.json'])

    def profile(self, name):
        return WORK / 'profiles' / name

    # --- Chrome -------------------------------------------------------------------------------------------------

    def launch(self, profile, label, extra=(), url='about:blank'):
        self.stop()
        self.launches += 1
        self.chrome = Chrome(self.environment, profile, label, self.launches, extra, url)
        log('Chrome started:', label)
        return self.chrome

    def stop(self):
        chrome, self.chrome = self.chrome, None
        if chrome is None:
            return
        if chrome.process.poll() is None:
            chrome.process.send_signal(signal.SIGTERM)  # a clean exit: the profile and the network log are complete
            try:
                chrome.process.wait(30)
            except subprocess.TimeoutExpired:
                log('Chrome did not exit on SIGTERM and was killed:', chrome.label)
                chrome.process.kill()
                chrome.process.wait()
        chrome.log.close()
        eventually(lambda: self.link.hello() is None and not host_processes(), 'the native hosts end with Chrome', 15)

    def since(self):
        return round(time.monotonic() - self.chrome.started, 2)

    def run(self, command, **options):
        return subprocess.run(command, **account(OWNER), env=self.environment, capture_output=True, text=True, **options)

    def shot(self, name):
        done = self.run(['import', '-window', 'root', str(OUT / (name + '.png'))])
        expect(done.returncode == 0, 'screenshot: ' + done.stderr[-200:])

    def toolbar_difference(self, first, second):
        """How many pixels differ in the right half of the window's top strip, where pinned buttons sit."""
        strips = []
        for name in (first, second):
            strips.append(str(OUT / (name + '-toolbar.png')))
            subprocess.run(['convert', str(OUT / (name + '.png')), '-crop', '720x140+720+0', '+repage', strips[-1]], check=True)
        done = subprocess.run(['compare', '-metric', 'AE', '-fuzz', '8%', *strips, 'null:'], capture_output=True, text=True)
        expect(done.returncode in (0, 1), 'compare: ' + done.stderr[-200:])
        return int(float(done.stderr.split()[0]))

    def browse(self, marker):
        """The owner's way to a page: the address bar, typed."""
        url = f'{ADDRESS}/browse?step={marker}'

        def attempt():
            for keys in (['key', '--clearmodifiers', 'ctrl+l'], ['type', '--clearmodifiers', '--delay', '1', url],
                         ['key', '--clearmodifiers', 'Delete'], ['key', '--clearmodifiers', 'Return']):
                self.run(['xdotool', *keys], timeout=30)
            return eventually(lambda: self.pages.seen('step=' + marker), 'the page arrives', 4)
        eventually(attempt, f'an ordinary page loads in Chrome ({marker})', 40, interval=1)

    def flags_clean(self):
        listing = subprocess.run(['ps', '-C', 'chrome', '-o', 'args='], capture_output=True, text=True).stdout
        expect(listing.strip(), 'Chrome processes are running')
        expect(not any(flag in listing for flag in NEVER), 'a Chrome process runs with a forbidden flag')
        listeners = [line for line in subprocess.run(['ss', '-lntp'], capture_output=True, text=True).stdout.splitlines() if '"chrome"' in line]
        expect(not listeners, f'Chrome listens on a port: {listeners}')

    def log_lines(self, chrome, *words):
        text = chrome.log_path.read_text(errors='replace')
        return [line[:300] for line in text.splitlines() if any(word in line for word in words)][:8]

    # --- questions ----------------------------------------------------------------------------------------------

    def wait_probe(self):
        hello = eventually(self.link.hello, 'the probe installs from its file: address and connects through its host', 90)
        expect(hello['id'] == self.probe['id'], f'the probe has the ID of its package: {hello}')
        return hello

    def ask(self, operation, **arguments):
        if self.link.hello() is None:
            self.wait_probe()
        return self.link.call(operation, **arguments)

    def installed(self, identity):
        reply = self.ask('get', id=identity)
        return reply['value'] if reply['ok'] else None

    def tool(self, action, arguments=None):
        done = subprocess.run([sys.executable, '-I', '-B', str(HERE / 'tool_call.py'), action, json.dumps(arguments or {})],
                              **account(OWNER), capture_output=True, text=True, timeout=60)
        try:
            result = json.loads(done.stdout)
        except ValueError:
            result = {'ok': False, 'error': {'code': 'no_answer', 'message': done.stderr[-300:]}}
        with open(OUT / 'tool.jsonl', 'a') as record:
            record.write(json.dumps({'at': round(time.monotonic() - STARTED, 2), 'action': action, 'result': result}) + '\n')
        return result

    def connected(self):
        result = self.tool('tabs')
        return bool(result.get('ok') and result['data']['items'])

    def unavailable(self):
        result = self.tool('tabs')
        return not result.get('ok') and result.get('error', {}).get('code') == 'chrome_unavailable'

    def settle(self, current, previous=None, timeout=120):
        """Wait until `previous` is gone and `current` is installed, enabled and connected. Seconds after Chrome's start."""
        wanted = {'new_installed', 'new_connected'} | ({'old_gone'} if previous else set())
        self.wait_probe()
        times = {'probe_connected': self.since()}
        end = time.monotonic() + timeout
        while True:
            if previous and 'old_gone' not in times and self.installed(previous['id']) is None:
                times['old_gone'] = self.since()
            if 'new_installed' not in times:
                info = self.installed(current['id'])
                if info and info['enabled']:
                    times['new_installed'] = self.since()
            if 'new_installed' in times and 'new_connected' not in times and self.connected():
                times['new_connected'] = self.since()
            if wanted <= set(times):
                log('settled:', current['name'], times)
                return times
            expect(self.chrome.process.poll() is None, 'Chrome exited')
            expect(time.monotonic() < end, f'{current["name"]} not installed and connected after {timeout}s: {times}')
            time.sleep(0.2)

    def one_host(self):
        """Exactly one copy of our host runs, as the owner, with the launcher's empty environment; the service has one peer."""
        hosts, peers = host_processes(), service_peers()
        expect(len(hosts) == 1, f'exactly one native host process: {hosts}')
        expect(len(peers) == 1, f'chrome.sock shows exactly one host: {peers}')
        pid, parent, uid = hosts[0]
        expect(uid == pwd.getpwnam(OWNER).pw_uid, 'the host runs as the owner')
        environment = dict(item.split('=', 1) for item in Path(f'/proc/{pid}/environ').read_bytes().decode().split('\0') if item)
        expect(environment == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, f"the host has the launcher's environment: {sorted(environment)}")
        return {'pid': pid, 'started_by_chrome': parent == self.chrome.process.pid}

    def refused(self):
        """The probe's own connection to our host: Chrome refuses it, and the service gains no peer."""
        before = sorted(pid for pid, _, _ in host_processes())
        box = {}

        def attempt():
            try:
                box['reply'] = self.ask('connectNative', name='org.aresos.chrome', timeout=20)
            except Failure as error:
                box['reply'] = str(error)
        thread = threading.Thread(target=attempt)
        thread.start()
        samples, end = [], None
        while True:
            samples.append((sorted(pid for pid, _, _ in host_processes()), len(service_peers())))
            if not thread.is_alive():
                end = end or time.monotonic() + 1.5
                if time.monotonic() > end:
                    break
            time.sleep(0.05)
        reply = box.get('reply')
        expect(isinstance(reply, dict) and reply.get('ok') and reply['value'] == {'connected': False, 'error': REFUSED, 'messages': []},
               f"Chrome refuses the probe's connection to org.aresos.chrome: {reply}")
        expect(all(sample == (before, 1) for sample in samples), f'no second host and no second peer while the probe tried: {samples[:5]}')
        expect(self.connected(), 'our extension still answers after the probe was refused')
        return len(samples)

    # --- records ------------------------------------------------------------------------------------------------

    def case(self, name, function):
        log(f'--- case {name}: {function.__doc__.strip().splitlines()[0]}')
        try:
            self.results[name] = {'pass': True, **(function(self) or {})}
        except Exception as error:
            traceback.print_exc()
            self.results[name] = {'pass': False, 'error': f'{type(error).__name__}: {error}'}
            self.diagnose(name)
        log(f'--- case {name}:', json.dumps(self.results[name]))

    def diagnose(self, name):
        try:
            if self.chrome:
                log('Chrome', self.chrome.label, 'running' if self.chrome.process.poll() is None else f'exited {self.chrome.process.returncode}')
                log('profile folders:', extension_folders(self.chrome.profile))
                for line in self.chrome.log_path.read_text(errors='replace').splitlines()[-25:]:
                    log('  chrome |', line[:300])
                self.shot('failure-case-' + name)
            log('probe:', self.link.hello(), '| hosts:', host_processes(), '| peers:', service_peers())
            if self.link.hello():
                log('extensions:', json.dumps(self.link.call('all')))
            log('tabs:', json.dumps(self.tool('tabs'))[:400])
        except Exception as error:
            log('diagnosis failed:', repr(error))

    def close(self):
        try:
            self.stop()
        except Exception as error:
            log('stopping Chrome:', repr(error))
        if self.service and self.service.poll() is None:
            self.service.terminate()
        if self.session and self.session.poll() is None:
            os.killpg(self.session.pid, signal.SIGTERM)
        # The runner uploads this folder as another user.
        subprocess.run(['chmod', '-R', 'a+rX', str(OUT)])

    def report(self):
        verdicts = {number: bool(self.results.get(number, {}).get('pass')) for number in '12345'}
        verdicts['1'] = verdicts['1'] and bool(self.results.get('1-pin', {}).get('pass'))
        (OUT / 'result.json').write_text(json.dumps({'setup': self.setup, 'verdicts': verdicts, 'cases': self.results}, indent=1))
        for number, passed in verdicts.items():
            print(f'CONTROL_CHROME_INSTALL_CASE_{number}_{"PASS" if passed else "FAIL"}', flush=True)
        if all(verdicts.values()):
            print('CONTROL_CHROME_INSTALL_PROOF_PASSED', flush=True)
            return 0
        return 1


# --- the cases ----------------------------------------------------------------------------------------------------

def case_install(p):
    """1. Install: a fresh profile, no network; Chrome installs ours from the file: address through the links."""
    a = p.bundles['a']
    expect(p.setup['addresses_on'] == ['lo'] and not p.setup['default_routes'], f'the container has no network but loopback: {p.setup}')
    for link, target in LINKS.items():
        expect(link.is_symlink() and os.readlink(link) == target, f'{link} is a link to {target}')
    expect(sorted(os.listdir(POLICIES)) == ['aresos-install-probe.json', 'aresos.json'], 'the policy folder holds our link and the probe')
    expect(list(json.loads(PROBE_POLICY.read_text())) == ['ExtensionInstallForcelist'], "the probe's policy file sets one key")
    p.place(a)
    rendered = pack.render(a['id'], a['version'])
    expect((POLICIES / 'aresos.json').read_bytes() == rendered['policy.json'], 'the policy behind the link is the rendered template')
    expect(a['id'] in rendered['update.xml'].decode() and pack.CRX_URL in rendered['update.xml'].decode(), 'the update manifest names the file: package')
    p.launch(p.profile('one'), 'case1-install')
    times = p.settle(a)
    p.install_seconds = times['new_installed']
    info = p.installed(a['id'])
    expect(info['name'] == 'AresOS Chrome' and info['version'] == a['version'], f'our extension, in its version: {info}')
    expect(info['installType'] == 'admin', f'installed by policy: {info}')
    expect(info['enabled'] is True and info['mayDisable'] is False, f'enabled and not disableable: {info}')
    answers = {}
    for operation, arguments in (('setEnabled', {'enabled': False}), ('uninstall', {})):
        reply = p.ask(operation, id=a['id'], **arguments)
        expect(not reply['ok'] and CANNOT_MODIFY in reply['error'], f'{operation} is refused: {reply}')
        answers[operation] = reply['error']
    after = p.installed(a['id'])
    expect(after and after['enabled'] is True, f'still installed and enabled after both attempts: {after}')
    expect(p.connected(), 'the tools reach Chrome through the host')
    p.flags_clean()
    time.sleep(3)
    p.shot('case1-pinned')
    return {'seconds_after_start': times, 'management': info, 'refusals': answers}


def case_origin(p):
    """2. The host trusts one origin: ours connects, the probe is refused by Chrome, the service sees one host."""
    a = p.bundles['a']
    if p.chrome is None or p.chrome.process.poll() is not None:
        p.place(a)
        p.launch(p.profile('one'), 'case2-origin')
    p.settle(a)
    manifest = HOST_MANIFEST.read_bytes()
    expect(manifest == pack.render(a['id'], a['version'])['native-host.json'], 'the host manifest behind the link is the rendered template')
    value = json.loads(manifest)
    expect(value['allowed_origins'] == [origin(a)] and value['path'] == str(LAUNCHER / 'host'), f'one origin, the fixed launcher: {value}')
    expect((LAUNCHER / 'host').read_bytes() == (ROOT / 'control/chrome/packaging/host').read_bytes(), 'the launcher is the packaged one')
    host = p.one_host()
    samples = p.refused()
    expect(p.one_host()['pid'] == host['pid'], 'the same host is still the only one')
    return {'host': host, 'refusal': REFUSED, 'samples_while_refused': samples}


def case_pin(p):
    """1 (the pin). The toolbar differs between force_pinned and the same policy without the pin."""
    a = p.bundles['a']
    unpinned = p.policy(a)
    del unpinned['ExtensionSettings'][a['id']]['toolbar_pin']
    try:
        for name, policy in (('case1-unpinned', unpinned), ('case1-pinned-again', None)):
            p.stop()
            p.place(a, policy)
            p.launch(p.profile(name), name)
            p.settle(a)
            time.sleep(3)
            p.shot(name)
    finally:
        p.stop()
        p.place(a)
    same = p.toolbar_difference('case1-pinned', 'case1-pinned-again')
    different = p.toolbar_difference('case1-pinned', 'case1-unpinned')
    log('toolbar pixels differing: pinned twice', same, '| pinned against unpinned', different)
    expect(different >= 150 and different >= 4 * same,
           f'the pinned button shows in the toolbar: {different} pixels differ without the pin, {same} between two pinned starts')
    return {'pixels_pinned_twice': same, 'pixels_pinned_against_unpinned': different}


def case_update(p):
    """3. Update and back in one profile: A, then B at the same paths, then A again, Chrome restarted each time."""
    a, b = p.bundles['a'], p.bundles['b']
    profile = p.profile('one')
    p.stop()
    if a['id'] not in extension_folders(profile):
        # Case 1 leaves A installed here; make the starting point if it didn't get that far.
        p.place(a)
        p.launch(profile, 'case3-0-a')
        p.settle(a)
    switches = []
    for number, (current, previous) in enumerate(((b, a), (a, b)), 1):
        p.stop()
        expect(previous['id'] in extension_folders(profile), 'the previous extension is in the profile before the switch')
        p.place(current)
        manifest = HOST_MANIFEST.read_bytes()
        expect(json.loads(manifest)['allowed_origins'] == [origin(current)], "the host's manifest names the current ID alone")
        expect(previous['id'].encode() not in manifest, "an origin of the previous bundle is not in the manifest's bytes")
        p.launch(profile, f'case3-{number}-{current["name"]}')
        times = p.settle(current, previous)
        eventually(lambda: previous['id'] not in extension_folders(profile), "the previous extension's folder leaves the profile", 60)
        times['old_folder_gone'] = p.since()
        listed = p.ask('all')['value']
        others = sorted(item['id'] for item in listed if item['id'] != p.probe['id'])
        expect(others == [current['id']], f'only the current ID is installed beside the probe: {listed}')
        p.refused()
        p.one_host()
        p.stop()
        recorded = preference_ids(profile)
        expect(current['id'] in recorded and previous['id'] not in recorded, "the profile's preferences hold the current ID and not the previous one")
        expect(extension_folders(profile) == sorted([current['id'], p.probe['id']]), f'the profile keeps the current extension and the probe: {extension_folders(profile)}')
        switches.append({'from': previous['name'], 'to': current['name'], 'seconds_after_start': times})
    return {'switches': switches}


def case_broken(p):
    """4. A broken package: changed or missing, a profile that never held the ID doesn't get it; an installed copy keeps running."""
    c = p.bundles['c']
    profile = p.profile('two')
    good = (c['folder'] / 'extension.crx').read_bytes()
    header = 12 + struct.unpack('<I', good[8:12])[0]
    position = header + (len(good) - header) // 2  # in the signed archive
    changed = good[:position] + bytes([good[position] ^ 1]) + good[position + 1:]
    expect(len(changed) == len(good) and sum(x != y for x, y in zip(good, changed)) == 1, 'one byte differs')
    hold = max(20.0, 4 * p.install_seconds)
    result = {'held_seconds': hold, 'changed_byte_at': position, 'package_bytes': len(good)}
    for label, content in (('changed', changed), ('missing', None)):
        p.stop()
        p.place(c)
        p.package(content)
        chrome = p.launch(profile, f'case4-fresh-{label}', url=f'{ADDRESS}/browse?step={label}-start')
        p.wait_probe()  # the probe installs by the same route in this very start
        samples = 0
        while p.since() < hold:
            expect(p.installed(c['id']) is None, f'a {label} package is not installed')
            expect(p.unavailable(), f'the tools answer chrome_unavailable with a {label} package')
            samples += 1
            time.sleep(1)
        expect(c['id'] not in extension_folders(profile), f'nothing of a {label} package is in the profile')
        expect(chrome.process.poll() is None and p.service.poll() is None, 'Chrome and the service stay up')
        expect(p.pages.seen(f'step={label}-start'), 'Chrome loaded its start page')
        p.browse(label + '-after')
        result['fresh_' + label] = {'samples': samples, 'chrome_log': p.log_lines(chrome, c['id'], 'CRX', 'crx')}
    p.stop()
    p.place(c)
    p.launch(profile, 'case4-fresh-restored')
    result['restored_seconds_after_start'] = p.settle(c)
    for label, content in (('changed', changed), ('missing', None)):
        p.stop()
        p.package(content)
        p.launch(profile, f'case4-installed-{label}')
        times = p.settle(c)
        time.sleep(8)
        info = p.installed(c['id'])
        expect(info and info['enabled'] and c['id'] in extension_folders(profile), f'the installed copy stays with a {label} package: {info}')
        expect(p.connected(), f'the installed copy stays connected with a {label} package')
        result['installed_' + label] = times
    p.stop()
    p.place(c)
    return result


def case_store(p):
    """5. Nothing asks the web store about us: the network log across two update checks, with both controls."""
    a = p.bundles['a']

    def run(label, policy=None, ours=True):
        p.stop()
        p.place(a, policy)
        record = OUT / f'netlog-{label}.json'
        # Chrome enforces a minimum of 30 seconds between extension update checks in release builds.
        p.launch(p.profile('five-' + label), 'case5-' + label,
                 extra=[f'--log-net-log={record}', '--extensions-update-frequency=30', '--disable-component-update'])
        if ours:
            p.settle(a)
        else:
            p.wait_probe()
        since = time.monotonic()
        eventually(lambda: len(p.pages.seen('/probe/update.xml', since)) >= 2, "two update checks of the probe reach the test's server", 240, 1)
        if label == 'negative':
            # Give the request this control is there to catch time to reach the log; the scan below decides.
            try:
                eventually(lambda: netlog.UPDATE_SERVICE in record.read_text(errors='replace'), 'the update service request', 60, 2)
            except Failure as error:
                log(str(error))
        seconds = p.since()
        p.stop()
        found = netlog.scan(record.read_text(errors='replace'), a['id'], p.probe['id'], ADDRESS)
        log('network log', label, json.dumps(found)[:1500])
        return {'seconds': seconds, **found}

    result = {'ours': run('ours')}
    problems = netlog.problems(result['ours'])
    if [kind for kind, _ in problems] == ['update_service']:
        # The brief's fallback: requests to the update service that Chrome sends anyway are compared with a
        # run of the probe alone; ours must add none.
        for link in LINKS:
            link.rename(link.with_name(link.name + '.aside'))
        try:
            result['probe_alone'] = run('probe-alone', ours=False)
        finally:
            for link in LINKS:
                link.with_name(link.name + '.aside').rename(link)
        expect(not netlog.problems({**result['probe_alone'], 'update_service': []}), 'the run of the probe alone is a valid comparison')
        expect(len(result['ours']['update_service']) <= len(result['probe_alone']['update_service']),
               f"our policy adds requests to the update service: {problems}")
    else:
        expect(not problems, f'the network log with our policy: {problems}')
    # The negative control: the same package under a policy without override_update_url must fail the scan.
    leaky = p.policy(a)
    del leaky['ExtensionSettings'][a['id']]['override_update_url']
    try:
        result['negative'] = run('negative', leaky)
    finally:
        p.place(a)
    kinds = [kind for kind, _ in netlog.problems(result['negative'])]
    expect('control' not in kinds, 'the negative run also saw two update checks')
    expect('update_service' in kinds or 'named' in kinds, f"without override_update_url the scan fails: {result['negative']}")
    result['negative_fails_with'] = kinds
    return result


def main():
    proof = Proof()
    try:
        proof.prepare()
        for name, function in (('1', case_install), ('2', case_origin), ('1-pin', case_pin), ('3', case_update),
                               ('4', case_broken), ('5', case_store)):
            proof.case(name, function)
    except Exception as error:
        # Outside a case: the setup itself. No case counts as passed.
        traceback.print_exc()
        proof.results['setup'] = {'pass': False, 'error': f'{type(error).__name__}: {error}'}
    finally:
        proof.close()
    return proof.report()


if __name__ == '__main__':
    raise SystemExit(main())
