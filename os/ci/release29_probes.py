"""Guest-only probes for the package 331 qualifying walk."""

import hashlib
import json
import pathlib
import re
import shlex
import time

import release28_walk as r28

CONTROL_CHECKER = r28.CONTROL_CHECKER
SERVICE_CHECKS = r28.CONTROL_CHECKS
CHROME_CHECKS = ('chrome_links', 'chrome_bundle', 'chrome_other_ids', 'chrome_sites', 'gh', 'chrome_polkit')
CHROME_FIRST_USE = 'os/ci/release29_chrome_probe.py'
POLKIT_REVIEW = 'os/ci/polkit-review.json'
SITES = r28.SITES
STAGED_SITES = '/var/lib/aresos-r29-rehearsal-sites.json'
SYNTHETIC_SITES = r28.SITES_LIST.encode() + b'\n'
PLACEHOLDER = b'{"format":0,"hosts":[]}'
SITE_METADATA = dict(regular=True, owner=[0, 250], mode='0640')
REFUSALS = dict.fromkeys(('tabs', 'read', 'open', 'take_tab'), 'chrome_settings_unavailable')
THEMES = {'28': r28.THEME, '29': 'AresOS'}
FONTS = {'Space Grotesk': r28.SPACE_GROTESK, 'Space Grotesk:bold': r28.SPACE_GROTESK}
FONTS_29 = FONTS | {'JetBrains Mono': '/usr/share/fonts/aresos/JetBrainsMono-Variable.ttf',
                    'Jersey 10': '/usr/share/fonts/aresos/Jersey10-Regular.ttf'}


def receipt_settings():
    return dict(control_checker=CONTROL_CHECKER, control_checks={
        '28': list(SERVICE_CHECKS), '29': list(SERVICE_CHECKS + CHROME_CHECKS)},
        chrome_first_use=CHROME_FIRST_USE, chrome_sites_sha256=hashlib.sha256(SYNTHETIC_SITES).hexdigest(),
        themes=THEMES, fonts={'28': FONTS, '29': FONTS_29}, polkit_review=POLKIT_REVIEW,
        game_memory_high=r28.MEMORY_HIGH)


def capture(guest, stage, vm, source):
    value = guest.capture_json(stage, vm.sw.framed('python3 -c ' + shlex.quote(source)))
    vm.td.save(stage, value)
    return value


def control(guest, stage, vm, *, expected_sites=None):
    names = SERVICE_CHECKS if expected_sites is None else SERVICE_CHECKS + CHROME_CHECKS
    source = pathlib.Path(CONTROL_CHECKER).read_text()
    probe = r28.program(r28.CHECK_CONTROL + 'print(json.dumps(release_checks))', checker=source, checks=names)
    checked = capture(guest, stage + '-control', vm, probe)
    lines = checked['stdout'].splitlines()
    assert checked['status'] == 0 and lines and lines[-1] == 'CONTROL_RELEASE_CHECKS_PASS', \
        'STOP: Control release checker failed: ' + json.dumps(checked)
    results = json.loads(lines[0])
    assert set(results) == set(names) and all(row['ok'] is True for row in results.values()), \
        'STOP: Control checks missing or failed at ' + stage
    r28.validate_control_service(results)
    if expected_sites is not None:
        digest = 'CONTROL_CHROME_SITES_SHA256 ' + expected_sites
        assert lines[1:-1] == [digest] and results['chrome_sites']['value'] == SITE_METADATA | {'sha256': expected_sites}, \
            'STOP: Chrome sites hash or metadata changed at ' + stage
    else:
        assert len(lines) == 2, 'STOP: unexpected Control service checker output'
    # Save the checker result before starting any systemd graph queries.
    login = capture(guest, stage + '-control-login', vm, 'import json, subprocess\n' + r28.LOGIN_GRAPH + 'print(json.dumps(login))')
    r28.validate_login(login, strict_requirements=True)
    return results


