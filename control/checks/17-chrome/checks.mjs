import assert from 'node:assert/strict';
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
import {PageView} from './view.mjs';
import {Hold,websocketShim} from './hold.mjs';
import {evaluate,eventually} from './protocol.mjs';
import {delay,address,key,screenshot} from './ui.mjs';

export const save=(out,name,value)=>fs.writeFileSync(`${out}/${name}.json`,JSON.stringify(value,null,2)+'\n');
export async function navigate(cdp,url){
  const r=await cdp.send('Page.navigate',{url});if(r.errorText)throw new Error(r.errorText);
  await eventually(async()=>await evaluate(cdp,'location.href')===url&&await evaluate(cdp,'document.readyState')==='complete','navigate '+url);
  await delay(250);
}
async function press(cdp,keyName){
  await cdp.send('Input.dispatchKeyEvent',{type:'keyDown',key:keyName,code:keyName,windowsVirtualKeyCode:keyName==='Enter'?13:35});
  await cdp.send('Input.dispatchKeyEvent',{type:'keyUp',key:keyName,code:keyName,windowsVirtualKeyCode:keyName==='Enter'?13:35});
}
function ref(view,name,role){const row=view.elements.find(e=>e.name===name&&(!role||e.role===role));assert.ok(row?.ref,`Missing ${role||''} ${name}`);return row.ref;}

export async function readAndAct(cdp,fixture,out,route,aria,frameSessions){
  const view=new PageView(cdp,frameSessions);await view.enable();
  const metrics=[];
  for(const page of ['form','table','frames','shadow','modal','article']){
    await navigate(cdp,fixture.base+'/'+page);
    if(page==='frames')await eventually(async()=>{const v=await view.read({limit:10000});return v.frames.length===3;},'three fixture frames');
    const v=await view.read({limit:10000});assert.equal(v.errors.length,0);
    const json=JSON.stringify(v);save(out,`${route}-view-${page}`,v);
    const metric={page,characters:json.length,tokensAt4Chars:Math.ceil(json.length/4),ms:v.ms,elements:v.total,frames:v.frames.length};
    if(aria){
      const start=performance.now();const text=await aria();
      fs.writeFileSync(`${out}/${route}-aria-${page}.txt`,text);
      Object.assign(metric,{ariaCharacters:text.length,ariaTokensAt4Chars:Math.ceil(text.length/4),ariaMs:Math.round((performance.now()-start)*100)/100});
    }
    metrics.push(metric);console.log('VIEW',route,JSON.stringify(metric));
    if(page==='form'){
      assert.equal(v.elements.find(e=>e.name==='Display name').state.required,true);
      assert.equal(v.elements.find(e=>e.name==='Updates').state.checked,'true');
      assert.equal(v.elements.find(e=>e.name==='Disabled').state.disabled,true);
      assert.ok(v.elements.some(e=>e.state.invalid==='true'));
      assert.ok(v.elements.some(e=>e.onScreen===false));
    }
    if(page==='shadow')assert.ok(v.elements.some(e=>e.name==='Shadow note'));
    if(page==='modal')assert.ok(v.elements.some(e=>e.role==='dialog'&&e.state.modal===true));
    if(page==='frames'){
      for(const frame of v.frames.filter(f=>f.parent)){
        const row=v.elements.find(e=>e.frame===frame.id&&e.name==='Frame note');assert.ok(row);
        await view.act(row.ref,'fill','edited-'+new URL(frame.url).searchParams.get('name'));
      }
      const after=await view.read({limit:10000});
      assert.equal(after.elements.filter(e=>e.name==='Frame note'&&e.value?.startsWith('edited-')).length,2);
    }
  }
  await navigate(cdp,fixture.base+'/form');let v=await view.read({limit:10000});
  await view.act(ref(v,'Display name'),'fill','Synthetic Reader');
  await view.act(ref(v,'Region'),'select','South');
  await view.act(ref(v,'Updates'),'check',false);
  await view.act(ref(v,'Start date'),'fill','2026-11-07');
  const upload=`${out}/synthetic-upload.txt`;fs.writeFileSync(upload,'Synthetic fixture attachment only.\n');
  await view.act(ref(v,'Local file'),'file',upload);
  assert.equal(await evaluate(cdp,'document.querySelector("#file").files[0].text()'),fs.readFileSync(upload,'utf8'));
  assert.deepEqual(await evaluate(cdp,'({name:document.querySelector("#name").value,region:document.querySelector("#region").value,updates:document.querySelector("#updates").checked,date:document.querySelector("#date").value,file:document.querySelector("#file").files[0].name})'),{name:'Synthetic Reader',region:'South',updates:false,date:'2026-11-07',file:'synthetic-upload.txt'});
  await view.act(ref(v,'Display name'),'focus');await press(cdp,'End');await cdp.send('Input.insertText',{text:'!'});
  assert.equal(await evaluate(cdp,'document.querySelector("#name").value'),'Synthetic Reader!');
  await view.act(ref(v,'Extra field 25'),'scroll');assert.ok(await evaluate(cdp,'scrollY')>0);
  await navigate(cdp,fixture.base+'/owner');v=await view.read({limit:10000});const old=ref(v,'Owner note');
  const again=await view.read({limit:10000});assert.equal(ref(again,'Owner note'),old);
  await view.act(ref(v,'Replace note'),'click');await assert.rejects(()=>view.act(old,'fill','wrong'),/STALE_REF/);
  assert.equal(await evaluate(cdp,'document.querySelector("#note").value'),'replacement');
  const replacement=ref(await view.read({limit:10000}),'Replacement');
  await navigate(cdp,fixture.base+'/owner');await assert.rejects(()=>view.act(replacement,'fill','wrong'),/STALE_REF/);
  v=await view.read({limit:10000});const owned=ref(v,'Owner note');
  // Simulate the owner opening a new tab, switching away, then back to a different tab.
  await key('ctrl+t');await address(fixture.base+'/other');
  await view.act(owned,'fill','tool-owned-tab-only');
  assert.equal(await evaluate(cdp,'document.querySelector("#note").value'),'tool-owned-tab-only');
  await screenshot(out,`${route}-owner-other-tab`);
  await key('ctrl+shift+Tab');await delay(200);await key('ctrl+Tab');
  await view.act(owned,'fill','still-bound-to-original');
  assert.equal(await evaluate(cdp,'document.querySelector("#note").value'),'still-bound-to-original');
  console.log('ACTIONS PASS',route,'fill/select/check/date/file/key/scroll/frames/shadow-read/stale/tab-switch');
  save(out,`${route}-actions`,{fileUploads:view.fileUploadResults,staleRemoved:'rejected',staleDocument:'rejected',tabBinding:'original retained'});
  save(out,`${route}-metrics`,metrics);view.close();return metrics;
}

