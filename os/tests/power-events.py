"""Exercise real evdev events in the disposable guest, without changing policy."""
import fcntl
import json
import pathlib
import struct
import subprocess
import time


def run(*args, check=True):
    return subprocess.run(args, check=check, capture_output=True, text=True)


def property_value(name):
    return run('busctl', 'get-property', 'org.freedesktop.login1',
               '/org/freedesktop/login1', 'org.freedesktop.login1.Manager', name).stdout.strip()


def journal():
    return run('journalctl', '-b', '-u', 'systemd-logind.service', '--no-pager', '-o', 'cat').stdout


def wait_for(check, description):
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(0.2)
    raise AssertionError(f'logind did not observe {description}:\n{journal()}')


sleep_units = [f'{name}.{kind}' for name in
               ('sleep', 'suspend', 'hibernate', 'hybrid-sleep', 'suspend-then-hibernate')
               for kind in ('target', 'service') if name != 'sleep' or kind == 'target']
# The sleep services use the systemd- prefix, unlike their targets.
sleep_units = [f'systemd-{unit}' if unit.endswith('.service') else unit for unit in sleep_units]


def session_state():
    return {name: run('pgrep', '-u', 'ares', '-x', name).stdout.split() for name in ('labwc', 'foot')}


def sleep_state():
    state = {}
    for unit in sleep_units:
        state[unit] = run('systemctl', 'show', unit, '-p', 'ActiveState',
                          '-p', 'ActiveEnterTimestampMonotonic').stdout
        assert 'ActiveState=inactive\n' in state[unit], state
        assert 'ActiveEnterTimestampMonotonic=0\n' in state[unit], state
    return state


evidence = {'events': [], 'requests': []}
try:
    evidence['policy'] = {name: property_value(name) for name in (
        'HandleLidSwitch', 'HandleLidSwitchExternalPower', 'HandleLidSwitchDocked',
        'HandleSuspendKey', 'HandleHibernateKey', 'HandlePowerKey')}
    for name, value in evidence['policy'].items():
        assert value == ('s "poweroff"' if name == 'HandlePowerKey' else 's "ignore"'), evidence
    evidence['inhibitors'] = run('systemd-inhibit', '--list', '--no-pager').stdout
    assert not any(name in evidence['inhibitors'] for name in
                   ('handle-lid-switch', 'handle-suspend-key', 'handle-hibernate-key')), evidence
    before_session = session_state()
    before_sleep = sleep_state()
    evidence['session_before'] = before_session
    evidence['sleep_before'] = before_sleep

    run('modprobe', 'uinput')
    with open('/dev/uinput', 'wb', buffering=0) as device:
        # Linux uinput v5 ABI on this x86_64 guest; no additional RPM is needed.
        # https://docs.kernel.org/input/uinput.html
        fcntl.ioctl(device, 0x40045564, 1)   # UI_SET_EVBIT(EV_KEY)
        fcntl.ioctl(device, 0x40045565, 142) # UI_SET_KEYBIT(KEY_SLEEP)
        fcntl.ioctl(device, 0x40045565, 205) # UI_SET_KEYBIT(KEY_SUSPEND)
        fcntl.ioctl(device, 0x40045564, 5)   # UI_SET_EVBIT(EV_SW)
        fcntl.ioctl(device, 0x4004556d, 0)   # UI_SET_SWBIT(SW_LID)
        fcntl.ioctl(device, 0x405c5503, struct.pack('HHHH80sI', 3, 0x1234, 1, 1,
                                                b'AresOS CI power events', 0))
        fcntl.ioctl(device, 0x5501)         # UI_DEV_CREATE
        run('udevadm', 'settle')
        wait_for(lambda: '(AresOS CI power events)' in journal(), 'the virtual input device')

        def emit(kind, code, value):
            device.write(struct.pack('llHHi', 0, 0, kind, code, value))
            device.write(struct.pack('llHHi', 0, 0, 0, 0, 0)) # SYN_REPORT

        for closed in (True, False):
            emit(5, 0, int(closed))
            wait_for(lambda: property_value('LidClosed') == f'b {str(closed).lower()}',
                     f'lid {"closed" if closed else "opened"}')
            time.sleep(3)
            assert session_state() == before_session
            assert sleep_state() == before_sleep
            evidence['events'].append(f'lid {"closed" if closed else "opened"}: observed and ignored')

        for code, name in ((142, 'Suspend'), (205, 'Hibernate')):
            old_count = journal().count(f'{name} key pressed short.')
            emit(1, code, 1)
            emit(1, code, 0)
            wait_for(lambda: journal().count(f'{name} key pressed short.') > old_count, f'{name} key')
            time.sleep(3)
            assert session_state() == before_session
            assert sleep_state() == before_sleep
            evidence['events'].append(f'{name} key: observed and ignored')
        fcntl.ioctl(device, 0x5502)         # UI_DEV_DESTROY

    for method in ('Suspend', 'Hibernate', 'HybridSleep', 'SuspendThenHibernate'):
        result = run('busctl', 'call', 'org.freedesktop.login1', '/org/freedesktop/login1',
                     'org.freedesktop.login1.Manager', method, 'b', 'false', check=False)
        evidence['requests'].append(dict(method=method, returncode=result.returncode,
                                         stdout=result.stdout, stderr=result.stderr))
        assert result.returncode != 0, evidence
        assert 'disabled' in result.stderr.lower(), evidence
        assert session_state() == before_session
        assert sleep_state() == before_sleep
    evidence['session_after'] = session_state()
    evidence['sleep_after'] = sleep_state()
    evidence['passed'] = True
    print('ARESOS_POWER_EVENTS_PASSED: lid and sleep keys observed/ignored; direct sleep requests rejected')
finally:
    evidence['logind_journal'] = journal()
    pathlib.Path('/run/aresos-power-events.json').write_text(json.dumps(evidence, indent=2) + '\n')
