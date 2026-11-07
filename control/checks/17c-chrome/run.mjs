import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {execFileSync,spawn} from 'node:child_process';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true')throw Error('Browser runs only on GitHub Linux runners');
const here=path.resolve('control/checks/17c-chrome'),work=path.resolve('.work/17c-chrome'),out=work+'/artifacts';fs.mkdirSync(out,{recursive:true});
const {fixture}=await import('./fixture.mjs');
const {address,key,delay,activateChrome,screenshot,x}=await import('../17-chrome/ui.mjs');
const {nativeBridge,evaluate,eventually}=await import('../17-chrome/protocol.mjs');
const {pack,idFor}=await import('../17-chrome/install.mjs');
const phase=process.env.CHECK_PHASE,summary={phase,head:process.env.GITHUB_SHA,run:process.env.GITHUB_RUN_ID,cases:[]},audit=new Map();
const save=(name,data)=>fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(data,null,2));
const log=(name,data)=>{summary.cases.push({name,...data});save('summary',summary);console.log(name,JSON.stringify(data))};
let chrome,bridge,selected,group,extId,version='0.3.0',wt;
const profile=work+'/profile',socket=work+'/native.sock';process.env.CHROME_CHECK_SOCKET=socket;
const f=await fixture(out,work,()=>`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${extId}"><updatecheck codebase="${f.base}/extension.crx" version="${version}"/></app></gupdate>`);
const kp=generateKeyPairSync('rsa',{modulusLength:2048});extId=idFor(kp.publicKey.export({type:'spki',format:'der'}));
const ext=work+'/extension';fs.cpSync(here+'/extension',ext,{recursive:true});
function packVersion(v){version=v;const m=JSON.parse(fs.readFileSync(ext+'/manifest.json'));Object.assign(m,{version:v,key:kp.publicKey.export({type:'spki',format:'der'}).toString('base64'),update_url:f.base+'/update.xml'});fs.writeFileSync(ext+'/manifest.json',JSON.stringify(m));pack(ext,work,kp)}
packVersion(version);
const host=work+'/host';fs.writeFileSync(host,`#!/bin/sh\nprintf '%s\\n' "$$" >> '${out}/host-pids.txt'\nexec python3 '${path.resolve('control/checks/17-chrome/native-host.py')}'\n`,{mode:0o755});
fs.writeFileSync(work+'/host.json',JSON.stringify({name:'org.aresos.chrome_check',description:'17c disposable check',path:host,type:'stdio',allowed_origins:[`chrome-extension://${extId}/`]}));
execFileSync('sudo',['install','-D','-m','644',work+'/host.json','/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome_check.json']);
function policy(forced=true){fs.writeFileSync(work+'/policy.json',JSON.stringify({ExtensionInstallForcelist:forced?[extId+';'+f.base+'/update.xml']:[],NativeMessagingUserLevelHosts:false,RestoreOnStartup:1}));execFileSync('sudo',['install','-D','-m','644',work+'/policy.json','/etc/opt/chrome/policies/managed/aresos-17c.json'])}policy();
const state=()=>bridge.send('Check.state');
async function boot(label,restore=false){
 bridge=await nativeBridge(socket);const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode',...(restore?['--restore-last-session']:[]),f.base+'/'];
 save('args-'+label,args);const fd=fs.openSync(out+'/chrome-'+label+'.log','a');chrome=spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});await activateChrome();await delay(3500);await connect();
}
async function connect(){const conn=new Promise(r=>bridge.once('check.connected',r));await key('ctrl+t');await address(`chrome-extension://${extId}/select.html?url=${encodeURIComponent(f.base+'/')}`);await key('Return');const c=await Promise.race([conn,delay(12000).then(()=>{throw Error('Extension did not connect')})]);selected=c.tabId;group=c.group;log('CONNECTED',c);}
async function close(kill=false){if(chrome?.exitCode===null){if(kill){chrome.kill('SIGKILL');try{execFileSync('pkill',['-KILL','-f',profile],{stdio:'ignore'})}catch{}}else{await activateChrome();await key('ctrl+shift+w');await delay(1500);if(chrome.exitCode===null)chrome.kill('SIGTERM')}await delay(800)}bridge?.close();bridge=undefined;chrome=undefined;}
async function nav(url=f.base+'/'){await bridge.send('Page.navigate',{url});await delay(400);if(url.startsWith(f.base))await eventually(()=>evaluate(bridge,"typeof send==='function'"),'fixture ready');}
const arrivals=id=>f.arrivals.filter(r=>r.case===id);
async function count(id,expected){await delay(250);assert.equal(arrivals(id).length,expected,id);audit.set(id,expected);return arrivals(id).length;}
async function hold(id,kind='fetch'){await evaluate(bridge,`send(${JSON.stringify(id)},${JSON.stringify(kind)});true`);return eventually(async()=>(await state()).pending.find(p=>JSON.stringify(p.description||p).includes(id)),'held '+id);}
async function dropAll(){for(const p of (await state()).pending)await bridge.send('Check.decide',{id:p.id,release:false});}
async function click(selector){const box=await evaluate(bridge,`(()=>{const b=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2}})()`);await bridge.send('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...box});await bridge.send('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...box});}
async function probe(name,fn){try{const r=await fn();log(name,{status:'observed',...r});return r}catch(e){log(name,{status:'unavailable',error:e.stack});return {error:e.message}}}
try{
 await boot('initial');
 const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);save('processes',{processes});assert.equal((await state()).manifest.permissions.includes('management'),false);
 await key('ctrl+t');await address('chrome://sandbox');await screenshot(out,'sandbox');await key('ctrl+w');
 if(phase==='pages'){
  // Independent receiver counts are checked again after Chrome exits.
  for(const kind of ['fetch','xhr','beacon','form-submit','form-request','form-event','ws','rtc','writer']){
   if(kind==='writer'){
    wt=spawn(path.resolve('.work/17b-chrome/venv/bin/python'),[path.resolve('control/checks/17b-chrome/webtransport.py'),work],{stdio:['ignore',fs.openSync(out+'/wt.log','a'),fs.openSync(out+'/wt.log','a')]});await eventually(()=>fs.existsSync(work+'/webtransport.json'),'WT receiver');
   }
   for(const release of [true,false]){
    await nav();if(kind==='ws')await evaluate(bridge,'connectWS().then(()=>true)');
    if(kind==='rtc'){await evaluate(bridge,'rtc()');await eventually(()=>evaluate(bridge,"channel.readyState==='open'"),'RTC open');}
    if(kind==='writer'){const info=JSON.parse(fs.readFileSync(work+'/webtransport.json'));await evaluate(bridge,`window.transport=new WebTransport(${JSON.stringify(info.url)},{serverCertificateHashes:[{algorithm:'sha-256',value:new Uint8Array(${JSON.stringify(info.hash)})}]});transport.ready.then(()=>{window.writer=transport.datagrams.writable.getWriter();return true})`);}
    const id='hold-'+kind+'-'+release,p=await hold(id,kind);await count(id,0);const before=await evaluate(bridge,'({states,url:location.href,failures:__hold17.failures})');await screenshot(out,id+'-waiting');await bridge.send('Check.decide',{id:p.id,release});
    if(kind==='writer'){await delay(300);const rows=fs.existsSync(out+'/webtransport-server.jsonl')?fs.readFileSync(out+'/webtransport-server.jsonl','utf8').trim().split('\n').map(JSON.parse):[];assert.equal(rows.filter(r=>r.body?.includes(id)).length,release?1:0);log('Q1_WRITER',{id,release,rows});}
    else await count(id,release?1:0);
    await assert.rejects(()=>bridge.send('Check.decide',{id:p.id,release}),/NOT_PENDING/);log('Q1_HOLD',{id,kind,release,before,after:await evaluate(bridge,'({states,url:location.href})'),arrivals:arrivals(id)});
   }
  }
  for(const [label,setup,code]of [
   ['same-frame',"const f=document.createElement('iframe');f.src='/';document.body.append(f);window.testFrame=f;",`testFrame.contentWindow.send('frame-same')`],
   ['blank',"window.testFrame=document.createElement('iframe');document.body.append(testFrame);",`testFrame.contentWindow.fetch('/receive?case=frame-blank',{method:'POST',body:'synthetic blank'})`],
   ['srcdoc',"window.testFrame=document.createElement('iframe');testFrame.srcdoc='<p>synthetic srcdoc</p>';document.body.append(testFrame);",`testFrame.contentWindow.fetch('/receive?case=frame-srcdoc',{method:'POST',body:'synthetic srcdoc'})`]
  ]){await nav();await evaluate(bridge,`(()=>{${setup}return true})()`);await delay(400);await evaluate(bridge,`${code};true`);const id='frame-'+(label==='same-frame'?'same':label);const p=await eventually(async()=>(await state()).pending.find(p=>JSON.stringify(p.description).includes(id)),label);await count(id,0);await bridge.send('Check.decide',{id:p.id,release:true});await count(id,1);log('Q1_FRAME',{id,source:p.source,arrivals:arrivals(id)});}
  await nav();await evaluate(bridge,`window.foreign=document.createElement('iframe');foreign.src=${JSON.stringify(f.base.replace('127.0.0.1','localhost')+'/')};document.body.append(foreign);true`);await delay(1000);const ft=await bridge.send('Page.getFrameTree');save('frame-tree',ft);const foreign=ft.frameTree.childFrames.find(t=>t.frame.url.includes('localhost'));assert.ok(foreign);const world=await bridge.send('Page.createIsolatedWorld',{frameId:foreign.frame.id,worldName:'check'});await bridge.send('Runtime.evaluate',{contextId:world.executionContextId,expression:`document.querySelector('button').click();document.forms[0].action='/receive?case=frame-cross';document.forms[0].requestSubmit();true`});const cp=await eventually(async()=>(await state()).pending.find(p=>JSON.stringify(p.description).includes('frame-cross')),'cross frame hold');await count('frame-cross',0);await bridge.send('Check.decide',{id:cp.id,release:false});log('Q1_CROSS_FRAME',{source:cp.source});
  // Native references are intentionally accessible to this hostile fixture.
  for(const attack of ['original','fresh-frame','prototype','toString','blob-worker']){
   await nav();const id='hostile-'+attack;
   const expression=attack==='fresh-frame'?`(()=>{const f=document.createElement('iframe');document.body.append(f);f.contentWindow.fetch('/receive?case=${id}',{method:'POST',body:'synthetic hostile'}).catch(()=>{});return true})()`:attack==='blob-worker'?`new Worker(URL.createObjectURL(new Blob([${JSON.stringify(`fetch('${f.base}/receive?case=${id}',{method:'POST',body:'synthetic blob'}).catch(()=>{})`)}],{type:'text/javascript'})));true`:`(()=>{${attack==='prototype'?"window.fetch=__hold17.original.fetch;":""}const raw=__hold17.original.fetch;window.detected=fetch.toString().includes('[native code]');raw('/receive?case=${id}',{method:'POST',body:'synthetic hostile'}).catch(()=>{});return true})()`;
   await evaluate(bridge,expression);await delay(700);const s=await state(),p=s.pending.find(p=>JSON.stringify(p).includes(id));await count(id,0);if(p)await bridge.send('Check.decide',{id:p.id,release:false});log('Q1_HOSTILE_HTTP',{id,caught:!!p,networkFallback:!!p?.network,children:s.history.filter(e=>e.method==='check.child')});
  }
  await nav();await evaluate(bridge,'connectWS().then(()=>true)');await evaluate(bridge,`__hold17.original.send.call(ws,JSON.stringify({case:'hostile-live',text:'synthetic bypass'}));true`);await count('hostile-live',1);log('Q1_HOSTILE_LIVE_COUNTEREXAMPLE',{arrivals:arrivals('hostile-live')});
  // Browser lifecycle events with actual held calls. No replay is armed.
  for(const ending of ['detach','stop','reload','update','host-loss','chrome-normal','chrome-kill','disable']){
   await nav();const id='end-'+ending;await hold(id);await count(id,0);
   if(ending==='detach')await bridge.send('Check.stop');
   if(ending==='stop'){await key('ctrl+t');await address(`chrome-extension://${extId}/popup.html`);await screenshot(out,'stop-before');await key('Return');await delay(500);}
   if(ending==='reload')await bridge.send('Check.reload');
   if(ending==='update'){packVersion('0.3.1');log('Q1_UPDATE_REQUEST',await bridge.send('Check.update'));}
   if(ending==='host-loss'){const pid=Number(fs.readFileSync(out+'/host-pids.txt','utf8').trim().split('\n').at(-1));process.kill(pid,'SIGKILL');await delay(500);}
   if(ending==='disable'){policy(false);await address('chrome://policy');await key('Tab');await key('Return');await delay(1500);}
   if(ending==='chrome-normal'||ending==='chrome-kill')await close(ending==='chrome-kill');
   await delay(700);await count(id,0);log('Q1_END',{ending,id,arrivals:arrivals(id)});await close();policy();await boot('after-'+ending);
  }
  log('Q6_INDICATORS',{state:await state()});
 }
 if(phase==='guards'){
  await nav();await bridge.send('Check.guard');
  // Page-load timer and owner-tab event flush the same shared outbox.
  await evaluate(bridge,"caseId='queue-timer';timerFlush=true;true");await click('#action');const timer=await eventually(async()=>(await state()).pending.find(p=>p.description?.url?.includes('queue-timer')),'timer queue');await count('queue-timer',0);await bridge.send('Check.decide',{id:timer.id,release:false});await assert.rejects(()=>bridge.send('Check.retire',{evidence:'dropped'}),/UNRESOLVED_SITE/);log('Q3_TIMER',{preview:timer,guardAfterDrop:(await state()).guards});
  const owner=await bridge.send('Check.open',{url:f.base+'/owner'});await delay(500);await bridge.send('Check.ownerTab',{tabId:owner.id});
  const ownerEval=async expression=>(await bridge.send('Check.ownerCommand',{method:'Runtime.evaluate',params:{expression,returnByValue:true}})).result.value;
  await ownerEval("caseId='queue-owner';true");assert.equal((await bridge.send('Check.tabs')).find(t=>t.id===owner.id).groupId,-1);
  // Use X input on the owner's tab, not a tool-dispatched CDP event.
  await bridge.send('Check.ownerCommand',{method:'Page.bringToFront'});const box=await ownerEval("(()=>{const b=document.querySelector('#flush').getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2}})()");const screen=await ownerEval('({x:screenX,y:screenY,top:outerHeight-innerHeight})');x('mousemove',Math.round(screen.x+box.x),Math.round(screen.y+screen.top+box.y),'click',1);
  const own=await eventually(async()=>(await state()).pending.find(p=>p.description?.url?.includes('queue-owner')),'owner flush held');await count('queue-owner',0);log('Q3_OWNER_HELD',{preview:own,notifications:(await state()).history.filter(r=>r.method==='check.notification')});
  await evaluate(bridge,`postMessage({decision:'send',id:${JSON.stringify(own.id)}},'*');true`);await bridge.send('Check.contentForge',{id:own.id});await key('ctrl+t');await address(`chrome-extension://${extId}/other.html?id=${encodeURIComponent(own.id)}`);await key('Return');await delay(300);await count('queue-owner',0);assert.ok((await state()).pending.some(p=>p.id===own.id));
  const details=await bridge.send('Check.details',{id:own.id});await delay(500);await screenshot(out,'owner-details');await assert.rejects(()=>bridge.send('Check.attach',{tabId:details.id}),/FORBIDDEN_PAGE/);await assert.rejects(()=>bridge.send('Check.open',{url:'chrome://settings/'}),/FORBIDDEN_PAGE/);await assert.rejects(()=>bridge.send('Check.open',{url:`chrome-extension://${extId}/details.html`}),/FORBIDDEN_PAGE/);
  await key('Return');await delay(500);await count('queue-owner',1);log('Q3_GENUINE_OWNER',{arrivals:arrivals('queue-owner'),refused:(await state()).history.filter(r=>r.method==='check.forgeryRefused')});
  // Dedicated/shared/service worker first-script coverage is an observation, not a premise.
  await nav();
  for(const kind of ['dedicated','shared','service']){
   const id='worker-'+kind;await evaluate(bridge,kind==='service'?`navigator.serviceWorker.register('/sw.js?case=${id}').then(()=>true)` :kind==='shared'?`window.shared=new SharedWorker('/worker.js?type=shared&case=${id}');shared.port.start();true`:`window.worker=new Worker('/worker.js?case=${id}');true`);await delay(1200);
   const s=await state(),p=s.pending.find(p=>JSON.stringify(p).includes(id));const before=arrivals(id).length;assert.ok(before<=1);if(p){assert.equal(before,0);await bridge.send('Check.decide',{id:p.id,release:false});}audit.set(id,before);log('Q1_WORKER_START',{kind,before,held:!!p,preview:p,targets:await bridge.send('Check.targets'),children:s.history.filter(r=>r.method==='check.child'||r.method==='check.childError')});
  }
  // Message-counting rule: four distinct messages, only one contains the typed text.
  await nav();await evaluate(bridge,"connectWS().then(()=>{caseId='chat';document.querySelector('#text').value='Synthetic17c';return true})");await click('#chat');await evaluate(bridge,"document.querySelector('#text').focus();true");await bridge.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await bridge.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await delay(300);const messages=(await state()).pending.filter(p=>p.kind==='ws');assert.equal(messages.length,4);assert.equal(messages.filter(p=>p.description.body.includes('Synthetic17c')).length,1);for(const p of messages){const id=JSON.parse(p.description.body).case;await count(id,0);await bridge.send('Check.decide',{id:p.id,release:false});}log('Q2_CHAT',{onlyText:1,allAfterActing:4,messages});
  // Trace initiators without substituting the coarse guard for attribution evidence.
  const traces=[];
  for(const kind of ['sync','timer','promise','mutation','postMessage','worker']){
   await nav();const id='cause-'+kind;await evaluate(bridge,`causeTest('${kind}','${id}');true`);const offset=(await state()).history.length;await click('#cause');await delay(600);const s=await state(),p=s.pending.find(p=>JSON.stringify(p).includes(id)&&!JSON.stringify(p).includes(id+'-first'));assert.ok(p,'cause held '+kind);await count(id,0);
   // Release the wrapper only into a deliberately denied network gate to obtain CDP initiators.
   if(!p.network){await evaluate(bridge,`__hold17.decide(${JSON.stringify(p.localId)},true);true`);await delay(400);}
   const events=(await state()).history.slice(offset).filter(r=>r.method==='check.initiator'&&r.params.url.includes(id));const correct=events.some(e=>JSON.stringify(e.params.initiator).includes('action17c'));traces.push({kind,correct,unknown:!correct,pageOwned:false,events,wrapperStack:p.stack});await dropAll();
  }
  log('Q4_CAUSES',{correct:traces.filter(t=>t.correct).length,total:traces.length,falsePage:0,traces});
  // Existing live object before attachment: remove cooperative wrap, then reattach inventory.
  await nav();await evaluate(bridge,"connectWS().then(()=>{WebSocket.prototype.send=__hold17.original.send;return true})");await bridge.send('Check.stop');await bridge.send('Check.attach',{tabId:selected});const proto=(await bridge.send('Runtime.evaluate',{expression:'WebSocket.prototype'})).result.objectId;const objects=(await bridge.send('Runtime.queryObjects',{prototypeObjectId:proto})).objects.objectId;const inventory=await bridge.send('Runtime.callFunctionOn',{objectId:objects,functionDeclaration:'function(){return this.map(s=>({url:s.url,state:s.readyState}))}',returnByValue:true});await evaluate(bridge,"ws.send(JSON.stringify({case:'preattach-live',text:'synthetic old'}));true");await count('preattach-live',1);await nav();await evaluate(bridge,'connectWS().then(()=>true)');const reloaded=await hold('postreload-live','ws');await count('postreload-live',0);await bridge.send('Check.decide',{id:reloaded.id,release:false});log('Q2_PREATTACH',{inventory,oldArrivals:arrivals('preattach-live'),reloadHeld:true});
  await nav(f.base+'/startup');await delay(500);await dropAll();await close();await boot('restart',true);await delay(1000);const rs=await state();assert.ok(rs.guards.includes(f.base));const rp=rs.pending.filter(p=>JSON.stringify(p).includes('restored-startup'));await count('restored-startup',0);log('Q3_RESTART',{guards:rs.guards,pending:rp,history:rs.history,targets:await bridge.send('Check.targets')});await dropAll();await bridge.send('Check.retire',{evidence:'adapter-resolved-all'});assert.equal((await state()).guards.length,0);log('Q3_RETIRE',{guardCount:0});
 }
 if(phase==='public'){
  await bridge.send('Check.public');await bridge.send('Network.setBypassServiceWorker',{bypass:true});await bridge.send('Page.addScriptToEvaluateOnNewDocument',{source:"for(const name of ['WebTransport','RTCPeerConnection'])Object.defineProperty(window,name,{value:class{constructor(){throw Error('Disabled for public check')}},configurable:false});"});
  const sites=[['github','https://github.com/microsoft/playwright','a#issues-tab'],['wikipedia','https://en.wikipedia.org/wiki/Web_browser','a[href="#History"]'],['youtube','https://www.youtube.com/watch?v=jNQXAC9IVRw','#expand'],['news','https://www.bbc.com/news','a[href="/news/world"]'],['amazon','https://www.amazon.com/dp/B0BDJ279KF','a[href="#customerReviews"]'],['reddit','https://www.reddit.com/r/programming/','button[aria-label="Expand navigation"]'],['stackoverflow','https://stackoverflow.com/questions/11227809/why-is-processing-a-sorted-array-faster-than-processing-an-unsorted-array','a[href="#answers"]'],['notion','https://www.notion.so/Notion-Template-Gallery-ef294a95e1a048b782c4e5366d3e1e2a','button[aria-label="Open sidebar"]'],['docs','https://docs.google.com/document/d/1ZWDFrVQ6xnmI6pC1PXqVk_zK6Hj37LRwDjAK3gx4J0Y/edit','[aria-label="View"]'],['search','https://www.google.com/search?q=web+browser','a[href*="tbm=nws"]']];
  for(const [name,url,selector]of sites)await probe('Q5_SITE',async()=>{const start=(await state()).history.length;await nav(url);await delay(4500);const snapshot=()=>evaluate(bridge,`({url:location.href,title:document.title,text:document.body?.innerText.slice(0,900),forms:document.forms.length,controller:navigator.serviceWorker?.controller?.scriptURL||null,wrapFailures:globalThis.__hold17?.failures,held:globalThis.__hold17?.pending.size})`);const rest=await snapshot();const middle=(await state()).history.length;const action=await evaluate(bridge,`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)return {found:false,selector:${JSON.stringify(selector)}};const text=e.innerText||e.getAttribute('aria-label');e.click();return {found:true,text}})()`);await delay(2200);const after=await snapshot(),s=await state();const traffic=s.history.slice(start).filter(e=>e.method==='check.public'),held=s.pending.filter(p=>!p.network);const row={name,url,rest,action,after,atRest:traffic.filter(e=>s.history.indexOf(e)<middle).length,afterClick:traffic.filter(e=>s.history.indexOf(e)>=middle).length,blocked:traffic.filter(e=>e.params.block).length,post:traffic.filter(e=>e.params.method==='POST').length,graphql:traffic.filter(e=>/graphql/i.test(e.params.url)).length,live:s.history.slice(start).filter(e=>/WebSocket|webTransport/i.test(e.method)),serviceWorkers:(await bridge.send('Check.targets')).filter(t=>/worker/.test(t.type)),inPageHeld:held.length,traffic};save('public-'+name,row);await screenshot(out,'public-'+name);await dropAll();return row;});
  // Public demo: synthetic data only, requests aborted. Compare actual network candidates three times.
  const repeats=[];for(let i=0;i<3;i++){await nav('https://www.selenium.dev/selenium/web/web-form.html');await delay(1200);await evaluate(bridge,"document.querySelector('input[name=\"my-text\"]').value='Synthetic17c';document.forms[0].requestSubmit();true");const p=await eventually(async()=>(await state()).pending.find(p=>p.kind==='form'),'public demo form');assert.ok(!p.network);const before=await evaluate(bridge,'({url:location.href,text:document.body.innerText.slice(0,150)})');const offset=(await state()).history.length;await bridge.send('Check.decide',{id:p.id,release:true});await delay(800);const candidates=(await state()).history.slice(offset).filter(e=>e.method==='check.public'&&e.params.url.includes('submitted-form'));assert.equal(candidates.length,1);assert.ok(candidates[0].params.block||candidates[0].params.method==='GET');repeats.push({before,candidate:candidates[0].params});}
  assert.ok(repeats.every(r=>r.candidate.block));log('Q1_PUBLIC_DEMO',{repeats});
 }
 if(bridge)save('extension-final',await state());await close();await delay(500);
 const rows=[...audit].map(([id,expected])=>({id,expected,actual:arrivals(id).length}));save('delivery-audit',rows);for(const r of rows)assert.equal(r.actual,r.expected,r.id);log('FINAL_DELIVERY_AUDIT',{status:'PASS',cases:rows.length});console.log('ALL 17C CHECKS COMPLETE');
}finally{if(bridge)await state().then(s=>save('extension-on-exit',s)).catch(()=>{});await screenshot(out,'final').catch(()=>{});await close();wt?.kill();f.close();save('summary',summary);}
