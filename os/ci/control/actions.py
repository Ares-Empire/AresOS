"""Package 18c, B2: the Control checks in the booted CI guest (check_build=control).

checks.py loads this file from actions.d (agreed change 8), so Control's checks stay in os/ci/control/. Each action
returns its evidence as files for the runner (os/ci/control/control_vm.py), which prints the PASS line. The owner's
steps run as `ares` through runuser; root stands in for his sudo (`ares` has no password in CI).
"""
import base64
import hashlib
import io
import json
import os
import pathlib
import pwd
import queue
import re
import shutil
import socket
import sqlite3
import ssl
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import traceback

from channel import export_bytes

HERE = pathlib.Path('/usr/libexec/aresos-ci/control')
RECORD = pathlib.Path('/usr/share/aresos/manifest/control.json')
GENERATED = pathlib.Path('/usr/libexec/aresos-control/generated')
USER_MCP = pathlib.Path('/usr/share/aresos/control/user-mcp.json')
MANAGED_SETTINGS = pathlib.Path('/etc/claude-code/managed-settings.json')
UNIT = 'aresos-toold.service'
SOCKETS = pathlib.Path('/run/aresos-tools')
# The modes the merged control/aresos_control/daemon.py sets (PR #27): act and chrome for the owner's peer-checked
# calls (his CLI and proxies; Chrome's native host), admin for root only; the folder 0711.
# os/tests/test_control_vm.py reads them from daemon.py itself, so a change there fails until this follows.
SOCKET_MODES = {'act.sock': 0o666, 'admin.sock': 0o600, 'chrome.sock': 0o666}
SOCKET_FOLDER_MODE = 0o711
SANDBOX = {'Type': 'simple', 'User': 'aresos-tools', 'Group': 'aresos-tools', 'NoNewPrivileges': 'yes',
           'ProtectSystem': 'strict', 'ProtectHome': 'yes', 'PrivateTmp': 'yes', 'PrivateDevices': 'yes',
           'UMask': '0077', 'Restart': 'on-failure', 'CapabilityBoundingSet': '', 'AmbientCapabilities': '',
           # 18e: a service failing at every start ends failed (about 15 s with RestartSec=2); one crash restarts.
           'StartLimitIntervalUSec': '30s', 'StartLimitBurst': '5'}
SANDBOX_SETS = {'RestrictAddressFamilies': {'AF_UNIX', 'AF_INET', 'AF_INET6'},
                'ReadWritePaths': {'/run/aresos-tools', '/var/lib/aresos-tools', '/var/lib/aresos-operation-evidence'}}
OTHER = 'aresos-ci-other'
# 18e: the idle loop sleeps until its next deadline; at most one wake-up a second with nothing pending.
IDLE_WAKEUPS_PER_SECOND = 1
CLAUDE_VERSION = '2.1.319'
HOME = pathlib.Path(pwd.getpwnam('ares').pw_dir)
# control/tests/support.py's message(): testapp's fixture account.
MESSAGE = {'account': 'fixture', 'to': ['alpha', 'beta'], 'cc': [], 'bcc': ['hidden'], 'subject': 'Fixture message',
           'text': 'Written in full', 'attachments': []}
RAW_REQUEST = '''import json, socket, sys
connection = socket.socket(socket.AF_UNIX)
try:
    connection.connect(sys.argv[1])
except OSError as error:
    print(json.dumps({"connect_error": error.errno, "error_name": type(error).__name__}))
    raise SystemExit(0)
connection.sendall(sys.argv[2].encode() + b"\\n")
data = b""
while not data.endswith(b"\\n"):
    chunk = connection.recv(65536)
    if not chunk:
        break
    data += chunk
print(data.decode().strip() or "{}")
'''


def environment(user):
    home = HOME if user == 'ares' else pathlib.Path('/')
    # Not ~/.local/bin: in this guest it holds the CI layer's broken stand-ins for bash, python3, env and more
    # (package 21, os/ci/overlay/shadow-path.sh), which exit 97. Claude Code is called by its full path, as the
    # README's install step does.
    return [f'HOME={home}', 'LANG=C.UTF-8', 'PATH=/usr/local/bin:/usr/bin:/usr/sbin',
            # CI only: the disposable guest neither updates nor reports the pinned Claude Code.
            'DISABLE_AUTOUPDATER=1', 'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1']


def as_user(user):
    return ['runuser', '-u', user, '--', 'env', '-i', *environment(user)]


