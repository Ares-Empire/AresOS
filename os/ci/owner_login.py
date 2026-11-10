"""Prepared, bounded physical login observations. No credential crosses UART."""
import hashlib
import inspect
import json
import os
import pathlib
import re
import shlex
import time

import owner_console
import owner_hidden
import owner_key_counter
import owner_xhci
from owner_console import screen
from owner_hidden import hidden_snapshot, identity, input_guard, same_process, device_number, reader_matches, echo_at
from owner_key_counter import publish, start, checkpoint, finish, count_events, compare


class ReaderChanged(AssertionError):
    pass


def login_timeout(text):
    rows = []
    for line in text.splitlines():
        line = line.split('#', 1)[0].split()
        if line and line[0] == 'LOGIN_TIMEOUT':
            assert len(line) == 2 and re.fullmatch('[0-9]+', line[1]), 'Invalid LOGIN_TIMEOUT'
            rows.append(int(line[1]))
    assert len(rows) <= 1, 'Duplicate LOGIN_TIMEOUT'
    value = rows[0] if rows else 60  # Verified util-linux2.41.5 login.c default.
    assert 0 < value <= 600, 'Unbounded or unsupported LOGIN_TIMEOUT'
    return value


def login_foreground(tty, proc=pathlib.Path('/proc')):
    physical = 4 * 256 + int(tty[3:])
    rows = hidden_snapshot(proc)
    groups = {r['tpgid'] for r in rows.values() if r['tty'] == physical and r['tpgid'] > 0}
    leaders = [r for r in rows.values() if len(groups) == 1 and r['pid'] == next(iter(groups))
        and r['tty'] == physical and r['pgrp'] == r['pid'] and r['session'] == r['pid']]
    assert len(leaders) == 1, 'No unique physical login foreground'
    assert len([r for r in rows.values() if r['tty']==physical and r['pgrp']==leaders[0]['pgrp']])==1, 'Multiple foreground login processes'
    return leaders[0]


def login_public(tty, fresh=False):
    import termios
    row = login_foreground(tty)
    assert row['comm'] in ('agetty', 'login') and row['exe'] == '/usr/bin/' + row['comm'], 'Unknown public reader'
    if fresh: assert row['comm'] == 'agetty', 'Old login alarm may still be running'
    fd = os.open('/dev/' + tty, os.O_RDONLY | os.O_NOCTTY | os.O_NONBLOCK)
    try:
        assert device_number(fd) == row['tty']
        attrs = termios.tcgetattr(fd)
    finally: os.close(fd)
    kill = attrs[6][termios.VKILL]
    kill = kill if isinstance(kill, int) else ord(kill)
    # agetty2.41.5 handles CTRL-U itself even with ICANON/ECHO off.
    assert row['comm'] == 'agetty' or bool(attrs[3] & termios.ICANON) and kill == 21, 'Line kill is not proved'
    return dict(reader=identity(row), canonical=bool(attrs[3] & termios.ICANON), vkill=21,
        kill_semantics='agetty2.41.5 CTRL-U handler' if row['comm'] == 'agetty' else 'canonical VKILL')


def login_remaining(state):
    return state['timeout'] / 2 - (time.monotonic() - state['username_at'])


def login_guard(state, minimum=0):
    receipt = state['reader']
    deadline=min(time.monotonic()+5,state['username_at']+state['timeout']/2)
    stable=0
    while True:
        try: result = dict(input_guard(state['tty'], dict(kind='login'), receipt))
        except (OSError,AssertionError):
            result=dict(ready=False,echo_enabled=None,syscall_number=None,canonical=False,vkill=None,
                value_recorded=False,queue_contents_read=False,observation=dict(reason='Reader unavailable',foreground_chain=[]))
        try:
            row = login_foreground(state['tty'])
            changed = not same_process(row, receipt)
        except (OSError, AssertionError): changed = True
        remaining = login_remaining(state)
        stable=stable+1 if result['ready'] and not changed and remaining>minimum else 0
        result.update(reader_changed=changed,remaining_seconds=remaining,stable_samples=stable,
            elapsed_seconds=state['timeout']/2-remaining,timeout_seconds=state['timeout'])
        result['ready']=stable>=3 and remaining>minimum
        result['reason']='reader-changed' if changed else 'budget-exceeded' if remaining<=minimum else 'guard'
        if changed or remaining<=minimum or stable>=3 or time.monotonic()>=deadline:return result
        time.sleep(.1)


def login_visibility(state):
    try:
        row = login_foreground(state['tty'])
        if not same_process(row, state['reader']) or not reader_matches(row, dict(kind='login')):
            return 'non_hidden'
        return 'non_hidden' if echo_at('/dev/' + state['tty'], row['tty']) else 'hidden'
    except (OSError, AssertionError): return 'unknown'


