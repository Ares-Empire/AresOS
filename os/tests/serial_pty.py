"""Unprivileged real Bash/PTY fixture. Files stay inside this worktree.

The local DrvFS cannot prove guest root/tmpfs modes. Only id/findmnt/stat and
guest private-record metadata are explicit stand-ins; byte transport, Bash,
SHA-256, acknowledgement parsing and termios use real local processes/PTYs.
"""
import contextlib
import json
import os
import pathlib
import pty
import select
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import termios
import fcntl
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'os/ci'))
import switch_vm as sw
import serial_transport as transport
from serial_console import TerminalReplies
from unittest.mock import patch


PYTHON_ADAPTER = '''import os,pathlib,stat,sys
from types import SimpleNamespace
RealPath=pathlib.Path
root=RealPath(os.environ['SERIAL_FIXTURE_ROOT'])
source=sys.argv[2]
class VirtualPath:
 def __init__(self,p):self.value=str(p)
 def real(self):
  for prefix,name in (('/var/lib/ares/records','records'),('/run/ares-owner-diagnostics','stops')):
   if self.value==prefix or self.value.startswith(prefix+'/'):return root/name/self.value[len(prefix):].lstrip('/')
  if self.value.startswith('/dev/vcsa'):return root/('vcsa'+self.value.removeprefix('/dev/vcsa'))
  return RealPath(self.value)
 def exists(self):return self.real().exists()
 def is_symlink(self):return self.real().is_symlink()
 def lstat(self):return SimpleNamespace(st_mode=(stat.S_IFDIR|0o700) if self.real().is_dir() else (stat.S_IFREG|0o600),st_uid=0)
 def glob(self,pattern):return [VirtualPath(self.value+'/'+p.relative_to(self.real()).as_posix()) for p in self.real().glob(pattern)]
 def read_text(self):return self.real().read_text()
 def read_bytes(self):return self.real().read_bytes()
 @property
 def name(self):return self.real().name
 def __str__(self):return self.value
pathlib.Path=VirtualPath
original_open=os.open
def open_tty(path,*args,**kw):
 if path in ('/dev/tty3','/dev/tty4'):path=os.environ['PHYSICAL_PTY']
 return original_open(path,*args,**kw)
os.open=open_tty
exec(compile(source,'exact-guest-source','exec'),{})
'''