def run(argv, input=None, timeout=300, cwd='/'):
    result = subprocess.run(argv, input=input, capture_output=True, text=True, timeout=timeout, cwd=cwd)
    return dict(argv=argv, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def ok(result):
    assert result['returncode'] == 0, result
    return result


def cli(user, *argv, value=None):
    command = ['/usr/bin/aresos', *argv] + (['--input', json.dumps(value)] if value is not None else [])
    result = run([*as_user(user), *command])
    try:
        result['json'] = json.loads(result['stdout'])
    except ValueError:
        result['json'] = None
    return result


def answered(result):
    assert result['returncode'] == 0 and result['json'] and result['json'].get('ok') is True, result
    return result['json']


def refused(result, code=None):
    """A refusal: a non-zero exit, and when there is a JSON answer, ok false with the given code."""
    data = result['json']
    assert result['returncode'] != 0 and (data is None or data.get('ok') is False), result
    if code:
        assert data and data['error']['code'] == code, result
    return data['error'].get('code') if data else result['stderr'].strip()[-300:]


def sha256(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def files_out(values):
    out = {}
    for name, value in values.items():
        raw = value if isinstance(value, bytes) else value.encode() if isinstance(value, str) else \
            (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
        out['control/' + name] = export_bytes(raw)
    return out


def show(*names):
    result = ok(run(['systemctl', 'show', UNIT, *[f'--property={name}' for name in names]]))
    return dict(line.split('=', 1) for line in result['stdout'].splitlines() if '=' in line)


def wait_active(seconds=90):
    deadline = time.monotonic() + seconds
    while True:
        state = show('ActiveState', 'SubState')
        if state == {'ActiveState': 'active', 'SubState': 'running'}:
            return state
        assert time.monotonic() < deadline, ('the service did not become active', state)
        time.sleep(1)


def release_checks(*names):
    result = run(['/usr/bin/python3', '-I', str(HERE / 'release_checks.py'), *names])
    lines = result['stdout'].splitlines()
    assert result['returncode'] == 0 and lines[-1:] == ['CONTROL_RELEASE_CHECKS_PASS'], result
    return json.loads(lines[0]), result


# Check 1. Every path of Part A has the owner, mode and content of the commit; no links; no managed-mcp.json.
def files(request):
    record = json.loads(RECORD.read_text())
    assert record['format'] == 1 and record['source_revision'] == request['revision'], \
        (record.get('source_revision'), request['revision'])
    for key in ('files', 'links', 'directories'):
        assert record[key] == request['expected'][key], f'control.json {key} is not what the commit installs'
    entries = {**record['files'], **record['vendor'],
               **{name: dict(mode=mode, sha256=None) for name, mode in record['directories'].items()}}
    rows = []
    for name, entry in sorted(entries.items()):
        path = pathlib.Path(name)
        for part in (path, *path.parents):
            info = part.lstat()
            assert not stat.S_ISLNK(info.st_mode), f'{part} is a link'
            assert (info.st_uid, info.st_gid) == (0, 0) and not info.st_mode & 0o022, (str(part), oct(info.st_mode))
        info = path.lstat()
        mode = f'{stat.S_IMODE(info.st_mode):04o}'
        assert mode == entry['mode'], (name, mode, entry['mode'])
        digest = None
        if entry['sha256'] is None:
            assert stat.S_ISDIR(info.st_mode), name
        else:
            assert stat.S_ISREG(info.st_mode), name
            digest = sha256(path)
            assert digest == entry['sha256'], f'{name} differs from the commit'
        rows.append(dict(path=name, owner='root:root', mode=mode, sha256=digest, source=entry.get('source')))
    for root in ('/usr/libexec/aresos-control', '/usr/lib/aresos-control', '/usr/share/aresos/control',
                 '/etc/claude-code'):
        extra = sorted(str(path) for path in pathlib.Path(root).rglob('*') if str(path) not in entries)
        assert not extra, f'not recorded in control.json: {extra[:20]}'
    for link, target in record['links'].items():
        assert os.readlink(link) == target, (link, os.readlink(link))
    assert not pathlib.Path('/etc/claude-code/managed-mcp.json').exists(), 'managed-mcp.json exists'
    summary = dict(revision=record['source_revision'], files=len(record['files']), vendored=len(record['vendor']),
                   directories=len(record['directories']), links=record['links'])
    return dict(returncode=0, summary=summary,
                files=files_out({'files.json': dict(summary, entries=rows, managed_mcp_json=False)}))


# Agreed change 7: the booted guest's /etc/claude-code files equal the image's.
def claude_code_files(request):
    results, result = release_checks('claude_code_files')
    return dict(returncode=0, summary=results['claude_code_files']['value'],
                files=files_out({'etc-claude-code.json': results}))


# Agreed change 12: the rehearsal's check actions, run here exactly as the rehearsal would run them.
def release(request):
    # Both CI guests have the probe policy and host. The release rehearsal has neither.
    results, result = release_checks('service_user', 'unit', 'claude_code_files', 'folders', 'state_folders',
                                     'chrome_links', 'chrome_bundle', 'chrome_sites', 'gh', 'chrome_polkit')
    summary = {name: value['ok'] for name, value in results.items()}
    return dict(returncode=0, summary=summary, files=files_out({'release-checks.json': results,
                                                                'release-checks.txt': result['stdout']}))


def cgroup_sample(cgroup):
    tasks = {}
    for pid in (cgroup / 'cgroup.procs').read_text().split():
        for task in pathlib.Path(f'/proc/{pid}/task').iterdir():
            try:
                status = dict(line.split(':', 1) for line in (task / 'status').read_text().splitlines() if ':' in line)
                schedstat = task / 'schedstat'
                timeslices = int(schedstat.read_text().split()[2]) if schedstat.exists() else 0
            except (FileNotFoundError, ProcessLookupError):
                continue
            tasks[f'{pid}/{task.name}'] = dict(switches=int(status['voluntary_ctxt_switches']) +
                                               int(status['nonvoluntary_ctxt_switches']), timeslices=timeslices)
    cpu = dict(line.split() for line in (cgroup / 'cpu.stat').read_text().splitlines())
    return dict(time=time.monotonic(), tasks=tasks, cpu_usec=int(cpu['usage_usec']))


# Agreed change 14: the service's memory and wake-ups while nothing uses it. Runs before any check talks to it.
def idle(request):
    wait_active()
    seconds = int(request.get('seconds', 60))
    cgroup = pathlib.Path('/sys/fs/cgroup' + show('ControlGroup')['ControlGroup'])
    first = cgroup_sample(cgroup)
    time.sleep(seconds)
    last = cgroup_sample(cgroup)
    elapsed = last['time'] - first['time']
    common = first['tasks'].keys() & last['tasks'].keys()
    switches = sum(last['tasks'][task]['switches'] - first['tasks'][task]['switches'] for task in common)
    timeslices = sum(last['tasks'][task]['timeslices'] - first['tasks'][task]['timeslices'] for task in common)
    pids = (cgroup / 'cgroup.procs').read_text().split()
    rollup = {}
    for pid in pids:
        for line in pathlib.Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines():
            key, _, rest = line.partition(':')
            if key in ('Rss', 'Pss', 'Pss_Anon', 'Private_Dirty', 'Swap'):
                rollup[key] = rollup.get(key, 0) + int(rest.split()[0])
    def number(name):
        path = cgroup / name
        return int(path.read_text()) if path.exists() else None
    memory = cgroup / 'memory.stat'
    memory_stat = dict(line.split() for line in memory.read_text().splitlines()) if memory.exists() else {}
    summary = dict(seconds=round(elapsed, 1), processes=len(pids), threads=len(last['tasks']),
                   memory_current_bytes=number('memory.current'), memory_peak_bytes=number('memory.peak'),
                   anon_bytes=int(memory_stat.get('anon', -1)), file_bytes=int(memory_stat.get('file', -1)),
                   **{key.lower() + '_kib': value for key, value in rollup.items()},
                   context_switches=switches, wakeups_per_second=round(switches / elapsed, 3),
                   timeslices_per_second=round(timeslices / elapsed, 3),
                   cpu_ms=round((last['cpu_usec'] - first['cpu_usec']) / 1000, 1),
                   cpu_percent=round((last['cpu_usec'] - first['cpu_usec']) / 1e4 / elapsed, 4))
    files = files_out({'idle-footprint.json': dict(summary, cgroup=str(cgroup), memory_stat=memory_stat, first=first,
                                                   last=last)})
    # 18e's deadline loop (before it: about 10 wake-ups a second, runs 43577034725 and 43671243430).
    bounded = summary['processes'] == 1 and summary['threads'] == 1 and \
        switches <= IDLE_WAKEUPS_PER_SECOND * elapsed
    return dict(returncode=0 if bounded else 1, summary=summary, files=files,
                stderr='' if bounded else f'idle: {switches} switches in {elapsed:.1f} s over '
                f'{summary["threads"]} threads (at most {IDLE_WAKEUPS_PER_SECOND} a second, one thread)')


# The layer is complete for Mail (step 2b): the fixture names, the CA in the trust store, the runner's servers.
def fixtures(request):
    names = {name: sorted({entry[4][0] for entry in socket.getaddrinfo(name, None, socket.AF_INET)})
             for name in ('greenmail', 'dovecot')}
    assert names == {'greenmail': ['10.0.2.2'], 'dovecot': ['10.0.2.2']}, names
    context = ssl.create_default_context()
    servers = {}
    for name, port in (('greenmail', 3993), ('greenmail', 3465), ('dovecot', 993)):
        deadline = time.monotonic() + 60
        while True:
            try:
                with socket.create_connection((name, port), timeout=10) as raw, \
                        context.wrap_socket(raw, server_hostname=name) as tls:
                    tls.settimeout(10)
                    greeting = tls.recv(200).decode(errors='replace').strip()
                    servers[f'{name}:{port}'] = dict(tls=tls.version(), subject=dict(
                        item[0] for item in tls.getpeercert()['subject']), greeting=greeting[:80])
                break
            except OSError as error:
                assert time.monotonic() < deadline, f'{name}:{port}: {error}'
                time.sleep(2)
    anchors = sorted(str(path) for path in pathlib.Path('/etc/pki/ca-trust/source/anchors').iterdir())
    summary = dict(hosts=names, servers=servers, anchors=anchors)
    return dict(returncode=0, summary=summary, files=files_out({'fixtures.json': summary}))


def mcp_session(argv, timeout=60, calls=()):
    """initialize, then tools/list (every page), then each (name, arguments) of calls, as an MCP client over stdio."""
    process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, cwd='/')
    lines, errors = queue.Queue(), []

    def read():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)
    threading.Thread(target=read, daemon=True).start()
    threading.Thread(target=lambda: errors.extend(process.stderr), daemon=True).start()

    def send(message):
        process.stdin.write(json.dumps(dict(jsonrpc='2.0', **message)) + '\n')
        process.stdin.flush()

    def receive(ident):
        deadline = time.monotonic() + timeout
        while True:
            line = lines.get(timeout=max(0.1, deadline - time.monotonic()))
            assert line is not None, ('the server closed its output', ''.join(errors)[-4000:])
            message = json.loads(line)
            if message.get('id') == ident:
                assert 'result' in message, message
                return message['result']
    try:
        send(dict(id=1, method='initialize', params=dict(protocolVersion='2025-06-18', capabilities={},
                                                         clientInfo=dict(name='aresos-ci', version='1'))))
        initialized = receive(1)
        send(dict(method='notifications/initialized'))
        tools, cursor, ident = [], None, 1
        while True:
            ident += 1
            send(dict(id=ident, method='tools/list', params=dict(cursor=cursor) if cursor else {}))
            page = receive(ident)
            tools += page['tools']
            cursor = page.get('nextCursor')
            if not cursor:
                break
        answers = []
        for name, arguments in calls:
            ident += 1
            began = time.monotonic()
            send(dict(id=ident, method='tools/call', params=dict(name=name, arguments=arguments)))
            answers.append(dict(name=name, arguments=arguments, result=receive(ident),
                                seconds=round(time.monotonic() - began, 2)))
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return dict(initialize=initialized, tools=tools, calls=answers, returncode=process.returncode,
                stderr=''.join(errors)[-4000:])


def raw_request(user, name, request):
    result = ok(run([*as_user(user), '/usr/bin/python3', '-I', '-c', RAW_REQUEST, str(SOCKETS / name),
                     json.dumps(request)]))
    return json.loads(result['stdout'])


ADMIN_HINT = 'Admin commands need sudo: run sudo aresos admin testapp fixture_configure (same options).'


# Check 3. The daily user's entry points answer; another user and the admin socket refuse.
def entry_points(request):
    wait_active()
    listed = answered(cli('ares', 'testapp', 'list', value={'limit': 3}))
    assert len(listed['data']['items']) <= 3, listed
    log = answered(cli('ares', 'control', 'log'))
    servers = {}
    # Chrome with no browser connected (its browser side is brief 18c-b): a read is a clear refusal, never a hang.
    no_browser = [('tabs', {})]
    for app in ('mail', 'control', 'chrome'):
        session = mcp_session([*as_user('ares'), '/usr/bin/aresos-mcp', app], calls=no_browser if app == 'chrome' else ())
        generated = json.loads((GENERATED / f'{app}-tools.json').read_text())
        instructions = (GENERATED / f'{app}-instructions.txt').read_text()
        assert session['initialize'].get('instructions', '') + '\n' == instructions, (app, session['initialize'])
        served = session['tools']
        assert [tool['name'] for tool in served] == [tool['name'] for tool in generated], app
        for tool, shipped in zip(served, generated):
            assert {key: tool.get(key) for key in shipped} == shipped, (app, tool['name'])
        servers[app] = dict(server=session['initialize'].get('serverInfo'),
                            protocol=session['initialize'].get('protocolVersion'),
                            tools=[tool['name'] for tool in served],
                            keys_beyond_generated=sorted({key for tool, shipped in zip(served, generated)
                                                          for key in tool.keys() - shipped.keys()}),
                            calls=session['calls'])
    for call in servers['chrome']['calls']:
        assert call['result'].get('isError') is True and 'chrome_unavailable' in json.dumps(call['result']), call
    chrome_cli = cli('ares', 'chrome', 'tabs', value={})
    refused(chrome_cli, 'chrome_unavailable')
    # A throwaway second user, made in this VM only.
    if run(['getent', 'passwd', OTHER])['returncode'] != 0:
        ok(run(['useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', OTHER]))
    other = pwd.getpwnam(OTHER)
    # 18e: the owner without sudo is told to use it, before any socket or password prompt.
    admin_cli = cli('ares', 'admin', 'testapp', 'fixture_configure', value={'failure': 'none', 'refuse': []})
    refusals = dict(
        other_cli_act=refused(cli(OTHER, 'testapp', 'list', value={'limit': 3}), 'permission_denied'),
        other_act_socket=raw_request(OTHER, 'act.sock', {'v': 1, 'method': 'tools', 'app': 'testapp'}),
        ares_admin_socket=raw_request('ares', 'admin.sock', {'v': 1, 'method': 'tools', 'app': 'testapp'}),
        # chrome.sock is 0666 like act.sock; the service admits only the owner's native host (SO_PEERCRED).
        other_chrome_socket=raw_request(OTHER, 'chrome.sock', {'v': 1, 'method': 'hello'}),
        ares_admin_cli=refused(admin_cli, 'permission_denied'))
    assert refusals['other_act_socket'].get('error', {}).get('code') == 'permission_denied', refusals
    assert refusals['other_chrome_socket'].get('error', {}).get('code') == 'permission_denied', refusals
    refusals['ares_admin_cli_message'] = admin_cli['json']['error']['message']
    assert refusals['ares_admin_cli_message'] == ADMIN_HINT, refusals
    assert 'password' not in admin_cli['stderr'].lower(), admin_cli
    refusals['ares_chrome_cli_no_browser'] = dict(code=chrome_cli['json']['error']['code'],
                                                  message=chrome_cli['json']['error']['message'])
    # admin.sock is 0600 for aresos-tools: the kernel refuses the connection before the service's own check.
    assert refusals['ares_admin_socket'].get('error_name') == 'PermissionError', refusals
    proxy = run([*as_user(OTHER), '/usr/bin/aresos-mcp', 'testapp'], input='', timeout=60)
    assert proxy['returncode'] != 0 and 'requires the configured owner user' in proxy['stderr'], proxy
    refusals['other_proxy'] = dict(returncode=proxy['returncode'], stderr=proxy['stderr'].strip()[-300:])
    summary = dict(testapp_list_items=len(listed['data']['items']),
                   log_items=len(log['data'].get('items', [])) if isinstance(log['data'], dict) else None,
                   mcp=servers, other_user=dict(name=OTHER, uid=other.pw_uid), refusals=refusals)
    return dict(returncode=0, summary=summary, files=files_out({'entry-points.json': summary}))


def operation(op_id):
    return answered(cli('ares', 'testapp', 'operation_status', value={'operation_id': op_id}))['data']


# Check 4. The precondition check refuses while the managed file is changed; the file comes back as shipped.
def precondition(request):
    wait_active()
    record = json.loads(RECORD.read_text())['files'][str(MANAGED_SETTINGS)]
    original, info = MANAGED_SETTINGS.read_bytes(), MANAGED_SETTINGS.stat()
    assert hashlib.sha256(original).hexdigest() == record['sha256'] and \
        f'{stat.S_IMODE(info.st_mode):04o}' == record['mode'], 'the managed settings are not as shipped'
    prepared = answered(cli('ares', 'testapp', 'prepare_send', value=MESSAGE))
    op_id = prepared['data']['approval']['operation_id']
    settings = json.loads(original)
    removed = settings['permissions']['ask'][0]
    changes = [('group-writable', lambda: os.chmod(MANAGED_SETTINGS, stat.S_IMODE(info.st_mode) | 0o020)),
               (f'ask rule {removed} removed', lambda: MANAGED_SETTINGS.write_text(json.dumps(dict(
                   settings, permissions=dict(settings['permissions'], ask=settings['permissions']['ask'][1:])),
                   indent=2) + '\n'))]
    cases = []
    for name, change in changes:
        try:
            change()
            refusal = cli('ares', 'testapp', 'prepare_send', value=MESSAGE)
        finally:
            MANAGED_SETTINGS.write_bytes(original)
            os.chown(MANAGED_SETTINGS, 0, 0)
            os.chmod(MANAGED_SETTINGS, stat.S_IMODE(info.st_mode))
        restored = MANAGED_SETTINGS.stat()
        case = dict(change=name, code=refused(refusal, 'boundary_not_installed'),
                    message=refusal['json']['error'].get('message', '')[:300],
                    restored_sha256=sha256(MANAGED_SETTINGS), restored_mode=f'{stat.S_IMODE(restored.st_mode):04o}')
        assert case['restored_sha256'] == record['sha256'] and case['restored_mode'] == record['mode'], case
        cases.append(case)
    # A clean baseline: evidence first, then cancel, acknowledge the notice, and nothing is pending.
    before = operation(op_id)
    assert before['operation']['state'] == 'reserved', before
    cancelled = answered(cli('ares', 'testapp', 'operation_cancel', value={'operation_id': op_id}))['data']
    pending_notice = answered(cli('ares', 'control', 'pending'))['data']
    answered(cli('ares', 'testapp', 'notice_ack', value={'operation_id': op_id}))
    after = answered(cli('ares', 'control', 'pending'))['data']
    assert after['total'] == 0 and not after['items'], after
    summary = dict(prepared=dict(operation_id=op_id, state=before['operation']['state']), refusals=cases,
                   shipped_sha256=record['sha256'], baseline=dict(cancelled_state=cancelled['operation']['state'],
                                                                  pending_before_ack=pending_notice['total'],
                                                                  pending_after_ack=after['total']))
    return dict(returncode=0, summary=summary, files=files_out({'precondition.json': dict(
        summary, operation_before_cancel=before, pending_before_ack=pending_notice)}))


def user_servers():
    path = HOME / '.claude.json'
    return json.loads(path.read_text()).get('mcpServers', {}) if path.exists() else {}


def same_server(stored, shipped):
    """Equal in every shipped field; anything Claude Code adds must be empty."""
    return all(stored.get(key) == value for key, value in shipped.items()) and \
        not any(stored[key] for key in stored.keys() - shipped.keys())


# Check 5. The user-scope install step, word for word from control/README.md, twice, beside a server of his own.
def user_mcp(request):
    wait_active()
    as_ares = as_user('ares')
    target = HOME / f'.local/share/claude/versions/{CLAUDE_VERSION}'
    link = HOME / '.local/bin/claude'
    # Where Claude Code's own installer puts it.
    ok(run([*as_ares, 'install', '-D', '-m', '0755', str(HERE / f'claude-{CLAUDE_VERSION}'), str(target)]))
    ok(run([*as_ares, 'mkdir', '-p', str(link.parent)]))
    ok(run([*as_ares, 'ln', '-sfn', str(target), str(link)]))
    claude = str(link)
    version = ok(run([*as_ares, claude, '--version'], cwd=HOME))
    assert version['stdout'].startswith(CLAUDE_VERSION), version
    own = dict(type='stdio', command='/usr/bin/python3', args=['-I', str(HERE / 'own-mcp.py')])
    ok(run([*as_ares, claude, 'mcp', 'add-json', '--scope', 'user', 'notes', json.dumps(own)], cwd=HOME))
    before = user_servers()
    assert set(before) == {'notes'} and same_server(before['notes'], own), before
    shipped = json.loads(USER_MCP.read_text())
    runs = []
    for attempt in (1, 2):
        result = ok(run([*as_ares, '/usr/bin/bash', '-c', request['install']], cwd=HOME))
        servers = user_servers()
        runs.append(dict(attempt=attempt, returncode=result['returncode'], stdout=result['stdout'][-2000:],
                         stderr=result['stderr'][-2000:], servers=servers))
        assert sorted(servers) == sorted({'notes', *shipped}), servers
        assert servers['notes'] == before['notes'], ('his own entry changed', servers['notes'])
        for name, server in shipped.items():
            assert same_server(servers[name], server), (name, servers[name])
    # The harness adds testapp the same way (its entry is the shipped one with `proxy testapp`).
    testapp = json.loads(json.dumps(shipped['control']))
    assert testapp['args'][-2:] == ['proxy', 'control'], testapp
    testapp['args'][-1] = 'testapp'
    ok(run([*as_ares, claude, 'mcp', 'add-json', '--scope', 'user', 'testapp', json.dumps(testapp)], cwd=HOME))
    listed = ok(run([*as_ares, claude, 'mcp', 'list'], cwd=HOME, timeout=240))
    connected = {}
    for name in ('notes', *shipped, 'testapp'):
        lines = [line for line in listed['stdout'].splitlines() if line.startswith(name + ':')]
        assert len(lines) == 1 and 'Connected' in lines[0] and 'Failed' not in lines[0], (name, listed)
        connected[name] = lines[0][-40:]
    summary = dict(claude=version['stdout'].strip(), his_own=before['notes'], installed=sorted(shipped),
                   runs=len(runs), connected=connected)
    return dict(returncode=0, summary=summary, files=files_out({'user-mcp-install.json': dict(
        summary, before=before, after_runs=runs, mcp_list=listed['stdout'], shipped=shipped)}))


def denials(*pids):
    journal = run(['journalctl', '-b', '--no-pager', '-o', 'cat'], timeout=120)['stdout']
    lines = [line for line in journal.splitlines() if 'avc:' in line and 'denied' in line]
    audit = pathlib.Path('/var/log/audit/audit.log')
    if audit.exists():
        lines += [line for line in audit.read_text(errors='replace').splitlines()
                  if 'type=AVC' in line and 'denied' in line]
    marks = ('aresos', 'act.sock', 'admin.sock', 'chrome.sock', *[f'pid={pid} ' for pid in pids])
    return lines, [line for line in lines if any(mark in line for mark in marks)]


# /proc/<pid>/net/{tcp,tcp6,udp,udp6}: a TCP socket in state 0A (LISTEN) listens; a UDP socket in state 07 (CLOSE) is
# bound but unconnected, which is what `ss -l` lists as a UDP listener.
LISTENING_STATES = {'tcp': '0A', 'tcp6': '0A', 'udp': '07', 'udp6': '07'}


def listening_sockets(pids):
    """The listening TCP and bound, unconnected UDP sockets the processes hold, from their own fd tables and their
    network namespace's tables. A process whose fds can't be read raises: never an empty answer for "couldn't look"."""
    inodes = {}
    for pid in pids:
        for fd in pathlib.Path(f'/proc/{pid}/fd').iterdir():
            try:
                target = os.readlink(fd)
            except FileNotFoundError:
                continue
            if target.startswith('socket:['):
                inodes[int(target[len('socket:['):-1])] = pid
    found = []
    for pid in pids:
        for kind, state in LISTENING_STATES.items():
            table = pathlib.Path(f'/proc/{pid}/net/{kind}')
            if kind.endswith('6') and not table.exists():
                continue  # no IPv6 in this network namespace, so no IPv6 socket either
            for line in table.read_text().splitlines()[1:]:
                fields = line.split()
                if fields[3] == state and int(fields[9]) in inodes:
                    found.append(dict(kind=kind, local=fields[1], pid=inodes[int(fields[9])], inode=int(fields[9])))
    unique = {(item['kind'], item['inode']): item for item in found}
    return sorted(unique.values(), key=lambda item: (item['kind'], item['inode'])), len(inodes)


def network_listeners(cgroup):
    """REVIEW-A1 #7: the unit allows AF_INET and AF_INET6 (Mail's and Chrome's outbound connections), but the service
    listens on Unix sockets only (the brief's "Must not change"). Every process of the unit holds no listening TCP or
    UDP socket, by its own tables and by ss. A listener of this check's own proves both ways can see one."""
    pids = [int(pid) for pid in pathlib.Path('/sys/fs/cgroup' + cgroup, 'cgroup.procs').read_text().split()]
    assert pids, ('no process in the unit', cgroup)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as control:
        control.bind(('127.0.0.1', 0))
        control.listen(1)
        port = control.getsockname()[1]
        own, _ = listening_sockets([os.getpid()])
        listed = run(['ss', '-H', '-l', '-n', '-t', '-u', '-p'], timeout=60)
    assert listed['returncode'] == 0, listed
    control_seen = dict(proc=any(item['kind'] == 'tcp' and item['local'].endswith(f':{port:04X}') for item in own),
                        ss=any(f':{port} ' in line and f'pid={os.getpid()},' in line
                               for line in listed['stdout'].splitlines()))
    assert all(control_seen.values()), ('the check cannot see a listener of its own', control_seen, listed)
    held, sockets_held = listening_sockets(pids)
    by_ss = [line for line in listed['stdout'].splitlines()
             if any(f'pid={pid},' in line for pid in pids)]
    summary = dict(pids=pids, sockets_held=sockets_held, listening=held, ss_lines=by_ss, control_listener=control_seen)
    assert not held and not by_ss, ('the service listens on the network', summary)
    return summary


# Check 2. The service under its sandbox, started by the boot alone. Runs after checks 3 to 5, so its SELinux scan
# also covers what they made the service do.
def service(request):
    wait_active()
    properties = show(*SANDBOX, *SANDBOX_SETS, 'ActiveState', 'SubState', 'NRestarts', 'MainPID', 'UnitFileState',
                      'InvocationID', 'ControlGroup', 'DropInPaths', 'FragmentPath', 'ExecMainStartTimestamp')
    for key, value in SANDBOX.items():
        assert properties[key] == value, (key, properties[key], value)
    for key, value in SANDBOX_SETS.items():
        assert set(properties[key].split()) == value, (key, properties[key])
    assert (properties['NRestarts'], properties['UnitFileState']) == ('0', 'enabled'), properties
    # Fedora's drop-ins for every service may apply; none of the unit's own.
    assert UNIT not in properties['DropInPaths'], properties['DropInPaths']
    # Started once in this boot by systemd itself: the journal knows one invocation, the current one.
    journal = run(['journalctl', '-b', '-u', UNIT, '--no-pager', '-o', 'json', '--output-fields=INVOCATION_ID,'
                   '_SYSTEMD_INVOCATION_ID,MESSAGE'], timeout=120)
    invocations = set()
    for line in journal['stdout'].splitlines():
        entry = json.loads(line)
        for key in ('INVOCATION_ID', '_SYSTEMD_INVOCATION_ID'):
            if isinstance(entry.get(key), str):
                invocations.add(entry[key].replace('-', '').lower())
    assert invocations == {properties['InvocationID'].replace('-', '').lower()}, (invocations, properties)
    pid = int(properties['MainPID'])
    cmdline = pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
    assert b'/usr/libexec/aresos-control/launch.py' in cmdline and b'service' in cmdline, cmdline
    status = {}
    for line in pathlib.Path(f'/proc/{pid}/status').read_text().splitlines():
        key, _, rest = line.partition(':')
        status[key] = rest.strip()
    process = {key: status[key] for key in ('Uid', 'Gid', 'Groups', 'NoNewPrivs', 'CapInh', 'CapPrm', 'CapEff',
                                            'CapBnd', 'CapAmb', 'Seccomp')}
    assert process['Uid'].split() == ['250'] * 4 and process['Gid'].split() == ['250'] * 4, process
    assert process['NoNewPrivs'] == '1', process
    for key in ('CapInh', 'CapPrm', 'CapEff', 'CapBnd', 'CapAmb'):
        assert int(process[key], 16) == 0, (key, process[key])
    folder = SOCKETS.lstat()
    assert stat.S_ISDIR(folder.st_mode) and stat.S_IMODE(folder.st_mode) == SOCKET_FOLDER_MODE and \
        folder.st_uid == 250, folder
    sockets = {}
    for path in sorted(SOCKETS.iterdir()):
        info = path.lstat()
        sockets[path.name] = dict(socket=stat.S_ISSOCK(info.st_mode), mode=f'{stat.S_IMODE(info.st_mode):04o}',
                                  owner=[info.st_uid, info.st_gid])
    assert sockets == {name: dict(socket=True, mode=f'{mode:04o}', owner=[250, 250])
                       for name, mode in SOCKET_MODES.items()}, sockets
    network = network_listeners(properties['ControlGroup'])
    try:
        context = pathlib.Path(f'/proc/{pid}/attr/current').read_text().strip('\0\n')
    except OSError as error:
        context = f'unreadable: {error}'
    selinux = dict(getenforce=run(['getenforce'])['stdout'].strip(), process_context=context)
    every, ours = denials(pid)
    selinux.update(avc_denials_in_boot=len(every), avc_denials_naming_the_service=ours)
    assert not ours, ours
    security = run(['systemd-analyze', 'security', UNIT, '--no-pager'], timeout=120)
    unit_journal = run(['journalctl', '-b', '-u', UNIT, '--no-pager', '-o', 'short-monotonic'], timeout=120)
    summary = dict(properties=properties, process=process, sockets=sockets,
                   socket_folder=f'{SOCKET_FOLDER_MODE:04o} aresos-tools', network_listeners=network,
                   selinux=selinux, invocations=sorted(invocations))
    return dict(returncode=0, summary=dict(user=properties['User'], nrestarts=properties['NRestarts'],
                                           selinux=selinux['getenforce'], avc_total=len(every),
                                           network_listeners=len(network['listening'])),
                files=files_out({'unit.json': summary, 'security.txt': security['stdout'] + security['stderr'],
                                 'journal-aresos-toold.txt': unit_journal['stdout'][-500000:],
                                 'selinux.txt': json.dumps(selinux, indent=2) + '\n' + '\n'.join(every[-200:]) + '\n'}))


# Step 2b: checks 6 to 9 and check 2's SELinux scan again. Claude Code sessions (sessions.py with B1's driver and
# model double) and Mail's flows (control/ci/image/mail_flows.py) sit beside this file in the Control layer.
EVIDENCE = pathlib.Path('/var/tmp/aresos-ci-evidence')
RECEIVER = pathlib.Path('/var/lib/aresos-operation-evidence/receiver.sqlite')
PASSWORDS = pathlib.Path('/var/lib/aresos-tools/mail-passwords')
# Agreed change 6: CI only, under /run (gone at the next boot); the shipped unit and its config stay as they are.
DROP_IN = pathlib.Path('/run/systemd/system/aresos-toold.service.d/aresos-ci-fail.conf')
REMINDER = 'AresOS held/unfinished work'


def layer_modules():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import mail_flows
    import sessions
    return sessions, mail_flows


def systemctl(*args):
    return ok(run(['systemctl', *args], timeout=120))


def wait_state(state, seconds=90):
    deadline = time.monotonic() + seconds
    while True:
        current = show('ActiveState', 'SubState', 'Result', 'NRestarts')
        if current['ActiveState'] == state:
            return current
        assert time.monotonic() < deadline, (f'the service did not become {state}', current)
        time.sleep(1)


def wait_sockets(seconds=60):
    """Type=simple reports active before the daemon binds its sockets (step 2a's start-up gap): wait for the first
    answer, counting the misses."""
    misses, deadline = [], time.monotonic() + seconds
    while True:
        answer = cli('ares', 'control', 'pending')
        if answer['returncode'] == 0 and answer['json'] and answer['json'].get('ok'):
            return answer['json']['data'], misses
        misses.append((answer['json'] or {}).get('error', {}).get('code') or answer['stderr'][-200:])
        assert time.monotonic() < deadline, answer
        time.sleep(0.5)


def compact_requests(path):
    """Model requests repeat Claude Code's system prompt and tool list; after the first, keep their digests."""
    requests = json.loads(path.read_text())
    for request in requests[1:]:
        for key in ('system', 'tools'):
            if key in request:
                raw = json.dumps(request[key], sort_keys=True).encode()
                request[key] = dict(sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))
    path.write_text(json.dumps(requests, indent=1))


