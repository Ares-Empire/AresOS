"""No hardware: actual login driver, prepared protocol, clocks and /proc models."""
import contextlib
import copy
import json
import pathlib
import re
import shlex
import struct
import sys
import unittest
from unittest.mock import patch,Mock,MagicMock

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_login as login
import owner_vm as vm
import serial_console
from owner_login_shim import command as prepared_command,LoginShim
from guest_shell import syntax


class Guest:
    owner_layout='de'
    owner_input_epoch=0
    screenshot_safe=True
    secrets=[]
    def __init__(self,case='pass'):
        self.case=case;self.events=[];self.key_counts=None;self.secret_keys=0;self.phase='username';self.enter_checks=0
    def keys(self,keys):
        self.events.append(('keys',tuple(keys)))
        if self.key_counts is not None:
            self.key_counts['press']+=len(keys);self.key_counts['release']+=len(keys)
        if self.phase=='password' and keys!=['ret']:self.secret_keys+=len(keys)*2
        if keys==['ret']:self.phase='password' if self.phase=='username' else 'complete'
    def command(self,name,source,**kw):
        syntax(name,source);self.events.append(('command',name,source,kw))
        if not source.startswith('python3 -B /run/ares-login-'):return ''
        parts=shlex.split(source);action=parts[3]
        if action=='begin':self.phase='username'
        if action=='clear':self.phase='public-clear'
        original=LoginShim.call
        def call(shim,op,arg=None):
            value=original(shim,op,arg)
            if op=='arm' and self.case=='budget':value.update(ready=False,reason='budget-exceeded',remaining_seconds=0)
            if op=='enter':
                self.enter_checks+=1
                if self.case=='twice' or self.case=='once' and self.enter_checks==1:
                    value.update(ready=False,reader_changed=True)
                    counts=shim.audit['counts']['hidden'];shim.audit['counts']['hidden']=dict.fromkeys(counts,0)
                    shim.audit['counts']['unknown']=counts
            return value
        with patch.object(LoginShim,'call',call):return prepared_command(self,source)
    def capture_json(self,name,source):
        syntax(name,source)
        self.events.append(('capture',name,source))
        if '# hidden-phase: left' in source:return dict(ready=True,reader_left=True)
        if '# hidden-read-diagnostics' in source:return dict(kind='hidden-read-diagnostics',value_recorded=False)
        raise AssertionError('Unmodelled login capture '+name)
    def resync_after_hidden(self,stage):return dict(status='passed')


