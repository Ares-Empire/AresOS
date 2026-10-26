import datetime,json,pathlib,sys
root=pathlib.Path.cwd();sys.path.insert(0,str(root/'os/ci'));import rehearsal_guard as guard
guard.configure('14');ledger=guard.budget(0);org=guard.organization_budget(0)
print('FRESH_PACKAGE',ledger['consumed_minutes'],'/400; HISTORY',ledger['history']['ids_count'],ledger['history']['total_count'],'ORG_FREE',org['remaining_minutes'])
value=dict(checked_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),decision='bcf2070',ledger=ledger,organization=org,required_plan_reservation=184,requested_cap=400,probe_native_reservation=42,qualification_reservation=130,closing_privacy_reservation=12)
folder=root/'os/manifest/ci/14/14k-ledger';folder.mkdir(exist_ok=True)
(folder/'preflight.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
# Invoke the production guards at their complete required reservation. A refusal
# is retained and stops dispatch; there is no smaller-reservation retry.
checks=[]
for name,call in [('package',lambda:guard.budget(184)),('organization',lambda:guard.organization_budget(184))]:
 try:
  result=call();checks.append(dict(check=name,status='passed',result=result))
 except AssertionError as error:
  checks.append(dict(check=name,status='refused',reason=str(error)));print('GUARD_REFUSAL',name,str(error))
value['checks']=checks;value['dispatch_allowed']=all(c['status']=='passed' for c in checks)
(folder/'preflight.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
(root/'.work/14/14k-plan-guard.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8',newline='\n')
assert value['dispatch_allowed'], 'STOP: required184-minute plan refused; no dispatch or rerun'
