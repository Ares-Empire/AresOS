"""Package 18c, B2: boot the Control test layer's disk once and run its checks (check_build=control).

It boots like os/ci/vm.py, whose own sequence stays as it is, and asks the guest's CI channel (checks.py, with the
Control layer's actions from os/ci/control/actions.py) for one check after another. Every check runs even when an
earlier one fails, so one run shows them all; each success prints its fixed PASS line, and the evidence goes under
evidence/control/. Then the guest is powered off with its power key and must stop cleanly. Run from the checkout's
root as root (sudo -E), after check-build.sh built the disk from localhost/aresos:control.

`control_vm.py chrome` is brief 18c-b's second pass (item 5) on the same disk with a fresh overlay: Chrome's checks
(os/ci/control/chrome_actions.py) in CHROME_STEPS' order, with the runner's screenshots, keys and the pass's one
reboot between them through QMP. Its evidence goes under evidence/control/chrome/.
"""
import hashlib
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from channel import Frames, frame, import_bytes  # noqa: E402
from qmp import QMP, assert_guest_poweroff  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / 'control/ci/image'))
import mail_fixture  # noqa: E402

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import evidence_scan  # noqa: E402

# (action, the line its success prints). The order matters: the idle footprint comes before anything talks to the
# service; the sandbox check (2) after checks 3 to 5 and before check 6 restarts the service; check 9 before check 8,
# so the password scan also covers check 9's transcripts; check 2's SELinux scan again after checks 6 to 9.
CHECKS = [
    ('control-files', 'CONTROL_IMAGE_FILES_PASS'),
    ('control-claude-code-files', 'CONTROL_ETC_CLAUDE_CODE_PASS'),
    ('control-release', 'CONTROL_RELEASE_CHECKS_PASS'),
    ('control-idle', 'CONTROL_IDLE_FOOTPRINT_RECORDED'),
    ('control-fixtures', 'CONTROL_FIXTURES_REACHABLE'),
    ('control-entry-points', 'CONTROL_ENTRY_POINTS_PASS'),
    ('control-precondition', 'CONTROL_PRECONDITION_PASS'),
    ('control-user-mcp', 'CONTROL_USER_MCP_INSTALL_PASS'),
    ('control-service', 'CONTROL_SERVICE_SANDBOX_PASS'),
    ('control-ordinary', 'CONTROL_ORDINARY_SESSION_PASS'),
    ('control-mail', 'CONTROL_MAIL_FLOWS_PASS'),
    ('control-interactive', 'CONTROL_INTERACTIVE_ASK_PASS'),
    ('control-passwords', 'CONTROL_PASSWORDS_PRIVATE_PASS'),
    ('control-selinux', 'CONTROL_SELINUX_AFTER_CHECKS_PASS'),
    # The Chrome follow-up: Chrome's storage plan and timing tests on the image's Python and SQLite.
    ('control-storage-tests', 'CONTROL_STORAGE_TESTS_PASS'),
    ('control-restart', 'CONTROL_SERVICE_RESTART_PASS'),
]
# Lines whose summary is printed with them: the numbers the owner is asked about and the recorded PermissionRequest.
WITH_SUMMARY = {'control-idle', 'control-ordinary', 'control-storage-tests'}

# Brief 18c-b, item 5 (steps 4, 4b and 5 fill it in): ('act', action, PASS line or None), ('screen', name),
# ('keys', [qcode, ...]) or ('reboot',). An action without a line is one part of the next line's check: that line is
# printed only when every part since the previous line passed. The polkit probe comes first; C6's first use right
# after C2; the pass's one reboot after it; the SELinux scan last.
CHROME_STEPS = [
    ('screen', 'polkit-before'),
    ('act', 'chrome-polkit-start', None),
    ('screen', 'polkit-dialog'),
    ('keys', ['esc']),
    ('act', 'chrome-polkit-finish', 'CONTROL_CHROME_POLKIT_PROBE_PASS'),
    ('act', 'chrome-files', 'CONTROL_CHROME_FILES_PASS'),
    ('act', 'chrome-hand-loaded', None),
    ('act', 'chrome-install', None),
    ('screen', 'c2-pinned'),
    ('act', 'chrome-managed-page', 'CONTROL_CHROME_INSTALL_PASS'),
    ('screen', 'c2-managed'),
    ('act', 'chrome-sites-first-use', 'CONTROL_CHROME_SITES_FIRST_USE_PASS'),
    ('reboot',),
    ('act', 'chrome-sites-after-reboot', 'CONTROL_CHROME_SITES_REBOOT_PASS'),
    ('act', 'chrome-selinux', 'CONTROL_CHROME_SELINUX_PASS'),
]
CHROME_WITH_SUMMARY = {'chrome-polkit-finish', 'chrome-files', 'chrome-sites-first-use', 'chrome-sites-after-reboot'}


