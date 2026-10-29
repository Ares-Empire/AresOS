"""Real two-PTY getpass/flush proof with explicit unprivileged sudo stand-ins."""
import contextlib
import copy
import fcntl
import json
import os
import pathlib
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import threading
import time
import tty
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_hidden as hidden
import owner_console as console
import owner_vm as vm
from test_owner_sudo_idle import row

PROMPT = 'Read-only token (hidden):'
VALUE = b'fixture-only-input'


def vcsa(text):
    lines = text.replace('\r', '').split('\n')[-50:]
    lines = [''] * (50 - len(lines)) + lines
    return bytes([50, 160, min(len(lines[-1]), 159), 49]) + b''.join(
        bytes([c, 7]) for line in lines for c in line.encode('latin1', 'replace')[:160].ljust(160))


class Proc:
    def __init__(self, folder, rows):
        self.root = pathlib.Path(folder)
        self.rows = rows
        self.write()

    def write(self):
        for r in self.rows:
            p = self.root / str(r['pid']); p.mkdir(exist_ok=True)
            fields = [r.get('state', 'S'), str(r['ppid']), str(r['pgrp']), str(r['session']),
                str(r['tty']), str(r['tpgid'])] + ['0'] * 13 + [r.get('start', '12345')]
            (p / 'stat').write_text(str(r['pid']) + ' (' + r['comm'] + ') ' + ' '.join(fields))
            (p / 'cmdline').write_bytes(b'\0'.join(a.encode() for a in r['args']) + b'\0')
            link = p / 'exe'
            if link.is_symlink(): link.unlink()
            link.symlink_to(r.get('exe', '/usr/bin/' + r['comm']))


def nested(physical, inner, pid, args):
    middle = 136 * 256 + 200
    assert middle not in (physical, inner)
    return [row(10, 1, 10, 10, physical, 20, 'bash', ['-bash']),
        row(20, 10, 20, 10, physical, 20, 'sudo', ['sudo', '-i']),
        row(21, 20, 21, 21, middle, 30, 'sudo', ['sudo', '-i']),
        row(22, 21, 22, 21, middle, 30, 'bash', ['-bash']),
        row(30, 22, 30, 21, middle, 30, 'sudo', ['sudo', '/var/lib/ares/at', 'login']),
        row(31, 30, 31, 31, inner, pid, 'sudo', ['sudo', '/var/lib/ares/at', 'login']),
        dict(row(pid, 31, pid, 31, inner, pid, 'python3', args), exe=os.path.realpath(sys.executable))]


