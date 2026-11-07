import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {generateKeyPairSync} from 'node:crypto';
import {execFileSync,spawn} from 'node:child_process';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true')throw Error('Browser runs only on GitHub Linux runners');
const here=path.resolve('control/checks/17b-chrome'),work=path.resolve('.work/17b-chrome'),out=work+'/artifacts';
fs.mkdirSync(out,{recursive:true});
const {fixture}=await import('./fixture.mjs');
const {address,key,delay,activateChrome,screenshot,x}=await import('../17-chrome/ui.mjs');
const {nativeBridge,evaluate,eventually}=await import('../17-chrome/protocol.mjs');
const {pack,idFor,installExternal}=await import('../17-chrome/install.mjs');
const phase=process.env.CHECK_PHASE||'all';
const summary={phase,longHold:process.env.LONG_HOLD==='true',run:process.env.GITHUB_RUN_ID,head:process.env.GITHUB_SHA,cases:[]},audit=new Map(),networkStarts=[];
const save=(n,v)=>fs.writeFileSync(out+'/'+n+'.json',JSON.stringify(v,null,2));
function log(name,row){summary.cases.push({name,...row});save('summary',summary);console.log(name,JSON.stringify(row));}
async function probe(name,fn){try{const row=await fn();log(name,{status:'observed',...row});return row;}catch(e){log(name,{status:'probe-error',error:e.stack});return {error:e.message};}}
let activeProfile=work+'/profile';
let updateVersion='0.2.0',id,chrome,bridge,selected,group;
const wt=spawn(work+'/venv/bin/python',[here+'/webtransport.py',work],{stdio:['ignore',fs.openSync(out+'/webtransport.log','a'),fs.openSync(out+'/webtransport.log','a')]});
await eventually(()=>fs.existsSync(work+'/webtransport.json'),'WebTransport receiver');
const wtInfo=JSON.parse(fs.readFileSync(work+'/webtransport.json'));save('webtransport-certificate',wtInfo);
const f=await fixture(out,work,()=>`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${id}"><updatecheck codebase="${f.base}/extension.crx" version="${updateVersion}"/></app></gupdate>`);
const ext=work+'/extension';fs.cpSync(here+'/extension',ext,{recursive:true});
const kp=generateKeyPairSync('rsa',{modulusLength:2048});id=idFor(kp.publicKey.export({type:'spki',format:'der'}));
function packVersion(v){updateVersion=v;const m=JSON.parse(fs.readFileSync(ext+'/manifest.json'));m.version=v;m.update_url=f.base+'/update.xml';m.key=kp.publicKey.export({type:'spki',format:'der'}).toString('base64');fs.writeFileSync(ext+'/manifest.json',JSON.stringify(m));pack(ext,work,kp);}
packVersion(updateVersion);
const socket=work+'/native.sock';process.env.CHROME_CHECK_SOCKET=socket;
const hostName='org.aresos.chrome_check',hostPath=path.resolve('control/checks/17-chrome/native-host.py');
for(const label of ['system','user']){
  const script=work+'/host-'+label;fs.writeFileSync(script,`#!/bin/sh\nprintf '%s\\n' '${label}' >> '${out}/host-starts.txt'\nprintf '%s\\n' "$$" >> '${out}/host-pids.txt'\nexec python3 '${hostPath}'\n`,{mode:0o755});
  const h={name:hostName,description:'17b CI check',path:script,type:'stdio',allowed_origins:[`chrome-extension://${id}/`]};
  const temp=work+'/host-'+label+'.json';fs.writeFileSync(temp,JSON.stringify(h));
  if(label==='system')execFileSync('sudo',['install','-D','-m','644',temp,'/etc/opt/chrome/native-messaging-hosts/'+hostName+'.json']);
  else {for(const d of [process.env.XDG_CONFIG_HOME+'/google-chrome/NativeMessagingHosts',work+'/profile/NativeMessagingHosts']){fs.mkdirSync(d,{recursive:true});fs.copyFileSync(temp,d+'/'+hostName+'.json');}}
}
function policy(userHosts,forced=true){const p={ExtensionInstallForcelist:forced?[id+';'+f.base+'/update.xml']:[],ExtensionInstallBlocklist:['fcoeoabgfenejglbffodgkkbkcdhcgfn'],NativeMessagingUserLevelHosts:userHosts};const file=work+'/policy.json';fs.writeFileSync(file,JSON.stringify(p));execFileSync('sudo',['install','-D','-m','644',file,'/etc/opt/chrome/policies/managed/aresos-17b.json']);save('policy-'+userHosts,p);}
policy(true);
async function stop(kill=false){
 if(chrome?.exitCode===null){
   if(kill){chrome.kill('SIGKILL');try{execFileSync('pkill',['-KILL','-f',activeProfile],{stdio:'ignore'});}catch{}}
   else{await activateChrome();await key('alt+F4');await delay(2000);if(chrome.exitCode===null){log('NORMAL_CLOSE_FALLBACK',{signal:'SIGTERM'});chrome.kill('SIGTERM');}}
   await delay(600);
 }
 bridge?.close();bridge=undefined;chrome=undefined;
}
async function boot(label){
 bridge=await nativeBridge(socket);
 const args=[`--user-data-dir=${activeProfile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode',f.base+'/'];
 save('chrome-'+label+'-args',args);const fd=fs.openSync(out+'/chrome-'+label+'.log','a');chrome=spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});
 await activateChrome();await delay(5000);await screenshot(out,'boot-'+label);await connect();
}
async function connect(){
  const conn=new Promise(r=>bridge.once('check.connected',r));
  await key('ctrl+t');await address(`chrome-extension://${id}/select.html?url=${encodeURIComponent(f.base+'/')}`);await key('Return');
  const c=await Promise.race([conn,delay(10000).then(()=>{throw Error('Extension failed to connect')})]);selected=c.tabId;group=c.group;
  await bridge.send('Check.enableGate');await bridge.send('Check.config',{});await bridge.send('Network.setBypassServiceWorker',{bypass:true});
  bridge.on('Network.requestWillBeSent',p=>networkStarts.push({at:Date.now(),url:p.request.url,method:p.request.method}));
  log('CONNECTED',{...c,host:fs.readFileSync(out+'/host-starts.txt','utf8').trim().split('\n').at(-1)});
}
function measureSettle(start,requests){let end=start+500;for(const r of requests.filter(r=>r.at>=start).sort((a,b)=>a.at-b.at)){if(r.at>end)break;end=Math.min(start+10000,r.at+500);}return end;}
const state=()=>bridge.send('Check.state');
const arrivals=id=>f.arrivals.filter(r=>r.kind==='receive'&&new URL(r.url,f.base).searchParams.get('case')===id);
async function nav(){await bridge.send('Page.bringToFront');await bridge.send('Page.navigate',{url:f.base+'/'});await delay(500);await eventually(()=>evaluate(bridge,"typeof send==='function'"),'fixture ready');}
async function held(id,kind='fetch',timeout=0){await evaluate(bridge,`send(${JSON.stringify(id)},${JSON.stringify(kind)},${timeout});'started'`);return eventually(async()=>{const s=await state();if(s.errors.length)throw Error(s.errors.join(';'));return s.pending.find(p=>p.url.includes('case='+id));},'held '+id);}
async function decide(p,release){return bridge.send('Check.decide',{id:p.id,release});}
async function inventory(constructor,body){
 const objectGroup='17b-inventory';
 try{
   const proto=(await bridge.send('Runtime.evaluate',{expression:constructor+'.prototype',objectGroup})).result.objectId;
   const objects=(await bridge.send('Runtime.queryObjects',{prototypeObjectId:proto,objectGroup})).objects.objectId;
   const result=await bridge.send('Runtime.callFunctionOn',{objectId:objects,functionDeclaration:body,returnByValue:true,awaitPromise:true});
   if(result.exceptionDetails)throw Error(JSON.stringify(result.exceptionDetails));return result.result.value;
 }finally{await bridge.send('Runtime.releaseObjectGroup',{objectGroup});}
}
async function dropCanceled(p){
 try{return await decide(p,false)}catch(e){const failed=(await state()).history.find(r=>r.method==='check.networkFailed'&&r.params.event.requestId===p.networkId&&r.params.event.canceled);if(!e.message.includes('Invalid InterceptionId')||!failed)throw e;log('ALREADY_CANCELED',{preview:p,failed});}
}
async function observe(id,expected){await delay(650);const a=arrivals(id);if(expected!==undefined){assert.equal(a.length,expected,id);audit.set(id,expected);}return a;}
async function matrix(label,action,{backstop=false,expected}={}){await nav();await bridge.send('Check.config',{backstop});const id='q1-'+label+(backstop?'-dnr':'');const p=await held(id);assert.equal(arrivals(id).length,0);save(id+'-held',await state());await action(p);await delay(1200);let after;try{after=bridge?await state():null}catch(e){after={transportError:e.message}}save(id+'-after',after);const a=await observe(id,expected);audit.set(id,a.length);log('Q1_'+label+(backstop?'_DNR':''),{id,preview:p,arrivals:a,detachEvents:after?.history?.filter(r=>['check.detached','check.controlEnded'].includes(r.method))});return a;}
try{
 await boot('initial');
 await screenshot(out,'policy-debug-bar');
 const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);const listeners=execFileSync('ss',['-lntp'],{encoding:'utf8'}).split('\n').filter(l=>l.includes('\"chrome\"'));assert.equal(listeners.length,0);save('processes',{processes,listeners});
 await key('ctrl+t');await address('chrome://sandbox');await screenshot(out,'sandbox-status');await key('ctrl+w');
 log('Q5_POLICY_INSTALL',{info:await bridge.send('Check.info'),policy:JSON.parse(fs.readFileSync(work+'/policy.json'))});
 await address('chrome://extensions/?id='+id);await screenshot(out,'policy-extension-controls');x('mousemove',1025,225,'click',1);await delay(300);assert.equal((await bridge.send('Check.info')).enabled,true);await screenshot(out,'policy-user-disable-refused');
 await key('ctrl+t');await address('https://chromewebstore.google.com/detail/claude/fcoeoabgfenejglbffodgkkbkcdhcgfn');await delay(2500);await screenshot(out,'claude-blocklisted');await key('ctrl+w');
 log('Q5_HOST_DEFAULT',{starts:fs.readFileSync(out+'/host-starts.txt','utf8')});
 await stop();policy(false);await boot('system-host');
 log('Q5_HOST_POLICY_FALSE',{starts:fs.readFileSync(out+'/host-starts.txt','utf8')});
 if(['all','safety'].includes(phase)){
 // A self-disable API can differ from the policy-disabled owner UI. Measure it.
 for(const op of ['disable','uninstall']){
   await matrix('policy-'+op,async()=>{await bridge.send(op==='disable'?'Check.disable':'Check.uninstall').catch(e=>log('Q1_POLICY_END',{op,error:e.message}));await screenshot(out,'policy-'+op);});
   await stop();await boot('after-policy-'+op);
 }
 await nav();await bridge.send('Check.config',{backstop:true});const dnrRelease=await held('dnr-approved-release');assert.equal(arrivals('dnr-approved-release').length,0);await decide(dnrRelease,true);log('Q1_DNR_APPROVED',{arrivals:await observe('dnr-approved-release',1)});
 await nav();const dnrDrop=await held('dnr-explicit-drop');await decide(dnrDrop,false);log('Q1_DNR_DROP',{arrivals:await observe('dnr-explicit-drop',0)});
 // Q1: controlled detach probes, with a fresh tab attachment between each.
 await matrix('host-dies',async()=>{const pid=Number(fs.readFileSync(out+'/host-pids.txt','utf8').trim().split('\n').at(-1));process.kill(pid,'SIGKILL');},{expected:0});
 await stop();await boot('after-host');
 await matrix('service-socket',async()=>{bridge.close();bridge=undefined;},{expected:0});
 await stop();await boot('after-socket');
 for(const backstop of [false,true]){
   await matrix('detach',()=>bridge.send('Check.detach'),{backstop});
   await bridge.send('Check.attach',{tabId:selected});
   if(backstop){const before=arrivals('q1-detach-dnr').length;await evaluate(bridge,"send('q1-detach-dnr');'new request'");await delay(700);assert.equal(arrivals('q1-detach-dnr').length,before);log('Q1_DNR_NEW_REQUEST',{before,after:arrivals('q1-detach-dnr').length,rules:(await state()).rules});}
   await bridge.send('Check.enableGate');
   await matrix('reload',async()=>{await bridge.send('Check.reload');await delay(1200);},{backstop});
   await stop();await boot('after-reload-'+backstop);
   await matrix('devtools',async()=>{await bridge.send('Page.bringToFront');await key('ctrl+shift+i');await delay(1200);await screenshot(out,'devtools-'+backstop);await key('ctrl+shift+i');},{backstop});
   // Native port survives the tab debugger being replaced.
   await stop();await boot('after-devtools-'+backstop);

 }
 log('Q1_MANAGED_BAR',{shown:false,evidence:'policy-debug-bar.png; no owner Cancel UI on force-installed extension'});
 await stop();policy(false,false);installExternal(id,updateVersion,work+'/own-extension.crx',work);activeProfile=work+'/nonforced-profile';await boot('nonforced-cancel');
 log('Q1_NONFORCED_INSTALL',{info:await bridge.send('Check.info')});
 for(const backstop of [false,true]){
   await matrix('cancel',async()=>{await bridge.send('Page.bringToFront');await screenshot(out,'before-cancel-'+backstop);x('mousemove',960,115,'click',1);await delay(500);await screenshot(out,'after-cancel-'+backstop);await eventually(async()=>(await state()).history.some(r=>r.method==='check.detached'&&r.params.reason==='canceled_by_user'),'Cancel really detached');},{backstop});
   await stop();await boot('after-cancel-'+backstop);
 }
 for(const op of ['disable','uninstall']){
   await matrix('nonforced-'+op,async()=>{await bridge.send(op==='disable'?'Check.disable':'Check.uninstall').catch(e=>log('Q1_NONFORCED_END',{op,error:e.message}));await screenshot(out,'nonforced-'+op);});
   await stop();policy(false);activeProfile=work+'/profile';await boot('restore-managed-'+op);
   if(op==='disable'){await stop();policy(false,false);activeProfile=work+'/nonforced-remove-profile';await boot('nonforced-remove');}
 }

 await matrix('tab-close',()=>bridge.send('Check.closeTab'),{expected:0});await stop();await boot('after-tab');
 await matrix('chrome-normal',()=>stop(),{expected:0});await boot('after-normal');
 await matrix('chrome-kill',()=>stop(true),{expected:0});await boot('after-kill');
 await probe('Q1_STOP_WORKER',async()=>{
   const p=await held('q1-worker-stop');const before=await bridge.send('Check.targets');
   const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'}).split('\n').filter(l=>l.includes('--extension-process'));
   assert.ok(processes.length,'extension worker renderer exists');save('worker-stop-before',{p,before,processes});
   for(const line of processes)process.kill(Number(line.trim().split(/\s+/)[0]),'SIGKILL');
   await delay(1200);const received=await observe('q1-worker-stop');
   await screenshot(out,'worker-stopped');audit.set('q1-worker-stop',received.length);log('Q1_WORKER_STOP_DELIVERY',{before,preview:p,arrivals:received});
   await connect();const after=await bridge.send('Check.targets');return {before,after,state:await state(),arrivals:await observe('q1-worker-stop',received.length)};
 });
 await stop();await boot('after-worker-stop');
 await matrix('policy-update',async()=>{packVersion('0.2.1');log('Q5_UPDATE_CHECK',await bridge.send('Check.update'));await delay(4000);});
 await stop();await boot('after-update');
 log('Q5_UPDATED',{version:(await state()).version,updates:f.arrivals.filter(r=>['update','crx'].includes(r.kind))});
 // Repeat instead of preserving an in-flight request. Compare before permitting one exact match.
 await nav();await bridge.send('Check.config',{mode:'repeat'});
 const repeated=[];bridge.on('check.repeated',r=>repeated.push(r));
 for(const kind of ['fetch','xhr','form','volatile']){
   await nav();const id='repeat-'+kind;for(let i=0;i<3;i++){await nav();await evaluate(bridge,`send('${id}','${kind}');'ok'`);await delay(400);}
   const rows=repeated.filter(r=>r.url.includes('case='+id));assert.equal(rows.length,3);assert.equal(arrivals(id).length,0);
   const first=rows[0],same=r=>r.url===first.url&&r.method===first.method&&r.body===first.body&&r.headerHash===first.headerHash;
   const normalized=r=>{if(kind!=='volatile')return r.body;const o=JSON.parse(r.body);delete o.nonce;return JSON.stringify(o)};
   const byteMatches=rows.filter(same).length,normalizedMatches=rows.filter(r=>r.url===first.url&&r.method===first.method&&r.headerHash===first.headerHash&&normalized(r)===normalized(first)).length;
   assert.equal(normalizedMatches,3);if(kind!=='volatile')assert.equal(byteMatches,3);
   if(kind==='fetch'){await bridge.send('Check.detach');log('Q1_REPEAT_DETACH',{arrivals:await observe(id,0)});await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');}
   await nav();await bridge.send('Check.arm',{url:first.url,method:first.method,body:first.body,headerHash:first.headerHash});await evaluate(bridge,`send('${id}','${kind}');'ok'`);await observe(id,kind==='volatile'?0:1);
   await nav();await evaluate(bridge,`send('${id}','${kind}');'duplicate replay'`);await observe(id,kind==='volatile'?0:1);const all=repeated.filter(r=>r.url.includes('case='+id));assert.equal(all.filter(r=>r.allowed).length,kind==='volatile'?0:1);
   log('Q1_REPEAT',{kind,attempts:rows,approvedAttempts:all.filter(r=>r.allowed),duplicateBlocked:!all.at(-1).allowed,comparisons:rows.length-1,byteMatches:byteMatches-1,normalizedMatches:normalizedMatches-1,ignoredFields:kind==='volatile'?['nonce']:[],arrivals:arrivals(id)});

 }
 await bridge.send('Check.config',{});await nav();
 }
 if(['all','workers-long'].includes(phase)){
 // Q2: page through worker, worker target, bypass, and background sync.
 await bridge.send('Network.setBypassServiceWorker',{bypass:false});await evaluate(bridge,'worker()');
 log('Q2_WORKER_CONTROLLED',{controlled:await evaluate(bridge,'!!navigator.serviceWorker.controller')});
 const targets=await bridge.send('Check.targets');save('targets',targets);
 const worker=targets.find(t=>['worker','service_worker'].includes(t.type)&&t.url===f.base+'/sw.js');
 if(worker){
   await probe('Q2_WORKER_ATTACH',()=>bridge.send('Check.workerAttach',{targetId:worker.id}));
   for(const kind of ['fetch','xhr','form'])for(const release of [true,false]){
     await nav();await evaluate(bridge,'worker()');const id='sw-page-'+kind+'-'+release;
     await evaluate(bridge,`send('${id}','${kind}');'ok'`);await delay(600);let s=await state();let p=s.pending.find(p=>p.url.includes('case='+id));
     const heldBefore=arrivals(id).length;
     // A page pause may precede a separate worker pause. Drain only this case.
     if(p)await decide(p,release);await delay(500);s=await state();for(const q of s.pending.filter(q=>q.url.includes('case='+id)))await decide(q,release);
     const a=await observe(id);if(p){assert.equal(heldBefore,0);assert.equal(a.length,release?1:0);audit.set(id,release?1:0);}
     log('Q2_PAGE_SW',{id,kind,release,preview:p,held:!!p,heldBefore,arrivals:a,states:kind==='form'?await evaluate(bridge,'({url:location.href,title:document.title,text:document.body.innerText.slice(0,300)})').catch(e=>({error:e.message})):await evaluate(bridge,'states')});
   }
   for(const release of [true,false]){
     await nav();await evaluate(bridge,'worker()');const id='sw-own-'+release;
     await evaluate(bridge,`navigator.serviceWorker.controller.postMessage({url:'${f.base}/receive?case=${id}'});'ok'`);await delay(500);
     const p=(await state()).pending.find(p=>p.url.includes(id));const before=arrivals(id).length;if(p)await decide(p,release);if(p&&!release)syncDroppedAt=Date.now();const a=await observe(id);if(p){assert.equal(before,0);assert.equal(a.length,release?1:0);audit.set(id,release?1:0);}
     log('Q2_OWN_SW',{id,release,preview:p,held:!!p,before,arrivals:a});
   }
 }
 let syncDroppedAt;
 for(const release of [true,false])await probe('Q2_SYNC',async()=>{await nav();await evaluate(bridge,'worker()');const id='sw-sync-'+release;const supported=await evaluate(bridge,`navigator.serviceWorker.ready.then(async r=>{if(!r.sync)return false;await r.sync.register('${id}');return true})`);await delay(2500);const p=(await state()).pending.find(p=>p.url.includes(id));const before=arrivals(id).length;if(p)await decide(p,release);if(p&&!release)syncDroppedAt=Date.now();const a=await observe(id);if(p){assert.equal(before,0);assert.equal(a.length,release?1:0);audit.set(id,release?1:0);}return {id,release,supported,held:!!p,before,arrivals:a};});
 await bridge.send('Network.setBypassServiceWorker',{bypass:true});
 for(const kind of ['fetch','xhr','form'])for(const release of [true,false]){await nav();const id='bypass-'+kind+'-'+release;const p=await held(id,kind);assert.equal(arrivals(id).length,0);await decide(p,release);log('Q2_BYPASS',{id,release,arrivals:await observe(id,release?1:0)});}
 await bridge.send('Network.setBypassServiceWorker',{bypass:false});await nav();await evaluate(bridge,'worker()');const workerOnly=await evaluate(bridge,"fetch('/worker-only').then(r=>r.text())");await bridge.send('Network.setBypassServiceWorker',{bypass:true});const bypassOnly=await evaluate(bridge,"fetch('/worker-only').then(r=>r.text())");assert.equal(workerOnly,'worker-only fixture response');assert.equal(bypassOnly,'not provided without worker');log('Q2_BYPASS_BREAK',{workerOnly,bypassOnly});
 // Q3: run waits concurrently; the single 10-minute hold belongs only to final verification.
 await nav();await bridge.send('Check.config',{});
 const durations=[30000,120000,...(process.env.LONG_HOLD==='true'?[600000]:[])];
 const holdRows=[];
 for(const ms of durations){const id='long-'+ms,p=await held(id);holdRows.push({id,ms,p,start:Date.now()});}
 const abort=await held('long-abort','fetch',30000),xhr=await held('long-xhr','xhr',30000);
 await evaluate(bridge,"retry('long-retry');'ok'");await eventually(async()=>(await state()).pending.filter(p=>p.url.includes('case=long-retry')).length===2,'second retry held',8000);
 save('long-before-retry-decision',{state:await state(),page:await evaluate(bridge,'states')});
 const retries=(await state()).pending.filter(p=>p.url.includes('case=long-retry'));assert.equal(retries.length,2);assert.equal(arrivals('long-retry').length,0);
 await dropCanceled(retries[0]);assert.equal(arrivals('long-retry').length,0);await decide(retries[1],true);await observe('long-retry',1);log('Q3_RETRY',{pending:retries,arrivals:arrivals('long-retry')});
 for(const row of holdRows){await delay(Math.max(0,row.ms-(Date.now()-row.start)));assert.equal(arrivals(row.id).length,0);await decide(row.p,true);log('Q3_LONG',{id:row.id,requestedMs:row.ms,heldMs:Date.now()-row.start,arrivals:await observe(row.id,1)});}
 for(const [id,p]of [['long-abort',abort],['long-xhr',xhr]]){const result=await probe('Q3_CANCELED_RELEASE_'+id,()=>decide(p,true));log('Q3_CANCELED',{id,result,arrivals:await observe(id,0)});}
 log('Q3_PAGE_STATES',{states:await evaluate(bridge,'states')});
 // Form stays pending for 30 seconds, then completes one navigation.
 await nav();const form=await held('long-form','form');await screenshot(out,'long-form-held');await delay(30000);assert.equal(arrivals('long-form').length,0);await decide(form,true);await observe('long-form',1);await screenshot(out,'long-form-released');log('Q3_FORM',{arrivals:arrivals('long-form')});
 await nav();
 assert.ok(syncDroppedAt,'background sync drop was exercised');
 const retry=await eventually(async()=>(await state()).history.find(r=>r.method==='check.retryDropped'&&r.params.url.includes('case=sw-sync-false')),'natural background-sync retry failed immediately',Math.max(1000,360000-(Date.now()-syncDroppedAt)));
 assert.equal((await state()).pending.filter(p=>p.url.includes('case=sw-sync-false')).length,0);
 log('Q2_NATURAL_RETRY',{afterDropMs:retry.at-syncDroppedAt,retry,arrivals:await observe('sw-sync-false',0)});
 }
 if(['all','live-public'].includes(phase)){
 // Q4 detection and handshake: event history is independent of the Fetch gate.
 const events=[];bridge.on('event',e=>{if(/WebSocket|webTransport|dataChannel|peerConnection/i.test(e.method))events.push({at:Date.now(),...e});});
 await evaluate(bridge,"connectWS();'ok'");await delay(1200);const wsState=await state(),wsPending=wsState.pending.filter(p=>p.url.endsWith('/socket'));if(wsPending.length){assert.equal(f.arrivals.filter(r=>r.kind==='ws-open').length,0);await decide(wsPending[0],false);log('Q4_WS_HANDSHAKE_DROP',{arrivals:f.arrivals.filter(r=>r.kind==='ws-open')});await evaluate(bridge,"connectWS();'ok'");const again=await eventually(async()=>(await state()).pending.find(p=>p.url.endsWith('/socket')),'second handshake');await decide(again,true);await delay(500);}
 log('Q4_WS_HANDSHAKE',{pending:wsPending,socketPauses:wsState.history.filter(r=>r.method==='check.socketPause'),server:f.arrivals.filter(r=>r.kind==='ws-open'),events:events.slice()});
 await evaluate(bridge,"ws.send('synthetic socket');'ok'");await delay(400);
 await bridge.send('Check.detach');await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');events.length=0;await delay(500);
 const oldSocket=await evaluate(bridge,'ws.readyState');const wsInventory=await probe('Q4_WS_IDLE_INVENTORY',()=>inventory('WebSocket','function(){return this.map(x=>({url:x.url,readyState:x.readyState}))}'));await evaluate(bridge,"ws.send('synthetic preattach');'ok'");await delay(400);
 log('Q4_WS_PREATTACH',{readyState:oldSocket,inventory:wsInventory,events:events.slice(),server:f.arrivals.filter(r=>r.kind.startsWith('ws'))});
 await probe('Q4_WEBRTC',async()=>{const media=await probe('Q4_MEDIA_DOMAIN',()=>bridge.send('Media.enable'));await evaluate(bridge,'rtc()');await eventually(()=>evaluate(bridge,"channel.readyState==='open'"),'RTC open');await evaluate(bridge,"channel.send('synthetic rtc');'ok'");await delay(300);const before=events.slice();await bridge.send('Check.detach');await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');const offset=events.length;const channels=await probe('Q4_RTC_IDLE_INVENTORY',()=>inventory('RTCDataChannel','function(){return this.map(x=>({label:x.label,readyState:x.readyState}))}'));await evaluate(bridge,"channel.send('synthetic preattach rtc');'ok'");await delay(300);return {media,inventory:channels,events:before,afterReattachEvents:events.slice(offset),readyState:await evaluate(bridge,'channel.readyState'),states:await evaluate(bridge,'states')};});
 await probe('Q4_WEBTRANSPORT',async()=>{const offset=events.length;await evaluate(bridge,`window.transport=new WebTransport(${JSON.stringify(wtInfo.url)},{serverCertificateHashes:[{algorithm:'sha-256',value:new Uint8Array(${JSON.stringify(wtInfo.hash)})}]});transport.ready.then(()=>mark('wt open')).catch(e=>mark(e.name));'attempted'`);await eventually(()=>evaluate(bridge,"states.some(s=>s.s==='wt open')"),'WebTransport open');await evaluate(bridge,"window.writer=transport.datagrams.writable.getWriter();writer.write(new TextEncoder().encode('synthetic transport'));'ok'");await delay(500);const before=events.slice(offset);await bridge.send('Check.detach');await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');const oldOffset=events.length;const transports=await probe('Q4_WT_IDLE_INVENTORY',()=>inventory('WebTransport',"async function(){return Promise.all(this.map(async x=>({ready:await Promise.race([x.ready.then(()=>true,()=>false),new Promise(r=>setTimeout(()=>r(null),10))]),closed:await Promise.race([x.closed.then(()=>true,()=>true),new Promise(r=>setTimeout(()=>r(false),10))])})))}"));await evaluate(bridge,"writer.write(new TextEncoder().encode('synthetic preattach transport'));'ok'");await delay(500);return {inventory:transports,events:before,afterReattachEvents:events.slice(oldOffset),states:await evaluate(bridge,'states'),server:fs.readFileSync(out+'/webtransport-server.jsonl','utf8')};});
 save('live-events',events);log('Q4_TRANSPORT_DIAGNOSTIC',{states:await evaluate(bridge,'states'),events});
 await nav();
 // Permanently watch typed text, including sends outside a 500ms settle window.
 const text='Synthetic 17b "a+b" / ✓',encoded=[text,encodeURIComponent(text),new URLSearchParams({text}).toString().slice(5),JSON.stringify(text).slice(1,-1),Buffer.from(text).toString('base64')];
 await bridge.send('Check.config',{texts:[text]});
 for(let i=0;i<encoded.length;i++)for(const wait of [5000,10000]){
   const id='typed-'+i+'-'+wait;const start=Date.now();await evaluate(bridge,`delayed('${id}',${i},${wait});document.querySelector('#text').value=${JSON.stringify(text)};document.querySelector('#text').dispatchEvent(new Event('input'));'ok'`);
   const p=await eventually(async()=>(await state()).pending.find(p=>p.url.includes('case='+id)),'delayed text',wait+5000);assert.ok(p.typed.length);assert.equal(arrivals(id).length,0);await decide(p,false);audit.set(id,0);log('Q4_TYPED',{id,encoding:i,delayMs:Date.now()-start,settleMs:measureSettle(start,networkStarts)-start,outsideSettle:p.at>measureSettle(start,networkStarts),preview:p});
 }
 const pixel='typed-image';await evaluate(bridge,`document.querySelector('#text').value=${JSON.stringify(text)};window.pixel=new Image();pixel.src='/receive?case=${pixel}&text='+encodeURIComponent(${JSON.stringify(text)});'ok'`);
 const p=await eventually(async()=>(await state()).pending.find(p=>p.url.includes(pixel)),'typed image');assert.ok(p.typed.length);await decide(p,false);await observe(pixel,0);log('Q4_TYPED_IMAGE',{preview:p});
const negative=await held('typed-negative');assert.equal(negative.typed.length,0);await decide(negative,false);await observe('typed-negative',0);log('Q4_TYPED_NEGATIVE',{preview:negative});
 // Q5 group ownership, refusal after owner ungroup, close while held.
 const opened=await bridge.send('Check.open',{url:f.base+'/new'});assert.equal(opened.groupId,group);assert.equal((await state()).groupInfo.title,'Claude');log('Q5_GROUP_OPEN',{opened,tabs:await bridge.send('Check.tabs')});
 await nav();const gp=await held('group-out');const gp2=await held('group-out-second');await screenshot(out,'group-before-drag');x('mousemove',210,20,'mousedown',1);await delay(200);x('mousemove',1050,20);await delay(600);x('mouseup',1);await delay(500);await screenshot(out,'group-after-drag');await eventually(async()=>(await bridge.send('Check.tabs')).find(t=>t.id===selected)?.groupId===-1,'owner dragged tab outside group');await assert.rejects(()=>evaluate(bridge,'document.title'),/OUTSIDE_CLAUDE_GROUP/);log('Q5_OUTSIDE_REFUSED',{refused:true});log('Q5_GROUP_OUT',{previews:[gp,gp2],arrivals:await observe('group-out',0),secondArrivals:await observe('group-out-second',0),state:await state()});
 await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');await nav();await held('group-close');await bridge.send('Check.closeGroup');log('Q5_GROUP_CLOSE',{arrivals:await observe('group-close',0)});
 await stop();await boot('public');
 // Public sites: only safe resources load; every potential text carrier is failed before sending.
 const pub=[];bridge.on('check.public',r=>pub.push({...r,at:Date.now()}));
 await bridge.send('Check.publicSocketBlock');await bridge.send('Page.addScriptToEvaluateOnNewDocument',{source:"for(const name of ['WebTransport','RTCPeerConnection'])Object.defineProperty(window,name,{value:class{constructor(){throw Error('Disabled for synthetic public check')}},configurable:false});"});
 await bridge.send('Check.config',{publicMode:true,texts:[text,'SyntheticFixture17b value+% ☃']});
 for(const [name,url]of [['wikipedia','https://en.wikipedia.org/wiki/Main_Page'],['news','https://www.bbc.com/news'],['demo','https://www.selenium.dev/selenium/web/web-form.html']]){
  await probe('Q4_PUBLIC_'+name,async()=>{const start=Date.now(),offset=pub.length;await bridge.send('Check.publicGuard',{denyAll:false});await bridge.send('Page.navigate',{url});await delay(4000);const title=await evaluate(bridge,'document.title');
   await bridge.send('Check.publicGuard',{denyAll:true});const actionStart=Date.now(),actionStarts=[actionStart];const action=await evaluate(bridge,`(()=>{const input=document.querySelector(${JSON.stringify(name==='wikipedia'?'input[name=search]':name==='demo'?'input[name="my-text"]':'input[type=search],input[type=text]')});if(!input)return {found:false};input.focus();input.value='SyntheticFixture17b value+% ☃';input.dispatchEvent(new Event('input',{bubbles:true}));input.select();return {found:true,form:!!input.form,name:input.name,type:input.type,placeholder:input.placeholder}})()`);
   if(action.found)await bridge.send('Input.insertText',{text:'SyntheticFixture17b value+% ☃'});
   if(action.found&&!action.form){await bridge.send('Input.dispatchKeyEvent',{type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await bridge.send('Input.dispatchKeyEvent',{type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});await delay(1000);}
   let repeated=[];const expected=action.found&&action.form?await evaluate(bridge,`(()=>{const f=Array.from(document.forms).find(f=>Array.from(f.elements).some(e=>e.value==='SyntheticFixture17b value+% ☃'));return f?{method:f.method.toUpperCase(),action:f.action,fields:Array.from(new FormData(f).entries())}:null})()`):null;
   if(action.found&&action.form){for(let i=0;i<(name==='demo'?3:1);i++){if(i){await bridge.send('Check.publicGuard',{denyAll:false});await bridge.send('Page.navigate',{url});await delay(1800);await bridge.send('Check.publicGuard',{denyAll:true});await evaluate(bridge,"document.querySelector('input[name=\"my-text\"]').value='SyntheticFixture17b value+% ☃';true");}if(i)actionStarts.push(Date.now());const before=pub.length;await evaluate(bridge,`(()=>{const input=document.querySelector(${JSON.stringify(name==='demo'?'input[name="my-text"]':'input[name=search]')});input.form.requestSubmit();return true})()`);await delay(700);repeated.push(pub.slice(before).filter(r=>r.typed.length));}}
   await delay(11000);const requests=pub.slice(offset);const textRequests=requests.filter(r=>r.typed.length);assert.ok(textRequests.every(r=>r.block));const canonical=r=>JSON.stringify({url:r.url,method:r.method,body:r.body,headerHash:r.headerHash});
   return {title,action,expected,observedFormMiss:expected?!textRequests.length:null,loadTypedFalseAlarms:requests.filter(r=>r.at<actionStart&&r.typed.length).length,elapsedMs:Date.now()-start,requests,textRequests:textRequests.length,ruleMisses:expected?requests.filter(r=>r.url.startsWith(expected.action)&&!r.typed.length).length:null,unlabelledRequests:requests.filter(r=>!r.typed.length).length,repeat:repeated.map(rows=>rows.map(canonical)),ignoredVolatileFields:[],actionStarts,settleWindows:actionStarts.map(start=>({start,end:measureSettle(start,networkStarts)})),outsideActionSettle:textRequests.filter(r=>r.at>measureSettle(actionStarts.findLast(start=>start<=r.at),networkStarts)).length};});
 }
 save('public-traffic',pub);save('network-starts',networkStarts);
 }
 if(bridge)save('extension-final-state',await state());
 // Final independent server log audit catches late arrivals after navigation/teardown.
 await stop();await delay(1000);const rows=[...audit].map(([id,expected])=>({id,expected,actual:arrivals(id).length}));save('delivery-audit',rows);for(const r of rows)assert.equal(r.actual,r.expected,r.id);
 log('FINAL_DELIVERY_AUDIT',{status:'PASS',cases:rows.length});console.log('ALL 17B CHECKS COMPLETE');
}finally{await screenshot(out,'final-screen').catch(()=>{});save('summary',summary);if(chrome)await stop();bridge?.close();f.close();wt.kill();}
