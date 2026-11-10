// Synthetic browser cases, imported only by the Linux-container entry point.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {verdicts} from './verdicts.mjs';
import {setTimeout as delay} from 'node:timers/promises';
import {measureCompatibility,compareCompatibility} from './compatibility.mjs';
import {popupMatrices} from './popups.mjs';
import {collectSiteResults} from './site-results.mjs';

export async function matrices({call,read,nav,target,counts,eventually,tab,fixture,admin,rpc,caller,ownerNavigate,ownerOpenPopup,popupEvidence,nativeDonor,closeNativeDonor,ownerKey,ownerDismiss,ownerHistory,ownerBookmark,lifecycle,restoreControl,stopClick,baseline,isolationAfter}) {
  const results=[];let trustOperation;
  async function check(name,fn) {
    try {await fn();results.push({name,passed:true});console.log(name,'PASS');}
    catch(error){results.push({name,passed:false,error:String(error.stack)});console.error(name,'FAIL',error.stack);
      // Preserve the failed assertion, then start a fresh browser for the next independent group.
      // Never retry this case or turn its result into a pass.
      if(name.startsWith('QUALIFICATION')||name.startsWith('GROUP 11'))try{await lifecycle({fixture:'kind',mode:'restore'});await lifecycle({fixture:'qualification',mode:'qualified'});}catch(recovery){console.error('FIXTURE POLICY CLEANUP FAILED',String(recovery));}
      if(!name.startsWith('GROUP 9'))try{await lifecycle('kill_chrome');await lifecycle('start_chrome');tab=await restoreControl();}catch(recovery){console.error('FIXTURE RECOVERY FAILED',String(recovery));}
    }
  }
  async function approval(result,id) {
    const prepared=result.approval ? result:result.followups?.find(item=>item.approval);
    assert.ok(prepared?.approval,JSON.stringify(result));assert.equal(counts(id),0,'zero arrivals before approval');
    await call('submit',prepared.approval);await eventually(()=>counts(id)===1,'one receiver arrival '+id);
    await call('submit',prepared.approval);await delay(30);assert.equal(counts(id),1,'a second attempt sends nothing');
  }
  async function reservedFor(id,except){
    let cursor;
    do{
      const current=await rpc('control_pending',{limit:10,...(cursor?{cursor}:{})});assert.equal(current.ok,true);
      for(const row of current.data.items){
        if(row.app!=='chrome'||row.operation_id===except||row.state!=='reserved')continue;
        const status=await call('operation_status',{operation_id:row.operation_id});
        if(status.operation.approval?.description?.untrusted_content?.page_state?.url?.includes(id))return status.operation.approval;
      }
      cursor=current.data.cursor;
    }while(cursor);
  }
  async function setup(parameters) {await nav('matrix&'+new URLSearchParams(parameters));}
  const words=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]).words;
  await check('GROUP 2 first-script natives are guarded in pages and frames',async()=>{
    for(const kind of ['top','same','cross']){
      const id='first-'+kind;await nav(kind==='top'?'preload-origin&id='+id:'preload-frame&id='+id+(kind==='cross'?'&cross=1':''));
      await approval(await call('click',await target('Continue')),id);
    }
  });
  await popupMatrices({check,call,rpc,nav,counts,eventually,tab,fixture,ownerOpenPopup,popupEvidence,approval});
  await check('GROUP 7 native compatibility inside and outside Claude tabs',async()=>{
    await nav('native-compat&id=controlled');
    const controlled=await measureCompatibility({id:'controlled',fixture,eventually,start:async()=>call('click',await target('Continue'))});
    fs.writeFileSync('/out/native-controlled.json',JSON.stringify(controlled,null,2));compareCompatibility(controlled,baseline.native);
  });
  await check('GROUP 8 Stop under a native modal revokes input before deferred cleanup',async()=>{
    await nav('stop-modal&id=stop-modal');const prepared=await call('click',await target('Send'));
    const opened=await call('click',await target('Continue'));assert.ok(opened.untrusted_content.dialog);assert.equal(counts('stop-modal'),0);
    const started=Date.now();await lifecycle({fixture:'stop'});assert.ok(Date.now()-started<3000,'Stop must return while the modal still blocks script cleanup');
    const stopped=JSON.parse(fs.readFileSync('/out/stop-result.json'));assert.equal(stopped.stopped,true);assert.ok(stopped.cleanup_pending);
    assert.equal((await call('tabs')).items.find(item=>item.tab===tab).controlled,false);
    const denied=await rpc('submit',prepared.approval);assert.ok(!denied.ok||denied.data.operation.state==='failed');assert.equal(counts('stop-modal'),0);
    ownerDismiss();await eventually(async()=>!(await call('tabs')).items.find(item=>item.tab===tab).cleanup_pending,'modal cleanup finishes after native owner dismissal');assert.equal(counts('stop-modal'),0,'Stop and dismissal never send the prepared work');
    await fixture.mutate('stop-modal','owner-native-click');await eventually(()=>counts('stop-modal')===1,'a cached page click works natively after release');
    await call('take_tab',{tab});
  });
  await check('GROUP 8 taken tabs preserve reads and guard the first input reload',async()=>{
    for(const mode of ['clean','dirty','media']){
      const id='taken-'+mode;await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=take-state&id='+id+'&mode='+mode);
      await eventually(()=>counts('loaded-'+id)===1,'taken page initial load');
      if(mode==='media'){ownerKey();await eventually(()=>counts('playing-'+id)===1,'native media started');}
      await call('take_tab',{tab});const before=await target('Continue');await read();await read();assert.equal(counts('loaded-'+id),1,'taking and reading never reload');
      const first=await rpc('click',before);assert.equal(first.ok,false);
      if(mode==='clean')assert.equal(first.error.code,'stale_reference');
      else{assert.equal(first.error.code,'reload_required');assert.equal(counts('loaded-'+id),1,'dirty and playing pages are preserved until explicit repeat');const repeated=await rpc('click',{...before,reload_taken_tab:true});assert.equal(repeated.ok,false);assert.equal(repeated.error.code,'stale_reference');}
      await eventually(()=>counts('loaded-'+id)===2,'only first input reloads');const fresh=await target('Continue');assert.notEqual(fresh.reference.document,before.reference.document);assert.equal((await rpc('click',before)).ok,false,'every old reference stays stale');await call('click',fresh);assert.equal(counts('loaded-'+id),2,'later input never repeats the reload');
    }
    await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=take-post');ownerKey();
    await eventually(()=>counts('taken-post')===1,'one native POST loaded the document');await call('take_tab',{tab});const denied=await rpc('click',await target('Continue'));assert.equal(denied.ok,false);assert.match(denied.error.message,/form submission|request method/);await delay(150);assert.equal(counts('taken-post'),1,'refusal must not resubmit POST');
    await call('navigate',{tab,url:'http://fixture.test:8765/?case=features&id=post-history'});await eventually(async()=>String((await call('read',{tab})).untrusted_content.url).includes('id=post-history'),'GET after POST');assert.equal((await rpc('navigate',{tab,direction:'back'})).ok,false);assert.equal(counts('taken-post'),1,'history must not resubmit POST');
  });
  results.push(...await collectSiteResults(()=>(import('./sites/matrices.mjs').then(({siteMatrices})=>siteMatrices({call,read,nav,target,counts,eventually,tab,fixture,admin,rpc,lifecycle})))));
  await check('GROUP 1 submit compose deletion and free-input matrix',async()=>{
    for(const tag of ['default','submit','override','external','empty','invalid','clobbered'])for(const key of ['click','Enter','Space','field']){
      const id='submit-'+tag+'-'+key;await nav('action-matrix&mode=submit&id='+id+'&tag='+tag);
      const result=key==='click'?await call('click',await target('Continue')):await call('press',{...await target(key==='field'?'Form field':'Continue'),key:key==='field'?'Enter':key});await approval(result,id);assert.equal(counts('unapproved-'+id),0,'the effective submitter destination must match approval');
    }
    for(const tag of ['textarea','input','div'])for(const key of ['Enter','Ctrl+Enter','Cmd+Enter']){
      const id='compose-'+tag+'-'+key;await nav('action-matrix&mode=compose&id='+encodeURIComponent(id)+'&tag='+tag);
      await approval(await call('press',{...await target('Compose'),key}),id);
    }
    for(const key of ['Delete','Backspace']){const id='delete-'+key;await nav('action-matrix&mode=delete&id='+id);await approval(await call('press',{...await target('Selected item'),key}),id);}
    await nav('action-matrix&mode=javascript&id=javascript');await approval(await call('click',await target('Delete')),'javascript');
    await nav('action-matrix&mode=free&id=free');
    for(const [verb,label,args] of [['fill','Text',{text:'Line one\nLine two'}],['select','Choice',{value:'b'}],['check','Tick',{checked:true}],['fill','Search',{text:'Search term'}]]){
      const result=await call(verb,{...await target(label),...args});assert.ok(!result.approval);assert.equal(result.followups.length,0);
    }
    assert.equal(counts('unexpected-enter'),0);
    const search=await call('click',await target('Continue'));assert.ok(!search.approval);await eventually(()=>counts('free')===1,'GET search stays free');
    const link=await call('click',await target('Read more'));assert.ok(!link.approval);await eventually(()=>counts('free')===2,'ordinary link stays free');
  });
  await check('GROUP 1 what asks word/label/key matrix',async()=>{
    let cases=0;
    for(const word of words)for(const label of ['name','aria','title','value','labelledby','hidden_labelledby','label','role','formaction']){
      const id='word-'+word+'-'+label;await setup({id,mode:'word',word,label});
      for(const route of ['click','Enter','Space']){
        const row=(await read()).find(row=>row.expected.role==='button'||row.expected.name==='Continue');assert.ok(row);
        const args={reference:row.reference,expected:row.expected};
        const result=route==='click'?await call('click',args):await call('press',{...args,key:route});
        await approval(result,id+'-'+route);cases++;
      }
      if(cases%81===0)console.log('GROUP 1 WORD_PROGRESS',cases,'strict receiver cases passed');
    }
  });
  await check('GROUP 1 Unicode word matching agrees across service and guard',async()=>{
    for(const [index,word]of ['ſend','veröﬀentlichen','beﬅellen'].entries()){
      const id='unicode-word-'+index;await setup({id,mode:'activation',wrapped:'click',word});
      const held=await call('click',await target('Continue'));assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);assert.ok(held.followups.some(item=>item.stopped));
      await approval(await call('click',await target(word)),id);assert.equal(counts('handler-'+id),1);
    }
  });
  await check('GROUP 2 stopped page steps handler/resume matrix',async()=>{
    for(const submit of ['native','event','button'])for(const route of ['click','key','fill','select','check']){
      const id='stopped-'+submit+'-'+route;await setup({id,mode:'stopped',submit,route});let result;
      if(route==='click')result=await call('click',await target('Continue'));
      else if(route==='key')result=await call('press',{...await target('Continue'),key:'x'});
      else if(route==='fill')result=await call('fill',{...await target('Trigger text'),text:'Changed'});
      else if(route==='select')result=await call('select',{...await target('Trigger choice'),value:'b'});
      else result=await call('check',{...await target('Trigger check'),checked:true});
      if(submit==='button'){assert.equal(counts(id),0);assert.ok(result.followups.some(item=>item.stopped));await approval(await call('click',await target('Submit')),id);}
      else await approval(result,id);
    }
  });
  await check('GROUP 2 script activations never replay',async()=>{
    for(const wrapped of ['click','cancelable','noncancelable'])for(const route of ['click','key','fill','select','check']){
      const id='activation-'+wrapped+'-'+route;await setup({id,mode:'activation',wrapped,route});
      const result=route==='click'?await call('click',await target('Continue')):route==='key'?await call('press',{...await target('Continue'),key:'x'}):route==='fill'?await call('fill',{...await target('Trigger text'),text:'Changed'}):route==='select'?await call('select',{...await target('Trigger choice'),value:'b'}):await call('check',{...await target('Trigger check'),checked:true});
      assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);assert.ok(result.followups.some(item=>item.stopped));
      const direct=await call('click',await target('Delete'));await approval(direct,id);
      assert.equal(counts('handler-'+id),1);
    }
  });
  await check('GROUP 2 loop with uncancelled enclosing submit sends once',async()=>{
    await nav('loop&id=uncancelled-loop');const result=await call('click',await target('Continue'));await approval(result,'uncancelled-loop');
  });
  await check('GROUP 2 delayed submission stays held after slow frame arming',async()=>{
    await nav('owner-input');await lifecycle({fixture:'arm_delay',milliseconds:650});
    const result=await call('click',await target('Continue'));await approval(result,'scheduled-input');
  });
  await check('GROUP 2 nested validation and fresh-frame fallback',async()=>{
    for(const mode of ['implicit','null-original']){
      const id='submitter-hijack-'+mode;await nav('submitter-hijack&id='+id+'&mode='+mode);
      const prepared=mode==='implicit'?await call('press',{...await target('Form field'),key:'Enter'}):await call('click',await target('Continue'));
      assert.equal(counts(id),0);const first=prepared.approval||prepared.followups.find(item=>item.approval).approval;await call('submit',first);
      assert.equal(counts(id),0,'a different successful submitter needs its own approval');
      const held=await reservedFor(id,first.operation_id);
      assert.ok(held,'the additional submission is prepared separately');await approval({approval:held},id);
      assert.match(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).body,/which=other/);
    }
    for(const mode of ['invalid','valid','double','other','nested']){
      const id='resume-'+mode;await nav('resume-matrix&id='+id+'&mode='+mode);
      const first=await call('click',await target('Continue'));assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);
      await approval(first,id);assert.equal(counts('handler-'+id),mode==='invalid'?0:mode==='nested'?2:1);
      assert.equal(counts('other-'+id),0);
      if(mode==='double'||mode==='other'||mode==='nested'){
        const original=first.approval||first.followups.find(item=>item.approval)?.approval;
        assert.ok(await reservedFor(id,original.operation_id),'the additional submission has its own reserved operation for this exact fixture');
      }
    }
    for(const cancel of [true,false]){
      tab=await nativeDonor(tab);
      const id='fresh-'+cancel;await nav('fresh-activation&id='+id+'&cancel='+cancel);
      const result=await call('click',await target('Continue'));assert.equal(counts('handler-'+id),0);
      const held=result.followups.find(item=>cancel?item.stopped:item.unknown);assert.ok(held,JSON.stringify(result));
      assert.ok(!held.approval,'fallback activations are never resumable');
      if(cancel)assert.equal(counts(id),0);else assert.equal((await call('operation_status',{operation_id:result.operation_id})).operation.state,'unknown');
      await closeNativeDonor();
    }
  });
  await check('GROUP 2 owner synchronous task delayed work and in-flight interleavings',async()=>{
    for(const [id,busy,after] of [['owner-sync',0,130],['owner-replay',0,130],['owner-flight',250,60],['owner-after-limit',0,650]]){
      await nav('owner-task&id='+id+'&busy='+busy+'&delay=100'+(id==='owner-replay'?'&replay=1':''));
      const continued=call('click',await target('Continue'));
      let record;const deadline=Date.now()+5000;
      while(!record&&Date.now()<deadline){record=fixture.arrivals.find(row=>row.url.includes('case=task-start')&&row.body===id);if(!record)await delay(5);}
      assert.ok(record);await delay(Math.max(0,record.time+after-Date.now()));ownerKey();const result=await continued;await delay(150);
      if(id==='owner-replay'){assert.equal(counts(id),1,'untrusted replay cannot inherit the first owner task');const held=result.followups.find(item=>item.approval);assert.ok(held);await call('submit',held.approval);await eventually(()=>counts(id)===2,'approved replay submission');await call('submit',held.approval);assert.equal(counts(id),2);}
      if(id==='owner-sync')assert.equal(counts(id),1,'synchronous owner submission passes; delayed second submission stays held');
      if(id==='owner-flight')assert.equal(counts(id),0,'owner input during the marked dispatch stays held');
      if(id==='owner-after-limit')assert.equal(counts(id),2,'owner work after the limit is ordinary browser work');
    }
  });
  await check('GROUP 2 owner defaults never exempt timer forms submitters or validation repairs',async()=>{
    for(const variant of ['same-submitter','other-form','other-submitter']){
      const id='owner-timer-'+variant;await nav('owner-timer&id='+id+'&variant='+variant);
      const continued=call('click',await target('Continue'));
      let record;const deadline=Date.now()+5000;while(!record&&Date.now()<deadline){record=fixture.arrivals.find(row=>row.url.includes('case=task-start')&&row.body===id);if(!record)await delay(5);}assert.ok(record);
      await delay(Math.max(0,record.time+130-Date.now()));ownerKey();
      await approval(await continued,id);
    }
  });
  await check('GROUP 2 unknown activation survives navigation of its source document',async()=>{
    tab=await nativeDonor(tab);
    const id='fresh-self';await nav('fresh-activation&id='+id+'&cancel=false&target=self');
    const result=await call('click',await target('Continue'));
    assert.equal(counts('handler-'+id),0);assert.ok(counts(id)<=1);
    assert.ok(result.untrusted_content.steps.some(step=>step.kind==='activation_unknown'));
    assert.equal((await call('operation_status',{operation_id:result.operation_id})).operation.state,'unknown');
    assert.ok(!result.followups.some(item=>item.stopped||item.approval),'the old activation is never reported stopped or resumable');
    await closeNativeDonor();
  });
  await check('GROUP 3 binding every form fact and generic sibling draft',async()=>{
    for(const change of ['label','element','visible','hidden','action','method','encoding','target','document']){
      const id='binding-'+change;await nav('binding&id='+id);const prepared=await call('click',await target('Submit'));assert.ok(prepared.approval);
      await fixture.mutate(id,change);await delay(100);
      const result=await rpc('submit',prepared.approval);assert.ok(!result.ok||result.data.operation.state==='failed',JSON.stringify(result));assert.equal(counts(id),0);
    }
    await nav('binding&id=before-input-change');const waiting=await call('click',await target('Submit'));await lifecycle({fixture:'arm_delay',milliseconds:650});const pending=rpc('submit',waiting.approval);await eventually(()=>fs.existsSync('/out/arm-ready.json'),'private arming barrier');await fixture.mutate('before-input-change','hidden');const refused=await pending;assert.ok(!refused.ok||refused.data.operation.state==='failed');assert.equal(counts('before-input-change'),0);
    await nav('binding&mode=sibling&id=sibling');const prepared=await call('click',await target('Send'));
    assert.match(JSON.stringify(prepared.approval),/Existing sibling draft/);await fixture.mutate('sibling','text');await delay(100);
    const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('sibling'),0);
  });
  await check('GROUP 4 page confirmations bind their full text and ask independently',async()=>{
    for(const text of ['Delete this synthetic item?','Submit this synthetic request?']){
      const id='dialog-'+text.split(' ')[0];await nav('page-dialog&id='+id+'&text='+encodeURIComponent(text));
      const prepared=await call('click',await target('OK'));assert.ok(prepared.approval);assert.match(prepared.approval.question,new RegExp(text.slice(0,-1)));
      await approval(prepared,id);
    }
    await nav('page-dialog&id=dialog-change');const prepared=await call('click',await target('OK'));
    await fixture.mutate('dialog-change','dialog');await delay(100);const result=await rpc('submit',prepared.approval);
    assert.ok(!result.ok||result.data.operation.state==='failed');assert.equal(counts('dialog-change'),0);
  });
  await check('GROUP 3 cross-frame adapter empty and oversized drafts',async()=>{
    for(const mode of ['empty','oversized']){const id='draft-'+mode;await nav('cross-draft&id='+id+'&mode='+mode);assert.equal((await rpc('click',await target('Send'))).ok,false);assert.equal(counts(id),0);}
    await nav('cross-draft&id=frame-draft&mode=frame');const prepared=await call('click',await target('Send'));
    assert.match(JSON.stringify(prepared.approval),/Existing cross-frame draft/);await fixture.mutate('frame-draft','text');await delay(100);
    const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('frame-draft'),0);
    for(const [site,change,label] of [['gmail','account','Send'],['gmail','recipient','Send'],['whatsapp','chat','Send']]){
      const id='adapter-bind-'+site+'-'+change;await nav('site&id='+id,site);const prepared=await call('click',await target(label));
      await fixture.mutate(id,change);await delay(100);const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts(id+'-'+label),0);
    }
  });
  await check('GROUP 4 exact native confirmation and mismatch matrix',async()=>{
    await nav('site&id=exact-confirm','github');const exact=await call('click',await target('Delete branch'));assert.match(exact.approval.question,/Delete branch fixture-repository/);
    await approval(exact,'exact-confirm-Delete branch');assert.ok((await call('operation_status',{operation_id:exact.approval.operation_id})).operation.stages.confirmation);
    for(const mismatch of ['text','prompt','frame','site','twice']){
      const id='confirm-'+mismatch;await nav('site&id='+id+'&confirm='+mismatch,'github');const prepared=await call('click',await target('Delete branch'));
      // Keep a current preparation live so response decoration must check it
      // while the mismatch leaves the renderer blocked on a native dialog.
      const retained=await call('click',await target('Delete branch'));assert.ok(retained.approval);
      await call('submit',prepared.approval);assert.equal(counts(id+'-Delete branch'),0);
      const {dialog}=await call('read',{tab});assert.ok(dialog);const next=await call('dialog',{tab,expected:dialog,accept:true,...(mismatch==='prompt'?{text:'yes'}:{})});
      await approval(next,id+'-Delete branch');
      assert.equal((await call('operation_status',{operation_id:retained.approval.operation_id})).operation.state,'reserved');
      await call('drop',{operation_id:retained.approval.operation_id});assert.equal(counts(id+'-Delete branch'),1);
    }
    for(const [id,text,asks] of [['new-confirm','Delete this item?',true],['free-confirm','Continue?',false]]){
      await nav('native-confirm&id='+id+'&text='+encodeURIComponent(text));const continued=await call('click',await target('Continue'));assert.ok(!continued.approval);assert.equal(counts(id),0);
      const {dialog}=await call('read',{tab});assert.ok(dialog);const answer=await call('dialog',{tab,expected:dialog,accept:true});
      if(asks)await approval(answer,id);else {assert.ok(!answer.approval);await eventually(()=>counts(id)===1,'free native confirmation');}
    }
  });
  await check('GROUP 4 a native-dialog handler submission is prepared separately',async()=>{
    const id='native-dialog-form';await nav('native-confirm&id='+id+'&mode=form&text='+encodeURIComponent('Submit this item?'));
    const continued=await call('click',await target('Continue'));assert.equal(counts(id),0);
    assert.equal((await call('operation_status',{operation_id:continued.operation_id})).operation.state,'unknown');
    const {dialog}=await call('read',{tab});const answer=await call('dialog',{tab,expected:dialog,accept:true});assert.ok(answer.approval);
    await call('submit',answer.approval);assert.equal(counts(id),0,'answering the dialog cannot approve an unnamed form submission');
    const form=await reservedFor(id,answer.approval.operation_id);assert.ok(form);await approval({approval:form},id);
    assert.match(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).body,/hidden=Bound\+after\+dialog/);
  });
  await check('GROUP 5 question fields, hidden values, password label, upload path and hash',async()=>{
    await nav('binding&id=question');const prepared=await call('click',await target('Submit'));const text=JSON.stringify(prepared.approval);
    assert.match(text,/Hidden original/);assert.match(text,/Private sign-in/);assert.doesNotMatch(text,/SENTINEL_PRIVATE_PASSWORD_20/);assert.match(prepared.approval.question,/hidden/);
    await nav('upload&id=upload-bytes');await call('fill',{...await target('Message'),text:'Draft Claude typed before the unrelated upload'});fs.mkdirSync('/home/owner/Downloads',{recursive:true});fs.writeFileSync('/home/owner/Downloads/fixture.txt','Exact synthetic upload bytes');
    const upload=caller('upload',{...await target('Upload'),path:'/home/owner/Downloads/fixture.txt'});assert.ok(upload.ok,JSON.stringify(upload));
    assert.match(upload.data.approval.question,/sha256/);assert.match(upload.data.approval.question,/fixture.txt/);await approval(upload.data,'upload-bytes');
    assert.equal(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='upload-bytes').body,'Exact synthetic upload bytes');
    const send=await call('click',await target('Send'));await fixture.mutate('upload-bytes','text');await delay(100);const changed=await rpc('submit',send.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('after-upload'),0);
  });
  await check('GROUP 6 exclusions through frame, popup, redirect, taking and history',async()=>{
    await nav('frame-excluded');assert.doesNotMatch(JSON.stringify(await read()),/EXCLUDED_PAGE_SENTINEL_20/);
    await nav('popup-excluded');await call('click',await target('Continue'));await delay(250);
    const tabs=await call('tabs');for(const item of tabs.items.filter(item=>item.url?.includes('approval.test'))){const result=await rpc('take_tab',{tab:item.tab});assert.equal(result.ok,false);}
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    await call('navigate',{tab,url:'http://fixture.test:8765/?case=redirect'});await delay(400);const redirected=await rpc('read',{tab});assert.equal(redirected.ok,false);
    await ownerNavigate('http://approval.test:8765/?case=excluded');assert.equal((await rpc('take_tab',{tab})).ok,false);
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    const back=await rpc('navigate',{tab,direction:'back'});assert.equal(back.ok,false);assert.doesNotMatch(JSON.stringify(await read()),/EXCLUDED_PAGE_SENTINEL_20/);
  });
  await check('GROUP 7 all password kinds across open closed and cross-site roots',async()=>{
    await nav('password-matrix');assert.doesNotMatch(JSON.stringify(await read()),/SENTINEL_PRIVATE_PASSWORD_20/);
    await call('click',await target('Show'));assert.doesNotMatch(JSON.stringify(await read()),/SENTINEL_PRIVATE_PASSWORD_20/);
    for(const file of ['browser-boundary.jsonl','tool.jsonl','service.txt'])assert.doesNotMatch(fs.readFileSync('/out/'+file,'utf8'),/SENTINEL_PRIVATE_PASSWORD_20/,file);
  });
  await check('GROUP 6 schemes links and forward routes',async()=>{
    await nav('features&id=repeat-reload');let previous=(await target('First')).reference.document;
    for(let index=0;index<2;index++){await call('navigate',{tab,direction:'reload'});await eventually(async()=>{const fresh=(await target('First')).reference.document;if(fresh===previous)return false;previous=fresh;return true;},'fresh guarded GET reload');}
    for(const method of ['get','post'])for(const override of [false,true]){
      const id='excluded-form-'+method+'-'+override;
      await nav('excluded-form&id='+id+'&method='+method+'&override='+override);
      assert.equal((await rpc('click',await target('Continue'))).ok,false,'known excluded form destination refuses before any native input');
      assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0,'the submit button handler must never run');
    }
    for(const url of ['file:///fixture','ftp://fixture.test/','chrome://settings','chrome-extension://fixture/','data:text/plain,fixture','blob:http://fixture.test/id','filesystem:http://fixture.test/temporary/id','view-source:http://fixture.test/','devtools://fixture/','intent://fixture/','tel:0000','javascript:void(0)','about:config','mailto:fixture@example.invalid']){
      assert.equal((await rpc('open',{url})).ok,false);assert.equal((await rpc('navigate',{tab,url})).ok,false);
      if(!url.startsWith('javascript:')){await nav('action-matrix&mode=badlink&id=badlink&url='+encodeURIComponent(url));assert.equal((await rpc('click',await target('Read more'))).ok,false);assert.equal(counts('badlink'),0);}
    }
    await nav('action-matrix&mode=badlink&id=excluded-link&url='+encodeURIComponent('http://approval.test:8765/?case=excluded'));assert.equal((await rpc('click',await target('Read more'))).ok,false);assert.equal(counts('excluded-link'),0);
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    await ownerNavigate('http://approval.test:8765/?case=excluded');await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    await ownerHistory('back');await ownerHistory('back');await call('take_tab',{tab});
    assert.equal((await rpc('navigate',{tab,direction:'forward'})).ok,false);
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
  });
  await check('GROUP 8 drop release close and stale references never dispatch prepared work',async()=>{
    for(const action of ['drop','release_tab']){
      await nav('compose');const prepared=await call('click',await target('Send'));const before=counts('compose');
      await call(action,action==='drop'?{operation_id:prepared.approval.operation_id}:{tab});
      const result=await rpc('submit',prepared.approval);assert.ok(!result.ok||result.data.operation.state==='failed');assert.equal(counts('compose'),before);
      if(action==='release_tab')await call('take_tab',{tab});
    }
    const opened=await call('open',{url:'http://fixture.test:8765/?case=compose'});await call('close_tab',{tab:opened.untrusted_content.tab || opened.tab});
  });
  await check('GROUP 13 changed read-only preview is a stated residual',async()=>{
    await nav('binding&mode=sibling&id=preview-residual');const prepared=await call('click',await target('Send'));
    await fixture.mutate('preview-residual','preview');await delay(100);await approval(prepared,'preview-residual');
    assert.ok(fixture.arrivals.some(row=>row.body.includes('Changed read-only preview')));
  });
  await check('GROUP 8 deadline and tabs outside the group',async()=>{
    await nav('binding&id=deadline');const prepared=await call('click',await target('Submit'));await lifecycle({fixture:'expire',operation_id:prepared.approval.operation_id});
    const expired=await rpc('submit',prepared.approval);assert.ok(!expired.ok||expired.data.operation.state==='failed');assert.equal(counts('deadline'),0);
    const outside=await target('Submit');await call('release_tab',{tab});const result=await rpc('click',outside);assert.equal(result.ok,false);assert.equal(counts('deadline'),0);await call('take_tab',{tab});
  });
  const adapters={};
  for(const [site,actions] of Object.entries({gmail:['Send'],whatsapp:['Send'],github:['Comment','Submit review','Merge pull request','Close issue','Delete branch','Delete tag','Delete repository','Save settings'],gemini:['Send','Delete chat','Share chat'],deezer:['Play','Pause','Skip','Seek','Volume','Queue','Like','Follow','Add to playlist','Remove from playlist','Delete playlist','Share track','Subscribe']})){
    await check('GROUP 10 adapter '+site,async()=>{
      for(const label of actions){
        const id='site-'+site+'-'+label;await nav('site&id='+encodeURIComponent(id),site);
        const result=await call('click',await target(label));
        const free=site==='deezer' && ['Play','Pause','Skip','Seek','Volume','Queue','Like','Follow','Add to playlist'].includes(label);
        if(free){assert.ok(!result.approval);await eventually(()=>counts(id+'-'+label)===1,'free '+label);}
        else {await approval(result,id+'-'+label);if(label==='Delete branch')assert.ok((await call('operation_status',{operation_id:result.approval.operation_id})).operation.stages.confirmation);}
      }
      adapters[site]=true;
    });
  }
  await check('GROUP 10 read-only bank',async()=>{
    admin('chrome_sites',{command:'readonly',site:'http://bank.test:8765/',enabled:true});await nav('site&id=bank','bank');
    for(const [verb,label,extra] of [['fill','Amount',{text:'1'}],['click','Continue',{}],['upload','File',{path:'/fixture.txt'}]]){
      const result=await rpc(verb,{...await target(label),...extra});
      assert.equal(result.ok,false,JSON.stringify(result));assert.equal(result.error.code,'readonly_site');
    }
    adapters.bank=true;
  });
  await check('GROUP 10 adapter shortcuts and account-specific questions',async()=>{
    for(const [site,field,key] of [['gmail','Message Body','Ctrl+Enter'],['gmail','Message Body','Cmd+Enter'],['gmail','Message Body','#'],['whatsapp','Type a message','Enter'],['gemini','Enter a prompt here','Enter']]){
      const id='shortcut-'+site+'-'+key;await nav('site&id='+encodeURIComponent(id),site);
      const prepared=await call('press',{...await target(field),key});assert.ok(prepared.approval);assert.match(JSON.stringify(prepared.approval),/Synthetic/);
      if(site==='gmail'&&key!=='#'){assert.match(JSON.stringify(prepared.approval),/hidden@example.invalid/);assert.match(JSON.stringify(prepared.approval),/recipient@example.invalid/);}
      await approval(prepared,id+'-'+(key==='#'?'Delete shortcut':'Enter'));
    }
  });
  await check('GROUP 11 exact owner kind, recipients, account and revocation',async()=>{
    await nav('site&id=trust-initial','gmail');const first=await call('click',await target('Send'));await approval(first,'trust-initial-Send');
    trustOperation=first.approval.operation_id;
    const entry=admin('chrome_sites',{command:'allow',operation_id:trustOperation});
    for(const change of ['account','recipient']){
      const id='adapter-bind-trust-'+change;await nav('site&id='+id,'gmail');await fixture.mutate(id,change);await delay(100);
      const prepared=await call('click',await target('Send'));assert.equal((await rpc('submit_trusted',prepared.approval)).ok,false);assert.equal(counts(id+'-Send'),0);await call('drop',{operation_id:prepared.approval.operation_id});
    }
    await lifecycle({fixture:'kind',mode:'widen'});await nav('site&id=trust-widened','gmail');const widened=await call('click',await target('Send'));assert.equal((await rpc('submit_trusted',widened.approval)).ok,false);assert.equal(counts('trust-widened-Send'),0);await call('drop',{operation_id:widened.approval.operation_id});await lifecycle({fixture:'kind',mode:'restore'});
    await nav('site&id=trust-next','gmail');const next=await call('click',await target('Send'));await call('submit_trusted',next.approval);
    await eventually(()=>counts('trust-next-Send')===1,'trusted receiver');
    admin('chrome_sites',{command:'revoke',id:entry.id});
    await nav('site&id=trust-revoked','gmail');const revoked=await call('click',await target('Send'));
    assert.ok(revoked.approval);assert.equal(counts('trust-revoked-Send'),0);
  });
  await check('QUALIFICATION conservative activations ask and core failures gate before reads',async()=>{
    admin('chrome_sites',{command:'allow',operation_id:trustOperation});
    await lifecycle({fixture:'qualification',mode:'conservative'});
    const notice=reply=>assert.match(reply.pending?.chrome_version_notice,/not qualified/,'every conservative result carries its notice');
    notice(await rpc('read',{tab}));notice(await rpc('read',{tab:-1}));
    for(const [index,[verb,label,args]]of [['click','Continue',{}],['select','Choice',{value:'b'}],['check','Tick',{checked:true}],['click','Read more',{}],['press','Continue',{key:'Enter'}],['press','Continue',{key:'Space'}],['click','Search now',{}]].entries()){
      const id='conservative-'+index;await nav('action-matrix&mode=conservative&id='+id);const view=await call('read',{tab});assert.match(view.version_notice,/not qualified/);
      const reply=await rpc(verb,{...await target(label),...args});notice(reply);assert.equal(reply.ok,true);await approval(reply.data,id);console.log('CONSERVATIVE RECEIVER',id,'0 before, 1 after, 1 after repeat');
    }
    const typing=await call('fill',{...await target('Text'),text:'Plain text\nwith line breaks'});assert.ok(!typing.approval);assert.equal(counts('unexpected-enter'),0);
    assert.ok(!(await call('scroll',{...await target('Text'),x:0,y:40})).approval,'scroll stays free');
    for(const submit of ['native','event']){
      const id='conservative-resume-'+submit;await setup({id,mode:'stopped',submit,route:'fill'});
      const result=await call('fill',{...await target('Trigger text'),text:'Free typing starts held submission'});
      await approval(result,id);console.log('CONSERVATIVE RECEIVER',id,'0 before, 1 after, 1 after repeat');
    }
    await nav('action-matrix&mode=submit&id=conservative-form&tag=submit');await approval(await call('click',await target('Continue')),'conservative-form');
    await setup({id:'conservative-script',mode:'conservative-script',route:'fill'});const scripted=await call('fill',{...await target('Trigger text'),text:'Free typing'});assert.equal(counts('conservative-script'),0);assert.equal(counts('handler-conservative-script'),0);assert.ok(scripted.followups.some(item=>item.stopped));await approval(await call('click',await target('Read more')),'conservative-script');assert.equal(counts('handler-conservative-script'),1);
    await nav('site&id=conservative-bank','bank');
    for(const [verb,label,args]of [['fill','Amount',{text:'1'}],['click','Continue',{}],['upload','File',{path:'/fixture.txt'}]]){const reply=await rpc(verb,{...await target(label),...args});notice(reply);assert.equal(reply.error.code,'readonly_site');}
    await nav('site&id=conservative-gmail','gmail');const generic=await call('click',await target('Send'));assert.equal(generic.approval.description.untrusted_content.page_state.adapter,null);assert.equal((await rpc('submit_trusted',generic.approval)).ok,false);assert.equal(counts('conservative-gmail-Send'),0);
    await approval(generic,'conservative-gmail-Send');
    await nav('password-matrix');assert.doesNotMatch(JSON.stringify(await read()),/SENTINEL_PRIVATE_PASSWORD_20/);
    const show=await call('click',await target('Show'));assert.ok(show.approval);await call('submit',show.approval);assert.doesNotMatch(JSON.stringify(await read()),/SENTINEL_PRIVATE_PASSWORD_20/);
    for(const file of ['browser-boundary.jsonl','tool.jsonl','service.txt'])assert.doesNotMatch(fs.readFileSync('/out/'+file,'utf8'),/SENTINEL_PRIVATE_PASSWORD_20/,file);
    await lifecycle({fixture:'qualification',mode:'password_exclusion'});
    assert.equal((await rpc('read',{tab})).ok,false);
    await lifecycle({fixture:'qualification',mode:'qualified'});
  });
  await check('GROUP 13 autosave and after-limit submissions are not held',async()=>{
    await nav('residual');await call('fill',{...await target('Autosave'),text:'Synthetic autosave'});
    await eventually(()=>counts('residual-autosave')>=1,'autosave residual');
    await setup({id:'residual-late',mode:'residual-delay'});const result=await call('click',await target('Continue'));
    assert.equal(result.followups.length,0);await eventually(()=>counts('residual-late')===1,'after-limit residual');
  });
  await check('VIEW representative long article/form complete paging',async()=>{
    await setup({id:'long',mode:'long'});let cursor,tree='',pages=0;const started=Date.now();
    do{const page=await call('read',{tab,...(cursor?{cursor}:{})});assert.ok(page.untrusted_content.tree.length<=16000);tree+=page.untrusted_content.tree;cursor=page.cursor;pages++;}while(cursor);
    assert.match(tree,/Paragraph 119/);assert.match(tree,/Field 79/);
    const measurement={characters:tree.length,utf8_bytes:Buffer.byteLength(tree),pages,milliseconds:Date.now()-started,token_estimate:Math.ceil(tree.length/4)};
    fs.writeFileSync('/out/view-measurements.json',JSON.stringify(measurement,null,2));console.log('VIEW MEASURED',JSON.stringify(measurement));
  });
  await check('FEATURE tools forms options find wait fill_form scroll and full catalogues',async()=>{
    await nav('features&id=tools');const first=await target('First');const form=await call('read_form',{tab,reference:first.reference});
    assert.match(JSON.stringify(form),/Hidden field/);assert.match(JSON.stringify(form),/Disabled option/);assert.match(JSON.stringify(form),/Second option/);
    for(const value of ['missing','c'])assert.equal((await rpc('select',{...await target('Choice'),value})).ok,false);
    const found=await call('find',{tab,text:'Findable synthetic paragraph'});assert.match(found.untrusted_content.tree,/Findable synthetic paragraph/);
    assert.equal((await call('wait',{tab,text:'Findable synthetic paragraph',timeout_ms:500})).condition_met,true);
    assert.equal((await call('wait',{tab,text:'Never present sentinel',timeout_ms:50})).condition_met,false);
    const filled=await call('fill_form',{fields:[{...await target('First'),text:'Changed first'},{...await target('Second'),text:'Changed second'}]});assert.equal(filled.remaining,0);
    assert.match(JSON.stringify(await read()),/Changed first/);assert.match(JSON.stringify(await read()),/Changed second/);
    await call('scroll',{...await target('First'),x:0,y:80});
    for(let index=0;index<12;index++){
      await nav('features&id=catalogue-'+index);ownerBookmark();await delay(100);
      const download=await call('click',await target('Download fixture'));assert.ok(!download.approval);
    }
    for(const verb of ['downloads','history','bookmarks']){
      let cursor,items=[];
      do{const page=await call(verb,{text:verb==='downloads'?'synthetic-':'fixture.test',limit:2,...(cursor?{cursor}:{})});assert.ok(page.items.length<=2);items.push(...page.items);cursor=page.cursor;}while(cursor);
      assert.ok(items.length>=12,verb+' complete catalogue: '+items.length);
      if(verb==='downloads')assert.ok(items.every(item=>item.filename?.includes('synthetic-')));
    }
  });
  await check('GROUP 8 actual popup Stop button drops all prepared work',async()=>{
    await nav('compose');const prepared=await call('click',await target('Send'));const before=counts('compose');
    await lifecycle({fixture:'popup'});await delay(150);stopClick();await delay(200);
    const result=await rpc('submit',prepared.approval);assert.ok(!result.ok||result.data.operation.state==='failed');assert.equal(counts('compose'),before);
    assert.equal((await call('tabs')).items.find(item=>item.tab===tab).controlled,false);
    await call('take_tab',{tab});
  });
  await check('GROUP 9 Chrome host service crash cutpoints never replay',async()=>{
    for(const component of ['chrome','host','service'])for(const phase of ['before-check','after-submitting','after-input']){
      const id='crash-'+component+'-'+phase;await nav('binding&id='+id);const prepared=await call('click',await target('Submit'));assert.ok(prepared.approval);
      let pending;
      if(phase==='after-submitting'){
        await lifecycle({fixture:'cut',point:'submitting'});pending=rpc('submit',prepared.approval).catch(error=>({transport:String(error)}));
        await eventually(()=>fs.existsSync('/out/checkpoint-ready.json'),'durable submitting barrier');
      } else if(phase==='after-input'){
        await lifecycle({fixture:'cut',point:'after-input'});
        pending=rpc('submit',prepared.approval).catch(error=>({transport:String(error)}));
        await eventually(()=>fs.existsSync('/out/checkpoint-ready.json'),'private post-input pre-reply barrier');
        assert.equal(counts(id),1,'receiver saw the input before its result was returned');
      }
      await lifecycle(component==='service'?{fixture:'kill_service'}:'kill_'+component);
      if(phase==='after-submitting'&&component!=='service')fs.writeFileSync('/out/checkpoint-release','release');
      if(component==='service')await lifecycle({fixture:'start_service'});else if(component==='chrome')await lifecycle('start_chrome');
      if(pending)await pending;
      tab=await restoreControl();const before=counts(id);
      assert.equal(before,phase==='after-input'?1:0,'receiver cutpoint '+id);
      const replay=await rpc('submit',prepared.approval);
      if(phase!=='before-check'){assert.equal(replay.ok,true,JSON.stringify(replay));assert.equal(replay.data.operation.state,'unknown','an interrupted outcome must stay unknown');}
      else assert.ok(!replay.ok||replay.data.operation.state!=='reserved');
      await delay(100);assert.equal(counts(id),before,'restart must never replay '+id);
      console.log('GROUP 9 CUT',id,'receiver',before,JSON.stringify(replay));
    }
  });
  await check('GROUP 7 no listening port after tool suite',async()=>isolationAfter());
  const qualified=verdicts(results,baseline,adapters);
  fs.writeFileSync('/out/qualification-result.json',JSON.stringify(qualified,null,2));
  fs.writeFileSync('/out/matrices.json',JSON.stringify(results,null,2));
  return results.filter(item=>!item.passed);
}