const matching=(arrivals,c)=>arrivals.filter(r=>['http','ws'].includes(r.kind)&&(r.url?.includes('case='+c)||r.body?.includes('case='+c)));
export async function holdChecks(cdp,fixture,out,route){
  const hold=new Hold(cdp);await hold.enable();const results=[];
  const kinds=['post','get','fetch','xhr','beacon','autosave','worker','cross','ping'];
  for(const kind of kinds)for(const decision of ['release','drop']){
    const c=`${kind}-${route}-${decision}`,before=fixture.arrivals.length;
    await navigate(cdp,fixture.base+'/hold?case='+c);
    if(kind==='worker')await eventually(async()=>await evaluate(cdp,'document.querySelector("#status").textContent')==='Worker ready','service worker activation');
    const view=new PageView(cdp);await view.enable();const v=await view.read({limit:10000});
    hold.intent={form:['post','get','cross'].includes(kind),typing:kind==='autosave'};
    if(kind==='autosave')await view.act(ref(v,'Message'),'fill','synthetic-autosave');
    else await view.act(ref(v,kind==='ping'?'Follow fixture link with ping':'Send fixture'),'click');
    await eventually(()=>[...hold.pending.values()].some(e=>e.preview.address.includes('case='+c))||matching(fixture.arrivals,c).length,'held or leaked '+c);
    await delay(600);
    const pending=[...hold.pending.values()].filter(e=>e.preview.address.includes('case='+c));
    const heldLog=matching(fixture.arrivals,c);
    const appearance=await evaluate(cdp,'document.body.innerText');
    if(kind==='fetch'&&decision==='release'){await cdp.send('Page.bringToFront');await screenshot(out,`${route}-while-fetch-held`);}
    const record={kind,decision,case:c,serverSequenceBefore:before,heldMs:600,whileHeld:heldLog.length,pending:pending.map(e=>({id:e.id,preview:e.preview,hash:e.hash})),appearance};
    if(kind!=='worker')assert.equal(heldLog.length,0,`${c} left before approval`);
    if(pending.length){
      assert.equal(pending.length,1);const entry=pending[0];
      await assert.rejects(()=>hold.decide(entry.id,decision,'changed-preview'),/PREVIEW_MISMATCH/);
      await hold.decide(entry.id,decision,entry.hash);
      await assert.rejects(()=>hold.decide(entry.id,decision,entry.hash),/NOT_PENDING/);
      if(decision==='release')await eventually(()=>matching(fixture.arrivals,c).length===1,'one arrival '+c);
      await delay(400);assert.equal(matching(fixture.arrivals,c).length,decision==='release'?1:0);
      record.result=decision==='release'?'held then exactly one arrival':'held then dropped, zero arrivals';
    }else{
      assert.equal(kind,'worker');assert.equal(heldLog.length,1);
      record.result='NOT HELD: service-worker request bypassed tab Fetch';
    }
    record.after=matching(fixture.arrivals,c);results.push(record);
    console.log('HOLD',route,kind,decision,'whileHeld='+record.whileHeld,'after='+record.after.length,record.result);
    if(kind==='fetch'&&decision==='release')await screenshot(out,`${route}-after-held-fetch`);
    view.close();hold.intent={};
  }
  // Trusted origins are an explicit owner policy exception; exercise it with synthetic data.
  const trustedCase=`fetch-${route}-trusted`;hold.trusted.add(fixture.base);
  await navigate(cdp,fixture.base+'/hold?case='+trustedCase);
  await evaluate(cdp,'document.querySelector("#trigger").click()');
  await eventually(()=>matching(fixture.arrivals,trustedCase).length===1,'trusted origin delivery');
  assert.equal(hold.pending.size,0);hold.trusted.clear();
  results.push({kind:'trusted-origin',after:matching(fixture.arrivals,trustedCase)});

  const wsCase=`ws-${route}-baseline`;
  await navigate(cdp,fixture.base+'/hold?case='+wsCase);
  await eventually(async()=>await evaluate(cdp,'document.querySelector("#status").textContent')==='Socket ready','WebSocket ready');
  let observed=0;const onSent=()=>observed++;cdp.on('Network.webSocketFrameSent',onSent);
  await evaluate(cdp,'document.querySelector("#message").focus()');await press(cdp,'Enter');
  await eventually(()=>matching(fixture.arrivals,wsCase).length===1,'WebSocket baseline leakage');
  assert.equal(hold.pending.size,0);assert.ok(observed>0);cdp.off('Network.webSocketFrameSent',onSent);
  results.push({kind:'ws-baseline',result:'Fetch did not pause WebSocket frame',after:matching(fixture.arrivals,wsCase),observed});
  const injection=await cdp.send('Page.addScriptToEvaluateOnNewDocument',{source:websocketShim});
  await press(cdp,'Enter');await eventually(()=>matching(fixture.arrivals,wsCase).length===2,'preload is not retroactive');
  results.push({kind:'ws-preload-existing-document',result:'new-document shim did not change the existing tab document',after:matching(fixture.arrivals,wsCase)});
  for(const decision of ['release','drop']){
    const c=`ws-${route}-shim-${decision}`;await navigate(cdp,fixture.base+'/hold?case='+c);
    await eventually(async()=>await evaluate(cdp,'document.querySelector("#status").textContent')==='Socket ready','WebSocket shim ready');
    await evaluate(cdp,'document.querySelector("#message").focus()');await press(cdp,'Enter');await delay(600);
    assert.equal(matching(fixture.arrivals,c).length,0);const pending=await evaluate(cdp,'__checkWS.list()');assert.equal(pending.length,1);
    await evaluate(cdp,`__checkWS.decide(${pending[0].id},${decision==='release'})`);
    if(decision==='release')await eventually(()=>matching(fixture.arrivals,c).length===1,'shim release');
    await delay(300);assert.equal(matching(fixture.arrivals,c).length,decision==='release'?1:0);
    results.push({kind:'ws-shim',decision,whileHeld:0,pending,after:matching(fixture.arrivals,c)});
  }
  // New-document scripts do not instrument worker realms: concrete cooperative-shim bypass.
  const bypass=`ws-${route}-bypass`;
  await navigate(cdp,fixture.base+'/hold?case='+bypass);
  await evaluate(cdp,`new Promise(resolve=>{const code="const ws=new WebSocket('ws://"+location.host+"/ws?case=${bypass}');ws.onopen=()=>{ws.send('synthetic-worker-bypass');postMessage('sent')}";const worker=new Worker(URL.createObjectURL(new Blob([code],{type:'text/javascript'})));worker.onmessage=()=>{worker.terminate();resolve(true)}})`);
  await eventually(()=>matching(fixture.arrivals,bypass).length===1,'unwrapped worker bypass');
  results.push({kind:'ws-shim-bypass',result:'worker WebSocket bypassed new-document shim',after:matching(fixture.arrivals,bypass)});
  await cdp.send('Page.removeScriptToEvaluateOnNewDocument',{identifier:injection.identifier});
  // Action gating works on already-open sockets: don't dispatch Enter until approved.
  const gated=`ws-${route}-action-gate`;await navigate(cdp,fixture.base+'/hold?case='+gated);
  await eventually(async()=>await evaluate(cdp,'document.querySelector("#status").textContent')==='Socket ready','action gate ready');
  await evaluate(cdp,'document.querySelector("#message").focus()');await delay(600);assert.equal(matching(fixture.arrivals,gated).length,0);
  await press(cdp,'Enter');await eventually(()=>matching(fixture.arrivals,gated).length===1,'approved Enter');
  results.push({kind:'ws-action-gate',whileHeld:0,after:matching(fixture.arrivals,gated)});
  console.log('WEBSOCKET',route,'Fetch leaked; cooperative shim held/released/dropped; worker bypass; Enter gate held/released');
  save(out,`${route}-holds`,results);await hold.close();return results;
}

