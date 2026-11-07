import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import net from 'node:net';
import {execFileSync,spawn} from 'node:child_process';
import {createHash,generateKeyPairSync,X509Certificate} from 'node:crypto';
// Must run before importing browser helpers, opening a profile or doing setup.
if(process.platform!=='linux'||process.env.GITHUB_ACTIONS!=='true')throw Error('Browser runs only on GitHub Linux runners');
const here=path.resolve('control/checks/17e-chrome'),work=path.resolve('.work/17e-chrome'),out=work+'/artifacts',phase=process.env.CHECK_PHASE;
const {fixture}=await import('./fixture.mjs');
const {pack,idFor}=await import('../17-chrome/install.mjs');
const {nativeBridge}=await import('../17d-chrome/bridge.mjs');
const {address,key,activateChrome,delay,screenshot,x}=await import('../17-chrome/ui.mjs');
const {evaluate,eventually}=await import('../17-chrome/protocol.mjs');
const sh=(cmd,args=[],options={})=>execFileSync(cmd,args,{encoding:'utf8',...options});
const sudo=(...args)=>sh('sudo',args);
fs.mkdirSync(out,{recursive:true});
sh('bash',[here+'/setup.sh']);
const hash=b=>createHash('sha256').update(b).digest('hex');
const save=(name,value)=>fs.writeFileSync(out+'/'+name+'.json',JSON.stringify(value,null,2));
const summary={phase,head:process.env.GITHUB_SHA,run:process.env.GITHUB_RUN_ID,cases:[]};
const log=(name,value)=>{summary.cases.push({name,...value});save('summary',summary);console.log(name,JSON.stringify(value));};
const kp=generateKeyPairSync('rsa',{modulusLength:2048});const extId=idFor(kp.publicKey.export({type:'spki',format:'der'}));
const f=await fixture(work,out,()=>`<?xml version="1.0"?><gupdate xmlns="http://www.google.com/update2/response" protocol="2.0"><app appid="${extId}"><updatecheck codebase="${f.base}/extension.crx" version="0.5.0"/></app></gupdate>`);
const ext=work+'/extension';fs.cpSync(here+'/extension',ext,{recursive:true});
const manifest=JSON.parse(fs.readFileSync(ext+'/manifest.json'));
if(phase==='public'){
 fs.copyFileSync(path.resolve('control/checks/17c-chrome/extension/public-guard.js'),ext+'/public-guard.js');
 manifest.content_scripts=[{matches:['<all_urls>'],exclude_matches:['http://127.0.0.1/*','http://localhost/*'],all_frames:true,run_at:'document_start',world:'MAIN',js:['public-guard.js']}];
}
Object.assign(manifest,{key:kp.publicKey.export({type:'spki',format:'der'}).toString('base64'),update_url:f.base+'/update.xml'});fs.writeFileSync(ext+'/manifest.json',JSON.stringify(manifest));pack(ext,work,kp);
const socket=work+'/native.sock',profile=work+'/browser-home/profile';
fs.writeFileSync(work+'/host',`#!/bin/sh\nprintf '%s\\n' "$$" >> '${work}/host-pids.txt'\nexport CHROME_CHECK_SOCKET='${socket}'\nexec python3 '${path.resolve('control/checks/17-chrome/native-host.py')}'\n`,{mode:0o755});
fs.writeFileSync(work+'/host-pids.txt','');sudo('chown','areschrome:areschrome',work+'/host-pids.txt');
fs.writeFileSync(work+'/host.json',JSON.stringify({name:'org.aresos.chrome_check',description:'17e disposable check',path:work+'/host',type:'stdio',allowed_origins:[`chrome-extension://${extId}/`]}));
sudo('install','-D','-m','644',work+'/host.json','/etc/opt/chrome/native-messaging-hosts/org.aresos.chrome_check.json');
let chrome,bridge,proxy,selected,proxied=true;
const samples=[];
const sampleTimer=setInterval(()=>{
 try{const text=sh('ps',['-u','aresproxy','-o','pid=,pcpu=,rss=,vsz=,time=']);for(const line of text.trim().split('\n')){const [pid,cpu,rssKiB,vszKiB,cpuTime]=line.trim().split(/\s+/);samples.push({at:Date.now(),mode:proxied?'checkpoint':'direct',pid:Number(pid),cpu:Number(cpu),rssKiB:Number(rssKiB),vszKiB:Number(vszKiB),cpuTime});}}catch{}
},1000);
function policy(mode=true,extension=true){
 proxied=mode;
 const roots=['proxy-root.pem','fixture-ca.pem'].map(n=>new X509Certificate(fs.readFileSync(work+'/'+n)).raw.toString('base64'));
 const p={ProxySettings:mode?{ProxyMode:'fixed_servers',ProxyServer:'http://127.0.0.1:18080',ProxyBypassList:'<-loopback>'}:{ProxyMode:'direct'},CACertificates:roots,QuicAllowed:!mode,WebRtcIPHandling:mode?'disable_non_proxied_udp':'default',ExtensionInstallForcelist:extension?[extId+';'+f.base+'/update.xml']:[],ExtensionSettings:{[extId]:extension?{toolbar_pin:'force_pinned'}:{installation_mode:'blocked'}},NativeMessagingUserLevelHosts:false,RestoreOnStartup:1};
 fs.writeFileSync(work+'/policy.json',JSON.stringify(p));sudo('install','-D','-m','644',work+'/policy.json','/etc/opt/chrome/policies/managed/aresos-17e.json');save('policy-'+(mode?'proxy':'direct'),p);
}
function firewall(on=true){
 try{sudo('nft','delete','table','inet','e17')}catch{}
 if(on){const uid=sh('id',['-u','areschrome']).trim();const rules=`table inet e17 {
 chain output {
  type filter hook output priority 0; policy accept;
  meta skuid ${uid} ip daddr 127.0.0.1 tcp dport 18080 counter accept;
  meta skuid ${uid} counter reject with icmpx type admin-prohibited;
 }
}
`;
 fs.writeFileSync(work+'/rules.nft',rules);sudo('nft','-f',work+'/rules.nft');save('nftables',{rules: sudo('nft','list','table','inet','e17')});}
}
async function control(action,params={}){
 const source="import socket,json,sys;s=socket.socket(socket.AF_UNIX);s.connect(sys.argv[1]);s.sendall(sys.argv[2].encode()+b'\\n');f=s.makefile();print(f.readline())";
 const result=JSON.parse(sudo('-u','aresproxy',work+'/venv/bin/python','-c',source,work+'/private/control.sock',JSON.stringify({action,...params})));
 if(result.error)throw Error(result.error);return result.result;
}
async function startProxy(){
 const fd=fs.openSync(work+'/proxy-console.log','a');
 proxy=spawn('sudo',['-u','aresproxy','env','CHECKPOINT_PRIVATE='+work+'/private','MALLOC_ARENA_MAX=2','prlimit','--as=805306368','--',work+'/venv/bin/mitmdump','-q','--listen-host','127.0.0.1','--listen-port','18080','--set','confdir='+work+'/private','--set','connection_strategy=lazy','--set','upstream_cert=false','--set','ssl_verify_upstream_trusted_ca='+work+'/upstream-roots.pem','--set','body_size_limit=32m','--set','rawtcp=false','--set','termlog_verbosity=error','-s',here+'/checkpoint.py'],{stdio:['ignore',fd,fd]});
 try{await eventually(()=>control('state'),'checkpoint ready',15000)}catch(e){console.error(fs.readFileSync(work+'/proxy-console.log','utf8').slice(-8000));throw e;}log('CHECKPOINT_READY',await control('state'));
}
async function stopProxy(){
 try{sudo('pkill','-KILL','-u','aresproxy')}catch{}await delay(500);proxy=undefined;
}
const rpc=(m,p={})=>bridge.send(m,p),ev=expression=>evaluate(bridge,expression);
async function connect(){
 const ready=new Promise(r=>bridge.once('check.connected',r));await key('ctrl+t');await address(`chrome-extension://${extId}/select.html?url=${encodeURIComponent(f.base+'/')}&tabId=${selected||''}`);await key('Return');
 const r=await Promise.race([ready,delay(15000).then(()=>{throw Error('Extension did not connect')})]);selected=r.tabId;await rpc('Page.bringToFront');await rpc('Network.enable');return r;
}
async function boot(label,mode=true,restore=false){
 policy(mode);firewall(mode);bridge=await nativeBridge(socket);bridge.on('check.network',event=>fs.appendFileSync(out+'/browser-network.jsonl',JSON.stringify(event)+'\n'));sudo('chown','areschrome:areschrome',socket);
 const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode',...(restore?['--restore-last-session']:[f.base+'/'])];
 save('args-'+label,args);const fd=fs.openSync(work+'/chrome-console.log','a');
 chrome=spawn('sudo',['-u','areschrome','env','DISPLAY='+process.env.DISPLAY,'XAUTHORITY='+work+'/browser-home/Xauthority','XDG_CONFIG_HOME='+work+'/config', '/usr/bin/google-chrome-stable',...args],{stdio:['ignore',fd,fd]});
 await activateChrome();await delay(3500);
 if(restore){
  const restored=async()=>(await control('state')).rows.some(r=>r.case==='e-restored-first'&&r.method==='GET'&&r.status==='held');
  if(!await restored()){await screenshot(out,'restore-before-button');x('mousemove',1376,285,'click',1);}
  await eventually(restored,'actual restored startup document captured',15000);log('RESTORED_BEFORE_ATTACH',{captured:true});
 }
 await connect();
 const processes=sh('ps',['-u','areschrome','-o','pid,args']);assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)|--ignore-certificate-errors/);save('processes-'+label,{processes});
 log('BROWSER_READY',{label,mode,selected});
}
async function close(kill=false){
 if(chrome){if(!kill){await activateChrome().catch(()=>{});await key('ctrl+shift+w').catch(()=>{});await delay(1200);}try{sudo('pkill',kill?'-KILL':'-TERM','-u','areschrome')}catch{}await delay(500);chrome=undefined;}
 bridge?.close();bridge=undefined;
}
async function nav(url=f.base+'/'){await rpc('Page.navigate',{url});await delay(700);}
const rows=id=>f.rows.filter(r=>r.case===id);
const arrivals=(id,kind='http')=>rows(id).filter(r=>r.kind===kind);
const expectations=new Map();
function expect(id,kind,n){expectations.set(id+'::'+kind,{id,kind,n})}
async function zero(id){await delay(250);assert.equal(rows(id).filter(r=>['headers','ws-open','ws-message'].includes(r.kind)).length,0,id+' leaked before approval');for(const kind of ['headers','http','ws-open','ws-message'])expect(id,kind,0);}
async function delivered(id,kind='http',n=1){await eventually(()=>arrivals(id,kind).length===n,'receiver '+id+' '+kind,12000);expect(id,kind,n);if(kind==='http')expect(id,'headers',n);return arrivals(id,kind);}
async function pending(id,kind){return eventually(async()=>{const s=await control('state');return s.rows.findLast(r=>r.case===id&&r.status==='held'&&(!kind||r.kind===kind))},'captured '+id,15000)}
async function approve(id,kind){const op=await pending(id,kind);await control('approve',{id:op.id});return op;}
async function guard(enabled=true){const result=await control('guard',{enabled});log('GUARD_BARRIER',result);return result;}
async function context(){const s=await rpc('Check.state');return control('context',{tokens:s.documents.map(d=>d.value)});}
async function send(id,body=id,extra={}){return ev(`send(${JSON.stringify(id)},${JSON.stringify(body)},${JSON.stringify(extra)})`)}
async function positive(id,body=id,extra={}){await guard(false);await send(id,body,extra);await delivered(id);}
async function probe(name,fn){try{const result=await fn();log(name,{status:'run',...result});return result}catch(e){log(name,{status:'not-met',error:e.stack});return {error:e.message}}}
async function snapshotProxy(){
 for(const name of ['events.jsonl','fatal-events.jsonl'])try{fs.writeFileSync(out+'/checkpoint-'+name,sudo('cat',work+'/private/'+name));}catch{}
 try{save('ledger',await control('state'))}catch{}
}
const c={fs,path,assert,sh,sudo,spawn,work,out,phase,here,save,log,hash,f,delay,eventually,address,key,screenshot,x,rpc,ev,nav,connect,boot,close,policy,firewall,control,startProxy,stopProxy,guard,context,send,positive,pending,approve,zero,delivered,expect,rows,arrivals,probe,get selected(){return selected},get chrome(){return chrome}};
try{
 await startProxy();await boot('initial');
 await rpc('Page.bringToFront');await key('ctrl+t');await address('chrome://sandbox');await screenshot(out,'sandbox');await key('ctrl+w');
 await context();await (await import('./'+phase+'.mjs')).default(c);
 await close();await delay(600);
 for(const e of expectations.values())assert.equal(arrivals(e.id,e.kind).length,e.n,'late/unexpected receiver delivery '+e.id+' '+e.kind);
 save('delivery-audit',[...expectations.values()].map(e=>({...e,actual:arrivals(e.id,e.kind).length})));
 log('FINAL_RECEIVER_AUDIT',{status:'PASS',assertions:expectations.size,receiverRows:f.rows.length});console.log('ALL 17E CHECKS COMPLETE',phase);
}finally{
 clearInterval(sampleTimer);save('resource-samples',samples);await snapshotProxy();save('summary',summary);await screenshot(out,'final').catch(()=>{});await close();await stopProxy();f.close();
 // Raw Chrome/mitmproxy consoles can include URLs; retain a count only.
 for(const name of ['chrome-console.log','proxy-console.log']){const file=work+'/'+name;if(fs.existsSync(file)){log('PRIVATE_DIAGNOSTIC',{name,bytes:fs.statSync(file).size});fs.rmSync(file)}}
 try{save('firewall-final',{rules:sudo('nft','list','table','inet','e17')})}catch{}
}