SITES_STATE = '''import json, os, pathlib, stat, subprocess
live=pathlib.Path(@LIVE@)
staged=pathlib.Path(@STAGED@)
operation=@OPERATION@
out={}
try:
    assert os.getuid()==0, 'expected a root read'
    path=staged if operation=='stage' else live
    if operation=='stage':
        assert not live.exists() and not live.is_symlink(), 'Chrome live list already exists before R29'
        with staged.open('xb') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(@CONTENTS@)
    info=path.lstat()
    out=dict(regular=stat.S_ISREG(info.st_mode), owner=[info.st_uid,info.st_gid], mode=f'{stat.S_IMODE(info.st_mode):04o}')
    assert out['regular'], 'Chrome sites is not a regular file'
    if operation=='placeholder':
        out['placeholder']=path.read_bytes()==@PLACEHOLDER@
    with path.open('rb') as stream:
        out['sha256']=subprocess.check_output(['/usr/bin/sha256sum'],stdin=stream,text=True,timeout=20).split()[0]
except Exception as error:
    out['error']=f'{type(error).__name__}: {error}'
print(json.dumps(out))
'''


def sites_state(guest, stage, vm, operation):
    source = r28.program(SITES_STATE, live=SITES, staged=STAGED_SITES, contents=SYNTHETIC_SITES,
                         operation=operation, placeholder=PLACEHOLDER)
    value = capture(guest, stage + '-sites-' + operation, vm, source)
    assert 'error' not in value and re.fullmatch('[0-9a-f]{64}', value.get('sha256', '')), \
        'STOP: Chrome sites ' + operation + ' failed: ' + json.dumps(value)
    return value


def stage_sites(guest, stage, vm):
    value = sites_state(guest, stage, vm, 'stage')
    assert all(value[k] == v for k, v in (SITE_METADATA | {'owner': [0, 0], 'mode': '0600'}).items()), \
        'STOP: staged Chrome list has unexpected metadata'
    return value['sha256']


def checked_sites(guest, stage, vm, expected):
    value = sites_state(guest, stage, vm, 'hash')
    assert value == SITE_METADATA | {'sha256': expected}, 'STOP: Chrome sites hash or metadata changed at ' + stage
    return value


# Both probes start from the supervisor's environment. The compositor sets its
# display name after startup, so its own initial /proc environ cannot supply it.
DESKTOP_ENV = r'''import os, pathlib, subprocess
HOME='/var/home/ares'
RUNTIME='/run/user/1001'
SUPERVISOR=b'/usr/bin/python3\0/usr/libexec/aresos-desktop\0session\0'

def pids(name):
    return subprocess.run(['pgrep','-u','ares','-x',name],capture_output=True,text=True).stdout.split()

def supervisor():
    found=[]
    for pid in pids('aresos-desktop'):
        folder=pathlib.Path('/proc',pid)
        try:
            if (folder/'cmdline').read_bytes()==SUPERVISOR:
                found.append((folder/'environ').read_text())
        except FileNotFoundError:
            continue
    assert len(found)==1, f'expected one desktop supervisor, found {len(found)}'
    env=dict(item.split('=',1) for item in found[0].split('\0') if '=' in item)
    assert env.get('HOME')==HOME, 'desktop supervisor HOME differs from the daily home'
    assert env.get('WAYLAND_DISPLAY') and env.get('XDG_RUNTIME_DIR')==RUNTIME, 'desktop supervisor has no Wayland display'
    return env

def daily(env):
    keep=('HOME','USER','LOGNAME','LANG','XDG_RUNTIME_DIR','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS',
          'XDG_SESSION_ID','XDG_SEAT','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP')
    return ['runuser','-u','ares','--','env','-i']+[k+'='+env[k] for k in keep if k in env]+[
        'PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin']

def active_vt():
    return pathlib.Path('/sys/class/tty/tty0/active').read_text().strip()
'''