def install_step(readme):
    """The user-scope install step of control/README.md, word for word."""
    blocks = re.findall(r"```sh\n(python3 - <<'INSTALL'\n.*?\nINSTALL)\n```", readme, re.S)
    assert len(blocks) == 1, 'control/README.md must hold exactly one install step'
    return blocks[0]


def expected_record():
    """What this checkout installs (build.sh's own install map), as check-image.sh computes it."""
    with tempfile.TemporaryDirectory() as folder:
        subprocess.run(['bash', 'os/build.sh', 'control-tree', 'os', 'control', f'{folder}/root'], check=True,
                       stdout=subprocess.DEVNULL)
        record = json.loads(pathlib.Path(folder, 'root/usr/share/aresos/manifest/control.json').read_text())
    return {key: record[key] for key in ('files', 'links', 'directories')}


def mail_arrivals(result, seeded, evidence):
    """Check 7 on the runner: GreenMail holds exactly one arrival per send, the attachment byte for byte, and the
    message the guest read is still unread on Dovecot."""
    summary = result['summary']
    received = {kind: mail_fixture.arrivals(sent['recipient']) for kind, sent in summary['sent'].items()}
    record = dict(received=received, onboarding_self_send=mail_fixture.arrivals(mail_fixture.ADDRESS),
                  read_message_flags=mail_fixture.flags(seeded['read']['message_id']),
                  deleted_left_inbox=mail_fixture.flags(seeded['delete']['message_id']) is None)
    (evidence / 'mail-runner.json').write_text(json.dumps(record, indent=2) + '\n')
    for kind, sent in summary['sent'].items():
        assert [mail['subject'] for mail in received[kind]] == [sent['subject']], (kind, received[kind])
    attachments = received['attachment'][0]['attachments']
    out = summary['attachment_out']
    assert [(item['size'], item['sha256']) for item in attachments] == [(out['size'], out['sha256'])], attachments
    assert '\\Seen' not in record['read_message_flags'], record['read_message_flags']
    assert record['deleted_left_inbox'], 'the deleted message is still in INBOX'


def password_not_in_evidence(evidence):
    """Check 8 on the runner: the evidence written so far never holds the password, also inside the checks'
    .tar.gz files (REVIEW-A1 #5); runner.sh stop checks again with the fixture logs."""
    found = evidence_scan.scan(evidence, mail_fixture.password().encode())
    (evidence / 'passwords-runner.json').write_text(json.dumps(dict(
        evidence_files=found['files'], archive_members=found['members'], holding_it=len(found['holding']),
        unreadable=found['unreadable']), indent=2) + '\n')
    assert not found['holding'], f'{len(found["holding"])} evidence files hold the password or cannot be searched'


