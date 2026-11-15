"""Real polkitd, a password agent and the service's own check (final fixes F7).

Runs as root inside a disposable, privileged Fedora container
(.github/workflows/control-chrome-polkit.yml). Never run it on a real system: it
creates users, starts a system bus and polkitd, and installs the policy.

What it shows, with the shipped policy file and confirm.py unchanged:
- the service's user checks a process of another user (the owner's native host
  stand-in) and the owner's agent asks for his password: the right one grants;
- a wrong password, no agent, another start time or a policy without the owner
  annotation refuse;
- a second check right after a yes asks again (nothing is kept);
- the dialog text names the change: every prompt pkttyagent shows is the
  policy's message with $(change) replaced by that case's change, and two
  cases use different changes, so the text can only come from the check;
- the check runs under an emulation of aresos-toold.service's sandboxing:
  read-only file system including /run, private /tmp and /dev, hidden homes,
  no new privileges and an empty capability bounding set.
The container has no logind seat, so no session is local and active. A CI-only
rule returns AUTH_ADMIN for the action, as allow_active=auth_admin does in the
owner's desktop session; that part is linux-tools' 18c-b image test.
"""
import fcntl
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import select
import shutil
import subprocess
import sys
import termios
import time
import uuid
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / '.work/polkit'
POLICY = ROOT / 'control/chrome/packaging/org.aresos.control.chrome-loosen.policy'
UNIT = (ROOT / 'control/packaging/aresos-toold.service').read_text()
SERVICE_USER = re.search(r'^User=(\S+)$', UNIT, re.M).group(1)
ACTION = 'org.aresos.control.chrome-loosen'
UNOWNED = ACTION + '-ci-unowned'
OWNER = 'owner'
PASSWORD = secrets.token_urlsafe(18)
CHANGE = 'Read-only off for ci.test'
OTHER_CHANGE = "Don't ask again: example_send as owner on https://ci.test"
ANSI = re.compile(r'\x1b\[[0-9;]*m')

# Emulates the unit's [Service] sandboxing for the check (systemd isn't PID 1 here).
SANDBOX = r'''
set -eu
user=$1; shift
mount -t tmpfs -o mode=1777 tmpfs /tmp
mkdir /tmp/.dev
mount -t tmpfs -o mode=755 tmpfs /tmp/.dev
for name in null zero full random urandom tty; do touch /tmp/.dev/$name; mount --bind /dev/$name /tmp/.dev/$name; done
mount --move /tmp/.dev /dev
for path in /home /root /run/user; do if [ -d "$path" ]; then mount -t tmpfs -o mode=000 tmpfs "$path"; fi; done
mount -o remount,bind,ro /
exec setpriv --reuid="$user" --regid="$user" --clear-groups --no-new-privs --bounding-set=-all --inh-caps=-all -- "$@"
'''

DRIVER = r'''
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
from aresos_control.chrome import confirm
action, pid, uid, offset, change = sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
confirm.ACTION = action
status = dict(line.split(':\t', 1) for line in open('/proc/self/status').read().splitlines() if ':\t' in line)
try:
    open('/run/aresos-ci-write-probe', 'w').close(); run_readonly = False
except OSError:
    run_readonly = True
peer = {'pid': pid, 'uid': uid, 'start': confirm.start_time(pid) + offset}
ask, reason = confirm.start(peer, change, timeout=60)
outcome = (False, reason) if ask is None else None
while outcome is None:
    outcome = ask.outcome(); time.sleep(0.05)
print(json.dumps({'granted': outcome[0], 'reason': outcome[1], 'uid': os.getuid(), 'no_new_privs': status.get('NoNewPrivs'),
                  'bounding_set': status.get('CapBnd'), 'run_readonly': run_readonly, 'tmp_entries': os.listdir('/tmp')}))
'''


def run(*command, **options):
    return subprocess.run(command, check=True, **options)


