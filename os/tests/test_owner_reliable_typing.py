"""No host keyboard access: model events, actual guest predicates and owned PTYs."""
import ast
import contextlib
import copy
import json
import os
import pathlib
import pty
import select
import shlex
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from unittest.mock import Mock,patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_vm as vm
import owner_hidden as hidden
import owner_key_counter as counter
from guest_shell import syntax
from owner_console_shim import execute_screen
from test_owner_hidden import vcsa,Proc,nested


def execute_guard(source, *,canonical=True,kill=21,syscall=0,state='S'):
    """Run the composed /proc/termios proof with explicit model facts."""
    import io
    from types import SimpleNamespace
    call,=[n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='input_guard']
    tty,expected,receipt=[ast.literal_eval(n) for n in call.args[:3]]
    from owner_console_shim import hidden_rows
    physical=4*256+int(tty[3:]);rows,_=hidden_rows(physical,expected,'ready',leaves=False)
    rows[-1]['state']=state
    with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
        proc=Proc(folder,rows).root
        for row in rows:(proc/str(row['pid'])/'syscall').write_text(str(syscall)+' 0x0 0x0 0x0')
        read_text,read_bytes,glob,readlink=pathlib.Path.read_text,pathlib.Path.read_bytes,pathlib.Path.glob,os.readlink
        def mapped(p):return proc/p.relative_to('/proc') if str(p).startswith('/proc/') else p
        output=io.StringIO()
        attrs=[0,0,0,termios.ICANON if canonical else 0,0,0,[b'\0']*32];attrs[6][termios.VKILL]=bytes([kill])
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(pathlib.Path,'read_text',lambda p:read_text(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path,'read_bytes',lambda p:read_bytes(mapped(p))))
            stack.enter_context(patch.object(pathlib.Path,'glob',lambda p,pattern:glob(proc if str(p)=='/proc' else p,pattern)))
            stack.enter_context(patch.object(os,'readlink',lambda p:readlink(mapped(pathlib.Path(p)))))
            stack.enter_context(patch.object(os,'open',return_value=123));stack.enter_context(patch.object(os,'close'))
            code=receipt['tty'];device=os.makedev((code>>8)&0xfff,(code&255)|((code>>12)&0xfff00))
            stack.enter_context(patch.object(os,'fstat',return_value=SimpleNamespace(st_rdev=device)))
            stack.enter_context(patch.object(termios,'tcgetattr',return_value=attrs))
            clock=Mock(now=0.0)
            stack.enter_context(patch.object(time,'monotonic',side_effect=lambda:clock.now))
            stack.enter_context(patch.object(time,'sleep',side_effect=lambda seconds:setattr(clock,'now',clock.now+seconds)))
            with contextlib.redirect_stdout(output):exec(compile(source,'actual-hidden-input-guard','exec'),{})
        return json.loads(output.getvalue())


class Driver:
    owner_layout='de';owner_input_epoch=0
    def __init__(self,case='pass'):
        self.case=case;self.events=[];self.counts=dict(press=0,release=0,repeat=0,syn_dropped=0)
        self.samples=0;self.enters=0;self.clears=0;self.proven=False;self.echo=None;self.unicode_data=None
    def keys(self,keys):
        if keys==['ret']:
            assert self.proven, 'Test observed unverified Enter'
            self.enters+=1
            if self.case=='bad-return':self.counts['syn_dropped']+=1
        if keys==['ctrl','u']:
            assert self.enters==0, 'Test observed clear after Enter'
            self.clears+=1
        self.events.append(('keys',tuple(keys)))
        self.counts['press']+=len(keys);self.counts['release']+=len(keys)
    def resync_after_hidden(self,stage):return dict(status='passed')
    def capture_json(self,name,source):
        syntax(name,source);self.events.append(('capture',name))
        if '# visible-echo' in source:
            words=shlex.split(source);script=words[words.index('python3')+2]
            value,=[ast.literal_eval(n.args[0]) for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Call)
                and isinstance(n.func,ast.Attribute) and n.func.attr=='endswith']
            return execute_screen(script,vcsa(self.echo if self.echo is not None else 'root# '+value),self.unicode_data)
        if '# hidden-input-guard' in source:
            return dict(ready=not(self.case=='bad-clear' and name.endswith('after-clear')),canonical=True,
                echo_enabled=False,vkill=21,syscall_number=0)
        if '# hidden-key-counter' in source:
            if name.endswith('-start'):return dict(status='ready',counts_only=True,path='/run/ares-input-fixture1')
            if '-sample-' in name:
                self.samples+=1
                if self.case in ('repeat','second','bad-clear') and self.samples==1:self.counts['repeat']+=1
                if self.case=='second' and self.samples==3:self.counts['repeat']+=1
                if self.case=='drop' and self.samples==1:self.counts['syn_dropped']+=1
            return dict(status='passed',complete=self.counts['syn_dropped']==0,keys_released=True,
                counts=dict(self.counts),counts_only=True,codes_recorded=False,values_recorded=False)
        if '# hidden-read-diagnostics' in source:return dict(kind='hidden-read-diagnostics')
        if '# hidden-phase: left' in source:return dict(ready=True,reader_left=True)
        raise AssertionError('Unmodelled capture '+name)