def login_audit_batch(data, before, after, counts):
    if before is not None or after is not None:
        kind = before if before == after and before is not None else 'unknown'
        count_events(data, counts[kind])


def login_exposure(audit):
    counts=audit['counts']
    non_hidden=sum(counts['non_hidden'][key] for key in ('press','release','repeat'))
    unknown=sum(counts['unknown'][key] for key in ('press','release','repeat'))
    dropped=sum(row['syn_dropped'] for row in counts.values())
    complete=audit.get('complete') is True
    return dict(non_hidden_events=non_hidden,unknown_events=unknown,syn_dropped=dropped,
        complete=complete,secret_tainted=bool(non_hidden or unknown or dropped or not complete))


def login_audit(fd, root, max_seconds=240):
    import select
    counts = {kind: dict(press=0, release=0, repeat=0, syn_dropped=0) for kind in ('hidden','non_hidden','unknown')}
    start = time.monotonic()
    complete=False
    publish(root/'audit-ready.json', dict(ready=True, counts_only=True))
    try:
        while time.monotonic()-start < max_seconds:
            state = json.loads((root/'state.json').read_text())
            if state.get('audit_stop'):complete=True;break
            if select.select([fd], [], [], .02)[0]:
                before = login_visibility(state) if state.get('armed') else None
                data = os.read(fd, 24*256)
                after_state = json.loads((root/'state.json').read_text())
                after = login_visibility(after_state) if after_state.get('armed') else None
                login_audit_batch(data,before,after,counts)
            publish(root/'audit.json', dict(counts_only=True, counts=counts, complete=True,value_recorded=False,
                codes_recorded=False, sampled_at=time.monotonic()))
        else: raise AssertionError('Login audit deadline')
    finally:
        os.close(fd)
        publish(root/'audit-result.json', dict(counts_only=True, counts=counts, complete=complete,value_recorded=False, codes_recorded=False))


def login_initialize(root, tty):
    import subprocess
    assert tty in ('tty3','tty4')
    versions = {}
    for tool in ('login','agetty'):
        value = subprocess.check_output(['/usr/bin/'+tool, '--version'], text=True, timeout=5).strip()
        assert re.search(r'\b2\.41\.5\b', value), 'Unverified login/getty version'
        versions[tool] = value
    config = pathlib.Path('/etc/login.defs')
    timeout = login_timeout(config.read_text() if config.exists() else '')
    ticket = start()
    state = dict(tty=tty,timeout=timeout,ticket=ticket,armed=False,audit_stop=False,versions=versions)
    publish(root/'state.json', state)
    assert released(ticket['device'])
    fd = os.open(ticket['device'], os.O_RDONLY | os.O_NONBLOCK | os.O_NOCTTY)
    pid = os.fork()
    if pid == 0:
        try:
            os.setsid(); null = os.open('/dev/null',os.O_RDWR)
            for target in (0,1,2): os.dup2(null,target)
            os.closerange(3,fd);os.closerange(fd+1,65536)
            login_audit(fd,root)
        finally: os._exit(0)
    os.close(fd)
    deadline=time.monotonic()+5
    while not (root/'audit-ready.json').exists() and time.monotonic()<deadline:time.sleep(.02)
    assert (root/'audit-ready.json').exists(), 'Login audit did not start'
    return dict(status='ready',timeout_seconds=timeout,half_budget_seconds=timeout/2,
        ticket=ticket,versions=versions,counters_started_before_username=True,observers_prepared=True)


