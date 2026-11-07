// Synthetic sites only. This is an experiment, not an AresOS service.
import http from 'node:http';
import fs from 'node:fs';
import {WebSocketServer} from 'ws';

const style = '<style>body{font:16px sans-serif;margin:32px;max-width:850px}label{display:block;margin:12px}input,select,button{font:inherit}fieldset{margin:12px}p{line-height:1.6}td,th{padding:8px;border:1px solid}dialog{padding:30px}</style>';
const html = (title, body) => `<!doctype html><html lang="en"><meta charset="utf-8"><title>${title}</title>${style}<body>${body}</body></html>`;
export async function fixtures(out) {
  const arrivals = [];
  let other;
  const record = row => {
    const entry = {seq:arrivals.length+1, at:Date.now(), ...row};
    arrivals.push(entry);
    fs.appendFileSync(`${out}/server.jsonl`, JSON.stringify(entry)+'\n');
  };
  const handler = async (req,res) => {
    const url = new URL(req.url, 'http://'+req.headers.host);
    let body = '';
    for await (const b of req) body += b;
    if (url.pathname === '/session') {
      record({kind:'login', method:req.method, url:req.url, body});
      res.writeHead(303, {'Set-Cookie':'fixture_session=synthetic-member; HttpOnly; SameSite=Lax; Max-Age=3600; Path=/', Location:'/owner'}).end(); return;
    }
    if (url.pathname === '/receive') {
      record({kind:'http', method:req.method, url:req.url, body, site:req.headers.host, cookie:!!req.headers.cookie});
      res.writeHead(200, {'Content-Type':'text/html','Access-Control-Allow-Origin':'*'}).end(html('Received', '<p id="status">Received synthetic submission.</p>')); return;
    }
    res.setHeader('Content-Type','text/html; charset=utf-8');
    if (url.pathname === '/login') return res.end(html('Fixture login', '<form action="/session" method="post"><input name="member" value="synthetic-member" type="hidden"><button autofocus>Sign in to fixture</button></form>'));
    if (url.pathname === '/owner') {
      record({kind:'owner-page', signedIn:req.headers.cookie?.includes('fixture_session=synthetic-member') || false});
      return res.end(html('Owner fixture', `<h1>Owner fixture</h1><p id="session">${req.headers.cookie?.includes('fixture_session=') ? 'Signed in: synthetic member' : 'NOT SIGNED IN'}</p><label>Owner note<input id="note" value="untouched"></label><button id="replace" onclick="document.querySelector('#note').outerHTML='<input id=note aria-label=Replacement value=replacement>'">Replace note</button>`));
    }
    if (url.pathname === '/other') return res.end(html('Other owner tab','<h1>Other owner tab</h1><label>Owner note<input id="note" value="owner-only"></label>'));
    if (url.pathname === '/form') return res.end(html('Long form', `<h1>Long form</h1><form action="/receive?case=long-form" method="post" enctype="multipart/form-data"><fieldset><legend>Profile</legend><label>Display name<input name="name" id="name" required></label><label>Email<input type="email" value="invalid" aria-invalid="true"></label><label>Notes<textarea id="notes">Synthetic notes</textarea></label><label>Region<select id="region" name="region"><option>North</option><option>South</option></select></label><label><input id="updates" name="updates" type="checkbox" checked>Updates</label><label><input name="plan" type="radio" checked value="basic">Basic</label><label><input name="plan" type="radio" value="plus">Plus</label><label>Start date<input id="date" name="date" type="date"></label><label>Local file<input id="file" name="file" type="file"></label><label>Disabled<input disabled value="fixed"></label></fieldset>${Array.from({length:25},(_,i)=>`<label>Extra field ${i+1}<input name="extra${i}"></label>`).join('')}<button>Submit synthetic form</button></form>`));
    if (url.pathname === '/table') return res.end(html('Table','<h1>Inventory</h1><table><caption>Synthetic stock</caption><thead><tr><th scope="col">Item</th><th scope="col">Count</th></tr></thead><tbody>'+Array.from({length:12},(_,i)=>`<tr><th scope="row">Item ${i}</th><td>${i+2}</td></tr>`).join('')+'</tbody></table>'));
    if (url.pathname === '/frames') return res.end(html('Frames',`<h1>Frame test</h1><iframe title="Same origin" src="/frame?name=same"></iframe><iframe title="Cross origin" src="${other}/frame?name=cross"></iframe>`));
    if (url.pathname === '/frame') return res.end(html('Frame '+url.searchParams.get('name'),`<h2>${url.searchParams.get('name')} frame</h2><label>Frame note<input id="frame-note" value="frame-original"></label><button onclick="this.textContent='Frame clicked'">Frame action</button>`));
    if (url.pathname === '/shadow') return res.end(html('Shadow component', '<h1>Shadow component</h1><fixture-widget></fixture-widget><script>customElements.define("fixture-widget",class extends HTMLElement{connectedCallback(){this.attachShadow({mode:"open"}).innerHTML=\'<label>Shadow note<input id="shadow-note" value="shadow-original"></label><button>Shadow action</button>\'}})</script>'));
    if (url.pathname === '/modal') return res.end(html('Modal', '<h1>Dialog test</h1><button>Behind dialog</button><dialog aria-labelledby="title"><h2 id="title">Confirm synthetic action</h2><label>Reason<input id="reason" required></label><button onclick="this.closest(\'dialog\').close()">Cancel</button></dialog><script>document.querySelector("dialog").showModal()</script>'));
    if (url.pathname === '/article') return res.end(html('Long article','<article><h1>Notes from a synthetic island</h1>'+Array.from({length:180},(_,i)=>`<section><h2>Section ${i+1}</h2><p>The island observatory keeps a record of wind, water and migrating birds. This paragraph is synthetic fixture text, repeated to measure a long structured page view.</p></section>`).join('')+'</article>'));
    if (url.pathname === '/sw.js') {
      res.setHeader('Content-Type','text/javascript');
      return res.end(`self.addEventListener('install',()=>self.skipWaiting());self.addEventListener('activate',e=>e.waitUntil(clients.claim()));self.addEventListener('message',e=>{if(e.data.case)e.waitUntil(fetch('/receive?case='+e.data.case,{method:'POST',body:'synthetic-worker-data'}).then(()=>e.source.postMessage('worker-sent')))})`);
    }
    if (url.pathname === '/hold') {
      const c = url.searchParams.get('case');
      const target = `/receive?case=${c}`;
      const kind = c.split('-')[0];
      let content;
      if (['post','get','cross'].includes(kind)) content = `<form action="${kind==='cross'?other:''}${target}" method="${kind==='get'?'get':'post'}"><input type="hidden" name="case" value="${c}"><label>Message<input id="message" name="message" value="synthetic-${c}"></label><button id="trigger">Send fixture</button></form>`;
      else if (kind==='ping') content = `<a id="trigger" href="/waiting" ping="${target}">Follow fixture link with ping</a>`;
      else content = `<label>Message<input id="message" value="synthetic-${c}"></label><button id="trigger">Send fixture</button><p id="status">Idle</p><script>
        const status=document.querySelector('#status'), input=document.querySelector('#message');
        const send=()=>{status.textContent='Waiting for network';
          ${kind==='xhr'?`const x=new XMLHttpRequest();x.open('POST','${target}');x.onload=()=>status.textContent='Sent';x.send(input.value);`:
          kind==='beacon'?`navigator.sendBeacon('${target}',input.value);status.textContent='Queued beacon';`:
          kind==='worker'?`navigator.serviceWorker.controller.postMessage({case:'${c}'});`:
          kind==='ws'?`socket.send(input.value);status.textContent='WebSocket send returned';`:
          `fetch('${target}',{method:'POST',body:input.value}).then(()=>status.textContent='Sent').catch(()=>status.textContent='Dropped');`}
        };
        ${kind==='ws'?`const socket=new WebSocket('ws://'+location.host+'/ws?case=${c}');socket.onopen=()=>status.textContent='Socket ready';input.onkeydown=e=>{if(e.key==='Enter')send()};`:''}
        ${kind==='worker'?`navigator.serviceWorker.register('/sw.js').then(()=>navigator.serviceWorker.ready).then(()=>{const ready=()=>{status.textContent='Worker ready'};if(navigator.serviceWorker.controller)ready();else navigator.serviceWorker.addEventListener('controllerchange',ready,{once:true})});navigator.serviceWorker.onmessage=()=>status.textContent='Worker sent';`:''}
        ${kind==='autosave'?'input.oninput=send;':''}
        document.querySelector('#trigger').onclick=send;
      </script>`;
      return res.end(html('Hold '+c, '<h1>Hold '+c+'</h1>'+content));
    }
    if (url.pathname==='/waiting') return res.end(html('Waiting','<p>Waiting page. Synthetic fixture.</p>'));
    res.statusCode=404; res.end('Fixture not found');
  };
  const a=http.createServer(handler), b=http.createServer(handler);
  await new Promise(r=>b.listen(0,'127.0.0.1',r)); other=`http://localhost:${b.address().port}`;
  await new Promise(r=>a.listen(0,'127.0.0.1',r));
  const wss=new WebSocketServer({server:a});
  wss.on('connection',(ws,req)=>ws.on('message',data=>record({kind:'ws',url:req.url,body:data.toString()})));
  return {base:`http://127.0.0.1:${a.address().port}`, other, arrivals, close:()=>{wss.close();a.close();b.close();}};
}