class Relay(contextlib.AbstractContextManager):
    def __init__(self):
        self.stack = contextlib.ExitStack()
        self.root = pathlib.Path(self.stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT / 'os/tests')))
        self.outer, self.physical = pty.openpty()
        self.inner, self.reader = pty.openpty()
        self.physical_name, self.reader_name = os.ttyname(self.physical), os.ttyname(self.reader)
        tty.setraw(self.physical)  # sudo keeps the outer terminal raw throughout.
        self.gate, gate_in = os.pipe()
        self.finish, finish_in = os.pipe()
        script = self.root / 'reader.py'
        script.write_text('''import getpass,os
os.write(1,b'STARTING\\n')
os.read(int(os.environ['READ_GATE']),1)
value=getpass.getpass('Read-only token (hidden): ')
assert value=='fixture-only-input'
del value
os.write(1,b'READ_OK\\n')
os.read(int(os.environ['FINISH_GATE']),1)
''')
        # Swap pipe ends: only these small non-secret coordination bytes use them.
        gate_read, gate_write = self.gate, gate_in
        finish_read, finish_write = self.finish, finish_in
        self.gate, self.finish = gate_write, finish_write
        def controlling():
            os.setsid(); fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        self.args = [sys.executable, '-I', '-B', str(script), 'login']
        self.process = subprocess.Popen(self.args, stdin=self.reader, stdout=self.reader, stderr=self.reader,
            preexec_fn=controlling, pass_fds=(gate_read, finish_read),
            env=dict(os.environ, READ_GATE=str(gate_read), FINISH_GATE=str(finish_read)))
        os.close(gate_read); os.close(finish_read)
        self.stop, self.forwarded = threading.Event(), threading.Event()
        self.output = bytearray(); self.sent = []
        def relay():
            while not self.stop.is_set():
                for fd in select.select([self.physical, self.inner], [], [], .02)[0]:
                    try: data = os.read(fd, 65536)
                    except OSError: return
                    if not data: return
                    os.write(self.inner if fd == self.physical else self.physical, data)
                    if fd == self.physical: self.forwarded.set()
        self.thread = threading.Thread(target=relay, daemon=True); self.thread.start()
        self.until(b'STARTING', 3)
        model = self.root / 'proc'; model.mkdir()
        self.model = Proc(model, nested(console_device(self.physical), console_device(self.reader), self.process.pid, self.args))
        self.expected = dict(kind='owner', argv=self.args)

    def drain(self, seconds=.02):
        while select.select([self.outer], [], [], seconds)[0]:
            self.output.extend(os.read(self.outer, 65536)); seconds = 0

    def until(self, marker, timeout=3):
        end = time.monotonic() + timeout
        while marker not in self.output and time.monotonic() < end: self.drain(.02)
        assert marker in self.output, 'PTY marker deadline'

    def send(self):
        self.sent.append(True); self.forwarded.clear(); os.write(self.outer, VALUE + b'\n')
        assert self.forwarded.wait(2), 'Relay did not forward input'

    def pending_bytes(self):
        return struct.unpack('I', fcntl.ioctl(self.reader, termios.FIONREAD, struct.pack('I', 0)))[0]

    def observe(self):
        self.drain()
        original_open, original_read = os.open, pathlib.Path.read_bytes
        def open_tty(path, *args, **kw):
            return original_open(self.physical_name if str(path) == '/dev/tty3' else path, *args, **kw)
        raw = vcsa(self.output.decode('latin1'))
        with patch.object(os, 'open', side_effect=open_tty), patch.object(pathlib.Path, 'read_bytes',
                lambda p: raw if str(p) == '/dev/vcsa3' else original_read(p)):
            return hidden.hidden_observation('tty3', self.expected, PROMPT, self.model.root)

    def completion(self, receipt):
        original = pathlib.Path.read_bytes
        raw = vcsa(self.output.decode('latin1'))
        with patch.object(pathlib.Path, 'read_bytes', lambda p: raw if str(p) == '/dev/vcsa3' else original(p)):
            return hidden.hidden_left('tty3', self.expected, receipt, self.model.root)

    def close(self):
        self.stop.set()
        try: os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError: pass
        self.process.wait(timeout=3); self.thread.join(timeout=1)
        for fd in (self.outer, self.physical, self.inner, self.reader, self.gate, self.finish): os.close(fd)
        self.stack.close()

    def __exit__(self, *args): self.close()


def console_device(fd):
    return hidden.device_number(fd)