# An action answers in one channel frame (os/ci/channel.py: 4 MiB of JSON, its files in base64, a third larger): one
# tar stays below TAR_LIMIT, and all tars of one action together below TARS_BUDGET.
TAR_LIMIT = 1_000_000
TARS_BUDGET = 2_400_000


def tree_out(folder, limit=TAR_LIMIT):
    """One folder as a gzip tar named after it: rendered screens repeat a lot."""
    for path in folder.rglob('requests.json'):
        compact_requests(path)
    for keep_every_screen in (True, False):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            # Too large with every intermediate frame: keep the named screens the driver acted on or proved with.
            archive.add(folder, arcname=folder.name, filter=lambda info: info if keep_every_screen or
                        '-wait-' not in info.name else None)
        data = buffer.getvalue()
        if len(data) < limit:
            return data
    raise AssertionError(f'{folder.name}: {len(data)} bytes even without the intermediate screens (limit {limit})')


def packed(files, folders, errors):
    """Each folder of {evidence name: folder} as a tar into files, within the frame's budget. Every folder named is
    required evidence: one that is missing (REVIEW-X1 #4), or a tar that can't be made or doesn't fit, is left out and
    named in errors. The check fails, but it still returns its outcomes and records (run 43568250360: check 9's
    transcripts tar, 1,057,224 bytes, raised past its whole record). Returns each name's size, or None for one left
    out."""
    left, sizes = TARS_BUDGET, {}
    for name, folder in folders.items():
        if not folder.is_dir():
            errors.append(f'evidence {name} missing: no folder {folder}')
            sizes[name] = None
            continue
        limit = min(TAR_LIMIT, left)
        try:
            files[name] = tree_out(folder, limit)
        except Exception as error:
            errors.append(f'evidence {name} left out: {type(error).__name__}: {error}')
            sizes[name] = None
            continue
        sizes[name] = len(files[name])
        left -= sizes[name]
    return sizes


