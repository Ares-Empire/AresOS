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

from owner_console import interactive_shell, process_snapshot, screen, foreground_observation


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


def return_shells(rows, trace, physical):
    saved, seen = [], set()
    row = rows.get(trace['chain'][0]['ppid'])
    while row and row['pid'] not in seen and len(seen) < 8:
        seen.add(row['pid'])
        if reader_matches(row, dict(kind='shell')) and row['tty'] == physical:
            saved.append(identity(row))
        row = rows.get(row['ppid'])
    return saved


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
            value.update(reader=dict(**identity(row), tty_path=path, physical=physical,
                origin_chain=[identity(r) for r in trace['chain']],
                return_shells=return_shells(rows, trace, physical)), raw='')
    return value


def same_process(row, saved):
    return row is not None and all(row[k] == saved[k] for k in ('pid', 'start', 'exe'))


def related_transition(rows, trace, expected, receipt):
    """Tie the new foreground to the granted reader, never just any shell."""
    if not trace['valid'] or not trace['reader']:
        return False
    leaf = trace['reader']
    if expected['kind'] == 'login':
        # util-linux login detaches, forks a new session/shell, then stays as
        # its PAM parent. The parent may have no controlling tty afterwards.
        parent = rows.get(receipt['pid'])
        return (same_process(parent, receipt) and reader_matches(parent, expected)
            and parent['ppid'] == receipt['ppid'] == 1 and parent['tty'] in (0, receipt['physical'])
            and reader_matches(leaf, dict(kind='shell')) and leaf['ppid'] == parent['pid']
            and leaf['tty'] == receipt['physical'] and leaf['pid'] == leaf['pgrp'] == leaf['session'] == leaf['tpgid'])
    origin = receipt['origin_chain']
    if reader_matches(leaf, dict(kind='shell')) and any(same_process(leaf, saved)
            and all(leaf[k] == saved[k] for k in ('ppid','pgrp','session','tty')) for saved in receipt['return_shells']):
        return True
    common = min(len(origin), len(trace['chain']))
    if not all(same_process(row, saved) and all(row[k] == saved[k] for k in ('ppid','pgrp','session','tty'))
            for row, saved in zip(trace['chain'][:common], origin[:common])):
        return False
    if len(trace['chain']) <= len(origin):
        return True  # Return to an already-verified ancestor shell.
    return (expected['kind'] == 'sudo' and origin[-1]['pid'] == receipt['pid']
        and len(trace['chain']) == len(origin) + 2)  # Verified direct sudo monitor/command.


def completion_observation(tty, expected, receipt, proc):
    rows = hidden_snapshot(proc)
    trace = reader_chain(rows, receipt['physical'], expected)
    raw = pathlib.Path('/dev/vcsa' + tty[3:]).read_bytes()
    full, line = screen(raw)
    leaf = trace['reader']
    reader_foreground = bool(leaf and same_process(leaf, receipt) and reader_matches(leaf, expected))
    related = related_transition(rows, trace, expected, receipt)
    idle = foreground_observation(receipt['physical'], proc)
    shell = bool(related and leaf and reader_matches(leaf, dict(kind='shell')) and idle['ready']
        and not any(r['ppid'] == leaf['pid'] for r in rows.values())
        and len([r for r in rows.values() if r['tty'] == leaf['tty'] and r['pgrp'] == leaf['pgrp']]) == 1)
    owner = expected if expected['kind'] == 'owner' else expected.get('next')
    result = None
    if owner and owner['kind'] == 'owner':
        if line == 'PASS ' + ' '.join(owner['argv'][4:]): result = 'PASS'
        elif line.startswith('STOP: '): result = 'STOP'
    handoff = bool(related and expected['kind'] == 'sudo' and owner and owner['kind'] == 'owner'
        and leaf and reader_matches(leaf, owner) and not reader_foreground)
    # A rejected login is deliberately NOT a successful completion/idle grant.
    # The layout failure test may assert this STOP and return to its retained
    # administrator; it never sends another value or Enter to this console.
    rejected = expected['kind'] == 'login' and reader_foreground and 'Login incorrect' in full and line.endswith('login:')
    again = hidden_snapshot(proc)
    relevant = {r['pid'] for r in trace['chain']} | {receipt['pid']}
    for snapshot in (rows, again):
        relevant.update(r['pid'] for r in snapshot.values() if leaf and (r['ppid'] == leaf['pid'] or r['pgrp'] == leaf['pgrp']))
    stable = all(rows.get(pid) == again.get(pid) for pid in relevant)
    prompt = bool(re.search(r'[$#]$', line))
    ready = stable and not reader_foreground and related and ((shell and prompt)
        or (expected['kind'] == 'owner' and result is not None))
    return dict(ready=ready, reader_left=stable and related and not reader_foreground,
        shell_idle=stable and shell, prompt_at_cursor=prompt, owner_result=result,
        handoff=stable and handoff, rejected=stable and rejected,
        reason='Verified hidden-reader transition' if ready else trace['reason'],
        observation=dict(reason=trace['reason'], foreground_chain=redacted_chain(trace['chain'])),
        completion_uses_echo=False, value_recorded=False, raw='' if ready else base64.b64encode(raw).decode())


def hidden_left(tty, expected, receipt, proc=pathlib.Path('/proc')):
    return completion_observation(tty, expected, receipt, proc)


