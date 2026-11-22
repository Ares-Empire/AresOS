"""Run the output gate on six fresh overlays of the CI-only disk."""
import contextlib
import json
import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from channel import Frames, frame  # noqa: E402
from qmp import QMP  # noqa: E402

PRIMARY = 'Virtual-1'
SECONDARY = 'Virtual-2'
STATES = ('none', 'listener', 'backend')


class GuestFailure(Exception):
    pass


def connect(path, process):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        with contextlib.closing(socket.socket(socket.AF_UNIX)) as probe:
            try:
                probe.connect(str(path))
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError(f'QEMU exited before {path.name}: {process.returncode}')
            else:
                return socket.socket(fileno=probe.detach())
        time.sleep(0.2)
    raise TimeoutError(f'Socket did not appear: {path}')


def stop(process):
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


class Boot:
    def __init__(self, qmp, checks, bus, evidence):
        self.qmp = qmp
        self.checks = checks
        self.incoming = Frames(checks.recv)
        self.bus = bus
        self.evidence = evidence
        self.sequence = 0

    def request(self, action, **arguments):
        self.sequence += 1
        request = dict(id=self.sequence, action=f'deskflow-{action}', **arguments)
        self.checks.sendall(frame(request))
        result = self.incoming.receive()
        assert result['id'] == self.sequence, result
        with (self.evidence / 'operations.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(request=request, result=result)) + '\n')
        if result.get('returncode') != 0:
            raise GuestFailure(result.get('stderr', repr(result)))
        return result

    def keys(self, key):
        self.qmp.command('send-key', {'keys': [{'type': 'qcode', 'data': name} for name in ('ctrl', 'alt', key)],
                                      'hold-time': 100})

    def ui_info(self, connected):
        size = ['270', '170', '1024', '0', '1024', '768'] if connected else ['0'] * 6
        result = subprocess.run([
            'busctl', f'--address={self.bus}', '--timeout=10s', 'call', 'org.qemu',
            '/org/qemu/Display1/Console_1', 'org.qemu.Display1.Console', 'SetUIInfo', 'qqiiuu', *size,
        ], capture_output=True, text=True, timeout=12)
        with (self.evidence / 'hotplug-commands.jsonl').open('a') as stream:
            stream.write(json.dumps(dict(connected=connected, returncode=result.returncode,
                                         stdout=result.stdout, stderr=result.stderr)) + '\n')
        return result.returncode == 0


@contextlib.contextmanager
def boot(disk, work, evidence):
    work.mkdir()
    evidence.mkdir()
    overlay = work / 'disk.qcow2'
    subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(disk), str(overlay)], check=True)
    shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', work / 'vars.fd')
    # Never contact the runner's session bus. Use an address owned by this boot.
    address = f'unix:path={work / "display.sock"}'
    accel = (['-accel', 'kvm', '-cpu', 'host'] if os.access('/dev/kvm', os.R_OK | os.W_OK)
             else ['-accel', 'tcg,thread=multi', '-cpu', 'max'])
    with (evidence / 'qemu.log').open('w') as log, contextlib.ExitStack() as stack:
        bus = subprocess.Popen(['dbus-daemon', '--session', '--nofork', f'--address={address}', '--print-address=1'],
                               stdout=subprocess.PIPE, stderr=log, text=True)
        stack.callback(stop, bus)
        assert bus.stdout.readline().startswith(address), 'private display bus did not start'
        bus.stdout.close()
        process = subprocess.Popen([
            'qemu-system-x86_64', '-machine', 'q35', *accel,
            '-smp', str(min(4, len(os.sched_getaffinity(0)))), '-m', '6144',
            '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
            '-drive', f'if=pflash,format=raw,file={work / "vars.fd"}',
            '-drive', f'file={overlay},format=qcow2,if=virtio',
            '-device', 'virtio-vga,max_outputs=2', '-device', 'qemu-xhci',
            '-device', 'usb-kbd', '-device', 'usb-tablet',
            '-device', 'pcie-root-port,id=deskflow-port,slot=1',
            '-display', 'dbus', '-nic', 'user,model=virtio-net-pci',
            '-qmp', f'unix:{work / "qmp.sock"},server=on,wait=off',
            '-serial', f'file:{evidence / "serial.log"}',
            '-device', 'virtio-serial-pci',
            '-chardev', f'socket,id=checks,path={work / "checks.sock"},server=on,wait=off',
            '-device', 'virtserialport,chardev=checks,name=org.aresos.ci', '-no-reboot',
        ], env=dict(os.environ, DBUS_SESSION_BUS_ADDRESS=address), stdout=log, stderr=subprocess.STDOUT)
        stack.callback(overlay.unlink)
        stack.callback(stop, process)
        monitor = QMP(stack.enter_context(connect(work / 'qmp.sock', process)))
        monitor.command('qmp_capabilities')
        checks = stack.enter_context(connect(work / 'checks.sock', process))
        checks.settimeout(170)
        guest = Boot(monitor, checks, address, evidence)
        assert guest.incoming.receive() == {'ready': True, 'protocol': 1}
        try:
            yield guest
        finally:
            (evidence / 'qmp-events.json').write_text(json.dumps(monitor.events, indent=2) + '\n')
            try:
                guest.request('diagnostics')
            except (OSError, EOFError, GuestFailure):
                pass


