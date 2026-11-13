"""Linux container supervisor. Root only creates synthetic fixtures and users;
all attacks and the native CLI run as the unprivileged fixture owner.
"""
import hashlib
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

ROOT = Path('/opt/aresos-control')
OUT = Path('/evidence')
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT))
MODE = os.environ.get('FILTER_MODE', 'present')
FIXTURES = json.loads((ROOT / 'fixtures.json').read_text())
ENV = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/home/assistant',
       'USER': 'assistant', 'LOGNAME': 'assistant', 'TERM': 'xterm-256color', 'LANG': 'C.UTF-8', 'DISABLE_AUTOUPDATER': '1',
       'CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC': '1',
       'CLAUDE_CODE_AUTO_CONNECT_IDE': 'false'}


def owner():
    os.setgroups([])
    os.setgid(10001)
    os.setuid(10001)


def run(args, name, env=None, timeout=90, required=True, input=None):
    result = subprocess.run(args, preexec_fn=owner, cwd='/home/assistant/work',
                            env=env or ENV, capture_output=True, text=True, timeout=timeout, input=input)
    log = f'COMMAND {json.dumps(args)}\nEXIT {result.returncode}\n{result.stdout}{result.stderr}'
    (OUT / (name + '.txt')).write_text(log)
    print(log, flush=True)
    if required:
        assert result.returncode == 0, name
    return result


