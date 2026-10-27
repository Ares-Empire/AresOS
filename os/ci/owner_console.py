"""Read-only VCSA waits and bounded, owner-style prompt resynchronization."""
import base64
import datetime
import inspect
import os
import pathlib
import re
import time


def interactive_shell(args):
    return (bool(args) and args[0] in (b'-bash', b'bash', b'/bin/bash', b'/usr/bin/bash')
        and all(arg in (b'-i', b'-l', b'--login', b'--noprofile', b'--norc') for arg in args[1:]))


def foreground_is_shell(fd):
    # tcgetpgrp rejects a tty belonging to another session, including our
    # serial observer reading tty3. /proc stat exposes the same foreground
    # group without changing or acquiring that controlling terminal.
    dev = os.fstat(fd).st_rdev
    minor = os.minor(dev)
    device = (minor & 255) | (os.major(dev) << 8) | ((minor & ~255) << 12)
    groups = set()
    for path in pathlib.Path('/proc').glob('[0-9]*/stat'):
        try:
            fields = path.read_text().rsplit(')', 1)[1].split()
            if len(fields) >= 6 and int(fields[4]) & 0xffffffff == device & 0xffffffff and int(fields[5]) > 0:
                groups.add(int(fields[5]))
        except (OSError, ValueError, IndexError):
            continue
    if len(groups) != 1:
        raise OSError('No unique physical foreground process group')
    group, = groups
    args = [part for part in pathlib.Path('/proc/' + str(group) + '/cmdline').read_bytes().split(b'\0') if part]
    return interactive_shell(args)


def screen(data):
    assert len(data) >= 4, 'Truncated VCSA header'
    rows, cols, x, y = data[:4]
    assert rows and cols and x < cols and y < rows, 'Invalid VCSA geometry'
    assert len(data) == 4 + rows * cols * 2, 'Truncated VCSA cells'
    text = bytes(data[4::2]).decode('latin1')
    lines = [text[i:i + cols].rstrip() for i in range(0, len(text), cols)]
    return '\n'.join(lines), text[y * cols:y * cols + x].rstrip()


def source(tty, predicate, timeout):
    assert tty in ('tty3', 'tty4')
    return ('import base64,json,pathlib,re,time\n' + inspect.getsource(screen) +
        '\ndata=None\nstable=0\nready=False\n' +
        'deadline=time.monotonic()+' + repr(timeout) + '\n' +
        'while time.monotonic()<deadline:\n' +
        '    data=pathlib.Path(' + repr('/dev/vcsa' + tty[3:]) + ').read_bytes()\n' +
        '    full,line=screen(data)\n' +
        '    if (' + predicate + '):\n' +
        '        stable+=1\n' +
        '        if stable>=3:\n            ready=True\n            break\n' +
        '    else: stable=0\n    time.sleep(0.2)\n' +
        'assert data is not None, "No VCSA sample"\n' +
        'print(json.dumps(dict(ready=ready,raw=base64.b64encode(data).decode())))\n')


def hidden_idle_source(tty, timeout):
    """No command-line text is returned or logged; only an idle-shell fact.

    Readline may turn ECHO off at an idle prompt. A foreground owner/Python
    command never grants Enter authority, even if output ends with '#'.
    """
    assert tty in ('tty3', 'tty4')
    return ('import base64,json,os,pathlib,termios,time\n' + inspect.getsource(interactive_shell)
        + inspect.getsource(foreground_is_shell)) + '''
ready=False
echo=False
deadline=time.monotonic()+@TIMEOUT@
while time.monotonic()<deadline:
    try:
        fd=os.open('/dev/@TTY@',os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            echo=bool(termios.tcgetattr(fd)[3]&termios.ECHO)
            shell=foreground_is_shell(fd)
        finally: os.close(fd)
        ready=shell
        if ready: break
    except (OSError,termios.error): pass
    time.sleep(.2)
raw=pathlib.Path('/dev/vcsa@NUMBER@').read_bytes() if not ready else b''
print(json.dumps(dict(ready=ready,echo_enabled=echo,foreground_shell=ready,raw=base64.b64encode(raw).decode())))
'''.replace('@TTY@', tty).replace('@NUMBER@', tty[3:]).replace('@TIMEOUT@', repr(timeout))


def wait(sample, timeout, retain, resync=None, record=None):
    """Only the caller can grant idle authority; samples never grant it.

    Empty Enter resyncs share that one grant within this wait. Ordinary typing
    invalidates it in the caller. Each phase keeps the original three stable
    samples and shares the original overall timeout, rather than tripling it.
    """
    deadline = time.monotonic() + timeout
    phases = 3 if resync is not None else 1
    pending = None
    attempts = 0
    for phase in range(phases):
        remaining = deadline - time.monotonic()
        assert remaining > 0, 'Physical console readiness deadline'
        value = sample(remaining / (phases - phase))
        assert type(value['ready']) is bool
        raw = base64.b64decode(value['raw'], validate=True)
        _, line = screen(raw)
        if pending is not None:
            pending.update(after_cursor_line=line, after_time=datetime.datetime.now(
                datetime.timezone.utc).isoformat(), ready=value['ready'])
            record(dict(pending))
            pending = None
        if value['ready']:
            return
        retain(phase + 1, raw)
        if phase + 1 < phases and not re.search(r'[$#]$', line):
            attempts += 1
            pending = dict(attempt=attempts, time=datetime.datetime.now(
                datetime.timezone.utc).isoformat(), before_cursor_line=line,
                after_cursor_line=None, enter_sent=False)
            record(dict(pending))
            resync()
            pending['enter_sent'] = True
            record(dict(pending))
    raise AssertionError('Physical console readiness deadline')
