"""Package 18c, B2: the Control checks in the booted CI guest (check_build=control).

checks.py loads this file from actions.d (agreed change 8), so Control's checks stay in os/ci/control/. Each action
returns its evidence as files for the runner (os/ci/control/control_vm.py), which prints the PASS line. The owner's
steps run as `ares` through runuser; root stands in for his sudo (`ares` has no password in CI).
"""
import hashlib
import io
import json
import os
import pathlib
import pwd
import queue
import shutil
import socket
import sqlite3
import ssl
import stat
import subprocess
import sys
import tarfile
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
# The modes today's control/aresos_control/daemon.py sets: act for the owner's peer-checked calls, admin and chrome
# for root only (Chrome's adapter, PR #27, may change chrome's).
SOCKET_MODES = {'act.sock': 0o666, 'admin.sock': 0o600, 'chrome.sock': 0o600}
SANDBOX = {'Type': 'simple', 'User': 'aresos-tools', 'Group': 'aresos-tools', 'NoNewPrivileges': 'yes',
           'ProtectSystem': 'strict', 'ProtectHome': 'yes', 'PrivateTmp': 'yes', 'PrivateDevices': 'yes',
           'UMask': '0077', 'Restart': 'on-failure', 'CapabilityBoundingSet': '', 'AmbientCapabilities': ''}
SANDBOX_SETS = {'RestrictAddressFamilies': {'AF_UNIX', 'AF_INET', 'AF_INET6'},
                'ReadWritePaths': {'/run/aresos-tools', '/var/lib/aresos-tools', '/var/lib/aresos-operation-evidence'}}
OTHER = 'aresos-ci-other'
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
    results, result = release_checks()
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
    return dict(returncode=0, summary=summary, files=files_out({'idle-footprint.json': dict(
        summary, cgroup=str(cgroup), memory_stat=memory_stat, first=first, last=last)}))


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


def mcp_session(argv, timeout=60):
    """initialize, then tools/list (every page), as an MCP client over stdio."""
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
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    return dict(initialize=initialized, tools=tools, returncode=process.returncode, stderr=''.join(errors)[-4000:])


def raw_request(user, name, request):
    result = ok(run([*as_user(user), '/usr/bin/python3', '-I', '-c', RAW_REQUEST, str(SOCKETS / name),
                     json.dumps(request)]))
    return json.loads(result['stdout'])


