"""Linux container supervisor. Root only creates synthetic fixtures and users;
all attacks and the launcher run as the unprivileged assistant.
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
                   Path('/etc/claude-code/managed-mcp.json')]:
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
    put('/home/assistant/.claude/settings.json', '{}\n')
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
        # Do not lose standalone/launcher evidence when a native qualification
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
            Path('/etc/claude-code/managed-settings.json').read_text()))
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
        launcher_checks()
        settings_checks()
        assert native_error is None, native_error
    finally:
        stub.terminate()
        stub.wait(timeout=10)
        log.close()


def launcher_checks():
    # Swap only the root-owned CLI target for an environment recorder in this
    # disposable container; no production test-switch exists in the launcher.
    cli = Path('/usr/local/bin/claude')
    target = cli.resolve()
    pin = ROOT / 'native-pin.json'
    original_pin = pin.read_bytes()
    cli.unlink()
    cli.write_text('#!/usr/bin/python3 -I\nimport json,os,sys\nprint("LAUNCHED " + json.dumps({"env":dict(os.environ),"args":sys.argv[1:]}))\n')
    cli.chmod(0o755)
    recorder_pin = json.loads(original_pin)
    recorder_pin['cli_sha256'] = digest(cli)
    pin.write_text(json.dumps(recorder_pin))
    put('/home/assistant/work/env-shadow/sitecustomize.py',
        'open("/home/assistant/work/python-env-ran", "w").write("executed")\n')
    put('/home/assistant/work/env-shadow/preload.cjs',
        'require("node:fs").writeFileSync("/home/assistant/work/node-env-ran", "executed");\n')
    planted = dict(ENV, NODE_OPTIONS='--require=/home/assistant/work/env-shadow/preload.cjs',
                   LD_PRELOAD='/opt/aresos-control/env-load.so',
                   LD_LIBRARY_PATH='/untrusted', PYTHONPATH='/home/assistant/work/env-shadow', PYTHONSTARTUP='/untrusted.py',
                   BASH_ENV='/untrusted.sh', ENV='/untrusted.sh', CLAUDE_CONFIG_DIR='/untrusted',
                   CLAUDE_CODE_PLUGIN_DIRS='/untrusted', ANTHROPIC_API_KEY='SYNTHETIC',
                   DISPLAY=':0', WAYLAND_DISPLAY='wayland-0', DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/10001/bus')
    try:
        for command, marker in [(['/usr/bin/true'], 'preload-ran'),
                                (['/usr/bin/python3', '-c', 'pass'], 'python-env-ran'),
                                (['/usr/local/bin/node', '-e', ''], 'node-env-ran')]:
            run(command, 'env-positive-' + marker, planted)
            assert Path('/home/assistant/work', marker).exists()
        for marker in ['preload-ran', 'python-env-ran', 'node-env-ran']:
            Path('/home/assistant/work', marker).unlink()
        result = run(['/usr/local/bin/aresos-assistant'], 'launcher-planted', planted, required=False)
        assert not any(Path('/home/assistant/work', marker).exists()
                       for marker in ['preload-ran', 'python-env-ran', 'node-env-ran']), 'planted startup code executed'
        if MODE == 'absent':
            assert result.returncode == 78 and 'REFUSE:' in result.stderr and 'LAUNCHED' not in result.stdout
            print('LAUNCHER_OK missing_filter_refused', flush=True)
        else:
            assert result.returncode == 0, result.stderr
            row = json.loads(result.stdout.split('LAUNCHED ')[1])
            assert row['args'] == ['--setting-sources', '']
            assert set(row['env']) == set(ENV) | {'LOGNAME', 'TERM'}, row
            assert row['env']['HOME'] == '/home/assistant'
            print('LAUNCHER_OK planted_environment_stripped fixed_cli_args', flush=True)
            dropins = Path('/etc/claude-code/managed-settings.d')
            dropins.mkdir(mode=0o755)
            try:
                empty = run(['/usr/local/bin/aresos-assistant'], 'launcher-empty-dropins', required=False)
                assert empty.returncode == 0 and 'LAUNCHED' in empty.stdout, empty.stderr
                for filename in ('99-open.json', 'notes.txt'):
                    entry = dropins / filename
                    entry.write_text(json.dumps({'sandbox': {'excludedCommands': ['aresos *']},
                                                 'permissions': {'allow': ['Bash(aresos *)']}}))
                    bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-dropin-' + filename, required=False)
                    assert bad.returncode == 78 and filename in bad.stderr and 'LAUNCHED' not in bad.stdout
                    entry.unlink()
            finally:
                dropins.rmdir()
            dropins.symlink_to('/home/assistant/work', target_is_directory=True)
            try:
                bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-symlink-dropins', required=False)
                assert bad.returncode == 78 and 'managed-settings.d' in bad.stderr and 'LAUNCHED' not in bad.stdout
            finally:
                dropins.unlink()
            remote = Path('/home/assistant/.claude/remote-settings.json')
            remote.write_text('{}')
            try:
                bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-remote-cache', required=False)
                assert bad.returncode == 78 and 'remote-settings.json' in bad.stderr and 'LAUNCHED' not in bad.stdout
            finally:
                remote.unlink()
            print('LAUNCHER_POLICY_SOURCES_OK empty_pass nonempty_and_symlink_refused', flush=True)
            helper = ROOT / 'node_modules/@anthropic-ai/sandbox-runtime/vendor/seccomp/x64/apply-seccomp'
            original = helper.read_bytes()
            helper.write_bytes(b'#!/bin/sh\nexit 0\n')
            try:
                bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-corrupt-filter', required=False)
                assert bad.returncode == 78 and 'hash mismatch' in bad.stderr and 'LAUNCHED' not in bad.stdout
            finally:
                helper.write_bytes(original)
            size = target.stat().st_size
            with target.open('ab') as binary:
                binary.write(b'CORRUPT')
            try:
                bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-corrupt-native', required=False)
                assert bad.returncode == 78 and 'native CLI hash mismatch' in bad.stderr
            finally:
                with target.open('r+b') as binary:
                    binary.truncate(size)
            for name, args in [('plugin', ['--plugin-dir', '/untrusted']),
                               ('bypass', ['--dangerously-skip-permissions'])]:
                bad = run(['/usr/local/bin/aresos-assistant', *args], 'launcher-options-' + name, required=False)
                assert bad.returncode == 78
            registry = Path('/home/assistant/.claude/plugins/installed_plugins.json')
            put(registry, '{"version":2,"plugins":{"unknown@old-marketplace":[{"installPath":"/untrusted"}]}}')
            try:
                bad = run(['/usr/local/bin/aresos-assistant'], 'launcher-preinstalled-plugin', required=False)
                assert bad.returncode == 78 and 'no installed plugins' in bad.stderr and 'LAUNCHED' not in bad.stdout
            finally:
                registry.unlink()
    finally:
        cli.unlink()
        cli.symlink_to(target)
        pin.write_bytes(original_pin)


def settings_checks():
    # No model, login or real credentials. These are configuration CLI commands.
    server = {'type': 'stdio', 'command': '/usr/bin/python3',
              'args': ['-I', '/opt/aresos-control/mcp-fixture.py']}
    put('/home/assistant/.claude.json', json.dumps({'mcpServers': {'rogue-user': server}}))
    put('/home/assistant/work/.mcp.json', json.dumps({'mcpServers': {'rogue-project': server}}))
    managed = Path('/etc/claude-code/managed-mcp.json')
    original = managed.read_bytes()
    managed.unlink()
    settings_path = Path('/etc/claude-code/managed-settings.json')
    settings_original = settings_path.read_bytes()
    positive = json.loads(settings_original)
    positive['allowManagedMcpServersOnly'] = False
    positive.pop('allowedMcpServers', None)
    settings_path.write_text(json.dumps(positive))
    try:
        control = run(['/usr/local/bin/claude', 'mcp', 'list'], 'mcp-unmanaged-positive')
        assert 'rogue-user' in control.stdout and 'rogue-project' in control.stdout
        assert Path('/home/assistant/work/mcp-started').exists()
    finally:
        managed.write_bytes(original)
        settings_path.write_bytes(settings_original)
    Path('/home/assistant/work/mcp-started').unlink()
    from boundary_assertions import validate_managed_mcp
    listed = run(['/usr/local/bin/claude', 'mcp', 'list'], 'mcp-list')
    names = validate_managed_mcp(listed, managed)
    print('MANAGED_MCP_OK user=assistant names=' + json.dumps(names), flush=True)
    checks = [
        ('mcp-add', ['mcp', 'add', '--transport', 'http', 'hostile', 'https://example.com/mcp'], 1, 'exclusive control'),
        ('marketplace-add', ['plugin', 'marketplace', 'add', 'https://example.com/marketplace.json'], 1, 'No external marketplaces are allowed'),
    ]
    errors = []
    for name, args, code, message in checks:
        result = run(['/usr/local/bin/claude', *args], name, required=False)
        if result.returncode != code or message.lower() not in (result.stdout + result.stderr).lower():
            errors.append(name)
    assert not Path('/home/assistant/work/mcp-started').exists(), 'unmanaged MCP executed under exclusive policy'
    for flag, value in [('--plugin-dir', '/home/assistant/work'), ('--plugin-url', 'https://example.com/plugin'),
                        ('--agents', '{}'), ('--mcp-config', '{"mcpServers":{"evil":{"command":"false"}}}')]:
        result = run(['/usr/local/bin/claude', flag, value, '-p', 'do not call a model'], 'flag-' + flag[2:], required=False)
        if result.returncode == 0 or 'disableSideloadFlags' not in result.stdout + result.stderr:
            errors.append(flag)
    # The auth preflight otherwise stops at /login before checking bypass.
    # A synthetic noncredential plus a local stub endpoint exposes the actual
    # permissionMode in the session-init event, without a model or real provider.
    # Native 2.1.319 clamps the mode instead of rejecting the flag at startup.
    offline = dict(ENV, ANTHROPIC_API_KEY='SYNTHETIC_BOUNDARY_NONCREDENTIAL',
                   ANTHROPIC_BASE_URL='http://127.0.0.1:18080')
    result = run(['/usr/local/bin/claude', '--dangerously-skip-permissions',
                  '--output-format', 'stream-json', '--verbose', '-p', 'do not call a model'],
                 'bypass-disabled', env=offline, required=False)
    events = [json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]
    init = [event for event in events if event.get('type') == 'system' and event.get('subtype') == 'init']
    if len(init) != 1 or init[0].get('permissionMode') != 'default':
        errors.append('bypass-disabled')
    assert result.returncode != 0, 'fake endpoint must never produce a model response'
    assert not errors, errors
    print('SETTINGS_OK mcp_exclusive marketplace_lock sideload_flags', flush=True)


if __name__ == '__main__':
    main()
