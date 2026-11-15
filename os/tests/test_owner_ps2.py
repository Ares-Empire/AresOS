"""PS/2 selection/mapping and read-only xHCI gates; no VM or host devices."""
import contextlib
import csv
import gzip
import hashlib
import io
import json
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'os/ci'))
import owner_key_counter as counter
import owner_keys
import owner_xhci as health
import owner_console
import owner_hidden
import owner_login
import owner_vm as vm
from guest_shell import syntax

BOOT = 'b' * 32
Q15 = (
    'xhci_hcd 0000:00:05.0: xHCI host not responding to stop endpoint command',
    'xhci_hcd 0000:00:05.0: xHCI host controller not responding, assume dead',
    'xhci_hcd 0000:00:05.0: HC died; cleaning up',
    'usb 1-1: USB disconnect, device number 2',
)


def journal(messages=('i8042: PNP: PS/2 Controller',), stamp=214_000_000):
    return [dict(_TRANSPORT='kernel', _BOOT_ID=BOOT, __MONOTONIC_TIMESTAMP=str(stamp+n), MESSAGE=m)
            for n, m in enumerate(messages)]


def context(needed=True, attached=False, removals=()):
    return dict(stage='synthetic-stage', since_usec=0, needed=needed, attached=attached,
                removals=[list(removal) for removal in removals])


def kernel_row(stamp, message):
    return dict(_TRANSPORT='kernel', _BOOT_ID=BOOT, __MONOTONIC_TIMESTAMP=str(stamp), MESSAGE=message)


def kernel_result(rows):
    return subprocess.CompletedProcess([], 0, '\n'.join(json.dumps(r) for r in rows), '')


