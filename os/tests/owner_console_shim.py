"""Read-only guest /proc and VCSA stand-ins; never acquire a host terminal."""
import contextlib
import ast
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace
from unittest.mock import patch

from test_owner_sudo_idle import relay, TTY


def execute_screen(source, raw, unicode_data=None):
    """Run the actual cursor predicate and three-sample loop, no host VCSA."""
    output = io.StringIO()
    class Clock:
        now = 0
        def monotonic(self): return self.now
        def sleep(self, delay): self.now += delay
    clock = Clock()
    def read(path):
        if str(path) in ('/dev/vcsu3','/dev/vcsu4'):
            if unicode_data is not None:return unicode_data
            import struct
            return struct.pack('='+'I'*(len(raw[4::2])),*raw[4::2])
        assert str(path) in ('/dev/vcsa3','/dev/vcsa4')
        return raw
    with patch.object(pathlib.Path,'read_bytes',read), patch.object(time,'monotonic',clock.monotonic), \
            patch.object(time,'sleep',clock.sleep), contextlib.redirect_stdout(output):
        exec(compile(source,'modelled-cursor-predicate','exec'),{})
    return json.loads(output.getvalue())


def execute_echo(command):
    """Actual echo predicate on explicit public-text screen facts."""
    import shlex
    from test_owner_hidden import vcsa
    words=shlex.split(command);source=words[words.index('python3')+2]
    value,=[ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Attribute) and n.func.attr=='endswith']
    return execute_screen(source,vcsa('root# '+value))


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


@contextlib.contextmanager
def model_clock(step=5):
    """Guest time for an observer that a walk runs: every sleep moves the clock. An observer that
    never sees what it waits for then ends at its own deadline and answers with its refusal, as in
    the VM, instead of waiting for ever on a clock that stands still."""
    class Clock:
        now = 0.0
        def monotonic(self): return self.now
        def sleep(self, delay): self.now += max(delay, step)
    clock = Clock()
    with patch.object(time, 'monotonic', clock.monotonic), patch.object(time, 'sleep', clock.sleep):
        yield clock


class InstalledTools:
    """A walk's own /var/lib/ares: the entry link as the tools place it, and the process it starts.

    The link is moved by the tools' own switch_entry. The reader's command line is what the real
    os/owner-tools/at execs through that link (a stand-in owner.py prints its command line and does
    nothing else). Nothing here comes from the reader the harness expects: a harness that names
    another folder meets a foreground process it does not know, as the VM showed in run 43581458429.
    """
    GUEST = '/var/lib/ares'
    STAND_IN = "import json; print(json.dumps(open('/proc/self/cmdline','rb').read().decode().split('\\0')[:-1]))\n"

    def __init__(self, folder):
        import test_owner_tools as common
        self.owner = common.owner
        self.home = pathlib.Path(folder).resolve() / 'var-lib-ares'
        self.home.mkdir()
        self.started = {}

    def install(self, fingerprint=None):
        """Publish a toolset and make it the entry: tools at the first install, tools-<fingerprint> at an update."""
        name = 'tools' if fingerprint is None else 'tools-' + fingerprint
        toolset = self.home / name
        toolset.mkdir()
        shutil.copyfile(pathlib.Path(__file__).resolve().parents[2] / 'os/owner-tools/at', toolset / 'at')
        (toolset / 'owner.py').write_text(self.STAND_IN)
        with patch.object(self.owner, 'HOME', self.home):
            self.owner.switch_entry(name)

    def as_guest(self, text):
        return text.replace(str(self.home), self.GUEST)

    def resolve(self, source):
        """The harness's own guest program that resolves the entry, run on this model."""
        entry = repr(self.GUEST + '/at')
        assert source.count(entry) == 1, 'The entry program names the entry once'
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(source.replace(entry, repr(str(self.home / 'at'))), 'modelled-entry', 'exec'), {})
        return json.loads(self.as_guest(output.getvalue()))

    def reader(self, args):
        """The command line of the tools' process that `sudo /var/lib/ares/at <args>` ends in."""
        key = (os.readlink(self.home / 'at'), tuple(args))
        if key not in self.started:
            done = subprocess.run(['bash', str(self.home / 'at'), *args], capture_output=True, text=True, check=True)
            self.started[key] = [self.as_guest(word) for word in json.loads(done.stdout)]
        return list(self.started[key])


