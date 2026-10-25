#!/usr/bin/bash
set -euo pipefail
test "$(id -u)" = 0
python3 - <<'SYSTEM_KEYBOARD'
import json
import shlex
import subprocess


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def identity(state):
    deployments = state['deployments']
    assert len(deployments) == 1, 'STOP: fix the keyboard before pin/switch; expected one stock deployment'
    deployment, = deployments
    assert deployment.get('booted') and not deployment.get('staged'), 'STOP: stock must be booted with nothing staged'
    assert not any(deployment.get(key) for key in ('requested-packages', 'requested-base-removals',
        'requested-base-local-replacements', 'requested-local-packages', 'requested-local-fileoverride-packages',
        'base-removals', 'base-local-replacements', 'packages')), 'STOP: modified stock'
    return {key: deployment[key] for key in ('checksum', 'serial', 'osname', 'booted', 'pinned')}


def arguments(text):
    args = shlex.split(text)
    assert ' '.join(args) == text, 'STOP: unqualified quoted kernel arguments; get help'
    return args


def keymap_argument(arg):
    return arg.split('=', 1)[0] in ('vconsole.keymap', 'rd.vconsole.keymap',
        'vconsole.keymap_toggle', 'rd.vconsole.keymap_toggle', 'vconsole.keymap.toggle', 'rd.vconsole.keymap.toggle')


def fix():
    bootc = json.loads(output('bootc', 'status', '--json'))['status']
    assert not bootc.get('staged') and not bootc.get('rollbackQueued'), 'STOP: pending deployment; get help'
    assert bootc['booted']['image']['imageDigest'] == 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151', 'STOP: unqualified stock digest'
    state = json.loads(output('rpm-ostree', 'status', '--json'))
    assert state.get('transaction') is None, 'STOP: deployment transaction active'
    before = identity(state)
    assert before['checksum'] == bootc['booted']['ostree']['checksum'], 'STOP: inconsistent stock identity'
    original = arguments(output('rpm-ostree', 'kargs'))
    corrected = [arg for arg in original if not keymap_argument(arg)]
    assert corrected and any(arg.startswith('ostree=') for arg in corrected), 'STOP: missing deployment boot target'
    if corrected != original:
        subprocess.run(['ostree', 'admin', 'instutil', 'set-kargs', *corrected], check=True)
        subprocess.run(['rpm-ostree', 'reload'], check=True)
    after = identity(json.loads(output('rpm-ostree', 'status', '--json')))
    assert after == before, 'STOP: deployment identity/count changed during keymap repair'
    observed = arguments(output('rpm-ostree', 'kargs'))
    assert not any(keymap_argument(arg) for arg in observed), 'STOP: keymap override remains'
    # libostree may regenerate the bootlink; no other argument may change.
    strip_bootlink = lambda args: [arg for arg in args if not arg.startswith('ostree=')]
    assert strip_bootlink(observed) == strip_bootlink(corrected), 'STOP: unrelated kernel argument changed'
    print('ARESOS_SYSTEM_KEYBOARD_RESULT ' + json.dumps(dict(status='passed', identity=after,
        deployment_count=1, before_arguments=original, after_arguments=observed,
        reboot_required=corrected != original)))


if __name__ == '__main__':
    fix()
SYSTEM_KEYBOARD
