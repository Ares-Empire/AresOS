"""Brief 18c-b, item 5: the Chrome checks in the booted CI guest, the second pass of check_build=control.

checks.py loads this file from actions.d beside 18c's actions (control.py), whose helpers it reuses. The runner
(os/ci/control/control_vm.py, CHROME_STEPS) takes the screenshots, presses the keys and reboots the guest between
actions through QMP; each action returns its evidence as files and the runner prints the PASS line.

How Chrome runs here: as `ares` in his session, started with the shell's own launch line and environment
(aresos-shell's ScopeLauncher: `systemd-run --user --scope --slice=app.slice`, the helper's environment with its
private values removed), taken from the helper running in his session. The shell's launch request itself belongs to
the desktop (its instance and launch nonce) and the guest's desktop is at its first start, so the pass uses the
shell's line rather than posing as the desktop (brief: "otherwise the same systemd-run --user --scope line with the
session's environment"). CI-only flags: --no-first-run, --no-default-browser-check, --password-store=basic. One
start of its own, with its own throw-away profile, adds a DevTools pipe to ask an extension loaded by hand (lead's
decision 5 after step 2b); every other start has no debugging flag.
"""
import ast
import grp
import hashlib
import importlib.machinery
import importlib.util
import json
import os
import pathlib
import pwd
import re
import secrets
import shutil
import signal
import socket
import stat
import subprocess
import sys
import threading
import time
import types
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ACTIONS_D = pathlib.Path(__file__).resolve().parent
CI = pathlib.Path('/usr/libexec/aresos-ci/control/chrome')
SHELL = pathlib.Path('/usr/libexec/aresos-shell')
BROWSER_APP = pathlib.Path('/usr/share/aresos/apps/browser.json')
RECORD = pathlib.Path('/usr/share/aresos/manifest/control.json')
GH_LOCK = pathlib.Path('/usr/share/aresos/manifest/gh.lock.json')
BUNDLE = pathlib.Path('/usr/share/aresos/chrome')
BUNDLE_FILES = ('extension.crx', 'native-host.json', 'policy.json', 'update.xml')
POLICIES = pathlib.Path('/etc/opt/chrome/policies/managed')
HOSTS = pathlib.Path('/etc/opt/chrome/native-messaging-hosts')
LINKS = {POLICIES / 'aresos.json': '/usr/share/aresos/chrome/policy.json',
         HOSTS / 'org.aresos.chrome.json': '/usr/share/aresos/chrome/native-host.json'}
CODE = pathlib.Path('/usr/libexec/aresos-control')
HOST_PROCESS = str(CODE / 'chrome/native_host.py')
POLKIT_ACTION = pathlib.Path('/usr/share/polkit-1/actions/org.aresos.control.chrome-loosen.policy')
TMPFILES = pathlib.Path('/usr/lib/tmpfiles.d/aresos-control-chrome.conf')
LIST_FOLDER = pathlib.Path('/var/lib/aresos-control')
LIST = LIST_FOLDER / 'chrome-excluded-sites.json'
OLD_LIST = pathlib.Path('/etc/aresos/control/chrome-excluded-sites.json')
# What he types after `sudo tee …` in his guide: the empty list on one line, Enter, then Ctrl-D.
EMPTY_LIST = b'{"format":1,"hosts":[]}\n'
UNIT_FILE = pathlib.Path('/usr/lib/systemd/system/aresos-toold.service')
# The test layer's own pieces (os/ci/control/chrome_layer.py).
TEST = pathlib.Path('/usr/share/aresos-install-test')
LAYER = TEST / 'layer.json'
ORDINARY = TEST / 'ordinary'
PROBE_POLICY = POLICIES / 'aresos-install-probe.json'
RUN = pathlib.Path('/run/aresos-install-test')
THROWAWAY = pathlib.Path('/var/tmp/aresos-ci-chrome-ordinary')
PORT = 18766
ADDRESS = f'http://localhost:{PORT}'
OWNER = 'ares'
CI_FLAGS = ['--no-first-run', '--no-default-browser-check', '--password-store=basic']
NEVER = ('--no-sandbox', '--remote-debugging', '--load-extension', '--disable-extensions-except')
LOADING = '--enable-unsafe-extension-debugging'
AGENT = '/usr/libexec/kf6/polkit-kde-authentication-agent-1'
CANNOT_MODIFY = 'cannot be modified by user'
CHANGE = 'polkit probe of brief 18c-b: allow editing on probe.invalid'
# The unit's [Service] lines that are not its sandbox; every other line is passed to systemd-run as a property.
NOT_SANDBOX = {'Type', 'ExecStart', 'Restart', 'RestartSec'}
LOG_LIMIT = 200_000
STATE = {}


class Failure(AssertionError):
    """A check of the Chrome pass did not hold."""


def expect(condition, message):
    if not condition:
        raise Failure(message)


def eventually(check, label, timeout=60, interval=0.25):
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


def load(name, path):
    # A loader by name: /usr/libexec/aresos-shell has no .py suffix.
    spec = importlib.util.spec_from_loader(name, importlib.machinery.SourceFileLoader(name, str(path)))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def control():
    """18c's actions (actions.d/control.py), for their helpers: run, cli, refused, files_out, denials, …"""
    if 'control' not in STATE:
        STATE['control'] = load('aresos_ci_control_actions', ACTIONS_D / 'control.py')
    return STATE['control']


