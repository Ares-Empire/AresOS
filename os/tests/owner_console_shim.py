"""Read-only guest /proc and VCSA stand-ins; never acquire a host terminal."""
import contextlib
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
