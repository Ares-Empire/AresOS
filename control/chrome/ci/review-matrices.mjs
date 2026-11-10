import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';

export async function reviewMatrices({check,nav,call,rpc,target,read,counts,eventually,approval,fixture,getTab,ownerKey,admin,ownerNavigate,ownerDismiss,nativeDonor,closeNativeDonor,setTab,lifecycle}){
  await check('GROUP 2 REVIEW inherited and newly created frames hold submissions',async()=>{
    for(const variant of ['blank','srcdoc','borrowed','new']){
      const id='review-frame-'+variant;await nav('review-page&mode='+(variant==='new'?'new-frame':'inline-hold')+'&variant='+variant+'&id='+id);
      await approval(await call('click',await target('Continue')),id);
      console.log('REVIEW P2 P3 P4 RECEIVER0/1/1',id);
    }
  });
  await check('GROUP 2 REVIEW borrowed wrappers respect another controlled tab and an ordinary document',async()=>{
    for(const outside of [false,true]){
      const id='review-cross-tab-'+outside;await nav('review-page&mode=cross-tab&id='+id);await call('click',await target('Open window'));
      const child=await eventually(async()=>(await call('tabs',{limit:100})).items.find(row=>row.url?.includes('mode=cross-tab-inner&id='+id)),'controlled other tab');
      const childTarget=async()=>{const page=await call('read',{tab:child.tab});const row=page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Ready');return row&&{reference:row.reference,expected:row.expected};};
      const old=await eventually(childTarget,'other tab reader');const first=await rpc('click',old);assert.equal(first.ok,false);assert.equal(first.error.code,'stale_reference');
      await call('click',await eventually(childTarget,'guarded other tab'));
      if(outside)await call('release_tab',{tab:child.tab});
      await call('click',await target('Continue'));
      if(outside){await eventually(()=>counts(id)===1,'outside document takes native path');await call('take_tab',{tab:child.tab});await call('close_tab',{tab:child.tab});}
      else{
        assert.equal(counts(id),0,'the other controlled document cannot take the source native path');
        await call('read',{tab:child.tab});let cursor,prepared;
        do{const pending=await rpc('control_pending',{limit:20,...(cursor?{cursor}:{})});assert.equal(pending.ok,true);for(const row of pending.data.items){if(row.app!=='chrome'||row.state!=='reserved')continue;const status=await call('operation_status',{operation_id:row.operation_id});if(status.operation.approval.description.untrusted_content.page_state.url.includes(id))prepared=status.operation.approval;}cursor=pending.data.cursor;}while(cursor&&!prepared);
        assert.ok(prepared);await approval({approval:prepared},id);await call('close_tab',{tab:child.tab});
      }
    }
  });
  await check('GROUP 11 REVIEW explicit pay and delete evidence overrides an owner allowed adapter',async()=>{
    await nav('review-page&mode=mixed-adapter&variant=none&id=review-adapter-baseline','gemini');const original=await call('click',await target('Send'));await approval(original,'review-adapter-baseline');
    const entry=admin('chrome_sites',{command:'allow',operation_id:original.approval.operation_id});
    try{for(const word of ['Pay','Delete']){const id='review-mixed-'+word;await nav('review-page&mode=mixed-adapter&variant='+word+'&id='+id,'gemini');const prepared=await call('click',await target('Send'));assert.ok(prepared.approval);assert.match(prepared.approval.question,new RegExp(word==='Pay'?'pay for':'delete'));assert.equal((await rpc('submit_trusted',prepared.approval)).ok,false);assert.equal(counts(id),0);await approval(prepared,id);}}
    finally{admin('chrome_sites',{command:'revoke',id:entry.id});}
  });
  await check('GROUP 2 REVIEW synchronous new shadow roots keep all submission kinds held',async()=>{
    for(const mode of ['open','closed'])for(const kind of ['native','event','click']){
      const id='review-shadow-'+mode+'-'+kind;await nav('review-page&mode=shadow&variant='+mode+'-'+kind+'&id='+id);
      const result=await call('click',await target('Continue'));assert.equal(counts(id),0);
      if(kind==='click'){
        assert.ok(result.followups?.some(row=>row.stopped),'script activation is stopped and never resumed');
        await approval(await call('click',await target('Submit')),id);
      }else await approval(result,id);
      console.log('REVIEW P5 RECEIVER0/1/1',id);
    }
  });
  await check('GROUP 2 REVIEW new shadow roots capture borrowed native events including noncomposed ones',async()=>{
    for(const mode of ['open','closed'])for(const composed of [false,true])for(const cancel of [false,true]){
      setTab(await nativeDonor(getTab()));
      const id='review-fallback-'+mode+'-'+composed+'-'+cancel;await nav('review-page&mode=shadow-fallback&variant='+mode+'&composed='+composed+'&cancel='+cancel+'&id='+id);
      const result=await call('click',await target('Continue'));assert.equal(counts('handler-'+id),0,'borrowed native event never reaches the asking handler');
      if(cancel){assert.equal(counts(id),0);assert.ok(result.followups.some(row=>row.stopped));await approval(await call('click',await target('Delete')),id);}
      else{assert.ok(counts(id)<=1);assert.ok(result.untrusted_content.steps.some(step=>step.kind==='activation_unknown'));assert.ok(!result.followups.some(row=>row.approval),'unknown activation never resumes');assert.equal((await call('operation_status',{operation_id:result.operation_id})).operation.state,'unknown');}
      await closeNativeDonor();console.log('REVIEW P5 borrowed native',id,'receiver',counts(id),'handler',counts('handler-'+id));
    }
  });
  await check('GROUP 1 REVIEW modified deletion keys normalized words malformed URLs and visible names',async()=>{
    for(const key of ['Shift+Delete','Ctrl+Backspace']){
      const id='review-key-'+key.replace('+','-');await nav('action-matrix&mode=delete&id='+id);
      const result=await call('press',{...await target('Selected item'),key});assert.match(result.approval.question,/delete.*using/);await approval(result,id);
    }
    for(const variant of ['nfc-delete','nfc-send','title','%ZZ','%FF','%E2%82']){
      const id='review-word-'+encodeURIComponent(variant);await nav('review-page&mode=label&variant='+encodeURIComponent(variant)+'&id='+encodeURIComponent(id));
      const result=await call('click',await target(variant==='title'?'Delete':variant==='nfc-delete'?'lo\u0308schen':variant==='nfc-send'?'vero\u0308ffentlichen':'Continue'));
      await approval(result,id);console.log('REVIEW P6 P7 P8 P15 RECEIVER0/1/1',id);
    }
  });
  await check('GROUP 3 REVIEW item confirmation file rich text and title mutations refuse',async()=>{
    for(const [mode,variant,label]of [['binding','listitem','Delete'],['binding','row','Delete'],['binding','article','Delete'],['binding','region','Delete'],['binding','section','Delete'],['binding','unsubscribe','Unsubscribe'],['binding','abbestellen','Abbestellen'],['confirmation','','OK'],['file','','Submit'],['rich','','Send'],['title','','Send']]){
      const id='review-bind-'+mode+'-'+variant;await nav('review-page&mode='+mode+'&variant='+variant+'&id='+id);
      const prepared=await call('click',await target(label));assert.ok(prepared.approval,JSON.stringify(prepared));
      await fixture.mutate(id,'review-change');const result=await rpc('submit',prepared.approval);
      assert.ok(!result.ok||result.data.operation.state==='failed',JSON.stringify(result));assert.equal(counts(id),0);
      await approval(await call('click',await target(label)),id);console.log('REVIEW P10 P11 P12 P13 P14 P22 RECEIVER0/1/1',id);
    }
  });
  await check('GROUP 2 REVIEW owner mark exact form submitter and unconsumed delayed work',async()=>{
    for(const variant of ['other-form','other-submitter','delayed-unconsumed']){
      const id='review-owner-'+variant;await nav('review-page&mode=owner-mark&variant='+variant+'&id='+id);
      const pending=call('click',await target('Continue'));
      const start=await eventually(()=>fixture.arrivals.find(row=>row.url.includes('case=task-start')&&row.body===id),'Claude start');
      await delay(Math.max(0,start.time+130-Date.now()));ownerKey();await approval(await pending,id);
      console.log('REVIEW P20 RECEIVER0/1/1',id);
    }
  });
  await check('GROUP 8 REVIEW iframe drafts and detached or Web Audio report before reload',async()=>{
    for(const mode of ['blank-editor','detached-media','web-audio']){
      const id='review-taken-'+mode,tab=getTab();await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=take-state&id='+id+'&mode='+mode);
      await eventually(()=>counts('loaded-'+id)===1,'owner page loaded');
      if(mode!=='blank-editor'){ownerKey();await eventually(()=>counts('playing-'+id)===1,'detached playback started');await delay(500);}
      await call('take_tab',{tab});const before=await target('Continue');const first=await rpc('click',before);assert.equal(first.ok,false);assert.equal(first.error.code,'reload_required');assert.equal(counts('loaded-'+id),1);
      const repeat=await rpc('click',{...before,reload_taken_tab:true});assert.equal(repeat.ok,false);assert.equal(repeat.error.code,'stale_reference');await eventually(()=>counts('loaded-'+id)===2,'explicit guarded reload');
    }
  });
  await check('GROUP 8 REVIEW script-started POST documents in tabs and popups never reload',async()=>{
    const tab=getTab(),id='review-script-post';await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=script-post&id='+id);await eventually(()=>counts(id)===1,'script POST');await call('take_tab',{tab});const refused=await rpc('click',await target('Continue'));assert.equal(refused.ok,false);assert.match(refused.error.message,/form submission|request method/);assert.equal(counts(id),1);
    await nav('review-page&mode=script-popup&id=review-script-popup');await call('click',await target('Open window'));await eventually(()=>counts('review-script-popup')===1,'popup script POST');
    const child=await eventually(async()=>(await call('tabs',{limit:100})).items.find(row=>row.url?.includes('/post-document?case=review-script-popup')),'POST popup exists');
    const page=await call('read',{tab:child.tab});const row=page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Continue');assert.ok(row);
    const popupRefused=await rpc('click',{reference:row.reference,expected:row.expected});assert.equal(popupRefused.ok,false);assert.match(popupRefused.error.message,/form submission|request method/);assert.equal(counts('review-script-popup'),1);await call('close_tab',{tab:child.tab});
  });
  await check('GROUP 4 REVIEW independent native dialogs arm before accept or dismiss or stay with owner',async()=>{
    for(const accept of [false,true]){
      const id='review-independent-dialog-'+accept;await nav('review-page&mode=independent-dialog&id='+id);await delay(600);await fixture.mutate(id,'review-change');
      const dialog=await eventually(async()=>(await call('read',{tab:getTab()})).dialog,'independent native dialog');assert.equal(counts(id),0);
      const answer=await rpc('dialog',{tab:getTab(),expected:dialog,accept});
      assert.equal(counts(id),0,'answering must never resume an unapproved form submission');
      if(!answer.ok){assert.equal(answer.error.code,'refused');assert.match(answer.error.message,/leave it to the owner/);assert.deepEqual((await call('read',{tab:getTab()})).dialog,dialog);console.log('REVIEW P1 private modal arming unavailable: owner handoff, receiver 0',id);ownerDismiss();await delay(600);}
      else{await approval(answer.data,id);console.log('REVIEW P1 RECEIVER0/1/1',id);}
    }
  });
  await check('GROUP 8 REVIEW no-op checks and isolated choices leave the owner tab selected',async()=>{
    const tab=getTab();await nav('features&id=review-noop');await call('check',{...await target('Tick'),checked:true});
    const owner=(await call('open',{url:'about:blank'})).untrusted_content.tab;assert.ok(Number.isInteger(owner));await call('release_tab',{tab:owner});
    const active=async()=>(await call('tabs',{limit:100})).items.find(row=>row.active&&row.focused)?.tab;assert.equal(await active(),owner);
    const result=await call('check',{...await target('Tick'),checked:true});assert.equal(result.untrusted_content.no_change,true);assert.equal(result.untrusted_content.dispatched,false);assert.equal(await active(),owner);
    await call('select',{...await target('Choice'),value:'b'});assert.equal(await active(),owner,'isolated selection cannot take focus');
    assert.equal((await call('tabs',{limit:100})).items.find(row=>row.tab===tab).active,false);
    await call('take_tab',{tab:owner});await call('close_tab',{tab:owner});
  });
  await check('GROUP 8 REVIEW Stop removes navigation blocks while a frozen wrapper awaits cleanup',async()=>{
    const tab=getTab();await nav('review-page&mode=frozen-stop&id=review-stop-blocks');await call('click',await target('Continue'));await lifecycle({fixture:'stop'});
    const stopped=(await call('tabs',{limit:100})).items.find(row=>row.tab===tab);assert.equal(stopped.controlled,false);assert.equal(stopped.cleanup_pending,true);
    await ownerNavigate('http://approval.test:8765/receive?case=review-stop-blocks');await eventually(()=>counts('review-stop-blocks')===1,'owner navigation is no longer DNR-blocked');
    await eventually(async()=>!(await call('tabs',{limit:100})).items.find(row=>row.tab===tab).cleanup_pending,'native document replacement finishes cleanup');
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
  });
  await check('GROUP 5 REVIEW page outcome records the actual post-input notice',async()=>{
    await nav('review-page&mode=notice&id=review-notice');const result=await call('click',await target('Continue'));
    assert.match(JSON.stringify(result.untrusted_content.page),/ERROR: the change failed/);
  });
}
