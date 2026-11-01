import pathlib,json,re,sys
r=pathlib.Path.cwd();w=r/'.work/14';run=int(sys.argv[1]);b=w/('run-'+str(run));e=b/'evidence'
NATIVE_TESTS=json.loads((r/'os/manifest/ci/14/14zzb-preflight/preparation.json').read_text())['whole_suite']['tests']

def read(p):return json.loads(p.read_text(encoding='utf-8'))
receipt=read(b/'receipt.json');assert receipt['status']=='success' and receipt['head']==read(w/'14zzb-one-push-scan.json')['checked_commit']
privacy=read(b/'14zzb-privacy-classification.json');assert privacy['status']=='passed'
assert read(w/'gitleaks/14zzb-owner-tools-native.json')==[]
log=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',log);assert m and int(m[1])==NATIVE_TESTS and re.search(r'Z OK\s*$',log,re.M)
native=read(e/'14-native-owner-devices.json');assert native['status']=='passed' and native['helper_mutations']==0 and native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
iso=read(e/'installer/iso-download.json');assert iso['status']=='passed' and iso['bytes']==9068650496 and iso['sha256']==iso['downloaded_sha256']==iso['official_sha256']
proof=read(e/'two-disk/owner-tools-result.json');assert proof['status']=='passed' and proof['commit']==receipt['head'] and proof['order']=='protected-second'
assert proof['release']==read(r/'os/manifest/release.json')['reference'] and proof['bundle_manifest']=='320ca9878367ee1da4d4634e74d1e3b2de0027d1e7436955f4c69eb21ab806a6'
assert proof['layout_profiles']==['de','us-failed','de-revert','us-intl','de']
for key,value in proof.items():
 if isinstance(value,bool):assert value,key
commands=[read(p) for p in (e/'two-disk').glob('*-command.json')];commands=[v for v in commands if v.get('physical') is True]
assert commands and all(v['command'] in read(r/'os/owner-tools/commands.json').values() for v in commands)
transfers=[read(p) for p in (e/'two-disk').glob('*-transport.json')];staged=[v for v in transfers if v.get('staged') is True]
assert staged and all(v['verified'] and all(x['status']=='passed' for x in v['steps']) for v in staged)
resyncs=[(p,read(p)) for p in (e/'two-disk').glob('*-wait-*-resync-*.json')]
waits={}
for path,event in resyncs:
 assert event['enter_sent'] is True and event['observer']['ready'] is True
 assert event['observer']['foreground_shell'] is True and event['observer']['observation']['ready'] is True
 assert event['observer']['observation']['foreground_chain'] and event['after_cursor_line'] is not None
 assert not re.search(r'[$#]$',event['before_cursor_line'])
 assert event['attempt'] in (1,2) and event['stage'] in path.name
 waits.setdefault(event['stage'],[]).append(event['attempt'])
 answer=read(path.with_name(event['stage']+'-idle-'+str(event['attempt'])+'.json'))
 assert {k:v for k,v in answer.items() if k!='raw'}==event['observer']
assert all(sorted(v)==list(range(1,len(v)+1)) and len(v)<=2 for v in waits.values())
logins=[(p,read(p)) for p in (e/'two-disk').glob('*-physical-login-result.json')]
assert logins and {v['tty'] for _,v in logins}=={'tty3','tty4'}
aborted=[]
for path,result in logins:
 assert result['status'] in ('passed','expected-rejection') and result['attempts'] in (1,2)
 assert result['reader_replacements']==result['attempts']-1 and result['value_recorded'] is False
 timing=result['timing']
 assert timing['counters_started_before_username'] and timing['within_half_timeout']
 assert 0<=timing['elapsed_seconds']<=timing['half_budget_seconds']==timing['timeout_seconds']/2
 prefix=path.name.removesuffix('-physical-login-result.json')
 restarts=sorted((e/'two-disk').glob(prefix+'-login-reader-restart-*.json'))
 assert len(restarts)==result['reader_replacements']
 if restarts:
  restart=read(restarts[0]);fresh=restart['fresh']
  assert restart['attempt']==1 and fresh['ready'] and fresh['fresh_login_prompt']
  assert fresh['line_kill_events']==fresh['public_eof_events']==4
  aborted.append(prefix+'-password-prompt-read-wait-')
