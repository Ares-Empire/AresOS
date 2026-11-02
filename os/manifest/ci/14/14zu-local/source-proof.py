import pathlib,sys,json,hashlib,gzip,csv,io,re,shlex
r=pathlib.Path.cwd();sys.path[:0]=[str(r/'os/ci'),str(r/'os/tests')]
import owner_keys,owner_xhci
import owner_vm
from guest_shell import syntax
from test_owner_ps2 import Q15,journal,BOOT
out=r/'os/manifest/ci/14/14zu-local'
raw=r/'.work/14/run-40897501964/evidence/two-disk/corrected-stock-boot-console.txt'
console=raw.read_text(encoding='utf-8')
assert 'i8042: PNP: PS/2 Controller' in console
assert 'input: AT Translated Set 2 keyboard as /devices/platform/i8042/serio0/input/' in console
vcsa=r/'.work/14/run-40897501964/evidence/two-disk/corrected-stock-records-completed-wait-53-timeout-1.vcsa'
raw_vcsa=vcsa.read_bytes()
assert hashlib.sha256(raw_vcsa).hexdigest()=='8649735e5bd80360e83a626321415b0e87aef64ffb4592f9eb15b14161f5fd8f'
screen=bytes(raw_vcsa[4::2]).decode('latin1')
for line in Q15:assert line in screen
counts=owner_xhci.classify(journal(Q15),0,BOOT)['counts']
src=json.loads((out/'sources.json').read_text())
def text(name):return gzip.decompress((out/name).read_bytes()).decode()
assert 'pcms->i8042_enabled = true;' in text('pc.c.gz')
csvrows=list(csv.DictReader(io.StringIO((r/'os/manifest/ci/13/13f-zero-cost/qemu-keymap.csv').read_text())))
codes={v['QEMU QKeyCode']:v for v in csvrows if v['QEMU QKeyCode'] and v['Linux Keycode'] and v['AT set2 keycode']}
mapping=[]
for profile,chars in owner_keys.maps().items():
    keys={k for chord in chars.values() for k in chord}
    mapping.append(dict(profile=profile,characters=len(chars),qcodes=len(keys),linux_keycodes_identical=True,
        qcode_to_linux={k:int(codes[k]['Linux Keycode'],0) for k in sorted(keys)}))
guest=object.__new__(owner_vm.Guest);guest.boot_number=1
def capture(name,command):
    syntax(name,command)
    words=shlex.split(command);compile(words[words.index('python3')+2],'boot-at-keymap','exec')
    return dict(device='/dev/input/event17',name='AT Translated Set 2 keyboard',bus=17,
        static_keycodes_checked=len(owner_keys.at_keycodes()))
guest.capture_json=capture;guest.keyboard_device()
proof=dict(status='source and retained-device proof; November VM transport qualification pending',
 pinned_runner_qemu='1:8.2.2+ds-0ubuntu1.18',upstream_reference='QEMU v8.2.2',
 machine='q35 default i8042=true; pc_basic_device_init -> pc_superio_init -> TYPE_I8042; early native QMP qtree assertion added',
 retained_guest=dict(sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),path=raw.relative_to(r).as_posix(),run=40897501964,
  facts=['i8042 PS/2 Controller ports0x60/0x64 IRQ1/12','AT Translated Set2 keyboard on platform/i8042/serio0'],raw_boot_console_committed=False),
 keyboard=dict(name='AT Translated Set 2 keyboard',bus=17,vendor=1,product=1,event_number_fixed=False,
  linux_atkbd_reference='v6.17; guest fork is not claimed identical; existing pinned guest keymaps and boot device name verified',
  runtime_selection_and_EVIOCGID_recheck=True,code_mapping_test='raw and i8042 translated AT set2 -> Linux keycode, all used qcodes incl modifiers/VT selection'),
 static_guest_mapping=dict(ioctl='EVIOCGKEYCODE 0x80084504; getter only',
  translated_set1_indices=len(owner_keys.at_keycodes()),boot_composition_bash_and_python_syntax=True,
  runtime='Mandatory guest boot assertion; actual guest execution awaits November'),
 queue=dict(protocol_limit_bytes=16,reply_headroom_bytes=8,backing_buffer_bytes=256,hold_ms=30,gap_ms=120,
  guarantee='One chord is bounded below16 scancode bytes; gaps permit draining but do not prove arbitrary-host-stall immunity. Counter/echo refusal stays mandatory.'),
 mappings=mapping,q15_class_counts=counts,health=dict(
  since='Each Linux boot-stage starts at monotonic0, covering failures even before serial login; owner-command/media boundaries keep that complete boot interval.',
  poll='Guest journalctl --dmesg --boot=0 --output=json; one poll per second inside every readiness/hidden observer, forced at entry/exit.',
  refusal='Controller-dead or unrequested disconnect plus attached/needed stick; endpoint timeout counted diagnostically; missing/inconsistent journal STOPs.',
  intentional_removal='Exactly one port2 disconnect, resolved by sysfs under owned PCI00:05.0 before device_del, only during independently requested removal.',
  exported='counts and classes; no kernel MESSAGE text',firmware_markers='No Linux journal in Windows/firmware markers; existing tools-absent/QMP/NVRAM audits stay mandatory'),
 actions_minutes=0,push=False,dispatch=False,hardware=False)
(out/'source-proof.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PASS retained i8042/AT guest device, q35 source, queue16/headroom8/buffer256, pinned layout mappings, exact Q15 classifier')
