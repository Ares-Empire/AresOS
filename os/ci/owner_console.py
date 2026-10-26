"""Read-only VCSA waits and bounded, owner-style prompt resynchronization."""
import base64
import datetime
import inspect
import re
import time


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