def turn_record(turn):
    return {key: value for key, value in turn.items() if key != 'tool_result'}


def write_as_owner(path, data):
    result = subprocess.run([*as_user('ares'), '/usr/bin/tee', str(path)], input=data, capture_output=True,
                            timeout=60)
    assert result.returncode == 0 and pathlib.Path(path).stat().st_uid == HOME.stat().st_uid, result.stderr


# Check 6 (with 18e: "quiet unless used", owner #254). Four Claude Code sessions as ares, his own MCP tool and hooks
# beside ours. The first starts healthy and stays unused through a stop; then it prepares and sends (it has used the
# tools) and goes through two outages. The second starts while the service has failed, after the desktop session
# came up again (agreed change 6), and gets our tools once the service is back, without a restart. The third leaves
# its send reserved (the owner answers No); the fourth, fresh and never using our tools, ends its turn while that
# work is held (SECURITY-REVIEW-A1 F1: PR #69's fix round, now merged, gives held work the usage gate).
# Per turn: (session, service during the turn, what his model calls, notices, his answer to our ask).
NOTE = 'mcp__notes__note'
LIST = 'mcp__testapp__list'
PREPARED = 'mcp__testapp__send'
ORDINARY_TURNS = [
    ('used-later', 'healthy', NOTE, 0, None), ('used-later', 'stopped, never used', NOTE, 0, None),
    ('used-later', 'started again', PREPARED, 0, 'Yes'), ('used-later', 'stopped, used', NOTE, 1, None),
    ('used-later', 'still stopped', NOTE, 0, None), ('used-later', 'still stopped', NOTE, 0, None),
    ('used-later', 'started again', NOTE, 0, None), ('used-later', 'stopped again', NOTE, 1, None),
    ('failed-fresh-session', 'failed', NOTE, 0, None), ('failed-fresh-session', 'still failed', LIST, 0, None),
    ('failed-fresh-session', 'recovered', LIST, 0, None),
    ('held-work', 'healthy, its send left reserved', PREPARED, 0, 'No'),
    ('fresh-beside-held', 'healthy, another session holds work', NOTE, 0, None)]
NOT_RUNNING = 'AresOS tools are not running'
# 18e fix round 2 (hooks.py REMINDER): the held-work Stop reason and the prompt context both end with these words,
# right after the held work's JSON. Only a session that used the tools gets either.
HELD_REMINDER = (" Don't complete, cancel, resend or acknowledge this work on your own: tell the owner what is "
                 "waiting, and let him decide.")
# The client's texts for a lost connection; a stopped service is never one any more (18e).
LOST = ('Service connection lost', 'operation_status')
# 18e check 10: a hook ends at once; the CLI and the proxies wait up to 3 s for a starting service, the hooks don't.
HOOK_SECONDS = 1.5


def ordinary_step(number, call):
    # Zero-padded: the double and the checks find a turn by its prompt as a substring.
    step = {'prompt': f'ORDINARY_OWNER_TURN_{number:02}', 'send': call}
    if call == NOTE:
        step['approval'] = {'word': f'turn{number}'}
    elif call == LIST:
        step['approval'] = {'limit': 3}
    else:
        step['prepare'] = {'name': 'mcp__testapp__prepare_send', 'input': MESSAGE}
    return step


def runtime_folder():
    """/run/user/<uid> of ares, where the proxies leave their marks (control/aresos_control/usage.py). The guest's
    greetd logs ares in (initial_session), which makes it; runuser opens no logind session. Only if it is missing,
    lingering (CI only, this throwaway guest) makes it without a login."""
    uid = pwd.getpwnam('ares').pw_uid
    path = pathlib.Path(f'/run/user/{uid}')
    record = dict(uid=uid, path=str(path), existed=path.is_dir(), linger_enabled=False,
                  sessions=run(['loginctl', 'list-sessions', '--no-legend'])['stdout'].strip()[-1000:],
                  user=run(['loginctl', 'show-user', 'ares', '-p', 'State', '-p', 'Linger', '-p', 'Sessions'])
                  ['stdout'].strip())
    if not record['existed']:
        ok(run(['loginctl', 'enable-linger', 'ares']))
        record['linger_enabled'] = True
        deadline = time.monotonic() + 30
        while not path.is_dir():
            assert time.monotonic() < deadline, ('no runtime folder after enable-linger', record)
            time.sleep(0.5)
    info = path.lstat()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid == uid and stat.S_IMODE(info.st_mode) == 0o700, record
    return path, record


def claude_process(sessions):
    """The running Claude Code (pid, start time): the top process of ares's claude binary, as its MCP servers see it."""
    target = os.path.realpath(sessions.CLAUDE)
    found = []
    for folder in pathlib.Path('/proc').iterdir():
        if not folder.name.isdigit():
            continue
        try:
            exe = os.readlink(folder / 'exe')
            argv0 = (folder / 'cmdline').read_bytes().split(b'\0')[0].decode(errors='replace')
            data = (folder / 'stat').read_bytes()
        except OSError:
            continue
        if exe == target or argv0 in (str(sessions.CLAUDE), target):
            fields = data[data.rindex(b')') + 2:].split()
            found.append((int(folder.name), int(fields[1]), int(fields[19])))
    pids = {pid for pid, _, _ in found}
    top = [(pid, start) for pid, parent, start in found if parent not in pids]
    assert len(top) == 1, ('not exactly one Claude Code', found)
    return top[0]


def marks_state(folder, uid):
    """Every entry of the marks folder, with its type, mode, owner and size; the two folders' own (private: 0700, the
    owner's) in `folders_private`. Records only: the checks come after the sessions."""
    state = dict(exists=folder.is_dir(), entries={})
    if not state['exists']:
        return state
    folders = {}
    for part in (folder.parent, folder):
        info = part.lstat()
        folders[part.name] = dict(directory=stat.S_ISDIR(info.st_mode), mode=f'{stat.S_IMODE(info.st_mode):04o}',
                                  uid=info.st_uid)
    state.update(folders=folders, folders_private=all(value == dict(directory=True, mode='0700', uid=uid)
                                                      for value in folders.values()))
    for path in sorted(folder.iterdir()):
        info = path.lstat()
        state['entries'][path.name] = dict(file=stat.S_ISREG(info.st_mode), mode=f'{stat.S_IMODE(info.st_mode):04o}',
                                           uid=info.st_uid, size=info.st_size)
    return state


def timed_cli(*argv):
    began = time.monotonic()
    result = cli('ares', *argv)
    error = (result['json'] or {}).get('error') or {}
    return dict(seconds=round(time.monotonic() - began, 2), returncode=result['returncode'],
                ok=bool(result['json'] and result['json'].get('ok')), code=error.get('code'),
                message=error.get('message'), stderr=result['stderr'][-300:])


def started():
    """systemctl start, then at once one call (18e: the client waits for the sockets; no transport error)."""
    systemctl('start', UNIT)
    return timed_cli('control', 'pending')


def stopped():
    systemctl('stop', UNIT)
    return wait_state('inactive')