TERMINAL = r'''import json,time
logfile=pathlib.Path('/run/aresos-r29-terminal.log')
out=dict(attempts=[],pid=None)
try:
    for _ in range(60):
        out['vt']=active_vt()
        if out['vt']=='tty1':
            break
        time.sleep(1)
    assert out['vt']=='tty1', 'Terminal requires tty1'
    env=supervisor()
    app=json.loads(pathlib.Path('/usr/share/aresos/apps/terminal.json').read_text())
    assert app['argv']==@ARGV@ and app['working_directory']=='~', 'Terminal app command or cwd differs'
    assert not pids('foot'), 'an earlier foot is still running'
    for attempt in range(1,6):
        assert active_vt()=='tty1', 'Terminal requires tty1'
        row=dict(attempt=attempt)
        out['attempts'].append(row)
        with logfile.open('wb') as log:
            result=subprocess.run(daily(env)+['setsid','-f']+app['argv'],cwd=env['HOME'],stdin=subprocess.DEVNULL,
                                  stdout=log,stderr=subprocess.STDOUT,timeout=15)
        row['exit']=result.returncode
        if result.returncode==0:
            for _ in range(40):
                found=pids('foot')
                if found or logfile.stat().st_size and 'no monitors available' in logfile.read_text(errors='replace'):
                    break
                time.sleep(.25)
            row['started']=found
            time.sleep(3)
            row['survived']=pids('foot')
        row['log']=logfile.read_text(errors='replace')[-2000:]
        assert result.returncode==0, 'Terminal launcher failed'
        if len(found)==1 and found==row['survived']:
            pid=found[0]
            row['cwd']=os.readlink('/proc/'+pid+'/cwd')
            assert row['cwd']==HOME, 'Terminal did not start in the daily home'
            assert active_vt()=='tty1', 'Terminal did not survive on tty1'
            out['pid']=int(pid)
            break
        assert not row['survived'] and 'no monitors available' in row['log'], 'Terminal foot did not survive'
        if attempt<5:
            time.sleep(2)
    assert out['pid'] is not None, 'Terminal could not find a monitor in five attempts'
except Exception as error:
    out['error']=f'{type(error).__name__}: {error}'
    if logfile.exists() and out['attempts']:
        out['attempts'][-1]['log']=logfile.read_text(errors='replace')[-2000:]
print(json.dumps(out))
'''


def open_terminal(guest, stage, vm):
    guest.keys(['ctrl', 'alt', 'f1'])
    guest.command(stage + '-terminal-session', vm.ACTIVE_DESKTOP)
    time.sleep(1)
    value = capture(guest, stage + '-terminal', vm, DESKTOP_ENV + r28.program(TERMINAL, argv=vm.HUB_TERMINAL))
    assert value['pid'] and 'error' not in value, 'STOP: Terminal probe failed: ' + json.dumps(value)
    return value


def session(guest, stage, vm, release):
    fonts = FONTS_29 if release == '29' else FONTS
    value = capture(guest, stage + '-session', vm, r28.program(r28.SESSION, as_ares=r28.AS_ARES, fonts=list(fonts)))
    assert value['labwc'] == 1 and value['theme'] == THEMES[release] and value['themerc'], 'STOP: running labwc theme differs at ' + stage
    assert value['fonts'] == fonts, 'STOP: session fontconfig differs at ' + stage
    vm.release_rules(guest, stage)
    vm.terminal_path(guest, stage)
    vm.polkit_sweep(guest, stage)


def first_use(guest, stage, vm, expected):
    placeholder = sites_state(guest, stage, vm, 'placeholder')
    assert placeholder.get('placeholder') is True and all(placeholder[k] == v for k, v in SITE_METADATA.items()), \
        'STOP: Chrome first-boot placeholder bytes or metadata differ'
    print('CONTROL_CHROME_FILES_PASS')
    source = pathlib.Path(CHROME_FIRST_USE).read_text()
    call = r28.program('\nmain(@LIVE@, @STAGED@, @EXPECTED@, @REFUSED@, @PLACEHOLDER@, @CONTENTS@)\n',
                       live=SITES, staged=STAGED_SITES, expected=expected, refused=REFUSALS,
                       placeholder=PLACEHOLDER, contents=SYNTHETIC_SITES)
    value = capture(guest, stage + '-chrome-first-use', vm, DESKTOP_ENV + source + call)
    assert value.get('refusals') == REFUSALS and value.get('page_server_hits') == 0 \
        and value.get('first_use') == 'CONTROL_CHROME_SITES_FIRST_USE_PASS', \
        'STOP: Chrome first-use gate failed: ' + json.dumps(value)
    print('CONTROL_CHROME_SITES_FIRST_USE_PASS')
    assert value.get('opened') is True and 'error' not in value, 'STOP: Chrome setup failed: ' + json.dumps(value)
    checked_sites(guest, stage, vm, expected)
    return value
