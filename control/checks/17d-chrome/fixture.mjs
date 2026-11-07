import http from 'node:http';
import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {WebSocketServer} from '../17-chrome/node_modules/ws/wrapper.mjs';
export async function fixture(out,work,getUpdate){
 const rows=[];let workerVersion=1;
 const record=row=>{row={...row,at:Date.now()};rows.push(row);fs.appendFileSync(out+'/server.jsonl',JSON.stringify(row)+'\n');};
 const server=http.createServer(async(req,res)=>{
  const u=new URL(req.url,'http://localhost');res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Cache-Control','no-store');
  if(u.pathname==='/update.xml'){res.setHeader('Content-Type','text/xml');return res.end(getUpdate())}
  if(u.pathname==='/extension.crx')return fs.createReadStream(work+'/own-extension.crx').pipe(res);
  if(u.pathname==='/receive'){const chunks=[];for await(const b of req)chunks.push(b);const b=Buffer.concat(chunks);record({kind:'http',case:u.searchParams.get('case'),method:req.method,url:req.url,length:b.length,sha256:createHash('sha256').update(b).digest('hex'),body:b.subarray(0,200).toString(),headers:req.headers});return res.end('received');}
  if(u.pathname==='/sw.js'||u.pathname==='/worker.js'){
   const id=u.searchParams.get('case')||'worker',shared=u.searchParams.has('shared'),sw=u.pathname==='/sw.js';record({kind:'worker-script',url:req.url,version:workerVersion});res.setHeader('Content-Type','application/javascript');res.setHeader('Service-Worker-Allowed','/');
   const source=`const version=${workerVersion},caseId=${JSON.stringify(id)};globalThis.results=[];function send(suffix){fetch('/receive?case='+caseId+'-v'+version+'-'+suffix,{method:'POST',body:'synthetic worker'}).then(()=>results.push('post-ok')).catch(e=>results.push(e.name));const w=new WebSocket('ws://'+location.host+'/socket?case='+caseId+'-v'+version+'-'+suffix);w.onopen=()=>{results.push('ws-open');w.send(JSON.stringify({case:caseId+'-v'+version+'-'+suffix}))};w.onerror=()=>results.push('ws-error');}send('first');`;
   return res.end(source+(sw?`self.addEventListener('install',e=>e.waitUntil(skipWaiting()));self.addEventListener('activate',e=>e.waitUntil(clients.claim()));self.addEventListener('message',e=>{if(e.data==='send')send('message')});self.addEventListener('sync',e=>{send('sync');e.waitUntil(Promise.resolve())});self.addEventListener('push',e=>send('push'));`:shared?`onconnect=e=>{const p=e.ports[0];p.onmessage=e=>{if(e.data==='send')send('message');p.postMessage({version,results})};p.start();p.postMessage({version,results})};`:`onmessage=e=>{if(e.data==='send')send('message');postMessage({version,results})};`));
  }
  if(u.pathname==='/page.js'){res.setHeader('Content-Type','application/javascript');return res.end(fs.readFileSync(new URL('./page.js',import.meta.url)));}
  record({kind:'document',url:req.url,host:req.headers.host});res.setHeader('Content-Type','text/html');
  const startup=u.pathname==='/startup'?`<script>fetch('/receive?case=startup-same',{method:'POST',body:'synthetic first'}).catch(()=>{});fetch('http://localhost:'+location.port+'/receive?case=startup-cross',{method:'POST',body:'synthetic first cross'}).catch(()=>{});window.firstAct=Date.now();</script>`:'';
  res.end(`<!doctype html>${startup}<meta charset="utf-8"><title>17d synthetic fixture</title><h1>Chrome floor check</h1><span id="account">synthetic-A</span><button id="queue">Queue deletion offline</button><button id="owner">Owner send</button><a id="read" href="#reading">Read section</a><pre id="status">ready</pre><script src="/page.js"></script>`);
 });
 const ws=new WebSocketServer({server,path:'/socket'});ws.on('connection',(s,req)=>{const id=new URL(req.url,'http://localhost').searchParams.get('case');record({kind:'ws-open',case:id});s.on('message',data=>record({kind:'ws-message',case:JSON.parse(data).case,body:data.toString()}));});
 await new Promise(r=>server.listen(0,'127.0.0.1',r));return {base:'http://127.0.0.1:'+server.address().port,rows,bump(){workerVersion++;return workerVersion},close(){for(const c of ws.clients)c.terminate();ws.close();server.closeAllConnections();server.close();}};
}