def put(path, text='synthetic fixture\n', uid=10001):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chown(path, uid, uid)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert MODE in ('present', 'absent')
    print('VERSIONS ' + (ROOT / 'pins.json').read_text().strip(), flush=True)
    for source in [ROOT / 'sandbox.json', ROOT / 'native-pin.json', Path('/etc/claude-code/managed-settings.json'),
                   ROOT / 'optional-sandbox.json']:
        (OUT / source.name).write_bytes(source.read_bytes())
    for args in (['uname', '-a'], ['bwrap', '--version'], ['node', '--version'], ['claude', '--version']):
        run(args, 'version-' + args[0])
    for path in FIXTURES['reads'] + FIXTURES['writes']:
        if not path.startswith(('/etc/', '/opt/')):
            put(path, '{}\n' if path.endswith('.json') else 'synthetic fixture\n')
    for path in FIXTURES['notebooks']:
        put(path, json.dumps({'cells': [{'cell_type': 'code', 'execution_count': None,
             'metadata': {}, 'outputs': [], 'source': ['synthetic_fixture = 1']}],
             'metadata': {}, 'nbformat': 4, 'nbformat_minor': 5}))
    # Claude's global configuration must be valid. None of these are real tokens.
    put('/home/assistant/.claude.json', '{}\n')
    put('/home/assistant/outside.txt')
    put('/home/assistant/.claude/settings.json', (ROOT / 'optional-sandbox.json').read_text())
    put('/home/assistant/work/.claude/settings.json', '{}\n')
    put('/home/assistant/work/.claude/settings.local.json', '{}\n')
    put('/home/assistant/work/.mcp.json', '{"mcpServers":{}}\n')
    for path in FIXTURES['writes']:
        put(path + '.boundary-replacement', 'replacement\n', uid=0 if path.startswith(('/etc/', '/opt/')) else 10001)
    # Deterministic receiver hostname: the proxy lives outside the sandbox netns.
    with open('/etc/hosts', 'a') as hosts:
        hosts.write('\n127.0.0.1 blocked.boundary.localhost\n')
    # Every directory under the synthetic home belongs to the owner, so DAC
    # cannot falsely make an owner-writable startup path look sandbox-protected.
    for folder, dirs, files in os.walk('/home/assistant'):
        os.chown(folder, 10001, 10001)
    for path in ['/var/lib/aresos-tools/state.sqlite', '/var/lib/aresos-tools/passwords.json']:
        os.chown(path, 10002, 10002)
        os.chmod(path, 0o600)
    os.chown('/var/lib/aresos-tools', 10002, 10002)
    os.chmod('/var/lib/aresos-tools', 0o700)
    Path('/run/aresos-tools').mkdir(exist_ok=True)
    os.chown('/run/aresos-tools', 10002, 10001)
    os.chmod('/run/aresos-tools', 0o750)
    Path('/home/assistant/work/act-alias.sock').symlink_to('/run/aresos-tools/act.sock')
    # A regular stand-in proves /dev/uinput is hidden, without host input devices.
    put('/dev/uinput', 'synthetic input device\n')
    log = open(OUT / 'stub.txt', 'w+')
    stub = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT / 'stub.py')], stdout=log, stderr=log)
    try:
        for _ in range(100):
            if 'STUB_READY' in (OUT / 'stub.txt').read_text():
                break
            assert stub.poll() is None, 'stub failed to start'
            time.sleep(.05)
        else:
            raise AssertionError('stub readiness timeout')
        # Positive controls: every listener receives a connection before attacks.
        for name, address in FIXTURES['sockets'].items():
            code = ('import socket; s=socket.socket(socket.AF_UNIX); '
                    f's.connect({(chr(0)+address[1:] if address.startswith("@") else address)!r})')
            if name == 'admin':
                subprocess.run(['/usr/bin/python3', '-I', '-c', code], check=True)
            else:
                run(['/usr/bin/python3', '-I', '-c', code], 'positive-' + name)
        run(['/usr/bin/python3', '-I', '-c',
             'import socket; s=socket.create_connection(("127.0.0.1",18080)); s.sendall(b"GET /positive HTTP/1.1\\r\\nHost: localhost\\r\\n\\r\\n"); print(s.recv(100))'], 'positive-network')
        # Reads of owner cookies/auth and writes to startup files really work
        # outside the sandbox. Service secrets and admin are denied by DAC.
        for path in FIXTURES['reads'][2:]:
            run(['/usr/bin/python3', '-I', '-c', f'open({path!r},"rb").read()'], 'positive-read-' + Path(path).name)
        for path in FIXTURES['writes']:
            if path.startswith('/home/'):
                run(['/usr/bin/python3', '-I', '-c', f'open({path!r},"ab").close()'], 'positive-write-' + str(FIXTURES['writes'].index(path)))
        # Identical same-directory rename succeeds with owner rights outside containment.
        for index, path in enumerate(FIXTURES['writes']):
            code = f'import os; p={path!r}; s=p+".boundary-replacement"; os.replace(s,p); os.replace(p,s)'
            original = Path(path).read_bytes()
            if path.startswith('/home/'):
                run(['/usr/bin/python3', '-I', '-c', code], 'positive-replace-' + str(index))
            else:
                # Root-owned image files are already protected by DAC. Root is
                # the only identity with a valid outside replacement control.
                subprocess.run(['/usr/bin/python3', '-I', '-c', code], check=True)
                print('POSITIVE_REPLACE_ROOT ' + path, flush=True)
            put(path, original.decode(), uid=10001 if path.startswith('/home/') else 0)
        from native import native_checks
        if MODE == 'absent':
            for helper in ROOT.glob('node_modules/@anthropic-ai/sandbox-runtime/vendor/seccomp/*/apply-seccomp'):
                helper.unlink()
        native_error = None
        try:
            native_checks(run, put, MODE,
                          {p: digest(p) for p in FIXTURES['reads'] + FIXTURES['writes'] + FIXTURES['notebooks'] + ['/dev/uinput']}, stub)
        except Exception as error:
            import traceback
            native_error = traceback.format_exc()
            (OUT / 'native-failure.txt').write_text(native_error)
            print(native_error, flush=True)
        # Do not lose standalone evidence when a native qualification
        # check fails. The entire workflow still fails at the end.

        # Run network positive controls before the zero-arrival observation window.
        config = ROOT / 'sandbox.json'
        original = config.read_bytes()
        allowed = json.loads(original)
        allowed['network']['allowedDomains'] = ['blocked.boundary.localhost']
        config.write_text(json.dumps(allowed))
        try:
            for suffix, tunnel in [('http', ''), ('connect', '--proxytunnel ')]:
                command = "curl --noproxy '' --silent --show-error --fail --max-time 5 " + tunnel + 'http://blocked.boundary.localhost:18080/payload'
                receiver_before = (OUT / 'stub.txt').read_text().count('GET /payload HTTP/1.1')
                positive = run(['/usr/local/bin/node', str(ROOT / 'run.mjs'), command], 'positive-proxy-' + suffix)
                assert positive.stdout.strip() == 'OK'
                assert (OUT / 'stub.txt').read_text().count('GET /payload HTTP/1.1') > receiver_before
            # Mutation control: running the SAME hostile harness with the
            # receiver allowed must fail its denial assertions, by two routes.
            mutation = run(['/usr/local/bin/node', str(ROOT / 'run.mjs'),
                            '/usr/bin/python3 -I /opt/aresos-control/hostile.py'],
                           'network-policy-mutation', required=False)
            mutation_rows = [json.loads(line[8:]) for line in mutation.stdout.splitlines() if line.startswith('HOSTILE ')]
            opened = [r['name'] for r in mutation_rows if not r['blocked'] and not r.get('unqualified')]
            assert mutation.returncode == 1 and opened == ['network:proxy-http', 'network:proxy-connect'], opened
            print('NETWORK_MUTATION_OK identical_harness_detects_allowed_receiver', flush=True)
        finally:
            config.write_bytes(original)
        time.sleep(.2)
        baseline = (OUT / 'stub.txt').read_text().splitlines()
        assert sum(line.startswith('CONNECTION ') for line in baseline) >= len(FIXTURES['sockets']) + 3
        snapshots = {p: digest(p) for p in FIXTURES['reads'] + FIXTURES['writes'] + FIXTURES['notebooks'] + ['/dev/uinput']}
        # Run hostile code even with the helper missing, to measure the fallback.
        with (OUT / 'standalone-processes.txt').open('w') as observer_log:
            observer = subprocess.Popen(['/usr/bin/python3', '-I', str(ROOT / 'observe.py')],
                                        stdout=observer_log, stderr=observer_log)
            try:
                result = run(['/usr/local/bin/node', str(ROOT / 'run.mjs'),
                              '/usr/bin/python3 -I /opt/aresos-control/hostile.py'], 'hostile', required=False)
            finally:
                observer.terminate()
                observer.wait(timeout=10)
        from boundary_assertions import policy_mounts, observed_processes
        observed = observed_processes(OUT / 'standalone-processes.txt')
        assert len(observed) == 1, 'standalone outside mount observation missing'
        assert int(observed[0]['cap_eff'], 16) == 0, 'observer capability leaked to standalone attack'
        standalone_view = policy_mounts(observed[0]['mountinfo'], json.loads(
            (ROOT / 'optional-sandbox.json').read_text()))
        (OUT / 'standalone-policy-mounts.json').write_text(json.dumps(standalone_view, indent=2))
        if (OUT / 'native-policy-mounts.json').exists():
            native_view = json.loads((OUT / 'native-policy-mounts.json').read_text())['hostile']
            comparison = {path: {'standalone': view, 'native': native_view[path],
                                'same_access': view['view'] == native_view[path]['view']}
                          for path, view in standalone_view.items()}
            (OUT / 'policy-mount-comparison.json').write_text(json.dumps(comparison, indent=2))
            assert all(row['same_access'] for row in comparison.values()), 'native and standalone mount policy differ'
            print('MOUNT_COMPARISON_OK paths=' + str(len(comparison)), flush=True)
        integrity = {p: {'before': before, 'after': digest(p) if Path(p).is_file() else None}
                     for p, before in snapshots.items()}
        (OUT / 'file-integrity.json').write_text(json.dumps(integrity, indent=2) + '\n')
        time.sleep(.2)
        after_log = (OUT / 'stub.txt').read_text().splitlines()
        (OUT / 'stub-new-connections.json').write_text(json.dumps(after_log[len(baseline):]) + '\n')
        rows = [json.loads(line[8:]) for line in result.stdout.splitlines() if line.startswith('HOSTILE ')]
        expected = len(FIXTURES['sockets']) + 2 + len(FIXTURES['reads']) + 3 * len(FIXTURES['writes']) + 6 + 6 + 1 + 1 + 2
        assert len(rows) == expected and f'HOSTILE_DONE {expected}' in result.stdout, 'hostile programs did not finish'
        assert 'WORK_READ_OK' in result.stdout and 'TEMP_WRITE_OK' in result.stdout
        assert 'SHADOW_ONLY /home/assistant/.bashrc' in result.stdout
        assert all(row['blocked'] or (MODE == 'absent' and row['name'] == 'connect:vsock' and row.get('unqualified')) for row in rows), 'OPEN ROUTES: ' + str([r for r in rows if not r['blocked'] and not r.get('unqualified')])
        assert result.returncode == 0
        assert all(row['before'] == row['after'] for row in integrity.values()), 'target changed'
        assert not Path('/home/assistant/work/fresh').exists(), 'new executable configuration created'
        assert stub.poll() is None, 'stub died during attacks'
        assert after_log == baseline, 'listener received hostile connection'
        print(f'BOUNDARY_OK mode={MODE} attacks={len(rows)} unchanged={len(snapshots)} hostile_connections=0 unqualified={sum(bool(r.get("unqualified")) for r in rows)}', flush=True)
        other_user_check()
        if MODE == 'present':
            from precedence import precedence_checks
            precedence_checks(run, put)
        assert native_error is None, native_error
    finally:
        stub.terminate()
        stub.wait(timeout=10)
        log.close()


def other_user_check():
    # The listener is live and reachable by the owner (the positive controls ran).
    # Another UID in this SAME container must not reach act.sock.
    def other():
        os.setgroups([])
        os.setgid(10003)
        os.setuid(10003)
    code = "import socket; socket.socket(socket.AF_UNIX).connect('/run/aresos-tools/act.sock')"
    denied = subprocess.run(['/usr/bin/python3', '-I', '-c', code], preexec_fn=other,
                            capture_output=True, text=True, timeout=5)
    assert denied.returncode != 0 and 'PermissionError' in denied.stderr, denied
    (OUT / 'other-user.txt').write_text(denied.stderr)
    print('OTHER_USER_OK same_container uid=10003 act.sock=EACCES', flush=True)


if __name__ == '__main__':
    main()
