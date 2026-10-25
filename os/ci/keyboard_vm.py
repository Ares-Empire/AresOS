"""Package 13 qualification; all storage/firmware observers are the package 11 ones."""
import base64
import hashlib
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import time

import two_disk_vm as td
import switch_vm as sw
import keyboard_entries as ke
from greeter import capture_stock_greeter

TEXT = 'yz-/!'


def loaded_map(text, layout):
    assert layout in ('de', 'us')
    for code, letter in zip((21, 44), ('z', 'y') if layout == 'de' else ('y', 'z')):
        # kbd 2.9.0 prints '+' for KT_LETTER (CapsLock-sensitive letters).
        rows = re.findall(r'^keycode\s+' + str(code) + r'\s*=\s*([^\s]+)', text, re.M)
        assert len(rows) == 1 and rows[0] in (letter, '+' + letter), 'STOP: loaded console map differs from ' + layout


def deployment_snapshot(guest, stage):
    # Export both raw observations before making any deployment decision.
    rpm = guest.capture_json(stage+'-rpm-ostree-status', sw.framed('rpm-ostree status --json'))
    bootc = guest.capture_json(stage+'-bootc-status', sw.framed('bootc status --json'))
    program = '''import json,pathlib,shlex
entries=[]
for p in pathlib.Path('/boot/loader/entries').glob('*.conf'):
    text=p.read_text()
    args=[a for line in text.splitlines() if line.startswith('options ') for a in shlex.split(line)[1:]]
    target,=[a.split('=',1)[1] for a in args if a.startswith('ostree=')]
    entries.append(dict(file=str(p),content=text,deployment=str(pathlib.Path('/sysroot'+target).resolve(strict=True))))
print(json.dumps(entries))
'''
    bls = guest.capture_json(stage+'-resolved-bls', sw.framed('python3 -c '+shlex.quote(program)))
    snapshot = dict(rpm=rpm, bootc=bootc, bls=bls)
    td.save(stage+'-deployments', snapshot)
    ke.entries(snapshot)
    return snapshot


def physical_keys(char, layout):
    assert layout in ('de', 'us')
    # QEMU 8.2.2 physical positions; xkeyboard-config 2.47 / kbd 2.9.0.
    # Source rows and the complete typed-string walk are retained under 13f.
    special = {' ': ['spc'], '\n': ['ret'], '!': ['shift', '1'], '.': ['dot']}
    if layout == 'de':
        special.update({'y': ['z'], 'z': ['y'], '-': ['slash'], '/': ['shift', '7'],
                        ';': ['shift', 'comma'], "'": ['shift', 'backslash']})
    else:
        special.update({'-': ['minus'], '/': ['slash'], ';': ['semicolon'], "'": ['apostrophe']})
    assert len(char) == 1 and char.isascii() and (char.islower() or char.isdigit() or char in special), char
    return special.get(char, [char])


def type_text(guest, text, layout):
    for char in text:
        guest.keys(physical_keys(char, layout))
        time.sleep(0.12)


