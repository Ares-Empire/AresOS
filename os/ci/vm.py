"""Boot a CI-only file disk; use virtio checks, QMP events and a passive console."""
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import time

from PIL import Image
from channel import Frames, frame, import_bytes
from qmp import QMP, assert_guest_poweroff
from offline_journal import check_offline_poweroff

work = pathlib.Path('vm-work').resolve()
evidence = pathlib.Path('evidence').resolve() / f'vm-pass-{os.environ["ARESOS_VM_PASS"]}'
evidence.mkdir(parents=True, exist_ok=True)
password = json.loads((work / 'credentials.json').read_text())['password']
disks = list((work / 'output').rglob('disk.raw'))
assert len(disks) == 1, disks
disk = disks[0]
assert disk.is_file() and disk.is_relative_to(work)
overlay = work / f'pass-{os.environ["ARESOS_VM_PASS"]}.qcow2'
assert not overlay.exists(), 'Each VM pass requires a fresh overlay'
subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(disk), str(overlay)], check=True)
firmware = pathlib.Path('/usr/share/OVMF/OVMF_CODE_4M.fd')
variables = pathlib.Path('/usr/share/OVMF/OVMF_VARS_4M.fd')
shutil.copyfile(variables, work / 'vars.fd')
for name in ('qmp.sock', 'checks.sock'):
    path = work / name
    if path.is_socket():
        path.unlink()
accel = ['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK) else ['-accel', 'tcg,thread=multi', '-cpu', 'max']
(evidence / 'vm-acceleration.txt').write_text(' '.join(accel) + '\n')
qemu = subprocess.Popen([
    'qemu-system-x86_64', '-machine', 'q35', *accel, '-smp', str(min(4, len(os.sched_getaffinity(0)))), '-m', '6144',
    '-drive', f'if=pflash,format=raw,readonly=on,file={firmware}',
    '-drive', f'if=pflash,format=raw,file={work / "vars.fd"}',
    '-drive', f'file={overlay},format=qcow2,if=virtio',
    '-device', 'virtio-vga', '-device', 'qemu-xhci', '-device', 'usb-kbd', '-device', 'usb-tablet',
    '-display', 'none', '-nic', 'user,model=virtio-net-pci',
    '-qmp', f'unix:{work / "qmp.sock"},server=on,wait=off',
    '-serial', f'file:{evidence / "serial.log"}',
    '-device', 'virtio-serial-pci',
    '-chardev', f'socket,id=checks,path={work / "checks.sock"},server=on,wait=off',
    '-device', 'virtserialport,chardev=checks,name=org.aresos.ci', '-no-reboot',
], stdout=open(evidence / 'qemu.log', 'w'), stderr=subprocess.STDOUT)
monitor = None
checks = None
sequence = 0


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


def request(action, **arguments):
    global sequence
    sequence += 1
    checks.sendall(frame(dict(id=sequence, action=action, **arguments)))
    result = incoming.receive()
    assert result.get('id') == sequence, result
    (evidence / f'{action}-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Guest {action}: {result.get("returncode")}', flush=True)
    if result.get('stdout'):
        print(result['stdout'], flush=True)
    assert result.get('returncode') == 0, result
    return result


def export():
    result = request('export')
    for name, value in result['files'].items():
        assert name in ('backend.json', 'runtime-updaters.json', 'power-events.json', 'updater-regressions.json'), name
        raw = import_bytes(value)
        json.loads(raw)
        (evidence / name).write_bytes(raw)
    return result['files']


def keys(names):
    monitor.command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in names], 'hold-time': 100})


def screenshot(name):
    ppm = work / 'screen.ppm'
    monitor.command('screendump', {'filename': str(ppm)})
    with Image.open(ppm) as image:
        image.save(evidence / name)


try:
    qmp_socket = connect(work / 'qmp.sock')
    monitor = QMP(qmp_socket)
    monitor.command('qmp_capabilities')
    checks = connect(work / 'checks.sock')
    checks.settimeout(900)
    incoming = Frames(checks.recv)
    assert incoming.receive() == {'ready': True, 'protocol': 1}
    request('policy')
    assert {'backend.json', 'runtime-updaters.json', 'updater-regressions.json'} <= export().keys()
    request('power-events')
    assert 'power-events.json' in export()
    assert monitor.command('query-status')['status'] == 'running', 'Ignored power events stopped the VM'
    keys(['ctrl', 'meta_l', 'esc'])
    request('shortcut')
    screenshot('aresos-labwc.png')
    keys(['ctrl', 'alt', 'f3'])
    request('recovery', password=password)
    screenshot('aresos-tty3-getty.png')
    keys(['ctrl', 'alt', 'f1'])
    journal_start = (evidence / 'serial.log').stat().st_size
    prepared = request('prepare-poweroff')
    deadline = time.monotonic() + 60
    while b'ARESOS_JOURNAL_READY' not in (evidence / 'serial.log').read_bytes()[journal_start:]:
        if qemu.poll() is not None or time.monotonic() >= deadline:
            raise TimeoutError('Journal follower did not forward its readiness record')
        time.sleep(0.1)
    screenshot('last-vm-frame.png')
    shutdown_start = (evidence / 'serial.log').stat().st_size
    event_start = len(monitor.events)
    monitor.command('system_powerdown')
    qemu.wait(timeout=120)
    monitor.reader.join(timeout=5)
    assert qemu.returncode == 0, 'Power key did not shut the guest down cleanly'
    shutdown_event = assert_guest_poweroff(monitor.events[event_start:])
    shutdown = (evidence / 'serial.log').read_bytes()[shutdown_start:].decode(errors='replace')
    assert re.search(r'Reached target[^\n]*(?:Power-Off|System Power Off|poweroff.target)', shutdown), 'Missing poweroff target evidence'
    offline = check_offline_poweroff(overlay, work, evidence, prepared['boot_id'])
    (evidence / 'poweroff.txt').write_text('QMP ACPI button -> poweroff.target -> guest SHUTDOWN -> QEMU exit 0\n'
                                         + f'Offline logind path: {offline["status"]}\n' + shutdown)
    (evidence / 'poweroff.json').write_text(json.dumps(dict(qemu_exit=0, journal_ready=True,
                                                         boot_id=offline['boot_id'],
                                                         offline_journal=offline,
                                                         shutdown=shutdown_event), indent=2) + '\n')
    print('UEFI VM checks passed: session, updater/sleep policy, recovery shortcut, tty3 getty, password authentication via login PAM, ignored lid/sleep events, clean ACPI poweroff', flush=True)
finally:
    if monitor:
        if qemu.poll() is None:
            try:
                screenshot('last-vm-frame.png')
            except Exception:
                pass
        (evidence / 'qmp-events.json').write_text(json.dumps(monitor.events, indent=2) + '\n')
    if checks:
        checks.close()
    if qemu.poll() is None:
        qemu.terminate()
        try:
            qemu.wait(timeout=15)
        except subprocess.TimeoutExpired:
            qemu.kill()
            qemu.wait()
    if monitor:
        qmp_socket.close()