def wait_failed(seconds=30):
    """The failed state the unit's start limit reaches on its own (18e), held for longer than RestartSec=2."""
    began = time.monotonic()
    while True:
        state = show('ActiveState', 'SubState', 'Result', 'NRestarts')
        if state['ActiveState'] == 'failed':
            reached = time.monotonic() - began
            time.sleep(4)
            again = show('ActiveState', 'SubState', 'Result', 'NRestarts')
            if again == state:
                return dict(state, seconds=round(reached, 1))
        assert time.monotonic() - began < seconds, ('the service did not stay failed', state)
        time.sleep(0.5)


def hook_timing(work):
    """The managed hooks exactly as Claude Code runs them (sh -c, as ares), the service stopped, an unmarked caller."""
    hooks = json.loads(MANAGED_SETTINGS.read_text())['hooks']
    timed = {}
    for event in ('UserPromptSubmit', 'Stop'):
        [entry] = hooks[event]
        [hook] = entry['hooks']
        payload = dict(session_id='ci-hook-timing', transcript_path=str(work / 'ci-hook-timing.jsonl'), cwd=str(work),
                       permission_mode='default', hook_event_name=event,
                       **({'prompt': 'CI'} if event == 'UserPromptSubmit' else {'stop_hook_active': False}))
        began = time.monotonic()
        result = run([*as_user('ares'), '/bin/sh', '-c', hook['command']], input=json.dumps(payload), timeout=60)
        timed[event] = dict(seconds=round(time.monotonic() - began, 3), returncode=result['returncode'],
                            stdout=result['stdout'][-300:], stderr=result['stderr'][-300:])
    return timed


def release_held(op_id):
    """A clean baseline after a case left work held (brief B2, "A clean baseline"): its evidence is saved first; then
    cancel what is still reserved and acknowledge the notice the cancel leaves."""
    record = dict(state=operation(op_id)['operation']['state'])
    if record['state'] == 'reserved':
        record['cancelled'] = answered(cli('ares', 'testapp', 'operation_cancel',
                                           value={'operation_id': op_id}))['data']['operation']['state']
    if answered(cli('ares', 'control', 'pending'))['data']['total']:
        record['notice_ack'] = cli('ares', 'testapp', 'notice_ack', value={'operation_id': op_id})['json']
    record['pending_after'] = answered(cli('ares', 'control', 'pending'))['data']['total']
    return record


# greetd starts its initial session (the auto-login of the image's /etc/greetd/config.toml) only when this file is
# missing: once per boot (greetd(5), "runfile").
GREETD_RUNFILE = pathlib.Path('/run/greetd.run')


def owner_sessions():
    """ares's logind sessions: id → its service, class, state, TTY and leader."""
    listed = run(['loginctl', 'show-user', 'ares', '--property=Sessions', '--value'])
    if listed['returncode'] != 0:
        return {}
    found = {}
    for session in listed['stdout'].split():
        shown = run(['loginctl', 'show-session', session, *[f'--property={name}' for name in (
            'Service', 'Class', 'State', 'TTY', 'Leader', 'Scope')]])
        found[session] = dict(line.split('=', 1) for line in shown['stdout'].splitlines() if '=' in line)
    return found


def desktop_with_service_failed(failed, diagnostics):
    """Agreed change 6 (REVIEW-A1 #1): with the service failed, the desktop session comes up as usual. The boot's
    greetd session is ended as a logout ends it (all of ares's processes, his runtime folder and his user manager;
    the checks' own runuser processes aren't his sessions); then greetd starts the auto-login once more, as at boot,
    and the CI layer's own session checks (checks.py's wait_session and desktop_session, the policy pass's) require
    the terminal and the desktop supervisor, Prism and the app helper in it. The service stays failed throughout."""
    import checks  # os/ci/overlay/checks.py, the CI layer's checks, beside actions.d in the guest
    began = time.monotonic()
    uid = pwd.getpwnam('ares').pw_uid
    before = owner_sessions()
    boot_sessions = sorted(session for session, values in before.items() if values.get('Service') == 'greetd')
    assert boot_sessions, ('no greetd session of ares to end', before)
    ok(run(['systemctl', 'stop', 'greetd.service'], timeout=120))
    ok(run(['loginctl', 'terminate-user', 'ares'], timeout=120))
    deadline = time.monotonic() + 180
    while True:
        left = dict(user=run(['loginctl', 'show-user', 'ares'])['returncode'] == 0,
                    runtime=pathlib.Path(f'/run/user/{uid}').exists(),
                    session_programs=run(['pgrep', '-u', 'ares', '-x', 'foot|labwc|prismlauncher'])['stdout'].split())
        if not any(left.values()):
            break
        assert time.monotonic() < deadline, ('ares was not logged out', left)
        time.sleep(1)
    logged_out = round(time.monotonic() - began, 1)
    # 18e's "marks vanish at logout" (its PLAN-GAP 7 here): his runtime folder went with the logout, the marks in it.
    marks_after_logout = pathlib.Path(f'/run/user/{uid}/aresos-control/used').exists()
    GREETD_RUNFILE.unlink(missing_ok=True)
    ok(run(['systemctl', 'start', 'greetd.service'], timeout=120))
    terminal = checks.wait_session()
    desktop = checks.desktop_session(diagnostics=diagnostics)
    after = owner_sessions()
    new_sessions = sorted(session for session, values in after.items() if values.get('Service') == 'greetd')
    assert new_sessions and not set(new_sessions) & set(boot_sessions), ('not a new desktop session', before, after)
    _, runtime = runtime_folder()
    assert runtime['existed'] and not runtime['linger_enabled'], ('the new session made no runtime folder', runtime)
    unit = show('ActiveState', 'Result', 'NRestarts')
    assert unit['ActiveState'] == 'failed' and unit['NRestarts'] == failed['NRestarts'], (
        'the service did not stay failed while the desktop came up', failed, unit)
    greetd = run(['systemctl', 'show', 'greetd.service', '--property=ActiveState', '--property=NRestarts',
                  '--property=Result'])['stdout'].split()
    return dict(seconds=round(time.monotonic() - began, 1), logged_out_seconds=logged_out, service=unit,
                marks_after_logout=marks_after_logout,
                sessions_before=before, sessions_after=after, greetd=greetd, terminals=terminal['stdout'].split(),
                desktop_state=desktop['state'], desktop_processes=desktop['processes'],
                prism_scope=desktop['prism_scope'], runtime=runtime, supervisor_log=desktop['supervisor_log'])


def held_context(requests_path, resume):
    """The held-work session's prompt context in the merged wording (18e fix round 2): the first of its model requests
    that carries held work is the one after the driver's resume prompt (its first prompt came before any use), and it
    holds REMINDER's words right after the held work's JSON. Read from the messages as Claude Code sent them."""
    if not pathlib.Path(requests_path).exists():
        return False
    for item in json.loads(pathlib.Path(requests_path).read_text()):
        text = json.dumps(item.get('messages'))
        if REMINDER in text:
            return resume in text and '}' + HELD_REMINDER in text
    return False


