import assert from 'node:assert/strict';
import {assertOwnerOverlap} from './owner-evidence.mjs';
import {completeIngress} from './ingress-scan.mjs';
import {setTimeout as delay} from 'node:timers/promises';
import {allTabs} from './tabs.mjs';
import {createHash} from 'node:crypto';
import fs from 'node:fs';

export async function guardedHandoffClick({rpc,call,target,eventually,receiverEvidence,id}){
  const before=await target('Ready');
  const first=await rpc('click',{...before,reload_taken_tab:true});
  assert.equal(first.ok,false);assert.equal(first.error.code,'stale_reference');
  assert.match(first.error.message,/reloaded to install its page guard/);
  // The new document can still be parsing after the reload has committed.
  let previous;
  const fresh=await eventually(async()=>{
    const current=await target('Ready');
    const settled=current.reference.document!==before.reference.document&&previous&&JSON.stringify(current.reference)===JSON.stringify(previous.reference);
    previous=current;return settled?current:false;
  },'guarded reload Ready view settled');
  assert.equal(receiverEvidence(id,'reload settled before guarded act').count,1);
  const stale=await rpc('click',before);assert.equal(stale.ok,false);assert.equal(stale.error.code,'stale_reference');
  assert.equal(receiverEvidence(id,'old reference still refuses').count,1);
  await call('click',fresh);
  assert.equal(receiverEvidence(id,'first guarded act after handoff').count,1);
}

