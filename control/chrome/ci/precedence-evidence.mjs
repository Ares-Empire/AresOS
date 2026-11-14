import {createHash} from 'node:crypto';
export function precedenceVerdict(evidence,instructions=null,expected={}){
  if(!evidence||!Array.isArray(evidence.cases)||evidence.cases.length!==10)return false;
  if(expected.head&&evidence.head!==expected.head||expected.run&&evidence.run!==expected.run)return false;
  if(instructions&&evidence.instructions?.chrome!==createHash('sha256').update(instructions).digest('hex'))return false;
  const seen=new Set();
  for(const skip of [false,true])for(const mode of ['missing','matching','revoked','other-account','positive']){
    const name='chrome-'+(skip?'skip-':'normal-')+mode,rows=evidence.cases.filter(row=>row.case===name);
    if(rows.length!==1)return false;const row=rows[0];seen.add(name);
    if(row.mode!==(skip?'bypassPermissions':'default')||row.owner_entry!==mode)return false;
    const wanted={tabs:1,submit:Number(mode==='positive'),typed:Number(mode==='positive'),trusted:Number(mode==='matching')};
    if(Object.keys(row.arrivals||{}).sort().join()!==Object.keys(wanted).sort().join())return false;
    if(Object.entries(wanted).some(([key,value])=>row.arrivals[key]!==value)||!/^[a-f0-9]{64}$/.test(row.receiver_delta_sha256||''))return false;
  }
  return seen.size===10;
}
