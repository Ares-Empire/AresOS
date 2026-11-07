import http from 'node:http';
import fs from 'node:fs';
import {WebSocketServer} from '../17-chrome/node_modules/ws/wrapper.mjs';
export async function fixture(out,work,getUpdate){
  const arrivals=[];const record=r=>{const row={...r,at:Date.now()};arrivals.push(row);fs.appendFileSync(out+'/server.jsonl',JSON.stringify(row)+'\n');};
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://localhost');
    if(url.pathname==='/update.xml'){record({kind:'update',url:req.url});res.setHeader('Content-Type','text/xml');return res.end(getUpdate());}
    if(url.pathname==='/extension.crx'){record({kind:'crx',url:req.url});return fs.createReadStream(work+'/own-extension.crx').pipe(res);}
    if(url.pathname==='/receive'){let body='';for await(const b of req)body+=b;record({kind:'receive',url:req.url,method:req.method,body});res.setHeader('Access-Control-Allow-Origin','*');return res.end('received');}
    if(url.pathname==='/sw.js'){res.setHeader('Content-Type','application/javascript');return res.end(`self.addEventListener('install',e=>e.waitUntil(skipWaiting()));self.addEventListener('activate',e=>e.waitUntil(clients.claim()));self.addEventListener('fetch',e=>{if(new URL(e.request.url).pathname==='/receive')e.respondWith(fetch(e.request))});self.addEventListener('message',e=>e.waitUntil(fetch(e.data.url,{method:'POST',body:'synthetic worker'}).then(()=>e.source.postMessage('sent')).catch(()=>e.source.postMessage('failed'))));self.addEventListener('sync',e=>e.waitUntil(fetch('/receive?case='+e.tag,{method:'POST',body:'synthetic sync'})));`);}
    res.setHeader('Content-Type','text/html');res.end(`<!doctype html><title>17b synthetic fixture</title><h1>Holds check</h1><input id="text"><button id="button">Action</button><output id="status">ready</output><form method="POST" action="/receive"><input name="value" value="synthetic form"></form><script>
    window.states=[];window.mark=s=>{states.push({s,at:Date.now()});document.querySelector('#status').textContent=s};
    window.send=(id,kind='fetch',timeout=0)=>{
      const url='/receive?case='+id;mark('started '+id);
      if(kind==='volatile'){fetch(url,{method:'POST',body:JSON.stringify({text:'synthetic volatile',nonce:Date.now()})}).catch(()=>{});return;}
      if(kind==='form'){document.forms[0].action=url;document.forms[0].requestSubmit();return;}
      if(kind==='xhr'){let x=new XMLHttpRequest();x.open('POST',url);x.timeout=timeout;x.onload=()=>mark('done '+id);x.onerror=()=>mark('error '+id);x.ontimeout=()=>mark('timeout '+id);x.send('synthetic xhr');return;}
      fetch(url,{method:'POST',body:'synthetic fetch',...(timeout?{signal:AbortSignal.timeout(timeout)}:{})}).then(()=>mark('done '+id)).catch(e=>mark(e.name+' '+id));
    };
    window.delayed=(id,encoding,wait)=>{const field=document.querySelector('#text');field.oninput=()=>setTimeout(()=>{const t=field.value;const data=[t,encodeURIComponent(t),new URLSearchParams({text:t}).toString().slice(5),JSON.stringify(t).slice(1,-1),btoa(unescape(encodeURIComponent(t)))][encoding];fetch('/receive?case='+id,{method:'POST',body:data}).catch(()=>{})},wait)};
    window.retry=id=>{let done=false;fetch('/receive?case='+id+'&attempt=1',{method:'POST',body:'synthetic retry',signal:AbortSignal.timeout(1000)}).then(()=>done=true).catch(()=>mark('first timed out'));setTimeout(()=>{if(!done){mark('retry 2');fetch('/receive?case='+id+'&attempt=2',{method:'POST',body:'synthetic retry',signal:AbortSignal.timeout(10000)}).then(()=>mark('done retry')).catch(()=>mark('retry failed'))}},1000)};
    window.worker=async()=>{await navigator.serviceWorker.register('/sw.js');await navigator.serviceWorker.ready;while(!navigator.serviceWorker.controller)await new Promise(r=>setTimeout(r,20));return true};
    window.connectWS=()=>{window.ws=new WebSocket('ws://'+location.host+'/socket');ws.onopen=()=>mark('ws open');ws.onmessage=e=>mark(e.data)};
    window.rtc=async()=>{window.a=new RTCPeerConnection({iceServers:[]});window.b=new RTCPeerConnection({iceServers:[]});a.onicecandidate=e=>e.candidate&&b.addIceCandidate(e.candidate);b.onicecandidate=e=>e.candidate&&a.addIceCandidate(e.candidate);window.channel=a.createDataChannel('fixture');b.ondatachannel=e=>{e.channel.onmessage=m=>mark('rtc '+m.data)};await a.setLocalDescription(await a.createOffer());await b.setRemoteDescription(a.localDescription);await b.setLocalDescription(await b.createAnswer());await a.setRemoteDescription(b.localDescription);return true};
    </script>`);
  });
  const ws=new WebSocketServer({server,path:'/socket'});ws.on('connection',s=>{record({kind:'ws-open'});s.on('message',b=>{record({kind:'ws-frame',body:b.toString()});s.send('echo')})});
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  return {base:'http://127.0.0.1:'+server.address().port,arrivals,close(){ws.close();server.closeAllConnections();server.close();}};
}
