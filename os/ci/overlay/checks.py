"""Fixed checks in a disposable test layer; no shell prompt or keyboard login."""
import json
import os
import pathlib
import subprocess
import time
import traceback

from channel import Frames, export_bytes, frame

HERE = pathlib.Path(__file__).parent
EXPORTS = {'backend.json': '/run/aresos-backend.json',
           'runtime-updaters.json': '/run/aresos-updaters.json',
           'updater-regressions.json': '/run/aresos-updater-regressions.json',
           'power-events.json': '/run/aresos-power-events.json'}


def run(*args, **kwargs):
    result = subprocess.run(args, capture_output=True, text=True, timeout=300, **kwargs)
    return dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def wait_session(extra_terminal=False):
    for _ in range(120):
        result = run('pgrep', '-u', 'ares', '-x', 'foot')
        if result['returncode'] == 0 and len(result['stdout'].split()) >= (2 if extra_terminal else 1):
            return result
        time.sleep(1)
    raise TimeoutError('AresOS terminal did not start')


def terminal_shells(pids):
    """Each AresOS terminal runs the system bash with the AresOS rcfile."""
    for _ in range(30):
        terminals = []
        for pid in pids:
            cmdline = pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')[:-1]
            children = run('pgrep', '-P', pid)['stdout'].split()
            terminals.append(dict(pid=pid, cmdline=[part.decode() for part in cmdline],
                                  shells=[os.readlink(f'/proc/{child}/exe') for child in children]))
        if all(terminal['shells'] == ['/usr/bin/bash'] for terminal in terminals):
            break
        time.sleep(1)
    for terminal in terminals:
        assert terminal['cmdline'][:3] == ['/usr/bin/foot', '--title=AresOS', '/usr/bin/bash'], terminals
        assert terminal['shells'] == ['/usr/bin/bash'], terminals
    return terminals


def check(action, request):
    if action == 'policy':
        wait_session()
        regressions = run('python3', str(HERE / 'updater_regressions.py'))
        assert regressions['returncode'] == 0, regressions
        print(regressions['stdout'], flush=True)
        return run('bash', str(HERE / 'guest.sh'))
    if action == 'recovery':
        for _ in range(100):
            if pathlib.Path('/sys/class/tty/tty0/active').read_text().strip() == 'tty3':
                break
            time.sleep(0.1)
        else:
            raise TimeoutError('Recovery shortcut did not select tty3')
        getty = run('systemctl', 'show', 'getty@tty3.service', '-p', 'ActiveState', '-p', 'MainPID')
        assert 'ActiveState=active\n' in getty['stdout'], getty
        pid = int(next(line.split('=', 1)[1] for line in getty['stdout'].splitlines() if line.startswith('MainPID=')))
        assert pid > 0, getty
        cmdline = pathlib.Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()
        tty = os.readlink(f'/proc/{pid}/fd/0')
        assert 'agetty' in cmdline and tty == '/dev/tty3', (cmdline, tty)
        assert pathlib.Path('/sys/class/tty/tty0/active').read_text().strip() == 'tty3'
        result = run('python3', str(HERE / 'pam_check.py'), input=json.dumps({'password': request['password']}))
        result.update(getty=getty, getty_cmdline=cmdline, getty_tty=tty)
        return result
    if action == 'power-events':
        return run('python3', str(HERE / 'power-events.py'))
    if action == 'shortcut':
        result = wait_session(extra_terminal=True)
        # Package 21 review 5: the session, its terminal and the recovery
        # terminal started although broken copies of every startup command
        # head the daily account's ~/.local/bin; none of them may have run.
        names = (HERE / 'shadow-names.txt').read_text().split()
        missing = [name for name in names if not os.access(f'/var/home/ares/.local/bin/{name}', os.X_OK)]
        assert names and not missing, ('shadowing programs missing', missing)
        result['terminals'] = terminal_shells(result['stdout'].split())
        # greetd's wrapper (non-interactive, not a login shell) sources
        # /etc/profile before the session: its profile scripts keep the system PATH.
        probe = pathlib.Path('/tmp/aresos-ci-profile-path')
        lines = probe.read_text().splitlines() if probe.exists() else []
        for line in lines:
            arg0, flags, login, path = line.split('|', 3)
            if 'i' not in flags and not arg0.startswith('-') and not login:
                assert '/var/home/ares/.local/bin' not in path.split(':'), ('session wrapper got the daily PATH', lines)
        result['profile_paths'] = lines
        ran = pathlib.Path('/tmp/aresos-ci-shadow-ran')
        assert not ran.exists(), ('a shadowing program ran', ran.read_text())
        result['shadowed'] = names
        return result
    if action == 'export':
        return dict(returncode=0, files={name: export_bytes(pathlib.Path(path).read_bytes())
                                       for name, path in EXPORTS.items() if pathlib.Path(path).exists()})
    if action == 'prepare-poweroff':
        # A separate cgroup without shutdown dependencies keeps the follower
        # alive after this check service stops. A cursor closes the startup gap.
        journal = run('journalctl', '--lines=1', '--show-cursor', '--no-pager', '--output=cat')
        assert journal['returncode'] == 0, journal
        cursor = journal['stdout'].rsplit('-- cursor: ', 1)[1].strip()
        assert cursor and '\n' not in cursor, journal
        follower = run('systemd-run', '--quiet', '--unit=aresos-ci-journal',
                       '--property=DefaultDependencies=no', '--property=IgnoreOnIsolate=yes',
                       '--property=Type=exec', '--property=StandardOutput=tty',
                       '--property=TTYPath=/dev/ttyS0', '/usr/bin/journalctl',
                       '--follow', f'--after-cursor={cursor}', '--no-pager', '--output=short-monotonic')
        assert follower['returncode'] == 0, follower
        assert run('logger', '--tag', 'aresos-ci', 'ARESOS_JOURNAL_READY')['returncode'] == 0
        boot_id = pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip().replace('-', '')
        assert run('logger', '--tag', 'aresos-ci', 'ARESOS_POWER_KEY_ARMED')['returncode'] == 0
        for operation in ('--flush', '--sync'):
            result = run('journalctl', operation)
            assert result['returncode'] == 0, result
        persistent = pathlib.Path('/var/log/journal')
        files = [str(path.relative_to(persistent)) for path in persistent.rglob('*.journal')]
        assert files, 'No persistent journal files before poweroff'
        config = run('systemd-analyze', 'cat-config', 'systemd/journald.conf')
        assert config['returncode'] == 0, config
        return dict(returncode=0, journal_unit='aresos-ci-journal.service', after_cursor=cursor,
                    boot_id=boot_id, persistent_files=files, journald_config=config['stdout'])
    raise ValueError(f'Unknown check: {action}')


def main():
    port = pathlib.Path('/dev/virtio-ports/org.aresos.ci')
    deadline = time.monotonic() + 60
    while not port.exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('CI virtio port absent')
        time.sleep(0.2)
    with port.open('r+b', buffering=0) as stream:
        incoming = Frames(stream.read)

        def send(value):
            data = frame(value)
            while data:
                written = stream.write(data)
                if not written:
                    raise EOFError('CI virtio port stopped accepting data')
                data = data[written:]

        send(dict(ready=True, protocol=1))
        while True:
            request = incoming.receive()
            try:
                result = check(request['action'], request)
            except Exception:
                result = dict(returncode=1, stderr=traceback.format_exc())
            send(dict(id=request['id'], **result))


if __name__ == '__main__':
    main()
