"""Replay the package-13 pre-dispatch evidence without a VM or network access."""
import hashlib
import json
import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'os/manifest/ci/13/zero-cost'
proof = json.loads((EVIDENCE / 'verification.json').read_text(encoding='utf-8'))
for item in proof['source_files']:
    raw = (EVIDENCE / item['file']).read_bytes()
    assert len(raw) == item['bytes']
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], item['file']
for name, item in proof['retained_inputs'].items():
    raw = (ROOT / name).read_bytes()
    assert len(raw) == item['bytes']
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], name


def source(name):
    return (EVIDENCE / name).read_text(encoding='utf-8')


def retained(name):
    return (ROOT / name).read_text(encoding='utf-8')


payload = source('anaconda-modules_payloads_payload_rpm_ostree_installation.py')
boss = source('anaconda-modules_boss_installation.py')
localization = source('anaconda-modules_localization_localization.py')
installation = source('anaconda-modules_localization_installation.py')
assert 'set_kargs_args.append("vconsole.keymap=" + localization.VirtualConsoleKeymap)' in payload
assert 'set_kargs_args = ["admin", "instutil", "set-kargs", "--merge"]' in payload
assert boss.index('PopulateMissingKeyboardConfigurationWithTask()') < boss.index('payloads_proxy.InstallWithTasks()')
assert 'task.succeeded_signal.connect(lambda: self._update_settings_from_task(task.get_result()))' in localization
assert 'self.set_vc_keymap(vc_keymap)' in localization
assert 'get_missing_keyboard_configuration(' in installation
assert 'KEYMAP="%s"' in installation

old = ROOT / 'os/manifest/ci/11n/b-1/installer'
for suffix in ('localed', 'installation', 'utils'):
    name = 'usr_lib64_python3.14_site-packages_pyanaconda_modules_localization_' + suffix + '.py'
    assert (old / name).read_bytes() == (EVIDENCE / ('anaconda-modules_localization_' + suffix + '.py')).read_bytes()

base = 'os/manifest/ci/11n/b-1/two-disk/'
bls = json.loads(retained(base + 'b-bls-entries.json'))
assert len(bls) == 2
for entry in bls:
    options, = re.findall(r'^options (.*)$', entry['content'], re.M)
    assert re.findall(r'(?:^|\s)vconsole.keymap=(\S+)', options) == ['us']
files = json.loads(retained(base + 'installed-keyboard-files.json'))['files']
assert 'KEYMAP="de"' in files['etc/vconsole.conf']
choices = json.loads(retained(base + 'webui-keyboard-proof.json'))
assert choices['module_before'] == choices['module_after']
assert choices['module_before']['XLayouts'] == ['de']
assert choices['module_before']['VirtualConsoleKeymap'] == ''
assert choices['live_localed']['keymap'] == 'us'

boot = retained('os/manifest/ci/11k/full-5/two-disk/aresos-boot-console.txt')
assert 'Kernel command line:' in boot and 'vconsole.keymap=de' in boot
assert 'vconsole.keymap=us' not in boot
keymap = retained('os/manifest/ci/11k/full-5/two-disk/tty-keymap-proof.txt')
assert re.search(r'^keycode\s+21 = \+z$', keymap, re.M)
assert re.search(r'^keycode\s+44 = \+y$', keymap, re.M)
assert 'RECOVERY_ADMIN_TTY3_LOGIN_AND_PASSWORD_SUDO_PASSED' in retained(
    'os/manifest/ci/11k/full-5/two-disk/tty-admin-login.txt')
typer = retained('os/ci/two_disk_vm.py')
assert "'y': ['z'], 'z': ['y']" in typer
assert "password = secrets.token_hex(24)" in typer
assert 'y' in 'ares-recovery' and '-' in 'ares-recovery'

vconsole = source('systemd-src_vconsole_vconsole-setup.c')
assert vconsole.index('/* Load data from configuration file (middle priority) */') < vconsole.index(
    '/* Let the kernel command line override /etc/vconsole.conf (highest priority) */')
assert 'struct xkb_rule_names rules = { 0 };' in source('labwc-src_input_keyboard.c')
assert 'XKB_DEFAULT_LAYOUT' in source('libxkbcommon-src_context-priv.c')
assert "value: 'us'" in source('libxkbcommon-meson_options.txt')
assert 'get_kargs' in source('bootc-crates_lib_src_bootc_kargs.rs')
assert 'ostree::BootconfigParser::get(&bootconfig, "options")' in source('bootc-crates_lib_src_bootc_kargs.rs')

subprocess.run(['git', 'diff', '--exit-code', '3459111', '--', 'os/ci', 'os/config', 'os/release',
                '.github/workflows', 'os/tests', 'os/manifest/base.json', 'os/manifest/release.json'],
               cwd=ROOT, check=True)
assert proof['status'] == 'STOP-PLAN-GAP'
assert proof['budget']['start'] is None and proof['budget']['dispatches'] == 0
print('ZERO_COST_EVIDENCE_REPLAY_PASSED: 26 source files, 16 retained inputs; runtime/audits/pins unchanged')
print('STOP-PLAN-GAP: the historical console value at the argument-writing boundary is not retained; no dispatch authorized')
