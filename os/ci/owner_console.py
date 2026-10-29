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


def process_snapshot(proc):
    rows = {}
    for path in proc.glob('[0-9]*/stat'):
        try:
            raw = path.read_text()
            pid = int(path.parent.name)
            fields = raw.rsplit(')', 1)[1].split()
            args = path.with_name('cmdline').read_bytes().removesuffix(b'\0').split(b'\0')
            # A reused PID or a process changing its group during the read is
            # never an idle proof. Unrelated processes may disappear normally.
            if path.read_text() != raw or len(fields) < 20:
                continue
            rows[pid] = dict(pid=pid, comm=raw.split('(', 1)[1].rsplit(')', 1)[0],
                state=fields[0], ppid=int(fields[1]), pgrp=int(fields[2]),
                session=int(fields[3]), tty=int(fields[4]) & 0xffffffff,
                tpgid=int(fields[5]), start=fields[19], argv=args)
        except (OSError, ValueError, IndexError):
            continue
    return rows


def foreground_observation(device, proc=pathlib.Path('/proc')):
    rows = process_snapshot(proc)
    groups = {r['tpgid'] for r in rows.values() if r['tty'] == device and r['tpgid'] > 0}
    chain = []
    def result(ready, reason):
        # Only these exact public harness argv are exportable. Unknown argv,
        # including anything provided after a hidden prompt, are redacted.
        diagnostic = []
        for r in chain:
            public = interactive_shell(r['argv']) or r['argv'] == [b'sudo', b'-i']
            diagnostic.append(dict(pid=r['pid'], comm=r['comm'],
                argv=[a.decode('utf-8', 'replace') for a in r['argv']] if public else ['[redacted]'],
                argv_redacted=not public, ppid=r['ppid'], pgrp=r['pgrp'],
                session=r['session'], tty=r['tty'], tpgid=r['tpgid']))
        return dict(ready=ready, reason=reason, foreground_chain=diagnostic)
    if len(groups) != 1:
        chain.extend(r for r in rows.values() if r['tty'] == device)
        return result(False, 'No unique physical foreground process group')
    group, = groups
    leader = rows.get(group)
    if leader is None or leader['pgrp'] != group or leader['tty'] != device:
        chain.extend(r for r in rows.values() if r['tty'] == device)
        return result(False, 'Broken physical foreground leader')
    chain.append(leader)
    # Retain the original bare interactive Bash rule.
    if interactive_shell(leader['argv']):
        return result(True, 'plain interactive bash')
    children = lambda pid: [r for r in rows.values() if r['ppid'] == pid]
    def descend(row, seen):
        if row['pid'] in seen:
            return
        seen.add(row['pid'])
        for child in sorted(children(row['pid']), key=lambda r: r['pid']):
            chain.append(child)
            descend(child, seen)
    descend(leader, set())
    def sudo(row):
        return row['comm'] == 'sudo' and row['argv'] == [b'sudo', b'-i'] and row['state'] in ('R', 'S')
    if not sudo(leader):
        return result(False, 'Unknown physical foreground command')
    if len([r for r in rows.values() if r['pgrp'] == group]) != 1:
        return result(False, 'Multiple physical foreground candidates')
    monitors = children(group)
    if len(monitors) != 1 or not sudo(monitors[0]):
        return result(False, 'No unique sudo monitor')
    monitor = monitors[0]
    shells = children(monitor['pid'])
    if len(shells) != 1:
        return result(False, 'No unique sudo command')
    shell = shells[0]
    if not interactive_shell(shell['argv']) or shell['comm'] != 'bash' or shell['state'] not in ('R', 'S'):
        return result(False, 'Sudo command is not interactive bash')
    major = (shell['tty'] >> 8) & 0xfff
    if not (136 <= major <= 143) or shell['tty'] == device:
        return result(False, 'Sudo shell is not on a pts')
    if (monitor['session'] != monitor['pid'] or monitor['pgrp'] != monitor['pid'] or
            shell['session'] != monitor['session'] or monitor['tty'] != shell['tty'] or
            shell['pgrp'] != shell['pid'] or shell['tpgid'] != shell['pgrp'] or
            monitor['tpgid'] != shell['pgrp']):
        return result(False, 'Sudo pts is not foreground interactive bash')
    if children(shell['pid']) or len([r for r in rows.values() if r['pgrp'] == shell['pgrp']]) != 1:
        return result(False, 'Sudo bash has child work or multiple foreground candidates')
    # Re-read the selected chain before granting authority; races fail closed.
    again = process_snapshot(proc)
    if rows != again:
        # Unrelated process churn is harmless; changes involving this relay or
        # new children/group members are not.
        relevant = {r['pid'] for r in chain}
        for snapshot in (rows, again):
            relevant.update(r['pid'] for r in snapshot.values() if r['ppid'] in relevant or r['pgrp'] in (group, monitor['pgrp'], shell['pgrp']))
        if any(rows.get(pid) != again.get(pid) for pid in relevant):
            return result(False, 'Foreground relay changed while observed')
    return result(True, 'sudo -i monitor to foreground pts interactive bash')


