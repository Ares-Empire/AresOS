"""Control's state in a booted AresOS, for the release rehearsal (package 18c, agreed change 12).

Needs nothing but the image itself: no Claude Code binary, no CI layer, only Python's standard library. Run it as
root in the booted guest, after the update from the previous release:

    python3 -I release_checks.py [check ...]        (or its text piped to: python3 -I - [check ...])

It prints one JSON object (every check with its values), then CONTROL_RELEASE_CHECKS_PASS, or
CONTROL_RELEASE_CHECKS_FAILED with the failed checks' names and exit status 1. Every check runs even when an
earlier one fails. With names, only those checks run. The check_build=control VM test runs it through the CI layer
(os/ci/control/actions.py), so the same file is proven there.

On the laptop systemd-sysusers creates aresos-tools at the first boot of the new release, where a taken 250 would
quietly become another number; the state folders in /var keep the owner they had. Only a rehearsal sees that.
"""
import grp
import hashlib
import json
import os
import pathlib
import pwd
import stat
import subprocess
import sys
import time

SERVICE_USER = 'aresos-tools'
SERVICE_ID = 250
UNIT = 'aresos-toold.service'
ROOT = pathlib.Path('/')
RECORD = 'usr/share/aresos/manifest/control.json'
SERVICE_CONFIG = 'usr/share/aresos/control/service.json'
PROXY_CONFIG = 'usr/share/aresos/control/proxy.json'
MANAGED = 'etc/claude-code'
# ostree keeps the image's own /etc in /usr/etc; /etc is the deployment's merge.
IMAGE_ETC = 'usr/etc'
STATE = {'var/lib/aresos-tools': 0o700, 'var/lib/aresos-operation-evidence': 0o700, 'run/aresos-tools': 0o711}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def service_user():
    """aresos-tools has UID and GID 250, and nothing else has either."""
    user, group = pwd.getpwnam(SERVICE_USER), grp.getgrnam(SERVICE_USER)
    value = dict(uid=user.pw_uid, gid=user.pw_gid, group_gid=group.gr_gid, home=user.pw_dir, shell=user.pw_shell,
                 users_with_250=sorted({entry.pw_name for entry in pwd.getpwall() if entry.pw_uid == SERVICE_ID}),
                 groups_with_250=sorted({entry.gr_name for entry in grp.getgrall() if entry.gr_gid == SERVICE_ID}))
    ok = ((user.pw_uid, user.pw_gid, group.gr_gid) == (SERVICE_ID,) * 3
          and value['users_with_250'] == [SERVICE_USER] and value['groups_with_250'] == [SERVICE_USER])
    return ok, value


def unit(wait=90):
    """The unit is enabled and active, and its main process runs as aresos-tools."""
    deadline = time.monotonic() + wait
    while True:
        shown = subprocess.run(['systemctl', 'show', UNIT, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID',
                                '-p', 'NRestarts', '-p', 'UnitFileState'],
                               capture_output=True, text=True, timeout=30)
        value = dict(line.split('=', 1) for line in shown.stdout.splitlines() if '=' in line)
        if value.get('ActiveState') not in ('activating', 'reloading') or time.monotonic() > deadline:
            break
        time.sleep(1)
    pid = int(value.get('MainPID') or 0)
    status = pathlib.Path(f'/proc/{pid}/status')
    ids = {}
    if pid and status.exists():
        for line in status.read_text().splitlines():
            key, _, rest = line.partition(':')
            if key in ('Uid', 'Gid'):
                ids[key] = [int(field) for field in rest.split()]
    value['main_process_ids'] = ids
    ok = (value.get('ActiveState') == 'active' and value.get('SubState') == 'running'
          and value.get('UnitFileState') == 'enabled'
          and ids.get('Uid') == [SERVICE_ID] * 4 and ids.get('Gid') == [SERVICE_ID] * 4)
    return ok, value


