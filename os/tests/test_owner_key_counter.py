"""Modelled evdev bytes and owned pipes only; never open a host input device."""
import contextlib
import json
import os
import pathlib
import struct
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'os/ci'))
import owner_key_counter as counter
import owner_vm as vm


def event(kind,code,value):return struct.pack('@llHHi',0,0,kind,code,value)


class KeyCounterTest(unittest.TestCase):
    def test_press_release_repeat_counts_without_codes_or_values(self):
        counts=dict(press=0,release=0,repeat=0,syn_dropped=0)
        counter.count_events(event(1,30,1)+event(1,30,2)+event(1,30,0)+event(4,4,999),counts)
        self.assertEqual(counts,dict(press=1,release=1,repeat=1,syn_dropped=0))
        self.assertEqual(set(counts),{'press','release','repeat','syn_dropped'})

    def test_syn_dropped_discards_until_report_and_never_proves_completeness(self):
        counts=dict(press=0,release=0,repeat=0,syn_dropped=0)
        dropping=counter.count_events(event(0,3,0)+event(1,30,1),counts)
        self.assertTrue(dropping)
        self.assertFalse(counter.count_events(event(1,30,0)+event(0,0,0)+event(1,30,1)+event(1,30,0),counts,dropping))
        self.assertEqual(counts,dict(press=1,release=1,repeat=0,syn_dropped=1))
        self.assertFalse(counter.compare(dict(complete=False,counts=counts),dict(key_event_count=2))['matches'])

    def test_short_or_unknown_events_refuse_without_exporting_contents(self):
        for data in (b'x',event(1,30,99)):
            with self.assertRaises(AssertionError):counter.count_events(data,dict(press=0,release=0,repeat=0,syn_dropped=0))

    def test_keyboard_selection_refuses_missing_multiple_or_wrong_capabilities(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            root=pathlib.Path(folder)
            def add(number,bits):
                p=root/('event'+str(number))/'device';(p/'id').mkdir(parents=True);(p/'capabilities').mkdir()
                (p/'name').write_text('AT Translated Set 2 keyboard\n')
                for name,value in (('bustype','0011'),('vendor','0001'),('product','0001')):(p/'id'/name).write_text(value+'\n')
                (p/'capabilities/key').write_text(hex(bits)[2:]+'\n')
            with self.assertRaisesRegex(AssertionError,'unique'):counter.keyboard(root)
            add(5,sum(1<<n for n in (28,30,42,44)))
            self.assertEqual(counter.keyboard(root),'/dev/input/event5')
            add(6,sum(1<<n for n in (28,30,42,44)))
            with self.assertRaisesRegex(AssertionError,'unique'):counter.keyboard(root)
            (root/'event6/device/capabilities/key').write_text('0')
            with self.assertRaisesRegex(AssertionError,'capabilities'):counter.keyboard(root)

    def test_getter_ioctls_only_repeat_settings_and_pressed_keys_refusal(self):
        import fcntl
        calls=[]
        def ioctl(fd,request,data,mutate):
            calls.append(request)
            if request==0x80084502:data[:]=__import__('array').array('H',[0x11,1,1,1])
            elif request==0x80084503:data[:]=__import__('array').array('I',[250,33])
            else:self.assertEqual(request,0x80604518)
        with patch.object(fcntl,'ioctl',side_effect=ioctl):
            self.assertEqual(counter.settings(123),dict(delay_ms=250,period_ms=33))
        self.assertEqual(calls,[0x80084502,0x80084503,0x80604518])
        def held(fd,request,data,mutate):
            ioctl(fd,request,data,mutate)
            if request==0x80604518:data[0]=1
        with patch.object(fcntl,'ioctl',side_effect=held),self.assertRaisesRegex(AssertionError,'pressed'):counter.settings(123)

    def test_observer_consumes_after_ready_and_publishes_only_counts(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            root=pathlib.Path(folder);incoming,writer=os.pipe()
            with patch.object(counter,'released',return_value=True):
                worker=threading.Thread(target=counter.observe,args=(incoming,root,dict(delay_ms=250,period_ms=33),3))
                worker.start()
                deadline=time.monotonic()+2
                while not (root/'ready.json').exists() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue((root/'ready.json').exists())
                os.write(writer,event(1,30,1)+event(1,30,0));(root/'stop').touch()
                worker.join(4);os.close(writer)
            self.assertFalse(worker.is_alive())
            result=json.loads((root/'result.json').read_text())
            self.assertTrue(result['complete']);self.assertEqual(result['counts']['press'],1)
            self.assertFalse(result['codes_recorded']);self.assertFalse(result['values_recorded'])
            self.assertEqual({p.name for p in root.iterdir()},{'ready.json','stop','result.json'})

    def test_checkpoint_waits_for_key_release_and_keeps_whole_window(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as folder:
            root=pathlib.Path(folder);incoming,writer=os.pipe();up=threading.Event()
            with patch.object(counter,'released',side_effect=lambda fd:up.is_set()),patch.object(counter,'private_root'):
                worker=threading.Thread(target=counter.observe,args=(incoming,root,dict(delay_ms=250,period_ms=33),5))
                worker.start();deadline=time.monotonic()+2
                while not (root/'ready.json').exists() and time.monotonic()<deadline:time.sleep(.01)
                os.write(writer,event(1,30,1)+event(1,30,0));(root/'sample-1.request').touch()
                time.sleep(.6);self.assertFalse((root/'sample-1.json').exists())
                up.set();deadline=time.monotonic()+2
                while not (root/'sample-1.json').exists() and time.monotonic()<deadline:time.sleep(.01)
                first=json.loads((root/'sample-1.json').read_text());self.assertTrue(first['keys_released'])
                self.assertEqual(first['counts']['press'],1)
                os.write(writer,event(1,28,1)+event(1,28,0))
                final=counter.finish(dict(path=str(root),device='/dev/input/fixture',pid=1))
                worker.join(2);os.close(writer)
                self.assertTrue(final['complete']);self.assertEqual(final['counts']['press'],2)
                self.assertEqual(first['counts']['press'],1);self.assertFalse(root.exists())

    def test_chunk_schedule_withholds_return_and_pauses_between_and_after_chunks(self):
        calls=[]
        with patch.object(vm,'type_text',side_effect=lambda g,t,l,counts: calls.append(('text',len(t),t=='\n'))), \
                patch.object(vm.time,'sleep',side_effect=lambda s:calls.append(('pause',s))):
            vm.type_token(None,'A'*33,'de',{},True)
        self.assertEqual(calls,[('text',16,False),('pause',1),('text',16,False),('pause',1),('text',1,False),('pause',1)])
        calls.clear()
        with patch.object(vm,'type_text',side_effect=lambda g,t,l,counts:calls.append((len(t),t=='\n'))):vm.type_token(None,'A'*40,'de',{},False)
        self.assertEqual(calls,[(40,False)])
        with patch.object(vm,'type_text') as typed:
            for value in ('','public\nfixture','public\rfixture'):
                with self.assertRaisesRegex(AssertionError,'before input'):vm.type_token(None,value,'de',{},True)
            typed.assert_not_called()

    def test_probe_checks_counter_start_and_finish_before_media_attachment(self):
        from guest_shell import syntax
        guest=Mock();media=Mock(fingerprint='f'*64);names=[]
        def capture(name,source):
            syntax(name,source);names.append(name)
            if name.endswith('-start'):return dict(status='ready',path='/run/ares-input-fixture1',pid=77,device='/dev/input/event5')
            if name=='probe-active-vt':return dict(active='tty2')
            if name=='probe-unicode-console':return dict(status='passed',getter_only=True,unicode_cells=8000)
            return dict(complete=True,keys_released=True,counts=dict(press=0,release=0,repeat=0,syn_dropped=0))
        guest.capture_json.side_effect=capture
        media.attach.side_effect=lambda *a: self.assertEqual(names,['probe-key-counter-start','probe-key-counter-sample-1',
            'probe-key-counter-stop','probe-active-vt','probe-unicode-console'])
        with patch.object(vm.td,'save'):vm.probe_media(guest,media)
        media.detach.assert_called_once_with(guest,'probe')
        self.assertEqual(guest.keys.call_args_list,[__import__('unittest').mock.call(['ctrl','alt','f3']),
            __import__('unittest').mock.call(['ctrl','alt','f2'])])

    def test_dummy_gate_never_enters_real_login_on_stall_or_wrong_refusal(self):
        for failure in ('stall','wrong'):
            console=Mock();console.guest.secrets=[];calls=[]
            def run(name,stage,**kw):
                calls.append(stage)
                self.assertEqual(len(kw['inputs'][1][1]),40)
                self.assertTrue(__import__('re').fullmatch('ghp_[A-Za-z0-9]{36}',kw['inputs'][1][1]) is not None)
                if failure=='stall':raise AssertionError('modelled stall')
                return dict(error='Different STOP')
            console.run.side_effect=run
            with patch.dict(os.environ,GITHUB_ACTOR='fixture-user'),patch.object(vm.td,'save') as saved:
                with self.assertRaisesRegex(AssertionError,'real CI token not typed'):vm.private_login(console)
            self.assertEqual(calls,['private-owner-dummy-login'])
            self.assertFalse(saved.call_args.args[1]['real_ci_token_typed'])

    def test_dummy_gate_normal_refusal_precedes_chunked_real_token(self):
        console=Mock();console.guest.secrets=[];console.last_hidden=dict(received_keys={'counts_only':True},key_comparison={'matches':True});calls=[]
        def run(name,stage,**kw):
            calls.append((stage,kw.get('token_chunks',False),kw.get('expect_stop',False)))
            return dict(error='Private release read failed; check read:packages permission/expiry and network; no credential was written')
        console.run.side_effect=run
        with patch.dict(os.environ,GITHUB_ACTOR='fixture-user',GH_TOKEN='public-test-value'),patch.object(vm.td,'save') as saved:vm.private_login(console)
        self.assertEqual(calls,[('private-owner-dummy-login',False,True),('private-owner-login',True,False)])
        self.assertNotIn('ghp_',json.dumps(saved.call_args.args[1]))


if __name__=='__main__':unittest.main()
