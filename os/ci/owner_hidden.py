"""Read-only hidden-input proof through at most three verified sudo relays.

The physical tty may stay raw throughout sudo -i. Only the actual reader's tty
and a cursor prompt printed after its flush can authorize a secret's one send.
"""
import base64
import inspect
import os
import pathlib
import re
import time

from owner_console import interactive_shell, process_snapshot, screen


def owner_reader(args):
    return dict(kind='owner', argv=['/usr/bin/python3', '-I', '-B', '/var/lib/ares/tools/owner.py', *args])


def sudo_reader(args, next_reader):
    return dict(kind='sudo', argv=['sudo', *args], next=next_reader)


def device_number(fd):
    dev = os.fstat(fd).st_rdev
    minor = os.minor(dev)
    return (minor & 255) | (os.major(dev) << 8) | ((minor & ~255) << 12)


def hidden_snapshot(proc):
    rows = process_snapshot(proc)
    for pid, row in rows.items():
        try:
            row['exe'] = os.readlink(str(proc / str(pid) / 'exe'))
        except OSError:
            row['exe'] = None
    return rows


def reader_matches(row, expected):
    args = [a.encode() for a in expected.get('argv', [])]
    if expected['kind'] == 'login':
        return row['comm'] == 'login' and row['exe'] == '/usr/bin/login'
    if expected['kind'] == 'sudo':
        return (row['comm'] == 'sudo' and row['exe'] == '/usr/bin/sudo'
            and row['argv'] in (args, [b'/usr/bin/sudo', *args[1:]]))
    if expected['kind'] == 'owner':
        return (bool(re.fullmatch(r'/usr/bin/python3(?:\.[0-9]+)?', row['exe'] or ''))
            and bool(re.fullmatch(r'python3(?:\.[0-9]+)?', row['comm'])) and row['argv'] == args)
    assert expected['kind'] == 'shell'
    return row['exe'] == '/usr/bin/bash' and row['comm'] == 'bash' and interactive_shell(row['argv'])


def reader_chain(rows, physical, expected):
    chain, terminals, hops = [], {physical}, 0
    def refuse(reason):
        return dict(valid=False, reason=reason, chain=chain, reader=None)
    groups = {r['tpgid'] for r in rows.values() if r['tty'] == physical and r['tpgid'] > 0}
    if len(groups) != 1:
        chain.extend(r for r in rows.values() if r['tty'] == physical)
        return refuse('No unique physical foreground group')
    pid, = groups
    current = rows.get(pid)
    if not current or current['tty'] != physical or current['pgrp'] != pid:
        return refuse('Broken physical foreground leader')
    def children(row):
        return [r for r in rows.values() if r['ppid'] == row['pid']]
    def shell(row):
        return reader_matches(row, dict(kind='shell'))
    owner = expected if expected['kind'] == 'owner' else expected.get('next')
    allowed_sudo = [dict(kind='sudo', argv=['sudo', '-i'])]
    if expected['kind'] == 'sudo':
        allowed_sudo.append(expected)
    if owner and owner['kind'] == 'owner':
        allowed_sudo.append(dict(kind='sudo', argv=['sudo', '/var/lib/ares/at', *owner['argv'][4:]]))
    for _ in range(16):
        if any(r['pid'] == current['pid'] for r in chain):
            return refuse('Cyclic foreground chain')
        chain.append(current)
        if current['state'] not in ('R', 'S'):
            return refuse('Foreground process is stopped or unavailable')
        if shell(current):
            if current['tpgid'] == current['pgrp'] == current['pid']:
                return dict(valid=True, reason='Foreground interactive bash', chain=chain, reader=current)
            child = rows.get(current['tpgid'])
            if not child or child['ppid'] != current['pid'] or child['tty'] != current['tty'] or child['session'] != current['session']:
                return refuse('Broken shell to foreground command link')
            current = child
            continue
        if current['pgrp'] != current['pid'] or current['tpgid'] != current['pid']:
            return refuse('Reader is not its tty foreground leader')
        if len([r for r in rows.values() if r['tty'] == current['tty'] and r['pgrp'] == current['pgrp']]) != 1:
            return refuse('Multiple foreground candidates')
        sudo = any(reader_matches(current, item) for item in allowed_sudo)
        if not sudo:
            if reader_matches(current, expected) or (owner and reader_matches(current, owner)):
                if any(r['tty'] or expected['kind'] != 'login' for r in children(current)):
                    return refuse('Reader still has child work')
                return dict(valid=True, reason='Expected foreground reader', chain=chain, reader=current)
            return refuse('Unexpected foreground reader')
        # PAM helpers without a controlling tty are not relays or tty readers.
        monitors = [r for r in children(current) if r['tty']]
        if not monitors:
            return dict(valid=True, reason='Foreground sudo before relay', chain=chain, reader=current)
        if len(monitors) != 1:
            return refuse('No unique sudo monitor')
        monitor = monitors[0]
        if (monitor['comm'] != 'sudo' or monitor['exe'] != '/usr/bin/sudo'
                or monitor['argv'] != current['argv'] or monitor['session'] != monitor['pid']
                or monitor['pgrp'] != monitor['pid'] or monitor['tty'] in terminals
                or not 136 <= (monitor['tty'] >> 8) & 0xfff <= 143):
            chain.append(monitor)
            return refuse('Unverified sudo tty transition')
        chain.append(monitor)
        terminals.add(monitor['tty']); hops += 1
        if hops > 3:
            return refuse('More than three sudo relays')
        commands = children(monitor)
        if len(commands) != 1:
            return refuse('No unique sudo command')
        command = commands[0]
        if (command['tty'] != monitor['tty'] or command['session'] != monitor['session']
                or command['tpgid'] != monitor['tpgid'] or command['pgrp'] != command['pid']):
            return refuse('Broken sudo monitor to command link')
        current = command
    return refuse('Foreground chain limit')


