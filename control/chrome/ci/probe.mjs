import fs from 'node:fs';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true'||!fs.existsSync('/.dockerenv'))throw Error('GitHub Linux container only');
const reports=[];
const server=http.createServer((request,response)=>{
  if(request.url==='/report'){
    let body='';request.on('data',chunk=>body+=chunk);request.on('end',()=>{const value=JSON.parse(body);reports.push(value);console.log(JSON.stringify(value));fs.writeFileSync('/out/injection-probe.json',JSON.stringify(reports,null,2));response.end('ok');});
  }else if(request.url==='/native-donor'){response.end('<!doctype html><title>Native donor</title>');
  }else if(request.url==='/popup'){
    response.end(`<script>fetch('http://fixture.test:8765/report',{method:'POST',body:JSON.stringify({phase:'popup-first-script',preloadMarker:typeof probeNewDocumentMarker,privateVisible:typeof probePrivate})});</script>`);
  }else if(request.url.startsWith('/update.xml')){
    const extension=JSON.parse(fs.readFileSync('/out/extension.json'));
    response.setHeader('Content-Type','text/xml');response.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${extension.id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${extension.version}"/></app></gupdate>`);
  }else if(request.url==='/extension.crx')response.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));
  else response.end(`<button id="target">Ordinary control</button><script>let handlers=0,same=false,detail;window.addEventListener('probe-event',()=>handlers++);const result=window.dispatchEvent(new Event('probe-event',{cancelable:true}));const original=new CustomEvent('original-target',{cancelable:true,detail:{fixture:7}});window.addEventListener('original-target',event=>{same=event===original;detail=event.detail;event.preventDefault();});window.dispatchEvent(new CustomEvent('probe-original',{detail:{event:original}}));const target=document.querySelector('#target'),relayed=new CustomEvent('probe-relayed',{cancelable:true,detail:{fixture:9}});let relaySame=false,relayDetail;target.addEventListener('probe-relayed',event=>{relaySame=event===relayed;relayDetail=event.detail;event.preventDefault();});const relayReturn=target.dispatchEvent(relayed);fetch('/report',{method:'POST',body:JSON.stringify({phase:'first-page-script',preloadMarker:typeof probeNewDocumentMarker,result,handlers,same,detail,relaySame,relayDetail,relayReturn,relayPrevented:relayed.defaultPrevented,originalPrevented:original.defaultPrevented,privateVisible:typeof probePrivate})});</script>`);
});
await new Promise(resolve=>server.listen(8765,'0.0.0.0',resolve));
const profile=fs.mkdtempSync('/tmp/aresos-injection-probe-');
const descriptor=fs.openSync('/out/chrome.txt','a');
const browser=spawn('qualification-chrome',[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--gtk-version=3','--host-resolver-rules=MAP *.test 127.0.0.1','about:blank'],{stdio:['ignore',descriptor,descriptor]});
try{
  const complete=()=>['first-page-script','popup-first-script','popup-observation','native-borrowed-open','native-borrowed-closed'].every(phase=>reports.some(value=>value.phase===phase));
  const until=Date.now()+60000;while(Date.now()<until&&!complete())await delay(100);
  if(!reports.some(value=>value.phase==='first-page-script'))throw Error('No first-script result; injection mechanism unproven');
  if(reports.find(value=>value.phase==='first-page-script').preloadMarker!=='boolean')throw Error('Root document preload marker did not run');
  for(const mode of ['open','closed']){const row=reports.find(value=>value.phase==='native-borrowed-'+mode);if(!row||row.handlers!==0)throw Error('Native entry did not capture borrowed '+mode+' dispatch: '+JSON.stringify(row));}
  if(!reports.some(value=>value.phase==='popup-first-script')||!reports.some(value=>value.phase==='popup-observation'))throw Error('No popup diagnostic result');
  console.log('DIAGNOSTIC ONLY: no acceptance result is produced.');
}finally{browser.kill('SIGTERM');await delay(500);if(browser.exitCode===null)browser.kill('SIGKILL');server.close();fs.rmSync(profile,{recursive:true,force:true});}
