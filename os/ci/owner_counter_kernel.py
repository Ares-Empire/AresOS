"""Mandatory disposable-runner/guest uinput proof; never run on the owner's host."""
import fcntl
import inspect
import json
import os
import pathlib
import select
import struct
import time
import uuid

from owner_key_counter import released, count_events, compare


def queued(fd):
    assert select.select([fd], [], [], 2)[0], 'STOP: uinput press never reached counting client'


def drain(fd):
    counts = dict(press=0, release=0, repeat=0, syn_dropped=0)
    dropping = False
    deadline = time.monotonic() + 2
    while select.select([fd], [], [], 0)[0]:
        assert time.monotonic() < deadline, 'STOP: uinput event drain deadline'
        dropping = count_events(os.read(fd, 24 * 256), counts, dropping)
    assert not dropping, 'STOP: incomplete uinput frame'
    return counts


def legacy_query(fd):
    # Exact 14zx released() ioctl on the counting client: the negative control.
    pressed = bytearray(96)
    fcntl.ioctl(fd, 0x80604518, pressed, True)
    return not any(pressed)


def exercise(writer, device, query):
    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    def emit(value):
        raw = struct.pack('@llHHi', 0, 0, 1, 194, value) + struct.pack('@llHHi', 0, 0, 0, 0, 0)
        assert os.write(writer, raw) == len(raw), 'STOP: short uinput write'
    try:
        emit(1)
        queued(fd)  # Prove press is queued before the getter; no timing race.
        assert query(device, fd) is False, 'STOP: uinput key state not pressed'
        first = drain(fd)
        emit(0)
        queued(fd)
        last = drain(fd)
        counts = {k: first[k] + last[k] for k in first}
        return dict(counts=counts, press_before_release=first['press'],
                    comparison=compare(dict(complete=True, counts=counts), dict(key_event_count=2)))
    finally: os.close(fd)


def prove():
    name = 'AresOS counter proof ' + uuid.uuid4().hex
    writer = os.open('/dev/uinput', os.O_WRONLY | os.O_NONBLOCK | os.O_NOCTTY)
    created = False
    try:
        fcntl.ioctl(writer, 0x40045564, 1)  # UI_SET_EVBIT EV_KEY
        fcntl.ioctl(writer, 0x40045565, 194)  # UI_SET_KEYBIT KEY_F24 (no text)
        fcntl.ioctl(writer, 0x405c5503, struct.pack('HHHH80sI', 6, 1, 1, 1, name.encode(), 0))
        fcntl.ioctl(writer, 0x5501)  # UI_DEV_CREATE
        created = True
        deadline = time.monotonic() + 10
        while True:
            matches = [p for p in pathlib.Path('/sys/class/input').glob('event[0-9]*')
                       if (p/'device/name').read_text().strip() == name]
            assert len(matches) <= 1, 'STOP: ambiguous uinput proof device'
            if matches and pathlib.Path('/dev/input', matches[0].name).exists(): break
            assert time.monotonic() < deadline, 'STOP: uinput event node deadline'
            time.sleep(.05)
        device = '/dev/input/' + matches[0].name
        old = exercise(writer, device, lambda device, fd: legacy_query(fd))
        assert old['press_before_release'] == 0 and old['counts'] == dict(press=0, release=1, repeat=0, syn_dropped=0), 'STOP: negative control did not reproduce counting-fd flush'
        assert old['comparison']['matches'] is False
        fixed = exercise(writer, device, lambda device, fd: released(device))
        assert fixed['press_before_release'] == 1 and fixed['counts'] == dict(press=1, release=1, repeat=0, syn_dropped=0), 'STOP: separate-open getter lost a queued press'
        assert fixed['comparison']['matches'] is True
        return dict(status='passed', real_kernel=True, kernel=os.uname().release,
                    negative_control=old, fixed=fixed, counts_only=True, skipped=False)
    finally:
        try:
            if created: fcntl.ioctl(writer, 0x5502)  # UI_DEV_DESTROY
        finally: os.close(writer)


def guest_source():
    functions = (released, count_events, compare, queued, drain, legacy_query, exercise, prove)
    return ('import fcntl,json,os,pathlib,select,struct,time,uuid,subprocess\n'
            + ''.join(inspect.getsource(f) for f in functions)
            + "\nsubprocess.run(['modprobe','uinput'],check=True,timeout=10)\nprint(json.dumps(prove()))\n")


def native():
    # Missing uinput defers the mandatory proof, never skips it. The live guest
    # must resolve this receipt before the first physical/hidden typing.
    result = (dict(status='guest-required', reason='native /dev/uinput absent', skipped=False)
              if not pathlib.Path('/dev/uinput').exists() else dict(prove(), location='native'))
    result.update(sha=os.environ['GITHUB_SHA'])
    pathlib.Path('evidence/14-counter-kernel.json').write_text(json.dumps(result, indent=2) + '\n')
    print('COUNTER_KERNEL_PROOF', result['status'], result.get('location', 'guest-before-hidden-input'))


if __name__ == '__main__': native()
