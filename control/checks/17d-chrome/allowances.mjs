export default async function(c){
 const {rpc,ev,nav,log,state,count,delay,f,assert,hash,probe,end,restart,discovery}=c;
 await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'fail'});
 const send=(id,body='synthetic approved',headers={'X-Check':'synthetic'})=>ev(`fetch('/receive?case=${id}',{method:'POST',headers:${JSON.stringify(headers)},body:${JSON.stringify(body)}}).catch(()=>{});true`);
 const allow=(id,body='synthetic approved',more={})=>rpc('Check.allow',{url:f.base+'/receive?case='+id,method:'POST',sha256:hash(body),headers:{'X-Check':'synthetic'},...more});
 await allow('one');await send('one');await delay(600);log('Q4_ONCE',{rows:await count('one',1),history:(await state()).history});
 await send('one');await delay(400);log('Q4_SECOND',{rows:await count('one',1),history:(await state()).history});
 await allow('competing');await ev("for(let i=0;i<2;i++)fetch('/receive?case=competing',{method:'POST',headers:{'X-Check':'synthetic'},body:'synthetic approved'}).catch(()=>{});true");await delay(500);log('Q4_COMPETING',{rows:await count('competing',1),history:(await state()).history.slice(-20)});
 await allow('wrong-body');await send('wrong-body','synthetic DIFFERENT');await count('wrong-body',0);log('Q4_BODY_MISMATCH',{history:(await state()).history.slice(-15)});
 await allow('wrong-header');await send('wrong-header','synthetic approved',{'X-Check':'changed'});await count('wrong-header',0);log('Q4_HEADER_MISMATCH',{history:(await state()).history.slice(-15)});
 // Exact URL/method and tab/site scope, with a positive recipient available.
 await allow('exact-target');await send('different-target');await count('different-target',0);await send('exact-target');await delay(500);discovery('exact-target','exact URL allowance');
 await allow('site-scope','synthetic approved',{site:'127.0.0.1'});await send('site-scope');await delay(400);log('Q4_SITE_SCOPE',{rows:discovery('site-scope','initiator-scoped allowance'),history:(await state()).history.slice(-12)});
 await allow('site-allow-worker-v1-first','synthetic approved',{site:'127.0.0.1'});await ev("window.competing=new SharedWorker('/worker.js?shared&case=site-allow-worker');competing.port.start();true");await delay(800);log('Q4_UNREACHED_SITE_ALLOWANCE',{rows:await count('site-allow-worker-v1-first',3),history:(await state()).history.slice(-20)});await rpc('Check.rules',{removeRuleIds:[8001]});
 // Expose the natural add-to-match interval, then hold a mismatching request at the named failure instant.
 for(const revoke of [false,true])for(const pause of [0,25,100,500])for(let i=0;i<3;i++){
  const id=`race-${revoke}-${pause}-${i}`;await rpc('Check.mode',{mode:'park'});const added=await allow(id);await delay(pause);await send(id,'synthetic wrong-body');await delay(150);
  const before=await state(),g=before.history.filter(e=>e.method==='check.gate'&&e.params.url.includes(id)).at(-1);assert.ok(g,'allowance must reach Fetch for deterministic detach race');
  if(revoke)await rpc('Check.rules',{removeRuleIds:[8001]});await rpc('Check.detach');await delay(300);log('Q4_RACE',{id,revoke,pause,added,gate:g,endedAt:Date.now(),rows:await count(id,1)});await rpc('Check.attach',{tabId:c.selected});await rpc('Check.rules',{removeRuleIds:[8001]});
 }
 // Natural delay is separate from the intentional diagnostic pause above.
 await rpc('Check.mode',{mode:'fail'});await rpc('Check.clear');await allow('natural-window');await send('natural-window');await delay(600);log('Q4_NATURAL_WINDOW',{rows:discovery('natural-window','natural allowance window'),history:(await state()).history});
 for(const cleanup of [false,true])for(const ending of ['reload','update','worker-crash','policy']){
  await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'fail'});await rpc('Check.cleanup',{enabled:cleanup});await allow('leftover-'+cleanup+'-'+ending);const before=await state();await end(ending);
  if(ending==='policy'){await c.address(f.base+'/startup?prefix=policy-unloaded-'+cleanup);log('Q4_POLICY_UNLOADED',{cleanup,same:discovery('policy-unloaded-'+cleanup+'-same','first send after policy block'),cross:discovery('policy-unloaded-'+cleanup+'-cross','cross-site first send after policy block')});}
  if(ending==='policy')await restart('leftover-'+cleanup+'-'+ending);else await c.connect();
  const after=await state();log('Q4_LIFETIME',{cleanup,ending,sameProfile:ending!=='policy',before:before.session,after:after.session,dynamic:after.dynamic,startup:after.startup,version:after.manifest.version});
  // If a leftover remains, detach the gate and deliberately try it, proving the receiver consequence.
  const id='leftover-'+cleanup+'-'+ending;await rpc('Check.mode',{mode:'pass'});await send(id);await delay(400);log('Q4_LEFTOVER_RECEIVER',{id,rows:discovery(id,'remaining allowance consequence')});await rpc('Check.rules',{removeRuleIds:[8001]});
 }
 await rpc('Check.cleanup',{enabled:true});await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'fail'});
 // Full immutable bodies in the wrapper, compared with Chrome's network observations of raw blocked sends.
 for(const [kind,expression]of [
  ['json',"JSON.stringify({delete:42,text:'synthetic'})"],['urlencoded',"new URLSearchParams({delete:'42',text:'synthetic'})"],
  ['multipart',"(()=>{const f=new FormData();f.append('delete','42');f.append('file',document.querySelector('#upload').files[0]);return f})()"],
  ['1mb',"'x'.repeat(1024*1024)"],['25mb',"'y'.repeat(25*1024*1024)"],
  ['stream',"new ReadableStream({start(c){c.enqueue(new TextEncoder().encode('synthetic stream'));c.close()}})"]
 ]){
  await nav();await rpc('Check.clear');const id='body-'+kind;if(kind==='multipart'){
   const file=c.work+'/synthetic-upload.txt';c.fs.writeFileSync(file,'SYNTHETIC_DISK_FILE_17D'.repeat(4096));
   // chrome.debugger cannot grant filesystem access. Select only this runner-created file in the real picker.
   await rpc('Page.bringToFront');const b=await ev("(()=>{const b=document.querySelector('#upload').getBoundingClientRect();return {x:screenX+b.x+35,y:screenY+outerHeight-innerHeight+b.y+b.height/2}})()");c.x('mousemove',Math.round(b.x),Math.round(b.y),'click',1);await delay(700);await c.screenshot(c.out,'synthetic-file-picker');await c.key('ctrl+l');c.x('type','--clearmodifiers','--delay','1',file);await c.key('Return');await delay(500);if(!await ev("document.querySelector('#upload').files.length===1"))await c.key('alt+o');await c.eventually(()=>ev("document.querySelector('#upload').files[0]?.name==='synthetic-upload.txt'"),'synthetic disk file selected');
  }
  await ev(`window.testBody=${expression};fetch('/receive?case=${id}',{method:'POST',body:testBody,${kind==='json'?"headers:{'Content-Type':'application/json'},":''}${kind==='stream'?"duplex:'half',":''}}).catch(e=>events.push(e.name));true`);await delay(800);await count(id,0);const network=(await state()).history;
  await ev(`__floor.enabled=true;testBody=${expression};fetch('/receive?case=wrap-${kind}',{method:'POST',body:testBody,${kind==='json'?"headers:{'Content-Type':'application/json'},":''}${kind==='stream'?"duplex:'half',":''}}).catch(e=>events.push(e.name));true`);await delay(1000);await count('wrap-'+kind,0);
  const wrapper=(await state()).history.filter(e=>e.method==='check.script'&&['held','stream-refused'].includes(e.params.event));assert.ok(wrapper.length,'wrapper body outcome '+kind);
  log('Q5_BODY',{kind,network,wrapper,page:await ev('events')});
  if(['1mb','25mb'].includes(kind)){
   await rpc('Network.enable',{maxPostDataSize:32*1024*1024});await rpc('Check.clear');await ev(`__floor.enabled=false;fetch('/receive?case=large-event-${kind}',{method:'POST',body:${expression}}).catch(()=>{});true`);await delay(1000);await count('large-event-'+kind,0);log('Q5_LARGE_EVENT_LIMIT',{kind,maxPostDataSize:32*1024*1024,events:(await state()).history});await rpc('Network.enable',{maxPostDataSize:65536});
  }
  if(kind!=='stream'){
   const held=(await state()).pending.find(p=>p.description.url.includes('wrap-'+kind));assert.ok(held);
   if(kind==='multipart')await ev("testBody.append('later','must not reach receiver');true");
   // Receiver-only oracle: this deliberately passes the gate to qualify the wrapper's stored bytes
   // separately from Chrome's incomplete body view. It does not qualify exact multipart replay.
   await rpc('Check.mode',{mode:'pass'});await rpc('Check.release',{id:held.id});await c.eventually(()=>c.arrivals('wrap-'+kind).length===1,'frozen receiver '+kind,20000);const rows=await count('wrap-'+kind,1);assert.equal(rows[0].sha256,held.description.sha256);assert.equal(rows[0].length,held.description.length);log('Q5_FROZEN_RECEIVER',{kind,description:held.description,rows,oracle:'synthetic gate passthrough, not replay qualification'});await rpc('Check.mode',{mode:'fail'});
  }
 }
 // Account fingerprint uses both HttpOnly cookies (debugger) and the page's displayed label.
 await nav();await ev("setAccount17('synthetic-A')");await ev("__floor.enabled=true;fetch('/receive?case=account-change',{method:'POST',body:'synthetic deletion'}).catch(()=>{});true");await delay(500);
 const held=(await state()).pending.find(p=>p.description.url.includes('account-change'));assert.ok(held);const before=await rpc('Check.account');
 await c.click('#signout');await c.eventually(()=>ev("document.querySelector('#account').textContent==='synthetic-signed-out'"),'fixture signed out');await c.click('#signinB');await c.eventually(()=>ev("document.querySelector('#account').textContent==='synthetic-B'"),'fixture signed in as B');
 await assert.rejects(()=>rpc('Check.release',{id:held.id}),/ACCOUNT_CHANGED/);await count('account-change',0);log('Q8_ACCOUNT_CHANGE',{before,after:await rpc('Check.account'),refused:true});
}
