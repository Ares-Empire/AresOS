import pathlib,json,hashlib,re
r=pathlib.Path.cwd();b=r/'.work/14/run-40844950597';e=b/'evidence/two-disk'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
records=[];observed=[]
for p in sorted(e.glob('*-owner-diagnostics.json')):
    v=read(p);record=dict(sha256=sha(p),path=p.relative_to(b).as_posix(),status=v['status'],command=v.get('command'),error=v.get('error'),mutations=sum(t.get('mutation') is True for t in v.get('trace',[])))
    records.append(record);print('OWNER',json.dumps(record))
    for i,t in enumerate(v.get('trace',[])):
        if t.get('observation')=='deployment-processes':
            for process in t['processes']:
                observed.append(dict(sha256=sha(p),path=p.relative_to(b).as_posix(),trace_index=i,process=process))
helpers=[v for v in observed if v['process'].get('excluded_as_system_helper') is True]
assert helpers
for v in helpers:
    p=v['process'];assert p['exe']=='/usr/bin/ostree' and p['cmdline']==['/usr/bin/ostree','admin','finalize-staged','--hold'] and p['cgroup'].splitlines()==['0::/system.slice/ostree-finalize-staged-hold.service'] and p['excluded_as_daemon'] is False
print('ACTUAL_HOLD_IDENTITIES',json.dumps(sorted({json.dumps(v['process'],sort_keys=True) for v in helpers})))
failed=next(v for v in records if v['path'].endswith('layout-us-begin-owner-diagnostics.json'))
failure=read(b/failed['path'])
print('LAYOUT_LAST_COMMANDS',json.dumps([dict(command=t.get('command'),script=t.get('script'),observation=t.get('observation'),returncode=t.get('returncode'),mutation=t.get('mutation'),stderr=t.get('stderr','')[-1600:]) for t in failure['trace'][-8:]]))
counters=[]
for p in sorted(e.glob('*-key-counter-result.json')):
    if p.name.startswith('probe-'):continue
    v=read(p);stage=p.stem.removesuffix('-key-counter-result');sent=read(p.with_name(stage+'-key-events-sent.json'));proof=read(p.with_name(stage+'-pre-enter-proof.json'))
    assert v['comparison']['matches'] and v['whole_window']['complete'] and v['whole_window']['keys_released']
    assert v['whole_window']['counts']['repeat']==v['whole_window']['counts']['syn_dropped']==0
    assert proof['status']=='passed' and proof['accepted_attempt']==len(proof['attempts'])==1 and not proof['enter_sent']
    counters.append(dict(sha256=sha(p),path=p.relative_to(b).as_posix(),sent=sent,received=v['received'],comparison=v['comparison'],whole_window=v['whole_window'],pre_enter=proof))
    print('COUNTER',stage,'length',sent['length'],'sent/received',sent['key_event_count'],v['comparison']['received_events'],'seconds',v['whole_window']['seconds'])
guards=[]
for p in sorted(e.glob('*-input-guard-*.json')):
    if not re.search(r'-input-guard-(?:before-value-[12]|before-enter-[12]|before-clear|after-clear)\.json$',p.name):continue
    v=read(p);assert v['ready'] and v['syscall_number']==0 and not v['echo_enabled'] and not v['value_recorded'] and not v['queue_contents_read']
    guards.append(dict(sha256=sha(p),path=p.relative_to(b).as_posix(),value=v))
diagnostics=[]
for p in sorted(e.glob('*-diagnostics-*.json')):
    v=read(p)
    if v.get('kind')!='hidden-read-diagnostics':continue
    assert v['read_only'] and not v['value_recorded'] and not v['queue_contents_read'] and not v['syscall_arguments_recorded']
    diagnostics.append(dict(sha256=sha(p),path=p.relative_to(b).as_posix(),value=v))
hidden=[]
for p in sorted(e.glob('*-read-wait-*.json')):
    if not re.search(r'-read-wait-[0-9]+\.json$',p.name):continue
    ready=read(p);left=read(p.with_name(p.stem+'-left.json'))
    assert ready['ready'] and ready['prompt_at_cursor'] and ready['reader_echo_enabled'] is False
    if not left['ready'] and left.get('reader_left') and left.get('shell_idle') and not left.get('prompt_at_cursor'):
        left=read(p.with_name(p.stem+'-left-after-resync.json'))
    assert left['ready'] and left['reader_left'] and left['completion_uses_echo'] is False and not left.get('raw')
    assert all(x['argv_redacted'] and x['argv']==['[redacted]'] for x in ready['observation']['foreground_chain'])
    ready.pop('raw',None);left.pop('raw',None)
    hidden.append(dict(sha256=sha(p),path=p.relative_to(b).as_posix(),ready=ready,left=left))
echoes=[p for p in e.glob('*-echo-*.json') if re.search(r'-echo-[0-9]+\.json$',p.name)]
assert echoes and all(read(p)['ready'] and read(p)['echo_matches'] and not read(p)['value_recorded'] for p in echoes)
transfers=[read(p) for p in e.glob('*-transport.json')];staged=[v for v in transfers if v.get('staged')]
assert staged and all(v['verified'] and all(s['status']=='passed' for s in v['steps']) for v in staged)
assert len(hidden)==len(counters)==8 and len(guards)==16
assert any(x.get('event')=='STOP' for x in read(e/'aresos-qmp.json'))
summary=dict(status='read-only retained outcome review; no rerun',run=40844950597,head=read(b/'receipt.json')['head'],owner_records=records,process_observations=observed,actual_hold_observations=helpers,counters=counters,input_guards=guards,hidden_diagnostics=diagnostics,hidden_pairs=hidden,visible_echo_proofs=len(echoes),verified_staged_transfers=len(staged),hidden_completions=len(list(e.glob('*-hidden-completed.json'))),pre_enter_stops=len(list(e.glob('*-pre-enter-stop.json'))),raw_console_or_secret_value_recorded=False,paused_stop_observed=True)
(b/'14zq-outcome-review.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
print('SUMMARY',len(records),'ownerrecords;',len(helpers),'actualhold observations;',len(counters),'hidden windows;',len(guards),'guards;',len(echoes),'echoes;',len(staged),'transfers;',summary['hidden_completions'],'completed hidden')