def ordinary(request):
    sessions, _ = layer_modules()
    wait_active()
    pending, _ = wait_sockets()
    assert pending['total'] == 0, pending
    sessions.prepare_home()
    out = EVIDENCE / 'ordinary'
    shutil.rmtree(out, ignore_errors=True)
    log = sessions.WORK / 'own-hooks.jsonl'
    log.unlink(missing_ok=True)
    settings = sessions.user_settings([NOTE, LIST, 'mcp__testapp__prepare_send'],
                                      {event: sessions.own_hook(event, log) for event in ('Stop', 'UserPromptSubmit')})
    runtime, runtime_record = runtime_folder()
    uid = runtime_record['uid']
    marks = runtime / 'aresos-control/used'
    service = {1: dict(**show('ActiveState', 'SubState'))}
    probes = dict(runtime=runtime_record)

    def used_later(number):
        index = number - 1
        if index == 1:
            service[number] = stopped()
            probes['marks_before_use'] = marks_state(marks, uid)
            probes['cli_while_stopped'] = timed_cli('control', 'pending')
            probes['hooks_while_stopped'] = hook_timing(sessions.WORK)
        elif index in (2, 6):
            probes[f'first_call_after_start_{number}'] = started()
            service[number] = show('ActiveState', 'SubState')
        elif index == 3:
            pid, start = claude_process(sessions)
            probes['session_key'] = key = f'{pid}-{start}'
            probes['marks_after_use'] = marks_state(marks, uid)
            probes['pending_after_use'] = answered(cli('ares', 'control', 'pending'))['data']
            # A clean baseline for the outages (a done send leaves nothing in runs so far; acknowledged if it does).
            for item in probes['pending_after_use'].get('notices') or []:
                if item.get('app') == 'testapp':
                    cli('ares', 'testapp', 'notice_ack', value={'operation_id': item['operation_id']})
            service[number] = stopped()
        elif index in (4, 5, 7):
            probes[f'marks_before_turn_{number}'] = marks_state(marks, uid)
            if index == 7:
                service[number] = stopped()

    def failed_fresh(number):
        index = number - 9
        if index == 1:
            pid, start = claude_process(sessions)
            probes['fresh_session_key'] = f'{pid}-{start}'
        elif index == 2:
            DROP_IN.unlink()
            systemctl('daemon-reload')
            systemctl('reset-failed', UNIT)
            probes[f'first_call_after_start_{number}'] = started()
            service[number] = show('ActiveState', 'SubState')

    def arm_failure(first):
        probes['marks_after_used_session'] = marks_state(marks, uid)
        DROP_IN.parent.mkdir(parents=True, exist_ok=True)
        # Only the failing start: the unit's own Restart=on-failure and start limit end it failed (18e).
        DROP_IN.write_text('# CI only (package 18c, B2 check 6): the service fails at every start.\n'
                           '[Service]\nExecStartPre=/usr/bin/false\n')
        systemctl('daemon-reload')
        start = run(['systemctl', 'start', UNIT], timeout=120)
        service[first] = dict(start_returncode=start['returncode'], **wait_failed())
        # Agreed change 6: armed before a fresh session starts, then the desktop session comes up as usual. A failure
        # here is the check's, but the sessions still run, so the run shows the rest.
        try:
            probes['desktop_with_service_failed'] = desktop_with_service_failed(service[first], probes)
        except Exception:
            errors.append('the desktop session with the service failed: ' + traceback.format_exc())

    def clean_baseline(first):
        pending = answered(cli('ares', 'control', 'pending'))['data']
        assert pending['total'] == 0, ('no clean baseline before the held work', pending)
        probes['marks_before_held_work'] = marks_state(marks, uid)

    def note_held(first):
        """The work the held-work session left: reserved, and in the pending list every hook reads."""
        held = cases['held-work']['turns'][0]['operation_id']
        probes['held_operation'] = held
        assert held, 'the held-work session prepared nothing'
        probes['held_operation_state'] = operation(held)['operation']['state']
        probes['pending_beside_held'] = answered(cli('ares', 'control', 'pending'))['data']
        probes['marks_beside_held'] = marks_state(marks, uid)
        assert held in json.dumps(probes['pending_beside_held']), ('the held work is not pending', probes)

    errors, cases = [], {}
    plan = [(number, *turn) for number, turn in enumerate(ORDINARY_TURNS, 1)]
    # (session, before it starts, before each of its turns). A session's own Claude Code starts with its first prompt,
    # so nothing waits before turn 1 (a request then could fall outside the turn's count).
    order = (('used-later', None, used_later), ('failed-fresh-session', arm_failure, failed_fresh),
             ('held-work', clean_baseline, None), ('fresh-beside-held', note_held, None))
    try:
        for case, before_session, before_turn in order:
            mine = [row for row in plan if row[1] == case]
            if before_session:
                before_session(mine[0][0])
            numbers = [number for number, *_ in mine]
            cases[case] = sessions.session(out / case, [ordinary_step(number, call) for number, _, _, call, *_ in mine],
                                           sessions.NORMAL, [answer for *_, answer in mine],
                                           before_turn=before_turn and (lambda index, hook=before_turn,
                                                                        numbers=numbers: hook(numbers[index])))
        probes['marks_after_sessions'] = marks_state(marks, uid)
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        if DROP_IN.exists():
            DROP_IN.unlink()
            run(['systemctl', 'daemon-reload'])
        if show('ActiveState')['ActiveState'] != 'active':
            run(['systemctl', 'reset-failed', UNIT])
            run(['systemctl', 'start', UNIT])
        # A clean baseline for checks 7 and 9 (brief B2): the held-work session's reservation, its evidence saved above.
        if probes.get('held_operation'):
            try:
                wait_sockets()
                probes['held_released'] = release_held(probes['held_operation'])
            except Exception:
                errors.append('releasing the held work: ' + traceback.format_exc())

    def expect(condition, *what):
        if not condition:
            errors.append(repr(what)[:3000])

    hooks = sessions.hook_lines(log)
    turns = [turn for case in cases.values() for turn in case['turns']]
    # His Stop hook per turn: his log in order, each turn from its UserPromptSubmit line to the next one; each run
    # recorded by the stop_hook_active it was given (run 43572578699: in a turn our hook blocks once, his runs only on
    # the attempt that ends the turn). The driver's resume prompt after a No goes on with the same turn.
    own_stops, current = {}, None
    for line in hooks:
        if line['event'] == 'UserPromptSubmit' and sessions.RESUME not in line['input'].get('prompt', ''):
            current = next((number for number, turn in enumerate(turns, 1)
                            if turn['prompt'] in line['input'].get('prompt', '')), None)
        elif line['event'] == 'Stop':
            own_stops.setdefault(current, []).append(line['input'].get('stop_hook_active'))
    rows = []
    for (number, case, state, call, notices, answer), turn in zip(plan, turns):
        result = turn['tool_result'] or {}
        screen = ' '.join(turn['on_screen'])
        told = [tail for tail in turn['continuation_tails'] if NOT_RUNNING in tail]
        row = dict(turn=number, session=case, service=state, call=call, **turn_record(turn),
                   tool_result=json.dumps(result)[:600], notices_expected=notices, notices=len(told),
                   notice_on_screen=NOT_RUNNING in screen,
                   own_user_prompt_submit_lines=sum(1 for line in hooks if line['event'] == 'UserPromptSubmit'
                                                    and turn['prompt'] in line['input'].get('prompt', '')),
                   own_stop_runs=own_stops.get(number, []),
                   extra_model_requests=turn['model_requests'] - (3 if call == PREPARED else 2))
        rows.append(row)
        expect(row['own_user_prompt_submit_lines'] == 1, 'his UserPromptSubmit hook', row)
        expect(1 <= len(row['own_stop_runs']) <= 1 + row['stop_continuations'], 'his Stop hook', row)
        expect(row['extra_model_requests'] == row['stop_continuations'], 'extra requests', row)
        hook_lines = ' '.join(line for line in turn['on_screen'] if 'hook' in line.lower())
        expect(not any(text in hook_lines or any(text in tail for tail in turn['continuation_tails']) for text in LOST),
               'a lost-connection text', row)
        if call == PREPARED and answer == 'Yes':
            # Used: a preparation and a send answered Yes; with the service up nothing changes (held work only).
            expect(turn['prompt_shown'] and turn['operation_id'] and not told and row['stop_continuations'] <= 1,
                   'the used turn', row)
            if turn['operation_id']:
                row['operation_state'] = operation(turn['operation_id'])['operation']['state']
                expect(row['operation_state'] == 'done', 'the send', row)
        elif call == PREPARED:
            # Used, and its send left reserved by his No: this session holds work, and its own Stop hook tells it so
            # (the gate is on use, and this session used the tools: its preparation's result named the operation).
            expect(turn['prompt_shown'] and turn['operation_id'] and not told, 'the No turn', row)
            if turn['operation_id']:
                row['operation_state'] = probes.get('held_operation_state')
                expect(row['operation_state'] == 'reserved', 'the send held by his No', row)
            expect(row['stop_continuations'] >= 1, 'the session that holds work is told', row)
            # In the merged wording: the Stop reason (the continuation's newest user text) and the resume prompt's
            # context (the first request of the session that carries the held work) end with REMINDER after the JSON.
            row['reminder_in_stop_reason'] = any('}' + HELD_REMINDER in tail for tail in turn['continuation_tails'])
            row['reminder_in_prompt_context'] = held_context(out / case / 'model/requests.json', sessions.RESUME)
            expect(row['reminder_in_stop_reason'] and row['reminder_in_prompt_context'], 'the held-work wording', row)
        else:
            expect((row['stop_continuations'], row['notices'], row['notice_on_screen']) ==
                   (notices, notices, bool(notices)), 'the notice', row)
            if not notices:
                expect(not hook_lines.count('hook error'), 'a hook error on screen', row)
        if call == NOTE:
            expect(not result.get('is_error') and f'OWN_NOTE turn{number}' in json.dumps(result), 'his tool', row)
            if not notices:
                # His own tool's turns: nothing of ours at all (a testapp result may name AresOS itself).
                expect(not any('AresOS' in line for line in turn['on_screen']), 'ours on screen', row)
        elif call == LIST:
            payloads = []
            for text in sessions.texts(result.get('content') or []):
                try:
                    payloads.append(json.loads(text))
                except ValueError:
                    pass
            row['list_answers'] = [dict(ok=p.get('ok'), code=(p.get('error') or {}).get('code')) for p in payloads
                                   if isinstance(p, dict)]
            if state == 'recovered':
                expect(not result.get('is_error') and dict(ok=True, code=None) in row['list_answers'],
                       'testapp list after the recovery, same session', row)
            else:
                expect('service_unavailable' in json.dumps(result), 'testapp list while failed', row)
    expect(len(turns) == len(ORDINARY_TURNS) and None not in own_stops, len(turns), own_stops.get(None))

    # The probes: marks, the client while stopped, the hooks' time, the failed state, the first calls after a start.
    key = probes.get('session_key')
    entries = lambda name: probes.get(name, {}).get('entries', {})  # noqa: E731
    mark_file = dict(file=True, mode='0600', uid=uid, size=0)
    expect(not entries('marks_before_use'), 'marks before any use', probes.get('marks_before_use'))
    expect(key and entries('marks_after_use') == {key: mark_file} and probes['marks_after_use'].get('folders_private'),
           'the mark after use', key, probes.get('marks_after_use'))
    for number, told in ((5, True), (6, True), (8, False)):
        expect(entries(f'marks_before_turn_{number}').get(f'{key}.told') == (mark_file if told else None),
               f'.told before turn {number}', probes.get(f'marks_before_turn_{number}'))
    expect(entries('marks_after_used_session') == {key: mark_file, f'{key}.told': mark_file}, 'after the used session',
           probes.get('marks_after_used_session'))
    fresh = probes.get('fresh_session_key')
    expect(fresh and fresh != key and not any(name.startswith(f'{fresh}') for name in entries('marks_after_sessions')),
           'the fresh session is unmarked', fresh, probes.get('marks_after_sessions'))
    # Agreed change 6 (REVIEW-A1 #1): the desktop session came up again while the service had failed.
    desktop = probes.get('desktop_with_service_failed') or {}
    expect(desktop.get('desktop_state', {}).get('state') == 'SETUP' and desktop.get('service', {}).get('ActiveState')
           == 'failed', 'the desktop session with the service failed', {k: v for k, v in desktop.items()
                                                                          if k != 'supervisor_log'})
    # SECURITY-REVIEW-A1 F1 (PR #69's fix round, merged, gives held work the usage gate): the held-work
    # session was marked as one that used the tools; the fresh session beside it was not, ended its turn without a
    # Stop block or an extra model request (the rows above), and none of its model requests carried the held work.
    held = probes.get('held_operation')
    held_marks = sorted(set(entries('marks_beside_held')) - set(entries('marks_before_held_work')))
    expect(len(held_marks) == 1 and entries('marks_beside_held')[held_marks[0]] == mark_file,
           'the held-work session is marked', probes.get('marks_before_held_work'), probes.get('marks_beside_held'))
    expect(entries('marks_after_sessions') == entries('marks_beside_held'), 'the session beside held work is unmarked',
           probes.get('marks_beside_held'), probes.get('marks_after_sessions'))
    carried, beside_requests = [], out / 'fresh-beside-held/model/requests.json'
    if beside_requests.exists():
        for index, item in enumerate(json.loads(beside_requests.read_text())):
            text = json.dumps([item.get('system'), item.get('messages')])
            if (held and held in text) or REMINDER in text:
                carried.append(index)
    beside = next((row for row in rows if row['session'] == 'fresh-beside-held'), None)
    holder = next((row for row in rows if row['session'] == 'held-work'), None) or {}
    held_work = {name: holder.get(name) for name in (
        'operation_state', 'model_requests', 'extra_model_requests', 'stop_continuations', 'resumed_after_no',
        'reminder_in_stop_reason', 'reminder_in_prompt_context', 'own_stop_runs', 'on_screen')}
    held_elsewhere = dict(operation_state=probes.get('held_operation_state'),
                          pending_total=(probes.get('pending_beside_held') or {}).get('total'),
                          requests_carrying_it=carried, released=probes.get('held_released'),
                          **{name: (beside or {}).get(name) for name in (
                              'model_requests', 'extra_model_requests', 'stop_continuations', 'own_stop_runs',
                              'on_screen')})
    expect(beside and not carried, 'the held work reached a session that never used the tools', held_elsewhere)
    expect((probes.get('held_released') or {}).get('pending_after') == 0, 'the held work released', held_elsewhere)
    down = probes.get('cli_while_stopped') or {}
    expect(down.get('code') == 'service_unavailable' and 'not running' in (down.get('message') or '') and
           'nothing was sent' in (down.get('message') or '') and 2.5 <= down.get('seconds', 0) <= 10,
           'the client while stopped', down)
    for event, hook in (probes.get('hooks_while_stopped') or {}).items():
        expect(hook['returncode'] == 0 and not hook['stdout'].strip() and hook['seconds'] < HOOK_SECONDS,
               f'the {event} hook while stopped', hook)
    expect(len(probes.get('hooks_while_stopped') or {}) == 2, 'the hooks were timed', probes.get('hooks_while_stopped'))
    for number in (3, 7, 11):
        first = probes.get(f'first_call_after_start_{number}') or {}
        expect(first.get('ok') is True and first.get('code') != 'transport_error', f'the first call before turn {number}',
               first)
    failed = service.get(9) or {}
    expect(failed.get('ActiveState') == 'failed' and failed.get('Result') in ('start-limit-hit', 'exit-code') and
           int(failed.get('NRestarts', 99)) <= 5 and failed.get('seconds', 99) <= 20, 'the failed state', failed)
    first = cases.get('used-later', {})
    offered, per_request = first.get('tools_offered', []), first.get('tools_per_request', [])
    # The Chrome tools are offered in his session as installed (user-mcp.json's chrome entry), every one of them, once
    # the servers are up (the session's last request; the first may go out before they connect).
    chrome = sorted(name for name in offered if name.startswith('mcp__chrome__'))
    shipped = sorted(f'mcp__chrome__{tool["name"]}' for tool in json.loads((GENERATED / 'chrome-tools.json').read_text()))
    expect(chrome == shipped, 'the session offered as Chrome tools', chrome, shipped)
    # The session started while the service had failed offers our tools once they connect (18e item 7).
    fresh_offered = cases.get('failed-fresh-session', {}).get('tools_offered', [])
    expect(LIST in fresh_offered, 'the fresh session offers ours',
           cases.get('failed-fresh-session', {}).get('tools_per_request'))
    after, _ = wait_sockets()
    expect(not after['total'], 'pending after check 6', after)
    summary = dict(turns=[{key_: row.get(key_) for key_ in (
        'turn', 'session', 'service', 'call', 'answer', 'model_requests', 'extra_model_requests', 'stop_continuations',
        'notices', 'own_stop_runs', 'seconds', 'active_seconds', 'on_screen')} for row in rows],
        own_stop_lines=sum(map(len, own_stops.values())), pending_after=after['total'],
        failed=failed, cli_while_stopped=down, hooks_while_stopped=probes.get('hooks_while_stopped'),
        first_calls_after_start={name: probes[name] for name in probes if name.startswith('first_call_after_start_')},
        runtime=runtime_record, tools_per_request=per_request,
        fresh_tools_per_request=cases.get('failed-fresh-session', {}).get('tools_per_request'),
        desktop_with_service_failed=dict(
            service=desktop.get('service'), desktop=(desktop.get('desktop_state') or {}).get('state'),
            latched=(desktop.get('desktop_state') or {}).get('latched'), seconds=desktop.get('seconds'),
            logged_out_seconds=desktop.get('logged_out_seconds'), marks_after_logout=desktop.get('marks_after_logout'),
            greetd_sessions=[sorted(session for session, values in (desktop.get(name) or {}).items()
                                    if values.get('Service') == 'greetd')
                             for name in ('sessions_before', 'sessions_after')]),
        held_work=held_work, held_elsewhere=held_elsewhere)
    files = {'ordinary/summary.json': dict(summary, rows=rows, service=service, probes=probes, settings=settings),
             'ordinary/own-hooks.jsonl': log.read_text() if log.exists() else ''}
    sizes = packed(files, {f'ordinary/{name}.tar.gz': out / name for name in cases}, errors)
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                evidence_bytes=sizes, files=files_out(files))