def keyboard_state(guest, stage, layout, allow_override=False, temporary_old=None):
    program = '''import json, pathlib, subprocess
result = dict(cmdline=pathlib.Path('/proc/cmdline').read_text().strip(),
    console=pathlib.Path('/etc/vconsole.conf').read_text(),
    x11=pathlib.Path('/etc/X11/xorg.conf.d/00-keyboard.conf').read_text(),
    localed=json.loads(subprocess.check_output(['busctl','--system','--json=short','call',
        'org.freedesktop.locale1','/org/freedesktop/locale1','org.freedesktop.DBus.Properties',
        'GetAll','s','org.freedesktop.locale1'])),
    loaded_map=subprocess.check_output(['dumpkeys','-C','/dev/tty3','--keys-only'], text=True),
    bls={str(p):p.read_text() for p in pathlib.Path('/boot/loader/entries').glob('*.conf')})
print(json.dumps(result))
'''
    result = guest.capture_json(stage + '-keyboard', sw.framed('python3 -c ' + shlex.quote(program)))
    assert result['localed']['data'][0]['X11Layout']['data'] == layout
    assert re.search(r'^KEYMAP=["\']?' + layout + r'["\']?$', result['console'], re.M)
    if allow_override:
        return result
    if not allow_override:
        from_kernel = result['cmdline'].split()
        if temporary_old is not None:
            # Before switch finalization only: the old stock entry is deliberately
            # untouched. Its exact identity and unchanged arguments were checked.
            snapshot = deployment_snapshot(guest, stage+'-temporary-stock')
            resolved = {e['file']: ke.entry_identity(e['deployment']) for e in snapshot['bls']}
            assert sum(identity == temporary_old for identity in resolved.values()) == 1
            texts = [text for file, text in result['bls'].items() if resolved[file] != temporary_old]
        else:
            texts = result['bls'].values()
        all_entries = [line.split()[1:] for text in texts for line in text.splitlines() if line.startswith('options ')]
        assert all_entries, 'Missing BLS options'
        for args in [from_kernel, *all_entries]:
            assert not any(re.match(r'(?:rd\.)?vconsole\.keymap(?:[._]toggle)?(?:=|$)', a) for a in args), 'PRODUCT FAILURE: console keymap override remains'
    # Physical typing below is the semantic check; retain the complete loaded map too.
    loaded_map(result['loaded_map'], layout)
    return result


def physical_input(guest, stage, layout, uid):
    ready = '/tmp/aresos-physical-' + stage
    program = "import os,pathlib\np=pathlib.Path(" + repr(ready) + ")\np.with_suffix('.ready').write_text(str(os.getuid()))\ns=input()\np.write_text(s)\n"
    guest.command(stage + '-prepare-input', 'set -e; printf %s ' + shlex.quote(base64.b64encode(program.encode()).decode()) + ' | base64 -d > /run/aresos-physical.py; chmod 0644 /run/aresos-physical.py')
    type_text(guest, 'python3 /run/aresos-physical.py\n', layout)
    guest.command(stage + '-input-ready', 'set -e; for n in {1..30}; do if test -e ' + ready + '.ready; then test "$(cat ' + ready + '.ready)" = ' + str(uid) + '; exit 0; fi; sleep 1; done; exit 1')
    type_text(guest, TEXT + '\n', layout)
    guest.command(stage + '-input-result', 'set -e; for n in {1..30}; do if test -e ' + ready + '; then test "$(cat ' + ready + ')" = ' + shlex.quote(TEXT) + '; test "$(stat -c %u ' + ready + ')" = ' + str(uid) + '; cat ' + ready + '; exit 0; fi; sleep 1; done; exit 1')
    td.save(stage + '-physical', dict(status='passed', layout=layout, text=TEXT, physical_qcodes=[physical_keys(c,layout) for c in TEXT], uid=uid, transport='QMP USB keyboard; serial observation only'))


