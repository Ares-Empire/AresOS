import assert from 'node:assert/strict';
import fs from 'node:fs';
import {allTabs} from './tabs.mjs';
export async function animatedDefaultMatrix({check,nav,call,target,approval,receiverEvidence,eventually,getTab,setTab,nativeDonor,closeNativeDonor}){
  const evidence=[];
  await check('GROUP 2 POST18D animated SVG native defaults stay held',async()=>{
    for(const kind of ['svg-animated-href','svg-animated-xlink'])for(const route of ['blank','frame','self']){
      const id='post18d-animated-default-'+kind+'-'+route;
      setTab(await nativeDonor(getTab()));await nav('review-page&mode=activation-default&'+new URLSearchParams({kind,route,id}));
      const before=await allTabs(call),stopped=await call('click',await target('Continue'));
      assert.equal(receiverEvidence(id,'animated native default held').count,0);
      assert.ok(stopped.followups.some(row=>row.stopped));assert.match(JSON.stringify(stopped.followups),/non-cancellable default was stopped/);
      const after=await allTabs(call);assert.deepEqual(after.items.map(row=>[row.tab,row.window,row.url]),before.items.map(row=>[row.tab,row.window,row.url]),'stopping an animated default creates no native browsing context or navigation');
      await approval(await call('click',await target('Delete')),id);
      if(route==='blank'){
        const child=await eventually(async()=>(await allTabs(call)).items.find(row=>row.tab!==getTab()&&row.url?.includes('/receive?case='+id)&&row.controlled),'approved animated target joins control');
        await call('close_tab',{tab:child.tab});
      }
      evidence.push({id,kind,route,before,stopped,after});await closeNativeDonor();
    }
  });
  fs.writeFileSync('/out/animated-defaults.json',JSON.stringify(evidence,null,2));
}