def retired(path):return any(path.name.startswith(prefix) for prefix in aborted)
stops=list((e/'two-disk').glob('*-pre-enter-stop.json'))
assert all(retired(p) and read(p)['enter_sent'] is False and read(p)['value_recorded'] is False for p in stops)
taint=e/'two-disk/owner-login-visual-taint.json'
if taint.exists():
 v=read(taint);assert v['secret_tainted'] and v['private_only'] and v['never_commit'] and v['counts_only'] and not v['value_recorded']
hidden_ready=sorted((e/'two-disk').glob('*-read-wait-*.json'))
hidden_ready=[p for p in hidden_ready if re.search(r'-read-wait-[0-9]+\.json$',p.name) and not retired(p)]
assert len(hidden_ready)==23, ('hidden readiness count',len(hidden_ready))
for path in hidden_ready:
 ready=read(path);left=read(path.with_name(path.stem+'-left.json'))
 assert ready['ready'] is True and ready['prompt_at_cursor'] is True and ready['reader_echo_enabled'] is False
 assert ready['reader']['exe'] and ready['reader']['tty_path'] and not ready.get('raw')
 assert left['value_recorded'] is False and left['completion_uses_echo'] is False
 if 'layout-plain-us' in path.name:
  assert left['rejected'] is True and left['ready'] is False
 else:
  if not left['ready']:
   assert left['reader_left'] and left['shell_idle'] and not left['prompt_at_cursor']
   left=read(path.with_name(path.stem+'-left-after-resync.json'))
  assert left['ready'] is True and left['reader_left'] is True and not left.get('raw')
 assert all(v.get('argv_redacted') is True and v['argv']==['[redacted]'] for v in ready['observation']['foreground_chain'])
handoffs=[read(p) for p in (e/'two-disk').glob('*-handoff-*.json')]
assert len(handoffs)==3 and all(v['ready'] is False and v['handoff_ready'] is True and v['reader_left'] is True and v['completion_uses_echo'] is False for v in handoffs)
completed=[read(p) for p in (e/'two-disk').glob('*-hidden-completed.json')]
assert len(completed)==22 and all(v['completion_uses_echo'] is False and v['foreground_shell'] is True and v['token_recorded'] is False for v in completed)
dummy=read(e/'two-disk/owner-length-token-proof.json');assert dummy['status']=='passed' and dummy['length']==40 and dummy['outcome']=='expected-registry-refusal' and dummy['comparison']['matches']
key_results=[read(p) for p in (e/'two-disk').glob('*-key-counter-result.json') if not p.name.startswith('probe-') and not retired(p)]
assert len(key_results)==23 and all(v['comparison']['matches'] and v['received']['counts_only'] and v['received']['complete'] and v['received']['counts']['syn_dropped']==0 for v in key_results)
pre_enter=[read(p) for p in (e/'two-disk').glob('*-pre-enter-proof.json') if not retired(p)]
assert len(pre_enter)==23 and all(p['status']=='passed' and p['enter_sent'] is False
    and p['accepted_attempt']==len(p['attempts']) in (1,2) and p['attempts'][-1]['comparison']['matches'] for p in pre_enter)
for p in pre_enter:
 assert all(a['sent']['last_key_was_ret'] is False for a in p['attempts'])
 if len(p['attempts'])==2:
  assert not p['attempts'][0]['comparison']['matches'] and p['clear']['ready']
  assert p['clear']['canonical'] and p['clear']['vkill']==21 and p['clear']['reader_still_waiting'] and not p['clear']['enter_sent']
for v in key_results:
 assert v['whole_window']['complete'] and v['whole_window']['keys_released'] and v['whole_window']['counts']['syn_dropped']==0
 assert v['received']['counts']['repeat']==0 and v['received']['counts']['press']==v['attempts'][-1]['comparison']['press']+1
 assert v['whole_window']['counts']['press']==sum(a['comparison']['press'] for a in v['attempts'])+1+(2 if v['clear'] else 0)
 assert v['whole_window']['counts']['release']==sum(a['comparison']['release'] for a in v['attempts'])+1+(2 if v['clear'] else 0)
 assert v['whole_window']['counts']['repeat']==sum(a['comparison']['repeat'] for a in v['attempts'])
