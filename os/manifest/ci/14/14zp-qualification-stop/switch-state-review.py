import pathlib,json,hashlib
r=pathlib.Path.cwd();b=r/'.work/14/run-40826092372';e=b/'evidence/two-disk';p=e/'owner-switch-owner-diagnostics.json';v=json.loads(p.read_text())
states={}
for name,command in [('rpm',['rpm-ostree','status','--json']),('bootc',['bootc','status','--json'])]:
    rows=[x for x in v['trace'] if x.get('command')==command]
    assert rows and rows[-1]['returncode']==0
    states[name]=json.loads(rows[-1]['stdout'])
rpm=states['rpm'];bootc=states['bootc']['status']
rows=[{k:d.get(k) for k in ('checksum','serial','osname','booted','pinned','staged','container-image-reference','container-image-reference-digest')} for d in rpm['deployments']]
mutations=[x for x in v['trace'] if x.get('mutation')]
assert len(mutations)==1 and mutations[0]['returncode']==0
script={k:val for k,val in mutations[0].items() if k not in ('stdout','stderr')}
assert 'transaction' in rpm and rpm['transaction'] is None
assert bootc.get('staged') is not None and not bootc.get('rollbackQueued')
stock=[d for d in rows if d['booted']];staged=[d for d in rows if d['staged']]
assert len(stock)==len(staged)==1 and stock[0]['pinned'] and not staged[0]['pinned']
assert staged[0]['container-image-reference-digest']==json.loads((r/'os/manifest/release.json').read_text())['reference'].split('@')[1]
summary=dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),path=p.relative_to(b).as_posix(),status='STOP after successful switch script, during title idle gate',error=v['error'],mutation=script,script_stderr=mutations[0].get('stderr'),deployments=rows,transaction=rpm['transaction'],rollback_queued=bootc.get('rollbackQueued'),bootc_staged_checksum=bootc['staged']['ostree']['checksum'],bootc_staged_digest=bootc['staged']['image']['imageDigest'],bootc_staged_reference=bootc['staged']['image']['image']['image'],process_snapshot_recorded=False,active_client_identity='not retained; unproved',new_title_record_saved=False,owner_switch_pass=False,reboot_after_stop=False)
(b/'14zp-switch-state.json').write_text(json.dumps(summary,indent=2)+'\n',newline='\n')
print(json.dumps(summary,indent=2))
