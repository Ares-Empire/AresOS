"""No device/privilege access: exact collector over modelled proc and getter ioctls."""
import ast
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import termios
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_hidden as hidden
import owner_read_diagnostics as diagnostics
import owner_vm as vm
from test_owner_hidden import Proc, nested


def execute_diagnostics(source, fail_ioctl=False, disappear=False, wchan='n_tty_read'):
    import fcntl
    call, = [n for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name) and n.func.id == 'collect']
    tty, expected, receipt = [ast.literal_eval(n) for n in call.args]
    rows = nested(receipt['physical'], 136 * 256 + 2, receipt['pid'], expected.get('argv', []))
    with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as directory:
        proc = Proc(directory, rows).root
        for r in rows:
            (proc / str(r['pid']) / 'wchan').write_text(wchan+'\n')
            (proc / str(r['pid']) / 'syscall').write_text('0 0xdeadbeef NEVER_EXPORT_ARGUMENTS 0 0\n')
        if disappear:
            (proc / str(receipt['pid']) / 'syscall').unlink()
        read_text, read_bytes, glob, readlink = pathlib.Path.read_text, pathlib.Path.read_bytes, pathlib.Path.glob, os.readlink
        def mapped(p):
            p = pathlib.Path(p)
            return proc / p.relative_to('/proc') if str(p).startswith('/proc/') else p
        devices = {}
        def open_tty(path, flags):
            assert flags == os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK
            path = str(path)
            if path in ('/dev/tty3','/dev/tty4'): device = os.makedev(4,int(path[-1]))
            else:
                number = int(path.removeprefix('/dev/pts/'))
                device = os.makedev(136 + number // 256, number % 256)
            devices[len(devices) + 100] = device
            return max(devices)
        def ioctl(fd, request, value, mutate):
            assert fd in devices and mutate
            assert request in (termios.TIOCINQ, termios.TIOCOUTQ, 0x4b44, 0x4b31, 0x4b64)
            if fail_ioctl: raise PermissionError(13, 'do not export exception text')
            value[0] = 7 if request == termios.TIOCINQ else 3
            return 0
        def text(p):
            return tty + '\n' if str(p) == '/sys/class/tty/tty0/active' else read_text(mapped(p))
        output = io.StringIO()
        with contextlib.ExitStack() as stack:
            for obj, name, value in ((pathlib.Path,'read_text',text), (pathlib.Path,'read_bytes',lambda p:read_bytes(mapped(p))),
                (pathlib.Path,'glob',lambda p,pattern:glob(proc if str(p)=='/proc' else p,pattern)),
                (os,'readlink',lambda p:readlink(mapped(p))), (os,'open',open_tty), (os,'close',lambda fd:None),
                (os,'fstat',lambda fd:SimpleNamespace(st_rdev=devices[fd])), (fcntl,'ioctl',ioctl),
                (termios,'tcgetattr',lambda fd:[termios.ICRNL|termios.IXON,0,0,termios.ICANON|termios.ISIG|termios.IEXTEN,0,0,[]]),
                (subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='Sudo version 1.9.17p2\n'))):
                stack.enter_context(patch.object(obj,name,value))
            with contextlib.redirect_stdout(output): exec(compile(source,'modelled-hidden-read-diagnostics','exec'), {})
        return json.loads(output.getvalue())


def fixture_source():
    rows = nested(4 * 256 + 3, 136 * 256 + 2, 40, hidden.owner_reader(['login'])['argv'])
    receipt = dict(pid=40, physical=4 * 256 + 3, origin_chain=rows)
    return diagnostics.source('tty3', hidden.owner_reader(['login']), receipt)


