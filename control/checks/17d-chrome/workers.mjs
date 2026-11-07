export default async function(c){
 const {rpc,ev,nav,log,state,count,delay,f,probe,discovery,save,assert}=c;
 await rpc('Check.mode',{mode:'pass'});await rpc('Check.floor',{domains:['127.0.0.1']});await nav();
 const collect=async(label)=>{await delay(1400);const rows=f.rows.filter(r=>['http','ws-open','ws-message'].includes(r.kind)&&r.case?.startsWith('worker-'));assert.equal(rows.filter(r=>r.kind==='http'&&!r.case.startsWith('worker-control')).length,0,'guarded workers must not deliver POSTs');for(const id of new Set(f.rows.filter(r=>r.kind==='attempt'&&r.case?.startsWith('worker-')&&!r.case.startsWith('worker-control')).map(r=>r.case))){const n=f.rows.filter(r=>r.kind==='attempt'&&r.case===id).length;assert.equal(rows.filter(r=>r.case===id&&r.kind==='ws-open').length,n,'reproduce worker WebSocket counterexample '+id);assert.equal(rows.filter(r=>r.case===id&&r.kind==='ws-message').length,n,'worker sends once per startup/event '+id);}for(const row of rows)discovery(row.case,'autonomous-worker counterexample');log(label,{scripts:f.rows.filter(r=>r.kind==='worker-script'),attempts:f.rows.filter(r=>r.kind==='attempt'),arrivals:rows,events:(await state()).history,targets:await rpc('Check.targets')});};
 await ev("(async()=>{window.swreg=await navigator.serviceWorker.register('/sw.js?case=worker-service',{updateViaCache:'none'});await navigator.serviceWorker.ready;return true})()");
 await collect('Q3_NEW_SERVICE');assert.equal(c.arrivals('worker-service-v1-first').filter(r=>r.kind==='http').length,0);
 await probe('Q3_SERVICE_WORKER_DOMAIN',async()=>({result:await rpc('Check.command',{method:'ServiceWorker.enable'})}));
 await rpc('Check.detach');await delay(35000);log('Q3_IDLE_TARGETS',{targets:await rpc('Check.targets')});
 // The browser, rather than an auto-attaching debugger, reaches this worker on navigation.
 await c.address(f.base+'/');await collect('Q3_NAVIGATION_START_NO_DEBUGGER');
 await rpc('Check.attach',{tabId:c.selected});await nav();
 await ev("navigator.serviceWorker.getRegistration().then(r=>{window.swreg=r;return true})");f.bump();
 await ev("swreg.update().then(()=>true)");await collect('Q3_EXPLICIT_UPDATE');assert.equal(c.arrivals('worker-service-v2-first').filter(r=>r.kind==='http').length,0);
 // A navigation update is observed separately; do not force it with a debugger update API.
 f.bump();await rpc('Check.detach');await c.address(f.base+'/');await delay(2500);await collect('Q3_NAVIGATION_UPDATE');
 await rpc('Check.attach',{tabId:c.selected});await nav();
 await probe('Q3_BACKGROUND_SYNC',async()=>{
  await ev("setTimeout(async()=>{const r=await navigator.serviceWorker.ready;await r.sync.register('synthetic-floor-sync')},600);true");await rpc('Check.detach');await delay(3500);await collect('Q3_SYNC_NO_PAGE_DEBUGGER');return {rows:f.rows.filter(r=>r.case?.includes('-sync')),registration:'real SyncManager.register, no dispatchSyncEvent'};
 });
 await rpc('Check.attach',{tabId:c.selected});await nav();
 await ev("window.shared=new SharedWorker('/worker.js?shared&case=worker-shared');shared.port.start();true");await collect('Q3_NEW_SHARED');discovery('worker-shared-v3-first','worker websocket floor coverage');
 // Tab-only WS allowance must not cover service/shared worker handshakes (webRequest tabId=-1).
 await rpc('Check.rules',{addRules:[{id:8002,priority:100,action:{type:'allow'},condition:{tabIds:[c.selected],resourceTypes:['websocket']}}]});
 await ev("shared.port.postMessage('send');navigator.serviceWorker.ready.then(r=>r.active.postMessage('send'));true");await collect('Q3_TAB_ALLOWANCE');
 discovery('worker-shared-v3-message','worker websocket tab allowance coverage');
 for(const suffix of ['first','message','sync'])for(const v of [1,2,3]){discovery(`worker-service-v${v}-${suffix}`,'worker startup/message/sync transport coverage');}
 await rpc('Check.rules',{removeRuleIds:[8002],addRules:[{id:7001,priority:1000,action:{type:'block'},condition:{resourceTypes:['websocket']}}]});await ev("window.globalSocket=new SharedWorker('/worker.js?shared&case=worker-global');globalSocket.port.start();true");await delay(700);log('Q3_GLOBAL_SOCKET_BLOCK',{rows:discovery('worker-global-v3-first','global websocket block diagnostic')});
 log('Q3_WORKER_TAB_IDS',{requests:(await state()).history.filter(e=>e.method==='check.webRequest'&&/socket|worker/.test(e.params.url)),note:'DNR-blocked handshakes may omit webRequest observations; a positive control below exposes the tab ID.'});
 // Positive worker control, with the floor removed, proves startup generators reach this receiver.
 await rpc('Check.floor',{clear:true});await ev("window.positive=new SharedWorker('/worker.js?shared&case=worker-control');positive.port.start();true");await delay(800);
 await count('worker-control-v3-first',3); // POST, open, one message
 log('Q3_WORKER_POSITIVE',{rows:c.arrivals('worker-control-v3-first'),events:(await state()).history.filter(e=>e.method==='check.webRequest')});
 await rpc('Check.floor',{domains:['127.0.0.1']});
 // Restart registration is exercised before any page is attached on the next boot.
 await rpc('Page.bringToFront');await delay(7000);await c.close(true);await c.boot('worker-restored',true);await collect('Q2_RESTORED_WORKER');
 log('Q3_PUSH',{status:'not-checked',reason:'No real push subscription/FCM credentials; debugger-delivered push would violate the requested independent trigger.'});
 // Real HTTP/3 receiver, same inherited fixture/certificate pinning as 17b/17c.
 await probe('Q1_WEBTRANSPORT',async()=>{
  const wt=c.spawn(c.work.replace('17d-chrome','17b-chrome')+'/venv/bin/python',[c.here.replace('17d-chrome','17b-chrome')+'/webtransport.py',c.work],{stdio:['ignore',c.fs.openSync(c.out+'/wt.log','a'),c.fs.openSync(c.out+'/wt.log','a')]});
  try{await c.eventually(()=>c.fs.existsSync(c.work+'/webtransport.json'),'WT fixture');const info=JSON.parse(c.fs.readFileSync(c.work+'/webtransport.json'));
   const rows=()=>c.fs.existsSync(c.out+'/webtransport-server.jsonl')?c.fs.readFileSync(c.out+'/webtransport-server.jsonl','utf8').trim().split('\n').filter(Boolean).map(JSON.parse):[];
   await nav();await rpc('Check.floor',{clear:true});
   const attempt=id=>ev(`(()=>{const t=new WebTransport('${info.url}?case=${id}',{serverCertificateHashes:[{algorithm:'sha-256',value:new Uint8Array(${JSON.stringify(info.hash)})}]});t.ready.then(()=>{t.close();events.push('wt-open')}).catch(e=>events.push(e.name));return true})()`);
   await attempt('wt-control');await delay(1800);const before=rows().length;assert.ok(before>0,'positive HTTP/3 handshake');
   await rpc('Check.floor',{domains:['127.0.0.1']});await attempt('wt-blocked');await delay(1800);assert.equal(rows().length,before);
   f.setTransport(info);await ev("window.wtShared=new SharedWorker('/worker.js?shared&case=worker-wt-shared');wtShared.port.start();navigator.serviceWorker.register('/sw.js?case=worker-wt-service');true");await delay(1800);
   for(const id of ['worker-wt-shared-v3-first','worker-wt-service-v3-first'])discovery(id,'worker WebSocket alongside WebTransport');
   const workerReports=[];for(const t of (await rpc('Check.targets')).filter(t=>t.url.includes('worker-wt'))){try{await rpc('Check.workerAttach',{targetId:t.id});const result=await rpc('Check.command',{source:{targetId:t.id},method:'Runtime.evaluate',params:{expression:'({available:typeof WebTransport,results})',returnByValue:true}});workerReports.push({target:t,result});}catch(e){workerReports.push({target:t,error:e.message});}}
   const all=rows();for(const row of all)assert.match(row.headers[':path'],/case=(wt-control|worker-wt-shared|worker-wt-service)$/,'registered HTTP/3 receiver case');
   save('webtransport-audit',{rows:all,pageBlockedArrivals:0,workerHandshakeArrivals:all.length-before,workerReports});return {control:before,blocked:0,workerHandshakeArrivals:all.length-before,workerReports,rows:all,events:(await state()).history.filter(e=>/webTransport/i.test(e.method)||e.method==='check.webRequest'&&e.params.type==='webtransport')};
  }finally{wt.kill();}
 });
}
