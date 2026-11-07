import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import {generateKeyPairSync,createHash} from 'node:crypto';
import {execFileSync,spawn} from 'node:child_process';
// Must precede every browser helper import and every process/profile operation.
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true')throw Error('Browser runs only on GitHub Linux runners');
const here=path.resolve('control/checks/17d-chrome'),work=path.resolve('.work/17d-chrome'),out=work+'/artifacts';fs.mkdirSync(out,{recursive:true});
const {fixture}=await import('./fixture.mjs');
const {address,key,delay,activateChrome,screenshot,x}=await import('../17-chrome/ui.mjs');
const {evaluate,eventually}=await import('../17-chrome/protocol.mjs');
const {nativeBridge}=await import('./bridge.mjs');
const {pack,idFor}=await import('../17-chrome/install.mjs');
const phase=process.env.CHECK_PHASE,summary={phase,head:process.env.GITHUB_SHA,run:process.env.GITHUB_RUN_ID,cases:[]},audit=new Map();
const save=(name,data)=>fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(data,null,2));
const log=(name,data)=>{summary.cases.push({name,...data});save('summary',summary);console.log(name,JSON.stringify(data));};
let chrome,bridge,selected,extId,version='0.4.0',wt;
let profile=work+'/profile',profileNumber=0;const socket=work+'/native.sock';process.env.CHROME_CHECK_SOCKET=socket;
const f=await fixture(out,work,()=>`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${extId}"><updatecheck codebase="${f.base}/extension.crx" version="${version}"/></app></gupdate>`);
const kp=generateKeyPairSync('rsa',{modulusLength:2048});extId=idFor(kp.publicKey.export({type:'spki',format:'der'}));
const ext=work+'/extension';fs.cpSync(here+'/extension',ext,{recursive:true});
function packVersion(v){version=v;const m=JSON.parse(fs.readFileSync(ext+'/manifest.json'));if(phase==='public'&&!m.content_scripts.some(s=>s.js.includes('public-guard.js'))){fs.copyFileSync(here.replace('17d-chrome','17c-chrome')+'/extension/public-guard.js',ext+'/public-guard.js');m.content_scripts.unshift({matches:['<all_urls>'],exclude_matches:['http://127.0.0.1/*','http://localhost/*'],all_frames:true,run_at:'document_start',world:'MAIN',js:['public-guard.js']});}Object.assign(m,{version:v,key:kp.publicKey.export({type:'spki',format:'der'}).toString('base64'),update_url:f.base+'/update.xml'});fs.writeFileSync(ext+'/manifest.json',JSON.stringify(m));pack(ext,work,kp);}
packVersion(version);
const host=work+'/host';fs.writeFileSync(host,`#!/bin/sh\nprintf '%s\\n' "$$" >> '${out}/host-pids.txt'\nexec python3 '${path.resolve('control/checks/17-chrome/native-host.py')}'\n`,{mode:0o755});
fs.writeFileSync(work+'/host.json',JSON.stringify({name:'org.aresos.chrome_check',description:'17d disposable check',path:host,type:'stdio',allowed_origins:[`chrome-extension://${extId}/`]}));
execFileSync('sudo',['install','-D','-m','644',work+'/host.json','/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome_check.json']);
function policy(forced=true){const p={ExtensionInstallForcelist:forced?[extId+';'+f.base+'/update.xml']:[],NativeMessagingUserLevelHosts:false,RestoreOnStartup:1,ExtensionSettings:{[extId]:forced?{toolbar_pin:'force_pinned'}:{installation_mode:'blocked'}}};fs.writeFileSync(work+'/policy.json',JSON.stringify(p));execFileSync('sudo',['install','-D','-m','644',work+'/policy.json','/etc/opt/chrome/policies/managed/aresos-17d.json']);}policy();
const rpc=(m,p={})=>bridge.send(m,p),state=()=>rpc('Check.state'),ev=expression=>evaluate(bridge,expression);
async function connect(){const conn=new Promise(r=>bridge.once('check.connected',r));await key('ctrl+t');await address(`chrome-extension://${extId}/select.html?url=${encodeURIComponent(f.base+'/')}&tabId=${selected||''}`);await key('Return');const c=await Promise.race([conn,delay(14000).then(()=>{throw Error('Extension did not connect')})]);selected=c.tabId;log('CONNECTED',c);return c;}
async function boot(label,restore=false){const priorStarts=f.rows.filter(r=>r.kind==='attempt'&&r.case==='startup-executed').length;bridge=await nativeBridge(socket);bridge.on('event',e=>fs.appendFileSync(out+'/extension-events.jsonl',JSON.stringify({at:Date.now(),...e})+'\n'));const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode',...(restore?['--restore-last-session']:[f.base+'/'])];save('args-'+label,args);const fd=fs.openSync(out+'/chrome-'+label+'.log','a');chrome=spawn('/usr/bin/google-chrome-stable',args,{stdio:['ignore',fd,fd]});await activateChrome();await delay(3500);if(restore&&phase==='floor')await eventually(()=>f.rows.filter(r=>r.kind==='attempt'&&r.case==='startup-executed').length>priorStarts,'startup script before any debugger attach');if(restore)log('Q2_BEFORE_ATTACH',{label,at:Date.now(),rows:f.rows.slice(-20)});await connect();}
async function close(kill=false){if(chrome?.exitCode===null){if(kill){chrome.kill('SIGKILL');try{execFileSync('pkill',['-KILL','-f',profile],{stdio:'ignore'})}catch{}}else{await activateChrome();await key('ctrl+shift+w');await delay(1800);if(chrome.exitCode===null){log('CLOSE_FALLBACK',{signal:'SIGTERM'});chrome.kill('SIGTERM');}}await delay(700);}bridge?.close();bridge=undefined;chrome=undefined;}
async function nav(url=f.base+'/'){await rpc('Page.navigate',{url});await delay(500);if(url.startsWith(f.base))await eventually(()=>ev("typeof attempt==='function'"),'fixture ready');}
const arrivals=id=>f.rows.filter(r=>['http','ws-open','ws-message'].includes(r.kind)&&r.case===id);
async function count(id,n){await delay(250);assert.equal(arrivals(id).length,n,id);audit.set(id,{expected:n});return arrivals(id);}
function discovery(id,reason){const n=arrivals(id).length;audit.set(id,{observed:n,reason});return arrivals(id);}
async function probe(name,fn){try{const r=await fn();log(name,{status:'observed',...r});return r;}catch(e){log(name,{status:'unavailable',error:e.stack});return {error:e.message};}}
async function end(ending){
 if(ending==='detach')await rpc('Check.detach');
 if(ending==='reload')await rpc('Check.reload');
 if(ending==='update'){packVersion('0.4.'+(Number(version.split('.').at(-1))+1));log('UPDATE_REQUEST',await rpc('Check.update'));}
 if(ending==='host-loss'){process.kill(Number(fs.readFileSync(out+'/host-pids.txt','utf8').trim().split('\n').at(-1)),'SIGKILL');}
 if(ending==='worker-crash'){const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'}).split('\n').filter(l=>l.includes('--extension-process'));assert.ok(processes.length);save('worker-crash-processes',{processes});for(const line of processes)process.kill(Number(line.trim().split(/\s+/)[0]),'SIGKILL');}
 if(ending==='policy'){policy(false);await address('chrome://policy');x('mousemove',85,170,'click',1);await eventually(async()=>{try{await state();return false}catch{return true}},'policy unloaded extension',90000);await screenshot(out,'policy-blocked');}
 if(ending==='normal'||ending==='kill')await close(ending==='kill');
 await delay(1500);
}
async function restart(label,kill=true){await close(kill);if(label.includes('policy')){profile=work+'/profile-after-policy-'+(++profileNumber);selected=undefined;log('FRESH_PROFILE_AFTER_POLICY',{label,reason:'Policy uninstalls the custom CRX; do not interpret the next installation as rule survival.'});}policy();await boot(label);}
async function click(selector){await rpc('Page.bringToFront');await delay(200);const b=await ev(`(()=>{const b=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect();return {x:b.x+b.width/2,y:b.y+b.height/2}})()`);await rpc('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...b});await rpc('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...b});}
const ctx={fs,assert,execFileSync,spawn,here,work,out,f,save,log,probe,delay,eventually,ev,rpc,state,nav,count,discovery,arrivals,audit,boot,close,restart,connect,end,click,address,key,x,screenshot,hash:s=>createHash('sha256').update(s).digest('hex'),get selected(){return selected;}};
try{
 await boot('initial');const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);save('processes',{processes});assert.equal((await state()).manifest.permissions.includes('management'),false);
 await key('ctrl+t');await address('chrome://sandbox');await screenshot(out,'sandbox');await key('ctrl+w');
 const run=await import('./'+phase+'.mjs');await run.default(ctx);
 save('extension-final',await state());await close();await delay(500);
 const rows=[...audit].map(([id,v])=>({id,...v,actual:arrivals(id).length}));save('delivery-audit',rows);
 for(const r of rows)assert.equal(r.actual,r.expected??r.observed,'late/unexpected arrival '+r.id);
 for(const r of f.rows.filter(r=>['http','ws-open','ws-message'].includes(r.kind)))assert.ok(r.case&&audit.has(r.case),'unregistered delivery '+JSON.stringify(r));
 log('FINAL_DELIVERY_AUDIT',{status:'PASS',cases:rows.length});console.log('ALL 17D CHECKS COMPLETE',phase);
}finally{if(bridge)await state().then(s=>save('extension-on-exit',s)).catch(()=>{});await screenshot(out,'final').catch(()=>{});await close();wt?.kill();f.close();save('summary',summary);}