class DiagnosticsTest(unittest.TestCase):
    def test_normal_kernel_symbol_suffixes_pass_and_arguments_stay_refused(self):
        for name in ('do_poll.constprop.0','__x64_sys_ppoll.isra.0','0'):
            result=execute_diagnostics(fixture_source(),wchan=name)
            self.assertTrue(all(r.get('wchan')==name for r in result['processes']))
        result=execute_diagnostics(fixture_source(),wchan='do_poll ARGUMENTS_MUST_NOT_ESCAPE')
        self.assertTrue(all('wchan_error' in r for r in result['processes']))
        self.assertNotIn('ARGUMENTS_MUST_NOT_ESCAPE',json.dumps(result))

    def test_chain_queues_flags_versions_and_syscall_numbers_only(self):
        result = execute_diagnostics(fixture_source())
        self.assertEqual(result['active_vt'], 'tty3')
        self.assertEqual(result['sudo_version'], '1.9.17p2')
        self.assertEqual({r['path'] for r in result['terminals']}, {'/dev/tty3','/dev/pts/200','/dev/pts/2'})
        self.assertTrue(all(r['TIOCINQ']==7 and r['TIOCOUTQ']==3 for r in result['terminals']))
        self.assertTrue(all(r['termios']['ICANON'] and not r['termios']['ECHO'] for r in result['terminals']))
        self.assertTrue(all(r['syscall_number']==0 and r['wchan']=='n_tty_read' for r in result['processes']))
        self.assertEqual(len(result['processes']),7)
        for secret in ('NEVER_EXPORT_ARGUMENTS','deadbeef','argv','cmdline'):
            self.assertNotIn(secret,json.dumps(result))
        fourth=execute_diagnostics(fixture_source().replace("'tty3'","'tty4'").replace('1027','1028'))
        self.assertEqual({r['path'] for r in fourth['terminals']}, {'/dev/tty3','/dev/tty4','/dev/pts/200','/dev/pts/2'})
        self.assertIn('KDGKBMODE',next(r for r in fourth['terminals'] if r['path']=='/dev/tty3'))

    def test_ioctl_refusal_records_errno_and_closes_without_reading_queue(self):
        result = execute_diagnostics(fixture_source(), fail_ioctl=True)
        self.assertTrue(all(r['error']==dict(kind='PermissionError',errno=13) for r in result['terminals']))
        self.assertNotIn('do not export',json.dumps(result))

    def test_disappeared_process_records_failure_without_losing_other_diagnostics(self):
        result = execute_diagnostics(fixture_source(), disappear=True)
        self.assertEqual(next(r for r in result['processes'] if r['pid']==40)['syscall_error']['errno'],2)
        self.assertEqual(len(result['terminals']),3)

    def test_counts_are_actual_sent_chords_and_press_release_events(self):
        class Guest:
            owner_layout='de'
            def keys(self, keys): pass
        counts = dict(key_event_count=0,key_chord_count=0,last_key_was_ret=False)
        with patch.object(vm.time,'sleep'): vm.type_text(Guest(),'aA_\n',counts=counts)
        self.assertEqual(counts,dict(key_event_count=12,key_chord_count=4,last_key_was_ret=True))

    def test_token_deadline_only_and_diagnostics_every_timeout(self):
        import base64
        import shlex
        from test_owner_hidden import vcsa
        for expected, token, seconds in ((hidden.owner_reader(['login']),True,180),
                (hidden.owner_reader(['verify']),False,840),(dict(kind='login'),False,60)):
            with self.subTest(expected=expected):
                guest = Mock(owner_input_epoch=0,owner_layout='de')
                console = vm.Console(guest)
                console.pending_hidden = dict(stage='fixture',expected=expected,reader={},epoch=0,token=token)
                deadlines=[]
                def capture(name, source):
                    if name.endswith('-key-counter-start'): return dict(status='ready',counts_only=True,path='/run/ares-input-fixture1')
                    if name.endswith('-key-counter-stop'): return dict(complete=True,counts=dict(press=6,release=6,repeat=0,syn_dropped=0))
                    if '-diagnostics-' in name: return dict(kind='hidden-read-diagnostics')
                    words=shlex.split(source)
                    script=words[words.index('python3')+2]
                    assignment=next(n for n in ast.walk(ast.parse(script)) if isinstance(n,ast.Assign)
                        and any(isinstance(t,ast.Name) and t.id=='deadline' for t in n.targets))
                    deadlines.append(ast.literal_eval(assignment.value.right))
                    return dict(ready=False,raw=base64.b64encode(vcsa('Read-only token (hidden):')).decode())
                guest.capture_json.side_effect=capture
                with patch.object(vm.time,'sleep'), patch.object(vm,'retain_vcsa'), patch.object(vm.td,'save') as saved:
                    with self.assertRaisesRegex(AssertionError,'secret will not be retyped'):
                        console.send_hidden('aA_')
                self.assertEqual(deadlines,[seconds])
                self.assertEqual(guest.keys.call_count,4)
                phases=[call.args[0] for call in saved.call_args_list if '-diagnostics-' in call.args[0]]
                self.assertEqual(phases,['fixture-diagnostics-completion-start','fixture-diagnostics-completion-timeout']
                    if token else ['fixture-diagnostics-completion-timeout'])
                record=next(call.args[1] for call in saved.call_args_list if '-diagnostics-' in call.args[0])
                self.assertEqual(record['typed']['length'],3)
                self.assertTrue(record['typed']['last_key_was_ret'])
                self.assertNotIn('aA_',json.dumps(record))


if __name__ == '__main__': unittest.main()