export async function reviewMatrices({check,nav,call,rpc,target,read,counts,eventually,approval,receiverEvidence,fixture,getTab,ownerKey,ownerChooseFile,admin,ownerNavigate,ownerDismiss,nativeDonor,closeNativeDonor,setTab,lifecycle}){
  await check('GROUP 2 RECHECK Claude timer fires inside the owner Enter mark',async()=>{
    const id='recheck-owner-overlap';await nav('review-page&mode=owner-overlap&id='+id);
    const pending=call('click',await target('Continue'));
    const start=await eventually(()=>fixture.arrivals.find(row=>row.url.includes('case=task-start')&&row.body===id),'Claude timer started');
    await delay(Math.max(0,start.time+130-Date.now()));ownerKey(true);const result=await pending;
    await eventually(()=>counts('owner-'+id)===1,'his immediate Enter arrival');
    assert.equal(receiverEvidence(id,'timer held during owner mark').count,0);
    const traces=completeIngress(fs.readFileSync('/out/browser-boundary.jsonl','utf8')).filter(row=>row?.owner_trace).map(row=>row.owner_trace);
    const evidence=assertOwnerOverlap(id,fixture.arrivals,traces);fs.writeFileSync('/out/owner-overlap.json',JSON.stringify(evidence,null,2));
    console.log('OWNER ENTER TIMER OVERLAP',JSON.stringify(evidence));
    await approval(result,id);assert.equal(receiverEvidence('owner-'+id,'owner Enter remains once').count,1);
  });
  await check('GROUP 2 RECHECK explicit payment and delete labels override GET search',async()=>{
    for(const variant of ['pay','delete','editable-native','editable-aria']){
      const id='recheck-search-'+variant;await nav('review-page&mode=search-label&variant='+variant+'&id='+id);
      const result=await call('click',await target('Continue'));
      assert.equal(receiverEvidence(id,'script handler stopped').count,0);assert.ok(result.followups?.some(row=>row.stopped));
      await approval(await call('click',await target(variant==='delete'?'Delete':'Pay')),id);
    }
    for(const [index,query] of ['Pay for lunch','Delete old notes','Send a letter'].entries()){
      const id='recheck-query-'+index;await nav('review-page&mode=ordinary-search&id='+id+'&query='+encodeURIComponent(query));
      const result=await call('press',{...await target('Query'),key:'Enter'});assert.ok(!result.approval&&!result.followups?.some(row=>row.approval),JSON.stringify(result));
      await eventually(()=>counts(id)===1,'ordinary GET search stays free');const evidence=receiverEvidence(id,'ordinary search is free');assert.equal(evidence.count,1);assert.equal(evidence.arrivals[0].method,'GET');assert.equal(new URL(evidence.arrivals[0].url,'http://fixture.test').searchParams.get('q'),query);
    }
  });
  await check('GROUP 4 REVIEW ordinary native dialogs from Claude owner and page tasks keep working',async()=>{
    for(const kind of ['alert','confirm','prompt'])for(const origin of ['claude','owner','task'])for(const accept of kind==='alert'?[true]:[false,true]){
      const id='review-dialog-'+kind+'-'+origin+'-'+accept;await nav('review-page&mode=native-dialog&dialog='+kind+'&id='+id);await delay(600);
      if(origin==='claude'){const opened=await rpc('click',await target('Continue'));assert.ok(opened.ok||opened.error.code==='unknown',JSON.stringify(opened));}
      else if(origin==='owner')ownerKey();else await fixture.mutate(id,'review-change');
      const dialog=await eventually(async()=>(await call('read',{tab:getTab()})).untrusted_content.dialog,'native '+kind+' from '+origin);assert.equal(dialog.kind,kind);assert.equal(dialog.unguarded,undefined,'ordinary dialogs must retain their private return hold');assert.equal(receiverEvidence(id,'native dialog open').count,0);
      const answer=await call('dialog',{tab:getTab(),expected:dialog,accept,...(kind==='prompt'?{text:'Synthetic answer'}:{})});
      assert.ok(!answer.approval,'the ordinary native answer has already happened');assert.ok(answer.followups?.some(row=>row.approval),'its resumed submission has a separate held approval');
      assert.equal(receiverEvidence(id,'after native answer').count,0,'answering cannot approve the resumed form');
      await approval(answer,id);console.log('REVIEW P1 ANSWERED RECEIVER0/1/1',id);
      const received=fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id);
      assert.equal(new URLSearchParams(received.body).get('reply'),kind==='alert'?'undefined':kind==='prompt'?(accept?'Synthetic answer':'null'):String(accept),'the cached native dialog must keep its return value');
    }
  });
  await check('GROUP 4 REVIEW blank and srcdoc native dialogs answer with a held continuation',async()=>{
    for(const variant of ['blank','srcdoc'])for(const kind of ['alert','confirm','prompt']){
      const id='review-inline-dialog-'+variant+'-'+kind;await nav('review-page&mode=inline-dialog&variant='+variant+'&dialog='+kind+'&id='+id);await delay(600);
      const opened=await rpc('click',await target('Continue'));assert.ok(opened.ok||opened.error.code==='unknown',JSON.stringify(opened));
      const dialog=await eventually(async()=>(await call('read',{tab:getTab()})).untrusted_content.dialog,'inline '+variant+' '+kind);assert.equal(dialog.kind,kind);assert.notEqual(dialog.frame,0);assert.equal(dialog.unguarded,undefined);assert.equal(receiverEvidence(id,'inline native dialog open').count,0);
      const answer=await call('dialog',{tab:getTab(),expected:dialog,accept:true,...(kind==='prompt'?{text:'Inline answer'}:{})});assert.equal(receiverEvidence(id,'inline native answered with hold').count,0);await approval(answer,id);
    }
  });
  await check('GROUP 8 REVIEW preexisting dialogs hand off within bounds and recover after the owner answers',async()=>{
    for(const kind of ['alert','confirm','prompt']){
      const id='review-preexisting-'+kind,tab=getTab(),session=(await call('tabs')).session;
      assert.equal(typeof session,'string');
      await call('release_tab',{tab});await eventually(async()=>(await allTabs(call)).items.some(row=>row.tab===tab&&!row.controlled&&!row.cleanup_pending),'owner tab fully released');
      await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=preexisting-dialog&dialog='+kind+'&id='+id);await delay(600);
      const started=Date.now(),taken=await call('take_tab',{tab});assert.ok(Date.now()-started<15000,'handoff is bounded before the transport deadline');assert.equal(taken.untrusted_content.owner_dialog,true);assert.match(taken.untrusted_content.ask_owner,/answer the dialog yourself/);assert.equal(receiverEvidence(id,'bounded handoff').count,0);
      try{fs.unlinkSync('/out/control-status.json');}catch(error){if(error.code!=='ENOENT')throw error;}
      await lifecycle({fixture:'control_status'});const status=await eventually(()=>fs.existsSync('/out/control-status.json')&&JSON.parse(fs.readFileSync('/out/control-status.json')),'native debugger snapshot after handoff');
      assert.equal(status.debugger_targets.find(row=>row.tab===tab)?.attached,false,'no debugger remains attached behind the native dialog');
      ownerDismiss();await eventually(()=>counts(id)===1,'owner answers the preexisting dialog');assert.equal(receiverEvidence(id,'owner answer').count,1);
      await eventually(async()=>(await read()).some(row=>row.expected.name==='Ready'),'read recovers without restarting Chrome');assert.equal((await call('tabs')).session,session);
      assert.equal((await call('operation_status',{operation_id:taken.operation_id})).operation.state,'done');
      await guardedHandoffClick({rpc,call,target,eventually,receiverEvidence,id});
    }
  });
  await check('GROUP 4 REVIEW borrowed native dialogs always ask bind the answer and never replay',async()=>{
    for(const kind of ['alert','confirm','prompt'])for(const variant of kind==='prompt'?['direct','conversion-message','conversion-default','changed-dialog']:['direct','conversion-message','changed-dialog']){
      setTab(await nativeDonor(getTab()));const tab=getTab(),id='review-borrowed-'+kind+'-'+variant;await nav('review-page&mode=borrowed-dialog&dialog='+kind+'&variant='+variant+'&id='+id);await delay(600);await fixture.mutate(id,'review-change');
      const dialog=await eventually(async()=>(await call('read',{tab})).untrusted_content.dialog,'borrowed '+kind);assert.equal(dialog.unguarded,true);
      const prepared=await call('dialog',{tab,expected:dialog,accept:true,...(kind==='prompt'?{text:'Chosen prompt'}:{})});assert.ok(prepared.approval);assert.match(prepared.approval.question,/outside the page guard/);assert.match(prepared.approval.question,/continuation isn't held/);assert.equal(receiverEvidence(id,'borrowed question').count,0);
      const changed=structuredClone(prepared.approval);changed.description.untrusted_content.input.accept=false;assert.equal((await rpc('submit',changed)).ok,false);assert.equal((await rpc('submit_trusted',prepared.approval)).ok,false);assert.equal(receiverEvidence(id,'borrowed unapproved answers refused').count,0);
      if(variant==='changed-dialog'){
        ownerDismiss();await eventually(async()=>!(await call('read',{tab})).untrusted_content.dialog,'owner closed first borrowed dialog');await fixture.mutate(id,'review-change');
        const replacement=await eventually(async()=>(await call('read',{tab})).untrusted_content.dialog,'replacement borrowed dialog');assert.notEqual(replacement.id,dialog.id);assert.equal(replacement.unguarded,true);
        const stale=await rpc('submit',prepared.approval);assert.ok(!stale.ok||stale.data.operation.state==='failed');assert.equal(receiverEvidence(id,'changed dialog approval refused').count,0);
        await approval(await call('dialog',{tab,expected:replacement,accept:true,...(kind==='prompt'?{text:'Replacement answer'}:{})}),id);
      }else if(variant==='direct')await approval(prepared,id);
      else{
        await call('submit',prepared.approval);assert.equal(receiverEvidence(id,'borrowed approved before outer dialog').count,0);await call('submit',prepared.approval);assert.equal(receiverEvidence(id,'borrowed approval repeated before outer dialog').count,0);
        const outer=await eventually(async()=>(await call('read',{tab})).untrusted_content.dialog,'outer native after string conversion');assert.equal(outer.unguarded,undefined);assert.notEqual(outer.id,dialog.id);
        const answered=await call('dialog',{tab,expected:outer,accept:true,...(kind==='prompt'?{text:'Outer answer'}:{})});assert.ok(!answered.approval);assert.equal(receiverEvidence(id,'outer native answered with hold').count,0);await approval(answered,id);
      }
      await closeNativeDonor();
    }
  });
  await check('GROUP 3 REVIEW ordinary blank and srcdoc editors bind drafts and send normally',async()=>{
    for(const variant of ['blank','srcdoc'])for(const changed of [false,true]){
      const id='review-editor-'+variant+'-'+changed;await nav('review-page&mode=inline-editor&variant='+variant+'&id='+id);
      let prepared=await call('click',await target('Send'));assert.ok(prepared.approval);assert.match(JSON.stringify(prepared.approval),/First draft line/);
      if(changed){await fixture.mutate(id,'review-change');const old=await rpc('submit',prepared.approval);assert.ok(!old.ok||old.data.operation.state==='failed');assert.equal(receiverEvidence(id,'inline draft changed').count,0);prepared=await call('click',await target('Send'));}
      await approval(prepared,id);
    }
  });
  await check('GROUP 3 REVIEW owner chosen attachments show byte digests and bind identical metadata replacements',async()=>{
    const id='review-owner-file';await nav('review-page&mode=owner-file&id='+id);
    const opening=call('click',await target('File'));opening.catch(()=>{});await ownerChooseFile();await opening;
    await eventually(async()=>(await read()).some(row=>row.expected.name==='File'&&row.expected.value?.length===1),'owner chosen File is installed');
    const first=await call('click',await target('Submit'));assert.ok(first.approval);
    assert.doesNotMatch(JSON.stringify(first.approval.description),/GOOD|EVIL/,'file bytes must never enter the approval or binding');
    for(const text of ['owner-picked.txt','4 bytes',createHash('sha256').update('GOOD').digest('hex')])assert.ok(first.approval.question.includes(text),first.approval.question);
    fs.writeFileSync('/out/owner-picked.txt','EVIL');fs.utimesSync('/out/owner-picked.txt',1700000000,1700000000);
    const refused=await rpc('submit',first.approval);assert.ok(!refused.ok||refused.data.operation.state==='failed');assert.equal(receiverEvidence(id,'selected bytes changed').count,0);
    await fixture.mutate(id,'review-change');
    const second=await call('click',await target('Submit'));assert.ok(second.approval.question.includes(createHash('sha256').update('EVIL').digest('hex')));await approval(second,id);
    assert.match(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).body,/EVIL/);
  });
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
      const child=await eventually(async()=>(await allTabs(call)).items.find(row=>row.url?.includes('mode=cross-tab-inner&id='+id)),'controlled other tab');
      const childTarget=async()=>{const page=await call('read',{tab:child.tab});const row=page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Ready');return row&&{reference:row.reference,expected:row.expected};};
      const old=await eventually(childTarget,'other tab reader');const first=await rpc('click',old);assert.equal(first.ok,false);assert.equal(first.error.code,'stale_reference');
      await call('click',await eventually(childTarget,'guarded other tab'));
      if(outside)await call('release_tab',{tab:child.tab});
      await call('click',await target('Continue'));
      if(outside){await eventually(()=>counts(id)===1,'outside document takes native path');await call('take_tab',{tab:child.tab});await call('close_tab',{tab:child.tab});}
      else{
        assert.equal(counts(id),0,'the other controlled document cannot take the source native path');
        await call('read',{tab:child.tab});let cursor,prepared;
        do{const pending=await rpc('control_pending',{limit:10,...(cursor?{cursor}:{})});assert.equal(pending.ok,true);for(const row of pending.data.items){if(row.app!=='chrome'||row.state!=='reserved')continue;const status=await call('operation_status',{operation_id:row.operation_id});if(status.operation.approval?.description?.untrusted_content?.page_state?.url?.includes(id))prepared=status.operation.approval;}cursor=pending.data.cursor;}while(cursor&&!prepared);
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
    for(const native of [false,true])for(const mode of ['open','closed'])for(const composed of [false,true])for(const cancel of [false,true]){
      setTab(await nativeDonor(getTab()));
      const id='review-fallback-'+native+'-'+mode+'-'+composed+'-'+cancel;await nav('review-page&mode=shadow-fallback&variant='+mode+'&composed='+composed+'&cancel='+cancel+'&native='+native+'&id='+id);
      const result=await call('click',await target('Continue'));assert.equal(receiverEvidence('handler-'+id,'borrowed native handler held').count,0,'borrowed native event never reaches the asking handler');
      assert.equal(receiverEvidence(id,'native default stopped before approval').count,0);assert.ok(result.followups.some(row=>row.stopped));assert.ok(!result.followups.some(row=>row.approval),'activations never resume');
      assert.ok(result.untrusted_content.steps.every(step=>step.kind==='activation'));await approval(await call('click',await target('Delete')),id);
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
    for(const [mode,variant,label]of [['binding','listitem','Delete'],['binding','row','Delete'],['binding','article','Delete'],['binding','region','Delete'],['binding','section','Delete'],['binding','unsubscribe','Unsubscribe'],['binding','abbestellen','Abbestellen'],['confirmation','','OK'],['confirmation','form','OK'],['confirmation','submit','OK'],['confirmation','submit-send','Send'],['quantity','','Pay'],['compose-key','','Message'],...['li-open','li-closed','row-open','row-closed','slot-li-open','slot-li-closed','slot-row-open','slot-row-closed'].map(variant=>['shadow-binding',variant,'Delete']),['file','','Submit'],['rich','','Send'],['title','','Send']]){
      const id='review-bind-'+mode+'-'+variant;await nav('review-page&mode='+mode+'&variant='+variant+'&id='+id);
      const prepare=async()=>mode==='compose-key'?call('press',{...await target(label),key:'Enter'}):call('click',await target(label));
      const prepared=await prepare();assert.ok(prepared.approval,JSON.stringify(prepared));
      if(mode==='shadow-binding'){assert.match(JSON.stringify(prepared.approval),/Invoice A/);if(variant.startsWith('slot-')){await eventually(()=>counts('slot-probe-'+id)===1,'native slot visibility probe');const probe=JSON.parse(receiverEvidence('slot-probe-'+id,'native closed-slot visibility').arrivals[0].body);assert.deepEqual(probe,{closed:variant.endsWith('closed'),public_slot:!variant.endsWith('closed')});}}
      if(['confirmation','compose-key'].includes(mode))assert.match(JSON.stringify(prepared.approval),/Approved draft/);
      if(mode==='quantity')assert.equal(prepared.approval.description.untrusted_content.page_state.item_fields.find(field=>field.label==='Quantity').value,'1');
      await fixture.mutate(id,'review-change');const result=await rpc('submit',prepared.approval);
      assert.ok(!result.ok||result.data.operation.state==='failed',JSON.stringify(result));assert.equal(receiverEvidence(id,'changed approval refused').count,0);
      const fresh=await prepare();
      if(mode==='shadow-binding')assert.match(JSON.stringify(fresh.approval),/Invoice B/);
      if(['confirmation','compose-key'].includes(mode))assert.match(JSON.stringify(fresh.approval),/Different draft/);
      if(mode==='quantity')assert.equal(fresh.approval.description.untrusted_content.page_state.item_fields.find(field=>field.label==='Quantity').value,'2');
      await approval(fresh,id);
      if(['shadow-binding','confirmation','compose-key'].includes(mode))assert.equal(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).body,mode==='shadow-binding'?'Invoice B':'Different draft');
      if(mode==='quantity')assert.equal(receiverEvidence(id,'approved quantity').arrivals[0].body,'2');
      console.log('REVIEW P10 P11 P12 P13 P14 P22 RECEIVER0/1/1',id);
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
    const tab=getTab(),id='review-script-post';await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=script-post&variant=after-owner-navigation&id='+id);
    await fixture.mutate(id,'review-change');await eventually(()=>counts(id)===1,'script POST');
    await eventually(async()=>(await allTabs(call)).items.some(row=>row.tab===tab&&row.url==='http://fixture.test:8765/post-document?case='+id),'script POST committed in the exact owner tab');
    await call('take_tab',{tab});const refused=await rpc('click',await target('Continue'));assert.equal(refused.ok,false);assert.match(refused.error.message,/form submission|request method/);assert.equal(counts(id),1);
    await nav('review-page&mode=script-popup&id=review-script-popup');await call('click',await target('Open window'));await eventually(()=>counts('review-script-popup')===1,'popup script POST');
    const child=await eventually(async()=>(await allTabs(call)).items.find(row=>row.url?.includes('/post-document?case=review-script-popup')),'POST popup exists');
    const page=await call('read',{tab:child.tab});const row=page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Continue');assert.ok(row);
    const popupRefused=await rpc('click',{reference:row.reference,expected:row.expected});assert.equal(popupRefused.ok,false);assert.match(popupRefused.error.message,/form submission|request method/);assert.equal(counts('review-script-popup'),1);await call('close_tab',{tab:child.tab});
  });
  await check('GROUP 8 REVIEW no-op checks and isolated choices leave the owner tab selected',async()=>{
    const tab=getTab();await nav('features&id=review-noop');await call('check',{...await target('Tick'),checked:true});
    const owner=(await call('open',{url:'about:blank'})).untrusted_content.tab;assert.ok(Number.isInteger(owner));await call('release_tab',{tab:owner});
    const active=async()=>(await allTabs(call)).items.find(row=>row.active&&row.focused)?.tab;assert.equal(await active(),owner);
    const result=await call('check',{...await target('Tick'),checked:true});assert.equal(result.untrusted_content.no_change,true);assert.equal(result.untrusted_content.dispatched,false);assert.equal(await active(),owner);
    await call('select',{...await target('Choice'),value:'b'});assert.equal(await active(),owner,'isolated selection cannot take focus');
    assert.equal((await allTabs(call)).items.find(row=>row.tab===tab).active,false);
    await call('take_tab',{tab:owner});await call('close_tab',{tab:owner});
  });
  await check('GROUP 8 REVIEW Stop removes navigation blocks while a frozen wrapper awaits cleanup',async()=>{
    const tab=getTab();await nav('review-page&mode=frozen-stop&id=review-stop-blocks');await call('click',await target('Continue'));await lifecycle({fixture:'stop'});
    const stopped=(await allTabs(call)).items.find(row=>row.tab===tab);assert.equal(stopped.controlled,false);assert.equal(stopped.cleanup_pending,true);
    await ownerNavigate('http://approval.test:8765/receive?case=review-stop-blocks',{allowPendingCleanup:true});await eventually(()=>counts('review-stop-blocks')===1,'owner navigation is no longer DNR-blocked');
    await eventually(async()=>!(await allTabs(call)).items.find(row=>row.tab===tab).cleanup_pending,'native document replacement finishes cleanup');
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
  });
  await check('GROUP 5 REVIEW page outcome records the actual post-input notice',async()=>{
    await nav('review-page&mode=notice&id=review-notice');const result=await call('click',await target('Continue'));
    assert.match(JSON.stringify(result.untrusted_content.page),/ERROR: the change failed/);
  });
}
