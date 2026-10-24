#!/usr/bin/bash
set -euo pipefail
test "$(id -u)" = 0
python3 - <<'PAUSE_STOCK'
import json
import pathlib
import subprocess
import time

# Names and commands come from the frozen image's existing updater audit.
SYSTEM = (
    'uupd.service', 'uupd-manual.service', 'uupd.timer',
    'rpm-ostreed-automatic.service', 'rpm-ostreed-automatic.timer',
    'bootc-fetch-apply-updates.service', 'bootc-fetch-apply-updates.timer',
    'bootc-update.service', 'bootc-update.timer',
    'systemd-sysupdate.service', 'systemd-sysupdate.timer',
    'systemd-sysupdate-reboot.service', 'systemd-sysupdate-reboot.timer',
    'systemd-sysupdated.service', 'dbus-org.freedesktop.sysupdate1.service',
    'dnf-automatic.service', 'dnf-automatic.timer',
    'dnf5-automatic.service', 'dnf5-automatic.timer',
    'dnf5-offline-transaction.service',
    'packagekit.service', 'packagekit-offline-update.service',
)
USER = ('uupd.service', 'uupd.timer')


def output(command):
    return subprocess.check_output(command, text=True, timeout=30)


def unit_files(command):
    return {p[0]: p[1] for line in output([*command, 'list-unit-files']).splitlines()
            if len(p := line.split()) >= 2}


def unit_state(command, name):
    fields = dict(line.split('=', 1) for line in output(
        [*command, 'show', name, '--property=LoadState,ActiveState,SubState']).splitlines() if '=' in line)
    assert fields.get('LoadState') in ('loaded', 'masked'), 'Updater unit could not be inspected: ' + name
    return fields


def pause_units():
    system = ['systemctl', '--no-pager', '--no-legend']
    global_user = ['systemctl', '--global', '--no-pager', '--no-legend']
    scopes = []
    receipt = []
    for command, names, scope in ((system, SYSTEM, 'system'), (global_user, USER, 'user')):
        files = unit_files(command)
        selected = [n for n in names if n in files]
        if scope == 'system':
            assert {'uupd.service', 'uupd.timer'} <= set(selected), 'Pinned stock updater units are missing'
        services = [n for n in selected if n.endswith('.service')]
        timers = [n for n in selected if n.endswith('.timer')]
        for timer in timers:
            assert files[timer] != 'masked-runtime', 'A temporary timer mask cannot prove persistent disablement'
        # Services cannot reactivate while the current maintenance session runs.
        # Timers remain persistently disabled after the runtime masks disappear.
        if services:
            flags = ['--runtime', 'mask'] + (['--now'] if scope == 'system' else [])
            subprocess.run([*command, *flags, *services], check=True)
        disable = [n for n in timers if files[n] != 'masked']
        if disable:
            flags = ['disable'] + (['--now'] if scope == 'system' else [])
            subprocess.run([*command, *flags, *disable], check=True)
        if scope == 'system':
            scopes.append((system, selected))
        elif selected:
            # Stock's first administrator is UID 1000. Inspect any active user
            # managers too, rather than treating a global disable as a stop.
            for bus in pathlib.Path('/run/user').glob('*/bus'):
                uid = bus.parent.name
                if not uid.isdigit():
                    continue
                user = output(['getent', 'passwd', uid]).split(':', 1)[0]
                manager = ['runuser', '-u', user, '--', 'env',
                    'XDG_RUNTIME_DIR=/run/user/' + uid,
                    'DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/' + uid + '/bus',
                    'systemctl', '--user', '--no-pager', '--no-legend']
                subprocess.run([*manager, 'daemon-reload'], check=True)
                subprocess.run([*manager, 'stop', *selected], check=True)
                scopes.append((manager, selected))
        after = unit_files(command)
        assert all(after[n] in ('disabled', 'masked') for n in timers), 'Updater timer is not persistently disabled'
        receipt.append(dict(scope=scope, present=selected, absent=[n for n in names if n not in files],
                            timers={n: after[n] for n in timers}))
    return scopes, receipt


def pause_stock():
    scopes, receipt = pause_units()
    deadline = time.monotonic() + 300
    while True:
        inactive = all(unit_state(command, name)['ActiveState'] in ('inactive', 'failed')
                       for command, names in scopes for name in names)
        status = json.loads(output(['rpm-ostree', 'status', '--json']))
        assert 'transaction' in status, 'Cannot inspect rpm-ostree transaction state'
        clients = [subprocess.run(['pgrep', '-x', name], capture_output=True) for name in ('bootc', 'rpm-ostree')]
        assert all(p.returncode in (0, 1) for p in clients), 'Cannot inspect deployment transactions'
        if inactive and status.get('transaction') is None and all(p.returncode == 1 for p in clients):
            break
        assert time.monotonic() < deadline, 'Updater/deployment transaction did not become idle'
        time.sleep(2)
    print('ARESOS_STOCK_UPDATERS_PAUSED ' + json.dumps(dict(status='passed', units=receipt,
          transactions_idle=True, service_masks='runtime', timer_disable='persistent')))
    print('Stock OS update timers are paused; leave them paused during the trial.')


if __name__ == '__main__':
    try:
        pause_stock()
    except (AssertionError, subprocess.SubprocessError) as error:
        raise SystemExit('STOP: stock updaters could not be paused. See EMERGENCY.md / get help. ' + str(error))
PAUSE_STOCK