def hidden_rows(physical, expected, phase, leaves=True, rejected=False, actual=None):
    """actual: a walk's own facts about the owner command typed last, dict(sudo=<the sudo words
    typed>, owner=<the tools' process, InstalledTools.reader>). The rows of that command are built
    from them, never from the reader the harness expects. Without it (unit fixtures) the rows repeat
    the expected reader."""
    from test_owner_sudo_idle import row
    from test_owner_hidden import nested
    login = row(1962,1,1962,1962,physical,1962,'login',['login','--','ares-recovery'])
    shell = row(2926,1962,2926,2926,physical,2926,'bash',['-bash'])
    relayed = expected['kind'] == 'sudo' and expected['next']['kind'] == 'owner'
    if actual is not None and (expected['kind'] == 'owner' or relayed):
        expected = dict(expected, argv=actual['owner'] if expected['kind'] == 'owner' else actual['sudo'])
        if relayed:
            expected['next'] = dict(expected['next'], argv=actual['owner'])
    if expected['kind'] == 'owner':
        rows = nested(physical,136*256+2,40,expected['argv'])
        if phase == 'left' and leaves:
            rows = rows[:4]
            rows[2]['tpgid'] = rows[3]['tpgid'] = rows[3]['pgrp']
        return rows, 'nested-owner-getpass' if phase != 'left' or not leaves else 'sudo-i-readline'
    if expected['kind'] == 'passwd':
        # Package 27: `sudo passwd ares` in the root console, passwd on sudo's pts.
        if phase == 'left' and leaves:
            login.update(tty=0,tpgid=-1)
            return [login,shell], 'persistent-login-readline'
        login.update(tty=0,tpgid=-1)
        shell['tpgid'] = 3000
        argv = ['sudo', *expected['argv']]
        return [login,shell,row(3000,2926,3000,2926,physical,3000,'sudo',argv),
            row(3001,3000,3001,3001,136*256+2,3002,'sudo',argv),
            row(3002,3001,3002,3001,136*256+2,3002,'passwd',expected['argv'])], 'sudo-passwd-reader'
    if expected == dict(kind='sudo', argv=['sudo', '-v'], next=dict(kind='shell')) and phase == 'left' and leaves:
        # Package 27: his `sudo -v` in a plain tty4 login shell returns to it.
        login.update(tty=0,tpgid=-1)
        return [login,shell], 'persistent-login-readline'
    if expected['kind'] == 'login':
        if phase == 'left' and leaves and not rejected:
            login.update(tty=0,tpgid=-1)
            return [login,shell], 'persistent-login-readline'
        return [login], 'login-rejected' if rejected else 'getty-login-reader'
    login.update(tty=0,tpgid=-1)
    shell['tpgid'] = 3000
    front = row(3000,2926,3000,2926,physical,3000,'sudo',expected['argv'])
    if phase == 'ready' or not leaves:
        return [login,shell,front], 'sudo-password-reader'
    if expected['next']['kind'] == 'shell' or phase == 'handoff':
        monitor = row(3001,3000,3001,3001,136*256+1,3002,'sudo',expected['argv'])
        child = row(3002,3001,3002,3001,136*256+1,3002,'bash',['-bash'])
        if phase == 'handoff':
            child.update(pid=4000,pgrp=4000,tpgid=4000,comm='python3',args=expected['next']['argv'])
            monitor['tpgid'] = 4000
        return [login,shell,front,monitor,child], 'sudo-owner-public-handoff' if phase == 'handoff' else 'sudo-i-readline'
    shell['tpgid'] = shell['pid']
    return [login,shell], 'persistent-login-readline'


def execute_hidden(source, leaves=True, rejected=False, facts=False, raw=None, actual=None):
    """Real composed proof over proc/VCSA facts; ECHO is always off.

    Completion deliberately traps tcgetattr so an ECHO dependency cannot pass.
    actual: see hidden_rows (a walk's own processes for the owner command typed last).
    """
    import termios
    from test_owner_hidden import Proc, vcsa, PROMPT
    names = ('hidden_observation','hidden_left','hidden_handoff')
    calls = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id in names]
    call, = calls
    tty, expected, third = [ast.literal_eval(n) for n in call.args[:3]]
    physical = 4 * 256 + int(tty[3:])
    phase = 'ready' if call.func.id == 'hidden_observation' else 'handoff' if call.func.id == 'hidden_handoff' else 'left'
    if phase != 'ready':
        assert 'tcgetattr' not in source, 'Completion script contains an ECHO check'
    rows, shape = hidden_rows(physical, expected, phase, leaves, rejected, actual)
    text = third if phase == 'ready' else ('Physically type yz-/!ü then Return:' if phase == 'handoff'
        else 'Login incorrect\nlocalhost login:' if rejected else 'root@bazzite:~# ' if leaves else PROMPT)
    raw = vcsa(text) if raw is None else raw
    with tempfile.TemporaryDirectory(dir=pathlib.Path(__file__).parent) as folder:
        proc = Proc(folder, rows).root
        read_text, read_bytes, glob, readlink = pathlib.Path.read_text, pathlib.Path.read_bytes, pathlib.Path.glob, os.readlink
        def mapped(path):
            p = pathlib.Path(path)
            return proc / p.relative_to('/proc') if str(p).startswith('/proc/') else p
        def open_tty(path, *args, **kw):
            if str(path) == '/dev/' + tty: return 123
            assert str(path).startswith('/dev/pts/'), path
            return 124
        def terminal(fd):
            assert phase == 'ready', 'Completion consulted ECHO'
            return [0,0,0,0]
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(pathlib.Path, 'read_text', lambda p: read_text(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path, 'read_bytes', lambda p: raw if str(p) == '/dev/vcsa' + tty[3:] else read_bytes(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path, 'glob', lambda p, pattern: glob(proc if str(p) == '/proc' else p, pattern)))
            stack.enter_context(patch.object(os, 'readlink', lambda p: readlink(mapped(p))))
            stack.enter_context(patch.object(os, 'open', side_effect=open_tty))
            stack.enter_context(patch.object(os, 'close'))
            # Owner getpass is on pts2; a second-console sudo is direct tty.
            stack.enter_context(patch.object(os, 'fstat', side_effect=lambda fd: SimpleNamespace(
                st_rdev=os.makedev(4, int(tty[3:])) if fd == 123 else os.makedev(136, 2))))
            stack.enter_context(patch.object(termios, 'tcgetattr', side_effect=terminal))
            with contextlib.redirect_stdout(output):
                exec(compile(source, 'modelled-hidden-reader', 'exec'), {})
        value = json.loads(output.getvalue())
    return (value,rows,shape) if facts else value
