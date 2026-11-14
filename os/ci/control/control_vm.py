"""Package 18c, B2: boot the Control test layer's disk once and run its checks (check_build=control).

It boots like os/ci/vm.py, whose own sequence stays as it is, and asks the guest's CI channel (checks.py, with the
Control layer's actions from os/ci/control/actions.py) for one check after another. Every check runs even when an
earlier one fails, so one run shows them all; each success prints its fixed PASS line, and the evidence goes under
evidence/control/. Then the guest is powered off with its power key and must stop cleanly. Run from the checkout's
root as root (sudo -E), after check-build.sh built the disk from localhost/aresos:control.
"""
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
    ('control-restart', 'CONTROL_SERVICE_RESTART_PASS'),
]
# Lines whose summary is printed with them: the numbers the owner is asked about and the recorded PermissionRequest.
WITH_SUMMARY = {'control-idle', 'control-ordinary'}


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
    """Check 8 on the runner: the evidence written so far never holds the password (runner.sh stop checks again)."""
    secret = mail_fixture.password().encode()
    hits = sorted(str(path.relative_to(evidence)) for path in evidence.rglob('*')
                  if path.is_file() and secret in path.read_bytes())
    files = sum(1 for path in evidence.rglob('*') if path.is_file())
    (evidence / 'passwords-runner.json').write_text(json.dumps(dict(evidence_files=files, holding_it=len(hits)),
                                                               indent=2) + '\n')
    assert not hits, f'{len(hits)} evidence files hold the password'


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
    disks = list((work / 'output').rglob('disk.raw'))
    assert len(disks) == 1, disks
    overlay = work / 'control.qcow2'
    assert not overlay.exists(), 'The Control pass requires a fresh overlay'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(disks[0]), str(overlay)], check=True)
    shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', work / 'control-vars.fd')
    for name in ('control-qmp.sock', 'control-checks.sock'):
        if (work / name).is_socket():
            (work / name).unlink()
    accel = (['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK)
             else ['-accel', 'tcg,thread=multi', '-cpu', 'max'])
    (vm_evidence / 'vm-acceleration.txt').write_text(' '.join(accel) + '\n')
    started = time.monotonic()
    qemu = subprocess.Popen([
        'qemu-system-x86_64', '-machine', 'q35', *accel, '-smp', str(min(4, len(os.sched_getaffinity(0)))),
        '-m', '6144',
        '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
        '-drive', f'if=pflash,format=raw,file={work / "control-vars.fd"}',
        '-drive', f'file={overlay},format=qcow2,if=virtio',
        '-device', 'virtio-vga', '-device', 'qemu-xhci', '-device', 'usb-kbd', '-device', 'usb-tablet',
        # The guest reaches the runner's loopback, where the fixture servers listen, as 10.0.2.2.
        '-display', 'none', '-nic', 'user,model=virtio-net-pci',
        '-qmp', f'unix:{work / "control-qmp.sock"},server=on,wait=off',
        '-serial', f'file:{vm_evidence / "serial.log"}',
        '-device', 'virtio-serial-pci',
        '-chardev', f'socket,id=checks,path={work / "control-checks.sock"},server=on,wait=off',
        '-device', 'virtserialport,chardev=checks,name=org.aresos.ci', '-no-reboot',
    ], stdout=open(vm_evidence / 'qemu.log', 'w'), stderr=subprocess.STDOUT)

    def connect(path):
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.connect(str(path))
                return sock
            except OSError:
                sock.close()
                if qemu.poll() is not None:
                    raise RuntimeError(f'QEMU exited: {qemu.returncode}')
                time.sleep(0.2)
        raise TimeoutError(f'Socket did not appear: {path}')

    monitor = checks = qmp_socket = None
    failed, timings = [], {}
    try:
        qmp_socket = connect(work / 'control-qmp.sock')
        monitor = QMP(qmp_socket)
        monitor.command('qmp_capabilities')
        checks = connect(work / 'control-checks.sock')
        checks.settimeout(1800)
        incoming = Frames(checks.recv)
        assert incoming.receive() == {'ready': True, 'protocol': 1}
        timings['boot_to_channel'] = round(time.monotonic() - started, 1)
        for sequence, (action, line) in enumerate(CHECKS, 1):
            began = time.monotonic()
            try:
                request = dict(id=sequence, action=action, **arguments.get(action, dict)())
            except Exception:
                failed.append(action)
                print(f'CONTROL_CHECK_FAILED {action} (runner side)\n{traceback.format_exc()[-4000:]}', flush=True)
                continue
            checks.sendall(frame(request))
            del request
            result = incoming.receive()
            timings[action] = round(time.monotonic() - began, 1)
            assert result.get('id') == sequence, result
            for name, value in (result.pop('files', None) or {}).items():
                path = (evidence / name.removeprefix('control/')).resolve()
                assert path.is_relative_to(evidence), name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(import_bytes(value))
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
        # A clean poweroff through the power key, as vm.py ends.
        event_start = len(monitor.events)
        monitor.command('system_powerdown')
        qemu.wait(timeout=180)
        monitor.reader.join(timeout=5)
        assert qemu.returncode == 0, 'Power key did not shut the guest down cleanly'
        assert_guest_poweroff(monitor.events[event_start:])
        timings['total'] = round(time.monotonic() - started, 1)
        print('CONTROL_VM_POWEROFF_CLEAN', flush=True)
    finally:
        (vm_evidence / 'timings.json').write_text(json.dumps(timings, indent=2) + '\n')
        if monitor:
            (vm_evidence / 'qmp-events.json').write_text(json.dumps(monitor.events, indent=2) + '\n')
        if checks:
            checks.close()
        if qemu.poll() is None:
            qemu.terminate()
            try:
                qemu.wait(timeout=15)
            except subprocess.TimeoutExpired:
                qemu.kill()
                qemu.wait()
        if qmp_socket:
            qmp_socket.close()
        overlay.unlink(missing_ok=True)
    print(f'Control VM step times (s): {json.dumps(timings)}', flush=True)
    if failed:
        raise SystemExit(f'Control checks failed: {", ".join(failed)}')


if __name__ == '__main__':
    main()