def mode_size(mode):
    return mode['width'], mode['height']


def mode_arg(mode):
    size = f'{mode["width"]}x{mode["height"]}'
    refresh = mode.get('refresh')
    return f'{size}@{refresh:.3f}Hz' if refresh else size


def set_mode(guest, name, mode, *, custom=False):
    if mode is None:
        guest.request('change', output=name, option='off')
    else:
        guest.request('change', output=name, option='custom-mode' if custom else 'mode', mode=mode_arg(mode))


def verify_mode(guest, name, mode):
    output = guest.request('snapshot')['outputs'][name]
    assert output['enabled'] == (mode is not None), output
    if mode is not None:
        current, = [listed for listed in output['modes'] if listed['current']]
        assert mode_size(current) == mode_size(mode), output
        if 'refresh' in mode:
            assert round(current['refresh'], 3) == round(mode['refresh'], 3), output


def wait_connector(guest, connected, original=None):
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        snap = guest.request('snapshot')
        outputs, connectors = snap['outputs'], snap['connectors']
        assert outputs[PRIMARY]['enabled'], outputs
        if original is None:
            drm = [path for path in connectors if path.endswith(f'-{SECONDARY}')]
            status = drm and all(connectors[path] == ('connected' if connected else 'disconnected') for path in drm)
            if status and (SECONDARY in outputs) == connected:
                return SECONDARY
        else:
            added = {path for path, state in connectors.items() if state == 'connected'} - original
            names = set(outputs) - {PRIMARY, SECONDARY, 'FALLBACK'}
            # The second DRM device may expose a duplicate Virtual-1.
            if not connected and not added and not names:
                return True
            if connected and len(added) == len(names) == 1:
                return names.pop()
        time.sleep(0.4)
    return None