def setup(log):
    if not (Path('/.dockerenv').exists() or Path('/run/.containerenv').exists()) or os.getuid() != 0:
        raise SystemExit('Only for a disposable container, as root.')
    run('useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', SERVICE_USER)
    run('useradd', '--create-home', '--groups', 'wheel', OWNER)
    run('chpasswd', input=f'{OWNER}:{PASSWORD}\n', text=True)
    try:
        pwd.getpwnam('polkitd')
    except KeyError:
        run('useradd', '--system', '--no-create-home', '--shell', '/usr/sbin/nologin', 'polkitd')
    machine = Path('/etc/machine-id')
    if not machine.exists() or not machine.read_text().strip():
        machine.write_text(uuid.uuid4().hex + '\n')
    Path('/run/dbus').mkdir(exist_ok=True)
    run('dbus-daemon', '--system', '--fork')
    actions = Path('/usr/share/polkit-1/actions')
    shutil.copy(POLICY, actions / POLICY.name)
    text = POLICY.read_text()
    unowned = re.sub(r'\n\s*<annotate key="org.freedesktop.policykit.owner">[^<]*</annotate>', '', text).replace(f'id="{ACTION}"', f'id="{UNOWNED}"')
    assert 'policykit.owner' not in unowned and UNOWNED in unowned
    (actions / (UNOWNED + '.policy')).write_text(unowned)
    Path('/etc/polkit-1/rules.d').mkdir(parents=True, exist_ok=True)
    Path('/etc/polkit-1/rules.d/10-aresos-ci.rules').write_text(
        '// CI only: no logind seat here, so stand in for allow_active=auth_admin.\n'
        'polkit.addRule(function(action, subject) {\n'
        f'  if (action.id == "{ACTION}" || action.id == "{UNOWNED}") return polkit.Result.AUTH_ADMIN;\n'
        '});\n')
    daemon = next(path for path in ['/usr/lib/polkit-1/polkitd', '/usr/libexec/polkitd', '/usr/libexec/polkit-1/polkitd'] if Path(path).exists())
    polkitd = subprocess.Popen(['runuser', '-u', 'polkitd', '--', daemon, '--no-debug'], stdout=log, stderr=log)
    deadline = time.monotonic() + 30
    while subprocess.run(['pkaction', '--action-id', ACTION], capture_output=True).returncode:
        if time.monotonic() > deadline or polkitd.poll() is not None:
            raise SystemExit('polkitd did not answer')
        time.sleep(0.5)
    return polkitd


def start_agent(pid):
    """pkttyagent as the owner, on its own terminal, registered for the subject process."""
    master, slave = os.openpty()
    ready, notify = os.pipe()
    process = subprocess.Popen(['setpriv', f'--reuid={OWNER}', f'--regid={OWNER}', '--init-groups', 'pkttyagent',
                                '--process', str(pid), '--notify-fd', str(notify)],
                               stdin=slave, stdout=slave, stderr=slave, pass_fds=(notify,), start_new_session=True,
                               preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0))
    os.close(slave)
    os.close(notify)
    # The agent closes its end once it is registered.
    if not select.select([ready], [], [], 20)[0] or os.read(ready, 1):
        raise SystemExit('pkttyagent did not register')
    os.close(ready)
    return process, master


def dialog_messages(transcript):
    """Each message pkttyagent showed: the lines between its header and "Authenticating as:"."""
    messages, current = [], None
    for line in ANSI.sub('', transcript).replace('\r', '').split('\n'):
        if '==== AUTHENTICATING FOR' in line:
            current = []
        elif current is not None and line.startswith('Authenticating as:'):
            messages.append(' '.join(part.strip() for part in current if part.strip()))
            current = None
        elif current is not None:
            current.append(line)
    return messages


def expected_message(change):
    message = ET.fromstring(POLICY.read_bytes()).find('action/message').text
    assert message.count('$(change)') == 1
    return message.replace('$(change)', change)


def dialog_problems(result, change, prompted):
    """A case that reached the agent must show exactly the policy's message naming its change."""
    messages = dialog_messages(result['transcript'])
    if prompted and not messages:
        return ['the agent showed no dialog']
    if len(messages) != result['prompts']:
        return [f'{len(messages)} dialog messages for {result["prompts"]} password prompts']
    wrong = [message for message in messages if message != expected_message(change)]
    if wrong:
        return [f'the dialog did not name the change: {wrong[0]!r}']
    return []