def login_action(root, action, argument=0):
    state = json.loads((root/'state.json').read_text()); tty=state['tty']
    if action == 'begin':
        deadline=time.monotonic()+state['timeout']+5; stable=0
        while time.monotonic()<deadline:
            try:
                public=login_public(tty,fresh=True)
                _,line=screen(pathlib.Path('/dev/vcsa'+tty[3:]).read_bytes())
                stable=stable+1 if line.endswith('login:') else 0
                if stable>=3:
                    state.update(username_at=time.monotonic(),getty=public['reader'])
                    publish(root/'state.json',state)
                    return dict(ready=True,reader=public['reader'],fresh_getty=True,timeout_seconds=state['timeout'])
            except (OSError,AssertionError):stable=0
            time.sleep(.1)
        raise AssertionError('No fresh login prompt before username')
    if action == 'echo':
        # The administrator by default; package 27 also logs in the daily account.
        user=argument if argument in ('ares-recovery','ares') else 'ares-recovery'
        stable=0
        while login_remaining(state)>0:
            row=login_foreground(tty);_,line=screen(pathlib.Path('/dev/vcsa'+tty[3:]).read_bytes())
            assert row['pid']==state['getty']['pid'] and row['start']==state['getty']['start'], 'Username reader changed'
            stable=stable+1 if line.endswith(user) and not line.endswith('-'+user) else 0
            if stable>=3:return dict(ready=True,echo_matches=True,value_recorded=False)
            time.sleep(.1)
        return dict(ready=False,reason='budget-exceeded')
    if action == 'ready':
        stable=0;value=dict(ready=False)
        while login_remaining(state)>0:
            value=hidden_observation(tty,dict(kind='login'),'Password:')
            reader=value.get('reader')
            if reader and (reader['pid']!=state['getty']['pid'] or reader['start']!=state['getty']['start']):
                value.update(ready=False,reader_changed=True);return value
            stable=stable+1 if value['ready'] else 0
            if stable>=3:
                state['reader']=reader;publish(root/'state.json',state)
                return value
            time.sleep(.1)
        value.update(ready=False,reason='budget-exceeded');return value
    if action == 'arm':
        minimum,events=json.loads(argument)
        assert isinstance(minimum,(int,float)) and 0<minimum<=3600 and type(events) is int and 0<events<10000
        value=login_guard(state,minimum)
        if not value['ready']:return value
        baseline=checkpoint(state['ticket'],1)
        value=login_guard(state,minimum)
        if not value['ready']:return value
        state.update(armed=True,baseline=baseline['counts'],secret_events_expected=events);publish(root/'state.json',state)
        value['baseline']=baseline['counts'];return value
    if action == 'guard':return login_guard(state,float(argument))
    if action == 'sample':
        value=checkpoint(state['ticket'],int(argument))
        state['last_sample']=value['counts'];publish(root/'state.json',state)
        return value
    if action == 'enter':
        deadline=min(time.monotonic()+2,state['username_at']+state['timeout']/2)
        expected=sum(state['last_sample'][key]-state['baseline'][key] for key in ('press','release','repeat'))
        while True:
            assert not (root/'audit-result.json').exists(), 'Visibility observer ended before Enter'
            audit=json.loads((root/'audit.json').read_text())
            total=sum(sum(row[key] for key in ('press','release','repeat')) for row in audit['counts'].values())
            if total==expected:break
            assert time.monotonic()<deadline, 'Incomplete secret-event visibility observation'
            time.sleep(.02)
        # The current reader is checked after the potentially bounded audit wait.
        value=login_guard(state,1);value['exposure']=audit
        exposure=login_exposure(audit)
        state['armed']=False;publish(root/'state.json',state)
        value['secret_tainted']=exposure['secret_tainted']
        value['ready']=value['ready'] and not exposure['secret_tainted']
        return value
    if action == 'entered':
        elapsed=state['timeout']/2-login_remaining(state)
        return dict(elapsed_seconds=elapsed,timeout_seconds=state['timeout'],half_budget_seconds=state['timeout']/2,
            within_half_timeout=elapsed<=state['timeout']/2,counters_started_before_username=True,value_recorded=False)
    if action == 'finish':
        state.update(armed=False,audit_stop=True);publish(root/'state.json',state)
        result=finish(state['ticket']);deadline=time.monotonic()+3
        while not (root/'audit-result.json').exists() and time.monotonic()<deadline:time.sleep(.02)
        assert (root/'audit-result.json').exists(), 'Login audit did not finish'
        result['exposure']=json.loads((root/'audit-result.json').read_text())
        return result
    if action == 'clear':
        value=login_public(tty);state['clear_reader']=value['reader'];state['clear_ticket']=start()
        publish(root/'state.json',state)
        return dict(ready=True,**value)
    if action == 'cleared':
        result=checkpoint(state['clear_ticket'],1)
        assert compare(result,dict(key_event_count=4))['matches'], 'Line kill events not verified'
        public=login_public(tty,fresh=True)
        assert public['reader']==state['clear_reader'], 'Public reader changed during line kill'
        return dict(ready=True,vkill=21,reader=public['reader'],line_kill_events=4,
            eof_semantics='agetty2.41.5 CTRL-D exits without authenticating')
    if action == 'fresh':
        result=finish(state['clear_ticket'])
        assert compare(result,dict(key_event_count=8))['matches'], 'Line kill/public EOF events not verified'
        deadline=time.monotonic()+state['timeout']+5;stable=0
        while time.monotonic()<deadline:
            try:
                public=login_public(tty,fresh=True)
                _,line=screen(pathlib.Path('/dev/vcsa'+tty[3:]).read_bytes())
                stable=stable+1 if line.endswith('login:') and public['reader']['pid']!=state['clear_reader']['pid'] else 0
                if stable>=3:return dict(ready=True,fresh_login_prompt=True,reader=public['reader'],line_kill_events=4,public_eof_events=4)
            except (OSError,AssertionError):stable=0
            time.sleep(.1)
        raise AssertionError('No fresh login prompt after line kill')
    if action == 'cleanup':
        names={p.name for p in root.iterdir()}
        assert names <= {'observer.py','state.json','audit-ready.json','audit.json','audit-result.json'}
        assert (root/'audit-result.json').exists(), 'Audit still running'
        for p in root.iterdir():assert p.is_file() and not p.is_symlink();p.unlink()
        root.rmdir();return dict(status='cleaned')
    raise AssertionError('Unknown prepared login action')


