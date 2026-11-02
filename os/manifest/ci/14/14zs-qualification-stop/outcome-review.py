import pathlib,json,hashlib,re,sys
r=pathlib.Path.cwd();b=r/'.work/14/run-40897501964';e=b/'evidence/two-disk';sys.path.insert(0,str(r/'os/ci'));import owner_console
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def ref(p):return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(b).as_posix())
records=[]
for p in sorted(e.glob('*-owner-diagnostics.json')):
 v=read(p);assert v['status']=='passed'
 records.append(dict(**ref(p),status=v['status'],command=v.get('command'),mutations=sum(x.get('mutation') is True for x in v.get('trace',[]))))
logins=[]
for p in sorted(e.glob('*-physical-login-result.json')):
 v=read(p);assert v['status']=='passed' and v['attempts']==1 and v['reader_replacements']==0 and not v['secret_tainted']
 assert v['timing']['timeout_seconds']==60 and v['timing']['within_half_timeout'] and v['timing']['elapsed_seconds']<=30
 prefix=p.name.removesuffix('-physical-login-result.json')
 finish,=[read(x) for x in e.glob(prefix+'-login-fast-finish-*.json')]
 exposure=finish['exposure'];assert exposure['complete']
 assert all(row['repeat']==row['syn_dropped']==0 for row in exposure['counts'].values())
 assert all(x==0 for k in ('non_hidden','unknown') for x in exposure['counts'][k].values())
 init,=[read(x) for x in e.glob(prefix+'-login-fast-init-*.json')]
 logins.append(dict(**ref(p),result=v,exposure=exposure,versions=init['versions'],observers_prepared=init['observers_prepared']))
assert len(logins)==2
counters=[]
for p in sorted(e.glob('*-key-counter-result.json')):
 v=read(p);assert v['comparison']['matches'] and v['received']['complete'] and v['whole_window']['keys_released']
 assert v['received']['counts']['repeat']==v['received']['counts']['syn_dropped']==0
 counters.append(dict(**ref(p),comparison=v['comparison'],complete=True,whole_window=v['whole_window']['counts']))
assert len(counters)==4 and not (e/'owner-login-visual-taint.json').exists()
stage='corrected-stock-records-completed-wait-53'
resyncs=[];timeouts=[]
for p in sorted(e.glob(stage+'-resync-*.json')):
 v=read(p);assert v['enter_sent'] and v['observer']['ready'] and v['observer']['foreground_shell']
 assert v['before_cursor_line']==v['after_cursor_line']=='' and v['ready'] is False
 resyncs.append(dict(**ref(p),receipt=v))
assert [x['receipt']['attempt'] for x in resyncs]==[1,2]
for p in sorted(e.glob(stage+'-timeout-*.vcsa')):
 raw=p.read_bytes();full,line=owner_console.screen(raw);assert line==''
 # Only geometry and locations of public prompt delimiters are retained.
 rows,cols,x,y=raw[:4]
 lines=full.splitlines()
 timeouts.append(dict(**ref(p),rows=rows,columns=cols,cursor_x=x,cursor_y=y,cursor_line_empty=True,
  prompt_suffix_rows=[i for i,s in enumerate(lines) if re.search(r'[$#]\s*$',s)],
  root_prefix_rows=[i for i,s in enumerate(lines) if 'root@' in s],
  pass_records_rows=[i for i,s in enumerate(lines) if 'PASS records' in s],raw_screen_saved_in_packet=False))
assert len(timeouts)==3
transfers=[read(p) for p in e.glob('*-transport.json')];staged=[x for x in transfers if x.get('staged')]
assert all(x['verified'] and all(s['status']=='passed' for s in x['steps']) for x in staged)
native=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',native);assert m and int(m[1])==540 and re.search(r'Z OK\s*$',native,re.M)
value=dict(status='STOP after passed corrected-stock records; physical prompt-readiness deadline after two authorized Enter resyncs',run=40897501964,head=read(b/'receipt.json')['head'],
 native=dict(tests=540,seconds=float(m[2]),skips=0),owner_records=records,logins=logins,hidden_counters=counters,
 resyncs=resyncs,timeout_geometry=timeouts,verified_staged_transfers=len(staged),
 hidden_completions=len(list(e.glob('*-hidden-completed.json'))),
 observed='owner records passed; sudo relay observer reported idle at each resync; physical cursor line remained empty',
 underlying_cause_proven=False,acceptance_met=False,product_fix_after_stop=False,reruns=0,
 not_reached=['private owner login and dummy-token path','verify and switch','AresOS boot/login','plain-US failure and revert','US International proof/finish','final German proof/finish','rollback','keep-stock','final Windows checks'],
 raw_visuals_saved_in_packet=False,credential_values_saved=False)
(b/'14zs-outcome-review.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
print('STOP_REVIEW',len(records),'passed owner records;',len(logins),'logins under30s;',len(counters),'matching hidden counters;',len(staged),'verified transfers; resync2/timeout3; cause unproved')
print('TIMEOUT_GEOMETRY',[(x['cursor_x'],x['cursor_y'],x['prompt_suffix_rows']) for x in timeouts])