class Line:
    def __init__(self, root, env, *, echo=False):
        self.root = pathlib.Path(root)
        master, slave = pty.openpty()
        self.master, self.slave_name = master, os.ttyname(slave)
        def controlling():
            os.setsid(); fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        self.process = subprocess.Popen(['bash','--noprofile','--norc','-i'],stdin=slave,stdout=slave,stderr=slave,
            preexec_fn=controlling,env=dict(env,TERM='dumb',PS1='root@bazzite:~# ',PS2='> '))
        os.close(slave); os.set_blocking(master,False)
        self.timeout, self.fault, self.limit, self.sent, self.output = .1, None, None, [], bytearray()
        self.sendall((('stty echo' if echo else 'stty -echo')+"; printf '\\nLOCAL_PTY_READY\\n'\n").encode())
        marker=b'\r\nLOCAL_PTY_READY\r\n'
        startup=self.until(marker,3)
        self.sent.clear();self.output=bytearray(startup.split(marker,1)[1])

    def settimeout(self,value):self.timeout=value

    def sendall(self,raw):
        self.sent.append(bytes(raw))
        if self.fault is not None:raw=self.fault(raw)
        if self.limit is not None:raw=raw[:self.limit]
        deadline=time.monotonic()+2
        while raw:
            assert time.monotonic()<deadline,'Local PTY input deadline'
            if select.select([], [self.master], [], .05)[1]:
                size=os.write(self.master,raw[:128]);raw=raw[size:]

    def recv(self,count):
        if not select.select([self.master],[],[],self.timeout)[0]:raise socket.timeout()
        raw=os.read(self.master,count);self.output.extend(raw);return raw

    def until(self,marker,timeout):
        out=b'';deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            try:out+=self.recv(65536)
            except socket.timeout:continue
            if marker in out:return out
        raise TimeoutError('Local PTY marker deadline')

    def close(self):
        try:os.killpg(self.process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
        self.process.wait(timeout=3);os.close(self.master)


class Fixture(contextlib.AbstractContextManager):
    def __init__(self, before=()):
        self.stack=contextlib.ExitStack()
        self.root=pathlib.Path(self.stack.enter_context(tempfile.TemporaryDirectory(dir=ROOT/'os/tests'))).resolve()
        self.evidence=self.root/'evidence';self.evidence.mkdir()
        self.stage=self.root/'stage';self.stage.mkdir()
        self.records=self.root/'records';self.records.mkdir()
        self.binary=self.root/'bin';self.binary.mkdir()
        self.stack.enter_context(patch.object(sw,'EVIDENCE',self.evidence))
        self.stack.enter_context(patch.object(transport,'STAGE_ROOT',str(self.stage)))
        self.stack.enter_context(patch.object(transport,'ACK_TIMEOUT',2))
        self.stack.enter_context(patch.object(transport,'TRANSFER_TIMEOUT',30))
        for name in before:(self.records/pathlib.PurePosixPath(name).name).write_text('{}\n')
        self.env=dict(os.environ,PATH=str(self.binary)+os.pathsep+os.environ['PATH'],SERIAL_FIXTURE_ROOT=str(self.root))
        self.shim('id','test "$*" = -u\nprintf "0\\n"\n')
        self.shim('findmnt','test "$1 $2 $3 $4 $5" = "-n -o FSTYPE -T '+str(self.stage)+'"\nprintf "tmpfs\\n"\n')
        self.shim('stat','test "$1" = -c\ntest "$2" = %u:%a\ncase "$3" in "'+str(self.stage)+'"/ares-serial-*/script) test -f "$3"; printf "0:600\\n";; "'+str(self.stage)+'"/ares-serial-*) test -d "$3"; printf "0:700\\n";; *) exit 1;; esac\n')
        mktemp=shutil.which('mktemp')
        self.shim('mktemp','test "$1" = /run/aresos-json.XXXXXX\nexec '+shlex.quote(mktemp)+' '+shlex.quote(str(self.root/'aresos-json.XXXXXX'))+'\n')
        adapter=self.root/'python-adapter.py';adapter.write_text(PYTHON_ADAPTER)
        self.shim('python3','if test "$1" = -c; then exec '+shlex.quote(sys.executable)+' '+shlex.quote(str(adapter))+' "$@"; '
            'else exec '+shlex.quote(sys.executable)+' "$@"; fi\n')
        self.physical=Line(self.root,self.env,echo=True);self.stack.callback(self.physical.close)
        self.env['PHYSICAL_PTY']=self.physical.slave_name
        self.serial=Line(self.root,self.env);self.stack.callback(self.serial.close)
        self.guest=object.__new__(sw.Guest)
        self.guest.console=self.serial;self.guest.transcript='';self.guest.buffer='';self.guest.boot_transcript=''
        self.guest.authentication_started=True;self.guest.replies=TerminalReplies();self.guest.secrets=[]
        self.guest.command_pending=False;self.guest.serial_input_epoch=0;self.guest.serial_completed_epoch=0
        self.guest.owner_input_epoch=0;self.guest.owner_layout='de';self.guest.screenshot_safe=True
        self.guest.screenshot=lambda name:None
        self.guest.keys=lambda keys:None
        self.screens()

    def shim(self,name,body):
        p=self.binary/name;p.write_text('#!/bin/bash\nset -eu\n'+body);p.chmod(0o700)

    def screens(self):
        raw=bytes([1,80,17,0])+b''.join(bytes([c,7]) for c in b'root@bazzite:~# '.ljust(80))
        for n in (3,4):(self.root/('vcsa'+str(n))).write_bytes(raw)

    def close(self):self.stack.close()
    def __exit__(self,*args):self.close()