def foreground_is_shell(fd, diagnostics=None):
    # tcgetpgrp rejects a tty in another session. /proc exposes the same
    # foreground group without acquiring or changing that terminal.
    dev = os.fstat(fd).st_rdev
    minor = os.minor(dev)
    device = (minor & 255) | (os.major(dev) << 8) | ((minor & ~255) << 12)
    value = foreground_observation(device)
    if diagnostics is not None:
        diagnostics.clear()
        diagnostics.update(value)
    if value['reason'] in ('No unique physical foreground process group', 'Broken physical foreground leader'):
        raise OSError(value['reason'])
    return value['ready']


def foreground_source():
    return ''.join(inspect.getsource(function) for function in
        (interactive_shell, process_snapshot, foreground_observation, foreground_is_shell))


def screen(data):
    assert len(data) >= 4, 'Truncated VCSA header'
    rows, cols, x, y = data[:4]
    assert rows and cols and x < cols and y < rows, 'Invalid VCSA geometry'
    assert len(data) == 4 + rows * cols * 2, 'Truncated VCSA cells'
    text = bytes(data[4::2]).decode('latin1')
    lines = [text[i:i + cols].rstrip() for i in range(0, len(text), cols)]
    return '\n'.join(lines), text[y * cols:y * cols + x].rstrip()


def source(tty, predicate, timeout, health=None):
    assert tty in ('tty3', 'tty4')
    import owner_xhci
    return owner_xhci.guard(('import base64,json,pathlib,re,time\n' + inspect.getsource(screen) +
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
        'print(json.dumps(dict(ready=ready,raw=base64.b64encode(data).decode())))\n'), health)


def hidden_idle_source(tty, timeout, health=None):
    """Only exact public shell/sudo argv may be exported on refusal.

    Readline may turn ECHO off at an idle prompt. A foreground owner/Python
    command never grants Enter authority, even if output ends with '#'.
    """
    assert tty in ('tty3', 'tty4')
    import owner_xhci
    return owner_xhci.guard(('import base64,json,os,pathlib,time\n' + foreground_source()) + '''
ready=False
observation={}
deadline=time.monotonic()+@TIMEOUT@
while time.monotonic()<deadline:
    try:
        fd=os.open('/dev/@TTY@',os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
        try:
            shell=foreground_is_shell(fd,observation)
        finally: os.close(fd)
        ready=shell
        if ready: break
    except OSError: pass
    time.sleep(.2)
raw=pathlib.Path('/dev/vcsa@NUMBER@').read_bytes() if not ready else b''
print(json.dumps(dict(ready=ready,completion_uses_echo=False,foreground_shell=ready,observation=observation,raw=base64.b64encode(raw).decode())))
'''.replace('@TTY@', tty).replace('@NUMBER@', tty[3:]).replace('@TIMEOUT@', repr(timeout)), health)


def wait(sample, timeout, retain, resync=None, record=None, observe=None):
    """Every Enter needs a fresh idle observation, within the original deadline.

    VCSA samples never grant authority. Each phase keeps the original three
    stable samples; no more than two physical Enters may redraw a shell prompt.
    """
    assert resync is None or (observe is not None and record is not None)
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
                after_cursor_line=None, enter_sent=False, observer=None)
            record(dict(pending))
            remaining = deadline - time.monotonic()
            assert remaining > 0, 'Physical console readiness deadline'
            answer = observe(remaining / (phases - phase - 1), attempts)
            pending['observer'] = {key: value for key, value in answer.items() if key != 'raw'}
            if not answer['ready'] and answer.get('raw'):
                _, after = screen(base64.b64decode(answer['raw'], validate=True))
                pending.update(after_cursor_line=after, ready=False,
                    after_time=datetime.datetime.now(datetime.timezone.utc).isoformat())
            record(dict(pending))
            assert type(answer['ready']) is bool, 'Invalid physical idle observation'
            assert answer['ready'], 'Physical console idle observer refused'
            resync()
            pending['enter_sent'] = True
            record(dict(pending))
    raise AssertionError('Physical console readiness deadline')
