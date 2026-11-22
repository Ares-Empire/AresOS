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
HOTPLUG_REHEARSAL = (
    "Before publication, get the owner's direct OK to run the check build's backend by hand "
    "on the laptop without installing it and unplug and replug the external monitor three times."
)


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
    output = guest.request('snapshot')['outputs'].get(name)
    assert output is not None, f'{name} missing from the output list'
    assert output['enabled'] == (mode is not None), output
    if mode is not None:
        current = [listed for listed in output['modes'] if listed['current']]
        assert len(current) == 1, output
        current = current[0]
        assert mode_size(current) == mode_size(mode), output
        if 'refresh' in mode:
            assert round(current['refresh'], 3) == round(mode['refresh'], 3), output


def wait_connector(guest, connected, original=None, *, secondary_before=()):
    drm_seen = False
    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        snap = guest.request('snapshot')
        outputs, connectors = snap['outputs'], snap['connectors']
        assert outputs[PRIMARY]['enabled'], outputs
        if original is None:
            drm = [path for path in connectors if path.endswith(f'-{SECONDARY}')]
            status = 'connected' if connected else 'disconnected'
            drm_match = any(connectors[path] == status for path in drm) or (
                not connected and any(path not in connectors for path in secondary_before)
            )
            labwc_match = (SECONDARY in outputs) == connected
            names = {SECONDARY} if connected else set()
        else:
            added = {path for path, state in connectors.items() if state == 'connected'} - original
            names = set(outputs) - {PRIMARY, SECONDARY, 'FALLBACK'}
            # The second DRM device may expose a duplicate Virtual-1.
            drm_match = bool(added) == connected
            labwc_match = len(names) == int(connected)
            assert len(added) <= 1, f'PCI fallback added multiple DRM connectors: {added}'
        if drm_match and labwc_match:
            return names.pop() if connected else True
        drm_seen |= drm_match
        time.sleep(0.4)
    assert not drm_seen, f'DRM reached connected={connected}, but labwc did not reflect the connector transition'
    return None


def hotplug(guest):
    base = guest.request('snapshot')
    original = {path for path, state in base['connectors'].items() if state == 'connected'}
    initially_connected = any(path.endswith(f'-{SECONDARY}') for path in original)

    def ui(connected):
        secondary_before = set()
        if not connected:
            before = guest.request('snapshot')['connectors']
            secondary_before = {path for path, state in before.items()
                                if state == 'connected' and path.endswith(f'-{SECONDARY}')}
        accepted = guest.ui_info(connected)
        observed = wait_connector(guest, connected, secondary_before=secondary_before)
        if observed:
            assert accepted, f'SetUIInfo rejected connected={connected}'
        return observed

    if ui(not initially_connected):
        toggle = ui
        method = 'SetUIInfo'
        cycles = 3
        if initially_connected:
            assert toggle(True), 'DRM did not reconnect after the SetUIInfo probe'
            cycles -= 1
    else:
        # A root port is present even when QEMU cannot change the virtio scanout.
        def pci(connected):
            if connected:
                guest.qmp.command('device_add', {'driver': 'virtio-gpu-pci', 'bus': 'deskflow-port', 'id': 'deskflow-head'})
            else:
                guest.qmp.command('device_del', {'id': 'deskflow-head'})

        rejected = None
        try:
            pci(True)
        except RuntimeError as error:
            rejected = str(error)
        name = wait_connector(guest, True, original)
        if not name:
            detail = 'Neither SetUIInfo nor the PCI fallback drove the DRM connector'
            if rejected:
                detail += f' (PCI command rejected: {rejected})'
            return dict(hotplug='unverified', detail=detail,
                        publication_requires=HOTPLUG_REHEARSAL)
        assert rejected is None, f'PCI command rejected despite a DRM transition: {rejected}'

        def toggle(connected):
            pci(connected)
            return wait_connector(guest, connected, original)

        method = 'virtio-gpu-pci'
        cycles = 3
    for _ in range(cycles):
        assert toggle(False), f'{method} did not disconnect the DRM connector'
        name = toggle(True)
        assert name, f'{method} did not reconnect the DRM connector'
    output = guest.request('snapshot')['outputs'][name]
    mode, = [listed for listed in output['modes'] if listed['preferred']]
    set_mode(guest, name, None)
    verify_mode(guest, name, None)
    set_mode(guest, name, mode)
    verify_mode(guest, name, mode)
    return dict(hotplug=method)


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
    return dict(status='passed', **hotplug(guest))


def custom(guest, ready):
    modes = ready['outputs'][PRIMARY]['modes']
    mode = dict(width=1022, height=766)
    assert mode_size(mode) not in {mode_size(listed) for listed in modes}
    transitions = []
    for operation, requested in (('set-custom-mode', mode), ('disable-output', None), ('reenable-custom-mode', mode)):
        try:
            set_mode(guest, PRIMARY, requested, custom=True)
            verify_mode(guest, PRIMARY, requested)
        except (GuestFailure, AssertionError, OSError, EOFError) as error:
            log = str(error)
            try:
                log += '\n' + guest.request('diagnostics')['session_log']
            except (OSError, EOFError, GuestFailure):
                pass
            expected = any('head_send_state' in line and 'Assertion' in line for line in log.splitlines())
            status = 'compositor-assertion' if expected else 'unverified'
            transitions.append(dict(operation=operation, status=status))
            return dict(status=status, operation=operation, detail=str(error)[-2000:], transitions=transitions)
        transitions.append(dict(operation=operation, status='passed'))
    return dict(status='passed', transitions=transitions)


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
            phase = 'boot'
            try:
                with boot(disk, work / name, evidence / name) as guest:
                    phase = 'readiness'
                    ready = guest.request('ready', state=state)
                    phase = 'operations'
                    results[name] = scenario(guest, ready)
            except Exception as error:
                results[name] = dict(status='failed', phase=phase, detail=str(error)[-4000:])
            print(f'DESKFLOW_VM {name} {json.dumps(results[name])}', flush=True)
    passed = all(results[f'regular-{state}']['status'] == 'passed' for state in STATES)
    incomplete = {name: result for name, result in results.items()
                  if name.startswith('custom-') and result['status'] not in ('passed', 'compositor-assertion')}
    if incomplete:
        print(f'DESKFLOW_CUSTOM_EVIDENCE_INCOMPLETE {json.dumps(incomplete)}', flush=True)
    (evidence / 'result.json').write_text(json.dumps(
        dict(gate='passed' if passed else 'failed', boots=results, custom_incomplete=incomplete), indent=2) + '\n')
    if not passed:
        raise SystemExit('DESKFLOW_OUTPUT_GATE_FAILED')
    print('DESKFLOW_OUTPUT_GATE_PASSED', flush=True)


if __name__ == '__main__':
    main()
