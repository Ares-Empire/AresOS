import pathlib,json,hashlib,re,collections
r=pathlib.Path.cwd();b=r/'.work/14/run-40866713472';e=b/'evidence/two-disk'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(sha256=sha(p),path=p.relative_to(b).as_posix())
records=[];holds=[];properties=[];journals=[]
for p in sorted(e.glob('*-owner-diagnostics.json')):
 v=read(p);record=dict(**ref(p),status=v['status'],command=v.get('command'),error=v.get('error'),mutations=sum(t.get('mutation') is True for t in v.get('trace',[])))
 records.append(record)
 for t in v.get('trace',[]):
  if t.get('observation')=='deployment-processes':
   for process in t['processes']:
    if process.get('excluded_as_system_helper') is True:holds.append(dict(**ref(p),process=process))
  command=t.get('command',[])
  if command[:2]==['loginctl','show-session']:
   assert t['returncode']==0 and not t['stderr']
   rows=[line.split('=',1) for line in t['stdout'].splitlines()];names=[c.removeprefix('--property=') for c in command[3:]]
   assert all(c.startswith('--property=') and ',' not in c for c in command[3:])
   assert len(rows)==len(names) and all(len(row)==2 for row in rows) and {row[0] for row in rows}==set(names)
   properties.append(dict(**ref(p),command=command,stdout=t['stdout'],returncode=0,each_key_once=True))
  if command and command[0]=='journalctl':
   assert command==['journalctl','-b','-1','-u','systemd-logind.service','--lines=200','--output=json','--no-pager']
   rows=[json.loads(line) for line in t['stdout'].splitlines()];assert len(rows)<=200
   assert not any(x.get('_TRANSPORT')=='kernel' for x in rows)
   journals.append(dict(**ref(p),command=command,records=len(rows),transports=dict(collections.Counter(x.get('_TRANSPORT') for x in rows)),kernel_records=0,messages_saved=False))
for item in holds:
 p=item['process'];assert p['exe']=='/usr/bin/ostree' and p['cmdline']==['/usr/bin/ostree','admin','finalize-staged','--hold']
 assert p['cgroup'].splitlines()==['0::/system.slice/ostree-finalize-staged-hold.service']
counters=[]
for p in sorted(e.glob('*-key-counter-result.json')):
 if p.name.startswith('probe-'):continue
 v=read(p);stem=p.stem.removesuffix('-key-counter-result');sent=read(p.with_name(stem+'-key-events-sent.json'));proof=read(p.with_name(stem+'-pre-enter-proof.json'))
 assert v['comparison']['matches'] and v['whole_window']['complete'] and v['whole_window']['keys_released']
 assert v['whole_window']['counts']['repeat']==v['whole_window']['counts']['syn_dropped']==0
 assert v['received']['codes_recorded'] is False and v['received']['values_recorded'] is False
 counters.append(dict(**ref(p),stage=stem,length=sent['length'],events_sent=sent['key_event_count'],last_key_was_ret=sent['last_key_was_ret'],counts=v['whole_window']['counts'],comparison=v['comparison'],seconds=v['whole_window']['seconds'],pre_enter=proof,attempts=len(v['attempts']),clear_used=v.get('clear') is not None))
guards=[]
for p in sorted(e.glob('*-input-guard-*.json')):
 if not re.search(r'-input-guard-(?:before-value-[12]|before-enter-[12]|before-clear|after-clear)\.json$',p.name):continue
 v=read(p);assert not v['value_recorded'] and not v['queue_contents_read']
 assert all(x['argv_redacted'] and x['argv']==['[redacted]'] for x in v['observation']['foreground_chain'])
 guards.append(dict(**ref(p),value=v))
failed=[x for x in guards if not x['value']['ready']];assert len(failed)==1
prefix='layout-reverted-login-password-prompt-read-wait-112'
before=read(e/(prefix+'-input-guard-before-value-1.json'));after=read(e/(prefix+'-input-guard-before-enter-1.json'));stop=read(e/(prefix+'-pre-enter-stop.json'));diagnostics=read(e/(prefix+'-diagnostics-input-refused.json'))
assert before['ready'] and before['syscall_number']==0 and before['observation']['foreground_chain'][0]['pid']==13852
assert not after['ready'] and after['observation']['foreground_chain'][0]['pid']==20186
assert stop['enter_sent'] is False and len(stop['attempts'])==1 and not stop['clear']
assert not diagnostics['value_recorded'] and not diagnostics['queue_contents_read'] and not diagnostics['syscall_arguments_recorded']
assert diagnostics['processes'][0]['pid']==13852 and diagnostics['processes'][0]['stat_error']['kind']=='FileNotFoundError'
transfers=[read(p) for p in e.glob('*-transport.json')];staged=[v for v in transfers if v.get('staged')]
assert all(v['verified'] and all(x['status']=='passed' for x in v['steps']) for v in staged)
echoes=[read(p) for p in e.glob('*-echo-*.json') if re.search(r'-echo-[0-9]+\.json$',p.name)]
assert all(v['ready'] and v['echo_matches'] and not v['value_recorded'] for v in echoes)
qmp=read(e/'aresos-qmp.json');assert any(x.get('event')=='STOP' for x in qmp)
versions=[]
for p in e.glob('*-boot-console.txt'):
 text=p.read_text(errors='replace')
 for match in re.finditer(r'systemd\s+([0-9][0-9A-Za-z.~-]*)\s+running in system mode',text):versions.append(dict(**ref(p),version=match[1]))
v=dict(status='STOP; read-only retained evidence review',run=40866713472,head=read(b/'receipt.json')['head'],owner_records=records,
 actual_hold_observations=holds,loginctl_properties=properties,scoped_journals=journals,counters=counters,input_guards=guards,
 failed_guard=failed[0],guard_before=before,guard_after=after,pre_enter_stop=stop,hidden_diagnostics=diagnostics,
 visible_echo_proofs=len(echoes),verified_staged_transfers=len(staged),hidden_completions=len(list(e.glob('*-hidden-completed.json'))),
 expected_plain_us_rejection=read(e/'layout-plain-us-failure.json'),paused_stop_observed=True,systemd_boot_versions=versions,
 cause_proven='original foreground login PID disappeared during the typing/serial-observation interval; replacement foreground did not match the verified reader',
 exit_cause_not_proven=True,raw_console_or_credential_value_saved=False)
(b/'14zr-outcome-review.json').write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
print('OUTCOME',len(records),'owner records;',len(holds),'hold observations;',len(properties),'real property queries;',len(journals),'bounded journals')
print('COUNTERS',len(counters),'all match,0repeats/0SYN;',len(guards),'guards/',len(failed),'refusal;',len(staged),'verified staged transfers;',len(echoes),'visible echo proofs')
print('OWNER_STATUSES',[(x['command'],x['status'],x['error']) for x in records])
print('JOURNAL_COUNTS',[(x['records'],x['transports']) for x in journals])
print('SYSTEMD_BOOT_VERSIONS',sorted({x['version'] for x in versions}))