class Ps2Test(unittest.TestCase):
    def test_unique_at_name_and_bus_selection_ignores_usb_and_wrong_bus(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'os/tests') as temporary:
            root = pathlib.Path(temporary)
            def add(n, name='AT Translated Set 2 keyboard', bus=17, vendor=1):
                p=root/f'event{n}'/'device';(p/'id').mkdir(parents=True);(p/'capabilities').mkdir()
                (p/'name').write_text(name)
                for field, value in (('bustype',bus),('vendor',vendor),('product',1)):
                    (p/'id'/field).write_text(f'{value:04x}')
                (p/'capabilities/key').write_text(hex(sum(1<<k for k in (28,30,42,44)))[2:])
            add(2,'QEMU QEMU USB Keyboard',3,0x0627);add(5,bus=3)
            with self.assertRaisesRegex(AssertionError,'i8042 AT'):counter.keyboard(root)
            add(17)
            self.assertEqual(counter.keyboard(root),'/dev/input/event17')
            add(8)
            with self.assertRaisesRegex(AssertionError,'unique'):counter.keyboard(root)

    def test_opened_device_identity_is_at_not_usb(self):
        import array,fcntl
        def ioctl(fd,request,data,mutate):
            if request==0x80084502:data[:]=array.array('H',[17,1,1,0xab83])
            elif request==0x80084503:data[:]=array.array('I',[250,33])
        with patch.object(fcntl,'ioctl',side_effect=ioctl),patch.object(counter.os,'open',return_value=2),patch.object(counter.os,'close'):
            self.assertEqual(counter.settings(1,'/dev/input/fixture'),dict(delay_ms=250,period_ms=33))
        def usb(fd,request,data,mutate):
            data[:]=array.array('H',[3,0x0627,1,1])
        with patch.object(fcntl,'ioctl',side_effect=usb),self.assertRaisesRegex(AssertionError,'changed'):
            counter.settings(1,'/dev/input/fixture')

    def test_actual_guest_static_mapping_getter_requires_every_pinned_index(self):
        import fcntl
        expected=owner_keys.at_keycodes();calls=[]
        def ioctl(fd,request,pair,mutate):
            self.assertEqual(request,0x80084504);calls.append(pair[0]);pair[1]=expected[pair[0]]
        with patch.object(fcntl,'ioctl',side_effect=ioctl):
            self.assertEqual(counter.at_mapping(1,expected),len(expected))
        self.assertEqual(calls,list(expected))
        with patch.object(fcntl,'ioctl'),self.assertRaisesRegex(AssertionError,'mapping differs'):
            counter.at_mapping(1,expected)

    def test_pinned_q35_ps2_queue_and_all_layout_qcodes_reach_identical_linux_codes(self):
        folder=ROOT/'os/manifest/ci/14/14zu-local'
        sources=json.loads((folder/'sources.json').read_text())
        data={}
        for row in sources:
            raw=gzip.decompress((folder/row['path']).read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);data[row['path']]=raw.decode()
        self.assertIn('pc_basic_device_init(pcms, isa_bus',data['pc_q35.c.gz'])
        self.assertIn('pcms->i8042_enabled = true;',data['pc.c.gz'])
        self.assertIn('isa_create_simple(isa_bus, TYPE_I8042)',data['pc.c.gz'])
        self.assertRegex(data['ps2.c.gz'],r'#define PS2_QUEUE_SIZE\s+16')
        self.assertRegex(data['ps2.c.gz'],r'#define PS2_QUEUE_HEADROOM\s+8')
        self.assertRegex(data['ps2.h.gz'],r'#define PS2_BUFFER_SIZE\s+256')
        self.assertIn('qemu_input_map_qcode_to_atset2[qcode]',data['ps2.c.gz'])
        linux=data['atkbd.c.gz']
        table=linux.split('static const unsigned short atkbd_set2_keycode',1)[1].split('#else',1)[1].split('#endif',1)[0]
        table=[int(n) for n in re.findall(r'\d+',table)]
        unxlate=linux.split('static const unsigned short atkbd_unxlate_table[128] = {',1)[1].split('};',1)[0]
        unxlate=[int(n) for n in re.findall(r'\d+',unxlate)]
        rows=list(csv.DictReader(io.StringIO((ROOT/'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv').read_text())))
        codes={r['QEMU QKeyCode']:r for r in rows if r['Linux Keycode'] and r['AT set2 keycode']}
        keys={key for mapping in owner_keys.maps().values() for chord in mapping.values() for key in chord}
        keys.update(('ctrl','alt','f2','f3','f4','u','d'))
        for key in sorted(keys):
            row=codes[key];scan=int(row['AT set2 keycode'],0);code=int(row['Linux Keycode'],0)
            index=(scan&0x7f)|((scan&0x80)<<1)|(0x80 if scan>>8==0xe0 else 0)
            self.assertEqual(table[index],code,(key,'raw set2'))
            set1=int(row['AT set1 keycode'],0)
            translated=unxlate[set1&0x7f]|(0x80 if set1>>8==0xe0 else 0)
            self.assertEqual(table[translated],code,(key,'i8042 translated'))
            getter_index=(set1&0x7f)|(0x80 if set1>>8==0xe0 else 0)
            self.assertEqual(owner_keys.at_keycodes()[getter_index],table[translated])
        sizes={k:3+(2 if int(codes[k]['AT set2 keycode'],0)>>8==0xe0 else 0) for k in keys}
        chords=[chord for mapping in owner_keys.maps().values() for chord in mapping.values()]
        chords += [['ctrl','alt',key] for key in ('f2','f3','f4')]
        self.assertLessEqual(max(sum(sizes[k] for k in chord) for chord in chords),16)
        self.assertEqual(vm.KEY_HOLD_MS,30);self.assertGreaterEqual(vm.KEY_GAP_SECONDS,.12)

    def test_runtime_vm_has_no_usb_keyboard_and_keeps_tools_controller(self):
        guest=object.__new__(vm.Guest);guest.mode='installed'
        args=guest.peripheral_args()
        self.assertNotIn('usb-kbd',' '.join(args));self.assertIn('qemu-xhci,id=usb-controller,addr=0x5',args)
        guest.monitor=Mock()
        with patch.object(vm.time,'sleep') as sleep:guest.keys(['a'])
        self.assertEqual(guest.monitor.command.call_args.args[1]['hold-time'],30)
        sleep.assert_called_once_with(.12)

    def test_every_completed_not_ready_observation_saves_independent_health_receipt(self):
        guest=object.__new__(vm.Guest);guest.xhci_context=context()
        for value,checked in ((dict(ready=False),True),(dict(ready=True),False),
                              (dict(ready=False,handoff_ready=True),False),(dict(ready=False,rejected=True),False)):
            with patch.object(vm.td.Guest,'capture_json',return_value=value),patch.object(health,'checkpoint') as check:
                self.assertEqual(guest.capture_json('observer','SYNTHETIC'),value)
                self.assertEqual(check.call_count,int(checked))
        with patch.object(vm.td.Guest,'capture_json',side_effect=TimeoutError()),patch.object(health,'checkpoint') as check:
            with self.assertRaises(TimeoutError):guest.capture_json('busy-serial','SYNTHETIC')
            check.assert_not_called()

    def test_exact_q15_classes_and_since_boundary_export_no_messages(self):
        value=health.classify(journal(Q15),0,BOOT)
        self.assertEqual(value['counts'],dict(endpoint_timeout=1,controller_dead=2,usb_disconnect=1,expected_disconnect=0))
        self.assertNotIn('xhci_hcd',json.dumps(value))
        self.assertFalse(any(health.classify(journal(Q15),215_000_000,BOOT)['counts'].values()))
        for needed,attached in ((True,False),(False,True),(False,False)):
            with patch.object(subprocess,'run',return_value=kernel_result(journal(Q15))):
                result=health.kernel_health(context(needed,attached))
            self.assertEqual(result['stop'],needed or attached)

    def test_only_requested_tools_port_disconnect_is_expected_never_death(self):
        with patch.object(subprocess,'run',return_value=kernel_result(journal(Q15[:1]))):
            self.assertFalse(health.kernel_health(context(True,True))['stop'])
        with patch.object(subprocess,'run',return_value=kernel_result(journal(('usb 1-2: USB disconnect, device number 3',)))):
            self.assertFalse(health.kernel_health(context(True,True,[('1-2',214_000_000)]))['stop'])
        with patch.object(subprocess,'run',return_value=kernel_result(journal(Q15))):
            self.assertTrue(health.kernel_health(context(True,True,[('1-2',214_000_000)]))['stop'])
        with self.assertRaisesRegex(AssertionError,'repeated'):
            health.classify(journal(('usb 1-2: USB disconnect, device number 3',)*2),0,BOOT,[['1-2',214_000_000]])

    def test_each_requested_removal_excuses_one_disconnect_of_its_port_after_it(self):
        line=lambda n:'usb 2-2: USB disconnect, device number '+str(n)
        two=[['2-2',100],['2-2',300]]
        # Run 43714310216's boot cut-27: two stick cycles, one line after each request. One port
        # excused once per boot counted 2 at the second unplug and stopped.
        self.assertEqual(health.classify([kernel_row(150,line(3)),kernel_row(350,line(4))],0,BOOT,two)['counts'],
                         dict(endpoint_timeout=0,controller_dead=0,usb_disconnect=0,expected_disconnect=2))
        # Before its first request the port's disconnect is unrequested; a later request does not excuse it.
        self.assertEqual(health.classify([kernel_row(50,line(2))],0,BOOT,two)['counts']['usb_disconnect'],1)
        self.assertEqual(health.classify([kernel_row(50,line(2)),kernel_row(150,line(3))],0,BOOT,two)['counts'],
                         dict(endpoint_timeout=0,controller_dead=0,usb_disconnect=1,expected_disconnect=1))
        # A request stamped at the line's own microsecond owns it.
        self.assertEqual(health.classify([kernel_row(100,line(3))],0,BOOT,two)['counts']['expected_disconnect'],1)
        # Another port is never excused, after any request.
        self.assertEqual(health.classify([kernel_row(350,'usb 2-1: USB disconnect, device number 4')],0,BOOT,two)['counts'],
                         dict(endpoint_timeout=0,controller_dead=0,usb_disconnect=1,expected_disconnect=0))
        # Two lines for one request stop, whichever request it is; so does one between the requests
        # (the first stick's line is its own: a second line before the next request is repeated).
        for rows in ([kernel_row(150,line(3)),kernel_row(160,line(4))],
                     [kernel_row(150,line(3)),kernel_row(350,line(4)),kernel_row(360,line(5))]):
            with self.subTest(rows=rows),self.assertRaisesRegex(AssertionError,'repeated tools-stick disconnect'):
                health.classify(rows,0,BOOT,two)
        # Without requests every disconnect is unrequested.
        self.assertEqual(health.classify([kernel_row(150,line(3)),kernel_row(350,line(4))],0,BOOT)['counts']['usb_disconnect'],2)

    def test_context_refuses_malformed_or_unordered_removals(self):
        health.preamble(context(removals=[('2-2',5),('2-2',6)]))
        for removals in ([['2-2']],[('2-2',1)],[['2-2','1']],[['2-2',-1]],[['2-2',True]],[['x',1]],
                         [['2-2',5],['2-2',5]],[['2-2',6],['2-2',5]],'2-2',None):
            with self.subTest(removals=removals),self.assertRaises(AssertionError):
                health.preamble(dict(context(),removals=removals))
        # The single-port key of one removal per boot is gone.
        with self.assertRaises(AssertionError):health.preamble(dict(context(),expected_disconnect='2-2'))

    def test_malformed_missing_or_cross_boot_journal_fails_closed(self):
        for rows in ([],journal(),journal()):
            if rows:
                if not hasattr(self,'one'):self.one=True;rows[0]['_TRANSPORT']='stdout'
                else:rows[0]['_BOOT_ID']='invalid'
            with patch.object(subprocess,'run',return_value=kernel_result(rows)),self.assertRaises(AssertionError):
                health.kernel_health(context())
        with patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],1,'','refused')),self.assertRaises(AssertionError):
            health.kernel_health(context())

    def test_poll_inside_wait_stops_before_deadline_and_never_sends_enter(self):
        from owner_console_shim import execute_screen
        from test_owner_records_prompt import retained_shape
        source=owner_console.source('tty3',"line.endswith('#')",90,context())
        syntax('ps2-health-readiness',vm.sw.framed('python3 -c '+shlex.quote(source)))
        output=io.StringIO()
        with patch.object(subprocess,'run',return_value=kernel_result(journal(Q15))),contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(SystemExit,'xHCI death/disconnect'):execute_screen(source,retained_shape())

    def test_all_readiness_generators_poll_even_at_timeout_and_compile(self):
        sources=[owner_console.source('tty3','False',1,context()),
            owner_console.hidden_idle_source('tty3',1,context()),
            owner_hidden.source('tty4',dict(kind='login'),prompt='Password:',health=context()),
            owner_hidden.source('tty4',dict(kind='login'),receipt={},health=context()),
            owner_hidden.guard_source('tty4',dict(kind='login'),{},health=context()),
            owner_login.guest_source(context()),health.guard('while False: pass\n',context())]
        for n,source in enumerate(sources):
            compile(source,'health-observer','exec')
            self.assertTrue(source.endswith('\nxhci_poll(True)\n'))
            syntax('ps2-observer-'+str(n),vm.sw.framed('python3 -c '+shlex.quote(source)))

    def test_timeout_checks_even_if_final_sample_has_no_loop(self):
        source=health.guard('ready=False\n',context())
        with patch.object(subprocess,'run',side_effect=[kernel_result(journal()),kernel_result(journal(Q15))]):
            with contextlib.redirect_stdout(io.StringIO()),self.assertRaisesRegex(SystemExit,'xHCI death/disconnect'):
                exec(source,{})

    def test_dead_controller_appearing_during_wait_stops_without_waiting_90_seconds(self):
        from owner_console_shim import execute_screen
        from test_owner_records_prompt import retained_shape
        # First poll healthy, next one sees the retained Q15 failure classes.
        calls=[]
        def run(argv,**kwargs):
            calls.append(argv)
            return kernel_result(journal(Q15 if len(calls)>1 else ('i8042: PNP',)))
        source=owner_console.source('tty3','False',90,context())
        with patch.object(subprocess,'run',side_effect=run),self.assertRaisesRegex(SystemExit,'xHCI death/disconnect'):
            execute_screen(source,retained_shape())
        self.assertEqual(len(calls),2)

    def test_early_stop_counts_survive_real_bash_checksum_framing_on_stderr(self):
        from test_guest_framing import FramingTest
        value=dict(counts=dict(controller_dead=2,usb_disconnect=1),stop=True,counts_only=True)
        script=health.preamble(context())+'\nkernel_health=lambda context: '+repr(value)+'\nxhci_poll(True)\n'
        # Existing helper executes unchanged framing in real Bash and redirects
        # only mktemp's /run allocation into an ordinary owned repo directory.
        FramingTest().exercise('python3 -c '+shlex.quote(script),code=1,
            stderr=json.dumps(dict(xhci_health=value))+'\nSTOP: xHCI death/disconnect while tools stick attached or needed\n')



