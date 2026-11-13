// Synthetic popup flows. This module generates fixtures; only the Linux runner opens them.
import assert from 'node:assert/strict';
import {setTimeout as delay} from 'node:timers/promises';

export function popupPage(url){
  const id=url.searchParams.get('id'),mode=url.searchParams.get('mode')||'clean';
  const name='popup-'+id,child='http://popup.test:8766/?case=popup-child&id='+id+'&mode='+mode;
  if(url.searchParams.get('case')==='popup-opener')return {
    body:mode==='post'?`<form method="post" target="${name}" action="http://popup.test:8766/post-document?case=${id}"><button type="submit">Open window</button></form>`:'<button type="button" style="position:fixed;inset:0;width:100vw;height:100vh;margin:0">Open window</button>',
    script:`let child;document.querySelector('button').onclick=()=>{child=window.open(${JSON.stringify(mode==='post'?'about:blank':child)},${JSON.stringify(name)},'popup,width=620,height=480');};window.addEventListener('message',event=>{if(event.source===child&&event.origin==='http://popup.test:8766'&&event.data===${JSON.stringify(id)})fetch('/receive?case=flow-'+${JSON.stringify(id)},{method:'POST',body:'opener relationship preserved'});});`,
  };
  return {
    body:mode==='typed-clean'?`<input aria-label="Draft" value="Saved"><form method="post" action="/receive?case=${id}" target="sink"><input name="draft" value="Saved"><button type="button">Continue</button></form><iframe name="sink" hidden></iframe>`:`<select aria-label="Draft"><option selected>Saved</option><option>Unsaved</option></select><form method="post" action="/receive?case=${id}" target="sink"><select name="draft"><option selected>Saved</option></select><button type="button">Continue</button></form><iframe name="sink" hidden></iframe>`,
    script:`document.title='Popup '+${JSON.stringify(id)};const firstSubmit=HTMLFormElement.prototype.submit,documentToken=Date.now()+'-'+Math.random();const probes=new EventSource('/events?id='+${JSON.stringify(id)});probes.onmessage=event=>{const change=JSON.parse(event.data);if(change.change==='popup-probe'){fetch('/receive?case=state-'+${JSON.stringify(id)},{method:'POST',body:JSON.stringify({document:documentToken,opener:!!opener,openerClosed:opener?.closed,name:window.name,draft:document.querySelector('input,textarea,select').value})});fetch('/mutation-ack?nonce='+change.nonce);}};fetch('/receive?case=loaded-'+${JSON.stringify(id)},{method:'POST',body:JSON.stringify({opener:!!opener,name:window.name,outerWidth,outerHeight})});${mode==='dirty'?"document.querySelector('input,textarea,select').value='Unsaved';":''}document.querySelector('button').onclick=()=>{opener?.postMessage(${JSON.stringify(id)},'http://fixture.test:8765');firstSubmit.call(document.querySelector('form'));};`,
  };
}