def cdp():
    if str(CI) not in sys.path:
        sys.path.insert(0, str(CI))
    import cdp as module
    return module


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def owner_ids():
    entry = pwd.getpwnam(OWNER)
    return entry.pw_uid, entry.pw_gid, os.getgrouplist(OWNER, entry.pw_gid)


def placeholder(tmpfiles_text):
    """The content the tmpfiles `f` line gives the list: everything after its sixth field, as written."""
    lines = [line for line in tmpfiles_text.splitlines() if line.startswith('f ')]
    expect(len(lines) == 1, f'one f line in the tmpfiles file: {lines}')
    fields = lines[0].split(None, 6)
    expect(len(fields) == 7 and fields[1] == str(LIST), f'the f line makes the list: {lines[0]}')
    return fields[6].encode()


def sandbox_properties(unit_text):
    """The unit's own sandbox as systemd-run properties: every [Service] line except how it starts and restarts."""
    properties, section = [], None
    for line in unit_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('['):
            section = line
            continue
        key, _, value = line.partition('=')
        if section == '[Service]' and key not in NOT_SANDBOX:
            properties.append(f'{key}={value}')
    expect(any(p.startswith('User=') for p in properties) and any(p.startswith('ReadWritePaths=') for p in properties),
           f'the unit names its user and its writable paths: {properties}')
    return properties


def as_service(name, argv, environment=('PATH=/usr/bin:/bin', 'LANG=C.UTF-8')):
    """argv as the service's user under the unit's own sandbox properties, waiting for its end (systemd-run)."""
    properties = sandbox_properties(UNIT_FILE.read_text())
    return ['systemd-run', f'--unit={name}', '--collect', '--wait', '--pipe', '--service-type=exec',
            *[f'--property={p}' for p in properties], *[f'--setenv={e}' for e in environment], '--', *argv]


def settings_message(source):
    """The installed adapter's refusal text for chrome_settings_unavailable (exclusions.py), read, never copied."""
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and len(node.args) == 2 and isinstance(node.args[0], ast.Constant)
                and node.args[0].value == 'chrome_settings_unavailable' and isinstance(node.args[1], ast.Constant)):
            return node.args[1].value
    raise Failure('exclusions.py has no chrome_settings_unavailable refusal')


def processes():
    rows = []
    for entry in pathlib.Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = [part.decode(errors='replace') for part in (entry / 'cmdline').read_bytes().split(b'\0')[:-1]]
            status = (entry / 'status').read_text()
            uid = int(re.search(r'^Uid:\s+(\d+)', status, re.M)[1])
            parent = int(re.search(r'^PPid:\s+(\d+)', status, re.M)[1])
            cgroup = (entry / 'cgroup').read_text().strip()
            exe = os.readlink(entry / 'exe')
        except (OSError, TypeError):
            continue
        rows.append(dict(pid=int(entry.name), parent=parent, uid=uid, cmdline=cmdline, cgroup=cgroup, exe=exe))
    return rows


def host_processes():
    return [row for row in processes() if HOST_PROCESS in row['cmdline']]


def chrome_processes():
    # By executable: Chrome's wrapper starts it with `exec -a "$0"`, so the main process's argv[0] is the wrapper's.
    return [row for row in processes() if row['exe'].startswith(('/opt/google/chrome/', '/usr/lib/opt/google/chrome/'))]


def service_peers(directory='/run/aresos-tools'):
    """Established server ends on chrome.sock (18e binds .chrome.sock.new and renames it; ss keeps the bind name)."""
    listing = control().run(['ss', '-x', '-a', '-n'])
    expect(listing['returncode'] == 0, f'ss: {listing["stderr"][-300:]}')
    names = {f'{directory}/chrome.sock', f'{directory}/.chrome.sock.new'}
    return [line for line in listing['stdout'].splitlines()
            if len(fields := line.split()) >= 6 and fields[:2] == ['u_str', 'ESTAB'] and fields[4] in names]


def label(pid):
    """The process's SELinux context, recorded: the pass starts Chrome from the CI service, not from his helper."""
    try:
        return pathlib.Path(f'/proc/{pid}/attr/current').read_text().strip('\0\n')
    except OSError as error:
        return f'unreadable: {error}'


def tcp_listeners_of(pids):
    found = []
    for pid in pids:
        try:
            inodes = {os.readlink(f'/proc/{pid}/fd/{fd}') for fd in os.listdir(f'/proc/{pid}/fd')}
        except OSError:
            continue
        for kind in ('tcp', 'tcp6'):
            for line in pathlib.Path(f'/proc/{pid}/net/{kind}').read_text().splitlines()[1:]:
                fields = line.split()
                if fields[3] == '0A' and f'socket:[{fields[9]}]' in inodes:
                    found.append((pid, kind, fields[1]))
    return found


def sessions():
    """loginctl's view: every session, and each of his with its properties."""
    view = dict(list=control().run(['loginctl', 'list-sessions', '--no-legend'])['stdout'],
                user=control().run(['loginctl', 'show-user', OWNER])['stdout'], sessions={})
    for session in control().run(['loginctl', 'show-user', OWNER, '--property=Sessions', '--value'])['stdout'].split():
        shown = control().run(['loginctl', 'show-session', session])['stdout']
        view['sessions'][session] = dict(line.split('=', 1) for line in shown.splitlines() if '=' in line)
    return view


