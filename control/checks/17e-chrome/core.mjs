// Q1-Q5: every operation has a receiver-side positive control.
export default async function(c){
 const {ev,rpc,guard,positive,send,delivered,zero,pending,approve,control,log,assert,delay,f,rows,context}=c;
 await positive('e-basic-control');await guard();await send('e-basic-held');await pending('e-basic-held');await zero('e-basic-held');const op=await approve('e-basic-held');await delivered('e-basic-held');await assert.rejects(()=>control('approve',{id:op.id}),/NOT_PENDING/);log('Q4_EXACT_HTTP',{op,receiver:rows('e-basic-held')});
 for(const [name,base] of [['ipv4',f.base],['ipv6','http://[::1]:18081'],['localhost','http://localhost:18081'],['linklocal','http://169.254.17.1:18081']]){
  const request=id=>ev(`fetch(${JSON.stringify(base+'/receive?case=') }+${JSON.stringify(id)},{method:'POST',body:${JSON.stringify(id)}}).catch(e=>results[${JSON.stringify(id)}]=e.name);true`);
  await guard(false);await request('e-'+name+'-control');await delivered('e-'+name+'-control');await guard();await request('e-'+name+'-held');await pending('e-'+name+'-held');await zero('e-'+name+'-held');await approve('e-'+name+'-held');await delivered('e-'+name+'-held');log('Q1_ROUTE',{name,receiver:rows('e-'+name+'-held')});
 }
 // Redirect itself is a complete held operation, followed by a distinct request.
 for(const held of [false,true]){const id='e-redirect-'+(held?'held':'control');await guard(held);await ev(`fetch('/redirect?case=${id}',{method:'POST',body:'redirect-body'}).catch(()=>{});true`);if(held){await zero(id);await approve(id);await pending(id);await zero(id);await approve(id);}await delivered(id);log('Q3_REDIRECT',{held,receiver:rows(id)});}
 await guard(false);await ev("globalThis.shared=new SharedWorker('/worker.js?shared');shared.port.start();globalThis.dedicated=new Worker('/worker.js');true");await ev("navigator.serviceWorker.register('/sw.js').then(()=>navigator.serviceWorker.ready).then(r=>globalThis.sw=r.active);true");await c.eventually(()=>ev('!!globalThis.sw'),'service worker active');
 for(const kind of ['dedicated','shared','service']){
  const post=p=>ev(`${kind==='dedicated'?'dedicated':kind==='shared'?'shared.port':'sw'}.postMessage(${JSON.stringify(p)});true`);
  await guard(false);await post({id:`e-${kind}-control`});await delivered(`e-${kind}-control`);
  await post({open:true,id:`e-${kind}-socket`});await delivered(`e-${kind}-socket`,'ws-open');
  await post({ws:true,id:`e-${kind}-ws-control`});await delivered(`e-${kind}-ws-control`,'ws-message');
  const barrier=await guard();await post({id:`e-${kind}-held`});await pending(`e-${kind}-held`);await zero(`e-${kind}-held`);await approve(`e-${kind}-held`);await delivered(`e-${kind}-held`);
  await post({ws:true,id:`e-${kind}-ws-held`});const m=await pending(`e-${kind}-socket`,'ws-message');await delay(300);assert.equal(c.arrivals(`e-${kind}-ws-held`,'ws-message').length,0);await control('approve',{id:m.id});await delivered(`e-${kind}-ws-held`,'ws-message');
  // Close reasons can contain data; require the pinned-core hook as well.
  await post({close:true,id:`e-${kind}-close-held`});const cl=await pending(`e-${kind}-socket`,'ws-control');await delay(200);assert.equal(c.arrivals(`e-${kind}-close-held`,'ws-close').length,0);await control('approve',{id:cl.id});await delivered(`e-${kind}-close-held`,'ws-close');log('Q2_EXISTING_WORKER_SOCKET',{kind,barrier,message:m,close:cl});
 }
 await guard(false);await ev("ws('e-page-socket');true");await delivered('e-page-socket','ws-open');await ev("sockets['e-page-socket'].send('e-page-ws-control');true");await delivered('e-page-ws-control','ws-message');await guard();await ev("sockets['e-page-socket'].send('e-page-ws-held');true");const p=await pending('e-page-socket','ws-message');assert.equal(c.arrivals('e-page-ws-held','ws-message').length,0);await control('approve',{id:p.id});await delivered('e-page-ws-held','ws-message');
 // HTTP/2 connection remains live across guard activation.
 await guard(false);await ev("fetch('https://fixture.test:18443/receive?case=e-h2-control',{method:'POST',body:'h2'}).catch(()=>{});true");await delivered('e-h2-control');await guard();await ev("fetch('https://fixture.test:18443/receive?case=e-h2-held',{method:'POST',body:'h2'}).catch(()=>{});true");await pending('e-h2-held');await zero('e-h2-held');await approve('e-h2-held');await delivered('e-h2-held');assert.equal(rows('e-h2-held').find(r=>r.kind==='headers').protocol,'2.0');log('Q2_HTTP2',{receiver:rows('e-h2-held')});
 // Attribution cannot act as permission. DNR overwrites a caller's forgery.
 await rpc('Check.tag',{documentId:'synthetic-generation-A'});await context();await send('e-forged','forged', {headers:{'x-ares-check':'forged'}});const forged=await pending('e-forged');assert.equal(forged.attribution,'current');await zero('e-forged');await approve('e-forged');await delivered('e-forged');assert.equal(rows('e-forged').find(r=>r.kind==='headers').attributionPresent,false);
 await rpc('Check.untag');await control('context',{tokens:[]});
 for(const [name,headers]of [['missing',{}],['stale',{'x-ares-check':'stale-generation'}]]){await send('e-'+name,name,{headers});const held=await pending('e-'+name);assert.equal(held.attribution,'uncertain');await zero('e-'+name);await control('cancel',{id:held.id});log('Q3_ATTRIBUTION',{name,held});}
 // A new document/account context cannot reuse an older approval.
 await send('e-context-old','old');const old=await pending('e-context-old');await control('context',{tokens:[]});await assert.rejects(()=>control('approve',{id:old.id}),/CONTEXT_CHANGED/);await control('cancel',{id:old.id});await zero('e-context-old');log('Q5_CONTEXT_REVALIDATION',{old,rejected:true});
 for(const variant of ['same','body','headers','account']){
  await positive(`e-race-${variant}-control`,'approved',{headers:{'x-synthetic-account':'A','x-synthetic-header':'one'}});
  await guard();const a=`e-race-${variant}-approved`,b=`e-race-${variant}-competitor`;
  // Case label differs only for independent receiver attribution; same-body
  // competition is additionally tested with identical URL below.
  await send(a,'approved',{headers:{'x-synthetic-account':'A','x-synthetic-header':'one'}});await send(b,variant==='body'?'different':'approved',{headers:{'x-synthetic-account':variant==='account'?'B':'A','x-synthetic-header':variant==='headers'?'two':'one'}});
  const ap=await pending(a),bp=await pending(b);await zero(a);await zero(b);await control('approve',{id:ap.id});await delivered(a);await zero(b);await control('cancel',{id:bp.id});log('Q5_COMPETITION',{variant,approved:ap,competitor:bp});
 }
 await guard();await ev("send('e-identical','same');send('e-identical','same');true");await c.eventually(async()=>(await control('state')).rows.filter(r=>r.case==='e-identical'&&r.status==='held').length===2,'two identical captured operations');const twins=(await control('state')).rows.filter(r=>r.case==='e-identical'&&r.status==='held');assert.equal(twins[0].sha256,twins[1].sha256);await control('approve',{id:twins[0].id});await delivered('e-identical');await control('cancel',{id:twins[1].id});log('Q5_IDENTICAL',{twins,receiver:rows('e-identical')});
 // Binary, multipart disk picker, compression and large finite upload.
 await guard(false);const disk=c.work+'/synthetic-upload.bin';c.fs.writeFileSync(disk,'SYNTHETIC_DISK_FILE_17E\n');await rpc('Page.bringToFront');const box=await ev("(()=>{const b=document.querySelector('#upload').getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2}})()");await rpc('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...box});await rpc('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...box});await delay(700);await c.key('ctrl+l');c.x('type','--clearmodifiers',disk);await c.key('Return');await delay(500);await c.key('Return');await c.eventually(()=>ev("document.querySelector('#upload').files.length===1"),'real disk file selected');await c.screenshot(c.out,'real-file-picker');
 const bodies={binary:"new Uint8Array([0,1,128,255,42])",multipart:"(()=>{const f=new FormData();f.append('file',document.querySelector('#upload').files[0]);return f})()",large:"new Uint8Array(25*1024*1024).fill(42)",compressed:"await new Response(new Blob(['synthetic gzip']).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer()"};
 for(const [kind,body]of Object.entries(bodies)){
  for(const held of [false,true]){const id=`e-body-${kind}-${held?'held':'control'}`;await guard(held);await ev(`(async()=>{const body=${body};const bytes=body instanceof FormData?await new Response(body).arrayBuffer():body;globalThis.expectedBody=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));send('${id}',body,${kind==='compressed'?"{headers:{'content-encoding':'gzip'}}":"{}"});return true})()`);if(held){await pending(id);await zero(id);await approve(id);}await delivered(id);if(kind!=='multipart'){const expected=await ev("expectedBody.map(x=>x.toString(16).padStart(2,'0')).join('')");assert.equal(c.arrivals(id)[0].sha256,expected);}log('Q4_BODY',{kind,held,receiver:rows(id)});}
 }
 await guard();await ev("send('e-oversized',new Uint8Array(34*1024*1024));true");await delay(1500);await zero('e-oversized');log('Q4_OVERSIZE',{page:await ev("results['e-oversized']"),receiver:rows('e-oversized')});
 // Proxy outage has no direct fallback.
 await c.stopProxy();await send('e-proxy-down');await delay(900);await zero('e-proxy-down');log('Q1_PROXY_DOWN',{page:await ev("results['e-proxy-down']"),receiver:rows('e-proxy-down')});await c.startProxy();assert.equal((await control('state')).guard,true);
 await (await import('./wire.mjs')).default(c);
}