OUTSIDE_REFUSAL = 'Path is outside the allowed folders; choose ~/Documents or ~/Downloads.'


# Check 7. Mail under the real unit, through the installed entry points only; then one send through Claude Code.
def mail(request):
    sessions, mail_flows = layer_modules()
    wait_active()
    wait_sockets()
    onboarding = mail_flows.onboard(request['password'])
    confirmed = answered(cli('root', 'admin', 'mail', 'account_settings',
                             value={'id': mail_flows.ACCOUNT, 'sent_policy': 'client'}))['data']
    flows = mail_flows.Flows(cli, write_as_owner)
    errors, claude = [], None
    try:
        flows.run(request['seeded'])
        # 18e: the refusal names the configured folders (the image's proxy.json), nothing else.
        refusal = flows.record.get('outside_refused') or {}
        assert (refusal.get('code'), refusal.get('message')) == ('file_refused', OUTSIDE_REFUSAL), refusal
        composition = flows.compose('claude')
        sessions.prepare_home()
        sessions.user_settings(['mcp__mail__prepare_send'])
        step = {'prompt': 'MAIL_OWNER_TURN_1', 'send': 'mcp__mail__send', 'prepare': {
            'name': 'mcp__mail__prepare_send', 'input': {key: composition[key] for key in
                                                         ('composition_id', 'composition_hash')}}}
        shutil.rmtree(EVIDENCE / 'mail-claude', ignore_errors=True)
        claude = sessions.session(EVIDENCE / 'mail-claude', [step], sessions.NORMAL, ['Yes'])
        turn = claude['turns'][0]
        state = mail_flows.wait_until(lambda: (lambda s: s if s not in ('reserved', 'submitting') else None)(
            flows.state(turn['operation_id'])))
        flows.record['claude'] = dict(turn_record(turn), owner_answers=claude['owner_answers'], state=state)
        assert turn['prompt_shown'] and claude['owner_answers'] == 1 and state == 'done', flows.record['claude']
    except Exception:
        errors.append(traceback.format_exc())
    pending = answered(cli('ares', 'control', 'pending'))['data']
    if pending['total']:
        errors.append(f'pending after the Mail flows: {pending}')
    sent = {kind: dict(recipient=mail_flows.RECIPIENTS[kind], subject=mail_flows.SUBJECTS[kind])
            for kind in mail_flows.RECIPIENTS}
    summary = dict(account=flows.record.get('account', {}).get('ready'), sent=sent,
                   attachment_out=flows.record.get('attachment_out'), attachment_in=flows.record.get('attachment_in'),
                   outside_refused=flows.record.get('outside_refused'), claude=flows.record.get('claude'),
                   pending_after=pending['total'])
    files = {'mail-flows.json': dict(summary, flows=flows.record, onboarding=dict(
        result=onboarding['result'], stderr=onboarding['stderr']), account_settings=confirmed),
        'mail-onboarding-screens.txt': '\n----\n'.join(onboarding['screens'])}
    sizes = packed(files, {'mail-claude.tar.gz': EVIDENCE / 'mail-claude'}, errors)
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                evidence_bytes=sizes, files=files_out(files))


def find_key(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]
        value = list(value.values())
    if isinstance(value, list):
        for child in value:
            found = find_key(child, key)
            if found is not None:
                return found
    return None


def arrivals_in_receiver(op_id):
    """How often the operation's message arrived. testapp's receiver stores one row per recipient (MESSAGE has three),
    so one send is one row for each of them; the container's pin counts sends (one POST each). Run 43572578699
    compared rows with it (3 against 1)."""
    connection = sqlite3.connect(f'file:{RECEIVER}?mode=ro', uri=True)
    try:
        per_recipient = dict(connection.execute(
            'SELECT recipient, count(*) FROM arrivals WHERE op=? GROUP BY recipient', (op_id,)).fetchall())
        total = connection.execute('SELECT count(*) FROM arrivals').fetchone()[0]
    finally:
        connection.close()
    # A send reaches every recipient or none of them (no failure is configured in these cases).
    assert set(per_recipient) in (set(), set(MESSAGE['to'] + MESSAGE['cc'] + MESSAGE['bcc'])), per_recipient
    return max(per_recipient.values(), default=0), per_recipient, total


# (case, mode, extra user allow rules, user PermissionRequest hook, answer): brief B2 check 9's table.
ASK_CASES = [('normal-yes', 'normal', [], False, 'Yes'), ('skip-no', 'skip', [], False, 'No'),
             ('skip-user-allow-send', 'skip', ['mcp__testapp__send'], False, 'No'),
             ('normal-permission-user', 'normal', [], True, 'hook')]


# Check 9. The ask, interactive, against the installed managed files and the real service; a clean baseline
# before every case.
def interactive(request):
    sessions, _ = layer_modules()
    wait_active()
    wait_sockets()
    sessions.prepare_home()
    out = EVIDENCE / 'interactive'
    shutil.rmtree(out, ignore_errors=True)
    managed = sha256(MANAGED_SETTINGS)
    assert managed == json.loads(RECORD.read_text())['files'][str(MANAGED_SETTINGS)]['sha256'], managed
    rows, errors = [], []
    for case, mode, extra, hook, answer in ASK_CASES:
        row = dict(case=case, mode=mode, answer=answer)
        try:
            pending = answered(cli('ares', 'control', 'pending'))['data']
            assert pending['total'] == 0, ('no clean baseline', pending)
            log = sessions.WORK / f'permission-{case}.jsonl'
            log.unlink(missing_ok=True)
            hooks = {'PermissionRequest': sessions.own_hook('PermissionRequest', log, matcher='mcp__testapp__send')} \
                if hook else None
            row['user_settings'] = sessions.user_settings(['mcp__testapp__prepare_send', *extra], hooks)
            step = {'prompt': 'ASK_OWNER_TURN_1', 'send': 'mcp__testapp__send',
                    'prepare': {'name': 'mcp__testapp__prepare_send', 'input': MESSAGE}}
            before = sessions.transcript_files()
            try:
                result = sessions.session(out / case, [step], sessions.SKIP if mode == 'skip' else sessions.NORMAL,
                                          [answer])
            finally:
                # Only this case's transcripts (checks 6 and 7 wrote theirs before): its own tar, beside the case's.
                # B2 requires them: a copy that fails fails the check (REVIEW-X1 #4).
                try:
                    row['transcripts'] = sessions.transcripts(out / f'{case}-transcripts', before)
                except Exception as error:
                    row['transcripts'] = f'not copied: {type(error).__name__}: {error}'
                    errors.append(f'{case}: transcripts {row["transcripts"]}')
                if log.exists():
                    (out / case).mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(log, out / case / 'permission-hook.jsonl')
            # A case that ran wrote at least its own session's transcript.
            assert row['transcripts'] != [], f'{case}: Claude Code wrote no transcript in this case'
            turn = result['turns'][0]
            op_id = turn['operation_id']
            send_arrivals, per_recipient, receiver_total = arrivals_in_receiver(op_id)
            row['receiver_rows_per_recipient'] = per_recipient
            status = operation(op_id)
            reminder = [index for index, request_ in enumerate(json.loads(
                (out / case / 'model/requests.json').read_text())) if REMINDER in json.dumps(request_['messages'])]
            row.update(turn_record(turn), owner_answers=result['owner_answers'], send_arrivals=send_arrivals,
                       receiver_total=receiver_total, operation_state=status['operation']['state'],
                       status_arrivals=find_key(status, 'arrivals'), hook_calls=len(sessions.hook_lines(log)),
                       stop_reminder_in_continuation=any(REMINDER in json.dumps(c['messages'])
                                                         for c in result['continuations']),
                       requests_with_reminder=reminder,
                       tool_result_is_error=bool((turn['tool_result'] or {}).get('is_error')))
            # A clean baseline: evidence first, then cancel what is still reserved and acknowledge the notice.
            row['pending_before_cleanup'] = answered(cli('ares', 'control', 'pending'))['data']
            released = release_held(op_id)
            row.update({name: released[name] for name in ('cancelled', 'notice_ack') if name in released},
                       pending_after_cleanup=released['pending_after'])
            assert row['pending_after_cleanup'] == 0, ('no clean baseline after', case)
            # Both counts agree: the service's own record names the same recipients the receiver holds.
            assert sorted(row['status_arrivals'] or []) == sorted(per_recipient), row
            if answer == 'hook':
                observed = {key: row[key] for key in ('send_arrivals', 'hook_calls', 'owner_answers')}
                pinned = request['expected']['normal-permission-user']
                assert observed == pinned, f'STOP: differs from the container pin {pinned}: {observed}'
            else:
                assert row['prompt_shown'] and row['owner_answers'] == 1, f'STOP: no prompt of the ask: {row}'
                assert row['send_arrivals'] == (1 if answer == 'Yes' else 0), f'STOP: arrivals: {row}'
                assert row['operation_state'] == ('done' if answer == 'Yes' else 'reserved'), row
                if case == 'skip-no':
                    assert row['stop_reminder_in_continuation'], f'the reminder did not reach the model: {row}'
        except Exception:
            errors.append(f'{case}: ' + traceback.format_exc())
        rows.append(row)
    # The outcomes and the PermissionRequest record first: nothing after this may lose them.
    permission = {row['case']: {key: row.get(key) for key in ('prompt_shown', 'send_arrivals', 'hook_calls',
                                                               'owner_answers')}
                  for row in rows if row['answer'] == 'hook'}
    summary = dict(cases={row['case']: {key: row.get(key) for key in (
        'prompt_shown', 'owner_answers', 'send_arrivals', 'operation_state', 'hook_calls', 'stop_continuations',
        'stop_reminder_in_continuation', 'resumed_after_no', 'pending_after_cleanup')} for row in rows},
        permission_request=permission, managed_settings_sha256=managed,
        transcripts={row['case']: row.get('transcripts') for row in rows})
    files = {'interactive/summary.json': dict(summary, rows=rows), 'permission-request.json': permission}
    sizes = packed(files, {f'interactive/{name}.tar.gz': out / name for case, *_ in ASK_CASES
                           for name in (case, f'{case}-transcripts')}, errors)
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                evidence_bytes=sizes, files=files_out(files))


