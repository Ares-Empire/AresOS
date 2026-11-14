// Receiver-backed public-tool tests, called only by the GitHub Linux browser harness.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';

export async function siteMatrices({call,read,nav,target,counts,eventually,tab,fixture,admin,rpc,lifecycle}) {
  if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true'||!fs.existsSync('/.dockerenv'))throw Error('Adapter browser cases run only in GitHub Linux containers');
  const results=[];let serial=0;
  const state=result=>result.approval.description.untrusted_content.page_state;
  const fresh=async(site,extra='',port=8765)=>{const id='adapters-'+site+'-'+(++serial);if(port===8765)await nav('adapter-sites&id='+id+extra,site);else{const url='http://'+site+'.test:'+port+'/?case=adapter-sites&id='+id+extra;await call('navigate',{tab,url,discard_unsaved:true});await eventually(async()=>{const page=await call('read',{tab});return page.untrusted_content.url===url&&page.characters>0;},'alternate fixture origin');await delay(250);}return id;};
  const receiver=(id,label='Send',compose='main')=>id+':'+label+':'+compose;
  const evidence=(id,phase)=>{const row={id,phase,count:counts(id),arrivals:fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id)};fs.appendFileSync('/out/adapters-receiver.jsonl',JSON.stringify(row)+'\n');return row;};
  async function check(name,fn) {
    try{await fn();results.push({name,passed:true});console.log(name,'PASS');}
    catch(error){results.push({name,passed:false,error:String(error.stack)});console.error(name,'FAIL',error.stack);
      // Keep the original failure. Cleanup only unblocks the next independent case.
      try{const page=await call('read',{tab});if(page.untrusted_content.dialog)await rpc('dialog',{tab,expected:page.untrusted_content.dialog,accept:false});}catch{}
      try{await lifecycle({fixture:'qualification',mode:'qualified'});}catch{}
    }
    fs.writeFileSync('/out/adapters.json',JSON.stringify(results,null,2));
  }
  async function approved(result,id,{trusted=false}={}) {
    assert.ok(result.approval,JSON.stringify(result));assert.equal(evidence(id,'before approval').count,0);
    await call(trusted?'submit_trusted':'submit',result.approval);
    await eventually(()=>counts(id)===1,'adapter receiver '+id);assert.equal(evidence(id,'after approval').count,1);
    await call(trusted?'submit_trusted':'submit',result.approval);await delay(50);
    assert.equal(evidence(id,'after repeat').count,1,'a repeated approval must never dispatch');
    console.log('ADAPTER RECEIVER',id,'0 before, 1 after, 1 after repeat');
  }
  async function refusedAfterChange(site,field,label='Send') {
    const id=await fresh(site),key=receiver(id,label,site==='gmail'?'first':'main');
    const prepared=await call('click',await target(label));assert.ok(prepared.approval);
    await fixture.mutate(id,field);const outcome=await rpc('submit',prepared.approval);
    assert.ok(!outcome.ok||outcome.data.operation.state==='failed',JSON.stringify(outcome));
    assert.equal(evidence(key,'changed approval refused').count,0);
    await rpc('submit',prepared.approval);assert.equal(counts(key),0);
    await approved(await call('click',await target(label)),key);
  }
  async function denyTrust(approval,id) {
    assert.equal(evidence(id,'before trusted refusal').count,0);
    assert.ok(approval,'An asking adapter input must prepare before dispatch');
    assert.equal((await rpc('submit_trusted',approval)).ok,false);
    assert.equal(evidence(id,'trusted route refused').count,0);
  }
  await check('GROUP 10 ADAPTER Gmail full compose and every bound field',async()=>{
    const id=await fresh('gmail'),prepared=await call('click',await target('Send')),page=state(prepared).adapter;
    assert.equal(page.account,'Synthetic account');assert.equal(page.to,'one@mail.test,two@mail.test');assert.equal(page.cc,'copy@mail.test');assert.equal(page.bcc,'hidden@mail.test');
    assert.equal(page.subject,'Synthetic subject first');assert.equal(page.text,'Full synthetic message\\u000aSecond line');
    assert.deepEqual(page.attachments,[{label:'Attachment: fixture.txt',text:'fixture.txt 3 bytes'}]);assert.equal(page.preview,'Full quoted preview');
    await approved(prepared,receiver(id,'Send','first'));
    const received=JSON.parse(evidence(receiver(id,'Send','first'),'content').arrivals[0].body);
    assert.equal(received.fields.find(field=>field.name==='bcc').value,page.bcc);assert.equal(received.fields.find(field=>field.name==='Message Body').value,'Full synthetic message\nSecond line');
    assert.deepEqual(received.attachments,page.attachments);assert.equal(received.preview,page.preview);
    for(const field of ['account','to','cc','bcc','subject','text','attachments','preview'])await refusedAfterChange('gmail',field);
  });
  await check('GROUP 10 ADAPTER two Gmail compose windows and inbox shortcut',async()=>{
    let id=await fresh('gmail','&variant=two');
    const first=await call('click',await target('Send'));assert.equal(state(first).adapter.to,'one@mail.test,two@mail.test');
    await fixture.mutate(id,'text:second');await approved(first,receiver(id,'Send','first'));assert.equal(counts(receiver(id,'Send','second')),0);
    const rows=(await read()).filter(row=>row.expected.name==='Send'&&row.expected.role==='button');assert.equal(rows.length,2);
    const second=await call('click',{reference:rows[1].reference,expected:rows[1].expected});assert.equal(state(second).adapter.to,'other@mail.test');assert.equal(state(second).adapter.text,'Changed synthetic text');
    await approved(second,receiver(id,'Send','second'));assert.equal(counts(receiver(id,'Send','first')),1);
    id=await fresh('gmail');const inbox=await call('press',{...await target('Selected message'),key:'#'});assert.equal(evidence(receiver(id,'Delete shortcut'),'inbox before approval').count,0);assert.ok(inbox.approval);
    await denyTrust(inbox.approval,receiver(id,'Delete shortcut'));await approved(inbox,receiver(id,'Delete shortcut'));
    for(const key of ['Ctrl+Enter','Cmd+Enter','#','Shift+#','Ctrl+#','Alt+#','Cmd+#']){
      id=await fresh('gmail');const prepared=await call('press',{...await target('Message Body'),key});
      await approved(prepared,receiver(id,key.endsWith('#')?'Delete shortcut':'Enter','first'));
    }
  });
  await check('GROUP 11 ADAPTER Gmail exact To Cc Bcc roles account revocation and widening',async()=>{
    let id=await fresh('gmail'),prepared=await call('click',await target('Send'));await approved(prepared,receiver(id,'Send','first'));
    const entry=admin('chrome_sites',{command:'allow',operation_id:prepared.approval.operation_id});
    for(const field of ['account','to','cc','bcc','recipient-role']){
      id=await fresh('gmail');await fixture.mutate(id,field);prepared=await call('click',await target('Send'));
      await denyTrust(prepared.approval,receiver(id,'Send','first'));await approved(prepared,receiver(id,'Send','first'));
    }
    id=await fresh('gmail');await fixture.mutate(id,'recipients-order');prepared=await call('click',await target('Send'));await approved(prepared,receiver(id,'Send','first'),{trusted:true});
    id=await fresh('gmail','',8766);prepared=await call('click',await target('Send'));assert.ok(state(prepared).adapter);await denyTrust(prepared.approval,receiver(id,'Send','first'));await approved(prepared,receiver(id,'Send','first'));
    for(const field of ['account','to','cc','bcc','subject','text','attachments','preview']){
      id=await fresh('gmail');prepared=await call('click',await target('Send'));await fixture.mutate(id,field);
      const changed=await rpc('submit_trusted',prepared.approval);assert.ok(!changed.ok||changed.data.operation.state==='failed',JSON.stringify(changed));assert.equal(evidence(receiver(id,'Send','first'),'trusted binding changed').count,0);
      await rpc('submit_trusted',prepared.approval);assert.equal(counts(receiver(id,'Send','first')),0);
      await approved(await call('click',await target('Send')),receiver(id,'Send','first'),{trusted:['subject','text','attachments','preview'].includes(field)});
    }
    await lifecycle({fixture:'kind',mode:'widen'});id=await fresh('gmail');prepared=await call('click',await target('Send'));await denyTrust(prepared.approval,receiver(id,'Send','first'));await call('drop',{operation_id:prepared.approval.operation_id});await lifecycle({fixture:'kind',mode:'restore'});
    admin('chrome_sites',{command:'revoke',id:entry.id});id=await fresh('gmail');prepared=await call('click',await target('Send'));await denyTrust(prepared.approval,receiver(id,'Send','first'));await approved(prepared,receiver(id,'Send','first'));
    id=await fresh('gmail','&variant=quoted');prepared=await call('click',await target('Send'));await approved(prepared,receiver(id,'Send','first'));const quotedEntry=admin('chrome_sites',{command:'allow',operation_id:prepared.approval.operation_id});
    id=await fresh('gmail','&variant=quoted');await fixture.mutate(id,'recipient-collision');prepared=await call('click',await target('Send'));await denyTrust(prepared.approval,receiver(id,'Send','first'));await approved(prepared,receiver(id,'Send','first'));admin('chrome_sites',{command:'revoke',id:quotedEntry.id});
  });
  await check('GROUP 10 ADAPTER WhatsApp every message chat text attachments and free activity',async()=>{
    let id=await fresh('whatsapp');const opened=await call('click',await target('Open chat'));assert.ok(!opened.approval);await eventually(()=>counts(receiver(id,'Open chat'))===1,'free read receipt');
    const filled=await call('fill',{...await target('Type a message'),text:'First typed message\nLine two'});assert.ok(!filled.approval);assert.equal(counts(receiver(id)),0);
    const first=await call('press',{...await target('Type a message'),key:'Enter'});assert.equal(state(first).adapter.chat,'Synthetic chat');assert.equal(state(first).adapter.text,'First typed message\\u000aLine two');assert.equal(state(first).adapter.attachments.length,1);
    await denyTrust(first.approval,receiver(id,'Enter'));await approved(first,receiver(id,'Enter'));
    const received=JSON.parse(evidence(receiver(id,'Enter'),'content').arrivals[0].body);assert.equal(received.fields.find(field=>field.name==='Type a message').value,'First typed message\nLine two');
    assert.equal((await rpc('sites',{command:'allow',operation_id:first.approval.operation_id})).ok,false);
    let ownerRefused=false;try{admin('chrome_sites',{command:'allow',operation_id:first.approval.operation_id});}catch{ownerRefused=true;}assert.ok(ownerRefused,'WhatsApp is never eligible, even through the owner channel');
    // A new document/message has a new approval; the prior one cannot send it.
    id=await fresh('whatsapp');const second=await call('click',await target('Send'));assert.notEqual(second.approval.operation_id,first.approval.operation_id);await denyTrust(second.approval,receiver(id));await approved(second,receiver(id));
    for(const field of ['chat','text','attachments','preview'])await refusedAfterChange('whatsapp',field);
  });
  await check('GROUP 10 ADAPTER GitHub actions and all named confirmations',async()=>{
    for(const label of ['Comment','Submit review','Approve review','Request changes','Merge pull request','Close issue','Close pull request','Delete branch','Delete tag','Delete repository','Save settings','Unstar']){
      const id=await fresh('github'),prepared=await call('click',await target(label));assert.equal(state(prepared).adapter.context,'fixture-repository / branch-1');assert.match(prepared.approval.question,/Synthetic account/);
      await denyTrust(prepared.approval,receiver(id,label));await approved(prepared,receiver(id,label));
      if(!['Comment','Submit review','Approve review','Request changes','Unstar'].includes(label))assert.ok((await call('operation_status',{operation_id:prepared.approval.operation_id})).operation.stages.confirmation);
    }
    const id=await fresh('github'),star=await call('click',await target('Star'));assert.ok(!star.approval);await eventually(()=>counts(receiver(id,'Star'))===1,'free star');
    for(const field of ['account','context','text','preview','attachments'])await refusedAfterChange('github',field,'Comment');
  });
  await check('GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded',async()=>{
    for(const [site,labels]of [['github',['Squash and merge','Rebase and merge','Confirm merge','Close this issue','Update settings','Add comment','Unstar repository']],['gemini',['Share conversation','Share','Delete conversation']],['deezer',['Share album','Share artist','Share to a contact','Unlike track','Unfollow artist']]])for(const label of labels){
      const id=await fresh(site),prepared=await call('click',await target(label));assert.equal(evidence(receiver(id,label),'alias before approval').count,0);assert.ok(state(prepared).adapter);await denyTrust(prepared.approval,receiver(id,label));await approved(prepared,receiver(id,label));
    }
  });
  await check('GROUP 4 ADAPTER every named GitHub confirmation mismatch',async()=>{
    for(const label of ['Merge pull request','Close issue','Close pull request','Delete branch','Delete tag','Delete repository','Save settings'])for(const mismatch of ['kind','text','frame','site','button','twice']){
      const id=await fresh('github','&mismatch='+mismatch),key=receiver(id,label),prepared=await call('click',await target(label));assert.ok(prepared.approval.description.untrusted_content.confirmation);
      assert.equal(evidence(key,'before original approval').count,0);await call('submit',prepared.approval);assert.equal(evidence(key,'different confirmation waiting').count,0);
      let answer,dialogInput;
      if(mismatch==='button')answer=await call('click',await target('Delete now'));
      else{const {untrusted_content:{dialog}}=await call('read',{tab});assert.ok(dialog);dialogInput={tab,expected:dialog,accept:true,...(mismatch==='kind'?{text:'Synthetic confirmation'}:{})};answer=await call('dialog',dialogInput);}
      if(mismatch==='button'||label.startsWith('Delete'))await approved(answer,key);
      else{
        // Merge/Close/Save aren't listed generic words. Their mismatched native
        // dialogs stay open, then a separate explicit dialog call is free (§6 group 4).
        assert.ok(!answer.approval);await eventually(()=>counts(key)===1,'independent free confirmation');assert.equal(evidence(key,'independent free dialog').count,1);
        assert.equal((await rpc('dialog',dialogInput)).ok,false);await delay(50);assert.equal(evidence(key,'repeat free dialog refused').count,1);
      }
      await call('submit',prepared.approval);assert.equal(counts(key),1);
    }
  });
  await check('GROUP 10 ADAPTER Gemini question content and always asking chat changes',async()=>{
    for(const label of ['Send','Delete chat','Share chat']){
      const id=await fresh('gemini'),prepared=await call('click',await target(label));assert.equal(state(prepared).adapter.text,'Full synthetic question');assert.equal(state(prepared).adapter.attachments.length,1);
      await denyTrust(prepared.approval,receiver(id,label));await approved(prepared,receiver(id,label));
      if(label!=='Send'){let refused=false;try{admin('chrome_sites',{command:'allow',operation_id:prepared.approval.operation_id});}catch{refused=true;}assert.ok(refused,'chat changes cannot be owner-allowed');}
    }
    for(const field of ['account','text','attachments','preview'])await refusedAfterChange('gemini',field);
  });
  await check('GROUP 11 ADAPTER Gemini exact account owner entry and revocation',async()=>{
    let id=await fresh('gemini'),prepared=await call('press',{...await target('Enter a prompt here'),key:'Enter'});await approved(prepared,receiver(id,'Enter'));
    const entry=admin('chrome_sites',{command:'allow',operation_id:prepared.approval.operation_id});
    for(const label of ['Delete chat','Share chat']){id=await fresh('gemini');prepared=await call('click',await target(label));await denyTrust(prepared.approval,receiver(id,label));await approved(prepared,receiver(id,label));}
    id=await fresh('gemini','',8766);prepared=await call('click',await target('Send'));assert.ok(state(prepared).adapter);await denyTrust(prepared.approval,receiver(id));await approved(prepared,receiver(id));
    id=await fresh('gemini');prepared=await call('click',await target('Send'));await approved(prepared,receiver(id),{trusted:true});
    id=await fresh('gemini');await fixture.mutate(id,'account');prepared=await call('click',await target('Send'));await denyTrust(prepared.approval,receiver(id));await approved(prepared,receiver(id));
    admin('chrome_sites',{command:'revoke',id:entry.id});id=await fresh('gemini');prepared=await call('click',await target('Send'));await denyTrust(prepared.approval,receiver(id));await approved(prepared,receiver(id));
  });
  await check('GROUP 10 ADAPTER Deezer playback additions removals posts shares and payments',async()=>{
    for(const label of ['Play','Pause','Skip','Next','Previous','Seek','Volume','Queue','Like','Follow','Add to playlist','Add to library','Unlike','Unfollow','Remove from playlist','Remove from favorites','Remove from favourites','Delete playlist','Post comment','Share track','Share playlist','Pay','Subscribe']){
      const id=await fresh('deezer'),result=await call('click',await target(label));
      if(['Play','Pause','Skip','Next','Previous','Seek','Volume','Queue','Like','Follow','Add to playlist','Add to library'].includes(label)){assert.ok(!result.approval);await eventually(()=>counts(receiver(id,label))===1,'free '+label);evidence(receiver(id,label),'free change');}
      else{await denyTrust(result.approval,receiver(id,label));await approved(result,receiver(id,label));}
    }
    let id=await fresh('deezer');
    for(const [verb,label,args]of [['select','Playback position',{value:'b'}],['select','Playback volume',{value:'b'}],['check','Library addition',{checked:true}]]){const changed=await call(verb,{...await target(label),...args});assert.ok(!changed.approval);await eventually(()=>counts(receiver(id,label))===1,'free '+label);evidence(receiver(id,label),'free choice');}
    id=await fresh('deezer','&variant=form-playback');const form=await call('click',await target('Play'));assert.equal(state(form).adapter,null);await approved(form,receiver(id,'Play'));
  });
  await check('GROUP 10 ADAPTER bank owner restriction all inputs and positive reads links scroll',async()=>{
    admin('chrome_sites',{command:'readonly',site:'http://bank.test:8765/',enabled:true});
    const id=await fresh('bank');assert.match(JSON.stringify(await call('read',{tab})),/Synthetic read-only balance/);
    const scroll=await call('scroll',{...await target('Amount'),x:0,y:30});assert.ok(!scroll.approval);
    for(const [verb,label,args]of [['fill','Amount',{text:'1'}],['click','Continue',{}],['upload','File',{path:'/fixture.txt'}],['check','Tick',{checked:true}],['select','Choice',{value:'b'}],['press','Amount',{key:'Enter'}]]){
      const response=await rpc(verb,{...await target(label),...args});assert.equal(response.ok,false);assert.equal(response.error.code,'readonly_site');assert.equal(counts(receiver(id,'Continue')),0);assert.equal(evidence(receiver(id,'Unexpected bank input'),'read-only input refused').count,0);
    }
    const form=await rpc('fill_form',{fields:[{...await target('Amount'),text:'1'}]});assert.equal(form.ok,false);assert.equal(form.error.code,'readonly_site');
    assert.ok(!(await call('click',await target('Account details'))).approval);await eventually(()=>counts(id+':link')===1,'bank link');
    const modalId=await fresh('bank');await fixture.mutate(modalId,'dialog');const dialog=await eventually(async()=>(await call('read',{tab})).untrusted_content.dialog,'read-only native dialog');
    for(const accept of [true,false]){const answer=await rpc('dialog',{tab,expected:dialog,accept});assert.equal(answer.ok,false);assert.equal(answer.error.code,'readonly_site');assert.equal(evidence(receiver(modalId,'Unexpected bank dialog'),'read-only dialog refused').count,0);}
    execFileSync('xdotool',['key','--clearmodifiers','Escape']);await delay(100);assert.equal(counts(receiver(modalId,'Unexpected bank dialog')),0);
  });
  await check('GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites',async()=>{
    for(const site of ['gmail','whatsapp','github','gemini','deezer']){
      const id=await fresh(site,'&variant=unknown'),prepared=await call('click',await target('Send'));assert.equal(state(prepared).adapter,null);await denyTrust(prepared.approval,receiver(id));await approved(prepared,receiver(id));
      await lifecycle({fixture:'qualification',mode:'adapter-off-'+site});const label=site==='github'?'Comment':site==='deezer'?'Post comment':'Send',disabled=await fresh(site),generic=await call('click',await target(label));assert.equal(state(generic).adapter,null);await approved(generic,receiver(disabled,label,site==='gmail'?'first':'main'));await lifecycle({fixture:'qualification',mode:'qualified'});
    }
    await lifecycle({fixture:'qualification',mode:'conservative'});
    for(const site of ['gmail','whatsapp','github','gemini','deezer']){
      const label=site==='github'?'Comment':site==='deezer'?'Post comment':'Send',id=await fresh(site),prepared=await call('click',await target(label));assert.equal(state(prepared).adapter,null);await denyTrust(prepared.approval,receiver(id,label,site==='gmail'?'first':'main'));await approved(prepared,receiver(id,label,site==='gmail'?'first':'main'));
    }
    await fresh('bank');const restricted=await rpc('fill',{...await target('Amount'),text:'1'});assert.equal(restricted.error.code,'readonly_site');await lifecycle({fixture:'qualification',mode:'qualified'});
  });
  await check('GROUP 10 ADAPTER Gemini question uses its required semantic name',async()=>{
    const id=await fresh('gemini'),prepared=await call('click',await target('Send'));assert.equal(evidence(receiver(id),'wording check').count,0);
    assert.match(prepared.approval.question,/Gemini: ask a question/);
    await call('drop',{operation_id:prepared.approval.operation_id});
  });
  await check('GROUP 10 ADAPTER Gmail question names its attachments',async()=>{
    const id=await fresh('gmail'),prepared=await call('click',await target('Send'));assert.equal(evidence(receiver(id,'Send','first'),'wording check').count,0);
    assert.match(prepared.approval.question,/\b(?:1|one) attachment\b/);
    assert.match(prepared.approval.question,/fixture\.txt/);
    await call('drop',{operation_id:prepared.approval.operation_id});
  });
  await check('GROUP 10 ADAPTER Gmail deletion shortcut question names the deletion',async()=>{
    const id=await fresh('gmail'),prepared=await call('press',{...await target('Selected message'),key:'#'});assert.ok(prepared.approval);assert.equal(evidence(receiver(id,'Delete shortcut'),'wording check').count,0);
    assert.match(prepared.approval.question,/delete/i);
    await call('drop',{operation_id:prepared.approval.operation_id});
  });
  if(results.some(row=>!row.passed))throw Object.assign(new AggregateError(results.filter(row=>!row.passed).map(row=>Error(row.name+': '+row.error)),'Adapter requirements failed; see adapters.json and adapters-receiver.jsonl'),{results});
  return results;
}
