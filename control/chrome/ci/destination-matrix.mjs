import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertDestinations} from './destination-evidence.mjs';
import {destinationRows} from './destination-fixtures.mjs';
export async function destinationMatrix({check,nav,call,target,approval,fixture,receiverEvidence}){
  const evidence=[];
  await check('GROUP 3 POST18D absolute destinations inherited bases targets and form owners',async()=>{
    for(const row of destinationRows()){
      await nav('review-page&mode=destination&'+new URLSearchParams(row));
      const prepared=await call('click',await target('Delete'));assert.ok(prepared.approval,JSON.stringify(prepared));
      const original=prepared.approval.description.untrusted_content.page_state;
      const address=original.form?.action||original.target.href;
      assert.equal(new URL(address).pathname,'/first/receive',row.id);
      assert.equal(original.form?.browsing_target||original.target.browsing_target,'sink-first');
      await fixture.mutate(row.id,'review-change');
      const reasked=await call('submit',prepared.approval);
      assert.equal(receiverEvidence(row.id,'changed destination held').count,0);
      assert.equal(reasked.operation.state,'failed');assert.ok(reasked.approval,JSON.stringify(reasked));
      assert.notEqual(reasked.approval.operation_id,prepared.approval.operation_id);
      await call('submit',prepared.approval);assert.equal(receiverEvidence(row.id,'stale destination approval stays retired').count,0);
      const fresh=reasked.approval.description.untrusted_content.page_state;
      assert.equal(new URL(fresh.form?.action||fresh.target.href).pathname,row.change==='target'?'/first/receive':'/second/receive');
      if(row.change==='target')assert.equal(fresh.form?.browsing_target||fresh.target.browsing_target,'sink-second');
      await approval(reasked,row.id);evidence.push({...row,prepared,reasked});
    }
  });
  fs.writeFileSync('/out/destinations.json',JSON.stringify(evidence,null,2));
  const snapshots=fs.readFileSync('/out/page-receiver.jsonl','utf8').trim().split('\n').map(JSON.parse);
  fs.writeFileSync('/out/destinations-audit.json',JSON.stringify(assertDestinations(evidence,snapshots,fixture.arrivals),null,2));
}