export async function popupMatrices({check,call,rpc,nav,counts,eventually,getTab,fixture,ownerOpenPopup,popupEvidence,popupControl,setTab,approval}){
  const rows=async targetTab=>{
    const page=await call('read',{tab:targetTab});
    return page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse);
  };
  const target=async targetTab=>{const row=await eventually(async()=>(await rows(targetTab)).find(row=>row.expected.name==='Continue'),'popup target');return {reference:row.reference,expected:row.expected};};
  const find=async id=>eventually(async()=>(await call('tabs',{limit:10})).items.find(item=>item.tab!==getTab()&&(item.url?.includes('case=popup-child&id='+id)||item.url?.includes('/post-document?case='+id))),'popup admitted '+id);
  const evidence=(id,phase)=>console.log('POPUP RECEIVER',id,phase,JSON.stringify(fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')?.includes(id))));
  await check('GROUP 8 popups preserve opener flow and guard first input without moving windows',async()=>{
    const tab=getTab();
    for(const mode of ['clean','dirty','typed-clean']){
      const id='popup-'+mode;await nav('popup-opener&id='+id+'&mode='+mode);const parent=(await call('tabs',{limit:10})).items.find(item=>item.tab===tab);const open=(await call('read',{tab})).untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Open window');
      await call('click',{reference:open.reference,expected:open.expected});const popup=await find(id);await eventually(async()=>(await find(id)).controlled,'private popup group');
      assert.notEqual(popup.window,parent.window,'the popup must remain separate from its opener window');
      await eventually(()=>counts('loaded-'+id)===1,'initial popup load');const before=await target(popup.tab);await rows(popup.tab);assert.equal(counts('loaded-'+id),1,'read preserves popup');
      const nativeBefore=await popupEvidence(id,'before');
      const first=await rpc('click',before);assert.equal(first.ok,false);assert.equal(first.error.code,mode==='clean'?'stale_reference':'reload_required');
      if(mode!=='clean'){assert.equal(counts('loaded-'+id),1);const repeated=await rpc('click',{...before,reload_taken_tab:true});assert.equal(repeated.error.code,'stale_reference');}
      await eventually(()=>counts('loaded-'+id)===2,'one guarded reload');const fresh=await target(popup.tab);assert.notEqual(fresh.reference.document,before.reference.document);assert.equal((await rpc('click',before)).ok,false);
      const loads=fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='loaded-'+id).map(row=>JSON.parse(row.body));
      assert.equal(loads.length,2);assert.ok(loads.every(load=>load.opener));assert.equal(loads[1].name,loads[0].name);
      assert.deepEqual(await popupEvidence(id,'after'),nativeBefore,'native popup window, position and size remain intact');
      await approval(await call('click',fresh),id);await eventually(()=>counts('flow-'+id)===1,'opener receives postMessage after reload');evidence(id,'guarded 0/1/1 and opener complete');
      await call('close_tab',{tab:popup.tab});
    }
  });
  await check('GROUP 8 opener badges and per-popup Stop preserve windows documents and focus',async()=>{
    const tab=getTab(),id='popup-stop';await nav('popup-opener&id='+id);
    const original=await popupControl('state');
    const open=(await rows(tab)).find(row=>row.expected.name==='Open window');
    await call('click',{reference:open.reference,expected:open.expected});const popup=await find(id);
    const active=await eventually(async()=>{const state=await popupControl('state');return state.tabs.find(row=>row.tab===tab)?.badge==='POP'&&state;},'opener popup badge');
    assert.equal(active.windows.length,original.windows.length+1,'only the page popup opens');
    assert.deepEqual(active.windows.filter(row=>row.id!==popup.window).map(({focused,...row})=>row),original.windows.map(({focused,...row})=>row));
    assert.equal(active.windows.find(row=>row.focused)?.id,popup.window,'native page popup keeps focus');
    assert.equal(active.windows.find(row=>row.id===popup.window)?.type,'popup');
    assert.deepEqual(active.popups.map(row=>row.tab),[popup.tab]);
    const before=await target(popup.tab);await eventually(()=>counts('loaded-'+id)===1,'single popup load');
    const probe=async()=>{const n=counts('state-'+id);await fixture.mutate(id,'popup-probe');await eventually(()=>counts('state-'+id)===n+1,'same-document state probe');return JSON.parse(fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='state-'+id).at(-1).body);};
    const pageBefore=await probe(),nativeBefore=await popupEvidence(id,'before-stop');
    const ui=await popupControl('stop',tab);
    assert.deepEqual(ui.after.windows,ui.before.windows,'Stop creates no window and changes no focus, position, size or type');
    assert.equal(ui.afterFocus,ui.beforeFocus,'Stop keeps the same focused native window');
    assert.equal((await find(id)).controlled,false);assert.equal(ui.after.tabs.find(row=>row.tab===tab)?.badge,'ON');
    assert.deepEqual(ui.after.popups,[]);assert.equal((await call('tabs',{limit:10})).items.find(row=>row.tab===tab).controlled,true,'per-popup Stop keeps opener control');
    assert.deepEqual(await probe(),pageBefore,'same document, draft, window.name and opener after Stop');
    assert.deepEqual(await popupEvidence(id,'after-stop'),nativeBefore);assert.equal(counts('loaded-'+id),1,'Stop never reloads');
    const denied=await rpc('click',before);assert.equal(denied.ok,false);assert.equal(counts(id),0,'later Claude input is refused without dispatch');evidence(id,'per-popup Stop preserves document and refuses later input');
    await popupControl('close-popup',id);
  });
  await check('GROUP 8 closing or releasing an opener ends popup control and clears badges',async()=>{
    for(const mode of ['release','close']){
      const tab=getTab(),id='popup-opener-'+mode;await nav('popup-opener&id='+id);
      const open=(await rows(tab)).find(row=>row.expected.name==='Open window');await call('click',{reference:open.reference,expected:open.expected});const popup=await find(id);
      await eventually(async()=>(await popupControl('state')).tabs.find(row=>row.tab===tab)?.badge==='POP','opener badge before '+mode);
      const before=await target(popup.tab),nativeBefore=await popupEvidence(id,'before-'+mode);
      await eventually(()=>counts('loaded-'+id)===1,'opener lifecycle initial load');
      if(mode==='release')await call('release_tab',{tab});else setTab(await popupControl('close-opener',tab));
      const ended=await eventually(async()=>{const state=await popupControl('state');return !state.popups.length&&state;},'opener '+mode+' revokes child');
      assert.ok(!ended.tabs.find(row=>row.tab===tab)?.badge,'opener badge clears');
      assert.equal((await find(id)).controlled,false);assert.deepEqual(await popupEvidence(id,'after-'+mode),nativeBefore);
      assert.equal((await rpc('click',before)).ok,false);assert.equal(counts('loaded-'+id),1);assert.equal(counts(id),0);evidence(id,'opener '+mode+' refuses later input without reload');
      await popupControl('close-popup',id);if(mode==='release')await call('take_tab',{tab});
    }
  });
  await check('GROUP 8 POST popups never resubmit and ordinary openers stay untouched',async()=>{
    const tab=getTab();
    const id='popup-post';await nav('popup-opener&id='+id+'&mode=post');
    const open=(await call('read',{tab})).untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Open window');
    await approval(await call('click',{reference:open.reference,expected:open.expected}),id);
    const popup=await find(id);await eventually(async()=>(await find(id)).controlled,'POST popup private group');
    const denied=await rpc('click',await target(popup.tab));assert.equal(denied.ok,false);assert.match(denied.error.message,/open its address.*Claude tab/);await delay(100);assert.equal(counts(id),1,'POST refusal makes no second request');evidence(id,'POST refusal');await call('close_tab',{tab:popup.tab});
    const outside=await ownerOpenPopup(tab);assert.equal(outside.controlled,false);await eventually(()=>counts('loaded-popup-outside')===1,'ordinary popup initial load');await delay(100);assert.equal(counts('loaded-popup-outside'),1);evidence('popup-outside','ordinary opener untouched');
    // Owner closes its own popup; the tool is never given authority over it.
    await ownerOpenPopup(null);await call('take_tab',{tab});
  });
}