def his_session(view):
    """His one active local session (its Type is recorded, not required: polkit's answer is what the probe tests)."""
    active = [name for name, info in view['sessions'].items() if info.get('Active') == 'yes' and info.get('Remote') == 'no'
              and info.get('Class') == 'user']
    expect(len(active) == 1, f'his one active local session: {view["sessions"]}')
    return active[0]


def prepare_run():
    if RUN.is_dir():
        return
    uid, gid, _ = owner_ids()
    RUN.mkdir(mode=0o755)
    log = RUN / 'probe.jsonl'
    log.touch()
    os.chown(log, uid, gid)


# --- the shell's launch line --------------------------------------------------------------------------------------

def helpers():
    uid = owner_ids()[0]
    return [row for row in processes() if row['uid'] == uid and row['cmdline'][1:2] == [str(SHELL)]]


def wait_session():
    """His session is up after boot: the app helper and his polkit agent run (a fresh boot reaches the CI channel
    well before greetd's auto-login has started them; run 44421776687). polkitd 127 logs no line when an agent
    registers (run 44427301872), so the probe's own journal line shows which session's agent was asked."""
    uid = owner_ids()[0]
    eventually(lambda: len(helpers()) == 1, 'the app helper runs in his session', 240, interval=1)
    agent = eventually(lambda: [row for row in processes() if row['uid'] == uid and AGENT in row['cmdline'][:2]],
                       'his polkit agent runs', 120, interval=1)
    return dict(agent=[dict(pid=row['pid'], cgroup=row['cgroup'], label=label(row['pid'])) for row in agent])


def session(request):
    """Before the probe: his session is up; loginctl's view of it (the probe's screenshots start from here)."""
    ready = wait_session()
    time.sleep(5)  # the desktop's first windows settle before the runner's first screenshot
    view = sessions()
    summary = dict(ready, session=his_session(view))
    return dict(returncode=0, summary=summary, files=control().files_out({'chrome/sessions-at-start.json': view}))