def login_root(root):
    import stat
    info=root.lstat()
    assert re.fullmatch('/run/ares-login-[0-9a-f]{16}',str(root)) and not root.is_symlink()
    assert stat.S_ISDIR(info.st_mode) and info.st_uid==0 and info.st_mode&0o777==0o700


def guest_source(health=None):
    import owner_xhci
    counter=(owner_key_counter.keyboard,owner_key_counter.settings,owner_key_counter.released,
        owner_key_counter.count_events,owner_key_counter.private_root,owner_key_counter.publish,
        owner_key_counter.observe,owner_key_counter.start,owner_key_counter.checkpoint,owner_key_counter.finish,
        owner_key_counter.compare)
    hidden=(owner_console.interactive_shell,owner_console.process_snapshot,owner_console.screen,
        owner_hidden.hidden_snapshot,owner_hidden.reader_matches,owner_hidden.reader_chain,owner_hidden.redacted_chain,
        owner_hidden.identity,owner_hidden.same_process,owner_hidden.device_number,owner_hidden.reader_tty,
        owner_hidden.echo_at,owner_hidden.return_shells,owner_hidden.hidden_observation,owner_hidden.input_guard)
    functions=(*counter,*hidden,login_timeout,login_foreground,login_public,login_remaining,login_guard,
        login_visibility,login_audit_batch,login_exposure,login_audit,login_initialize,login_action,login_root)
    return owner_xhci.guard(('import base64,hashlib,json,os,pathlib,re,sys,time,termios\n'
        +''.join(inspect.getsource(f) for f in functions)+'''
root=pathlib.Path(__file__).parent
login_root(root)
assert hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()==sys.argv[2]
value=login_initialize(root,sys.argv[3]) if sys.argv[1]=='init' else login_action(root,sys.argv[1],sys.argv[3] if len(sys.argv)>3 else 0)
raw=json.dumps(value).encode()
print('\\nARESOS_EXPORT_START')
print(base64.encodebytes(raw).decode(),end='')
print('ARESOS_EXPORT_END')
print('ARESOS_EXPORT_SHA256 '+hashlib.sha256(raw).hexdigest()+'  guest.json')
'''),health)