def tty(guest, stage, layout, password):
    guest.keys(['ctrl','alt','f3'])
    guest.command(stage + '-getty', 'set -e; for n in {1..60}; do if test "$(cat /sys/class/tty/tty0/active)" = tty3 && pgrep -t tty3 -x agetty; then exit 0; fi; sleep 1; done; exit 1')
    guest.screenshot_safe = False
    type_text(guest, 'ares-recovery\n', layout)
    guest.command(stage + '-password-ready', "python3 - <<'PY'\n" + pathlib.Path('os/ci/tty_password.py').read_text() + '\nPY')
    type_text(guest, password + '\n', layout)
    guest.command(stage + '-login-ready', 'set -e; for n in {1..60}; do if pgrep -t tty3 -u 1000 -x bash; then exit 0; fi; sleep 1; done; exit 1')
    type_text(guest, 'sudo -k\nsudo touch /run/aresos-tty-' + stage + '\n', layout)
    guest.command(stage + '-sudo-ready', 'set -e; for n in {1..30}; do pgrep -t tty3 -x sudo && exit 0; sleep 1; done; exit 1')
    time.sleep(1)
    type_text(guest, password + '\n', layout)
    guest.command(stage + '-sudo-result', 'set -e; for n in {1..30}; do if test -e /run/aresos-tty-' + stage + '; then test "$(stat -c %u /run/aresos-tty-' + stage + ')" = 0; exit 0; fi; sleep 1; done; exit 1')
    physical_input(guest, stage + '-tty', layout, 1000)
    guest.screenshot_safe = True
    guest.screenshot(stage + '-tty3')
    type_text(guest, 'sudo -k\nexit\n', layout)
    guest.command(stage + '-logout', 'set -e; for n in {1..30}; do if pgrep -t tty3 -x agetty; then if pgrep -t tty3 -u 1000; then exit 1; fi; exit 0; fi; sleep 1; done; exit 1')


def foot(guest, stage, layout):
    guest.keys(['ctrl','alt','f1'])
    guest.command(stage + '-foot-ready', 'set -e; for n in {1..120}; do if test "$(cat /sys/class/tty/tty0/active)" = tty1 && pgrep -u ares -x foot; then exit 0; fi; sleep 1; done; exit 1')
    # Inspect the actual compositor environment, never substitute a layout just for this test.
    program = '''import json,pathlib,subprocess
pid,=subprocess.check_output(['pgrep','-u','ares','-x','labwc'],text=True).split()
env=dict(s.split('=',1) for s in pathlib.Path('/proc',pid,'environ').read_bytes().decode().split('\\0') if '=' in s)
print(json.dumps({k:v for k,v in env.items() if k.startswith('XKB_DEFAULT_')}))
'''
    env=guest.capture_json(stage + '-labwc-environment',sw.framed('python3 -c '+shlex.quote(program)))
    assert env['XKB_DEFAULT_LAYOUT'] == layout
    physical_input(guest, stage + '-foot', layout, 1001)
    guest.screenshot(stage + '-foot')


def repair(guest, stage):
    before = deployment_snapshot(guest, stage+'-before')
    result = guest.command(stage, pathlib.Path('os/release/system-keyboard.sh').read_text())
    clean=re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', result).replace('\r','')
    proof,=[json.loads(line.split(' ',1)[1]) for line in clean.splitlines() if line.startswith('ARESOS_SYSTEM_KEYBOARD_RESULT ')]
    td.save(stage,proof)
    assert proof['status']=='passed' and proof['deployment_count'] in (1,2)
    after = deployment_snapshot(guest, stage+'-after')
    assert proof['identity'] == ke.identities(before['rpm']) == ke.identities(after['rpm'])
    ke.unchanged_old(before, after)
    return after


def inject(guest, value):
    # Test setup uses the same qualified no-new-deployment primitive as the repair.
    assert value in ('de','us')
    checked_source = pathlib.Path('os/release/system-keyboard.sh').read_text().split("<<'SYSTEM_KEYBOARD'\n")[1].split('\nSYSTEM_KEYBOARD')[0]
    program=checked_source.split("if __name__ == '__main__':")[0]+'''fix()
args=shlex.split(subprocess.check_output(['rpm-ostree','kargs'],text=True))
args=[a for a in args if not a.startswith(('vconsole.keymap=','rd.vconsole.keymap='))]
subprocess.run(['ostree','admin','instutil','set-kargs',*args,'vconsole.keymap=@VALUE@'],check=True)
subprocess.run(['rpm-ostree','reload'],check=True)
'''.replace('@VALUE@',value)
    guest.command('inject-' + value, 'python3 -c '+shlex.quote(program))


def finish(guest,audit,stage):
    try:
        if guest.process.poll() is None and not getattr(guest,'failed_command',False) and sys.exc_info()[0] is None:
            guest.poweroff(stage)
    finally:
        guest.close(stage)
        audit.check(stage,guest)


