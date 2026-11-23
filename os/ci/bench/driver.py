"""Run one hosted bench script with a private QEMU disk and virtio connection."""
import http.client
import json
import os
import pathlib
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from channel import Frames, frame
from qmp import QMP

from fake_net import NAMESPACE_ENV, REPLY, Stubs, listening, offline_namespace
from network import Level, NIC, STUB_PORT, qemu_nic, require_loopback
from script import dispatch, SHA

WORK = pathlib.Path('vm-work').resolve()
EVIDENCE = pathlib.Path('evidence/bench').resolve()
BOOT_ID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
SESSION_FACTS = {'greetd_running', 'initial_login_attempted', 'compositor_running', 'seat_session',
                 'active_greetd_session', 'compositor_in_session'}
QEMU_ENV = {'PATH': os.defpath, 'LC_ALL': 'C'}
DISPATCH_ENV = ('GITHUB_ACTIONS', 'GITHUB_EVENT_NAME', 'RUNNER_ENVIRONMENT', 'GITHUB_JOB',
                'GITHUB_REF_TYPE', 'GITHUB_REF_NAME', 'GITHUB_EVENT_PATH', 'GITHUB_SHA', 'BENCH_SCRIPT')


class Failed(Exception):
    """The VM ran and an assertion failed."""