class LoginTest(unittest.TestCase):
    def driver(self,case='pass'):
        guest=Guest(case);console=vm.Console(guest);saved=[]
        with patch.object(vm.td,'save',side_effect=lambda n,v:saved.append((n,copy.deepcopy(v)))), \
                patch.object(vm,'wait_tty'),patch.object(vm.Console,'after_hidden'), \
                patch.object(login.time,'monotonic',return_value=10.0),patch.object(vm.time,'sleep'):
            try:console.login('fixture-only-password','fixture-login');result=None
            except AssertionError as error:result=error
        return guest,saved,result

    def test_timeout_configuration_source_default_override_and_refusals(self):
        self.assertEqual(login.login_timeout('#LOGIN_TIMEOUT 60\n'),60)
        self.assertEqual(login.login_timeout('LOGIN_TIMEOUT 90 # owner choice\n'),90)
        for text in ('LOGIN_TIMEOUT 0','LOGIN_TIMEOUT -1','LOGIN_TIMEOUT 1.5',
                     'LOGIN_TIMEOUT 60\nLOGIN_TIMEOUT 60','LOGIN_TIMEOUT 601','LOGIN_TIMEOUT'):
            with self.subTest(text=text),self.assertRaises(AssertionError):login.login_timeout(text)

    def test_actual_driver_prepares_before_username_and_completes_inside_half_timeout(self):
        guest,saved,result=self.driver();self.assertIsNone(result)
        first_key=next(i for i,x in enumerate(guest.events) if x[0]=='keys' and x[1]==('a',))
        setup=next(i for i,x in enumerate(guest.events) if x[0]=='command' and x[1].endswith('login-observers-prepare'))
        self.assertLess(setup,first_key)
        self.assertTrue(any(n.endswith('-login-timing') and v['within_half_timeout'] for n,v in saved))
        for item in guest.events:
            if item[0]=='command':self.assertNotIn('fixture-only-password',item[2])

    def test_budget_exceeded_before_secret_never_types_it(self):
        guest,saved,result=self.driver('budget');self.assertIsInstance(result,AssertionError)
        self.assertEqual(guest.secret_keys,0)
        self.assertFalse(any(v.get('secret_tainted') for n,v in saved if isinstance(v,dict)))

    def test_replaced_reader_line_kill_fresh_prompt_and_one_whole_restart(self):
        guest,saved,result=self.driver('once');self.assertIsNone(result)
        self.assertEqual(sum(x[:2]==('keys',('ctrl','u')) for x in guest.events),1)
        self.assertEqual(sum(x[:2]==('keys',('ctrl','d')) for x in guest.events),1)
        restart=[v for n,v in saved if '-login-reader-restart-' in n]
        self.assertEqual(len(restart),1);self.assertTrue(restart[0]['fresh']['fresh_login_prompt'])
        taint=[v for n,v in saved if n=='owner-login-visual-taint']
        self.assertTrue(taint and all(v['private_only'] and v['never_commit'] and not v['value_recorded'] for v in taint))

    def test_second_reader_replacement_stops_without_password_enter(self):
        guest,saved,result=self.driver('twice');self.assertIsInstance(result,AssertionError)
        self.assertIn('Second login reader replacement',str(result))
        # Only the two visible usernames get Return; neither secret does.
        self.assertEqual(sum(x[:2]==('keys',('ret',)) for x in guest.events),2)
        self.assertEqual(len([n for n,v in saved if '-login-reader-restart-' in n]),2)

    def test_q14_shape_is_identity_refusal_not_event_loss(self):
        fixture=json.loads((ROOT/'os/manifest/ci/14/14zr-qualification-stop/hidden-reader-stop.json').read_text())
        before,after=fixture['before'],fixture['after'];self.assertTrue(before['ready']);self.assertFalse(after['ready'])
        state=dict(timeout=60,username_at=0,tty='tty4',reader=dict(pid=13852,start='fixture',exe='/usr/bin/login'))
        with patch.object(login,'input_guard',return_value=after),patch.object(login,'login_foreground',return_value=dict(pid=20186,start='replacement',exe='/usr/bin/agetty')),patch.object(login.time,'monotonic',return_value=20):
            value=login.login_guard(state)
        self.assertTrue(value['reader_changed']);self.assertFalse(value['ready'])
        self.assertEqual(fixture['pre_enter_stop']['attempts'][0]['comparison']['received_events'],64)

    def test_remaining_time_is_checked_again_immediately_before_secret(self):
        state=dict(timeout=60,username_at=0,tty='tty3',reader=dict(pid=20,start='fixture',exe='/usr/bin/login'))
        row=dict(pid=20,start='fixture',exe='/usr/bin/login')
        with patch.object(login,'input_guard',return_value=dict(ready=True)),patch.object(login,'login_foreground',return_value=row):
            with patch.object(login.time,'monotonic',return_value=17):self.assertTrue(login.login_guard(state,12)['ready'])
            with patch.object(login.time,'monotonic',return_value=19):self.assertFalse(login.login_guard(state,12)['ready'])

    def test_prepared_source_compiles_and_inline_rpc_keeps_checksum_protocol(self):
        source=login.guest_source();compile(source,'actual-prepared-program','exec')
        self.assertIn('count_events(data, counts[kind])',source)
        from owner_login_shim import frame
        value=dict(ready=True,counts_only=True)
        import base64,hashlib,io
        tail='raw=json.dumps(value).encode()'+source.rsplit('raw=json.dumps(value).encode()',1)[1]
        output=io.StringIO()
        with contextlib.redirect_stdout(output):
            exec(compile(tail,'actual-prepared-export','exec'),dict(value=value,json=json,base64=base64,hashlib=hashlib))
        self.assertEqual(json.loads(serial_console.decode_export(output.getvalue())),value)
        self.assertEqual(json.loads(serial_console.decode_export(frame(value))),value)
        bad=re.sub(r'(?<=ARESOS_EXPORT_SHA256 )[0-9a-f]{64}','0'*64,frame(value))
        with self.assertRaisesRegex(ValueError,'checksum'):serial_console.decode_export(bad)

    def test_visibility_classification_uses_identity_and_reader_echo(self):
        state=dict(tty='tty4',reader=dict(pid=13852,start='old',exe='/usr/bin/login'))
        row=dict(pid=13852,start='old',exe='/usr/bin/login',comm='login',tty=1028)
        with patch.object(login,'login_foreground',return_value=row),patch.object(login,'echo_at',return_value=False):
            self.assertEqual(login.login_visibility(state),'hidden')
        with patch.object(login,'login_foreground',return_value=dict(row,pid=20186)):
            self.assertEqual(login.login_visibility(state),'non_hidden')
        with patch.object(login,'login_foreground',side_effect=OSError):self.assertEqual(login.login_visibility(state),'unknown')

    def test_visibility_counter_counts_only_with_unknown_transition_and_syn_drop(self):
        counts={k:dict(press=0,release=0,repeat=0,syn_dropped=0) for k in ('hidden','non_hidden','unknown')}
        data=b''.join(struct.pack('@llHHi',0,0,1,30,v) for v in (1,0))
        login.login_audit_batch(data,'hidden','hidden',counts)
        login.login_audit_batch(data,'hidden','non_hidden',counts)
        login.login_audit_batch(data,'non_hidden','non_hidden',counts)
        login.login_audit_batch(struct.pack('@llHHi',0,0,0,3,0),'unknown','unknown',counts)
        for kind in counts:self.assertEqual((counts[kind]['press'],counts[kind]['release']),(1,1))
        self.assertEqual(counts['unknown']['syn_dropped'],1)
        self.assertEqual(set(counts['hidden']),{'press','release','repeat','syn_dropped'})
        self.assertTrue(login.login_exposure(dict(counts=counts,complete=True))['secret_tainted'])
        counts={k:dict(press=0,release=0,repeat=0,syn_dropped=0) for k in counts}
        counts['hidden']['syn_dropped']=1
        self.assertTrue(login.login_exposure(dict(counts=counts,complete=True))['secret_tainted'])
        counts['hidden']['syn_dropped']=0
        self.assertTrue(login.login_exposure(dict(counts=counts,complete=False))['secret_tainted'])
        self.assertFalse(login.login_exposure(dict(counts=counts,complete=True))['secret_tainted'])

    def test_old_login_is_not_a_fresh_pre_username_reader(self):
        with patch.object(login,'login_foreground',return_value=dict(comm='login',exe='/usr/bin/login')), \
                patch.object(login.os,'open') as opened,self.assertRaisesRegex(AssertionError,'Old login alarm'):
            login.login_public('tty4',fresh=True)
        opened.assert_not_called()

    def test_unknown_public_reader_refuses_before_line_kill_or_io(self):
        for row in (dict(comm='bash',exe='/usr/bin/bash'),dict(comm='agetty',exe='/tmp/agetty')):
            with patch.object(login,'login_foreground',return_value=row),patch.object(login.os,'open') as opened, self.assertRaisesRegex(AssertionError,'Unknown public reader'):
                login.login_public('tty4')
            opened.assert_not_called()

    def test_secret_taint_marks_screenshots_private_without_breaking_required_ocr(self):
        guest=object.__new__(vm.Guest);guest.monitor=Mock()
        with patch.object(vm.Guest,'run_secret_tainted',True),patch.object(vm.td,'save') as save, \
                patch.object(vm.td.Guest,'screenshot',autospec=True) as capture:
            guest.screenshot('after-secret-reader-change')
        capture.assert_called_once_with(guest,'after-secret-reader-change')
        self.assertTrue(save.call_args.args[1]['secret_tainted'])
        self.assertTrue(save.call_args.args[1]['never_commit'])
        self.assertTrue(save.call_args.args[1]['required_ocr_capture_preserved'])

    def test_prepared_root_refuses_non_root_shared_or_symlink_paths(self):
        from types import SimpleNamespace
        root=MagicMock();root.__str__.return_value='/run/ares-login-'+('a'*16);root.is_symlink.return_value=False
        for uid,mode,link in ((1000,0o40700,False),(0,0o40755,False),(0,0o40700,True),(0,0o100700,False)):
            root.lstat.return_value=SimpleNamespace(st_uid=uid,st_mode=mode);root.is_symlink.return_value=link
            with self.assertRaises(AssertionError):login.login_root(root)
        root.lstat.return_value=SimpleNamespace(st_uid=0,st_mode=0o40700);root.is_symlink.return_value=False
        login.login_root(root)


if __name__=='__main__':unittest.main()
