import pathlib,json,re,sys
r=pathlib.Path.cwd();w=r/'.work/14';run=int(sys.argv[1]);b=w/('run-'+str(run));e=b/'evidence'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
receipt=read(b/'receipt.json');assert receipt['status']=='success' and receipt['head']==read(w/'14zj-one-push-scan.json')['checked_commit']
privacy=read(b/'14zj-privacy-classification.json');assert privacy['status']=='passed'
assert read(w/'gitleaks/14zj-qualification-native.json')==[]
log=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',log);assert m and int(m[1])==470 and re.search(r'Z OK\s*$',log,re.M)
native=read(e/'14-native-owner-devices.json');assert native['status']=='passed' and native['helper_mutations']==0 and native['protected_fixture_unchanged'] and native['all_fixture_mounts_unmounted_and_loops_detached']
iso=read(e/'installer/iso-download.json');assert iso['status']=='passed' and iso['bytes']==9068650496 and iso['sha256']==iso['downloaded_sha256']==iso['official_sha256']
proof=read(e/'two-disk/owner-tools-result.json');assert proof['status']=='passed' and proof['commit']==receipt['head'] and proof['order']=='protected-second'
assert proof['release']==read(r/'os/manifest/release.json')['reference'] and proof['bundle_manifest']=='683b1cff54d8a80406a70afd3f1173343a8a3fc95d301ef8cdbf05ab39010974'
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
hidden_ready=sorted((e/'two-disk').glob('*-read-wait-*.json'))
hidden_ready=[p for p in hidden_ready if re.search(r'-read-wait-[0-9]+\.json$',p.name)]
assert len(hidden_ready)==22, ('hidden readiness count',len(hidden_ready))
for path in hidden_ready:
 ready=read(path);left=read(path.with_name(path.stem+'-left.json'))
 assert ready['ready'] is True and ready['prompt_at_cursor'] is True and ready['reader_echo_enabled'] is False
 assert ready['reader']['exe'] and ready['reader']['tty_path'] and not ready.get('raw')
 assert left['ready'] is True and left['value_recorded'] is False and not left.get('raw')
 assert all(v.get('argv_redacted') is True and v['argv']==['[redacted]'] for v in ready['observation']['foreground_chain'])
audits=read(b/'independent-audits.json');assert audits['status'].startswith('passed')
value=dict(status='passed independent qualification evidence review',run=run,head=receipt['head'],artifact=receipt,native_tests=470,native_seconds=float(m[2]),native_skips=0,loop_checks=len(native['checks']),loop_mutations=0,protected_fixture_unchanged=True,fixture_cleanup=True,qualification=proof,physical_owner_command_records=len(commands),fresh_idle_resyncs=len(resyncs),resynced_waits=len(waits),staged_transfers=len(staged),staged_sha_and_syntax_verified=True,privacy=privacy,independent_audits=audits,acceptance_met=True,hidden_ready_and_left_pairs=len(hidden_ready),hidden_value_recorded=False)
(b/'14zj-qualification-proof.json').write_text(json.dumps(value,indent=2)+'\n',newline='\n');print('QUALIFICATION_ACCEPTED',run,470,'native tests;',len(commands),'physical owner records;',len(staged),'verified transfers; unknown artifact findings0')
