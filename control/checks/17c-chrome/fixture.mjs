import http from 'node:http';
import fs from 'node:fs';
import {WebSocketServer} from '../17-chrome/node_modules/ws/wrapper.mjs';
export async function fixture(out,work,getUpdate){
 const arrivals=[];const record=row=>{row={...row,at:Date.now()};arrivals.push(row);fs.appendFileSync(out+'/server.jsonl',JSON.stringify(row)+'\n')};
 const server=http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://localhost');res.setHeader('Access-Control-Allow-Origin','*');
  if(u.pathname==='/update.xml'){record({kind:'update',url:req.url});res.setHeader('Content-Type','text/xml');return res.end(getUpdate())}
  if(u.pathname==='/extension.crx')return fs.createReadStream(work+'/own-extension.crx').pipe(res);
  if(['/receive','/receipt'].includes(u.pathname)){let body='';for await(const b of req)body+=b;record({kind:u.pathname==='/receipt'?'rtc':'http',case:u.searchParams.get('case'),url:req.url,method:req.method,body:body||u.searchParams.get('body')});return res.end('received')}
  if(u.pathname==='/worker.js'||u.pathname==='/sw.js'){
   record({kind:'worker-script',url:req.url});
   res.setHeader('Content-Type','application/javascript');
   const id=u.searchParams.get('case')||'worker-first',type=u.searchParams.get('type');
   const send=`fetch('/receive?case=${id}',{method:'POST',body:'synthetic worker first'}).catch(()=>{});`;
   return res.end(type==='shared'?`onconnect=e=>{const p=e.ports[0];p.onmessage=e=>{fetch(e.data.url,{method:'POST',body:e.data.body}).catch(()=>{})};p.start();${send}}`:u.pathname==='/sw.js'?`${send}self.addEventListener('install',e=>e.waitUntil(skipWaiting()));self.addEventListener('activate',e=>e.waitUntil(clients.claim()));self.addEventListener('message',e=>e.waitUntil(fetch(e.data.url,{method:'POST',body:e.data.body}).catch(()=>{})));`:`${send}onmessage=e=>fetch(e.data.url,{method:'POST',body:e.data.body}).catch(()=>{});`)
  }
  record({kind:'document',url:req.url});res.setHeader('Content-Type','text/html');res.end(`<!doctype html><meta charset="utf-8"><title>17c synthetic fixture</title><h1>Page holding check</h1><input id="text"><button id="action">Queue synthetic work</button><button id="flush">Refresh list</button><button id="chat">Chat click</button><button id="cause">Cause test</button><output id="status">ready</output><form method="POST" action="/receive"><input name="value" value="synthetic form"><button>Submit</button></form><script>
  window.states=[];window.mark=s=>{states.push(s);document.querySelector('#status').textContent=s};window.caseId='unset';
  const url=id=>'/receive?case='+id;
  window.send=(id,kind='fetch')=>{mark('waiting '+id);if(kind==='xhr'){const r=new XMLHttpRequest();r.open('POST',url(id));r.onload=()=>mark('done '+id);r.onerror=()=>mark('error '+id);r.send('synthetic xhr');return}if(kind==='beacon'){mark('beacon accepted '+navigator.sendBeacon(url(id),'synthetic beacon'));return}if(kind.startsWith('form')){const f=document.forms[0];f.action=url(id);kind==='form-submit'?f.submit():kind==='form-event'?f.querySelector('button').click():f.requestSubmit();return}if(kind==='ws'){ws.send(JSON.stringify({case:id,text:'synthetic ws'}));return}if(kind==='rtc'){channel.send(JSON.stringify({case:id,text:'synthetic rtc'}));return}if(kind==='writer'){writer.write(new TextEncoder().encode(JSON.stringify({case:id,text:'synthetic wt'})));return}fetch(url(id),{method:'POST',body:'synthetic fetch'}).then(()=>mark('done '+id)).catch(e=>mark(e.name+' '+id));};
  window.connectWS=()=>{window.ws=new WebSocket('ws://'+location.host+'/socket');return new Promise(r=>ws.onopen=r)};
  window.rtc=async()=>{window.a=new RTCPeerConnection({iceServers:[]});window.b=new RTCPeerConnection({iceServers:[]});a.onicecandidate=e=>e.candidate&&b.addIceCandidate(e.candidate);b.onicecandidate=e=>e.candidate&&a.addIceCandidate(e.candidate);window.channel=a.createDataChannel('synthetic');b.ondatachannel=e=>{e.channel.onmessage=m=>{const d=JSON.parse(m.data);fetch('/receipt?case='+d.case+'&body='+encodeURIComponent(m.data))}};await a.setLocalDescription(await a.createOffer());await b.setRemoteDescription(a.localDescription);await b.setLocalDescription(await b.createAnswer());await a.setRemoteDescription(b.localDescription);};
  document.querySelector('#chat').onclick=()=>{ws.send(JSON.stringify({case:caseId+'-presence',presence:'active'}));ws.send(JSON.stringify({case:caseId+'-subscription',subscribe:'synthetic-room'}));ws.send(JSON.stringify({case:caseId+'-typing',typing:true}));};document.querySelector('#text').onkeydown=e=>{if(e.key==='Enter')ws.send(JSON.stringify({case:caseId+'-message',text:e.target.value}))};
  document.querySelector('#action').onclick=()=>localStorage.setItem('queue','synthetic queued deletion 42');
  document.querySelector('#flush').onclick=()=>{const body=localStorage.getItem('queue');if(body)fetch(url(caseId),{method:'POST',body}).catch(()=>{})};
  setInterval(()=>{if(window.timerFlush&&localStorage.getItem('queue')){timerFlush=false;document.querySelector('#flush').click()}},100);
  window.causeTest=(kind,id)=>{caseId=id;document.querySelector('#cause').onclick=function action17c(){const run=()=>fetch(url(id),{method:'POST',body:'synthetic cause'}).catch(()=>{});if(kind==='timer')setTimeout(run,80);else if(kind==='promise')Promise.resolve().then(run);else if(kind==='mutation'){const o=new MutationObserver(()=>{o.disconnect();run()});o.observe(document.querySelector('#status'),{childList:true});mark('mutated')}else if(kind==='postMessage'){addEventListener('message',function h(e){if(e.data==='cause17c'){removeEventListener('message',h);run()}});postMessage('cause17c','*')}else if(kind==='worker'){const w=new Worker('/worker.js?case='+id+'-first');w.postMessage({url:url(id),body:'synthetic worker cause'})}else run()};};
  window.startup=${u.pathname==='/startup'};if(startup)fetch('/receive?case=restored-startup',{method:'POST',body:'synthetic startup'}).catch(()=>{});
  if(${JSON.stringify(u.searchParams.get('auto'))})send(${JSON.stringify(u.searchParams.get('auto'))});
  </script>`);
 });
 const ws=new WebSocketServer({server,path:'/socket'});ws.on('connection',s=>s.on('message',data=>{let value;try{value=JSON.parse(data)}catch{value={case:'unparsed',text:data.toString()}}record({kind:'ws',case:value.case,body:data.toString()})}));
 await new Promise(r=>server.listen(0,'127.0.0.1',r));return {base:'http://127.0.0.1:'+server.address().port,arrivals,close(){for(const c of ws.clients)c.terminate();ws.close();server.closeAllConnections();server.close()}};
}
