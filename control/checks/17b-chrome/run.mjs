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
const {pack,idFor}=await import('../17-chrome/install.mjs');
const summary={run:process.env.GITHUB_RUN_ID,head:process.env.GITHUB_SHA,cases:[]},audit=new Map();
const save=(n,v)=>fs.writeFileSync(out+'/'+n+'.json',JSON.stringify(v,null,2));
function log(name,row){summary.cases.push({name,...row});save('summary',summary);console.log(name,JSON.stringify(row));}
async function probe(name,fn){try{const row=await fn();log(name,{status:'observed',...row});return row;}catch(e){log(name,{status:'probe-error',error:e.stack});return {error:e.message};}}
let updateVersion='0.2.0',id,chrome,bridge,selected,group;
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
  else {const d=process.env.XDG_CONFIG_HOME+'/google-chrome/NativeMessagingHosts';fs.mkdirSync(d,{recursive:true});fs.copyFileSync(temp,d+'/'+hostName+'.json');}
}
function policy(userHosts){const p={ExtensionInstallForcelist:[id+';'+f.base+'/update.xml'],ExtensionInstallBlocklist:['fcoeoabgfenejglbffodgkkbkcdhcgfn'],NativeMessagingUserLevelHosts:userHosts};const file=work+'/policy.json';fs.writeFileSync(file,JSON.stringify(p));execFileSync('sudo',['install','-D','-m','644',file,'/etc/opt/chrome/policies/managed/aresos-17b.json']);save('policy-'+userHosts,p);}
policy(true);
async function stop(kill=false){bridge?.close();bridge=undefined;if(chrome?.exitCode===null){if(kill){chrome.kill('SIGKILL');execFileSync('pkill',['-KILL','-f',work+'/profile'],{stdio:'ignore'});}else{await activateChrome();await key('ctrl+shift+q');await delay(2000);if(chrome.exitCode===null)chrome.kill('SIGTERM');}await delay(600);}chrome=undefined;}
async function boot(label){
 bridge=await nativeBridge(socket);
 const args=[`--user-data-dir=${work}/profile`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode',f.base+'/'];
 save('chrome-'+label+'-args',args);const fd=fs.openSync(out+'/chrome-'+label+'.log','a');chrome=spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});
 await activateChrome();await delay(5000);await screenshot(out,'boot-'+label);await connect();
}
async function connect(){
  const conn=new Promise(r=>bridge.once('check.connected',r));
  await key('ctrl+t');await address(`chrome-extension://${id}/select.html?url=${encodeURIComponent(f.base+'/')}`);await key('Return');
  const c=await Promise.race([conn,delay(10000).then(()=>{throw Error('Extension failed to connect')})]);selected=c.tabId;group=c.group;
  await bridge.send('Check.enableGate');await bridge.send('Check.config',{});await bridge.send('Network.setBypassServiceWorker',{bypass:true});
  log('CONNECTED',{...c,host:fs.readFileSync(out+'/host-starts.txt','utf8').trim().split('\n').at(-1)});
}
const state=()=>bridge.send('Check.state');
const arrivals=id=>f.arrivals.filter(r=>r.kind==='receive'&&new URL(r.url,f.base).searchParams.get('case')===id);
async function nav(){await bridge.send('Page.navigate',{url:f.base+'/'});await delay(500);await eventually(()=>evaluate(bridge,"typeof send==='function'"),'fixture ready');}
async function held(id,kind='fetch',timeout=0){await evaluate(bridge,`send(${JSON.stringify(id)},${JSON.stringify(kind)},${timeout});'started'`);return eventually(async()=>{const s=await state();if(s.errors.length)throw Error(s.errors.join(';'));return s.pending.find(p=>p.url.includes('case='+id));},'held '+id);}
async function decide(p,release){return bridge.send('Check.decide',{id:p.id,release});}
async function observe(id,expected){await delay(650);const a=arrivals(id);if(expected!==undefined){assert.equal(a.length,expected,id);audit.set(id,expected);}return a;}
async function matrix(label,action,{backstop=false,expected}={}){await nav();await bridge.send('Check.config',{backstop});const id='q1-'+label+(backstop?'-dnr':'');const p=await held(id);assert.equal(arrivals(id).length,0);save(id+'-held',await state());await action(p);await delay(1200);const a=await observe(id,expected);log('Q1_'+label+(backstop?'_DNR':''),{id,preview:p,arrivals:a});return a;}
try{
 await boot('initial');
 await screenshot(out,'policy-debug-bar');
 const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);save('processes',{processes});
 log('Q5_POLICY_INSTALL',{info:await bridge.send('Check.info'),policy:JSON.parse(fs.readFileSync(work+'/policy.json'))});
 await probe('Q5_DISABLE',()=>bridge.send('Check.disable'));
 await probe('Q5_REMOVE',()=>bridge.send('Check.uninstall'));
 log('Q5_HOST_DEFAULT',{starts:fs.readFileSync(out+'/host-starts.txt','utf8')});
 await stop();policy(false);await boot('system-host');
 log('Q5_HOST_POLICY_FALSE',{starts:fs.readFileSync(out+'/host-starts.txt','utf8')});
 // Q1: controlled detach probes, with a fresh tab attachment between each.
 await matrix('host-dies',async()=>{const pid=Number(fs.readFileSync(out+'/host-pids.txt','utf8').trim().split('\n').at(-1));process.kill(pid,'SIGKILL');},{expected:0});
 await stop();await boot('after-host');
 await matrix('service-socket',async()=>{bridge.close();bridge=undefined;},{expected:0});
 await stop();await boot('after-socket');
 for(const backstop of [false,true]){
   await matrix('detach',()=>bridge.send('Check.detach'),{backstop});
   await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');
   await matrix('reload',async()=>{await bridge.send('Check.reload');await delay(1200);},{backstop});
   await stop();await boot('after-reload-'+backstop);
   await matrix('devtools',async()=>{await bridge.send('Page.bringToFront');await key('ctrl+shift+i');await delay(1200);await screenshot(out,'devtools-'+backstop);await key('ctrl+shift+i');},{backstop});
   // Native port survives the tab debugger being replaced.
   await stop();await boot('after-devtools-'+backstop);
   await matrix('cancel',async()=>{await bridge.send('Page.bringToFront');await screenshot(out,'before-cancel-'+backstop);x('mousemove',1378,134,'click',1);await delay(500);await screenshot(out,'after-cancel-'+backstop);},{backstop});
   await stop();await boot('after-cancel-'+backstop);
 }
 await matrix('tab-close',()=>bridge.send('Check.closeTab'),{expected:0});await stop();await boot('after-tab');
 await matrix('chrome-normal',()=>stop(),{expected:0});await boot('after-normal');
 await matrix('chrome-kill',()=>stop(true),{expected:0});await boot('after-kill');
 await probe('Q1_STOP_WORKER',async()=>{const p=await held('q1-worker-stop');const result=await bridge.send('ServiceWorker.enable');const stopped=await bridge.send('ServiceWorker.stopAllWorkers');await delay(1000);return {result,stopped,arrivals:await observe('q1-worker-stop')};});
 await stop();await boot('after-worker-stop');
 await matrix('policy-update',async()=>{packVersion('0.2.1');log('Q5_UPDATE_CHECK',await bridge.send('Check.update'));await delay(4000);});
 await stop();await boot('after-update');
 log('Q5_UPDATED',{version:(await state()).version,updates:f.arrivals.filter(r=>['update','crx'].includes(r.kind))});
 // Repeat instead of preserving an in-flight request. Compare before permitting one exact match.
 await nav();await bridge.send('Check.config',{mode:'repeat'});
 const repeated=[];bridge.on('check.repeated',r=>repeated.push(r));
 for(const kind of ['fetch','xhr','form']){
   await nav();const id='repeat-'+kind;for(let i=0;i<3;i++){await nav();await evaluate(bridge,`send('${id}','${kind}');'ok'`);await delay(400);}
   const rows=repeated.filter(r=>r.url.includes('case='+id));assert.equal(rows.length,3);assert.equal(arrivals(id).length,0);
   const first=rows[0];assert.ok(rows.every(r=>r.url===first.url&&r.method===first.method&&r.body===first.body));
   await nav();await bridge.send('Check.arm',{url:first.url,method:first.method,body:first.body});await evaluate(bridge,`send('${id}','${kind}');'ok'`);await observe(id,1);
   log('Q1_REPEAT',{kind,attempts:rows,byteMatches:rows.length,normalizedMatches:rows.length,ignoredFields:[]});
 }
 await bridge.send('Check.config',{});await nav();
 // Q2: page through worker, worker target, bypass, and background sync.
 await bridge.send('Network.setBypassServiceWorker',{bypass:false});await evaluate(bridge,'worker()');
 log('Q2_WORKER_CONTROLLED',{controlled:await evaluate(bridge,'!!navigator.serviceWorker.controller')});
 const targets=await bridge.send('Check.targets');save('targets',targets);
 const worker=targets.find(t=>t.type==='service_worker'&&t.url===f.base+'/sw.js');
 if(worker){
   await probe('Q2_WORKER_ATTACH',()=>bridge.send('Check.workerAttach',{targetId:worker.id}));
   for(const kind of ['fetch','xhr','form'])for(const release of [true,false]){
     await nav();await evaluate(bridge,'worker()');const id='sw-page-'+kind+'-'+release;
     await evaluate(bridge,`send('${id}','${kind}');'ok'`);await delay(600);let s=await state();let p=s.pending.find(p=>p.url.includes('case='+id));
     const heldBefore=arrivals(id).length;
     // A page pause may precede a separate worker pause. Drain only this case.
     if(p)await decide(p,release);await delay(500);s=await state();for(const q of s.pending.filter(q=>q.url.includes('case='+id)))await decide(q,release);
     const a=await observe(id);if(p){assert.equal(heldBefore,0);assert.equal(a.length,release?1:0);audit.set(id,release?1:0);}
     log('Q2_PAGE_SW',{id,kind,release,held:!!p,heldBefore,arrivals:a,states:kind==='form'?null:await evaluate(bridge,'states')});
   }
   for(const release of [true,false]){
     await nav();await evaluate(bridge,'worker()');const id='sw-own-'+release;
     await evaluate(bridge,`navigator.serviceWorker.controller.postMessage({url:'${f.base}/receive?case=${id}'});'ok'`);await delay(500);
     const p=(await state()).pending.find(p=>p.url.includes(id));const before=arrivals(id).length;if(p)await decide(p,release);const a=await observe(id);if(p){assert.equal(before,0);assert.equal(a.length,release?1:0);audit.set(id,release?1:0);}
     log('Q2_OWN_SW',{id,release,held:!!p,before,arrivals:a});
   }
 }
 await probe('Q2_SYNC',async()=>{await nav();await evaluate(bridge,'worker()');const id='sw-sync';const supported=await evaluate(bridge,`navigator.serviceWorker.ready.then(async r=>{if(!r.sync)return false;await r.sync.register('${id}');return true})`);await delay(2500);const p=(await state()).pending.find(p=>p.url.includes(id));const before=arrivals(id).length;if(p)await decide(p,false);return {supported,held:!!p,before,arrivals:await observe(id)};});
 await bridge.send('Network.setBypassServiceWorker',{bypass:true});
 for(const kind of ['fetch','xhr','form'])for(const release of [true,false]){await nav();const id='bypass-'+kind+'-'+release;const p=await held(id,kind);assert.equal(arrivals(id).length,0);await decide(p,release);log('Q2_BYPASS',{id,release,arrivals:await observe(id,release?1:0)});}
 // Q3: run waits concurrently; the single 10-minute hold belongs only to final verification.
 await nav();await bridge.send('Check.config',{});
 const durations=[30000,120000,...(process.env.LONG_HOLD==='true'?[600000]:[])];
 const holdRows=[];
 for(const ms of durations){const id='long-'+ms,p=await held(id);holdRows.push({id,ms,p,start:Date.now()});}
 const abort=await held('long-abort','fetch',30000),xhr=await held('long-xhr','xhr',30000);
 await evaluate(bridge,"retry('long-retry');'ok'");await delay(1250);
 const retries=(await state()).pending.filter(p=>p.url.includes('case=long-retry'));assert.equal(retries.length,2);assert.equal(arrivals('long-retry').length,0);
 await decide(retries[0],false);await decide(retries[1],true);await observe('long-retry',1);log('Q3_RETRY',{pending:retries,arrivals:arrivals('long-retry')});
 for(const row of holdRows){await delay(Math.max(0,row.ms-(Date.now()-row.start)));assert.equal(arrivals(row.id).length,0);await decide(row.p,true);log('Q3_LONG',{id:row.id,requestedMs:row.ms,heldMs:Date.now()-row.start,arrivals:await observe(row.id,1)});}
 for(const [id,p]of [['long-abort',abort],['long-xhr',xhr]]){const result=await probe('Q3_CANCELED_RELEASE_'+id,()=>decide(p,true));log('Q3_CANCELED',{id,result,arrivals:await observe(id,0)});}
 log('Q3_PAGE_STATES',{states:await evaluate(bridge,'states')});
 // Form stays pending for 30 seconds, then completes one navigation.
 await nav();const form=await held('long-form','form');await delay(30000);assert.equal(arrivals('long-form').length,0);await decide(form,true);await observe('long-form',1);log('Q3_FORM',{arrivals:arrivals('long-form')});
 await nav();
 // Q4 detection and handshake: event history is independent of the Fetch gate.
 const events=[];bridge.on('event',e=>{if(/WebSocket|webTransport|dataChannel|peerConnection/i.test(e.method))events.push({at:Date.now(),...e});});
 await evaluate(bridge,"connectWS();'ok'");await delay(1200);const wsPending=(await state()).pending.filter(p=>p.type==='WebSocket');
 log('Q4_WS_HANDSHAKE',{pending:wsPending,server:f.arrivals.filter(r=>r.kind==='ws-open'),events:events.slice()});
 await evaluate(bridge,"ws.send('synthetic socket');'ok'");await delay(400);
 await bridge.send('Check.detach');await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');events.length=0;await delay(500);
 const oldSocket=await evaluate(bridge,'ws.readyState');await evaluate(bridge,"ws.send('synthetic preattach');'ok'");await delay(400);
 log('Q4_WS_PREATTACH',{readyState:oldSocket,events:events.slice(),server:f.arrivals.filter(r=>r.kind.startsWith('ws'))});
 await probe('Q4_WEBRTC',async()=>{await bridge.send('Media.enable');await evaluate(bridge,'rtc()');await eventually(()=>evaluate(bridge,"channel.readyState==='open'"),'RTC open');await evaluate(bridge,"channel.send('synthetic rtc');'ok'");return {events:events.slice(),states:await evaluate(bridge,'states')};});
 await probe('Q4_WEBTRANSPORT',async()=>{await evaluate(bridge,`window.transport=new WebTransport('https://127.0.0.1:9/');transport.ready.catch(e=>mark(e.name));'attempted'`);await delay(1000);return {events:events.slice(),states:await evaluate(bridge,'states')};});
 await nav();
 // Permanently watch typed text, including sends outside a 500ms settle window.
 const text='Synthetic 17b "a+b" / ✓',encoded=[text,encodeURIComponent(text),new URLSearchParams({text}).toString().slice(5),JSON.stringify(text).slice(1,-1),Buffer.from(text).toString('base64')];
 await bridge.send('Check.config',{texts:[text]});
 for(let i=0;i<encoded.length;i++)for(const wait of [5000,10000]){
   const id='typed-'+i+'-'+wait;const start=Date.now();await evaluate(bridge,`document.querySelector('#text').value=${JSON.stringify(text)};setTimeout(()=>{fetch('/receive?case=${id}',{method:'POST',body:${JSON.stringify(encoded[i])}}).catch(()=>{})},${wait});'ok'`);
   const p=await eventually(async()=>(await state()).pending.find(p=>p.url.includes('case='+id)),'delayed text',wait+5000);assert.ok(p.typed.length);assert.equal(arrivals(id).length,0);await decide(p,false);audit.set(id,0);log('Q4_TYPED',{id,encoding:i,delayMs:Date.now()-start,settleMs:500,outsideSettle:true,preview:p});
 }
 const pixel='typed-image';await evaluate(bridge,`document.querySelector('#text').value=${JSON.stringify(text)};window.pixel=new Image();pixel.src='/receive?case=${pixel}&text='+encodeURIComponent(${JSON.stringify(text)});'ok'`);
 const p=await eventually(async()=>(await state()).pending.find(p=>p.url.includes(pixel)),'typed image');assert.ok(p.typed.length);await decide(p,false);await observe(pixel,0);log('Q4_TYPED_IMAGE',{preview:p});
 // Q5 group ownership, refusal after owner ungroup, close while held.
 const opened=await bridge.send('Check.open',{url:f.base+'/new'});log('Q5_GROUP_OPEN',{opened,tabs:await bridge.send('Check.tabs')});
 await nav();const gp=await held('group-out');await bridge.send('Check.ungroup',{tabId:selected});await delay(500);await probe('Q5_OUTSIDE_REFUSED',()=>evaluate(bridge,'document.title'));log('Q5_GROUP_OUT',{arrivals:await observe('group-out',0),state:await state()});
 await bridge.send('Check.attach',{tabId:selected});await bridge.send('Check.enableGate');await nav();await held('group-close');await bridge.send('Check.closeGroup');log('Q5_GROUP_CLOSE',{arrivals:await observe('group-close',0)});
 await stop();await boot('public');
 // Public sites: only safe resources load; every potential text carrier is failed before sending.
 const pub=[];bridge.on('check.public',r=>pub.push({...r,at:Date.now()}));
 await bridge.send('Check.config',{publicMode:true,texts:[text,'SyntheticFixture17b']});
 for(const [name,url]of [['wikipedia','https://en.wikipedia.org/wiki/Main_Page'],['news','https://www.bbc.com/news'],['demo','https://www.selenium.dev/selenium/web/web-form.html']]){
  await probe('Q4_PUBLIC_'+name,async()=>{const start=Date.now(),offset=pub.length;await bridge.send('Page.navigate',{url});await delay(4000);const title=await evaluate(bridge,'document.title');
   const action=await evaluate(bridge,`(()=>{const input=document.querySelector(${JSON.stringify(name==='wikipedia'?'input[name=search]':name==='demo'?'input[name="my-text"]':'input[type=search],input[type=text]')});if(!input)return {found:false};input.value='SyntheticFixture17b';input.dispatchEvent(new Event('input',{bubbles:true}));return {found:true,form:!!input.form}})()`);
   let repeated=[];
   if(action.found&&action.form){for(let i=0;i<(name==='demo'?3:1);i++){const before=pub.length;await evaluate(bridge,`(()=>{const input=document.querySelector(${JSON.stringify(name==='demo'?'input[name="my-text"]':'input[name=search]')});input.form.requestSubmit();return true})()`);await delay(700);repeated.push(pub.slice(before).filter(r=>r.typed.length));}}
   await delay(11000);const requests=pub.slice(offset);const textRequests=requests.filter(r=>r.typed.length);assert.ok(textRequests.every(r=>r.block));const canonical=r=>JSON.stringify({url:r.url,method:r.method,body:r.body});
   return {title,action,elapsedMs:Date.now()-start,requests,textRequests:textRequests.length,ruleMisses:textRequests.filter(r=>!r.block).length,unlabelledRequests:requests.filter(r=>!r.typed.length).length,repeat:repeated.map(rows=>rows.map(canonical)),ignoredVolatileFields:[],outsideInitialSettle:textRequests.filter(r=>r.at-start>4500).length};});
 }
 save('public-traffic',pub);
 // Final independent server log audit catches late arrivals after navigation/teardown.
 await stop();await delay(1000);const rows=[...audit].map(([id,expected])=>({id,expected,actual:arrivals(id).length}));save('delivery-audit',rows);for(const r of rows)assert.equal(r.actual,r.expected,r.id);
 log('FINAL_DELIVERY_AUDIT',{status:'PASS',cases:rows.length});console.log('ALL 17B CHECKS COMPLETE');
}finally{await screenshot(out,'final-screen').catch(()=>{});save('summary',summary);if(chrome)await stop();bridge?.close();f.close();}