def input_guard(tty, expected, receipt, for_clear=False, proc=pathlib.Path('/proc')):
    """Prove canonical VKILL semantics without inspecting queued secret bytes."""
    import termios
    rows = hidden_snapshot(proc)
    trace = reader_chain(rows, receipt['physical'], expected)
    value = dict(ready=False,canonical=False,echo_enabled=None,vkill=None,syscall_number=None,
        value_recorded=False,queue_contents_read=False,
        observation=dict(reason=trace['reason'],foreground_chain=redacted_chain(trace['chain'])))
    row = trace['reader']
    if not trace['valid'] or not row or not reader_matches(row,expected) or not same_process(row,receipt): return value
    if [identity(r) for r in trace['chain']] != receipt['origin_chain']: return value
    fd = os.open(receipt['tty_path'],os.O_RDONLY|os.O_NOCTTY|os.O_NONBLOCK)
    try:
        assert device_number(fd)==receipt['tty'], 'Hidden reader tty changed'
        attrs = termios.tcgetattr(fd)
    finally: os.close(fd)
    kill = attrs[6][termios.VKILL]
    kill = kill if type(kill) is int else ord(kill)
    number = (proc/str(row['pid'])/'syscall').read_text().split()[0]
    assert re.fullmatch(r'-?[0-9]+',number), 'Hidden reader syscall unavailable'
    value.update(canonical=bool(attrs[3]&termios.ICANON),echo_enabled=bool(attrs[3]&termios.ECHO),
        vkill=kill,syscall_number=int(number))
    again = reader_chain(hidden_snapshot(proc),receipt['physical'],expected)
    stable = again['valid'] and [identity(r) for r in again['chain']]==receipt['origin_chain']
    value['ready'] = bool(stable and row['state']=='S' and not value['echo_enabled'] and value['syscall_number']==0
        and (not for_clear or (value['canonical'] and kill==21)))
    return value


def guard_source(tty,expected,receipt,for_clear=False,health=None):
    import owner_xhci
    functions=(interactive_shell,process_snapshot,hidden_snapshot,reader_matches,reader_chain,redacted_chain,
        identity,same_process,device_number,input_guard)
    return owner_xhci.guard(('import json,os,pathlib,re,time\n# hidden-input-guard\n'+''.join(inspect.getsource(f) for f in functions)
        + '\nvalue=dict(ready=False,reason="No stable canonical hidden reader")\n'
        + 'deadline=time.monotonic()+5\nstable=0\nwhile time.monotonic()<deadline:\n'
        + '    try:\n        value=input_guard('+repr(tty)+','+repr(expected)+','+repr(receipt)+','+repr(for_clear)+')\n'
        + '        stable=stable+1 if value["ready"] else 0\n        if stable>=3: break\n'
        + '    except (OSError,AssertionError): stable=0\n    time.sleep(.1)\n'
        + 'value["ready"]=bool(value.get("ready") and stable>=3)\nprint(json.dumps(value))\n'),health)


def hidden_handoff(tty, expected, receipt, prompt, proc=pathlib.Path('/proc')):
    value = completion_observation(tty, expected, receipt, proc)
    _, line = screen(pathlib.Path('/dev/vcsa' + tty[3:]).read_bytes())
    value['handoff_ready'] = value['handoff'] and line.startswith(prompt)
    value['ready'] = False  # A public-input handoff never claims hidden completion.
    if value['handoff_ready']: value['raw'] = ''
    return value


def source(tty, expected, prompt=None, receipt=None, timeout=60, handoff=None, health=None):
    import owner_xhci
    assert 0 < timeout <= (840 if receipt is not None else 60)
    functions = (interactive_shell, process_snapshot, screen, hidden_snapshot, reader_matches,
        reader_chain, redacted_chain, identity)
    if receipt is None:
        functions += (device_number, reader_tty, echo_at, return_shells, hidden_observation)
    else:
        functions += (foreground_observation, same_process, related_transition, completion_observation,
            hidden_handoff if handoff else hidden_left)
    body = 'import base64,json,os,pathlib,re,termios,time\n' + ''.join(inspect.getsource(f) for f in functions)
    call = ('hidden_observation(' + repr(tty) + ',' + repr(expected) + ',' + repr(prompt) + ')' if receipt is None
        else ('hidden_handoff(' + repr(tty) + ',' + repr(expected) + ',' + repr(receipt) + ',' + repr(handoff) + ')' if handoff
            else 'hidden_left(' + repr(tty) + ',' + repr(expected) + ',' + repr(receipt) + ')'))
    return owner_xhci.guard(body + '\n# hidden-phase: ' + ('ready' if receipt is None else 'handoff' if handoff else 'left') + '''
deadline=time.monotonic()+@TIMEOUT@
value=dict(ready=False,observation=dict(reason='No readable reader observation',foreground_chain=[]),raw='')
stable=0
while time.monotonic()<deadline:
    try:
        value=@CALL@
        stable=stable+1 if value['ready'] else 0
        if stable>=3 or value.get('handoff_ready') or value.get('rejected') or (not value['ready'] and value.get('reader_left') and value.get('shell_idle') and not value.get('prompt_at_cursor')): break
    except (OSError,termios.error,AssertionError): pass
    time.sleep(.1)
if value['ready'] and stable<3:
    value['ready']=False
    value['reason']='Unstable hidden-reader transition'
if not value['ready'] and not value.get('handoff_ready') and not value.get('raw'):
    value['raw']=base64.b64encode(pathlib.Path(@VCSA@).read_bytes()).decode()
print(json.dumps(value))
'''.replace('@TIMEOUT@', repr(timeout)).replace('@CALL@', call).replace('@VCSA@', repr('/dev/vcsa' + tty[3:])),health)
