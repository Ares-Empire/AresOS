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


def deployment_processes(root=pathlib.Path('/proc')):
    processes = []
    for process in sorted(root.iterdir(), key=lambda p: int(p.name) if p.name.isdigit() else -1):
        if not process.name.isdigit():
            continue
        try:
            executable = str((process / 'exe').readlink())
            if pathlib.Path(executable.removesuffix(' (deleted)')).name not in ('bootc', 'rpm-ostree'):
                continue
            cmdline = (process / 'cmdline').read_bytes().decode().rstrip('\0').split('\0')
            cgroup = (process / 'cgroup').read_text()
        except (FileNotFoundError, ProcessLookupError):
            # A process which exited while being read cannot keep a client active.
            continue
        paths = [line.split(':', 2)[2] for line in cgroup.splitlines()]
        daemon = any(path == '/system.slice/rpm-ostreed.service' or
                     path.startswith('/system.slice/rpm-ostreed.service/') for path in paths)
        processes.append(dict(pid=int(process.name), exe=executable, cmdline=cmdline,
                              cgroup=cgroup, excluded_as_daemon=daemon))
    return processes


def pause_stock():
    decision = dict(units=[], transaction=None, transaction_observed=False, processes=[],
                    units_inactive=False, transaction_idle=False, clients_idle=False,
                    cancel=dict(ran=False, transaction=None))
    receipt = []
    try:
        scopes, receipt = pause_units()
        deadline = time.monotonic() + 300
        while True:
            decision['units'] = []
            decision['units_inactive'] = False
            for index, (command, names) in enumerate(scopes):
                for name in names:
                    decision['units'].append(dict(scope=index, name=name, **unit_state(command, name)))
            decision['units_inactive'] = all(u['ActiveState'] in ('inactive', 'failed') for u in decision['units'])
            status = json.loads(output(['rpm-ostree', 'status', '--json']))
            decision['transaction_observed'] = 'transaction' in status
            assert decision['transaction_observed'], 'Cannot inspect rpm-ostree transaction state'
            decision['transaction'] = status['transaction']
            decision['transaction_idle'] = status['transaction'] is None
            transaction = status['transaction']
            assert transaction is None or (isinstance(transaction, list) and len(transaction) == 3 and
                   all(isinstance(value, str) for value in transaction)), 'Unexpected rpm-ostree transaction shape'
            decision['processes'] = deployment_processes()
            decision['clients_idle'] = not any(not p['excluded_as_daemon'] for p in decision['processes'])
            if decision['units_inactive'] and not decision['transaction_idle'] and not decision['cancel']['ran']:
                remaining = deadline - time.monotonic()
                assert remaining > 0, 'Idle deadline reached before cancellation'
                decision['cancel'] = dict(ran=True, transaction=status['transaction'])
                print('ARESOS_STOCK_CANCEL_REQUEST ' + json.dumps(decision), flush=True)
                result = subprocess.run(['rpm-ostree', 'cancel'], capture_output=True, text=True,
                                        timeout=remaining, check=False)
                decision['cancel'].update(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
                assert result.returncode == 0, 'rpm-ostree cancel failed'
                # Re-read all predicates after cancel, including a transaction that raced completion.
            elif all(decision[key] for key in ('units_inactive', 'transaction_idle', 'clients_idle')):
                print('ARESOS_STOCK_UPDATERS_PAUSED ' + json.dumps(dict(status='passed', units=receipt,
                      transactions_idle=True, service_masks='runtime', timer_disable='persistent', decision=decision)))
                print('Stock OS update timers are paused; leave them paused during the trial.')
                return
            assert time.monotonic() < deadline, 'Updater/deployment transaction did not become idle'
            time.sleep(2)
    except (AssertionError, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print('STOP: stock updaters could not be paused. See EMERGENCY.md / get help.', flush=True)
        failed = [key for key in ('units_inactive', 'transaction_idle', 'clients_idle') if not decision[key]]
        print('ARESOS_STOCK_PAUSE_STOP ' + json.dumps(dict(status='stopped', error=str(error),
              false_predicates=failed, units=receipt, decision=decision)), flush=True)
        raise SystemExit(1) from error


if __name__ == '__main__':
    pause_stock()

PAUSE_STOCK

# Repeat the same pause immediately before inspecting/discarding/pinning.
python3 - <<'PIN_STOCK'
import json
import re
import subprocess

ISO_DIGEST = 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151'
IMAGE = 'ghcr.io/ublue-os/bazzite-nvidia-open'


def require(ok, message):
    if not ok:
        raise SystemExit('STOP: ' + message + '. See EMERGENCY.md / get help; do not reboot, roll back or repin automatically.')


def status():
    value = json.loads(subprocess.check_output(['rpm-ostree', 'status', '--json'], text=True))
    require('transaction' in value and value['transaction'] is None, 'A deployment transaction is active or cannot be inspected')
    deployments = value['deployments']
    booted = [(i, d) for i, d in enumerate(deployments) if d.get('booted')]
    require(len(booted) == 1, 'Expected exactly one booted stock deployment')
    index, stock = booted[0]
    bootc = json.loads(subprocess.check_output(['bootc', 'status', '--json'], text=True))['status']
    require(stock.get('container-image-reference-digest') == ISO_DIGEST
            and bootc['booted']['image']['imageDigest'] == ISO_DIGEST, 'Booted stock differs from the recorded ISO digest')
    require(stock['checksum'] == bootc['booted']['ostree']['checksum'], 'Stock checksum observations disagree')
    require(not bootc.get('rollbackQueued'), 'A rollback is queued')
    return deployments, index, stock, bootc


def upstream(reference):
    return bool(re.fullmatch(r'(?:ostree-image-signed:docker://|ostree-unverified-registry:)?'
                + re.escape(IMAGE) + r'(?::[A-Za-z0-9_.-]+|@sha256:[0-9a-f]{64})', reference))


deployments, index, stock, bootc = status()
require(upstream(stock.get('container-image-reference', '')), 'Booted origin is not the recorded upstream Bazzite')
checksum = stock['checksum']
staged = [d for d in deployments if d.get('staged')]
require(len(staged) <= 1, 'More than one staged deployment')
discarded = None
if staged:
    candidate, = staged
    require(not candidate.get('booted') and not candidate.get('pinned'), 'The staged deployment is booted or pinned')
    reference = candidate.get('container-image-reference', '')
    digest = candidate.get('container-image-reference-digest', '')
    require(upstream(reference), 'Staged origin is not upstream Bazzite')
    require(re.fullmatch(r'sha256:[0-9a-f]{64}', digest) and re.fullmatch(r'[0-9a-f]{64}', candidate['checksum']),
            'Staged deployment identity is incomplete')
    require(bootc.get('staged') and bootc['staged']['image']['imageDigest'] == digest
            and bootc['staged']['ostree']['checksum'] == candidate['checksum'], 'Staged identity observations disagree')
    discarded = dict(reference=reference, digest=digest, checksum=candidate['checksum'], version=candidate.get('version'))
    print('ARESOS_STOCK_DISCARD ' + json.dumps(discarded), flush=True)
    subprocess.run(['rpm-ostree', 'cleanup', '-p'], check=True)
    deployments, index, stock, bootc = status()
    require(stock['checksum'] == checksum, 'Booted checksum changed after pending cleanup')
require(not any(d.get('staged') for d in deployments) and not bootc.get('staged'), 'A staged deployment remains')
subprocess.run(['ostree', 'admin', 'pin', str(index)], check=True)
deployments, index, stock, bootc = status()
require(stock['checksum'] == checksum and stock.get('pinned'), 'Pin did not preserve the booted stock deployment')
require(not any(d.get('staged') for d in deployments) and not bootc.get('staged'), 'A staged deployment appeared while pinning')
print('Pinned booted stock deployment:', checksum)
print('ARESOS_STOCK_PIN_RESULT ' + json.dumps(dict(status='passed', booted_checksum=checksum,
      booted_digest=ISO_DIGEST, staged_discarded=discarded is not None, discarded=discarded,
      pinned=True, no_staged=True)))
PIN_STOCK