def redacted_chain(chain):
    return [dict(pid=r['pid'], comm=r['comm'] if re.fullmatch(r'(?:sudo|bash|login|python3(?:\.[0-9]+)?)', r['comm']) else '[redacted]',
        argv=['[redacted]'], argv_redacted=True, ppid=r['ppid'], pgrp=r['pgrp'],
        session=r['session'], tty=r['tty'], tpgid=r['tpgid']) for r in chain]


def identity(row):
    return {k: row[k] for k in ('pid', 'ppid', 'pgrp', 'session', 'tty', 'tpgid', 'start', 'exe')}


def reader_tty(physical, tty, row):
    if row['tty'] == physical:
        return '/dev/' + tty
    major, minor = (row['tty'] >> 8) & 0xfff, (row['tty'] & 255) | ((row['tty'] >> 12) & 0xfff00)
    assert 136 <= major <= 143 and 0 <= minor <= 255, 'Unsupported reader tty'
    return '/dev/pts/' + str((major - 136) * 256 + minor)


def echo_at(path, device):
    import termios
    fd = os.open(path, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        assert device_number(fd) == device, 'Reader tty device changed'
        return bool(termios.tcgetattr(fd)[3] & termios.ECHO)
    finally:
        os.close(fd)


def hidden_observation(tty, expected, prompt, proc=pathlib.Path('/proc')):
    import termios
    assert tty in ('tty3', 'tty4') and prompt and prompt == prompt.rstrip()
    fd = os.open('/dev/' + tty, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        physical = device_number(fd)
        outer_echo = bool(termios.tcgetattr(fd)[3] & termios.ECHO)
    finally:
        os.close(fd)
    rows = hidden_snapshot(proc)
    trace = reader_chain(rows, physical, expected)
    raw = pathlib.Path('/dev/vcsa' + tty[3:]).read_bytes()
    _, line = screen(raw)
    value = dict(ready=False, physical_echo_enabled=outer_echo, reader_echo_enabled=None,
        prompt_at_cursor=line.endswith(prompt), observation=dict(reason=trace['reason'], foreground_chain=redacted_chain(trace['chain'])),
        reader=None, raw=base64.b64encode(raw).decode())
    row = trace['reader']
    if trace['valid'] and row and reader_matches(row, expected):
        path = reader_tty(physical, tty, row)
        value['reader_echo_enabled'] = echo_at(path, row['tty'])
        again = reader_chain(hidden_snapshot(proc), physical, expected)
        stable = (again['valid'] and [identity(r) for r in trace['chain']] == [identity(r) for r in again['chain']])
        value['ready'] = stable and not value['reader_echo_enabled'] and value['prompt_at_cursor']
        if value['ready']:
            value.update(reader=dict(**identity(row), tty_path=path, physical=physical), raw='')
    return value


def hidden_left(tty, expected, receipt, proc=pathlib.Path('/proc')):
    rows = hidden_snapshot(proc)
    trace = reader_chain(rows, receipt['physical'], expected)
    current = rows.get(receipt['pid'])
    ready, reason = False, trace['reason']
    # This is read completion, never an idle/Enter grant. The caller still
    # requires its normal shell or expected public-input/result predicate.
    if current is None or current['start'] != receipt['start'] or current['exe'] != receipt['exe']:
        ready, reason = True, 'Reader exited or exec completed'
    elif echo_at(receipt['tty_path'], receipt['tty']):
        ready, reason = True, 'Reader tty echo restored'
    elif (trace['valid'] and expected['kind'] == 'sudo' and trace['reader']['tty'] != receipt['tty']
            and any(r['pid'] == receipt['pid'] for r in trace['chain'])):
        ready, reason = True, 'Authenticated sudo started its verified relay'
    return dict(ready=ready, reason=reason, observation=dict(reason=trace['reason'], foreground_chain=redacted_chain(trace['chain'])),
        value_recorded=False, raw='' if ready else base64.b64encode(pathlib.Path('/dev/vcsa' + tty[3:]).read_bytes()).decode())


def source(tty, expected, prompt=None, receipt=None, timeout=60):
    assert 0 < timeout <= 60
    functions = (interactive_shell, process_snapshot, screen, device_number, hidden_snapshot, reader_matches,
        reader_chain, redacted_chain, identity, reader_tty, echo_at, hidden_observation, hidden_left)
    body = 'import base64,json,os,pathlib,re,termios,time\n' + ''.join(inspect.getsource(f) for f in functions)
    call = ('hidden_observation(' + repr(tty) + ',' + repr(expected) + ',' + repr(prompt) + ')' if receipt is None
        else 'hidden_left(' + repr(tty) + ',' + repr(expected) + ',' + repr(receipt) + ')')
    return body + '\n# hidden-phase: ' + ('ready' if receipt is None else 'left') + '''
deadline=time.monotonic()+@TIMEOUT@
value=dict(ready=False,observation=dict(reason='No readable reader observation',foreground_chain=[]),raw='')
while time.monotonic()<deadline:
    try:
        value=@CALL@
        if value['ready']: break
    except (OSError,termios.error,AssertionError): pass
    time.sleep(.1)
if not value['ready'] and not value.get('raw'):
    value['raw']=base64.b64encode(pathlib.Path(@VCSA@).read_bytes()).decode()
print(json.dumps(value))
'''.replace('@TIMEOUT@', repr(timeout)).replace('@CALL@', call).replace('@VCSA@', repr('/dev/vcsa' + tty[3:]))
