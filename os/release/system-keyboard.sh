#!/usr/bin/bash
set -euo pipefail
test "$(id -u)" = 0
python3 - <<'SYSTEM_KEYBOARD'
import json
import re
import shlex
import subprocess


def output(*args):
    return subprocess.check_output(args, text=True).strip()


def identity(state):
    deployments = state['deployments']
    assert 1 <= len(deployments) <= 2, 'STOP: expected one or two stock deployments'
    booted = [d for d in deployments if d['booted']]
    assert len(booted) == 1, 'STOP: expected exactly one booted stock deployment'
    stock, = booted
    assert all(type(d['booted']) is bool and type(d['pinned']) is bool for d in deployments), 'STOP: invalid deployment flags'
    # v2026.4 set-kargs targets deployments[0], not a booted-deployment lookup.
    assert deployments[0] is stock, 'STOP: booted stock is not the default; get help'
    reference = stock['container-image-reference']
    assert re.fullmatch(r'(?:ostree-image-signed:docker://|ostree-unverified-registry:)?'
        r'ghcr\.io/ublue-os/bazzite-nvidia-open(?::[A-Za-z0-9_.-]+|@sha256:[0-9a-f]{64})', reference), 'STOP: unqualified stock origin'
    identities = []
    for deployment in deployments:
        assert not deployment.get('staged') and not deployment['pinned'], 'STOP: staged or already pinned stock'
        assert deployment['checksum'] == stock['checksum'] and deployment['osname'] == stock['osname'], 'STOP: mixed stock identities'
        assert deployment['container-image-reference'] == reference, 'STOP: mixed stock origins'
        assert deployment['container-image-reference-digest'] == 'sha256:ed93d2158a1bcba16b226bfb3ab6391446d11466646188c800b982d709435151', 'STOP: unqualified stock digest'
        assert not any(deployment.get(key) for key in ('requested-packages', 'requested-base-removals',
            'requested-base-local-replacements', 'requested-base-remote-replacements', 'requested-local-packages',
            'requested-local-fileoverride-packages', 'base-removals', 'base-local-replacements',
            'base-remote-replacements', 'packages', 'modules', 'requested-modules', 'regenerate-initramfs')) and deployment.get('unlocked', 'none') == 'none', 'STOP: modified stock'
        assert re.fullmatch('[0-9a-f]{64}', deployment['checksum']) and type(deployment['serial']) is int and deployment['serial'] >= 0, 'STOP: incomplete stock identity'
        identities.append({key: deployment[key] for key in ('checksum', 'serial', 'osname', 'booted', 'pinned')})
    assert len({(d['checksum'], d['serial'], d['osname']) for d in identities}) == len(identities), 'STOP: duplicate deployment identity'
    return identities


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
    assert 'transaction' in state and state['transaction'] is None, 'STOP: deployment transaction active or unknown'
    before = identity(state)
    assert before[0]['checksum'] == bootc['booted']['ostree']['checksum'] and before[0]['serial'] == bootc['booted']['ostree']['deploySerial'] and before[0]['osname'] == bootc['booted']['ostree']['stateroot'], 'STOP: inconsistent stock identity'
    assert not bootc['booted']['pinned'], 'STOP: bootc stock already pinned'
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
        deployment_count=len(after), before_arguments=original, after_arguments=observed,
        reboot_required=corrected != original)))


if __name__ == '__main__':
    fix()
SYSTEM_KEYBOARD