def claude_code_files():
    """Agreed change 7: /etc/claude-code holds exactly its two files, equal to the image's (its /usr/etc copy and
    control.json's record), root-owned with the recorded mode; no managed-mcp.json."""
    record = json.loads((ROOT / RECORD).read_text())['files']
    expected = {name: entry for name, entry in record.items() if name.startswith('/' + MANAGED + '/')}
    folder = ROOT / MANAGED
    value = dict(present=sorted(path.name for path in folder.iterdir()), files={})
    ok = len(expected) == 2 and value['present'] == sorted(pathlib.PurePath(name).name for name in expected)
    for name, entry in sorted(expected.items()):
        path = ROOT / name.lstrip('/')
        image = ROOT / IMAGE_ETC / path.relative_to(ROOT / 'etc')
        info = path.lstat()
        row = dict(mode=f'{stat.S_IMODE(info.st_mode):04o}', owner=[info.st_uid, info.st_gid],
                   regular=stat.S_ISREG(info.st_mode), recorded=entry['sha256'],
                   sha256=sha256(path) if stat.S_ISREG(info.st_mode) else None,
                   image_sha256=sha256(image) if image.is_file() and not image.is_symlink() else None)
        value['files'][name] = row
        ok = ok and row['regular'] and row['owner'] == [0, 0] and row['mode'] == entry['mode'] and \
            row['sha256'] == row['image_sha256'] == entry['sha256']
    value['managed_mcp'] = (folder / 'managed-mcp.json').exists()
    return ok and not value['managed_mcp'], value


def folders():
    """The two folders the tools may use exist as folders of the owner (tmpfiles makes them only when missing)."""
    owner = json.loads((ROOT / SERVICE_CONFIG).read_text())['owner_uid']
    configured = json.loads((ROOT / PROXY_CONFIG).read_text())['folders']
    value = dict(owner_uid=owner, folders={})
    ok = len(configured) == 2
    for name in configured:
        path = ROOT / name.lstrip('/')
        info = path.lstat() if path.exists() or path.is_symlink() else None
        row = dict(exists=info is not None)
        if info:
            row.update(directory=stat.S_ISDIR(info.st_mode), link=stat.S_ISLNK(info.st_mode), uid=info.st_uid,
                       mode=f'{stat.S_IMODE(info.st_mode):04o}')
        value['folders'][name] = row
        ok = ok and bool(info) and row['directory'] and row['uid'] == owner
    return ok, value


def state_folders():
    """The service's state and socket folders, and everything in the state folders, belong to aresos-tools."""
    value = {}
    ok = True
    for name, mode in STATE.items():
        path = ROOT / name
        info = path.lstat()
        row = dict(directory=stat.S_ISDIR(info.st_mode), owner=[info.st_uid, info.st_gid],
                   mode=f'{stat.S_IMODE(info.st_mode):04o}', expected_mode=f'{mode:04o}')
        ok = ok and row['directory'] and row['owner'] == [SERVICE_ID] * 2 and row['mode'] == row['expected_mode']
        if name.startswith('var/'):
            entries, foreign = 0, []
            for folder, names, files in os.walk(path):
                for entry in names + files:
                    entries += 1
                    inner = os.lstat(os.path.join(folder, entry))
                    if (inner.st_uid, inner.st_gid) != (SERVICE_ID, SERVICE_ID):
                        foreign.append([os.path.relpath(os.path.join(folder, entry), path), inner.st_uid, inner.st_gid])
            row.update(entries=entries, not_owned=foreign[:20], not_owned_count=len(foreign))
            ok = ok and not foreign
        value['/' + name] = row
    return ok, value


CHECKS = dict(service_user=service_user, unit=unit, claude_code_files=claude_code_files, folders=folders,
              state_folders=state_folders)


def run(names=None):
    results = {}
    for name in names or CHECKS:
        try:
            ok, value = CHECKS[name]()
        except Exception as error:
            ok, value = False, dict(error=f'{type(error).__name__}: {error}')
        results[name] = dict(ok=ok, value=value)
    return results


def main(argv):
    unknown = [name for name in argv if name not in CHECKS]
    if unknown:
        raise SystemExit(f'Unknown check: {unknown}; known: {list(CHECKS)}')
    results = run(argv)
    print(json.dumps(results, sort_keys=True), flush=True)
    failed = [name for name, result in results.items() if not result['ok']]
    if failed:
        print('CONTROL_RELEASE_CHECKS_FAILED ' + ' '.join(failed), flush=True)
        return 1
    print('CONTROL_RELEASE_CHECKS_PASS', flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
