import http from 'node:http';
import fs from 'node:fs';
const page=(body,script='')=>`<!doctype html><meta charset="utf-8"><title>Synthetic fixture</title><style>body{font:16px sans-serif;margin:20px}button,input,textarea{margin:8px}</style>${body}<script>${script}</script>`;
export async function fixtures() {
  const arrivals=[];
  const server=http.createServer(async(req,res)=>{
    const url=new URL(req.url,'http://fixture.test:8765');
    if(url.pathname === '/update.xml'){
      const {id,version}=JSON.parse(fs.readFileSync('/out/extension.json'));
      res.setHeader('Content-Type','application/xml');res.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${version}"/></app></gupdate>`);return;
    }
    if(url.pathname === '/extension.crx'){res.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));return;}
    if(url.pathname === '/receive') {
      let body='';for await(const part of req)body+=part;
      const record={time:Date.now(),url:req.url,method:req.method,body,host:req.headers.host};arrivals.push(record);fs.appendFileSync('/out/receiver.jsonl',JSON.stringify(record)+'\n');
      res.end(page('<p>Received synthetic input</p>'));return;
    }
    const kind=url.searchParams.get('case') || 'compose';
    let body,script='';
    if(kind==='compose') {
      body='<label>Message<textarea aria-label="Message">Existing synthetic draft</textarea></label><button>Send</button><p aria-label="Preview">Read-only preview</p>';
      script=`document.querySelector('button').onclick=()=>fetch('/receive?case=compose',{method:'POST',body:document.querySelector('textarea').value});`;
    } else if(kind==='native' || kind==='event') {
      body=`<form action="/receive?case=${kind}" method="post" target="sink"><input aria-label="Required" name="required" required><button type="submit">Submit</button></form><button id="continue" type="button">Continue</button><iframe name="sink" hidden></iframe>`;
      script=`document.querySelector('#continue').onclick=()=>document.querySelector('form').${kind==='native'?'submit()':'requestSubmit()'};`;
      if(kind==='event')body=body.replace(' required>',' value="valid" required>');
    } else if(kind==='activation') {
      body='<button id="continue">Continue</button><a href="/receive?case=activation">Delete</a>';
      script="document.querySelector('button').onclick=()=>document.querySelector('a').dispatchEvent(new MouseEvent('click',{cancelable:false,bubbles:true}));";
    } else if(kind==='owner-input') {
      body='<button id="continue" type="button">Continue</button><form id="owner" action="/receive?case=owner-input" method="post" target="sink"><input type="hidden" name="source" value="owner"><button type="submit">Submit by owner</button></form><form id="scheduled" action="/receive?case=scheduled-input" method="post" target="sink"><input type="hidden" name="source" value="scheduled"></form><iframe name="sink" hidden></iframe>';
      script="document.querySelector('#continue').onclick=()=>{fetch('/receive?case=owner-start',{method:'POST',body:'Claude input started'});setTimeout(()=>document.querySelector('#scheduled').submit(),350);};";
    } else if(kind==='password') {
      body='<input type="password" aria-label="Secret" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Current" autocomplete="current-password" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Masked" style="-webkit-text-security:disc" value="SENTINEL_PRIVATE_PASSWORD_20"><input aria-label="Switch" type="password" value="SENTINEL_PRIVATE_PASSWORD_20"><button>Show</button>';
      script="document.querySelector('button').onclick=()=>document.querySelector('[aria-label=Switch]').type='text';";
    } else if(kind==='residual') {
      body='<button aria-label="">●</button><textarea aria-label="Autosave"></textarea>';
      script="document.querySelector('button').onclick=()=>fetch('/receive?case=residual-click',{method:'POST',body:'ordinary click'});document.querySelector('textarea').oninput=e=>fetch('/receive?case=residual-autosave',{method:'POST',body:e.target.value});";
    } else {res.statusCode=404;res.end('Unknown synthetic fixture');return;}
    res.setHeader('Content-Type','text/html');res.end(page(body,script));
  });
  await new Promise(resolve=>server.listen(8765,'0.0.0.0',resolve));
  const second=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end(page('<input aria-label="Cross-site message" value="Cross-origin draft">'));});
  await new Promise(resolve=>second.listen(8766,'0.0.0.0',resolve));
  return {arrivals,close:()=>{server.close();second.close();}};
}
