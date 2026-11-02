import pathlib,json,hashlib,re
r=pathlib.Path.cwd();b=r/'.work/14/run-40826092372';e=b/'evidence/two-disk'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
owner=[]
for p in sorted(e.glob('*-owner-diagnostics.json')):
    v=read(p);row=dict(sha256=digest(p),path=p.relative_to(b).as_posix(),status=v['status'],command=v.get('command'),error=v.get('error'),mutations=sum(t.get('mutation') is True for t in v.get('trace',[])),trace_length=len(v.get('trace',[])))
    owner.append(row)
    print('OWNER',json.dumps(row))
v=read(e/'owner-switch-owner-diagnostics.json')
print('STOP_LAST_COMMANDS',json.dumps([dict(command=t.get('command'),event=t.get('event'),returncode=t.get('returncode'),mutation=t.get('mutation'),error=t.get('error'),stderr=t.get('stderr','')[-1500:]) for t in v['trace'][-6:]]))
counters=[]
for p in sorted(e.glob('*-key-counter-result.json')):
    v=read(p);stage=p.stem.removesuffix('-key-counter-result');sent=read(p.with_name(stage+'-key-events-sent.json'));pre=read(p.with_name(stage+'-pre-enter-proof.json'))
    row=dict(sha256=digest(p),path=p.relative_to(b).as_posix(),sent=sent,received=v['received'],comparison=v['comparison'],whole_window=v['whole_window'],attempts=v['attempts'],clear=v['clear'],pre_enter=pre)
    assert v['comparison']['matches'] and v['whole_window']['complete'] and v['whole_window']['keys_released']
    assert v['whole_window']['counts']['repeat']==v['whole_window']['counts']['syn_dropped']==0
    assert pre['status']=='passed' and pre['accepted_attempt']==len(pre['attempts'])==1 and not pre['enter_sent']
    assert sent['last_key_was_ret'] and v['received']['codes_recorded'] is v['received']['values_recorded'] is False
    counters.append(row)
    print('COUNTER',stage,'length',sent['length'],'events',sent['key_event_count'],json.dumps(v['comparison']),'seconds',v['whole_window']['seconds'],'attempts',len(v['attempts']))
    if sent.get('chunked'):assert sent['chunk_size']==16 and sent['between_chunks_seconds']==sent['before_return_seconds']==1
diagnostics=[]
for p in sorted(e.glob('*-diagnostics-*.json')):
    v=read(p)
    if v.get('kind')!='hidden-read-diagnostics':continue
    assert v['read_only'] and not v['value_recorded'] and not v['queue_contents_read'] and not v['syscall_arguments_recorded']
    diagnostics.append(dict(sha256=digest(p),path=p.relative_to(b).as_posix(),value=v))
    print('HIDDEN_DIAGNOSTICS',p.name,v['phase'],'length',v['typed']['length'],'last_return',v['typed']['last_key_was_ret'])
guards=[]
for p in sorted(e.glob('*-input-guard-*.json')):
    if not re.search(r'-input-guard-(?:before-value-[12]|before-enter-[12]|before-clear|after-clear)\.json$',p.name):continue
    v=read(p);assert v['ready'] and v['syscall_number']==0 and not v['echo_enabled'] and not v['value_recorded'] and not v['queue_contents_read']
    guards.append(dict(sha256=digest(p),path=p.relative_to(b).as_posix(),value=v))
hidden=[]
for p in sorted(e.glob('*-read-wait-*.json')):
    if not re.search(r'-read-wait-[0-9]+\.json$',p.name):continue
    ready=read(p);left=read(p.with_name(p.stem+'-left.json'))
    assert ready['ready'] and ready['prompt_at_cursor'] and ready['reader_echo_enabled'] is False
    assert left['ready'] and left['reader_left'] and left['completion_uses_echo'] is False and not left.get('raw')
    assert all(v['argv_redacted'] and v['argv']==['[redacted]'] for v in ready['observation']['foreground_chain'])
    ready.pop('raw',None);hidden.append(dict(sha256=digest(p),path=p.relative_to(b).as_posix(),ready=ready,left=left))
echoes=[p for p in e.glob('*-echo-*.json') if re.search(r'-echo-[0-9]+\.json$',p.name)]
assert echoes and all(read(p)['ready'] and read(p)['echo_matches'] and not read(p)['value_recorded'] for p in echoes)
transfers=[read(p) for p in e.glob('*-transport.json')];staged=[v for v in transfers if v.get('staged')]
assert staged and all(v['verified'] and all(s['status']=='passed' for s in v['steps']) for v in staged)
assert len(counters)==len(hidden)==6 and len(guards)==12
assert any(v.get('event')=='STOP' for v in read(e/'corrected-stock-qmp.json'))
summary=dict(status='read-only inspected retained failure evidence; no rerun',run=40826092372,head=read(b/'receipt.json')['head'],owner_records=owner,counters=counters,hidden_diagnostics=diagnostics,input_guards=guards,hidden_ready_and_left_pairs=hidden,visible_echo_proofs=len(echoes),successful_hidden_completions=len(list(e.glob('*-hidden-completed.json'))),verified_staged_transfers=len(staged),pre_enter_stops=len(list(e.glob('*-pre-enter-stop.json'))),token_value_or_ordered_keys_recorded=False,paused_stop_observed=True)
(b/'14zp-diagnostics-review.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8',newline='\n')
print('SUMMARY',len(owner),'owner records;',len(counters),'verified hidden windows;',len(guards),'read0 guards;',len(echoes),'echoes;',len(staged),'verified transfers; hidden completions',summary['successful_hidden_completions'])
