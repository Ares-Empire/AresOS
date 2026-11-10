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
    body:`<input aria-label="Draft" value="Saved"><form method="post" action="/receive?case=${id}" target="sink"><input name="draft" value="Saved"><button type="button">Continue</button></form><iframe name="sink" hidden></iframe>`,
    script:`document.title='Popup '+${JSON.stringify(id)};const firstSubmit=HTMLFormElement.prototype.submit;fetch('/receive?case=loaded-'+${JSON.stringify(id)},{method:'POST',body:JSON.stringify({opener:!!opener,name:window.name,outerWidth,outerHeight})});${mode==='dirty'?"document.querySelector('input').value='Unsaved';":''}document.querySelector('button').onclick=()=>{opener?.postMessage(${JSON.stringify(id)},'http://fixture.test:8765');firstSubmit.call(document.querySelector('form'));};`,
  };
}

export async function popupMatrices({check,call,rpc,nav,counts,eventually,tab,fixture,ownerOpenPopup,approval}){
  const rows=async targetTab=>{
    const page=await call('read',{tab:targetTab});
    return page.untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse);
  };
  const target=async targetTab=>{const row=await eventually(async()=>(await rows(targetTab)).find(row=>row.expected.name==='Continue'),'popup target');return {reference:row.reference,expected:row.expected};};
  const find=async id=>eventually(async()=>(await call('tabs',{limit:10})).items.find(item=>item.tab!==tab&&(item.url?.includes('case=popup-child&id='+id)||item.url?.includes('/post-document?case='+id))),'popup admitted '+id);
  const evidence=(id,phase)=>console.log('POPUP RECEIVER',id,phase,JSON.stringify(fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')?.includes(id))));
  await check('GROUP 8 popups preserve opener flow and guard first input without moving windows',async()=>{
    for(const mode of ['clean','dirty']){
      const id='popup-'+mode;await nav('popup-opener&id='+id+'&mode='+mode);const open=(await call('read',{tab})).untrusted_content.tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse).find(row=>row.expected.name==='Open window');
      await call('click',{reference:open.reference,expected:open.expected});const popup=await find(id);await eventually(async()=>(await find(id)).controlled,'private popup group');
      await eventually(()=>counts('loaded-'+id)===1,'initial popup load');const before=await target(popup.tab);await rows(popup.tab);assert.equal(counts('loaded-'+id),1,'read preserves popup');
      const first=await rpc('click',before);assert.equal(first.ok,false);assert.equal(first.error.code,mode==='dirty'?'reload_required':'stale_reference');
      if(mode==='dirty'){assert.equal(counts('loaded-'+id),1);const repeated=await rpc('click',{...before,reload_taken_tab:true});assert.equal(repeated.error.code,'stale_reference');}
      await eventually(()=>counts('loaded-'+id)===2,'one guarded reload');const fresh=await target(popup.tab);assert.notEqual(fresh.reference.document,before.reference.document);assert.equal((await rpc('click',before)).ok,false);
      const loads=fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='loaded-'+id).map(row=>JSON.parse(row.body));
      assert.equal(loads.length,2);assert.ok(loads.every(load=>load.opener));assert.deepEqual(loads[1],loads[0],'popup window, name and opener remain intact');
      await approval(await call('click',fresh),id);await eventually(()=>counts('flow-'+id)===1,'opener receives postMessage after reload');evidence(id,'guarded 0/1/1 and opener complete');
      await call('close_tab',{tab:popup.tab});
    }
  });
  await check('GROUP 8 POST popups never resubmit and ordinary openers stay untouched',async()=>{
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
