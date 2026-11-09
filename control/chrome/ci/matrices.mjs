// Synthetic browser cases, imported only by the Linux-container entry point.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';

export async function matrices({call,read,nav,target,counts,eventually,tab,fixture,admin,rpc,caller,ownerNavigate,ownerKey,lifecycle,restoreControl,stopClick,baseline}) {
  const results=[];
  async function check(name,fn) {
    try {await fn();results.push({name,passed:true});console.log(name,'PASS');}
    catch(error){results.push({name,passed:false,error:String(error.stack)});console.error(name,'FAIL',error.stack);
      // Preserve the failed assertion, then start a fresh browser for the next independent group.
      // Never retry this case or turn its result into a pass.
      if(!name.startsWith('GROUP 9'))try{await lifecycle('kill_chrome');await lifecycle('start_chrome');tab=await restoreControl();}catch(recovery){console.error('FIXTURE RECOVERY FAILED',String(recovery));}
    }
  }
  async function approval(result,id) {
    const prepared=result.approval ? result:result.followups?.find(item=>item.approval);
    assert.ok(prepared?.approval,JSON.stringify(result));assert.equal(counts(id),0,'zero arrivals before approval');
    await call('submit',prepared.approval);await eventually(()=>counts(id)===1,'one receiver arrival '+id);
    await call('submit',prepared.approval);await delay(30);assert.equal(counts(id),1,'a second attempt sends nothing');
  }
  async function setup(parameters) {await nav('matrix&'+new URLSearchParams(parameters));}
  const words=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]).words;
  await check('GROUP 1 submit compose deletion and free-input matrix',async()=>{
    for(const tag of ['default','submit'])for(const key of ['click','Enter','Space','field']){
      const id='submit-'+tag+'-'+key;await nav('action-matrix&mode=submit&id='+id+'&tag='+tag);
      const result=key==='click'?await call('click',await target('Continue')):await call('press',{...await target(key==='field'?'Form field':'Continue'),key:key==='field'?'Enter':key});await approval(result,id);
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
    for(const word of words)for(const label of ['name','aria','title','value','labelledby','hidden_labelledby','label','role','formaction'])for(const route of ['click','Enter','Space']){
      const id='word-'+word+'-'+label+'-'+route;await setup({id,mode:'word',word,label});
      const row=(await read()).find(row=>row.expected.role==='button'||row.expected.name==='Continue');assert.ok(row);
      const args={reference:row.reference,expected:row.expected};
      const result=route==='click'?await call('click',args):await call('press',{...args,key:route});
      await approval(result,id);
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
      await approval(result,id);
    }
  });
  await check('GROUP 2 script activations never replay',async()=>{
    for(const wrapped of ['click','cancelable','noncancelable']){
      const id='activation-'+wrapped;await setup({id,mode:'activation',wrapped});
      const result=await call('click',await target('Continue'));
      assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);assert.ok(result.followups.some(item=>item.stopped));
      const direct=await call('click',await target('Delete'));await approval(direct,id);
      assert.equal(counts('handler-'+id),1);
    }
  });
  await check('GROUP 2 loop with uncancelled enclosing submit sends once',async()=>{
    await nav('loop&id=uncancelled-loop');const result=await call('click',await target('Continue'));await approval(result,'uncancelled-loop');
  });
  await check('GROUP 2 nested validation and fresh-frame fallback',async()=>{
    for(const mode of ['invalid','valid','double','other','nested']){
      const id='resume-'+mode;await nav('resume-matrix&id='+id+'&mode='+mode);
      const first=await call('click',await target('Continue'));assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);
      await approval(first,id);assert.equal(counts('handler-'+id),mode==='invalid'?0:mode==='nested'?2:1);
      assert.equal(counts('other-'+id),0);
      if(mode==='double'||mode==='other'||mode==='nested'){
        const notices=await call('notices');assert.ok(notices.total>0,'additional submission has its own pending check');
      }
    }
    for(const cancel of [true,false]){
      const id='fresh-'+cancel;await nav('fresh-activation&id='+id+'&cancel='+cancel);
      const result=await call('click',await target('Continue'));assert.equal(counts('handler-'+id),0);
      const held=result.followups.find(item=>cancel?item.stopped:item.unknown);assert.ok(held,JSON.stringify(result));
      assert.ok(!held.approval,'fallback activations are never resumable');
      if(cancel)assert.equal(counts(id),0);else assert.equal(result.operation.state,'unknown');
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
  await check('GROUP 3 binding every form fact and generic sibling draft',async()=>{
    for(const change of ['label','element','visible','hidden','action','method','encoding','target','document']){
      const id='binding-'+change;await nav('binding&id='+id);const prepared=await call('click',await target('Submit'));assert.ok(prepared.approval);
      fixture.mutate(id,change);await delay(100);
      const result=await rpc('submit',prepared.approval);assert.ok(!result.ok||result.data.operation.state==='failed',JSON.stringify(result));assert.equal(counts(id),0);
    }
    await nav('binding&mode=sibling&id=sibling');const prepared=await call('click',await target('Send'));
    assert.match(JSON.stringify(prepared.approval),/Existing sibling draft/);fixture.mutate('sibling','text');await delay(100);
    const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('sibling'),0);
  });
  await check('GROUP 4 page confirmations bind their full text and ask independently',async()=>{
    for(const text of ['Delete this synthetic item?','Submit this synthetic request?']){
      const id='dialog-'+text.split(' ')[0];await nav('page-dialog&id='+id+'&text='+encodeURIComponent(text));
      const prepared=await call('click',await target('OK'));assert.ok(prepared.approval);assert.match(prepared.approval.question,new RegExp(text.slice(0,-1)));
      await approval(prepared,id);
    }
    await nav('page-dialog&id=dialog-change');const prepared=await call('click',await target('OK'));
    fixture.mutate('dialog-change','dialog');await delay(100);const result=await rpc('submit',prepared.approval);
    assert.ok(!result.ok||result.data.operation.state==='failed');assert.equal(counts('dialog-change'),0);
  });
  await check('GROUP 3 cross-frame adapter empty and oversized drafts',async()=>{
    for(const mode of ['empty','oversized']){const id='draft-'+mode;await nav('cross-draft&id='+id+'&mode='+mode);assert.equal((await rpc('click',await target('Send'))).ok,false);assert.equal(counts(id),0);}
    await nav('cross-draft&id=frame-draft&mode=frame');const prepared=await call('click',await target('Send'));
    assert.match(JSON.stringify(prepared.approval),/Existing cross-frame draft/);fixture.mutate('frame-draft','text');await delay(100);
    const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('frame-draft'),0);
    for(const [site,change,label] of [['gmail','account','Send'],['gmail','recipient','Send'],['whatsapp','chat','Send']]){
      const id='adapter-bind-'+site+'-'+change;await nav('site&id='+id,site);const prepared=await call('click',await target(label));
      fixture.mutate(id,change);await delay(100);const changed=await rpc('submit',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts(id+'-'+label),0);
    }
  });
  await check('GROUP 4 exact native confirmation and mismatch matrix',async()=>{
    await nav('site&id=exact-confirm','github');const exact=await call('click',await target('Delete branch'));assert.match(exact.approval.question,/Delete branch fixture-repository/);
    await approval(exact,'exact-confirm-Delete branch');assert.ok((await call('operation_status',{operation_id:exact.approval.operation_id})).operation.stages.confirmation);
    for(const mismatch of ['text','prompt']){
      const id='confirm-'+mismatch;await nav('site&id='+id+'&confirm='+mismatch,'github');const prepared=await call('click',await target('Delete branch'));
      await call('submit',prepared.approval);assert.equal(counts(id+'-Delete branch'),0);
      const {dialog}=await call('read',{tab});assert.ok(dialog);const next=await call('dialog',{tab,expected:dialog,accept:true,...(mismatch==='prompt'?{text:'yes'}:{})});
      await approval(next,id+'-Delete branch');
    }
    for(const [id,text,asks] of [['new-confirm','Delete this item?',true],['free-confirm','Continue?',false]]){
      await nav('native-confirm&id='+id+'&text='+encodeURIComponent(text));const continued=await call('click',await target('Continue'));assert.ok(!continued.approval);assert.equal(counts(id),0);
      const {dialog}=await call('read',{tab});assert.ok(dialog);const answer=await call('dialog',{tab,expected:dialog,accept:true});
      if(asks)await approval(answer,id);else {assert.ok(!answer.approval);await eventually(()=>counts(id)===1,'free native confirmation');}
    }
  });
  await check('GROUP 5 question fields, hidden values, password label, upload path and hash',async()=>{
    await nav('binding&id=question');const prepared=await call('click',await target('Submit'));const text=JSON.stringify(prepared.approval);
    assert.match(text,/Hidden original/);assert.match(text,/Private sign-in/);assert.doesNotMatch(text,/SENTINEL_PRIVATE_PASSWORD_20/);assert.match(prepared.approval.question,/hidden/);
    await nav('upload&id=upload-bytes');fs.mkdirSync('/home/owner/Downloads',{recursive:true});fs.writeFileSync('/home/owner/Downloads/fixture.txt','Exact synthetic upload bytes');
    const upload=caller('upload',{...await target('Upload'),path:'/home/owner/Downloads/fixture.txt'});assert.ok(upload.ok,JSON.stringify(upload));
    assert.match(upload.data.approval.question,/sha256/);assert.match(upload.data.approval.question,/fixture.txt/);await approval(upload.data,'upload-bytes');
    assert.equal(fixture.arrivals.find(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='upload-bytes').body,'Exact synthetic upload bytes');
    const send=await call('click',await target('Send'));fixture.mutate('upload-bytes','text');await delay(100);const changed=await rpc('submit',send.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed');assert.equal(counts('after-upload'),0);
  });
  await check('GROUP 6 exclusions through frame, popup, redirect, taking and history',async()=>{
    await nav('frame-excluded');assert.doesNotMatch(JSON.stringify(await read()),/EXCLUDED_PAGE_SENTINEL_20/);
    await nav('popup-excluded');await call('click',await target('Continue'));await delay(250);
    const tabs=await call('tabs');for(const item of tabs.items.filter(item=>item.url?.includes('approval.test'))){const result=await rpc('take_tab',{tab:item.tab});assert.equal(result.ok,false);}
    await nav('redirect');const redirected=await rpc('read',{tab});assert.equal(redirected.ok,false);
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
    for(const url of ['file:///fixture','ftp://fixture.test/','chrome://settings','chrome-extension://fixture/','data:text/plain,fixture','javascript:void(0)','about:config','mailto:fixture@example.invalid']){
      assert.equal((await rpc('open',{url})).ok,false);assert.equal((await rpc('navigate',{tab,url})).ok,false);
    }
    await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    await ownerNavigate('http://approval.test:8765/?case=excluded');await ownerNavigate('http://fixture.test:8765/?case=compose');await call('take_tab',{tab});
    // The excluded entry remains in forward history after the owner steps back twice.
    await call('navigate',{tab,direction:'back'}).catch(()=>{});
    assert.equal((await rpc('read',{tab})).ok,false);
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
    fixture.mutate('preview-residual','preview');await delay(100);await approval(prepared,'preview-residual');
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
  await check('GROUP 11 exact owner kind, recipients, account and revocation',async()=>{
    await nav('site&id=trust-initial','gmail');const first=await call('click',await target('Send'));await approval(first,'trust-initial-Send');
    const entry=admin('chrome_sites',{command:'allow',operation_id:first.approval.operation_id});
    await nav('site&id=trust-next','gmail');const next=await call('click',await target('Send'));await call('submit_trusted',next.approval);
    await eventually(()=>counts('trust-next-Send')===1,'trusted receiver');
    admin('chrome_sites',{command:'revoke',id:entry.id});
    await nav('site&id=trust-revoked','gmail');const revoked=await call('click',await target('Send'));
    assert.ok(revoked.approval);assert.equal(counts('trust-revoked-Send'),0);
  });
  await check('QUALIFICATION conservative activations ask and core failures gate before reads',async()=>{
    await lifecycle({fixture:'qualification',mode:'conservative'});
    await nav('action-matrix&mode=free&id=conservative');const view=await call('read',{tab});assert.match(view.version_notice,/not qualified/);
    for(const [verb,label,args] of [['click','Continue',{}],['select','Choice',{value:'b'}],['check','Tick',{checked:true}]]){
      const prepared=await call(verb,{...await target(label),...args});assert.ok(prepared.approval);assert.equal(counts('conservative'),0);await call('drop',{operation_id:prepared.approval.operation_id});
    }
    const typing=await call('fill',{...await target('Text'),text:'Plain text\nwith line breaks'});assert.ok(!typing.approval);assert.equal(counts('unexpected-enter'),0);
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
  const required={
    1:['GROUP 1 what asks word/label/key matrix','GROUP 1 submit compose deletion and free-input matrix'],
    2:['GROUP 2 stopped page steps handler/resume matrix','GROUP 2 script activations never replay','GROUP 2 loop with uncancelled enclosing submit sends once','GROUP 2 owner synchronous task delayed work and in-flight interleavings','GROUP 2 nested validation and fresh-frame fallback'],
    3:['GROUP 3 binding every form fact and generic sibling draft','GROUP 3 cross-frame adapter empty and oversized drafts'],
    4:['GROUP 4 page confirmations bind their full text and ask independently','GROUP 4 exact native confirmation and mismatch matrix'],
    5:['GROUP 5 question fields, hidden values, password label, upload path and hash'],
    6:['GROUP 6 exclusions through frame, popup, redirect, taking and history','GROUP 6 schemes links and forward routes'],
    7:['GROUP 7 all password kinds across open closed and cross-site roots'],
    8:['GROUP 8 drop release close and stale references never dispatch prepared work','GROUP 8 actual popup Stop button drops all prepared work','GROUP 8 deadline and tabs outside the group'],
    9:['GROUP 9 Chrome host service crash cutpoints never replay'],
    10:['GROUP 10 adapter gmail','GROUP 10 adapter whatsapp','GROUP 10 adapter github','GROUP 10 adapter gemini','GROUP 10 adapter deezer','GROUP 10 read-only bank'],
    11:['GROUP 11 exact owner kind, recipients, account and revocation'],
    13:['GROUP 13 changed read-only preview is a stated residual','GROUP 13 autosave and after-limit submissions are not held'],
  };
  const groups=Object.fromEntries(Object.entries(required).map(([group,names])=>[group,names.every(name=>results.some(result=>result.name===name&&result.passed))]));
  groups[2] &&= baseline.owner===true;
  groups[7] &&= baseline.forgery===true && baseline.isolation===true;
  groups[13] &&= baseline.residual===true;
  const qualified={groups,core:{classification:groups[1],page_script:groups[2]&&groups[8]&&groups[9],binding:groups[3]&&groups[4]&&groups[5],password_exclusion:groups[7]},adapters:Object.fromEntries(['gmail','whatsapp','github','bank','gemini','deezer'].map(site=>[site,adapters[site]===true]))};
  fs.writeFileSync('/out/qualification-result.json',JSON.stringify(qualified,null,2));
  fs.writeFileSync('/out/matrices.json',JSON.stringify(results,null,2));
  return results.filter(item=>!item.passed);
}
