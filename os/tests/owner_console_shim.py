"""Read-only guest /proc and VCSA stand-ins; never acquire a host terminal."""
import contextlib
import ast
import io
import json
import os
import pathlib
import re
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from test_owner_sudo_idle import relay, TTY


def execute_idle(source, raw, rows=None):
    import termios
    tty, = re.findall(r"os.open\('/dev/tty([34])'", source)
    number = int(tty)
    if rows is None:
        rows = relay()
        for row in rows:
            if row['tty'] == TTY:
                row['tty'] = 4 * 256 + number
    with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent) as directory:
        proc = pathlib.Path(directory)
        for row in rows:
            folder = proc / str(row['pid']); folder.mkdir()
            fields = ['S', str(row['ppid']), str(row['pgrp']), str(row['session']),
                str(row['tty']), str(row['tpgid'])] + ['0'] * 13 + ['12345']
            (folder / 'stat').write_text(str(row['pid']) + ' (' + row['comm'] + ') ' + ' '.join(fields))
            (folder / 'cmdline').write_bytes(b'\0'.join(arg.encode() for arg in row['args']) + b'\0')
        read_text, read_bytes, glob = pathlib.Path.read_text, pathlib.Path.read_bytes, pathlib.Path.glob
        def mapped(path):
            return proc / path.relative_to('/proc') if str(path).startswith('/proc/') else path
        def bytes_at(path):
            return raw if str(path) in ('/dev/vcsa3', '/dev/vcsa4') else read_bytes(mapped(path))
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(pathlib.Path, 'read_text', lambda path: read_text(mapped(path))))
            stack.enter_context(patch.object(pathlib.Path, 'read_bytes', bytes_at))
            stack.enter_context(patch.object(pathlib.Path, 'glob', lambda path, pattern: glob(proc if str(path) == '/proc' else path, pattern)))
            stack.enter_context(patch.object(os, 'open', return_value=123))
            stack.enter_context(patch.object(os, 'close'))
            stack.enter_context(patch.object(os, 'fstat', return_value=SimpleNamespace(st_rdev=0)))
            stack.enter_context(patch.object(os, 'major', return_value=4, create=True))
            stack.enter_context(patch.object(os, 'minor', return_value=number, create=True))
            stack.enter_context(patch.object(termios, 'tcgetattr', return_value=[0, 0, 0, 0]))
            with contextlib.redirect_stdout(output):
                exec(compile(source, 'modelled-physical-idle', 'exec'), {})
        return json.loads(output.getvalue())


def execute_hidden(source, leaves=True):
    """Execute a composed hidden-read command on synthetic proc/termios facts."""
    import termios
    from test_owner_hidden import Proc, nested, vcsa, PROMPT
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id in ('hidden_observation', 'hidden_left')]
    call, = calls
    tty, expected, third = [ast.literal_eval(n) for n in call.args]
    physical = 4 * 256 + int(tty[3:])
    leaving = call.func.id == 'hidden_left'
    if expected['kind'] == 'owner':
        rows = nested(physical, 136 * 256 + 2, 40, expected['argv'])
    elif expected['kind'] == 'login':
        rows = [dict(pid=10, ppid=1, pgrp=10, session=10, tty=physical,
            tpgid=10, comm='login', args=['login', '--', 'ares-recovery'])]
    else:
        rows = [dict(pid=20, ppid=1, pgrp=20, session=20, tty=physical,
            tpgid=20, comm='sudo', args=expected['argv'])]
    raw = vcsa(('root@bazzite:~# ' if leaves else PROMPT) if leaving else third)
    with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent) as folder:
        proc = Proc(folder, rows).root
        read_text, read_bytes, glob, readlink = pathlib.Path.read_text, pathlib.Path.read_bytes, pathlib.Path.glob, os.readlink
        def mapped(path):
            p = pathlib.Path(path)
            return proc / p.relative_to('/proc') if str(p).startswith('/proc/') else p
        def open_tty(path, *args, **kw):
            if str(path) == '/dev/' + tty: return 123
            assert str(path) == '/dev/pts/2', path
            return 124
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(pathlib.Path, 'read_text', lambda p: read_text(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path, 'read_bytes', lambda p: raw if str(p) == '/dev/vcsa' + tty[3:] else read_bytes(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path, 'glob', lambda p, pattern: glob(proc if str(p) == '/proc' else p, pattern)))
            stack.enter_context(patch.object(os, 'readlink', lambda p: readlink(mapped(p))))
            stack.enter_context(patch.object(os, 'open', side_effect=open_tty))
            stack.enter_context(patch.object(os, 'close'))
            stack.enter_context(patch.object(os, 'fstat', side_effect=lambda fd: SimpleNamespace(
                st_rdev=os.makedev(4, int(tty[3:])) if fd == 123 else os.makedev(136, 2))))
            stack.enter_context(patch.object(termios, 'tcgetattr', return_value=[0, 0, 0, termios.ECHO if leaving and leaves else 0]))
            with contextlib.redirect_stdout(output):
                exec(compile(source, 'modelled-hidden-reader', 'exec'), {})
        return json.loads(output.getvalue())
