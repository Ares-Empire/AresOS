"""Hidden completion is a foreground transition, independent of terminal ECHO."""
import contextlib
import copy
import fcntl
import json
import os
import pathlib
import pty
import select
import signal
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_hidden as hidden
import owner_console as console
from test_owner_hidden import Proc, Relay, vcsa, PROMPT
from test_owner_sudo_idle import row


def q8():
    value=json.loads((ROOT/'os/tests/fixtures/owner-console/14zk-q8-transition.json').read_text())
    receipt=value['readiness']['reader']
    parent=dict(row(1962,1,1962,1962,0,-1,'login',['login','--','ares-recovery']), start=receipt['start'])
    child=copy.deepcopy(value['completion']['observation']['foreground_chain'][0])
    child.update(args=['-bash'],exe='/usr/bin/bash')
    return receipt,[parent,child],(ROOT/value['public_cursor_fixture']['path']).read_bytes()


@contextlib.contextmanager
def physical_screen(raw):
    original=pathlib.Path.read_bytes
    with patch.object(pathlib.Path,'read_bytes',lambda p:raw if str(p) in ('/dev/vcsa3','/dev/vcsa4') else original(p)):
        yield


class LoginPTY(contextlib.AbstractContextManager):
    """Actual fork/detach/new-session/bash topology; no real PAM/login invoked.

    Only the Python parent's executable/name/manager PPID are explicit stand-ins
    for login/systemd. TTY, session, groups, ancestry and Readline are real.
    """
    def __init__(self):
        self.temp=tempfile.TemporaryDirectory(dir=ROOT/'os/tests');self.root=pathlib.Path(self.temp.name)
        self.master,slave=pty.openpty();self.slave_name=os.ttyname(slave);self.output=bytearray()
        script=self.root/'login-parent.py'
        script.write_text('''import fcntl,getpass,os,signal,termios
value=getpass.getpass('Password: ')
assert value=='fixture-only-input'
del value
signal.signal(signal.SIGHUP,signal.SIG_IGN)
fcntl.ioctl(0,termios.TIOCNOTTY,0)
child=os.fork()
if child==0:
 os.setsid()
 fd=os.open(os.environ['LOGIN_TEST_TTY'],os.O_RDWR)
 fcntl.ioctl(fd,termios.TIOCSCTTY,0)
 for target in (0,1,2):os.dup2(fd,target)
 signal.signal(signal.SIGHUP,signal.SIG_DFL)
 os.execve('/usr/bin/bash',['-bash','--noprofile','--norc','-i'],dict(os.environ,PS1='completion-fixture$ ',PS2='> '))
for fd in (0,1,2):os.close(fd)
os.waitpid(child,0)
''')
        def controlling():os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
        self.process=subprocess.Popen([sys.executable,'-I','-B',str(script)],stdin=slave,stdout=slave,stderr=slave,
            preexec_fn=controlling,env=dict(os.environ,LOGIN_TEST_TTY=self.slave_name,TERM='dumb'))
        os.close(slave);self.until(b'Password:')
        self.original=hidden.hidden_snapshot
        self.child=None

    def until(self,marker):
        deadline=time.monotonic()+4
        while marker not in self.output and time.monotonic()<deadline:
            if select.select([self.master],[],[],.05)[0]:self.output.extend(os.read(self.master,65536))
        assert marker in self.output,'Local login-like PTY deadline'

    def snapshot(self,proc):
        rows=self.original(proc)
        if self.process.pid in rows:
            rows[self.process.pid].update(comm='login',exe='/usr/bin/login',ppid=1,argv=[b'login',b'--',b'ares-recovery'])
        return rows

    @contextlib.contextmanager
    def facts(self):
        original=os.open
        def tty(path,*a,**kw):return original(self.slave_name if str(path)=='/dev/tty3' else path,*a,**kw)
        with patch.object(hidden,'hidden_snapshot',side_effect=self.snapshot),patch.object(os,'open',side_effect=tty),physical_screen(vcsa(self.output.decode('latin1'))):
            yield

    def __exit__(self,*args):
        rows=self.original(pathlib.Path('/proc'))
        for child in rows.values():
            if child['ppid']==self.process.pid:
                try:os.killpg(child['pgrp'],signal.SIGKILL)
                except ProcessLookupError:pass
        if self.process.poll() is None:self.process.kill()
        self.process.wait(timeout=4);os.close(self.master);self.temp.cleanup()


