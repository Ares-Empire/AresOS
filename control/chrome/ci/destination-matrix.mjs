import assert from 'node:assert/strict';
import fs from 'node:fs';
import {assertDestinations} from './destination-evidence.mjs';
import {destinationRows} from './destination-fixtures.mjs';
export async function destinationMatrix({check,nav,call,target,approval,fixture,receiverEvidence,eventually}){
  const evidence=[];
  await check('GROUP 3 POST18D absolute destinations inherited bases targets and form owners',async()=>{
    for(const row of destinationRows()){
      await nav('review-page&mode=destination&'+new URLSearchParams(row));
      const prepared=await call('click',await target('Delete'));assert.ok(prepared.approval,JSON.stringify(prepared));
      const original=prepared.approval.description.untrusted_content.page_state;
      const address=original.form?.action||original.target.href;
      assert.equal(new URL(address).pathname,'/first/receive',row.id);
      assert.equal(original.form?.browsing_target||original.target.browsing_target,row.change==='svg-self'?'_self':'sink-first');
      await fixture.mutate(row.id,'review-change');
      if(row.change.startsWith('animation'))await new Promise(resolve=>setTimeout(resolve,150));
      const reasked=await call('submit',prepared.approval);
      assert.equal(receiverEvidence(row.id,'changed destination held').count,0);
      assert.equal(reasked.operation.state,'failed');assert.ok(reasked.approval,JSON.stringify(reasked));
      assert.notEqual(reasked.approval.operation_id,prepared.approval.operation_id);
      await call('submit',prepared.approval);assert.equal(receiverEvidence(row.id,'stale destination approval stays retired').count,0);
      const fresh=reasked.approval.description.untrusted_content.page_state;
      assert.equal(new URL(fresh.form?.action||fresh.target.href).pathname,row.change.endsWith('target')?'/first/receive':'/second/receive');
      if(row.change.endsWith('target'))assert.equal(fresh.form?.browsing_target||fresh.target.browsing_target,'sink-second');
      await approval(reasked,row.id);
      const context=await eventually(()=>fixture.compatibility.find(item=>item.id===row.id&&item.phase==='destination-context'),'native destination context');
      const nativeTab=(await call('tabs',{limit:10})).items.find(item=>item.tab===prepared.approval.description.untrusted_content.page_state.tab);
      assert.ok(nativeTab);assert.equal(context.top,row.change==='svg-self');
      if(row.change==='svg-self')assert.equal(nativeTab.url,context.url,'the same controlled top tab followed its native SVG default');
      else{assert.equal(context.name,row.change.endsWith('target')?'sink-second':'sink-first');assert.equal(new URL(nativeTab.url).searchParams.get('case'),'review-page','a named frame must leave the top document intact');}
      evidence.push({...row,prepared,reasked,context,nativeTab});
    }
  });
  fs.writeFileSync('/out/destinations.json',JSON.stringify(evidence,null,2));
  const snapshots=fs.readFileSync('/out/page-receiver.jsonl','utf8').trim().split('\n').map(JSON.parse);
  fs.writeFileSync('/out/destinations-audit.json',JSON.stringify(assertDestinations(evidence,snapshots,fixture.arrivals,fixture.compatibility),null,2));
}