class Guest:
    """One QEMU guest on an overlay of the disk the control build made: boot, ask, look, press, power off."""

    def __init__(self, work, evidence, name):
        self.work, self.evidence, self.name = work, evidence, name
        self.overlay = work / f'{name}.qcow2'
        self.vars = work / f'{name}-vars.fd'
        self.qemu = self.monitor = self.checks = self.qmp_socket = self.incoming = None
        self.boots, self.sequence, self.events = 0, 0, []

    def create(self):
        disks = list((self.work / 'output').rglob('disk.raw'))
        assert len(disks) == 1, disks
        assert not self.overlay.exists(), f'The {self.name} pass requires a fresh overlay'
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(disks[0]), str(self.overlay)],
                       check=True)
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', self.vars)

    def boot(self):
        """Start QEMU on the overlay (again, for a reboot) and wait for the guest's CI channel. Seconds to the channel."""
        self.boots += 1
        suffix = '' if self.boots == 1 else f'-{self.boots}'
        qmp_path, checks_path = self.work / f'{self.name}-qmp.sock', self.work / f'{self.name}-checks.sock'
        for path in (qmp_path, checks_path):
            if path.is_socket():
                path.unlink()
        accel = (['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK)
                 else ['-accel', 'tcg,thread=multi', '-cpu', 'max'])
        (self.evidence / 'vm-acceleration.txt').write_text(' '.join(accel) + '\n')
        started = time.monotonic()
        self.qemu = subprocess.Popen([
            'qemu-system-x86_64', '-machine', 'q35', *accel, '-smp', str(min(4, len(os.sched_getaffinity(0)))),
            '-m', '6144',
            '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
            '-drive', f'if=pflash,format=raw,file={self.vars}',
            '-drive', f'file={self.overlay},format=qcow2,if=virtio',
            '-device', 'virtio-vga', '-device', 'qemu-xhci', '-device', 'usb-kbd', '-device', 'usb-tablet',
            # The guest reaches the runner's loopback, where the fixture servers listen, as 10.0.2.2.
            '-display', 'none', '-nic', 'user,model=virtio-net-pci',
            '-qmp', f'unix:{qmp_path},server=on,wait=off',
            '-serial', f'file:{self.evidence / f"serial{suffix}.log"}',
            '-device', 'virtio-serial-pci',
            '-chardev', f'socket,id=checks,path={checks_path},server=on,wait=off',
            '-device', 'virtserialport,chardev=checks,name=org.aresos.ci', '-no-reboot',
        ], stdout=open(self.evidence / f'qemu{suffix}.log', 'w'), stderr=subprocess.STDOUT)
        self.qmp_socket = self.connect(qmp_path)
        self.monitor = QMP(self.qmp_socket)
        self.monitor.command('qmp_capabilities')
        self.checks = self.connect(checks_path)
        self.checks.settimeout(1800)
        self.incoming = Frames(self.checks.recv)
        assert self.incoming.receive() == {'ready': True, 'protocol': 1}
        return round(time.monotonic() - started, 1)

    def connect(self, path):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.connect(str(path))
                return sock
            except OSError:
                sock.close()
                if self.qemu.poll() is not None:
                    raise RuntimeError(f'QEMU exited: {self.qemu.returncode}')
                time.sleep(0.2)
        raise TimeoutError(f'Socket did not appear: {path}')

    def act(self, request):
        """Send one action; its answer comes back with the same id."""
        self.sequence += 1
        self.checks.sendall(frame(dict(request, id=self.sequence)))
        result = self.incoming.receive()
        assert result.get('id') == self.sequence, result
        return result

    def keys(self, names):
        self.monitor.command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in names], 'hold-time': 100})

    def screenshot(self, path):
        from PIL import Image  # the runner's, as os/ci/vm.py uses it; not needed to load this file elsewhere
        ppm = self.work / f'{self.name}-screen.ppm'
        self.monitor.command('screendump', {'filename': str(ppm)})
        with Image.open(ppm) as image:
            image.save(path)
        ppm.unlink()

    def poweroff(self):
        """A clean poweroff through the power key, as vm.py ends."""
        event_start = len(self.monitor.events)
        self.monitor.command('system_powerdown')
        self.qemu.wait(timeout=180)
        self.monitor.reader.join(timeout=5)
        assert self.qemu.returncode == 0, 'Power key did not shut the guest down cleanly'
        assert_guest_poweroff(self.monitor.events[event_start:])
        self.release()

    def release(self):
        if self.monitor:
            self.events += self.monitor.events
            self.monitor = None
        if self.checks:
            self.checks.close()
            self.checks = None
        if self.qemu and self.qemu.poll() is None:
            self.qemu.terminate()
            try:
                self.qemu.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.qemu.kill()
                self.qemu.wait()
        if self.qmp_socket:
            self.qmp_socket.close()
            self.qmp_socket = None

    def close(self):
        self.release()
        (self.evidence / 'qmp-events.json').write_text(json.dumps(self.events, indent=2) + '\n')
        self.overlay.unlink(missing_ok=True)


