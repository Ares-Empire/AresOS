// This module runs only in the GitHub Linux browser container.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {browserMixes} from './guard-matrix.mjs';
import {defaultRows,whitespaceKinds,whitespaceText} from './recheck3-fixtures.mjs';
import {allTabs} from './tabs.mjs';
import {assertRecheck3} from './recheck3-evidence.mjs';
const shown=text=>text.replaceAll('\\','\\\\').replaceAll('\n','\\u000a');
export async function recheck3Matrices({check,nav,call,target,approval,receiverEvidence,fixture,eventually,getTab,setTab,nativeDonor,closeNativeDonor}){
  const evidence={mixed:[],defaults:[],whitespace:[]};
  await check('GROUP 2 RECHECK3 every single wrapped step holds across roots events and registration order',async()=>{
    for(const row of browserMixes()){
      setTab(await nativeDonor(getTab()));const id=`recheck3-mix-${row.mask}-${row.mode}-${row.composed}-${row.order}`;
      await nav('review-page&mode=mixed&'+new URLSearchParams({id,mask:row.mask,root:row.mode,composed:row.composed,order:row.order}));
      const stopped=await call('click',await target('Continue'));assert.equal(receiverEvidence(id,'mixed handler held').count,0);
      assert.equal(stopped.untrusted_content.steps.length,1);assert.equal(stopped.untrusted_content.steps[0].kind,'activation');
      assert.ok(stopped.followups.some(row=>row.stopped));await approval(await call('click',await target('Delete')),id);
      assert.equal(receiverEvidence(id,'only the approved handler ran').arrivals[0].body,'mixed handler');
      evidence.mixed.push({id,...row,stopped});await closeNativeDonor();
    }
  });
  await check('GROUP 2 RECHECK3 every hyperlink and form submitter default is neutralised',async()=>{
    for(const {kind,route,id}of defaultRows()){
      setTab(await nativeDonor(getTab()));await nav('review-page&mode=activation-default&'+new URLSearchParams({kind,route,id}));
      const stopped=await call('click',await target('Continue'));
      assert.equal(receiverEvidence(id,'native default held').count,0);assert.equal(receiverEvidence('ping-'+id,'native ping held').count,0);
      assert.ok(stopped.followups.some(row=>row.stopped));assert.match(JSON.stringify(stopped.followups),/non-cancellable default was stopped/);
      await approval(await call('click',await target('Delete')),id);
      if(route==='ping'){await eventually(()=>receiverEvidence('ping-'+id,'approved ping once').count===1,'approved hyperlink ping');assert.equal(receiverEvidence('ping-'+id,'repeat never pings again').count,1);}
      if(route==='blank'){
        const child=await eventually(async()=>(await allTabs(call)).items.find(row=>row.tab!==getTab()&&row.url?.includes('/receive?case='+id)&&row.controlled),'approved target joins control');
        await call('close_tab',{tab:child.tab});
      }
      evidence.defaults.push({id,kind,route,stopped});await closeNativeDonor();
    }
  });
  await check('GROUP 3 RECHECK3 rendered whitespace survives questions reasking stopping and final dispatch',async()=>{
    for(const kind of whitespaceKinds)for(const change of kind==='pre-line'?['line']:['indent','line']){
      const id='recheck3-space-'+kind+'-'+change;
      await nav('review-page&mode=compose-whitespace&'+new URLSearchParams({kind,change,id}));
      const prepared=await call('click',await target('Send')),render=text=>kind==='pre-line'?text.replace(/^[ \t]+/gm,''):text;
      assert.ok(prepared.approval.question.includes(shown(render(whitespaceText.before))),JSON.stringify(prepared));
      const original=prepared.approval.description.untrusted_content.page_state.compose;
      assert.ok(original.text.includes(shown(render(whitespaceText.before))));
      await fixture.mutate(id,'review-change');const reasked=await call('submit',prepared.approval);
      assert.equal(receiverEvidence(id,'whitespace first change held').count,0);assert.equal(reasked.operation.state,'failed');
      assert.ok(reasked.approval.question.includes(shown(render(whitespaceText.before))));assert.ok(reasked.approval.question.includes(shown(render(whitespaceText[change]))));
      assert.notEqual(reasked.approval.operation_id,prepared.approval.operation_id);assert.ok(reasked.approval.description.untrusted_content.page_state.compose.text.includes(shown(render(whitespaceText[change]))));
      await call('submit',prepared.approval);assert.equal(receiverEvidence(id,'old whitespace approval stays retired').count,0);
      await fixture.mutate(id,'review-change');const stopped=await call('submit',reasked.approval);
      assert.equal(stopped.operation.state,'failed');assert.ok(!stopped.approval);assert.match(stopped.operation.reason,/text next to Send keeps changing.*owner/);
      await call('submit',reasked.approval);assert.equal(receiverEvidence(id,'bounded whitespace stop and repeat').count,0);
      const fresh=await call('click',await target('Send'));await approval(fresh,id);
      assert.equal(receiverEvidence(id,'fresh whitespace body received exactly').arrivals[0].body,whitespaceText.line+'\n');
      evidence.whitespace.push({id,kind,change,prepared,reasked,stopped,fresh});
    }
  });
  fs.writeFileSync('/out/recheck3.json',JSON.stringify(evidence,null,2));
  const snapshots=fs.readFileSync('/out/page-receiver.jsonl','utf8').trim().split('\n').map(line=>JSON.parse(line));
  fs.writeFileSync('/out/recheck3-audit.json',JSON.stringify(assertRecheck3(evidence,snapshots,fixture.arrivals),null,2));
}
