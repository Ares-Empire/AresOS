// Q1-Q5: every operation has a receiver-side positive control.
export default async function(c){
 const {ev,rpc,guard,positive,send,delivered,zero,pending,approve,control,log,assert,delay,f,rows,context}=c;
 // Explicitly ignore all browser proxy configuration in a process with the
 // browser's uid. This distinguishes kernel containment from policy obedience.
 for(const enforced of [false,true]){
  c.firewall(enforced);
  for(const [family,host]of [[4,'127.0.0.1'],[6,'::1'],[4,'localhost'],[4,'169.254.17.1']]){
   const id=`e-kernel-${host.replaceAll(':','v').replaceAll('.','-')}-${enforced?'blocked':'control'}`;
   const source="import socket,sys;s=socket.socket(socket.AF_INET6 if sys.argv[1]=='6' else socket.AF_INET);s.settimeout(1);s.connect((sys.argv[2],18081));s.sendall(('GET /receive?case='+sys.argv[3]+' HTTP/1.1\\r\\nHost: fixture\\r\\nConnection: close\\r\\n\\r\\n').encode());s.recv(100)";
   const result=await new Promise(resolve=>{const p=c.spawn('sudo',['-u','areschrome','python3','-c',source,String(family),host,id],{stdio:'ignore'});p.on('exit',code=>resolve({code}))});
   if(enforced)await zero(id);else await delivered(id);log('Q1_KERNEL_BYPASS',{enforced,host,result,receiver:rows(id)});
  }
 }
 await positive('e-basic-control');await guard();await send('e-basic-held');await pending('e-basic-held');await zero('e-basic-held');const op=await approve('e-basic-held');await delivered('e-basic-held');await assert.rejects(()=>control('approve',{id:op.id}),/NOT_PENDING/);log('Q4_EXACT_HTTP',{op,receiver:rows('e-basic-held')});
 await guard(false);await ev("ws('e-handshake-control');true");await delivered('e-handshake-control','ws-open');await guard();await ev("ws('e-handshake-held');true");const handshake=await pending('e-handshake-held','handshake');await zero('e-handshake-held');await control('approve',{id:handshake.id});await delivered('e-handshake-held','ws-open');log('Q4_HANDSHAKE',{handshake,receiver:rows('e-handshake-held')});
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
  await post({ws:true,id:`e-${kind}-ws-held`});const m=await pending(`e-${kind}-socket`,'ws-message');await delay(300);assert.equal(c.arrivals(`e-${kind}-ws-held`,'ws-message').length,0);await control('approve',{id:m.id});await delivered(`e-${kind}-ws-held`,'ws-message');assert.equal(c.arrivals(`e-${kind}-ws-held`,'ws-message')[0].sha256,m.sha256);
  // Close reasons can contain data; require the pinned-core hook as well.
  await post({close:true,id:`e-${kind}-close-held`});const cl=await pending(`e-${kind}-socket`,'ws-control');await delay(200);assert.equal(c.arrivals(`e-${kind}-close-held`,'ws-close').length,0);await control('approve',{id:cl.id});await delivered(`e-${kind}-close-held`,'ws-close');assert.equal(c.arrivals(`e-${kind}-close-held`,'ws-close')[0].sha256,cl.payloadSha256);log('Q2_EXISTING_WORKER_SOCKET',{kind,barrier,message:m,close:cl});
 }
 await guard(false);await ev("ws('e-page-socket');true");await delivered('e-page-socket','ws-open');await ev("sockets['e-page-socket'].send('e-page-ws-control');true");await delivered('e-page-ws-control','ws-message');await guard();await ev("sockets['e-page-socket'].send('e-page-ws-held');true");const p=await pending('e-page-socket','ws-message');assert.equal(c.arrivals('e-page-ws-held','ws-message').length,0);await control('approve',{id:p.id});await delivered('e-page-ws-held','ws-message');
 await guard(false);await ev("globalThis.concurrent17=0;globalThis.traffic17=setInterval(()=>{const id='e-concurrent-'+(++concurrent17);send(id);sockets['e-page-socket'].send(id)},25);true");await delay(140);const barrier=await guard();await delay(280);await ev('clearInterval(traffic17);true');
 const concurrent=(await control('state')).rows.filter(r=>(r.case.startsWith('e-concurrent-')||r.case==='e-page-socket')&&r.status==='held');
 assert.ok(concurrent.some(r=>r.kind==='http'));assert.ok(concurrent.some(r=>r.kind==='ws-message'));
 for(const r of concurrent){if(r.kind==='http')assert.equal(rows(r.case).filter(v=>v.kind==='headers').length,0);await control('cancel',{id:r.id});}
 await ev("sockets['e-page-socket'].close();true");
 for(let i=0;i<35;i++){const queued=(await control('state')).rows.filter(r=>(r.case.startsWith('e-concurrent-')||r.case==='e-page-socket')&&r.status==='held');for(const r of queued)await control('cancel',{id:r.id});await delay(40);}
 log('Q2_CONCURRENT_BARRIER',{barrier,captured:concurrent,receiver:c.f.rows.filter(r=>r.case?.startsWith('e-concurrent-'))});
 // HTTP/2 connection remains live across guard activation.
 await guard(false);await ev("fetch('https://fixture.test:18443/receive?case=e-h2-control',{method:'POST',body:'h2'}).catch(()=>{});true");await delivered('e-h2-control');await guard();await ev("fetch('https://fixture.test:18443/receive?case=e-h2-held',{method:'POST',body:'h2'}).catch(()=>{});true");await pending('e-h2-held');await zero('e-h2-held');await approve('e-h2-held');await delivered('e-h2-held');assert.equal(rows('e-h2-held').find(r=>r.kind==='headers').protocol,'2.0');log('Q2_HTTP2',{receiver:rows('e-h2-held')});
 // Attribution cannot act as permission. DNR overwrites a caller's forgery.
 await rpc('Check.tag',{documentId:'synthetic-generation-A'});await context();await send('e-forged','forged', {headers:{'x-ares-check':'forged'}});const forged=await pending('e-forged');assert.equal(forged.attribution,'current');await zero('e-forged');await approve('e-forged');await delivered('e-forged');assert.equal(rows('e-forged').find(r=>r.kind==='headers').attributionPresent,false);
 const previousToken=(await rpc('Check.state')).documents.find(d=>d.tabId===c.selected).value;await rpc('Check.tag',{documentId:'synthetic-generation-B'});await context();await rpc('Check.untag');
 for(const [name,headers]of [['missing',{}],['stale',{'x-ares-check':previousToken}]]){await send('e-'+name,name,{headers});const held=await pending('e-'+name);assert.equal(held.attribution,'uncertain');await zero('e-'+name);await control('cancel',{id:held.id});log('Q3_ATTRIBUTION',{name,held});}
 await guard(false);
 await ev(`(()=>{globalThis.foreign17=document.createElement('iframe');foreign17.src='http://localhost:18081/';document.body.append(foreign17);globalThis.opaque17=document.createElement('iframe');opaque17.sandbox='allow-scripts';opaque17.srcdoc='<script>onmessage=e=>fetch("http://127.0.0.1:18081/receive?case="+e.data,{method:"POST",body:e.data}).catch(()=>{})<'+ '/script>';document.body.append(opaque17);return true})()`);await delay(800);
 for(const kind of ['foreign','opaque'])for(const held of [false,true]){
  const id=`e-frame-${kind}-${held?'held':'control'}`;await guard(held);await ev(`${kind==='foreign'?'foreign17':'opaque17'}.contentWindow.postMessage('${id}','*');true`);if(held){await pending(id);await zero(id);await approve(id);}await delivered(id);log('Q3_FRAME_HANDOFF',{kind,held,receiver:rows(id)});
 }
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
 await guard(false);const disk=c.work+'/synthetic-upload.bin';c.fs.writeFileSync(disk,'SYNTHETIC_DISK_FILE_17E\n');await rpc('Page.bringToFront');
 const box=await ev("(()=>{const b=document.querySelector('#upload').getBoundingClientRect();return {x:screenX+b.x+35,y:screenY+outerHeight-innerHeight+b.y+b.height/2}})()");
 await rpc('Check.detach');c.x('mousemove',Math.round(box.x),Math.round(box.y),'click',1);
 await c.eventually(()=>/^(Open File|Open|Select File|Choose File)$/i.test(c.x('getactivewindow','getwindowname')),'native file picker visible',15000);
 await c.screenshot(c.out,'real-file-picker');await c.key('ctrl+l');await delay(300);c.x('type','--clearmodifiers','--delay','1',disk);await delay(700);await c.screenshot(c.out,'real-file-picker-path');c.x('mousemove',1233,895,'click',1);await delay(700);
 await rpc('Check.attach',{tabId:c.selected});await c.eventually(()=>ev("document.querySelector('#upload').files.length===1"),'real disk file selected');await c.screenshot(c.out,'real-file-selected');
 const bodies={binary:"new Uint8Array([0,1,128,255,42])",multipart:"(()=>{const f=new FormData();f.append('file',document.querySelector('#upload').files[0]);return f})()",large:"new Uint8Array(25*1024*1024).fill(42)",compressed:"await new Response(new Blob(['synthetic gzip']).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer()"};
 for(const [kind,body]of Object.entries(bodies)){
  for(const held of [false,true]){const id=`e-body-${kind}-${held?'held':'control'}`;await guard(held);await ev(`(async()=>{const body=${body};const bytes=body instanceof FormData?await new Response(body).arrayBuffer():body;globalThis.expectedBody=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)));send('${id}',body,${kind==='compressed'?"{headers:{'content-encoding':'gzip'}}":"{}"});return true})()`);let captured;if(held){captured=await pending(id);await zero(id);await approve(id);}await delivered(id);if(captured)assert.equal(c.arrivals(id)[0].sha256,captured.bodySha256);if(kind==='multipart')assert.equal(c.arrivals(id)[0].diskMarker,true);if(kind!=='multipart'){const expected=await ev("expectedBody.map(x=>x.toString(16).padStart(2,'0')).join('')");assert.equal(c.arrivals(id)[0].sha256,expected);}log('Q4_BODY',{kind,held,receiver:rows(id)});}
 }
 await guard();await ev("for(let i=0;i<3;i++)send('e-buffer-limit-'+i,new Uint8Array(25*1024*1024).fill(42));true");
 const limited=await c.eventually(()=>{const events=c.sudo('cat',c.work+'/private/events.jsonl').trim().split('\n').map(JSON.parse);return events.find(r=>r.case?.startsWith('e-buffer-limit-')&&r.reason==='buffer-limit')},'aggregate buffer refusal');
 const buffered=(await control('state')).rows.filter(r=>r.case.startsWith('e-buffer-limit-')&&r.status==='held');assert.equal(buffered.length,2);for(let i=0;i<3;i++)await zero('e-buffer-limit-'+i);for(const op of buffered)await control('cancel',{id:op.id});log('Q11_AGGREGATE_BUFFER_LIMIT',{held:buffered.length,refusal:limited,positiveControl:'e-body-large-control'});
 await ev("send('e-oversized',new Uint8Array(34*1024*1024));true");await c.eventually(()=>ev("typeof results['e-oversized']==='string'"),'oversized input visibly fails to the page');await zero('e-oversized');log('Q4_OVERSIZE',{page:await ev("results['e-oversized']"),receiver:rows('e-oversized')});
 // Proxy outage has no direct fallback.
 await c.stopProxy();await send('e-proxy-down');await delay(900);await zero('e-proxy-down');log('Q1_PROXY_DOWN',{page:await ev("results['e-proxy-down']"),receiver:rows('e-proxy-down')});await c.startProxy();assert.equal((await control('state')).guard,true);
 await (await import('./wire.mjs')).default(c);
}