class CompletionTest(unittest.TestCase):
    def test_retained_q8_chain_and_public_cursor_complete_with_persistent_parent(self):
        receipt,rows,raw=q8()
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            proc=Proc(folder,rows).root
            with physical_screen(raw),patch.object(hidden,'echo_at',side_effect=AssertionError('ECHO completion forbidden')):
                result=hidden.hidden_left('tty3',dict(kind='login'),receipt,proc)
        self.assertTrue(result['ready'] and result['reader_left'] and result['shell_idle'] and result['prompt_at_cursor'])
        self.assertFalse(result['completion_uses_echo']);self.assertFalse(result['value_recorded'])

    def test_real_login_like_parent_and_readline_bash_complete_while_echo_stays_off(self):
        with LoginPTY() as f:
            with f.facts():proof=hidden.hidden_observation('tty3',dict(kind='login'),'Password:')
            self.assertTrue(proof['ready']);self.assertFalse(proof['reader_echo_enabled'])
            os.write(f.master,b'fixture-only-input\n');f.until(b'completion-fixture$ ')
            fd=os.open(f.slave_name,os.O_RDONLY|os.O_NOCTTY)
            try:self.assertFalse(termios.tcgetattr(fd)[3]&termios.ECHO)
            finally:os.close(fd)
            self.assertIsNone(f.process.poll())  # PAM-like login parent persists.
            with f.facts(),patch.object(hidden,'echo_at',side_effect=AssertionError('ECHO completion forbidden')):
                result=hidden.hidden_left('tty3',dict(kind='login'),proof['reader'])
            self.assertTrue(result['ready']);self.assertFalse(result['completion_uses_echo'])

    def test_getpass_still_foreground_never_completes_even_with_a_fake_shell_prompt(self):
        with Relay() as f:
            os.write(f.gate,b'1');f.until(PROMPT.encode());proof=f.observe()
            with physical_screen(vcsa('root@bazzite:~#')),patch.object(hidden,'echo_at',side_effect=AssertionError('ECHO completion forbidden')):
                result=hidden.hidden_left('tty3',f.expected,proof['reader'],f.model.root)
            self.assertFalse(result['ready']);self.assertFalse(result['reader_left']);self.assertEqual(f.sent,[])

    def test_wrong_reader_parent_group_session_or_extra_child_never_grants_completion(self):
        for index,key,value in ((1,'ppid',999),(1,'exe','/usr/bin/tmux'),(1,'session',1962),
                (1,'tpgid',999),(0,'exe','/usr/bin/other'),(0,'ppid',999)):
            receipt,rows,raw=q8();rows[index][key]=value
            with self.subTest(key=key),tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
                proc=Proc(folder,rows).root
                with physical_screen(raw),patch.object(hidden,'echo_at',side_effect=AssertionError('ECHO completion forbidden')):
                    result=hidden.hidden_left('tty3',dict(kind='login'),receipt,proc)
                self.assertFalse(result['ready'])
        receipt,rows,raw=q8()
        rows.append(row(3000,2926,2926,2926,1027,2926,'sleep',['sleep','1']))
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            proc=Proc(folder,rows).root
            with physical_screen(raw):result=hidden.hidden_left('tty3',dict(kind='login'),receipt,proc)
            self.assertFalse(result['ready']);self.assertFalse(result['shell_idle'])

    def test_sudo_public_handoff_is_not_completion_then_returns_to_verified_shell(self):
        from owner_console_shim import execute_hidden
        expected=hidden.sudo_reader(['/var/lib/ares/at','layout','proof'],hidden.owner_reader(['layout','proof']))
        proof=execute_hidden(hidden.source('tty4',expected,prompt='[sudo] password for ares-recovery:'))
        handoff=execute_hidden(hidden.source('tty4',expected,receipt=proof['reader'],handoff='Physically type'))
        self.assertTrue(handoff['handoff_ready'] and handoff['reader_left']);self.assertFalse(handoff['ready'])
        done=execute_hidden(hidden.source('tty4',expected,receipt=proof['reader']))
        self.assertTrue(done['ready'] and done['shell_idle']);self.assertFalse(done['completion_uses_echo'])

    def test_expected_wrong_layout_login_is_a_refusal_not_a_completion_grant(self):
        from owner_console_shim import execute_hidden
        proof=execute_hidden(hidden.source('tty4',dict(kind='login'),prompt='Password:'))
        result=execute_hidden(hidden.source('tty4',dict(kind='login'),receipt=proof['reader']),rejected=True)
        self.assertTrue(result['rejected']);self.assertFalse(result['ready']);self.assertFalse(result['shell_idle'])

    def test_owner_result_on_cursor_requires_departed_reader_and_verified_lineage(self):
        from owner_console_shim import execute_hidden
        expected=hidden.owner_reader(['login'])
        proof=execute_hidden(hidden.source('tty3',expected,prompt=PROMPT))
        command=hidden.source('tty3',expected,receipt=proof['reader'])
        refusal=hidden.source('tty3',expected,receipt=proof['reader'],timeout=1)
        for text in ('PASS login','STOP: fixture refusal'):
            with self.subTest(text=text):
                value=execute_hidden(command,raw=vcsa(text))
                self.assertTrue(value['ready'] and value['reader_left'])
                self.assertFalse(value['prompt_at_cursor'])
                value=execute_hidden(refusal,leaves=False,raw=vcsa(text))
                self.assertFalse(value['ready']);self.assertFalse(value['reader_left'])
        for text in ('PASS switch','PASS login\nstill waiting','STOP invented-format'):
            self.assertFalse(execute_hidden(refusal,raw=vcsa(text))['ready'])
        # A result line never substitutes for account-login shell authority.
        receipt,rows,_=q8()
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            proc=Proc(folder,rows).root
            with physical_screen(vcsa('PASS login')):
                self.assertFalse(hidden.hidden_left('tty3',dict(kind='login'),receipt,proc)['ready'])


if __name__=='__main__':unittest.main()