class StickRemovalsInOneBootTest(unittest.TestCase):
    """The real attach and detach, twice in one boot, against a modelled kernel journal.

    Run 43714310216 (22d, tools-local) stopped at cut-27's second unplug: its walk is the
    first to attach and remove the stick twice in one boot (tools-next, export-version-2).
    """

    def boot(self, unplug_lines=1, stages=('tools-next', 'export-version-2')):
        import owner_media
        from types import SimpleNamespace
        clock = [400_000_000]
        rows = journal()
        events, checks = [], []

        def later():
            clock[0] += 1_000_000
            return clock[0]

        media = object.__new__(owner_media.Media)
        media.path, media.expected = pathlib.Path('/nonexistent/owner-tools.raw'), 'e' * 64
        media.attached, media.fingerprint = False, 'f' * 64

        def qmp(name, args=None):
            if name == 'query-block':
                return [dict(inserted={'node-name': 'owner-tools', 'file': str(media.path)})]
            if name == 'device_del':
                for _ in range(unplug_lines):
                    rows.append(kernel_row(later(), 'usb 2-2: USB disconnect, device number ' + str(len(rows))))
                events.append(dict(event='DEVICE_DELETED', data=dict(device='owner-tools-usb')))
            return {}

        def capture_json(name, source):
            later()
            output = io.StringIO()
            if name.endswith('-xhci-health'):
                words = shlex.split(source)
                with patch.object(subprocess, 'run', return_value=kernel_result(rows)), contextlib.redirect_stdout(output):
                    exec(words[words.index('python3') + 2], {})
                checks.append((name, json.loads(output.getvalue())))
                return checks[-1][1]
            if name.endswith('-tools-usb-port'):
                # The guest program itself, over a stand-in for the controller's sysfs folder.
                program = source.split("<<'PY'\n", 1)[1].split('\nPY\n', 1)[0]
                sysfs = "'/sys/bus/pci/devices/0000:00:05.0'"
                self.assertIn(sysfs, program)
                with tempfile.TemporaryDirectory(dir=ROOT / 'os/tests') as root:
                    (pathlib.Path(root) / 'usb2/2-2').mkdir(parents=True)
                    with patch.object(time, 'clock_gettime_ns', return_value=clock[0] * 1000), \
                            contextlib.redirect_stdout(output):
                        exec(program.replace(sysfs, repr(root)), {})
                return json.loads(output.getvalue())
            if name.endswith('-media-hotplug'):
                return dict(blockdevices=[dict(label='ARESTOOLS')])
            raise AssertionError('unexpected capture ' + name)

        guest = SimpleNamespace(xhci_context=dict(context(needed=False), stage='cut-27'), owner_signed_in=True,
                                owner_physical_signed_in=True, mode='installed', boot_number=12,
                                monitor=SimpleNamespace(command=qmp, events=events), capture_json=capture_json,
                                command=lambda name, source: later(), device_inventory=dict)
        with patch.object(owner_media, 'digest', return_value=media.expected), \
                patch.object(owner_media.Media, 'verify'), patch.object(owner_media.td, 'save'):
            for stage in stages:
                media.attach(guest, stage)
                media.detach(guest, stage)
        return guest, rows, dict(checks)

    def test_two_removals_in_one_boot_each_excuse_their_own_line(self):
        guest, rows, checks = self.boot()
        removals = guest.xhci_context['removals']
        lines = [int(r['__MONOTONIC_TIMESTAMP']) for r in rows if 'USB disconnect' in r['MESSAGE']]
        # The run's shape: two lines of port 2-2 in one boot, each after its own request.
        self.assertEqual([port for port, _ in removals], ['2-2', '2-2'])
        self.assertTrue(removals[0][1] < lines[0] < removals[1][1] < lines[1])
        counts = lambda name: (checks[name]['counts']['expected_disconnect'], checks[name]['counts']['usb_disconnect'])
        self.assertEqual(counts('tools-next-requested-unplug-xhci-health'), (0, 0))
        self.assertEqual(counts('tools-next-unplug-confirmed-xhci-health'), (1, 0))
        self.assertEqual(counts('export-version-2-before-hotplug-xhci-health'), (1, 0))
        self.assertEqual(counts('export-version-2-requested-unplug-xhci-health'), (1, 0))
        self.assertEqual(counts('export-version-2-unplug-confirmed-xhci-health'), (2, 0))
        self.assertFalse(any(value['stop'] for value in checks.values()))
        self.assertEqual(checks['export-version-2-before-hotplug-xhci-health']['tools_removals_requested'], 1)
        self.assertEqual(checks['export-version-2-unplug-confirmed-xhci-health']['tools_removals_requested'], 2)

    def test_one_unplug_logging_two_lines_still_stops(self):
        with self.assertRaisesRegex(AssertionError, 'repeated tools-stick disconnect'):
            self.boot(unplug_lines=2, stages=('tools-next',))


if __name__=='__main__':unittest.main()
