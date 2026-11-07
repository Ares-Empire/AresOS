import fs from 'node:fs';
import http from 'node:http';
import https from 'node:https';
import http2 from 'node:http2';
import {createHash} from 'node:crypto';
import {WebSocketServer} from '../17-chrome/node_modules/ws/wrapper.mjs';
export async function fixture(work,out,getUpdate){
 const rows=[];const hash=b=>createHash('sha256').update(b).digest('hex');
 const record=row=>{row={at:Date.now(),...row};rows.push(row);fs.appendFileSync(out+'/receiver.jsonl',JSON.stringify(row)+'\n');};
 const handler=async(req,res)=>{
  const u=new URL(req.url,'http://fixture');const id=u.searchParams.get('case')||'';
  res.setHeader('Cache-Control','no-store');res.setHeader('Access-Control-Allow-Origin','*');res.setHeader('Access-Control-Allow-Headers','*');
  if(u.pathname==='/update.xml'){res.setHeader('Content-Type','text/xml');return res.end(getUpdate());}
  if(u.pathname==='/extension.crx')return fs.createReadStream(work+'/own-extension.crx').pipe(res);
  if(u.pathname==='/receive'){
   // Header arrival is recorded before any body byte. No cookie/header values
   // or bodies are logged, including on public-site runs.
   record({kind:'headers',case:id,method:req.method,protocol:req.httpVersion,attributionPresent:'x-ares-check' in req.headers,accountHash:hash(req.headers['x-synthetic-account']||''),headerHash:hash(req.headers['x-synthetic-header']||'')});
   let length=0;const sha=createHash('sha256');
   req.on('data',b=>{if(!length)record({kind:'first-byte',case:id});length+=b.length;sha.update(b)});
   req.on('aborted',()=>record({kind:'aborted',case:id,length}));
   req.on('end',()=>{record({kind:'http',case:id,length,sha256:sha.digest('hex')});res.end('received')});return;
  }
  if(u.pathname==='/redirect'){res.writeHead(307,{Location:`http://localhost:18081/receive?case=${id}`});return res.end();}
  if(u.pathname==='/hsts'){res.setHeader('Strict-Transport-Security','max-age=10000');return res.end('HSTS fixture');}
  if(u.pathname==='/worker.js'||u.pathname==='/sw.js'){
   res.setHeader('Content-Type','application/javascript');res.setHeader('Service-Worker-Allowed','/');
   return res.end(`let socket;function act(p){if(p.open){socket=new WebSocket('ws://127.0.0.1:18081/socket?case='+p.id);socket.onopen=()=>postResult('open')}else if(p.close)socket.close(1000,p.id);else if(p.ws)socket.send(p.id);else fetch('/receive?case='+p.id,{method:'POST',body:p.id}).catch(()=>{})}function postResult(v){globalThis.result=v}onmessage=e=>act(e.data);onconnect=e=>{e.ports[0].onmessage=e=>act(e.data);e.ports[0].start()};self.addEventListener('install',e=>e.waitUntil(skipWaiting()));self.addEventListener('activate',e=>e.waitUntil(clients.claim()));`);
  }
  res.setHeader('Content-Type','text/html');
  res.end(`<!doctype html><meta charset="utf-8"><title>17e synthetic signed-in fixture</title><h1>Checkpoint fixture</h1><p>Synthetic account A</p><input type="file" id="upload"><pre id="status">ready</pre><script>
  globalThis.results={};globalThis.sockets={};
  function send(id,body=id,extra={}){fetch('/receive?case='+id,{method:'POST',body,...extra}).then(r=>results[id]='HTTP '+r.status,e=>results[id]=e.name);return true}
  function ws(id){const s=new WebSocket('ws://127.0.0.1:18081/socket?case='+id);sockets[id]=s;s.onopen=()=>results[id]='open';s.onerror=()=>results[id]='error';return true}
  function transports(wt){return (async()=>{const r={};try{const t=new WebTransport(wt.url+'?case=e-webtransport',{serverCertificateHashes:[{algorithm:'sha-256',value:new Uint8Array(wt.hash)}]});await Promise.race([t.ready,new Promise((_,j)=>setTimeout(()=>j(Error('timeout')),5000))]);const w=t.datagrams.writable.getWriter();await w.write(new TextEncoder().encode('e-webtransport'));r.wt='delivered';t.close()}catch(e){r.wt=e.name+':'+e.message}return r})()}
  function rtc(config){return (async()=>{const p=new RTCPeerConnection(config);const d=p.createDataChannel('synthetic');globalThis.peer=p;const offer=await p.createOffer();await p.setLocalDescription(offer);await new Promise(r=>{if(p.iceGatheringState==='complete')return r();p.onicegatheringstatechange=()=>{if(p.iceGatheringState==='complete')r()};setTimeout(r,4500)});return p.localDescription.sdp})()}
  </script>`);
 };
 const servers=[];const sockets=[];
 const plain=http.createServer(handler);await new Promise(r=>plain.listen(18081,'0.0.0.0',r));servers.push(plain);
 const v6=http.createServer(handler);await new Promise(r=>v6.listen({port:18081,host:'::1',ipv6Only:true},r));servers.push(v6);
 const tls=http2.createSecureServer({allowHTTP1:true,key:fs.readFileSync(work+'/fixture.key'),cert:fs.readFileSync(work+'/fixture.pem')},handler);await new Promise(r=>tls.listen(18443,'0.0.0.0',r));servers.push(tls);
 const invalid=https.createServer({key:fs.readFileSync(work+'/bad.key'),cert:fs.readFileSync(work+'/bad.pem')},handler);await new Promise(r=>invalid.listen(18444,'0.0.0.0',r));servers.push(invalid);
 for(const server of [plain,v6,tls]){const w=new WebSocketServer({server});sockets.push(w);w.on('connection',(s,req)=>{const id=new URL(req.url,'http://fixture').searchParams.get('case');record({kind:'ws-open',case:id,attributionPresent:'x-ares-check' in req.headers});s.on('message',b=>record({kind:'ws-message',case:b.toString().startsWith('e-')?b.toString():'e-binary',length:b.length,sha256:hash(b)}));s.on('close',(code,b)=>record({kind:'ws-close',case:b.toString().startsWith('e-')?b.toString():id,code,length:b.length,sha256:hash(b)}));});}
 return {base:'http://127.0.0.1:18081',rows,record,close(){for(const w of sockets){for(const c of w.clients)c.terminate();w.close()}for(const s of servers){s.closeAllConnections?.();s.close()}}};
}