export async function publicChecks(cdp,out,route){
  const hold=new Hold(cdp);hold.publicMode=true;await hold.enable();
  const results=[];
  for(const [name,url]of [['wikipedia','https://en.wikipedia.org/wiki/Main_Page'],['news','https://www.bbc.com/news'],['demo-form','https://www.selenium.dev/selenium/web/web-form.html']]){
    const start=hold.history.length;
    const record={name,url};
    try{
      hold.phase='load';
      await navigate(cdp,url);await delay(2000);
      record.title=await evaluate(cdp,'document.title');
      record.textSample=(await evaluate(cdp,'document.body.innerText')).slice(0,800);
      if(name==='wikipedia'){
        hold.phase='action';
        hold.intent={form:true,typing:true};
        record.action=await evaluate(cdp,`(()=>{const input=document.querySelector('input[name=search]');if(!input)return 'no search field';input.value='synthetic fixture query';input.form.requestSubmit();return 'search submitted to request gate'})()`);
        await delay(700);
      }
      if(name==='demo-form'){
        hold.phase='action';
        hold.intent={form:true};record.action=await evaluate(cdp,`(()=>{const form=document.querySelector('form');if(!form)return 'no form';form.querySelector('input').value='Synthetic fixture';form.requestSubmit();return 'form submitted to request gate'})()`);
        await delay(700);
      }
    }catch(e){record.error=e.message;}
    record.requests=hold.history.slice(start);results.push(record);
    record.loadFalseAlarms=record.requests.filter(r=>r.reason&&r.phase==='load').length;
    record.actionCandidates=record.requests.filter(r=>r.reason&&r.phase==='action').length;
    record.guardOnlyDrops=record.requests.filter(r=>!r.reason&&r.decision==='drop').length;
    console.log('PUBLIC',name,record.title||record.error,'requests='+record.requests.length,'loadFalseAlarms='+record.loadFalseAlarms,'actionCandidates='+record.actionCandidates,'guardOnlyDrops='+record.guardOnlyDrops,record.action||'');
    hold.intent={};
  }
  save(out,`${route}-public-sites`,results);await hold.close();return results;
}
