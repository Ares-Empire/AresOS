"""Observe the pinned KDE Plasma Login greeter and its active graphical VT."""
import json
import pathlib
import pwd
import subprocess
import time


def greeter_identity(executable, uid, expected_uid, environment):
    if pathlib.PurePosixPath(executable).name != 'plasma-login-greeter' or uid != expected_uid:
        return None
    kind = environment.get('XDG_SESSION_TYPE')
    vt = environment.get('XDG_VTNR', '')
    if kind not in ('wayland', 'x11') or not vt.isdecimal() or int(vt) < 1:
        return None
    return dict(executable=executable, uid=uid, type=kind, vt=int(vt),
                session_class=environment.get('XDG_SESSION_CLASS'))


def candidates(proc, uid):
    for process in proc.glob('[0-9]*'):
        try:
            executable = str((process / 'exe').readlink())
            if pathlib.PurePosixPath(executable).name != 'plasma-login-greeter':
                continue
            status = (process / 'status').read_text()
            actual_uid = int(next(line for line in status.splitlines() if line.startswith('Uid:')).split()[2])
            environment = dict(entry.split('=', 1) for entry in (process / 'environ').read_bytes().decode(errors='replace').split('\0') if '=' in entry)
            identity = greeter_identity(executable, actual_uid, uid, environment)
            if identity:
                yield dict(pid=int(process.name), **identity)
        except (FileNotFoundError, ProcessLookupError):
            # Process replacement during startup is observed afresh next poll.
            continue


def wait_ready(timeout=120):
    uid = pwd.getpwnam('plasmalogin').pw_uid
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for identity in candidates(pathlib.Path('/proc'), uid):
            if subprocess.run(['systemctl', 'is-active', '--quiet', 'display-manager.service']).returncode:
                continue
            subprocess.run(['chvt', str(identity['vt'])], check=True)
            if pathlib.Path('/sys/class/tty/tty0/active').read_text().strip() == 'tty' + str(identity['vt']):
                subprocess.run(['loginctl', 'list-sessions', '--no-legend'], check=True)
                print(json.dumps(identity, sort_keys=True))
                print('STOCK_GRAPHICAL_GREETER_READY')
                return
        time.sleep(1)
    subprocess.run(['loginctl', 'list-sessions', '--no-legend'], check=False)
    subprocess.run(['systemctl', 'status', 'display-manager.service', '--no-pager'], check=False)
    raise TimeoutError('No live Plasma Login greeter with graphical environment and active VT')


if __name__ == '__main__':
    wait_ready()