def shell_launcher():
    """aresos-shell's own ScopeLauncher, with the environment of the helper running in his session."""
    found = helpers()
    expect(len(found) == 1, f'one app helper runs in his session: {found}')
    helpers_ = found
    raw = pathlib.Path(f'/proc/{helpers_[0]["pid"]}/environ').read_bytes().split(b'\0')
    environ = {key.decode(): value.decode() for key, _, value in (item.partition(b'=') for item in raw if b'=' in item)}
    shell = STATE.get('shell') or STATE.setdefault('shell', load('aresos_shell_for_ci', SHELL))
    launcher = shell.ScopeLauncher(environ=environ)
    expect({'XDG_RUNTIME_DIR', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'} <= set(launcher.environment()),
           f'the session environment reaches the app: {sorted(launcher.environment())}')
    return launcher, helpers_[0]['pid']


def app(identity, name):
    return types.SimpleNamespace(id=identity, name=name, environment={}, gpu=None, discovered=False)


def launch(identity, name, argv, log_name, pass_fds=()):
    """One start through the shell's line, as `ares`; the scope execs argv, so the process is argv's own."""
    launcher, helper = shell_launcher()
    uid, gid, groups = owner_ids()
    command = launcher.command(app(identity, name), argv, secrets.token_hex(8))
    log = open(RUN / log_name, 'wb')
    process = subprocess.Popen(command, env=launcher.environment(app(identity, name)), cwd=pwd.getpwnam(OWNER).pw_dir,
                               user=uid, group=gid, extra_groups=groups, pass_fds=pass_fds, stdin=subprocess.DEVNULL,
                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    log.close()
    return process, dict(command=command, helper=helper, log=log_name)


def browser_argv(extra=()):
    definition = json.loads(BROWSER_APP.read_text())
    return [*definition['argv'], *CI_FLAGS, *extra], definition


class Pages:
    """The page server in the guest: the probe's update address, an ordinary page, and what arrived."""

    def __init__(self, probe):
        self.hits, self.lock = [], threading.Lock()
        update = ('<?xml version="1.0" encoding="UTF-8"?>\n<gupdate xmlns="http://www.google.com/update2/response" '
                  f'protocol="2.0"><app appid="{probe["id"]}"><updatecheck codebase="{ADDRESS}/probe/extension.crx" '
                  f'version="{probe["version"]}" /></app></gupdate>\n').encode()
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
                    body, kind = b'<!doctype html><title>Chrome pass</title><p>An ordinary page.</p>', 'text/html'
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

    def seen(self, text):
        with self.lock:
            return [path for _, path in self.hits if text in path]


class ProbeLink:
    """The check's end of the probe's native host (install proof, item 2): questions out, answers back."""

    def __init__(self):
        path = RUN / 'probe.sock'
        path.unlink(missing_ok=True)
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


def fixtures():
    """Once per boot: the run folder, the probe's link and the page server."""
    if 'link' not in STATE:
        prepare_run()
        layer = json.loads(LAYER.read_text())
        STATE.update(layer=layer, link=ProbeLink(), pages=Pages(layer['probe']))
    return STATE['layer'], STATE['link'], STATE['pages']


class Chrome:
    """One Chrome start through the shell's line; stopped by its own PID."""

    def __init__(self, label, extra=(), devtools=None):
        self.label = label
        self.session = wait_session()
        argv, _ = browser_argv(extra)
        expect(not any(argument.startswith(NEVER) for argument in argv), f'a forbidden Chrome flag: {argv}')
        kept, self.devtools = (), None
        if devtools is not None:
            module = cdp()
            ours, kept = module.descriptors()
            argv = module.command(argv[0], [module.FLAG, *devtools, *argv[1:]], kept)
        self.process, self.launch = launch('browser', 'Chrome', argv, f'chrome-{label}.txt', pass_fds=kept)
        self.started = time.monotonic()
        if devtools is not None:
            for descriptor in kept:
                os.close(descriptor)
            self.devtools = module.Client(*ours)

    def since(self):
        return round(time.monotonic() - self.started, 2)

    def stop(self, link):
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.devtools:
            self.devtools.close()
        eventually(lambda: link.hello() is None and not host_processes() and not chrome_processes(),
                   'Chrome and the native hosts end', 60)


def installed(link, identity):
    reply = link.call('get', id=identity)
    return reply['value'] if reply['ok'] else None


def settle(chrome, link, ours, timeout=120):
    """Probe connected, ours installed and enabled, one host on chrome.sock. Seconds after Chrome's start."""
    hello = eventually(link.hello, 'the probe installs from its file: address and connects through its host', timeout)
    times = {'probe_connected': chrome.since()}

    def enabled():
        expect(chrome.process.poll() is None, f'Chrome exited: {chrome.process.returncode}')
        info = installed(link, ours)
        return info if info and info['enabled'] else None
    info = eventually(enabled, 'ours is installed and enabled', timeout)
    times['installed'] = chrome.since()
    eventually(lambda: len(host_processes()) == 1 and len(service_peers()) == 1, 'one host on chrome.sock', 60)
    times['host_connected'] = chrome.since()
    return hello, info, times


def one_host(chrome):
    hosts, peers = host_processes(), service_peers()
    expect(len(hosts) == 1 and len(peers) == 1, f'exactly one host and one chrome.sock peer: {hosts} {peers}')
    host = hosts[0]
    expect(host['uid'] == owner_ids()[0], f'the host runs as {OWNER}: {host}')
    raw = pathlib.Path(f'/proc/{host["pid"]}/environ').read_bytes().decode().split('\0')
    environment = dict(item.split('=', 1) for item in raw if item)
    expect(environment == {'PATH': '/usr/bin:/bin', 'LANG': 'C.UTF-8'}, f"the launcher's environment: {environment}")
    browser = [row for row in processes() if row['pid'] == chrome.process.pid]
    return dict(pid=host['pid'], cgroup=host['cgroup'], chrome_cgroup=browser[0]['cgroup'] if browser else None,
                in_chrome_scope=bool(browser) and host['cgroup'] == browser[0]['cgroup'], label=label(host['pid']),
                chrome_label=label(chrome.process.pid))


def tool(name, value):
    return control().cli(OWNER, 'chrome', name, value=value)


def chrome_log(chrome):
    return (RUN / chrome.launch['log']).read_bytes()[-LOG_LIMIT:]


# --- the polkit probe ---------------------------------------------------------------------------------------------

def polkit_start(request):
    """A process started with the shell's line is pkcheck's subject, run as the service runs it; its dialog waits."""
    prepare_run()
    ready = wait_session()
    view = sessions()
    session = his_session(view)
    confirm = load('aresos_confirm_for_ci', CODE / 'aresos_control/chrome/confirm.py')
    subject, launched = launch('polkit-probe', 'polkit probe', ['/usr/bin/sleep', '900'], 'polkit-subject.txt')
    eventually(lambda: pathlib.Path(f'/proc/{subject.pid}/cmdline').read_bytes() == b'/usr/bin/sleep\x00900\x00',
               'the subject runs', 30)
    cgroup = pathlib.Path(f'/proc/{subject.pid}/cgroup').read_text().strip()
    expect('/user@' in cgroup and '/app.slice/app-aresos-' in cgroup, f'the subject is in his app.slice: {cgroup}')
    peer = dict(pid=subject.pid, start=confirm.start_time(subject.pid), uid=owner_ids()[0])
    argv = confirm.command(peer, confirm.shown(CHANGE))
    command = as_service('aresos-ci-polkit-probe', argv)
    began = time.time()
    output = open(RUN / 'polkit-probe.txt', 'wb')
    probe = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT)
    output.close()
    time.sleep(8)
    STATE['polkit'] = dict(subject=subject, probe=probe, began=began, session=session, command=command, peer=peer)
    summary = dict(session=session, ready=ready, subject=dict(pid=subject.pid, cgroup=cgroup, launch=launched['command'],
                                                 label=label(subject.pid)),
                   pkcheck=argv, systemd_run=command, waiting_after_8s=probe.poll() is None)
    files = {'chrome/polkit-sessions.json': view, 'chrome/polkit-start.json': summary}
    if probe.poll() is not None:
        # polkit answered at once: without asking his agent (0) or with no agent (2). Brief: stop and report.
        summary['exit'] = probe.returncode
        summary['output'] = (RUN / 'polkit-probe.txt').read_text(errors='replace')[-4000:]
        return dict(returncode=1, summary=summary, files=control().files_out(files),
                    stderr=f'pkcheck answered without waiting for his agent: {summary}')
    return dict(returncode=0, summary=summary, files=control().files_out(files))


def polkit_finish(request):
    """After the runner's Escape: pkcheck ends dismissed (3), polkit's journal names his session; then clean up."""
    state = STATE['polkit']
    probe, subject = state['probe'], state['subject']
    try:
        code = probe.wait(60)
        dismissed_by_escape = True
    except subprocess.TimeoutExpired:
        dismissed_by_escape = False
        control().run(['systemctl', 'stop', 'aresos-ci-polkit-probe.service'])
        code = probe.wait(30)
    subject.send_signal(signal.SIGTERM)
    subject.wait(30)
    output = (RUN / 'polkit-probe.txt').read_text(errors='replace')
    # systemd-run --wait reports how the service's process ended; that status is pkcheck's own exit code.
    status = re.findall(r'Main processes terminated with: code=exited[/,] ?status=(\d+)', output)
    code = int(status[-1]) if status else code
    journal = control().run(['journalctl', '-b', '--no-pager', '-o', 'short-iso-precise',
                             f'--since=@{int(state["began"]) - 1}'], timeout=120)['stdout']
    lines = [line for line in journal.splitlines()
             if ('polkit' in line or 'pkcheck' in line or 'chrome-loosen' in line) and 'Got message type=' not in line]
    operator = [line for line in lines if 'org.aresos.control.chrome-loosen' in line and 'Operator of' in line]
    summary = dict(exit=code, systemd_run_exit=probe.returncode, dismissed_by_escape=dismissed_by_escape,
                   session=state['session'], subject_pid=state['peer']['pid'], dismissed_detail='polkit.dismissed' in output,
                   journal_operator_lines=operator, journal_names_his_session=any(
                       f'unix-session:{state["session"]} ' in line for line in operator))
    files = control().files_out({'chrome/polkit-probe-output.txt': output, 'chrome/polkit-journal.txt':
                                 '\n'.join(lines) + '\n', 'chrome/polkit-finish.json': summary})
    # polkit asked his session's agent for this subject and only the operator's answer ended it: pkcheck waited (the
    # start's 8 s), ended after Escape as not authorized, and polkitd's line names his session and the subject. KDE's
    # agent reports a cancelled dialog as a failed authentication (1); 3 ("dismissed") would mean the same here.
    subject_name = f'unix-process:{state["peer"]["pid"]}:{state["peer"]["start"]} '
    named = [line for line in operator if f'unix-session:{state["session"]} ' in line and subject_name in line]
    summary['service_would_say'] = confirm_refusal(code)
    if code not in (1, 3) or not dismissed_by_escape or not named:
        return dict(returncode=1, summary=summary, files=files,
                    stderr=f'polkit did not ask his agent for the subject and end on his answer: {summary}')
    return dict(returncode=0, summary=summary, files=files)


def confirm_refusal(code):
    """What the service tells Chrome's details page for this exit code (confirm.py, REFUSALS)."""
    confirm = load('aresos_confirm_for_ci', CODE / 'aresos_control/chrome/confirm.py')
    return confirm.REFUSALS.get(code, 'polkit could not check the request')


# --- C1 files -----------------------------------------------------------------------------------------------------

def metadata(path, kind):
    info = path.lstat()
    expect(kind(info.st_mode), f'{path}: wrong file type {oct(info.st_mode)}')
    return dict(path=str(path), owner=f'{pwd.getpwuid(info.st_uid).pw_name}:{grp.getgrgid(info.st_gid).gr_name}',
                mode=f'{stat.S_IMODE(info.st_mode):04o}')


def files(request):
    """C1: every path of "Agree" in the booted guest, the two links, the policy folder, the placeholder after boot."""
    record = json.loads(RECORD.read_text())
    expected = request['expected']
    rows = []
    expect(metadata(RECORD, stat.S_ISREG)['owner'] == 'root:root', 'control.json is root:root')
    for key in ('files', 'links', 'directories'):
        expect(record[key] == expected[key], f'control.json {key} is what the commit installs')
    for name in (CODE / 'chrome/host', CODE / 'chrome/native_host.py', POLKIT_ACTION, TMPFILES):
        entry = record['files'][str(name)]
        row = dict(metadata(name, stat.S_ISREG), sha256=sha256(name))
        expect(row['owner'] == 'root:root' and row['mode'] == entry['mode'] and row['sha256'] == entry['sha256'],
               f'{name} as recorded: {row} {entry}')
        rows.append(row)
    folder = metadata(BUNDLE, stat.S_ISDIR)
    expect(folder['owner'] == 'root:root' and folder['mode'] == '0755', f'the bundle folder: {folder}')
    expect(sorted(os.listdir(BUNDLE)) == sorted(BUNDLE_FILES), f'the bundle holds its four files: {os.listdir(BUNDLE)}')
    rows.append(folder)
    extension = record['chrome_extension']
    for name in BUNDLE_FILES:
        path = BUNDLE / name
        row = dict(metadata(path, stat.S_ISREG), sha256=sha256(path))
        entry = extension['files'][str(path)]
        expect(row['owner'] == 'root:root' and row['mode'] == entry['mode'] == '0644' and row['sha256'] == entry['sha256'],
               f'{path} as recorded: {row} {entry}')
        rows.append(row)
    for name in ('policy.json', 'native-host.json', 'update.xml'):
        expect(extension['id'] in (BUNDLE / name).read_text(), f'{name} names the recorded ID')
    for link, target in LINKS.items():
        row = dict(metadata(link, stat.S_ISLNK), target=os.readlink(link))
        pristine = pathlib.Path('/usr') / link.relative_to('/')
        expect(row['owner'] == 'root:root' and row['target'] == target == record['links'][str(link)],
               f'{link} links to {target}: {row}')
        expect(pristine.is_symlink() and os.readlink(pristine) == target, f'{link} equals {pristine}')
        parent = link.parent
        while parent != pathlib.Path('/etc'):
            info = metadata(parent, stat.S_ISDIR)
            expect(info['owner'] == 'root:root' and info['mode'] == '0755', f'{parent}: {info}')
            parent = parent.parent
        rows.append(dict(row, usr_etc=os.readlink(pristine)))
    policies = sorted(os.listdir(POLICIES))
    expect(policies == ['aresos-install-probe.json', 'aresos.json'], f'the policy folder holds ours and the probe\'s: {policies}')
    probe_policy = json.loads(PROBE_POLICY.read_text())
    probe_id = json.loads(LAYER.read_text())['probe']['id']
    expect(list(probe_policy) == ['ExtensionInstallForcelist'] and len(probe_policy['ExtensionInstallForcelist']) == 1
           and probe_policy['ExtensionInstallForcelist'][0].startswith(probe_id + ';file:///usr/share/aresos-install-test/'),
           f"the probe's policy file sets ExtensionInstallForcelist alone: {probe_policy}")
    lock = json.loads(GH_LOCK.read_text())
    gh_rows = [dict(metadata(pathlib.Path('/usr/bin/gh'), stat.S_ISREG), sha256=sha256('/usr/bin/gh')),
               dict(metadata(pathlib.Path('/usr/share/licenses/gh/LICENSE'), stat.S_ISREG),
                    sha256=sha256('/usr/share/licenses/gh/LICENSE')),
               dict(metadata(GH_LOCK, stat.S_ISREG), sha256=sha256(GH_LOCK))]
    expect([(r['owner'], r['mode']) for r in gh_rows] == [('root:root', '0755'), ('root:root', '0644'), ('root:root', '0644')],
           f'gh, its licence and lock: {gh_rows}')
    expect(gh_rows[0]['sha256'] == lock['binary_sha256'] == record['gh']['binary_sha256'], 'gh is its pin')
    expect(gh_rows[1]['sha256'] == lock['license_sha256'], "gh's licence is its pin")
    expect(gh_rows[2]['sha256'] == request['gh_lock_sha256'], "gh's lock is the checkout's")
    rows += gh_rows
    tmpfiles = TMPFILES.read_text()
    folder = metadata(LIST_FOLDER, stat.S_ISDIR)
    listing = dict(metadata(LIST, stat.S_ISREG), sha256=sha256(LIST))
    expect(folder['owner'] == 'root:root' and folder['mode'] == '0755', f'{LIST_FOLDER}: {folder}')
    expect(listing['owner'] == 'root:aresos-tools' and listing['mode'] == '0640', f'{LIST}: {listing}')
    expect(LIST.read_bytes() == placeholder(tmpfiles), f'the list is the placeholder: {LIST.read_bytes()[:200]!r}')
    expect(sorted(os.listdir(LIST_FOLDER)) == [LIST.name], f'{LIST_FOLDER} holds the list alone')
    expect(not os.path.lexists(OLD_LIST), f'nothing at {OLD_LIST}')
    rows += [folder, listing]
    summary = dict(paths=len(rows), extension_id=extension['id'], chrome_build=record['chrome_build'],
                   gh=record['gh']['version'], policies=policies, hosts=sorted(os.listdir(HOSTS)),
                   placeholder=LIST.read_text())
    return dict(returncode=0, summary=summary, files=control().files_out({'chrome/files.json': dict(summary, rows=rows)}))


# --- C2 install ---------------------------------------------------------------------------------------------------

def hand_loaded(request):
    """C2, the extension loaded by hand: a start of its own with the pipe and a throw-away profile; it can't switch
    ours off (lead's decision 5 after step 2b, as the install proof's case_ordinary)."""
    layer, link, _ = fixtures()
    ours = json.loads(RECORD.read_text())['chrome_extension']['id']
    shutil.rmtree(THROWAWAY, ignore_errors=True)
    THROWAWAY.mkdir(mode=0o700)
    uid, gid, _ = owner_ids()
    os.chown(THROWAWAY, uid, gid)
    module = cdp()
    chrome = Chrome('hand-loaded', extra=[f'--user-data-dir={THROWAWAY}'], devtools=(LOADING,))
    try:
        hello, info, times = settle(chrome, link, ours)
        listeners = tcp_listeners_of([row['pid'] for row in chrome_processes()])
        expect(not listeners, f'Chrome listens on a port: {listeners}')
        extensions = chrome.devtools.page('chrome://extensions/')
        eventually(lambda: _evaluate(extensions, "typeof chrome.developerPrivate?.updateProfileConfiguration === "
                                     "'function'") is True, 'chrome://extensions has loaded', 60)
        extensions.evaluate('chrome.developerPrivate.updateProfileConfiguration({inDeveloperMode: true})', wait=True)
        identity = chrome.devtools.call('Extensions.loadUnpacked', {'path': str(ORDINARY)})['id']
        page = chrome.devtools.page(f'chrome-extension://{identity}/page.html')
        eventually(lambda: _evaluate(page, "typeof chrome.management?.setEnabled === 'function'") is True,
                   'the page of the extension loaded by hand', 60)
        own = page.evaluate('chrome.management.getSelf().then(self => [self.id, self.installType])', wait=True)
        expect(own == [identity, 'development'], f'loaded by hand, not by policy: {own}')
        try:
            page.evaluate(f"chrome.management.setEnabled('{ours}', false)", wait=True)
            answer = 'allowed'
        except module.Error as error:
            answer = str(error)
        expect(CANNOT_MODIFY in answer, f'setEnabled(false) by an extension loaded by hand is refused: {answer}')
        after = page.evaluate(f"chrome.management.get('{ours}').then(i => [i.enabled, i.installType, i.mayDisable])",
                              wait=True)
        expect(after == [True, 'admin', False], f'ours is still enabled, by policy, not disableable: {after}')
        host = one_host(chrome)
        summary = dict(asked=True, install_type=own[1], set_enabled_false=answer, ours_after=after, times=times,
                       host=host, probe=hello['id'])
    finally:
        log = chrome_log(chrome)
        chrome.stop(link)
        shutil.rmtree(THROWAWAY, ignore_errors=True)
    return dict(returncode=0, summary=summary, files=control().files_out({
        'chrome/c2-hand-loaded.json': summary, 'chrome/chrome-hand-loaded.txt': log}))


def _evaluate(page, expression):
    try:
        return page.evaluate(expression)
    except cdp().Error:
        return None


def start_his_chrome(label):
    layer, link, _ = fixtures()
    record = json.loads(RECORD.read_text())['chrome_extension']
    chrome = Chrome(label)
    STATE['chrome'] = chrome
    hello, info, times = settle(chrome, link, record['id'])
    expect(hello['id'] == layer['probe']['id'], f'the probe has the ID of its package: {hello}')
    return chrome, record, info, times


def install(request):
    """C2: item 2's case 1 on the shipped Chrome in his session, his own (fresh) profile, no debugging flag."""
    _, link, _ = fixtures()
    profile = pathlib.Path(pwd.getpwnam(OWNER).pw_dir) / '.config/google-chrome'
    before = sorted(os.listdir(profile)) if profile.is_dir() else None
    expect(not (profile / 'Default').exists(), f'his profile is fresh before its first start: {before}')
    chrome, record, info, times = start_his_chrome('his-profile')
    expect(info['name'] == 'AresOS Chrome' and info['version'] == record['version'], f'ours in its version: {info}')
    expect(info['installType'] == 'admin' and info['mayDisable'] is False, f'installed by policy, not disableable: {info}')
    every = chrome_processes()
    expect(every and not any(arg.startswith(NEVER) for row in every for arg in row['cmdline']),
           'no Chrome process has a forbidden flag')
    expect(not any(arg.startswith(LOADING) or arg.startswith('--user-data-dir') for row in every for arg in row['cmdline']),
           'his Chrome runs his own profile, without the throw-away start\'s flags')
    listeners = tcp_listeners_of([row['pid'] for row in every])
    expect(not listeners, f'Chrome listens on a port: {listeners}')
    host = one_host(chrome)
    expect('/app.slice/app-aresos-browser-' in host['chrome_cgroup'], f"Chrome is in the shell's scope: {host}")
    reply = link.call('uninstall', id=record['id'])
    expect(not reply['ok'] and CANNOT_MODIFY in reply['error'], f'uninstall is refused: {reply}')
    after = installed(link, record['id'])
    expect(after and after['enabled'] is True, f'still installed and enabled after the uninstall attempt: {after}')
    view = sessions()
    summary = dict(profile_folder_before=before, seconds_after_start=times, management=info, uninstall=reply['error'],
                   host=host, launch=chrome.launch['command'], session=his_session(view),
                   chrome_main=[dict(pid=r['pid'], cgroup=r['cgroup']) for r in every if r['pid'] == chrome.process.pid])
    return dict(returncode=0, summary=summary, files=control().files_out({
        'chrome/c2-install.json': summary, 'chrome/c2-sessions.json': view}))


def hand_over(url, label):
    """Open `url` in his running Chrome the way a second start from the shell does: Chrome hands it over and exits."""
    argv, _ = browser_argv([url])
    second, launched = launch('browser', 'Chrome', argv, f'chrome-{label}.txt')
    try:
        code = second.wait(60)
    except subprocess.TimeoutExpired:
        code = None
    expect(STATE['chrome'].process.poll() is None, 'his Chrome still runs')
    return dict(exit=code, launch=launched['command'])


def his_page(step):
    """An ordinary page of the page server in a tab of his, opened by hand-over, arrived at the server."""
    _, _, pages = fixtures()
    opened = hand_over(f'{ADDRESS}/browse?step={step}', step)
    eventually(lambda: pages.seen(f'step={step}'), f'his page {step} arrives at the page server', 60)
    return opened


def his_tab(request):
    """An ordinary page of his in his Chrome, so his tabs hold a web page for C6; its window takes the focus for the
    runner's Alt+F, which opens Chrome's menu with its "managed" note (C2's second screenshot). chrome://management
    can't be opened this way: Chrome doesn't open chrome:// pages handed over from a command line (run 44427301872)."""
    chrome = STATE['chrome']
    page = his_page('his-tab')
    time.sleep(4)
    summary = dict(his_page=page)
    return dict(returncode=0, summary=summary, files=control().files_out({
        'chrome/chrome-his-profile.txt': chrome_log(chrome)}))


# --- C6 sites -----------------------------------------------------------------------------------------------------

def list_state():
    info = LIST.lstat()
    expect(stat.S_ISREG(info.st_mode), f'{LIST} is a regular file')
    return dict(sha256=sha256(LIST), uid=info.st_uid, gid=info.st_gid, mode=f'{stat.S_IMODE(info.st_mode):04o}')


def tabs_listed():
    result = tool('tabs', {})
    data = result['json'] or {}
    if result['returncode'] == 0 and data.get('ok') is True and (data.get('data') or {}).get('items'):
        return data
    STATE['last_tabs'] = data or result['stderr'][-500:]
    return None


def sites_first_use(request):
    """C6's first use, right after C2: with the placeholder every read and action refuses and reaches no page; root
    writes the empty list his way (`sudo tee`, root standing in for sudo), and tabs lists his tabs."""
    _, _, pages = fixtures()
    message = settings_message((CODE / 'aresos_control/chrome/exclusions.py').read_text())
    tmpfiles = TMPFILES.read_text()
    expect(LIST.read_bytes() == placeholder(tmpfiles), 'the placeholder is still in place')
    before = list_state()
    target = f'{ADDRESS}/browse?step=first-use'
    calls = {'tabs': {}, 'read': {'tab': 1}, 'open': {'url': target}, 'take_tab': {'tab': 1}}
    answers = {}
    for name, value in calls.items():
        result = tool(name, value)
        control().refused(result, 'chrome_settings_unavailable')
        expect(result['json']['error']['message'] == message, f'{name}: the new message: {result["json"]}')
        answers[name] = result['json']['error']
    time.sleep(2)
    expect(not pages.seen('step=first-use'), f'the page server received nothing: {pages.seen("step=first-use")}')
    written = subprocess.run(['/usr/bin/tee', str(LIST)], input=EMPTY_LIST, stdout=subprocess.DEVNULL,
                             stderr=subprocess.PIPE, timeout=30)
    expect(written.returncode == 0, f'tee: {written.stderr[-300:]!r}')
    after = list_state()
    expect((after['uid'], after['gid'], after['mode']) == (before['uid'], before['gid'], before['mode']) ==
           (0, grp.getgrnam('aresos-tools').gr_gid, '0640'), f'owner, group and mode unchanged: {before} {after}')
    expect(LIST.read_bytes() == EMPTY_LIST, 'the list is what he typed')
    try:
        listed = eventually(tabs_listed, 'tabs lists his tabs once the list is written', 60, interval=1)
    except Failure as error:
        raise Failure(f'{error}; the last answer: {STATE.get("last_tabs")}') from error
    summary = dict(refusals=answers, page_server_hits=len(pages.seen('step=first-use')), before=before, list=after,
                   tabs=len(listed['data']['items']))
    return dict(returncode=0, summary=summary, files=control().files_out({'chrome/c6-first-use.json': dict(
        summary, tab_titles=[item.get('title') for item in listed['data']['items']])}))


def sites_after_reboot(request):
    """C6 after the pass's one reboot: the list's hash, owner, group and mode unchanged; Chrome again lists his tabs."""
    now = list_state()
    expect(now == request['list'], f'the written list survives the reboot unchanged: {request["list"]} {now}')
    chrome, record, info, times = start_his_chrome('after-reboot')
    his_page('his-tab-after-reboot')
    listed = eventually(tabs_listed, 'tabs lists his tabs after the reboot', 90, interval=1)
    summary = dict(list=now, seconds_after_start=times, tabs=len(listed['data']['items']), host=one_host(chrome))
    return dict(returncode=0, summary=summary, files=control().files_out({
        'chrome/c6-after-reboot.json': summary, 'chrome/chrome-after-reboot.txt': chrome_log(chrome)}))


def selinux(request):
    """18c's SELinux scan again at the end of this pass; a denial naming Chrome's host, the service, gh or pkcheck
    fails it."""
    actions = control()
    actions.wait_active()
    hosts = [row['pid'] for row in host_processes()]
    every, ours = actions.denials(actions.show('MainPID')['MainPID'], *hosts)
    named = [line for line in every if any(mark in line for mark in (
        'native_host', 'comm="host"', 'comm="pkcheck"', 'comm="gh"', '/usr/bin/gh', 'pkcheck'))]
    summary = dict(getenforce=actions.run(['getenforce'])['stdout'].strip(), avc_denials_in_boot=len(every),
                   naming_ours=len(set(ours) | set(named)))
    expect(summary['getenforce'] == 'Enforcing' and not ours and not named, dict(summary, lines=ours + named))
    probe_log = (RUN / 'probe.jsonl').read_bytes()[-LOG_LIMIT:] if (RUN / 'probe.jsonl').exists() else b''
    return dict(returncode=0, summary=summary, files=actions.files_out({
        'chrome/selinux.txt': json.dumps(summary, indent=2) + '\n' + '\n'.join(every[-200:]) + '\n',
        'chrome/probe.jsonl': probe_log}))


ACTIONS = {'chrome-session': session, 'chrome-polkit-start': polkit_start, 'chrome-polkit-finish': polkit_finish, 'chrome-files': files,
           'chrome-hand-loaded': hand_loaded, 'chrome-install': install, 'chrome-his-tab': his_tab,
           'chrome-sites-first-use': sites_first_use, 'chrome-sites-after-reboot': sites_after_reboot,
           'chrome-selinux': selinux}
