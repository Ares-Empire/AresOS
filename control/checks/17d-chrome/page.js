// Synthetic fixture, never loaded on a public site.
window.events=[];const mark=(kind,value)=>{events.push({kind,value,at:Date.now()});document.querySelector('#status').textContent=JSON.stringify(events.slice(-4));};
document.addEventListener('click',e=>mark('click',{id:e.target.id,trusted:e.isTrusted}),true);
window.attempt=(id,kind='fetch',cross=false)=>{
 const url=(cross?'http://localhost:'+location.port:'')+'/receive?case='+id;mark('attempt',{id,kind,cross});
 if(kind==='xhr'){const r=new XMLHttpRequest();r.open('POST',url);r.onload=()=>mark('xhr-ok',id);r.onerror=()=>mark('xhr-error',id);r.send('synthetic xhr');}
 else if(kind==='beacon')mark('beacon-return',navigator.sendBeacon(url,'synthetic beacon'));
 else if(kind==='form'){const form=document.createElement('form');form.method='POST';form.action=url;const i=document.createElement('input');i.name='data';i.value='synthetic form';form.append(i);document.body.append(form);form.submit();}
 else if(kind==='ping'){const a=document.createElement('a');a.href='#reading';a.ping=url;a.textContent='reading';document.body.append(a);a.click();}
 else if(kind==='ws'){const s=new WebSocket('ws://'+location.host+'/socket?case='+id);s.onopen=()=>mark('ws-open',id);s.onerror=()=>mark('ws-error',id);window.lastSocket=s;}
 else fetch(url,{method:'POST',body:'synthetic fetch'}).then(()=>mark('fetch-ok',id)).catch(e=>mark(e.name,id));
 return true;
};
window.db17=()=>new Promise((resolve,reject)=>{const r=indexedDB.open('synthetic17d',1);r.onupgradeneeded=()=>r.result.createObjectStore('outbox');r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error);});
window.queue17=async()=>{const db=await db17();await new Promise((resolve,reject)=>{const t=db.transaction('outbox','readwrite');t.objectStore('outbox').put({delete:42},'pending');t.oncomplete=resolve;t.onerror=reject});db.close();mark('queued',42);};
window.flush17=async id=>{const db=await db17();const value=await new Promise(r=>{const q=db.transaction('outbox').objectStore('outbox').get('pending');q.onsuccess=()=>r(q.result)});db.close();return fetch('/receive?case='+id,{method:'POST',body:JSON.stringify(value)}).catch(()=>{});};
document.querySelector('#queue').onclick=()=>queue17();document.querySelector('#owner').onclick=()=>fetch('/receive?case=owner-notification',{method:'POST',body:'synthetic owner'}).then(()=>mark('owner-sent',true));
window.setAccount17=async account=>{const data=await (await fetch('/session?account='+account)).json();document.querySelector('#account').textContent=data.account;return true;};
document.querySelector('#signout').onclick=()=>setAccount17('synthetic-signed-out');document.querySelector('#signinB').onclick=()=>setAccount17('synthetic-B');
window.write17=async kind=>{
 const at=Date.now();let result='ok';
 try{
  if(kind==='localStorage')localStorage.setItem('synthetic17d','deletion 42');
  if(kind==='sessionStorage')sessionStorage.setItem('synthetic17d','deletion 42');
  if(kind==='indexedDB')await queue17();
  if(kind==='cache'){const c=await caches.open('synthetic17d');await c.put('/synthetic-cached',new Response('deletion 42'));}
  if(kind==='cookie')document.cookie='synthetic17d=deletion42; SameSite=Lax; path=/';
  if(kind==='opfs'){const root=await navigator.storage.getDirectory(),file=await root.getFileHandle('synthetic17d',{create:true}),w=await file.createWritable();await w.write('deletion 42');await w.close();}
  if(kind==='broadcast'){const b=new BroadcastChannel('synthetic17d');b.postMessage({delete:42});b.close();}
  if(kind==='window'){const i=document.createElement('iframe');i.src='/';await new Promise(r=>{i.onload=r;document.body.append(i)});i.contentWindow.postMessage({delete:42},'*');window.handoffFrame=i;}
  if(kind==='dedicated'){const w=new Worker('/worker.js?case=handoff-dedicated');w.postMessage({delete:42});window.handoffWorker=w;}
  if(kind==='shared'){const w=new SharedWorker('/worker.js?shared&case=handoff-shared');w.port.start();w.port.postMessage({delete:42});window.handoffShared=w;}
  if(kind==='registration')await navigator.serviceWorker.register('/sw.js?case=storage-sw');
  if(kind==='sync'){const r=await navigator.serviceWorker.ready;await r.sync.register('synthetic17d');}
  if(kind==='periodicSync'){const r=await navigator.serviceWorker.ready;await r.periodicSync.register('synthetic17d',{minInterval:3600000});}
 }catch(e){result=e.name+': '+e.message;}
 return {kind,at,done:Date.now(),result};
};