# Check 3. The daily user's entry points answer; another user and the admin socket refuse.
def entry_points(request):
    wait_active()
    listed = answered(cli('ares', 'testapp', 'list', value={'limit': 3}))
    assert len(listed['data']['items']) <= 3, listed
    log = answered(cli('ares', 'log'))
    servers = {}
    for app in ('mail', 'control'):
        session = mcp_session([*as_user('ares'), '/usr/bin/aresos-mcp', app])
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
                                                          for key in tool.keys() - shipped.keys()}))
    # A throwaway second user, made in this VM only.
    if run(['getent', 'passwd', OTHER])['returncode'] != 0:
        ok(run(['useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', OTHER]))
    other = pwd.getpwnam(OTHER)
    refusals = dict(
        other_cli_act=refused(cli(OTHER, 'testapp', 'list', value={'limit': 3}), 'permission_denied'),
        other_act_socket=raw_request(OTHER, 'act.sock', {'v': 1, 'method': 'tools', 'app': 'testapp'}),
        ares_admin_socket=raw_request('ares', 'admin.sock', {'v': 1, 'method': 'tools', 'app': 'testapp'}),
        ares_admin_cli=refused(cli('ares', 'admin', 'testapp', 'fixture_configure',
                                   value={'failure': 'none', 'refuse': []})))
    assert refusals['other_act_socket'].get('error', {}).get('code') == 'permission_denied', refusals
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
    assert stat.S_ISDIR(folder.st_mode) and stat.S_IMODE(folder.st_mode) == 0o711 and folder.st_uid == 250, folder
    sockets = {}
    for path in sorted(SOCKETS.iterdir()):
        info = path.lstat()
        sockets[path.name] = dict(socket=stat.S_ISSOCK(info.st_mode), mode=f'{stat.S_IMODE(info.st_mode):04o}',
                                  owner=[info.st_uid, info.st_gid])
    assert sockets == {name: dict(socket=True, mode=f'{mode:04o}', owner=[250, 250])
                       for name, mode in SOCKET_MODES.items()}, sockets
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
    summary = dict(properties=properties, process=process, sockets=sockets, socket_folder='0711 aresos-tools',
                   selinux=selinux, invocations=sorted(invocations))
    return dict(returncode=0, summary=dict(user=properties['User'], nrestarts=properties['NRestarts'],
                                           selinux=selinux['getenforce'], avc_total=len(every)),
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


def tree_out(folder, name):
    """One case folder as a gzip tar: rendered screens repeat a lot, and one action must stay below a frame."""
    for path in folder.rglob('requests.json'):
        compact_requests(path)
    for keep_every_screen in (True, False):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            # Too large with every intermediate frame: keep the named screens the driver acted on or proved with.
            archive.add(folder, arcname=name, filter=lambda info: info if keep_every_screen or
                        '-wait-' not in info.name else None)
        data = buffer.getvalue()
        if len(data) < 1_000_000:
            return data
    raise AssertionError(f'{name}: {len(data)} bytes even without the intermediate screens')


def turn_record(turn):
    return {key: value for key, value in turn.items() if key != 'tool_result'}


def write_as_owner(path, data):
    result = subprocess.run([*as_user('ares'), '/usr/bin/tee', str(path)], input=data, capture_output=True,
                            timeout=60)
    assert result.returncode == 0 and pathlib.Path(path).stat().st_uid == HOME.stat().st_uid, result.stderr


# Check 6. An ordinary session stays ordinary: his own MCP tool and hooks beside ours, with the service healthy,
# stopped in the middle of a session and started again, then failed (agreed change 6) before a fresh session.
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
    settings = sessions.user_settings(['mcp__notes__note'], {event: sessions.own_hook(event, log)
                                                            for event in ('Stop', 'UserPromptSubmit')})

    def step(number):
        return {'prompt': f'ORDINARY_OWNER_TURN_{number}', 'send': 'mcp__notes__note',
                'approval': {'word': f'turn{number}'}}
    service = {1: dict(state='healthy', **show('ActiveState', 'SubState'))}

    def stop_then_start(index):
        if index == 1:
            systemctl('stop', UNIT)
            service[2] = dict(state='stopped', **wait_state('inactive'))
        elif index == 2:
            systemctl('start', UNIT)
            wait_active()
            service[3] = dict(state='started again', **show('ActiveState', 'SubState'),
                              calls_before_the_sockets_answered=wait_sockets()[1])

    def recover(index):
        if index == 1:
            DROP_IN.unlink()
            systemctl('daemon-reload')
            systemctl('reset-failed', UNIT)
            systemctl('start', UNIT)
            wait_active()
            service[5] = dict(state='recovered', **show('ActiveState', 'SubState'),
                              calls_before_the_sockets_answered=wait_sockets()[1])
    errors, cases = [], {}
    try:
        cases['stopped-mid-session'] = sessions.session(out / 'stopped-mid-session', [step(1), step(2), step(3)],
                                                        sessions.NORMAL, [None, None, None], before_turn=stop_then_start)
        DROP_IN.parent.mkdir(parents=True, exist_ok=True)
        DROP_IN.write_text('# CI only (package 18c, B2 check 6): the service fails at every start.\n'
                           '[Service]\nExecStartPre=/usr/bin/false\n')
        systemctl('daemon-reload')
        service[4] = dict(state='failed', restart=run(['systemctl', 'restart', UNIT], timeout=120)['returncode'],
                          **wait_state('failed'))
        cases['failed-fresh-session'] = sessions.session(out / 'failed-fresh-session', [step(4), step(5)],
                                                         sessions.NORMAL, [None, None], before_turn=recover)
    except Exception:
        errors.append(traceback.format_exc())
    finally:
        if DROP_IN.exists():
            DROP_IN.unlink()
            run(['systemctl', 'daemon-reload'])
            run(['systemctl', 'reset-failed', UNIT])
            run(['systemctl', 'start', UNIT])
    hooks = sessions.hook_lines(log)
    turns = [turn for case in cases.values() for turn in case['turns']]
    rows = []
    for number, turn in enumerate(turns, 1):
        result = turn['tool_result'] or {}
        prompts = [line for line in hooks if line['event'] == 'UserPromptSubmit'
                   and turn['prompt'] in line['input'].get('prompt', '')]
        row = dict(turn=number, service=service.get(number, {}).get('state'), **turn_record(turn),
                   own_tool_ran=not result.get('is_error') and f'OWN_NOTE turn{number}' in json.dumps(result),
                   own_user_prompt_submit_lines=len(prompts),
                   extra_model_requests=turn['model_requests'] - 2)
        rows.append(row)
        try:
            assert row['own_tool_ran'] and row['own_user_prompt_submit_lines'] == 1, row
            assert row['extra_model_requests'] == row['stop_continuations'], row
            if row['service'] in ('healthy', 'started again', 'recovered'):
                assert row['stop_continuations'] == 0 and not any('AresOS' in line for line in row['on_screen']), row
            else:
                assert row['stop_continuations'] <= 1, ('the Stop guard did not hold', row)
        except AssertionError:
            errors.append(traceback.format_exc())
    stops = [line for line in hooks if line['event'] == 'Stop']
    if len(stops) != sum(1 + turn['stop_continuations'] for turn in turns) or len(turns) != 5:
        errors.append(f'his Stop hook ran {len(stops)} times over {len(turns)} turns')
    after, _ = wait_sockets()
    if after['total']:
        errors.append(f'pending after check 6: {after}')
    summary = dict(turns=[{key: row[key] for key in ('turn', 'service', 'model_requests', 'extra_model_requests',
                                                     'stop_continuations', 'seconds', 'on_screen', 'own_tool_ran')}
                          for row in rows], own_stop_lines=len(stops), pending_after=after['total'])
    files = {'ordinary/summary.json': dict(summary, rows=rows, service=service, settings=settings),
             'ordinary/own-hooks.jsonl': log.read_text() if log.exists() else ''}
    for name in cases:
        files[f'ordinary/{name}.tar.gz'] = tree_out(out / name, name)
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                files=files_out(files))


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
    if (EVIDENCE / 'mail-claude').exists():
        files['mail-claude.tar.gz'] = tree_out(EVIDENCE / 'mail-claude', 'mail-claude')
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                files=files_out(files))


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
    connection = sqlite3.connect(f'file:{RECEIVER}?mode=ro', uri=True)
    try:
        return [connection.execute(query, args).fetchone()[0] for query, args in (
            ('SELECT count(*) FROM arrivals WHERE op=?', (op_id,)), ('SELECT count(*) FROM arrivals', ()))]
    finally:
        connection.close()


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
            result = sessions.session(out / case, [step], sessions.SKIP if mode == 'skip' else sessions.NORMAL,
                                      [answer])
            turn = result['turns'][0]
            op_id = turn['operation_id']
            send_arrivals, receiver_total = arrivals_in_receiver(op_id)
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
            if row['operation_state'] == 'reserved':
                row['cancelled'] = answered(cli('ares', 'testapp', 'operation_cancel',
                                                value={'operation_id': op_id}))['data']['operation']['state']
            if answered(cli('ares', 'control', 'pending'))['data']['total']:
                row['notice_ack'] = cli('ares', 'testapp', 'notice_ack', value={'operation_id': op_id})['json']
            row['pending_after_cleanup'] = answered(cli('ares', 'control', 'pending'))['data']['total']
            assert row['pending_after_cleanup'] == 0, ('no clean baseline after', case)
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
    copied = sessions.transcripts(out / 'transcripts')
    permission = {row['case']: {key: row.get(key) for key in ('prompt_shown', 'send_arrivals', 'hook_calls',
                                                               'owner_answers')}
                  for row in rows if row['answer'] == 'hook'}
    summary = dict(cases={row['case']: {key: row.get(key) for key in (
        'prompt_shown', 'owner_answers', 'send_arrivals', 'operation_state', 'hook_calls', 'stop_continuations',
        'stop_reminder_in_continuation', 'resumed_after_no', 'pending_after_cleanup')} for row in rows},
        permission_request=permission, managed_settings_sha256=managed, transcripts=len(copied))
    files = {'interactive/summary.json': dict(summary, rows=rows, transcripts=copied),
             'permission-request.json': permission}
    for case, *_ in ASK_CASES:
        if (out / case).exists():
            files[f'interactive/{case}.tar.gz'] = tree_out(out / case, case)
    if (out / 'transcripts').exists():
        files['interactive/transcripts.tar.gz'] = tree_out(out / 'transcripts', 'transcripts')
    return dict(returncode=1 if errors else 0, stderr='\n'.join(errors)[-6000:], summary=summary,
                files=files_out(files))