class Guest:
    def __init__(self, work, disk, network=Level.NONE, outside_port=None):
        self.work = work
        self.network = network
        self.outside_port = outside_port
        self.stubs = Stubs(work, STUB_PORT) if network == Level.FAKE else None
        self.overlay = work / 'guest.qcow2'
        self.vars = work / 'vars.fd'
        self.qemu = self.checks = self.qmp_socket = None
        self.sequence = 0
        self.accel = 'kvm' if os.access('/dev/kvm', os.R_OK | os.W_OK) else 'tcg'
        subprocess.run(['qemu-img', 'create', '-f', 'qcow2', '-F', 'raw', '-b', str(disk), str(self.overlay)],
                       check=True, env=QEMU_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        shutil.copyfile('/usr/share/OVMF/OVMF_VARS_4M.fd', self.vars)

    def boot(self):
        qmp, checks = self.work / 'qmp.sock', self.work / 'bench.sock'
        for path in (qmp, checks):
            path.unlink(missing_ok=True)
        accel = ['-accel', 'kvm', '-cpu', 'host'] if self.accel == 'kvm' else ['-accel', 'tcg,thread=multi', '-cpu', 'max']
        if self.stubs:
            self.stubs.up()
        self.qemu = subprocess.Popen([
            'qemu-system-x86_64', '-machine', 'q35', *accel,
            '-smp', str(min(4, len(os.sched_getaffinity(0)))), '-m', '6144',
            '-drive', 'if=pflash,format=raw,readonly=on,file=/usr/share/OVMF/OVMF_CODE_4M.fd',
            '-drive', f'if=pflash,format=raw,file={self.vars}',
            '-drive', f'file={self.overlay},format=qcow2,if=virtio',
            '-device', 'virtio-vga', '-device', 'qemu-xhci', '-device', 'usb-kbd', '-device', 'usb-tablet',
            '-display', 'none', *qemu_nic(self.network), '-serial', 'null',
            '-qmp', f'unix:{qmp},server=on,wait=off',
            '-device', 'virtio-serial-pci', '-chardev', f'socket,id=bench,path={checks},server=on,wait=off',
            '-device', 'virtserialport,chardev=bench,name=org.aresos.bench', '-no-reboot',
        ], env=QEMU_ENV, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.qmp_socket = self.connect(qmp)
        self.monitor = QMP(self.qmp_socket)
        self.monitor.command('qmp_capabilities')
        self.checks = self.connect(checks)
        self.checks.settimeout(240)
        self.incoming = Frames(self.checks.recv)
        if self.incoming.receive() != {'ready': True, 'protocol': 1}:
            raise ValueError('Invalid bench handshake')
        self.checks.settimeout(40)
        if self.stubs and self.call('setup_fake', certificate=self.stubs.ca.read_text()) != {'configured': True}:
            raise ValueError('Guest fake network setup failed')

    def connect(self, path):
        deadline = time.monotonic() + 30
        while self.qemu.poll() is None and time.monotonic() < deadline:
            sock = socket.socket(socket.AF_UNIX)
            try:
                sock.connect(str(path))
                return sock
            except OSError:
                sock.close()
                time.sleep(0.2)
        raise TimeoutError('VM socket unavailable')

    def call(self, action, **fields):
        self.sequence += 1
        self.checks.sendall(frame(dict(action=action, id=self.sequence, **fields)))
        reply = self.incoming.receive()
        if reply.pop('id', None) != self.sequence or 'error' in reply:
            raise ValueError('Invalid guest reply')
        return reply

    def status(self, record):
        status = self.call('status')
        boot, revision = status.get('boot_id'), status.get('revision')
        if not isinstance(boot, str) or not BOOT_ID.fullmatch(boot):
            raise ValueError('Invalid guest boot ID')
        if revision != record['head_sha']:
            raise Failed('guest revision differs from dispatched head')
        no_nic = self.network == Level.NONE
        if status.get('no_nic') is not no_nic:
            raise Failed('guest NIC does not match the requested network level')
        if type(status.get('active_session')) is not bool:
            raise ValueError('Invalid session status')
        session = status.get('session')
        if (not isinstance(session, dict) or session.keys() != SESSION_FACTS
                or not all(type(value) is bool for value in session.values())):
            raise ValueError('Invalid session facts')
        record['boots'][-1].update(boot_id=boot, revision=revision, no_nic=no_nic,
                                  active_session=status['active_session'], session=session)
        return record['boots'][-1]

    def link(self, state):
        if not self.stubs:
            raise ValueError('Guest has no fake network')
        self.monitor.command('set_link', {'name': NIC, 'up': state == 'up'})
        facts = self.call('probe_fake', state=state, outside_port=self.outside_port)
        want = dict(carrier=True, stub=state == 'up', stub_unreachable=state == 'down', outside_unreachable=True)
        if facts != want:
            raise Failed('guest fake network behavior differed from the fixture')
        return dict(state=state, **facts)

    def screenshot(self, path):
        from PIL import Image

        ppm = self.work / 'screen.ppm'
        self.monitor.command('screendump', {'filename': str(ppm)})
        with Image.open(ppm) as image:
            image.save(path)
        ppm.unlink()

    def reboot(self):
        if self.call('reboot').get('scheduled') is not True:
            raise Failed('guest reboot request failed')
        if self.qemu.wait(timeout=150) != 0:
            raise Failed('guest did not shut down for reboot')
        self.close()
        self.boot()

    def close(self):
        for connection in (self.checks, self.qmp_socket):
            if connection:
                try:
                    connection.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                connection.close()
        self.checks = self.qmp_socket = None
        if self.qemu and self.qemu.poll() is None:
            self.qemu.terminate()
            try:
                self.qemu.wait(timeout=15)
            except subprocess.TimeoutExpired:
                self.qemu.kill()
                self.qemu.wait()
        if self.stubs:
            self.stubs.down()


def run_step(guest, step, number, record):
    kind = step['kind']
    if kind == 'status':
        return dict(status=guest.status(record).copy())
    if kind == 'net':
        return guest.link(step['state'])
    if kind in ('wait', 'expect'):
        check = step['for']
        deadline = time.monotonic() + (150 if kind == 'wait' else 35)
        while True:
            if check == 'active_session':
                passed = guest.status(record)['active_session']
            else:
                passed = guest.call('health').get('healthy') is True
            if passed:
                return dict(check=check)
            if time.monotonic() >= deadline:
                if check == 'active_session':
                    try:
                        reply = guest.call('journal')
                        (EVIDENCE / f'{number:03d}.journal.txt').write_text(reply['output'], encoding='utf-8')
                        guest.screenshot(EVIDENCE / f'{number:03d}.png')
                    except Exception:
                        pass  # Log the original failed assertion even when diagnostics are unavailable.
                raise Failed(f'{check} did not pass')
            time.sleep(1)
    if kind == 'shot':
        name = f'{number:03d}.png'
        guest.screenshot(EVIDENCE / name)
        return dict(file=name)
    if kind == 'reboot':
        old = guest.status(record)['boot_id']
        guest.reboot()
        record['boots'].append({})
        new = guest.status(record)['boot_id']
        if new == old:
            raise Failed('reboot retained the old boot ID')
        return dict(boot_id=new)
    reply = guest.call(kind, **({'argv': step['argv']} if kind == 'exec' else {}))
    fields = {}
    if kind == 'journal':
        name = f'{number:03d}.journal.txt'
        (EVIDENCE / name).write_text(reply['output'], encoding='utf-8')
        fields['file'] = name
    if reply['code'] != 0:
        raise Failed(f'{kind} returned a failure')
    return fields


def run_guest(steps, record, outside_port=None):
    disk_root = WORK / 'output'
    disks = list(disk_root.rglob('disk.raw'))
    if (len(disks) != 1 or not disks[0].is_relative_to(disk_root) or disks[0].resolve() != disks[0]
            or not stat.S_ISREG(disks[0].lstat().st_mode)):
        raise ValueError('Bench requires one regular disk under its output directory')
    revision = (WORK / 'bench-revision').read_text().strip()
    if not SHA.fullmatch(revision) or revision != record['head_sha']:
        raise ValueError('Image label does not match dispatched head')
    EVIDENCE.mkdir()
    results = EVIDENCE / 'results.txt'
    record.update(image_revision=revision, boots=[{}], outcome='unusable')
    started = time.monotonic()
    try:
        # Keep socket paths short even when Actions uses a long checkout path.
        with tempfile.TemporaryDirectory(prefix='aresos-bench-') as directory:
            guest = Guest(pathlib.Path(directory), disks[0], record['network'], outside_port)
            record['acceleration'] = guest.accel
            try:
                guest.boot()
                guest.status(record)
                with results.open('w', encoding='utf-8') as log:
                    for number, step in enumerate(steps, 1):
                        kind = step['kind']
                        try:
                            fields = run_step(guest, step, number, record)
                            line = f'PASS {number:03d} {kind}'
                        except Failed as error:
                            line = f'FAIL {number:03d} {kind} ({error})'
                            fields = {'reason': str(error)}
                        except Exception:
                            line = f'UNUSABLE {number:03d} {kind}'
                            fields = {'reason': 'VM operation failed'}
                        print(line, file=log, flush=True)
                        passed = line.startswith('PASS ')
                        print(json.dumps(dict(n=number, kind=kind, ok=passed, **fields)), flush=True)
                        if not passed:
                            record['outcome'] = 'failed' if line.startswith('FAIL ') else 'unusable'
                            return 1 if record['outcome'] == 'failed' else 2
                record['outcome'] = 'passed'
                return 0
            finally:
                guest.close()
    finally:
        record['vm_seconds'] = round(time.monotonic() - started, 1)
        (EVIDENCE / 'run.json').write_text(json.dumps(record, indent=2) + '\n')


def main():
    steps, record = dispatch()
    network = record['network']
    if network == Level.INTERNET and not sys.argv[1:]:
        return run_guest(steps, record)
    if sys.argv[1:2] == ['--offline'] and len(sys.argv) == 3:
        if network not in (Level.FAKE, Level.NONE):
            raise ValueError('Hosted offline launcher received an internet script')
        require_loopback()
        return run_guest(steps, record, int(sys.argv[2]))
    if sys.argv[1:]:
        raise ValueError('Unexpected bench driver arguments')
    with listening() as outside:
        with_code = http.client.HTTPConnection('127.0.0.1', outside.server_port, timeout=2)
        try:
            with_code.request('GET', '/')
            reply = with_code.getresponse()
            if reply.status != 200 or reply.read(64) != REPLY:
                raise ValueError('Outside bench fixture failed its positive control')
        finally:
            with_code.close()
        command = offline_namespace([sys.executable, '-B', __file__, '--offline', str(outside.server_port)])
        runtime_env = dict(NAMESPACE_ENV, **{key: os.environ[key] for key in DISPATCH_ENV})
        status = subprocess.run(command, env=runtime_env, check=False).returncode
        if status == 0:
            if outside.connections != 1:
                print('FAIL traffic reached the outside bench fixture', file=sys.stderr)
                path = EVIDENCE / 'run.json'
                result = json.loads(path.read_text())
                result['outcome'] = 'failed'
                path.write_text(json.dumps(result, indent=2) + '\n')
                return 1
            print('PASS outside listener positive control and no guest traffic')
        return status if status in (0, 1, 2) else 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        print('Bench VM unusable during setup or cleanup', file=sys.stderr)
        sys.exit(2)
