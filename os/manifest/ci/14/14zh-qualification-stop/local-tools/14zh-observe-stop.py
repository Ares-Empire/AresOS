import pathlib,json,re,hashlib,subprocess,sys
r=pathlib.Path.cwd();w=r/'.work/14';b=w/'run-40630352782';e=b/'evidence/two-disk';sys.path.insert(0,str(r/'os/ci'));import owner_console as vc
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert read(b/'receipt.json')['head']=='d15678dc491905f592c2b7b1af852fca1d35e08b'
raw=(e/'private-owner-login-physical-idle-timeout-1.vcsa').read_bytes();full,line=vc.screen(raw)
p=subprocess.run([str(w/'gitleaks/gitleaks.exe'),'stdin','--redact=100','--no-banner','--log-level','warn','--report-format','json','--report-path',str(w/'gitleaks/14zh-qualification-decoded-vcsa.json')],input=full.encode(),capture_output=True)
assert p.returncode==0 and read(w/'gitleaks/14zh-qualification-decoded-vcsa.json')==[]
markers=('GitHub username:','Read-only token (hidden):','PASS login','STOP:','root@bazzite:~#','Password:')
vcsa=dict(sha256=h(e/'private-owner-login-physical-idle-timeout-1.vcsa'),path='evidence/two-disk/private-owner-login-physical-idle-timeout-1.vcsa',geometry=list(raw[:4]),cursor_line_empty=not line,markers={m:[i+1 for i,s in enumerate(full.split('\n')) if m in s] for m in markers},decoded_gitleaks_findings=0,token_prefix_present=bool(re.search(r'(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]{8,}',full)),decoded_text_saved=False)
assert not vcsa['token_prefix_present'] and vcsa['markers']['Read-only token (hidden):']==[50] and not vcsa['markers']['PASS login'] and not vcsa['markers']['STOP:']
ready=read(e/'private-owner-login-physical-idle.json');assert not ready['ready'];ready.pop('raw')
log=(b/'native.log').read_text(encoding='utf-8');m=re.search(r'Ran (\d+) tests in ([\d.]+)s',log);assert m and m[1]=='452' and re.search(r'Z OK\s*$',log,re.M)
resync=[]
for p in e.glob('*-wait-*-resync-*.json'):
 v=read(p);assert v['enter_sent'] and v['observer']['ready'] and v['ready'] and v['attempt']==1
 assert {k:x for k,x in read(e/(v['stage']+'-idle-1.json')).items() if k!='raw'}==v['observer']
 resync.append(dict(sha256=h(p),path=p.relative_to(b).as_posix(),event=v))
staged=[read(p) for p in e.glob('*-transport.json') if read(p).get('staged')];assert len(staged)==101 and all(v['verified'] and all(x['status']=='passed' for x in v['steps']) for v in staged)
assert read(e/'before-first-network-deployments.json')==read(e/'after-first-network-deployments.json')
summary=dict(status='STOP private login hidden completion; no idle authority, no Enter',run=40630352782,head=read(b/'receipt.json')['head'],native_tests=452,native_seconds=float(m[2]),native_skips=0,foreground_refusal=ready,vcsa=vcsa,resyncs=resync,staged_transfers=len(staged),all_staged_sha_and_syntax_verified=True,hidden_observation=read(e/'private-owner-login-hidden-input.json'),serial_resync=read(e/'private-owner-login-serial-resync.json'),failure_counter=read(e/'corrected-stock-failure-counter.json'),owner_diagnostics_count=len(list(e.glob('*-owner-diagnostics.json'))),private_login_owner_record_present=(e/'private-owner-login-owner-diagnostics.json').exists(),after_network_unchanged=True,tools_removed_before_reboot=read(e/'tools-stock-media-detach.json')['absent_before_shutdown'],last_console_marker='Read-only token (hidden):',private_login_cause_proven=False,not_proven='No inner pts termios or visible prompt snapshot at the instant hidden input was sent; early/flushed or dropped physical input cannot be distinguished.',observed_source_boundary='owner.py login: input username; getpass token; validate_login; podman login. No PASS/STOP or private-login record was produced.',source_implementation_unchanged=True)
(b/'14zh-stop-observations.json').write_text(json.dumps(summary,indent=2)+'\n',newline='\n')
print('PASS zero-cost STOP observation replay; no decoded console or token saved; no implementation mutation')