def holds(path, secret):
    with open(path, 'rb') as stream:
        tail = b''
        while chunk := stream.read(1 << 20):
            if secret in tail + chunk:
                return True
            tail = chunk[-len(secret):]
    return False


SCANNED = ('/var/lib/aresos-tools', '/var/lib/aresos-operation-evidence', str(HOME), '/tmp', '/var/tmp', '/var/log',
           '/run', '/root')


# Check 8. The app passwords: unreadable for ares; the per-run synthetic password in exactly the one file.
def passwords(request):
    secret = request['password'].encode()
    assert len(secret) >= 32, 'not the per-run password'
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
    hits, counts = [], {}
    for root in SCANNED:
        scanned = unreadable = 0
        for folder, _, names in os.walk(root):
            for name in names:
                path = os.path.join(folder, name)
                try:
                    if not stat.S_ISREG(os.lstat(path).st_mode):
                        continue
                    scanned += 1
                    if holds(path, secret):
                        hits.append(path)
                except OSError:
                    unreadable += 1
        counts[root] = dict(files=scanned, unreadable=unreadable)
    journal = subprocess.Popen(['journalctl', '--no-pager', '-o', 'export'], stdout=subprocess.PIPE)
    in_journal, tail = False, b''
    while chunk := journal.stdout.read(1 << 20):
        in_journal = in_journal or secret in tail + chunk
        tail = chunk[-len(secret):]
    journal.wait(timeout=120)
    hits = sorted(set(hits))
    operations = pathlib.Path('/var/lib/aresos-operation-evidence/operations.jsonl')
    summary = dict(password_sha256=hashlib.sha256(secret).hexdigest(), files_holding_it=hits,
                   journal_export_holds_it=in_journal, operations_jsonl_holds_it=operations.exists() and
                   holds(operations, secret), scanned=counts, modes=modes, refusals=refusals)
    assert hits == [str(stored[0])] and not in_journal, summary
    return dict(returncode=0, summary=dict(files_holding_it=len(hits), journal=in_journal),
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
    # Type=simple: "active" comes before the daemon has bound its sockets. A call in that gap gets transport_error
    # (seen in run 43556905450); wait for the first answer, counting the misses.
    pending, misses = wait_sockets()
    assert pending['total'] == 0, pending
    summary = dict(state, nrestarts=show('NRestarts')['NRestarts'], pending=pending['total'],
                   calls_before_the_sockets_answered=misses)
    if request.get('mail_account'):
        accounts = answered(cli('ares', 'mail', 'accounts'))['data']['accounts']
        summary['mail_ready'] = [account['ready'] for account in accounts if account['id'] == request['mail_account']]
        assert summary['mail_ready'] == [True], accounts
    return dict(returncode=0, summary=summary, files=files_out({'restart.json': summary}))


ACTIONS = {'control-files': files, 'control-claude-code-files': claude_code_files, 'control-release': release,
           'control-idle': idle, 'control-fixtures': fixtures, 'control-entry-points': entry_points,
           'control-precondition': precondition, 'control-user-mcp': user_mcp, 'control-service': service,
           'control-ordinary': ordinary, 'control-mail': mail, 'control-interactive': interactive,
           'control-passwords': passwords, 'control-selinux': selinux_after, 'control-restart': restart}