class Prepared:
    def __init__(self,console,stage):
        import base64,secrets
        from switch_vm import framed
        self.console,self.guest,self.stage=console,console.guest,stage
        self.started=None
        self.finished=False
        self.public_baseline=None
        self.root='/run/ares-login-'+secrets.token_hex(8)
        raw=guest_source(owner_xhci.context(self.guest)).encode();self.digest=hashlib.sha256(raw).hexdigest()
        compile(raw,'prepared-login-observer','exec')
        source='''set -e
test "$(/usr/bin/findmnt -n -o FSTYPE -T /run)" = tmpfs
python3 - <<'ARES_LOGIN_PREPARE'
import base64,hashlib,os,pathlib
root=pathlib.Path(@ROOT@);root.mkdir(mode=0o700)
raw=base64.b64decode(@BODY@)
assert hashlib.sha256(raw).hexdigest()==@SHA@
compile(raw,'prepared-login-observer','exec')
fd=os.open(root/'observer.py',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
with os.fdopen(fd,'wb') as f:f.write(raw)
ARES_LOGIN_PREPARE
'''.replace('@ROOT@',repr(self.root)).replace('@BODY@',repr(base64.b64encode(raw).decode())).replace('@SHA@',repr(self.digest))
        self.guest.command(stage+'-login-observers-prepare',source)
        value=self.rpc('init',console.tty,timeout=20)
        assert value['status']=='ready' and value['counters_started_before_username'] and value['observers_prepared']
        self.timeout=value['timeout_seconds'];self.ticket=value['ticket']

    def rpc(self,action,argument=None,timeout=None):
        from serial_console import decode_export
        import two_disk_vm as td
        command='python3 -B '+shlex.quote(self.root+'/observer.py')+' '+action+' '+self.digest
        if argument is not None:command+=' '+shlex.quote(str(argument))
        assert len(command.encode())<=256, 'Prepared login control must stay inline'
        seconds=timeout if timeout is not None else max(.1,min(10,self.remaining()))
        name=self.stage+'-login-fast-'+action+'-'+str(getattr(self,'sequence',0));self.sequence=getattr(self,'sequence',0)+1
        value=json.loads(decode_export(self.guest.command(name,command,timeout=seconds)))
        if action=='arm' and value.get('ready'):self.public_baseline=value['baseline']
        td.save(name,value)
        return value

    def remaining(self):
        return self.timeout/2-(time.monotonic()-self.started) if self.started is not None else self.timeout/2

    def begin(self):
        # Waiting for an old failed login to expire is outside the measured window.
        value=self.rpc('begin',timeout=self.timeout+6);assert value['ready'] and value['fresh_getty']
        self.started=time.monotonic()
        # Guest starts its clock before returning; it is independently checked at every gate.
        return value

    def guard(self,pending,phase,minimum=0):
        value=self.rpc('enter' if phase.startswith('before-enter') else 'guard',minimum)
        if value.get('secret_tainted'):mark_tainted(self.guest,value.get('exposure'),'observer saw non-hidden or unknown secret events')
        if value.get('reader_changed'):
            pending['login_last_guard']=value
            if pending.get('counts',{}).get('key_event_count',0):mark_tainted(self.guest,value.get('exposure'),'reader replaced during hidden value',pending['counts']['key_event_count'])
            raise ReaderChanged('Login reader replaced; Enter withheld')
        assert self.remaining()>minimum and value['remaining_seconds']>minimum, 'Login half-timeout budget exceeded; no secret/Enter'
        return value

    def finish(self):
        value=self.rpc('finish',timeout=10);self.finished=True
        audit=value['exposure'];self.exposure=audit
        possible=(sum(value['counts'][k]-self.public_baseline[k] for k in ('press','release','repeat'))
            if self.public_baseline is not None else 0)
        if login_exposure(audit)['secret_tainted'] and possible:
            mark_tainted(self.guest,audit,'non-hidden, unknown or incomplete secret-key observation',possible)
        return value

    def clear_and_fresh(self):
        value=self.rpc('clear',timeout=10)
        assert value['ready'] and value['vkill']==21, 'Replacement line kill unproved'
        self.guest.owner_input_epoch=getattr(self.guest,'owner_input_epoch',0)+1
        self.guest.keys(['ctrl','u'])
        cleared=self.rpc('cleared',timeout=10)
        assert cleared['ready'] and cleared['vkill']==21 and cleared['line_kill_events']==4
        # Source-verified public getty EOF creates a new alarm lifetime. It
        # also avoids trusting cursor erasure of multibyte username fragments.
        self.guest.owner_input_epoch=getattr(self.guest,'owner_input_epoch',0)+1
        self.guest.keys(['ctrl','d'])
        value=self.rpc('fresh',timeout=self.timeout+6)
        assert value['ready'] and value['fresh_login_prompt'] and value['line_kill_events']==value['public_eof_events']==4
        return value

    def cleanup(self):
        if not self.finished:self.finish()
        assert self.rpc('cleanup',timeout=10)['status']=='cleaned'


def mark_tainted(guest,counts,reason,possible_events=0):
    import two_disk_vm as td
    guest.secret_tainted=True
    # This is a run-wide policy, including screenshots from later boot objects.
    guest.__class__.run_secret_tainted=True
    guest.screenshot_safe=False
    observed=counts.get('counts',{}) if counts else {}
    non_hidden=sum(observed.get('non_hidden',{}).get(k,0) for k in ('press','release','repeat'))
    unknown=sum(observed.get('unknown',{}).get(k,0) for k in ('press','release','repeat'))
    observation=dict(reason=reason,counts=counts,possible_non_hidden_events=dict(minimum=non_hidden,
        maximum=max(possible_events,non_hidden+unknown)),classification='event batches bracketed by reader identity/ECHO; unknown is conservative')
    observations=[*guest.__class__.__dict__.get('run_login_taints',[]),observation]
    guest.__class__.run_login_taints=observations
    td.save('owner-login-visual-taint',dict(secret_tainted=True,private_only=True,never_commit=True,
        scope='all run VCSA, raw screen fields and screenshots',observations=observations,counts_only=True,value_recorded=False))
