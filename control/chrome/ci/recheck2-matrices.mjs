// Loaded only by the GitHub Linux-container harness.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {allTabs} from './tabs.mjs';
import {assertNativeLimit} from './activation-evidence.mjs';
import {setTimeout as delay} from 'node:timers/promises';
export async function recheck2Matrices({check,nav,call,target,approval,receiverEvidence,fixture,eventually,getTab,setTab,nativeDonor,closeNativeDonor,ownerKey,lifecycle,restoreControl}){
  await check('GROUP 2 RECHECK2 every borrowed native insertion route captures noncomposed shadow events',async()=>{
    for(const mode of ['open','closed'])for(const route of ['insertBefore','replaceChild','append','prepend','replaceChildren','markup']){
      setTab(await nativeDonor(getTab()));const id='recheck2-shadow-'+mode+'-'+route;
      await nav('review-page&mode=shadow-fallback&variant='+mode+'&native=true&composed=false&cancel=true&route='+route+'&id='+id);
      const result=await call('click',await target('Continue'));assert.equal(receiverEvidence('handler-'+id,'native insertion handler held').count,0);
      assert.equal(receiverEvidence(id,'native insertion default held').count,0);assert.ok(result.followups.some(row=>row.stopped));
      await approval(await call('click',await target('Delete')),id);await closeNativeDonor();
    }
    for(const mode of ['open','closed'])for(const variant of ['same','other','root']){
      setTab(await nativeDonor(getTab()));const id='recheck2-event-'+mode+'-'+variant;
      await nav('review-page&mode=event-reuse&variant='+variant+'&root='+mode+'&id='+id);
      const result=await call('click',await target('Continue'));
      assert.equal(receiverEvidence('handler-'+id,'reused event first handler held').count,0);
      assert.equal(receiverEvidence('other-handler-'+id,'reused event other handler held').count,0);
      assert.equal(receiverEvidence(id,'reused event defaults held').count,0);
      assert.equal(result.untrusted_content.steps.length,2,'both borrowed-native dispatches are reported');
      await approval(await call('click',await target('Delete one')),id);await closeNativeDonor();
    }
  });
  await check('GROUP 2 RECHECK2 native defaults cover new tabs frames ping forms and downloads',async()=>{
    setTab(await nativeDonor(getTab()));await nav('review-page&mode=network-fence&id=recheck2-fence-page');
    await call('click',await target('Continue'));assert.equal(receiverEvidence('recheck2-network-fence','session fence blocks a real native form request').count,0);
    await fixture.mutate('recheck2-fence-page','review-change');await eventually(()=>receiverEvidence('recheck2-network-fence','session fence expires').count===1,'native request after hold expiry');
    await closeNativeDonor();
    for(const variant of ['blank','frame','ping','form','form-blank','download']){
      setTab(await nativeDonor(getTab()));const id='recheck2-default-'+variant;
      await nav('review-page&mode=native-default&variant='+variant+'&id='+id);
      const result=await call('click',await target('Continue'));
      assert.equal(receiverEvidence(id,'uncancellable default held').count,0);
      assert.equal(receiverEvidence('ping-'+id,'uncancellable ping held').count,0);
      assert.ok(result.followups.some(row=>row.stopped));assert.ok(!result.followups.some(row=>row.approval));
      assert.match(JSON.stringify(result.followups),/non-cancellable default was stopped/);
      await approval(await call('click',await target('Delete')),id);
      if(variant==='ping'){await eventually(()=>receiverEvidence('ping-'+id,'approved ping observed').count===1,'one approved ping');assert.equal(receiverEvidence('ping-'+id,'approved ping remains once').count,1);}
      if(variant==='blank'||variant==='form-blank'){
        const child=await eventually(async()=>(await allTabs(call)).items.find(row=>row.tab!==getTab()&&row.url?.includes('/receive?case='+id)&&row.controlled),'approved native target joins control');
        await call('close_tab',{tab:child.tab});
      }
      await closeNativeDonor();
    }
  });
  await check('GROUP 2 RECHECK2 the owner navigates during the network hold',async()=>{
    const id='recheck2-owner-navigation';await nav('review-page&mode=owner-navigation&id='+id);
    const pending=call('click',await target('Continue'));
    const started=await eventually(()=>fixture.arrivals.find(row=>row.url.includes('case=task-start')&&row.body===id),'owner-navigation start');
    await delay(Math.max(0,started.time+130-Date.now()));ownerKey(true);await pending;
    await eventually(()=>receiverEvidence(id,'owner native navigation').count===1,'owner navigation during hold');
    assert.equal(receiverEvidence(id,'owner navigation remains once').count,1);
  });
  await check('GROUP 3 RECHECK2 live compose text reasks once while outside text stays free',async()=>{
    const outside='recheck2-compose-outside';await nav('review-page&mode=compose-preview&variant=outside&id='+outside);
    const prepared=await call('click',await target('Send'));await fixture.mutate(outside,'review-change');await delay(150);
    await approval(prepared,outside);assert.equal(receiverEvidence(outside,'outside live text keeps original preview').arrivals[0].body,'Original preview');
    const inside='recheck2-compose-inside';await nav('review-page&mode=compose-preview&variant=inside&id='+inside);
    const initial=await call('click',await target('Send'));await fixture.mutate(inside,'review-change');await delay(1150);
    const reasked=await call('submit',initial.approval);assert.equal(receiverEvidence(inside,'first live change held').count,0);
    assert.match(reasked.approval.question,/Original preview.*Live preview/);await delay(1100);
    const stopped=await call('submit',reasked.approval);assert.equal(stopped.operation.state,'failed');assert.ok(!stopped.approval);
    assert.match(stopped.operation.reason,/text next to Send keeps changing.*owner/);assert.equal(receiverEvidence(inside,'second live change held').count,0);
    await call('submit',reasked.approval);assert.equal(receiverEvidence(inside,'repeat bounded stop').count,0);
  });
  await check('GROUP 13 RECHECK2B all-native limit records user activation and honest after-click reporting',async()=>{
    const observations=[];
    for(const mode of ['open','closed'])for(const capability of ['network','popup','download','clipboard','payment']){
      setTab(await nativeDonor(getTab(),'http://localhost:8765'));
      const id='recheck2b-limit-'+mode+'-'+capability;
      await nav('review-page&mode=all-native-limit&root='+mode+'&variant='+capability+'&id='+id,'localhost');
      // Autonomous SSE delivery grants no input. Let any prior owner-created
      // popup's transient activation expire before measuring the fresh document.
      await delay(5500);await fixture.mutate(id,'review-change');
      const alone=await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='all-native-limit'&&row.cause==='alone'),'autonomous native result');
      assert.equal(alone.before.active,false);assert.equal(alone.atHandler.active,false);assert.equal(alone.trusted,false);assert.equal(alone.secure,true);
      assert.equal(receiverEvidence(id+'-alone','known limit autonomous handler').count,1);
      assert.equal(receiverEvidence(id+'-claude','known limit before Claude input').count,0);
      const result=await call('click',await target('Continue'));
      const clicked=await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='all-native-limit'&&row.cause==='claude'),'Claude native result');
      assert.equal(clicked.trusted,false);assert.equal(clicked.secure,true);assert.equal(receiverEvidence(id+'-claude','known limit after Claude input').count,1);
      // The invisible native step is not falsely described as stopped. The
      // response observes only the dispatched input and untrusted page notice.
      assert.equal(result.followups.length,0);assert.equal(result.untrusted_content.dispatched,true);assert.equal(result.untrusted_content.steps.length,0);
      assert.ok(result.untrusted_content.page.notices.includes('Hostile native Delete handler ran'));
      const status=await call('operation_status',{operation_id:result.operation_id});
      assert.match(status.operation.stages.dispatched.untrusted_content,/delivery not proven/);assert.match(status.operation.reason,/Free input dispatched once/);
      assert.doesNotMatch(status.operation.reason,/nothing|stopped|no input/i);
      const row={id,mode,capability,alone,clicked,added_transient_activation:!alone.atHandler.active&&clicked.atHandler.active,result,status};observations.push(row);
      console.log('RECHECK2B LIMIT',JSON.stringify({id,added_transient_activation:row.added_transient_activation,alone:alone.outcome,clicked:clicked.outcome}));
      await delay(150);
      for(const child of (await allTabs(call)).items.filter(row=>row.tab!==getTab()&&row.url?.includes('mode=activation-popup&id='+id))){assert.equal(child.controlled,true);await call('close_tab',{tab:child.tab});}
      await closeNativeDonor();
    }
    fs.writeFileSync('/out/all-native-limit.json',JSON.stringify(observations,null,2));
    const audit=assertNativeLimit(observations,fixture.arrivals);fs.writeFileSync('/out/all-native-limit-audit.json',JSON.stringify(audit,null,2));
  });
  await check('GROUP 5 RECHECK2C clipboard writes are reported without reading contents',async()=>{
    const results=[];
    for(const route of ['writeText','write','copy','writeText-nav']){
      const id='recheck2c-clipboard-'+route;await nav('review-page&mode=clipboard-report&variant='+route+'&id='+id,'localhost');
      assert.equal(receiverEvidence(id,'clipboard before click').count,0);
      const result=await call('click',await target('Continue'));await eventually(()=>receiverEvidence(id,'clipboard accepted once').count===1,'native clipboard operation accepted');
      assert.equal(result.untrusted_content.page.clipboard.written,true);assert.equal(result.untrusted_content.page.clipboard.message,'The page wrote to the clipboard.');
      assert.deepEqual(result.untrusted_content.page.clipboard.routes,[route==='writeText-nav'?'writeText':route]);
      assert.doesNotMatch(JSON.stringify(result),/SYNTHETIC_CLIPBOARD_CONTENT_2C/);
      const status=await call('operation_status',{operation_id:result.operation_id});assert.equal(receiverEvidence(id,'clipboard status never replays').count,1);
      results.push({id,route,result,status});
    }
    fs.writeFileSync('/out/clipboard-report.json',JSON.stringify(results,null,2));
  });
  await check('GROUP 8 RECHECK2 extension restart reconciles leftover session network rules',async()=>{
    // Reproduce a lost worker timer: a session rule survives but all its private
    // state is gone. Stop first so this experiment doesn't strand MAIN wrappers.
    await lifecycle({fixture:'network_restart',tab:getTab()});
    const before=JSON.parse(fs.readFileSync('/out/network-restart.json'));assert.ok(before.rules.some(rule=>rule.id===2));
    await eventually(async()=>{try{return (await call('tabs')).session!==before.session;}catch{return false;}},'new extension session');
    setTab(await restoreControl());await lifecycle({fixture:'control_status'});
    const after=JSON.parse(fs.readFileSync('/out/control-status.json'));assert.notEqual(after.session,before.session);
    assert.ok(!after.network_rules.some(rule=>rule.id===2),'startup removed the rule whose timer was lost');
    fs.writeFileSync('/out/network-restart-audit.json',JSON.stringify({before,after},null,2));
  });
}