guards=[(p,read(p)) for p in (e/'two-disk').glob('*-input-guard-*.json') if re.search(r'-input-guard-(?:before-value-[12]|before-enter-[12]|before-clear|after-clear)\.json$',p.name) and not retired(p)]
assert len(guards)>=46 and all(v['ready'] and v['syscall_number']==0 and v['echo_enabled'] is False
    and v['value_recorded'] is False and v['queue_contents_read'] is False for p,v in guards)
assert all(v['canonical'] and v['vkill']==21 for p,v in guards if p.stem.endswith(('-before-clear','-after-clear')))
echoes=[read(p) for p in (e/'two-disk').glob('*-echo-*.json') if re.search(r'-echo-[0-9]+\.json$',p.name)]
assert echoes and all(v['ready'] and v['echo_matches'] and not v['value_recorded'] for v in echoes)
timings=[read(p)['keyboard_timing'] for p in (e/'two-disk').glob('*-owner-route.json')]
assert timings and all(t==dict(hold_ms=30,minimum_gap_ms=120) for t in timings)

switch=read(e/'two-disk/owner-switch-owner-diagnostics.json');assert switch['status']=='passed'
observed=[p for t in switch['trace'] if t.get('observation')=='deployment-processes' for p in t['processes']]
helpers=[p for p in observed if p.get('excluded_as_system_helper') is True]
assert helpers,'STOP: no real post-staging hold-helper classification retained'
for p in helpers:
 assert p['exe']=='/usr/bin/ostree' and p['cmdline']==['/usr/bin/ostree','admin','finalize-staged','--hold'] and p['cgroup'].splitlines()==['0::/system.slice/ostree-finalize-staged-hold.service']
audits=read(b/'independent-audits.json');assert audits['status'].startswith('passed')
value=dict(status='passed independent qualification evidence review',run=run,head=receipt['head'],artifact=receipt,native_tests=NATIVE_TESTS,native_seconds=float(m[2]),native_skips=0,loop_checks=len(native['checks']),loop_mutations=0,protected_fixture_unchanged=True,fixture_cleanup=True,qualification=proof,physical_owner_command_records=len(commands),fresh_idle_resyncs=len(resyncs),resynced_waits=len(waits),staged_transfers=len(staged),staged_sha_and_syntax_verified=True,privacy=privacy,independent_audits=audits,acceptance_met=True,hidden_ready_and_left_pairs=len(hidden_ready),hidden_value_recorded=False)
(b/'14zzb-qualification-proof.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n');print('QUALIFICATION_ACCEPTED',run,NATIVE_TESTS,'native tests;',len(commands),'physical owner records;',len(staged),'verified transfers; unknown artifact findings0')

sys.path.insert(0,str(r/'os/ci'))
from owner_keys import at_keycodes
at=[read(p) for p in (e/'two-disk').glob('boot-*-at-keyboard.json')]
assert at and all(v['name']=='AT Translated Set 2 keyboard' and v['bus']==17 and
    v['static_keycodes_checked']==len(at_keycodes()) and re.fullmatch('/dev/input/event[0-9]+',v['device']) for v in at)
health=[read(p) for p in (e/'two-disk').glob('*-xhci-health.json')]
assert health and all(v['counts_only'] is True and v['stop'] is False for v in health)
caps=read(e/'14-host-capabilities.json')
assert caps['qemu']['keyboard']=='i8042/ps2-kbd; qtree verified'
extra=dict(status='passed actual PS2 boot/static mappings and counts-only xHCI health records',at_boots=len(at),
    static_keycodes_checked=len(at_keycodes()),health_checkpoints=len(health),hardware='actual disposable runner/guest, not local stand-ins')
(b/'14zzb-ps2-health-proof.json').write_text(json.dumps(extra,indent=2)+'\n',encoding='utf-8',newline='\n')
print('PS2_HEALTH_ACCEPTED',len(at),len(health))