def hotplug(guest):
    base = guest.request('snapshot')
    plugged = guest.ui_info(True)
    appeared = plugged and wait_connector(guest, True)
    unplugged = plugged and guest.ui_info(False)
    vanished = unplugged and wait_connector(guest, False)
    if appeared and vanished:
        def toggle(connected):
            assert guest.ui_info(connected), 'SetUIInfo rejected'
            assert wait_connector(guest, connected), f'no DRM/labwc transition for connected={connected}'

        name = SECONDARY
        method = 'SetUIInfo'
    else:
        # A root port is present even when QEMU cannot change the virtio scanout.
        original = {path for path, state in base['connectors'].items() if state == 'connected'}

        def pci(connected):
            if connected:
                guest.qmp.command('device_add', {'driver': 'virtio-gpu-pci', 'bus': 'deskflow-port', 'id': 'deskflow-head'})
            else:
                guest.qmp.command('device_del', {'id': 'deskflow-head'})
            return wait_connector(guest, connected, original)

        try:
            name = pci(True)
            detached = pci(False)
        except RuntimeError as error:
            print(f'DESKFLOW_HOTPLUG_UNVERIFIED {error}', flush=True)
            return 'unverified'
        if not name or not detached:
            print('DESKFLOW_HOTPLUG_UNVERIFIED no second output transition in both DRM and labwc', flush=True)
            return 'unverified'

        def toggle(connected):
            assert pci(connected), f'no PCI DRM/labwc transition for connected={connected}'

        method = 'virtio-gpu-pci'
    toggle(True)
    for _ in range(2):
        toggle(False)
        toggle(True)
    output = guest.request('snapshot')['outputs'][name]
    mode, = [listed for listed in output['modes'] if listed['preferred']]
    set_mode(guest, name, None)
    verify_mode(guest, name, None)
    set_mode(guest, name, mode)
    verify_mode(guest, name, mode)
    return method


def regular(guest, ready):
    modes = ready['outputs'][PRIMARY]['modes']
    preferred, = [mode for mode in modes if mode['preferred']]
    alternate = next(mode for mode in modes if mode_size(mode) != mode_size(preferred))
    if not preferred['current']:
        set_mode(guest, PRIMARY, preferred)
    verify_mode(guest, PRIMARY, preferred)
    for mode in (preferred, alternate):
        for _ in range(3):
            set_mode(guest, PRIMARY, None)
            verify_mode(guest, PRIMARY, None)
            set_mode(guest, PRIMARY, mode)
            verify_mode(guest, PRIMARY, mode)
    guest.keys('f3')
    guest.request('vt', expected='tty3')
    guest.keys('f1')
    guest.request('vt', expected='tty1')
    assert guest.request('snapshot', geometry=False)['outputs'][PRIMARY]['enabled']
    return dict(status='passed', hotplug=hotplug(guest))


def custom(guest, ready):
    modes = ready['outputs'][PRIMARY]['modes']
    mode = dict(width=1022, height=766)
    assert mode_size(mode) not in {mode_size(listed) for listed in modes}
    try:
        set_mode(guest, PRIMARY, mode, custom=True)
        set_mode(guest, PRIMARY, None)
        set_mode(guest, PRIMARY, mode, custom=True)
        verify_mode(guest, PRIMARY, mode)
    except (GuestFailure, AssertionError) as error:
        proof = guest.request('diagnostics')
        log = str(error) + proof['session_log']
        kind = 'compositor-assertion' if 'head_send_state' in log and 'Assertion' in log else 'unverified'
        return dict(status=kind, detail=str(error)[-2000:])
    return dict(status='passed')


def main():
    vm_work = pathlib.Path('vm-work').resolve()
    disk, = (vm_work / 'output').rglob('disk.raw')
    work = vm_work / 'deskflow'
    work.mkdir()
    evidence = pathlib.Path('evidence/deskflow').resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    results = {}
    for scenario in (regular, custom):
        for state in STATES:
            name = f'{scenario.__name__}-{state}'
            try:
                with boot(disk, work / name, evidence / name) as guest:
                    ready = guest.request('ready', state=state)
                    results[name] = scenario(guest, ready)
            except Exception as error:
                results[name] = dict(status='failed', detail=str(error)[-4000:])
            print(f'DESKFLOW_VM {name} {json.dumps(results[name])}', flush=True)
    passed = all(results[f'regular-{state}']['status'] == 'passed' for state in STATES)
    (evidence / 'result.json').write_text(json.dumps(dict(gate='passed' if passed else 'failed', boots=results),
                                                     indent=2) + '\n')
    if not passed:
        raise SystemExit('DESKFLOW_OUTPUT_GATE_FAILED')
    print('DESKFLOW_OUTPUT_GATE_PASSED', flush=True)


if __name__ == '__main__':
    main()