def keep_files(result, evidence):
    for name, value in (result.pop('files', None) or {}).items():
        path = (evidence / name.removeprefix('control/')).resolve()
        assert path.is_relative_to(evidence), name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(import_bytes(value))


def main():
    work = pathlib.Path('vm-work').resolve()
    evidence = pathlib.Path('evidence').resolve() / 'control'
    vm_evidence = evidence / 'vm'
    vm_evidence.mkdir(parents=True, exist_ok=True)
    # check-build.sh reads the commit as the runner's user (git refuses a checkout owned by another one).
    revision = os.environ['ARESOS_REVISION']
    assert re.fullmatch('[0-9a-f]{40}', revision), revision
    expected_pin = json.loads(pathlib.Path('control/boundary/interactive-permission-request-expected.json')
                              .read_text())
    seeded = {}
    # Built when the action is sent: the seeding needs the servers up, the password stays in memory, and no request
    # is ever written anywhere.
    arguments = {'control-files': lambda: dict(revision=revision, expected=expected_record()),
                 'control-idle': lambda: dict(seconds=60),
                 'control-user-mcp': lambda: dict(install=install_step(pathlib.Path('control/README.md').read_text())),
                 'control-mail': lambda: dict(password=mail_fixture.password(), seeded=seeded.setdefault(
                     'mail', mail_fixture.seed())),
                 'control-interactive': lambda: dict(expected=expected_pin),
                 'control-passwords': lambda: dict(password=mail_fixture.password()),
                 'control-restart': lambda: dict(mail_account='ci')}
    verify = {'control-mail': lambda result: mail_arrivals(result, seeded['mail'], evidence),
              'control-passwords': lambda result: password_not_in_evidence(evidence)}
    guest = Guest(work, vm_evidence, 'control')
    guest.create()
    started = time.monotonic()
    failed, timings = [], {}
    try:
        timings['boot_to_channel'] = guest.boot()
        for action, line in CHECKS:
            began = time.monotonic()
            try:
                request = dict(action=action, **arguments.get(action, dict)())
            except Exception:
                failed.append(action)
                print(f'CONTROL_CHECK_FAILED {action} (runner side)\n{traceback.format_exc()[-4000:]}', flush=True)
                continue
            result = guest.act(request)
            del request
            timings[action] = round(time.monotonic() - began, 1)
            keep_files(result, evidence)
            if result.get('returncode') == 0 and action in verify:
                try:
                    verify[action](result)
                except Exception:
                    result.update(returncode=1, stderr=traceback.format_exc())
            (vm_evidence / f'{action}-result.json').write_text(json.dumps(result, indent=2) + '\n')
            if 'permission_request' in (result.get('summary') or {}):
                # Recorded whatever the other cases showed: the accepted residual of brief B2 check 9.
                print('CONTROL_PERMISSION_REQUEST_RECORDED ' + json.dumps(
                    result['summary']['permission_request'], sort_keys=True), flush=True)
            if result.get('returncode') == 0:
                summary = json.dumps(result.get('summary', {}), sort_keys=True)
                print(f'{line} {summary}' if action in WITH_SUMMARY else line, flush=True)
                print(f'  {action}: {summary[:3000]}', flush=True)
            else:
                failed.append(action)
                print(f'CONTROL_CHECK_FAILED {action}\n{result.get("stderr", "")[-6000:]}', flush=True)
        guest.poweroff()
        timings['total'] = round(time.monotonic() - started, 1)
        print('CONTROL_VM_POWEROFF_CLEAN', flush=True)
    finally:
        (vm_evidence / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')
        guest.close()
    print(f'Control VM step times (s): {json.dumps(timings)}', flush=True)
    if failed:
        raise SystemExit(f'Control checks failed: {", ".join(failed)}')


def screen_difference(first, second):
    """How many pixels differ between two screenshots of the same size (the polkit dialog's appearance)."""
    from PIL import Image, ImageChops
    with Image.open(first) as a, Image.open(second) as b:
        difference = ImageChops.difference(a.convert('RGB'), b.convert('RGB')).convert('L')
        return sum(count for value, count in enumerate(difference.histogram()) if value > 24)


def chrome_main():
    """Brief 18c-b, item 5: the Chrome pass, on the same disk with a fresh overlay, after 18c's pass."""
    work = pathlib.Path('vm-work').resolve()
    evidence = pathlib.Path('evidence').resolve() / 'control'
    chrome_evidence = evidence / 'chrome'
    vm_evidence = chrome_evidence / 'vm'
    vm_evidence.mkdir(parents=True, exist_ok=True)
    results = {}
    # The runner's inputs: what the commit installs (as check 1 computes it) and the reviewed gh lock.
    arguments = {'chrome-files': lambda: dict(expected=expected_record(), gh_lock_sha256=hashlib.sha256(
                     pathlib.Path('os/gh.lock.json').read_bytes()).hexdigest()),
                 'chrome-sites-after-reboot': lambda: dict(list=results['chrome-sites-first-use']['summary']['list'])}
    verify = {'chrome-polkit-finish': lambda result: result['summary'].update(screen_pixels_changed=screen_difference(
        chrome_evidence / 'polkit-before.png', chrome_evidence / 'polkit-dialog.png'))}
    guest = Guest(work, vm_evidence, 'chrome')
    guest.create()
    started = time.monotonic()
    failed, timings, parts_failed = [], {}, False
    try:
        timings['boot_to_channel'] = guest.boot()
        for step in CHROME_STEPS:
            began = time.monotonic()
            kind = step[0]
            try:
                if kind == 'screen':
                    guest.screenshot(chrome_evidence / f'{step[1]}.png')
                    continue
                if kind == 'keys':
                    guest.keys(step[1])
                    continue
                if kind == 'reboot':
                    guest.poweroff()
                    timings['reboot_to_channel'] = guest.boot()
                    print('CONTROL_CHROME_REBOOTED', flush=True)
                    continue
                _, action, line = step
                result = guest.act(dict(action=action, **arguments.get(action, dict)()))
            except Exception:
                label = step[1] if kind == 'act' else ' '.join(map(str, step))
                failed.append(label)
                parts_failed = True
                print(f'CONTROL_CHECK_FAILED {label} (runner side)\n{traceback.format_exc()[-4000:]}', flush=True)
                continue
            finally:
                timings[step[1] if len(step) > 1 and isinstance(step[1], str) else kind] = round(
                    time.monotonic() - began, 1)
            keep_files(result, evidence)
            if result.get('returncode') == 0 and action in verify:
                try:
                    verify[action](result)
                except Exception:
                    result.update(returncode=1, stderr=traceback.format_exc())
            results[action] = result
            (vm_evidence / f'{action}-result.json').write_text(json.dumps(result, indent=2) + '\n')
            summary = json.dumps(result.get('summary', {}), sort_keys=True)
            if result.get('returncode') != 0:
                failed.append(action)
                parts_failed = True
                print(f'CONTROL_CHECK_FAILED {action}\n{result.get("stderr", "")[-6000:]}', flush=True)
            if line and not parts_failed:
                print(f'{line} {summary}' if action in CHROME_WITH_SUMMARY else line, flush=True)
            if result.get('returncode') == 0:
                print(f'  {action}: {summary[:3000]}', flush=True)
            if line:
                parts_failed = False
        guest.poweroff()
        timings['total'] = round(time.monotonic() - started, 1)
        print('CONTROL_CHROME_VM_POWEROFF_CLEAN', flush=True)
    finally:
        (vm_evidence / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')
        guest.close()
    print(f'Control Chrome VM step times (s): {json.dumps(timings)}', flush=True)
    if failed:
        raise SystemExit(f'Control Chrome checks failed: {", ".join(failed)}')


if __name__ == '__main__':
    if sys.argv[1:] == ['chrome']:
        chrome_main()
    else:
        assert not sys.argv[1:], sys.argv
        main()