def main():
    mode,=sys.argv[1:]
    assert mode in ('probe','keyboard')
    authorization=json.loads(pathlib.Path('evidence/13-dispatch-authorization.json').read_text())
    assert authorization['allowance']=='13'
    assert authorization['native']['status']=='passed' and authorization['native']['sha']==os.environ['GITHUB_SHA'], 'STOP: native preflight must pass before any VM'
    td.EVIDENCE.mkdir(parents=True,exist_ok=True)
    sw.WORK,sw.EVIDENCE=td.WORK,td.EVIDENCE
    if mode=='probe':
        # Preserve every old probe predicate, including both disk mappings.
        td.main()
        return
    assert authorization['probe']['status']=='passed' and authorization['probe']['commit']==os.environ['GITHUB_SHA']
    import crypt
    password='yz-/!'+secrets.token_hex(20)
    hashed=crypt.crypt(password,crypt.mksalt(crypt.METHOD_SHA512))
    print(f'::add-mask::{password}',flush=True); print(f'::add-mask::{hashed}',flush=True)
    credentials=td.WORK/'credentials.json'; credentials.write_text(json.dumps(dict(password=password))); credentials.chmod(0o600)
    td.Guest.order='protected-second'; sw.Guest=td.Guest
    for name in ('vmlinuz','initrd.img'):
        with (td.WORK/name).open('wb') as output:
            subprocess.run(['bsdtar','-xOf',str(td.WORK/td.LIVE['filename']),'images/pxeboot/'+name],stdout=output,check=True)
    audit=td.Audit()
    shutil.copyfile(td.WORK/'vars.fd',td.EVIDENCE/'pre-firmware-vars.fd')
    td.marker(audit,'baseline-firmware',baseline=True)
    td.install(audit,password,hashed)
    release=json.loads(pathlib.Path('os/manifest/release.json').read_text()); target=release['reference']
    guest=td.start_installed(password,hashed,'stock',firmware_default=True)
    try:
        initial = deployment_snapshot(guest,'first-stock-before-repair')
        td.installed_keyboard(guest)
        keyboard_state(guest,'first-stock-diagnostic','de',allow_override=True)
        # Both real deployment starting states are exercised before pin, without
        # booting a deliberately wrong map or changing the backup identity.
        repaired = repair(guest,'repair-installer-value')
        for value in ('de','us'):
            inject(guest,value); repaired = repair(guest,'repair-starting-'+value)
        old = [ke.key(d) for d in initial['rpm']['deployments'] if not d['booted']]
        temporary_old = old[0] if old else None
        stock_identity, = [d for d in repaired['rpm']['deployments'] if d['booted']]
        guest.command('stock-pause',pathlib.Path('os/release/pause-stock-updates.sh').read_text())
        stock=sw.pin_stock(guest,'stock-pin')
        pinned = deployment_snapshot(guest,'after-pin')
        expected = ke.identities(repaired['rpm'])
        expected[0]['pinned'] = True
        assert ke.identities(pinned['rpm']) == expected, 'STOP: pin changed the stock list'
        ke.unchanged_old(initial, pinned)
    finally:
        finish(guest,audit,'first-stock-fixed-pinned')
    td.restore_windows_order('after-first-login-pin'); audit.windows_default=True
    td.marker(audit,'unattended-windows'); td.marker(audit,'detached-windows',detached=True)
    brew=None
    for stage,layout in (('corrected-stock','de'),('aresos','de'),('aresos-us','us'),('aresos-back-de','de'),('rollback','de')):
        guest=td.start_installed(password,hashed,stage)
        try:
            snapshot = deployment_snapshot(guest,stage)
            if stage != 'corrected-stock':
                ke.retained_pair(snapshot,stock_identity,target)
            state=guest.capture_json(stage+'-status',sw.framed('bootc status --json'))
            expected=target if stage.startswith('aresos') else json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@')[1]
            assert (sw.booted_reference(state)==expected if stage.startswith('aresos') else sw.booted_digest(state)==expected)
            if not stage.startswith('aresos'):
                assert state['status']['booted']['ostree']['checksum']==stock['booted_checksum']
            keyboard_state(guest,stage,layout,temporary_old=temporary_old if stage=='corrected-stock' else None)
            tty(guest,stage,layout,password)
            output=guest.command(stage+'-homebrew',pathlib.Path('os/tests/inherited-homebrew.sh').read_text().replace('@STAGE@',stage))
            hashes=re.findall(r'^([0-9a-f]{64})  /',output,re.M); assert len(hashes)==1
            if brew is None: brew=hashes[0]
            assert brew==hashes[0]
            if stage=='corrected-stock':
                guest.command('verify-release',pathlib.Path('os/release/verify.sh').read_text().replace('@REFERENCE@',target).replace('@IDENTITY@',release['signature']['identity']))
                guest.command('switch',pathlib.Path('os/release/switch.sh').read_text().replace('@REFERENCE@',target),timeout=1500)
                sw.inspect_transaction(guest.capture_json('pending-switch',sw.framed('bootc status --json')),target,stock['booted_checksum'])
                pending = deployment_snapshot(guest,'after-switch-staged')
                staged = [d for d in pending['rpm']['deployments'] if d.get('staged')]
                assert len(staged)==1 and not staged[0]['booted'] and not staged[0]['pinned']
                assert staged[0]['container-image-reference-digest']==target.split('@')[1]
                assert ke.identities(dict(deployments=[d for d in pending['rpm']['deployments'] if not d.get('staged')])) == ke.identities(pinned['rpm'])
                ke.unchanged_old(initial,pending)
            elif stage.startswith('aresos'):
                guest.command(stage+'-policy',pathlib.Path('os/tests/guest.sh').read_text())
                foot(guest,stage,layout)
                if stage in ('aresos','aresos-us'):
                    next_layout='us' if stage=='aresos' else 'de'
                    guest.command(stage+'-change-layout',"set -e; localectl --no-convert set-keymap "+next_layout+"; localectl --no-convert set-x11-keymap "+next_layout+" pc105 '' ''")
                else:
                    guest.command('rollback',pathlib.Path('os/release/rollback.sh').read_text().replace('@BASE_DIGEST@',json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@')[1]))
                    sw.inspect_transaction(guest.capture_json('pending-rollback',sw.framed('bootc status --json')),sw.booted_reference(json.loads((td.EVIDENCE/'corrected-stock-status.json').read_text())),stock['booted_checksum'],rollback=True,digest=json.loads(pathlib.Path('os/manifest/base.json').read_text())['reference'].split('@')[1])
                    ke.retained_pair(deployment_snapshot(guest,'after-rollback-queued'),stock_identity,target,queued=True)
            else:
                guest.command('rollback-session',pathlib.Path('os/release/stock-session.sh').read_text())
                capture_stock_greeter(guest,td.EVIDENCE,'rollback-greeter')
        finally:
            finish(guest,audit,stage)
    td.marker(audit,'final-unattended-windows'); td.marker(audit,'final-detached-windows',detached=True)
    td.save('keyboard-result',dict(status='passed',order='protected-second',commit=os.environ['GITHUB_SHA'],release=target,
        starting_states=['de','us'],layouts=['de','us','de'],physical_text=TEXT,tty3_login_password_sudo=True,
        foot_physical=True,all_entries_no_keymap_override=True,all_entries_scope='after-switch-finalization-and-rollback',
        temporary_old_stock_removed_by_finalization=True,rollback_stock_checksum=stock['booted_checksum'],
        protected_disk_unchanged=True,bootnext_audited=True,windows_default=True))


if __name__=='__main__':
    main()