SCANNED = ('/var/lib/aresos-tools', '/var/lib/aresos-operation-evidence', str(HOME), '/tmp', '/var/tmp', '/var/log',
           '/run', '/root')
JOURNAL = ['journalctl', '--no-pager', '-o', 'export']


def tree_scanner():
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    import tree_scan
    return tree_scan


def search_for(needles, roots=SCANNED):
    """Check 8's search (REVIEW-X1 #2): every file under the roots, a FUSE mount there as root first and as its
    owner where root was refused (tree_scan.py), and the journal's export to its end. `errors` names whatever could
    not be searched, a runtime file that vanished unread included; check 8 fails on any. What root was refused is
    an error until the owner's walk names that very path as searched (RECHECK-X2 #2)."""
    scanner = tree_scanner()
    mounts = scanner.fuse_mounts(roots)
    found = scanner.scan(roots, needles, handover=[point for point, _, _ in mounts])
    refused = found.pop('refused')
    del found['covered']  # root's own walk has nothing to cover
    # scan() files a refusal under one of the handover points, so the loop below meets every one of them.
    assert set(refused) <= {point for point, _, _ in mounts}, refused
    found['fuse_mounts'], found['owner_walks'] = [], []
    for point, kind, uid in mounts:
        owner = pwd.getpwuid(uid).pw_name
        refusals = refused.get(point, [])
        found['fuse_mounts'].append(dict(mount=point, type=kind, owner=owner, root_refused=len(refusals)))
        if not refusals:
            continue  # root read all of it (allow_other, say): its files are in root's count
        # The needles go on stdin, never on a command line. The owner walks the whole mount, and is told which
        # paths root was refused (RECHECK-X2 #2), each with the number root's listing gave it.
        request = json.dumps(dict(roots=[point], needles=[needle.hex() for needle in needles],
                                  cover=[[path, inode] for path, inode, _ in refusals]))
        result = run([*as_user(owner), '/usr/bin/python3', '-I', str(HERE / 'tree_scan.py')], input=request,
                     timeout=600)
        if result['returncode'] != 0:
            found['errors'] += [refusal for _, _, refusal in refusals] + [
                f'{point} ({kind}) as {owner}: exit {result["returncode"]}: {result["stderr"][-500:]}']
            continue
        walked = json.loads(result['stdout'])
        # The owner's walk hands nothing on: what it can't read is an error of its own.
        assert not walked['refused'], walked['refused']
        for key in ('hits', 'vanished', 'errors'):
            found[key] += walked[key]
        # Root's refusal stands, as an error, unless the owner's walk met that very path and searched it, listed it
        # or found it not to be a file: a path that is gone by then, or that the owner's view leaves out, was never
        # searched by anyone.
        found['errors'] += [f"{refusal}, and {owner}'s walk did not search it either"
                            for path, _, refusal in refusals if path not in walked['covered']]
        # And it was that mount the owner walked: unmounted meanwhile, the walk was of the folder under it.
        if (point, kind, uid) not in scanner.fuse_mounts(roots):
            found['errors'].append(f"{point} ({kind}): no longer mounted after {owner}'s walk, so what root was "
                                   'refused there may not be what was walked')
        found['owner_walks'].append(dict(mount=point, type=kind, owner=owner, files=walked['files'][point],
                                         root_refused=len(refusals)))
    with tempfile.TemporaryFile() as stderr, subprocess.Popen(JOURNAL, stdout=subprocess.PIPE, stderr=stderr) as journal:
        in_journal = bool(scanner.found_in(journal.stdout, needles))
        code = journal.wait(timeout=120)
        stderr.seek(0)
        message = stderr.read()[-500:].decode(errors='replace')
    if code != 0:
        found['errors'].append(f'journal export exited {code}: {message}')
    found.update(in_journal=in_journal, journal_returncode=code, journal_stderr=message)
    return found


# Check 8. The app passwords: unreadable for ares; the per-run synthetic password in exactly the one file.
def passwords(request):
    secret = request['password'].encode()
    assert len(secret) >= 32, 'not the per-run password'
    _, mail_flows = layer_modules()
    user = mail_flows.USERNAME.encode()
    # The password itself, and the encoded forms a mail login carries (the forms Mail's own scrubber knows).
    needles = (secret, base64.b64encode(secret), base64.b64encode(b'\0' + user + b'\0' + secret),
               base64.b64encode(user + b'\0' + user + b'\0' + secret))
    refusals = dict(list_state=run([*as_user('ares'), '/usr/bin/ls', '/var/lib/aresos-tools']),
                    list_passwords=run([*as_user('ares'), '/usr/bin/ls', str(PASSWORDS)]))
    stored = sorted(path for path in PASSWORDS.iterdir())
    assert len(stored) == 1, f'{len(stored)} password files'
    refusals['read_password_file'] = run([*as_user('ares'), '/usr/bin/cat', str(stored[0])])
    for name, result in refusals.items():
        assert result['returncode'] != 0 and 'Permission denied' in result['stderr'] and not result['stdout'], name
        refusals[name] = dict(returncode=result['returncode'], stderr=result['stderr'].strip()[-200:])
    modes = {}
    for path, mode in ((PASSWORDS, 0o700), (stored[0], 0o600)):
        info = path.lstat()
        modes[str(path)] = dict(mode=f'{stat.S_IMODE(info.st_mode):04o}', owner=[info.st_uid, info.st_gid])
        assert stat.S_IMODE(info.st_mode) == mode and (info.st_uid, info.st_gid) == (250, 250), modes
    found = search_for(needles)
    hits = sorted({path if index == 0 else f'{path} (encoded form {index})' for path, index in found['hits']})
    operations = pathlib.Path('/var/lib/aresos-operation-evidence/operations.jsonl')
    summary = dict(password_sha256=hashlib.sha256(secret).hexdigest(), files_holding_it=hits,
                   journal_export_holds_it=found['in_journal'], journal_returncode=found['journal_returncode'],
                   journal_stderr=found['journal_stderr'], operations_jsonl_holds_it=operations.exists() and
                   bool(tree_scanner().holds(operations, needles)), forms_searched=len(needles),
                   scanned=found['files'], paths=found['paths'], fuse_mounts=found['fuse_mounts'],
                   owner_walks=found['owner_walks'], vanished=found['vanished'], errors=found['errors'], modes=modes,
                   refusals=refusals)
    # What couldn't be searched fails the check like a hit: "not found" must mean "looked everywhere".
    assert hits == [str(stored[0])] and not found['in_journal'] and not found['errors'], summary
    return dict(returncode=0, summary=dict(files_holding_it=len(hits), journal=found['in_journal'],
                                           files_searched=sum(found['files'].values()), paths=found['paths'],
                                           vanished=found['vanished'], fuse_mounts=found['fuse_mounts'],
                                           owner_walks=found['owner_walks']),
                files=files_out({'passwords.json': summary}))


# Check 2 again, after checks 6 to 9: no SELinux denial names the service, its files or its sockets.
def selinux_after(request):
    wait_active()
    journal = run(['journalctl', '-b', '-u', UNIT, '--no-pager', '-o', 'json', '--output-fields=_PID'], timeout=120)
    pids = sorted({json.loads(line).get('_PID') for line in journal['stdout'].splitlines()} - {None})
    every, ours = denials(show('MainPID')['MainPID'], *pids)
    summary = dict(getenforce=run(['getenforce'])['stdout'].strip(), avc_denials_in_boot=len(every),
                   avc_denials_naming_the_service=ours, service_pids=pids)
    assert summary['getenforce'] == 'Enforcing' and not ours, summary
    return dict(returncode=0, summary=dict(summary, avc_denials_naming_the_service=len(ours)), files=files_out({
        'selinux-after.txt': json.dumps(summary, indent=2) + '\n' + '\n'.join(every[-200:]) + '\n'}))


# The end of the pass: a restarted service comes back with the Mail account still ready and nothing pending.
def restart(request):
    ok(run(['systemctl', 'restart', UNIT]))
    state = wait_active()
    # Type=simple: "active" comes before the daemon has bound its sockets. A call in that gap got transport_error
    # (run 43556905450); since 18e the client waits up to 3 s for the sockets, so the first call answers.
    pending, misses = wait_sockets()
    assert pending['total'] == 0 and not misses, (pending, misses)
    summary = dict(state, nrestarts=show('NRestarts')['NRestarts'], pending=pending['total'],
                   calls_before_the_sockets_answered=misses)
    if request.get('mail_account'):
        accounts = answered(cli('ares', 'mail', 'accounts'))['data']['accounts']
        summary['mail_ready'] = [account['ready'] for account in accounts if account['id'] == request['mail_account']]
        assert summary['mail_ready'] == [True], accounts
    return dict(returncode=0, summary=summary, files=files_out({'restart.json': summary}))


# Main's handoff ("Chrome merged", partial index): the storage plan and timing tests of control/chrome_tests on the
# image's own Python and SQLite, against the installed aresos_control. The layer carries only the test modules.
STORAGE_SUITE = HERE / 'storage-suite'
STORAGE_TESTS = ('test_full_disk_reads', 'test_open_index_timing')
STORAGE_PROBE = '''import json, sqlite3, sys, aresos_control
print(json.dumps(dict(python=sys.version.split()[0], executable=sys.executable, sqlite=sqlite3.sqlite_version,
                      sqlite_module=sqlite3.__file__, aresos_control=aresos_control.__file__)))
'''


def storage_tests(request):
    work = pathlib.Path('/var/tmp/aresos-ci-storage')
    shutil.rmtree(work, ignore_errors=True)
    # test_engine.py keeps its scratch beside the checkout (<root>/.work), so the modules run from a folder the owner
    # can write; as `ares`, as control-base runs them unprivileged.
    shutil.copytree(STORAGE_SUITE, work / 'control')
    for path in (work, *work.rglob('*')):
        os.chown(path, HOME.stat().st_uid, HOME.stat().st_gid)
    tests = work / 'control/chrome_tests'
    # The service's own import path (launch.py: the installed tree, then the vendored dependencies); -B leaves no
    # bytecode beside the installed code.
    command = [*as_user('ares'), f'PYTHONPATH={tests}:/usr/libexec/aresos-control:/usr/lib/aresos-control/vendor',
               '/usr/bin/python3', '-B']
    probe = json.loads(ok(run([*command, '-c', STORAGE_PROBE], cwd=str(tests)))['stdout'])
    assert probe['aresos_control'] == '/usr/libexec/aresos-control/aresos_control/__init__.py', probe
    began = time.monotonic()
    result = run([*command, '-m', 'unittest', '-v', *STORAGE_TESTS], timeout=600, cwd=str(tests))
    output = result['stdout'] + result['stderr']
    ran = re.search(r'^Ran (\d+) tests? in', output, re.M)
    timing = next((json.loads(line.split(' ', 1)[1]) for line in output.splitlines()
                   if line.startswith('step7-timing ')), None)
    passed = result['returncode'] == 0 and re.search(r'^OK$', output, re.M) is not None
    summary = dict(probe, tests=int(ran[1]) if ran else None, passed=passed,
                   seconds=round(time.monotonic() - began, 1), timing=timing)
    shutil.rmtree(work, ignore_errors=True)
    return dict(returncode=0 if passed else 1, stderr='' if passed else output[-6000:], summary=summary,
                files=files_out({'storage-tests.json': summary, 'storage-tests.txt': output}))


ACTIONS = {'control-files': files, 'control-claude-code-files': claude_code_files, 'control-release': release,
           'control-idle': idle, 'control-fixtures': fixtures, 'control-entry-points': entry_points,
           'control-precondition': precondition, 'control-user-mcp': user_mcp, 'control-service': service,
           'control-ordinary': ordinary, 'control-mail': mail, 'control-interactive': interactive,
           'control-passwords': passwords, 'control-selinux': selinux_after, 'control-storage-tests': storage_tests,
           'control-restart': restart}