class HiddenTest(unittest.TestCase):
    def test_expected_owner_path_matches_real_install_and_resolving_entry(self):
        import ast
        import shutil
        source = ast.parse((ROOT/'os/owner-tools/owner.py').read_text())
        install, = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'install']
        # Execute only the real installer's three ordinary-file placement steps.
        # Device checks and privileged handlers are not called by this path test.
        placement = [n for n in install.body if isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
            and isinstance(n.value.func, ast.Attribute) and (n.value.func.attr in ('copytree','symlink_to')
                or ast.unparse(n.value.func) == 'HOME.mkdir')]
        self.assertEqual([n.value.func.attr for n in placement], ['mkdir','copytree','symlink_to'])
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            root = pathlib.Path(folder); payload=root/'payload'; payload.mkdir(); home=root/'home'
            shutil.copyfile(ROOT/'os/owner-tools/at', payload/'at')
            (payload/'owner.py').write_text('import json,sys; print(json.dumps(sys.argv))')
            exec(compile(ast.Module(body=placement, type_ignores=[]), 'real install placement', 'exec'),
                dict(HOME=home, payload=payload, shutil=shutil))
            result=subprocess.run(['bash',str(home/'at'),'login'],capture_output=True,text=True,check=True)
            self.assertFalse(result.stderr)
            actual=json.loads(result.stdout)
            expected=hidden.owner_reader(['login'])['argv']
            self.assertEqual(expected[:3], ['/usr/bin/python3','-I','-B'])
            self.assertEqual(actual, [str(home/'tools/owner.py'), 'login'])
            self.assertEqual(expected[3:], ['/var/lib/ares/'+str(pathlib.Path(actual[0]).relative_to(home)), 'login'])

    def test_old_outer_echo_check_fires_early_and_tcsa_flush_loses_input(self):
        with Relay() as f:
            self.assertFalse(bool(termios.tcgetattr(f.physical)[3] & termios.ECHO))
            self.assertFalse(console.foreground_observation(console_device(f.physical), f.model.root)['ready'])
            self.assertTrue(bool(termios.tcgetattr(f.reader)[3] & termios.ECHO))
            f.send()
            end = time.monotonic() + 2
            while not f.pending_bytes() and time.monotonic() < end: time.sleep(.01)
            self.assertGreater(f.pending_bytes(), 0)
            os.write(f.gate, b'1'); f.until(PROMPT.encode())
            self.assertEqual(f.pending_bytes(), 0)
            f.drain(.1); self.assertNotIn(b'READ_OK', f.output)
            self.assertIsNone(f.process.poll())
            self.assertEqual(len(f.sent), 1)  # STOP; never retry the discarded value.

    def test_new_proof_waits_for_inner_echo_and_prompt_and_value_arrives(self):
        with Relay() as f:
            early = f.observe()
            self.assertFalse(early['ready']); self.assertFalse(early['physical_echo_enabled'])
            self.assertTrue(early['reader_echo_enabled']); self.assertFalse(early['prompt_at_cursor'])
            os.write(f.gate, b'1'); f.until(PROMPT.encode())
            ready = f.observe(); self.assertTrue(ready['ready'])
            self.assertEqual(ready['reader']['tty_path'], f.reader_name)
            self.assertFalse(ready['reader_echo_enabled'])
            before = len(f.output); f.send(); f.until(b'READ_OK')
            self.assertNotIn(VALUE, f.output[before:])
            left = f.completion(ready['reader'])
            # Restored ECHO is not completion while the reader process still
            # owns the foreground and has not produced a result/shell prompt.
            self.assertFalse(left['ready']); self.assertFalse(left['completion_uses_echo'])
            self.assertFalse(left['value_recorded']); self.assertEqual(len(f.sent), 1)

    def test_busy_reader_with_echo_off_is_not_ready_without_cursor_prompt(self):
        with Relay() as f:
            flags = termios.tcgetattr(f.reader); flags[3] &= ~termios.ECHO
            termios.tcsetattr(f.reader, termios.TCSANOW, flags)
            value = f.observe()
            self.assertFalse(value['ready']); self.assertFalse(value['reader_echo_enabled'])
            self.assertEqual(f.sent, [])

    def test_expected_reader_argv_exe_and_relay_links_are_required(self):
        for index, key, value in ((6, 'args', ['python3', 'untrusted-input']), (6, 'exe', '/usr/bin/other'),
                (4, 'comm', 'tmux'), (5, 'session', 21), (5, 'tty', 136 * 256 + 200),
                (6, 'tpgid', 999), (6, 'ppid', 999)):
            with self.subTest(index=index, key=key), Relay() as f:
                os.write(f.gate, b'1'); f.until(PROMPT.encode())
                f.model.rows[index][key] = value; f.model.write()
                self.assertFalse(f.observe()['ready']); self.assertEqual(f.sent, [])

    def test_direct_login_sudo_second_console_sudo_and_owner_use_the_same_proof(self):
        from owner_console_shim import execute_hidden
        for tty_name in ('tty3', 'tty4'):
            for spec, prompt in ((dict(kind='login'), 'Password:'),
                    (hidden.sudo_reader(['-i'], dict(kind='shell')), vm.SUDO_PROMPT),
                    (hidden.sudo_reader(['/var/lib/ares/at', 'layout', 'proof'], hidden.owner_reader(['layout', 'proof'])), vm.SUDO_PROMPT),
                    (hidden.owner_reader(['login']), PROMPT)):
                with self.subTest(tty=tty_name, kind=spec['kind']):
                    proof = execute_hidden(hidden.source(tty_name, spec, prompt=prompt))
                    self.assertTrue(proof['ready'] and proof['prompt_at_cursor'])
                    self.assertFalse(proof['reader_echo_enabled'])
                    self.assertEqual(proof['reader']['tty_path'], '/dev/pts/2' if spec['kind'] == 'owner' else '/dev/'+tty_name)
                    left = execute_hidden(hidden.source(tty_name, spec, receipt=proof['reader']))
                    self.assertTrue(left['ready']); self.assertFalse(left['value_recorded'])

    def test_composed_read_completion_is_bounded_and_exports_refusal_without_value(self):
        from owner_console_shim import execute_hidden
        expected = hidden.owner_reader(['login'])
        proof = execute_hidden(hidden.source('tty3', expected, prompt=PROMPT))
        class Clock:
            now = 0
            delays = []
            def monotonic(self): return self.now
            def sleep(self, delay):
                self.delays.append(delay)
                self.now += 10  # Model slow observations without 600 DrvFS scans.
        clock = Clock()
        with patch.object(time, 'monotonic', clock.monotonic), patch.object(time, 'sleep', clock.sleep):
            left = execute_hidden(hidden.source('tty3', expected, receipt=proof['reader']), leaves=False)
        self.assertFalse(left['ready']); self.assertFalse(left['value_recorded'])
        self.assertTrue(left['observation']['foreground_chain'])
        self.assertGreaterEqual(clock.now, 60); self.assertLess(clock.now, 60.2)
        self.assertTrue(clock.delays and all(delay == .1 for delay in clock.delays))

    def test_three_sudo_transitions_pass_and_four_refuse(self):
        for hops in (3, 4):
            with self.subTest(hops=hops), Relay() as f:
                rows = f.model.rows
                middle = 136*256+200; extra = middle+1
                rows[2]['tpgid'] = rows[3]['tpgid'] = 25
                rows[4].update(ppid=27, tty=extra, session=26)
                rows += [row(25,22,25,21,middle,25,'sudo',['sudo','-i']),
                    row(26,25,26,26,extra,30,'sudo',['sudo','-i']),
                    row(27,26,27,26,extra,30,'bash',['-bash'])]
                if hops == 4:
                    rows[-2]['tpgid'] = rows[-1]['tpgid'] = 28
                    rows[4].update(ppid=32,tty=extra+1,session=29)
                    rows += [row(28,27,28,26,extra,28,'sudo',['sudo','-i']),
                        row(29,28,29,29,extra+1,30,'sudo',['sudo','-i']),
                        row(32,29,32,29,extra+1,30,'bash',['-bash'])]
                f.model.write(); os.write(f.gate,b'1'); f.until(PROMPT.encode())
                self.assertEqual(f.observe()['ready'], hops == 3)

    def test_exact_qualification7_process_shape_waits_for_the_real_prompt(self):
        fixture = json.loads((ROOT/'os/tests/fixtures/owner-console/14zi-qualification7.json').read_text())
        self.assertEqual(fixture['run'], 40630352782)
        with Relay() as f:
            rows = []
            original_pid = fixture['processes'][-1]['pid']
            devices = {1027: console_device(f.physical), 34817:136*256+200, 34818:console_device(f.reader)}
            for index, captured in enumerate(fixture['processes']):
                v = {key: captured[key] for key in ('pid','ppid','pgrp','session','tty','tpgid','comm')}
                for key in ('pid','ppid','pgrp','session','tpgid'):
                    if v[key] == original_pid: v[key] = f.process.pid
                v['tty'] = devices[v['tty']]
                v['args'] = (['sudo','-i'] if index < 2 else ['-bash'] if index == 2
                    else ['sudo','/var/lib/ares/at','login'] if index < 5 else f.args)
                if index == 5: v['exe'] = os.path.realpath(sys.executable)
                rows.append(v)
            proc = f.root/'retained-proc';proc.mkdir();f.model = Proc(proc,rows)
            self.assertFalse(console.foreground_observation(console_device(f.physical),proc)['ready'])
            self.assertFalse(f.observe()['ready'])
            os.write(f.gate,b'1');f.until(PROMPT.encode())
            self.assertTrue(f.observe()['ready']);self.assertEqual(f.sent,[])

    def test_secret_is_not_retyped_when_read_completion_refuses(self):
        from test_owner_reliable_typing import Driver
        class Guest(Driver):
            def capture_json(self, stage, command):
                self.command = command
                if '# hidden-phase: left' not in command:return super().capture_json(stage,command)
                return dict(ready=False, raw=__import__('base64').b64encode(vcsa(PROMPT)).decode(),
                    observation=dict(foreground_chain=[]))
        guest = Guest(); guest.proven=True; c = vm.Console(guest)
        c.pending_hidden = dict(stage='synthetic-read', epoch=0, expected=hidden.owner_reader(['login']),
            reader=dict(pid=10, start='1', exe='/usr/bin/python3', tty=34818, tty_path='/dev/pts/2', physical=1027))
        calls = []
        original=vm.type_text
        def type_once(g, text, layout, counts=None):
            calls.append(text);return original(g,text,layout,counts=counts)
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder, patch.object(vm.td, 'EVIDENCE', pathlib.Path(folder)), \
                patch.object(vm, 'type_text', side_effect=type_once):
            with self.assertRaisesRegex(AssertionError, 'will not be retyped'): c.send_hidden(VALUE.decode())
            with self.assertRaisesRegex(AssertionError, 'already attempted'): c.send_hidden(VALUE.decode())
        self.assertEqual(calls, [VALUE.decode(), '\n']); self.assertNotIn(VALUE.decode(), guest.command)


if __name__ == '__main__': unittest.main()
