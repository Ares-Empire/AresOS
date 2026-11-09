import fs from 'node:fs';
import http from 'node:http';
import {spawn} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true'||!fs.existsSync('/.dockerenv'))throw Error('GitHub Linux container only');
const reports=[];
const server=http.createServer((request,response)=>{
  if(request.url==='/report'){
    let body='';request.on('data',chunk=>body+=chunk);request.on('end',()=>{const value=JSON.parse(body);reports.push(value);console.log(JSON.stringify(value));fs.writeFileSync('/out/injection-probe.json',JSON.stringify(reports,null,2));response.end('ok');});
  }else if(request.url==='/update.xml'){
    const extension=JSON.parse(fs.readFileSync('/out/extension.json'));
    response.setHeader('Content-Type','text/xml');response.end(`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${extension.id}"><updatecheck codebase="http://127.0.0.1:8765/extension.crx" version="${extension.version}"/></app></gupdate>`);
  }else if(request.url==='/extension.crx')response.end(fs.readFileSync('/workspace/.work/20-package/own-extension.crx'));
  else response.end(`<script>let handlers=0;window.addEventListener('probe-event',()=>handlers++);const result=window.dispatchEvent(new Event('probe-event',{cancelable:true}));fetch('/report',{method:'POST',body:JSON.stringify({phase:'first-page-script',result,handlers,privateVisible:typeof probePrivate})});</script>`);
});
await new Promise(resolve=>server.listen(8765,'0.0.0.0',resolve));
const profile=fs.mkdtempSync('/tmp/aresos-injection-probe-');
const descriptor=fs.openSync('/out/chrome.txt','a');
const browser=spawn('qualification-chrome',[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--gtk-version=3','--host-resolver-rules=MAP *.test 127.0.0.1','about:blank'],{stdio:['ignore',descriptor,descriptor]});
try{
  const until=Date.now()+60000;while(Date.now()<until&&!reports.some(value=>value.phase==='first-page-script'))await delay(100);
  if(!reports.some(value=>value.phase==='first-page-script'))throw Error('No first-script result; injection mechanism unproven');
  console.log('DIAGNOSTIC ONLY: no acceptance result is produced.');
}finally{browser.kill('SIGTERM');await delay(500);if(browser.exitCode===null)browser.kill('SIGKILL');server.close();fs.rmSync(profile,{recursive:true,force:true});}
