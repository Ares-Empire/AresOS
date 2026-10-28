"""Read-only hidden-reader diagnostics. Never read queued bytes or syscall args."""
import inspect
import os
import pathlib
import re

from owner_hidden import device_number, hidden_snapshot, reader_chain, reader_tty
from owner_console import interactive_shell, process_snapshot


def terminal_diagnostics(path, device, physical=False):
    import array
    import fcntl
    import termios
    value = dict(path=path, device=device)
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
        assert device_number(fd) == device, 'Terminal device changed'
        flags = termios.tcgetattr(fd)
        value['termios'] = {name: bool(flags[index] & getattr(termios, name)) for name, index in
            (('ICANON', 3), ('ECHO', 3), ('ICRNL', 0), ('IXON', 0), ('IEXTEN', 3), ('ISIG', 3))}
        for name in ('TIOCINQ', 'TIOCOUTQ'):
            number = array.array('i', [0])
            fcntl.ioctl(fd, getattr(termios, name), number, True)
            assert number[0] >= 0
            value[name] = number[0]
        if physical:
            # linux/kd.h: getters only. No terminal settings or LEDs are changed.
            for name, request, kind in (('KDGKBMODE', 0x4b44, 'i'), ('KDGETLED', 0x4b31, 'B'), ('KDGKBLED', 0x4b64, 'B')):
                number = array.array(kind, [0])
                fcntl.ioctl(fd, request, number, True)
                value[name] = number[0]
    except (OSError, AssertionError) as error:
        value['error'] = dict(kind=type(error).__name__, errno=getattr(error, 'errno', None))
    finally:
        if fd is not None: os.close(fd)
    return value


def process_diagnostics(proc, pid):
    value = dict(pid=pid)
    for name in ('stat', 'wchan', 'syscall'):
        try:
            text = (proc / str(pid) / name).read_text()
            if name == 'stat':
                state = text.rsplit(')', 1)[1].split()[0]
                assert re.fullmatch('[RSDZTWtXxKWPIN]', state)
                value['state'] = state
            elif name == 'wchan':
                assert re.fullmatch(r'[a-zA-Z0-9_]+\s*', text)
                value['wchan'] = text.strip()
            else:
                # Deliberately discard addresses and ALL syscall arguments.
                number = text.split()[0]
                assert number == 'running' or re.fullmatch(r'-?\d+', number)
                value['syscall_number'] = number if number == 'running' else int(number)
        except (OSError, AssertionError, IndexError) as error:
            value[name + '_error'] = dict(kind=type(error).__name__, errno=getattr(error, 'errno', None))
    return value


def collect(tty, expected, receipt, proc=pathlib.Path('/proc'), sysroot=pathlib.Path('/sys')):
    import platform
    import subprocess
    assert tty in ('tty3', 'tty4')
    physical = receipt['physical']
    rows = hidden_snapshot(proc)
    trace = reader_chain(rows, physical, expected)
    # Include the granted chain even if a process exited or the current chain broke.
    chain = {r['pid']: r for r in receipt['origin_chain']}
    chain.update({r['pid']: r for r in trace['chain']})
    devices = {physical, 4 * 256 + 3}  # Always include tty3, including tty4 password failures.
    devices.update(r['tty'] for r in chain.values() if r['tty'])
    terminals = []
    for device in sorted(devices):
        try:
            path = '/dev/tty3' if device == 4 * 256 + 3 else reader_tty(physical, tty, dict(tty=device))
            terminals.append(terminal_diagnostics(path, device, device in (physical, 4 * 256 + 3)))
        except AssertionError:
            terminals.append(dict(device=device, error=dict(kind='UnsupportedTerminal')))
    try:
        active = (sysroot / 'class/tty/tty0/active').read_text().strip()
        assert re.fullmatch(r'tty\d+', active)
    except (OSError, AssertionError): active = None
    sudo = None
    try:
        result = subprocess.run(['/usr/bin/sudo', '-V'], capture_output=True, text=True, timeout=10,
            env=dict(os.environ, LC_ALL='C'))
        match = re.search(r'^Sudo version ([0-9]+\.[0-9]+\.[0-9]+(?:p[0-9]+)?)$', result.stdout, re.M)
        if result.returncode == 0 and match: sudo = match[1]
    except (OSError, subprocess.TimeoutExpired): pass
    return dict(kind='hidden-read-diagnostics', read_only=True, value_recorded=False,
        queue_contents_read=False, syscall_arguments_recorded=False, active_vt=active,
        python_version=platform.python_version(), sudo_version=sudo, terminals=terminals,
        processes=[process_diagnostics(proc, pid) for pid in sorted(chain)])


def source(tty, expected, receipt):
    from owner_hidden import reader_matches
    functions = (interactive_shell, process_snapshot, device_number, hidden_snapshot,
        reader_matches, reader_chain, reader_tty, terminal_diagnostics, process_diagnostics, collect)
    return ('import json,os,pathlib,re\n# hidden-read-diagnostics\n' +
        ''.join(inspect.getsource(f) for f in functions) +
        '\nprint(json.dumps(collect(' + repr(tty) + ',' + repr(expected) + ',' + repr(receipt) + ')))\n')