def check(subject, owner_uid, action=ACTION, password=None, agent=True, offset=0, change=CHANGE):
    process, master = start_agent(subject.pid) if agent else (None, None)
    driver = subprocess.Popen(['unshare', '--mount', '--propagation', 'private', '--', 'sh', '-c', SANDBOX, 'sandbox', SERVICE_USER,
                               'python3', '-I', '-S', '-c', DRIVER, str(ROOT / 'control'), action, str(subject.pid), str(owner_uid), str(offset), change],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    transcript, prompts, deadline, reading = b'', 0, time.monotonic() + 90, master is not None
    while driver.poll() is None and time.monotonic() < deadline:
        if not reading:
            time.sleep(0.2)
            continue
        if select.select([master], [], [], 0.2)[0]:
            try:
                chunk = os.read(master, 4096)
            except OSError:
                chunk = b''
            if not chunk:
                # The agent's terminal closed; keep waiting for the check itself.
                reading = False
                continue
            transcript += chunk
            if transcript.count(b'Password:') > prompts:
                prompts = transcript.count(b'Password:')
                os.write(master, password.encode() + b'\n')
    if driver.poll() is None:
        driver.kill()
    output, errors = driver.communicate()
    if process is not None:
        process.terminate()
        try:
            process.wait(10)
        except subprocess.TimeoutExpired:
            process.kill()
        os.close(master)
    lines = output.strip().splitlines()
    result = json.loads(lines[-1]) if lines else {'granted': None, 'reason': 'driver failed'}
    return {**result, 'change': change, 'prompts': prompts, 'transcript': transcript.decode('utf-8', 'replace').replace(PASSWORD, '<password>'),
            'driver_errors': errors[-2000:]}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / 'polkitd.log', 'w') as log:
        polkitd = setup(log)
        versions = {name: subprocess.run(command, capture_output=True, text=True).stdout.strip()
                    for name, command in {'polkit': ['rpm', '-q', 'polkit'], 'pkcheck': ['pkcheck', '--version'],
                                          'fedora': ['cat', '/etc/fedora-release']}.items()}
        owner_uid = pwd.getpwnam(OWNER).pw_uid
        subject = subprocess.Popen(['setpriv', f'--reuid={OWNER}', f'--regid={OWNER}', '--init-groups', 'sleep', '600'])
        wrong = 'not-' + PASSWORD
        cases = [
            ('right password', dict(password=PASSWORD), True, None, True),
            ('no agent right after a yes', dict(agent=False), False, 'no password dialog', False),
            ('wrong password', dict(password=wrong), False, None, True),
            ('another start time for the same pid', dict(password=PASSWORD, offset=1), False, None, False),
            ('policy without the owner annotation', dict(action=UNOWNED, password=PASSWORD), False, 'trusted callers', False),
            ('right password again, another change', dict(password=PASSWORD, change=OTHER_CHANGE), True, None, True),
        ]
        results, failures = [], []
        for label, options, granted, reason, prompted in cases:
            result = {'case': label, **check(subject, owner_uid, **options)}
            results.append(result)
            problems = []
            if result['granted'] is not granted:
                problems.append(f'granted={result["granted"]}, expected {granted}')
            if reason and reason.lower() not in str(result.get('reason')).lower():
                problems.append(f'reason lacks {reason!r}')
            problems += dialog_problems(result, result['change'], prompted)
            if granted and result['prompts'] != 1:
                problems.append(f'{result["prompts"]} password prompts, expected one')
            if result.get('uid') != pwd.getpwnam(SERVICE_USER).pw_uid or result.get('no_new_privs') != '1' \
                    or set(str(result.get('bounding_set'))) != {'0'} or result.get('run_readonly') is not True:
                problems.append('the check did not run as the sandboxed service user')
            if problems:
                failures.append({'case': label, 'problems': problems})
            print(json.dumps({'case': label, 'granted': result['granted'], 'reason': result.get('reason'),
                              'dialog': dialog_messages(result['transcript']), 'problems': problems}), flush=True)
        subject.kill()
        polkitd.terminate()
    record = {'service_user': SERVICE_USER, 'action': ACTION, 'versions': versions, 'results': results, 'failures': failures,
              'successful': not failures}
    (OUT / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps({'successful': not failures, 'failures': failures}), flush=True)
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
