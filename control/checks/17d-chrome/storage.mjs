export default async function(c){
 const {rpc,ev,nav,log,state,count,delay,f,probe,assert}=c;
 await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'pass'});
 const subscriptions=[];
 for(const [method,params]of [['DOMStorage.enable',{}],['Storage.trackIndexedDBForOrigin',{origin:f.base}],['Storage.trackCacheStorageForOrigin',{origin:f.base}],['ServiceWorker.enable',{}],['BackgroundService.startObserving',{service:'backgroundSync'}],['BackgroundService.startObserving',{service:'periodicBackgroundSync'}]]){
  subscriptions.push(await probe('Q6_SUBSCRIBE_'+method,async()=>({result:await rpc('Check.command',{method,params})})));
 }
 for(const kind of ['localStorage','sessionStorage','indexedDB','cache','cookie','opfs','broadcast','window','dedicated','shared','registration','sync','periodicSync']){
  await rpc('Check.clear');const result=await ev(`write17('${kind}')`);await delay(1000);const h=(await state()).history;
  const browser=h.filter(e=>!e.method.startsWith('check.')),script=h.filter(e=>e.method==='check.script'&&e.params.event==='write-or-handoff');
  log('Q6_PAGE_WRITE',{kind,result,browser,script,latencies:browser.map(e=>({method:e.method,ms:e.at-result.at}))});
 }
 for(const id of ['handoff-dedicated','handoff-shared','storage-sw'])for(const suffix of ['first','message','sync'])await count(id+'-v1-'+suffix,0);
 // Direct worker subscription/injection after startup; no claim of pre-first-line coverage.
 const target=(await rpc('Check.targets')).find(t=>t.type==='service_worker'&&t.url.includes('storage-sw'));
 if(target)await probe('Q6_WORKER_WRITES',async()=>{
  await rpc('Check.workerAttach',{targetId:target.id});const source={targetId:target.id};
  const command=(method,params={})=>rpc('Check.command',{source,method,params});
  await command('Runtime.addBinding',{name:'__report17'});await command('Runtime.evaluate',{expression:c.fs.readFileSync(c.here+'/extension/observe.js','utf8')});
  const subscribed=[];for(const method of ['Storage.trackIndexedDBForOrigin','Storage.trackCacheStorageForOrigin']){try{await command(method,{origin:f.base});subscribed.push({method,ok:true})}catch(e){subscribed.push({method,error:e.message})}}
  for(const kind of ['indexedDB','cache','opfs','broadcast','cookie','localStorage','sync','periodicSync']){
   await rpc('Check.clear');const code=`(async()=>{const at=Date.now();try{${kind==='indexedDB'?"const db=await new Promise(r=>{const q=indexedDB.open('synthetic-worker17d',1);q.onupgradeneeded=()=>q.result.createObjectStore('outbox');q.onsuccess=()=>r(q.result)});await new Promise(r=>{const t=db.transaction('outbox','readwrite');t.objectStore('outbox').put('deletion42','pending');t.oncomplete=r});db.close();":kind==='cache'?"const ca=await caches.open('synthetic-worker17d');await ca.put('/worker-cache',new Response('deletion42'));":kind==='opfs'?"const root=await navigator.storage.getDirectory(),file=await root.getFileHandle('worker17d',{create:true}),w=await file.createWritable();await w.write('deletion42');await w.close();":kind==='broadcast'?"const b=new BroadcastChannel('synthetic-worker');b.postMessage('deletion42');b.close();":kind==='sync'?"await registration.sync.register('synthetic-worker17d');":kind==='periodicSync'?"await registration.periodicSync.register('synthetic-worker17d',{minInterval:3600000});":kind==='cookie'?"document.cookie='synthetic-worker=42';":"localStorage.setItem('synthetic-worker','42');"}return {at,result:'ok'}}catch(e){return {at,result:e.name+': '+e.message}}})()`;
   const result=await command('Runtime.evaluate',{expression:code,returnByValue:true,awaitPromise:true});await delay(1000);log('Q6_WORKER_WRITE',{kind,result,subscribed,events:(await state()).history});
  }
 });
 // No network operation at the click: only an IndexedDB outbox record.
 await nav();await rpc('Check.clear');const start=f.rows.length;await c.click('#queue');await c.eventually(()=>ev("events.some(e=>e.kind==='queued')"),'offline deletion committed');await delay(250);
 const evidence=(await state()).history;assert.ok(evidence.some(e=>e.method==='Storage.indexedDBContentUpdated'),'debugger must report offline outbox write');assert.equal(f.rows.slice(start).filter(r=>r.kind==='http').length,0);
 const owner=await rpc('Check.open',{url:f.base+'/'});await delay(600);await rpc('Check.attach',{tabId:owner.id});await ev("flush17('offline-later');true");await count('offline-later',0);log('Q6_OFFLINE_OUTBOX',{evidence,receiver:[],laterPage:await ev('events'),guardKept:true});
}
