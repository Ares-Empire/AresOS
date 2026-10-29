import pathlib,json,hashlib,sys
r=pathlib.Path.cwd();w=r/'.work/14/14zt';b=r/'.work/14/run-40897501964/evidence/two-disk'
sys.path.insert(0,str(r/'os/tests'));import test_owner_records_prompt as regression
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8',newline='\n')
p=b/'corrected-stock-records-completed-wait-53-timeout-1.vcsa';raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='8649735e5bd80360e83a626321415b0e87aef64ffb4592f9eb15b14161f5fd8f'
event=json.loads((b/'corrected-stock-records-completed-wait-53-resync-1.json').read_text())
rows=[]
for row in event['observer']['observation']['foreground_chain']:
 assert row['argv_redacted'] is False and row['argv'] in (['sudo','-i'],['-bash'])
 rows.append(dict(row,args=row['argv']))
values=[];commands=[]
for stage,tty,profile,chain in [('corrected-stock-records-completed','tty3','de',rows),
 *((stage,tty,profile,None) for stage,tty,profile in regression.REMAINING)]:
 result=regression.stopped_prompt(raw,stage,tty,profile,rows=chain)
 assert result['reason']=='Physical console readiness deadline'
 assert result['physical_keys']==[['ret'],['ret']] and result['raw_timeouts']==3 and result['observer_timeouts']==0
 assert not result['completion_granted'] and all(v['observer_ready'] and not v['ready'] for v in result['resyncs'])
 commands.extend(result.pop('commands'));result['physical_enter_attempts']=len(result.pop('physical_keys'))
 values.append(result)
save(w/'exact-replay.json',dict(status='passed negative exact-private-VCSA replay; never accepts the disconnected-keyboard historical prompt',
 source=dict(sha256=hashlib.sha256(raw).hexdigest(),path=p.relative_to(r).as_posix()),
 original_retained_relay_replayed=True,cases=values,raw_bytes_committed=False,
 later_stage_injection='counterfactual local refusal cases, not observations that these stages ran in Q15',
 final_windows_reachable_after_refusal=False,production_code_changed=False))
save(w/'negative-guest-commands.json',commands)
print('PASS exact private VCSA and retained relay;9 readiness contexts STOP,2 Enters/3 retained samples each; no completion grant')