class ReliableTypingTest(unittest.TestCase):
    def run_hidden(self,case='pass',value='aa',chunked=False,token=True):
        guest=Driver(case);console=vm.Console(guest)
        console.pending_hidden=dict(stage='fixture',expected=hidden.owner_reader(['login']),reader={},epoch=0,token=token)
        saved=[]
        def save(name,value):
            saved.append((name,copy.deepcopy(value)))
            if name.endswith('-pre-enter-proof') and value['status']=='passed':guest.proven=True
        with patch.object(vm.td,'save',side_effect=save),patch.object(vm.time,'sleep'):
            try:result=console.send_hidden(value,chunk_token=chunked)
            except AssertionError as error:result=error
        return guest,console,saved,result

    def test_short_holds_and_at_least_120_ms_gap_for_every_chord(self):
        guest=object.__new__(vm.Guest);guest.monitor=Mock();events=[]
        guest.monitor.command.side_effect=lambda command,args:events.append((command,args['hold-time']))
        with patch.object(vm.time,'sleep',side_effect=lambda gap:events.append(('gap',gap))):
            guest.keys(['a']);guest.keys(['shift','b']);guest.keys(['ret'])
        self.assertEqual(events,[('send-key',30),('gap',.12)]*3)

    def test_verified_value_is_the_only_path_to_single_enter(self):
        guest,console,saved,result=self.run_hidden()
        self.assertIsInstance(result,dict);self.assertTrue(result['ready'])
        self.assertEqual((guest.enters,guest.clears),(1,0));self.assertTrue(console.last_hidden['key_comparison']['matches'])
        proof=next(v for n,v in saved if n.endswith('-pre-enter-proof') and v['status']=='passed')
        self.assertFalse(proof['enter_sent']);self.assertFalse(proof['attempts'][0]['sent']['last_key_was_ret'])

    def test_repeat_requires_verified_canonical_clear_and_one_retype(self):
        guest,console,saved,result=self.run_hidden('repeat')
        self.assertIsInstance(result,dict);self.assertEqual((guest.enters,guest.clears),(1,1))
        self.assertEqual(len(console.last_hidden['attempts']),2)
        self.assertTrue(console.last_hidden['clear_proof']['ready'])
        self.assertTrue(console.last_hidden['key_comparison']['matches'])
        self.assertEqual(console.last_hidden['received_keys']['counts']['repeat'],0)
        self.assertEqual(console.last_hidden['received_keys']['whole_window_counts']['repeat'],1)

    def test_second_bad_value_stops_without_enter_or_another_clear(self):
        guest,console,saved,result=self.run_hidden('second')
        self.assertIsInstance(result,AssertionError);self.assertIn('Second hidden-value',str(result))
        self.assertEqual((guest.enters,guest.clears),(0,1));self.assertEqual(len(console.last_hidden['attempts']),2)

    def test_syn_dropped_stops_without_enter_or_retype(self):
        guest,console,saved,result=self.run_hidden('drop')
        self.assertIsInstance(result,AssertionError);self.assertEqual((guest.enters,guest.clears),(0,0))

    def test_unproved_clear_stops_before_retype_or_enter(self):
        guest,console,saved,result=self.run_hidden('bad-clear')
        self.assertIsInstance(result,AssertionError);self.assertEqual((guest.enters,guest.clears),(0,1))
        self.assertEqual(guest.counts['press'],4)  # Two value keys, then Ctrl-U; no second value.

    def test_long_chunked_value_is_verified_before_return(self):
        guest,console,saved,result=self.run_hidden(value='a'*377,chunked=True)
        self.assertIsInstance(result,dict);self.assertEqual(guest.enters,1)
        self.assertEqual(console.last_hidden['counts']['key_chord_count'],378)
        self.assertTrue(console.last_hidden['key_comparison']['matches'])

    def test_visible_echo_uses_cursor_line_and_withholds_enter_on_corruption(self):
        guest=Driver();guest.echo='root# /var/lib/ares/at login\nroot# /var/lib/ares/aatt login'
        with patch.object(vm.td,'save'),self.assertRaisesRegex(AssertionError,'Enter withheld'):
            vm.Console(guest).visible('/var/lib/ares/at login\n')
        self.assertEqual(guest.enters,0)

    def test_visible_echo_matches_before_enter(self):
        guest=Driver();guest.proven=True
        with patch.object(vm.td,'save'):vm.Console(guest).visible('/var/lib/ares/at login\n')
        self.assertEqual(guest.enters,1)

    def test_unicode_echo_checks_codepoints_instead_of_font_slots(self):
        import struct
        guest=Driver();guest.proven=True;guest.echo='root# yz-/!\x81'
        raw=vcsa('root# yz-/!ü');guest.unicode_data=struct.pack('='+'I'*len(raw[4::2]),*raw[4::2])
        with patch.object(vm.td,'save'):vm.Console(guest).visible('yz-/!ü\n')
        self.assertEqual(guest.enters,1)
        guest.enters=0;guest.unicode_data=b'bad-size'
        with patch.object(vm.td,'save'),self.assertRaisesRegex(AssertionError,'Unicode console size'):
            vm.Console(guest).visible('yz-/!ü\n')
        self.assertEqual(guest.enters,0)

    def test_passwords_use_the_same_pre_enter_counter(self):
        guest,console,saved,result=self.run_hidden(token=False)
        self.assertIsInstance(result,dict);self.assertEqual(guest.enters,1)
        self.assertTrue(any(name.endswith('-key-counter-result') for name,value in saved))

    def test_post_enter_drop_never_clears_or_retypes(self):
        guest,console,saved,result=self.run_hidden('bad-return')
        self.assertIsInstance(result,AssertionError);self.assertIn('no post-Enter retry',str(result))
        self.assertEqual((guest.enters,guest.clears),(1,0))

    def test_hidden_line_break_is_refused_before_input(self):
        guest,console,saved,result=self.run_hidden(value='public\nfixture')
        self.assertIsInstance(result,AssertionError);self.assertEqual(guest.events,[])

    def test_actual_guard_accepts_only_unchanged_canonical_reader_in_read(self):
        rows=nested(1027,136*256+2,40,hidden.owner_reader(['login'])['argv'])
        # Match the Proc fixture's actual executable symlink and start tick.
        for row in rows:row.update(start='12345',exe=row.get('exe','/usr/bin/'+row['comm']))
        receipt=dict(hidden.identity(rows[-1]),physical=1027,tty_path='/dev/pts/2',origin_chain=[hidden.identity(r) for r in rows[1:]])
        source=hidden.guard_source('tty3',hidden.owner_reader(['login']),receipt,for_clear=True)
        self.assertTrue(execute_guard(source)['ready'])
        for change in (dict(canonical=False),dict(kill=3),dict(syscall=1),dict(state='R')):
            self.assertFalse(execute_guard(source,**change)['ready'])
        normal=hidden.guard_source('tty3',hidden.owner_reader(['login']),receipt)
        self.assertTrue(execute_guard(normal,canonical=False)['ready'])

    def test_real_canonical_getpass_ctrl_u_discards_previous_value_before_enter(self):
        master,slave=pty.openpty()
        def controlling():
            import fcntl
            os.setsid();fcntl.ioctl(0,termios.TIOCSCTTY,0)
        code="import getpass; value=getpass.getpass('Value:'); assert value=='replacement'; print('VALUE_MATCHED')"
        process=subprocess.Popen([sys.executable,'-c',code],stdin=slave,stdout=slave,stderr=slave,preexec_fn=controlling)
        try:
            output=b'';deadline=time.monotonic()+3
            while b'Value:' not in output and time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:output+=os.read(master,4096)
            self.assertIn(b'Value:',output)
            attrs=termios.tcgetattr(slave)
            self.assertTrue(attrs[3]&termios.ICANON);self.assertFalse(attrs[3]&termios.ECHO)
            self.assertEqual(attrs[6][termios.VKILL],b'\x15')
            os.write(master,b'corrupted');os.write(master,b'\x15');time.sleep(.1)
            self.assertIsNone(process.poll())
            os.write(master,b'replacement\n')
            while process.poll() is None and time.monotonic()<deadline:
                if select.select([master],[],[],.1)[0]:output+=os.read(master,4096)
            self.assertEqual(process.wait(timeout=2),0)
            self.assertNotIn(b'corrupted',output);self.assertNotIn(b'replacement',output)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=2)
            os.close(master);os.close(slave)


if __name__=='__main__':unittest.main()
