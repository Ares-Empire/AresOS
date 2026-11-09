import fs from 'node:fs';
import net from 'node:net';
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {fixtures} from './fixture.mjs';
if(process.platform !== 'linux' || process.env.GITHUB_ACTIONS !== 'true' || !fs.existsSync('/.dockerenv'))throw Error('Browser runs only in GitHub Linux containers');
const fixture=await fixtures();
const profile=fs.mkdtempSync('/tmp/aresos-chrome-fixture-');
const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--disable-background-mode','--host-resolver-rules=MAP *.test 127.0.0.1','about:blank'];
assert.ok(!args.some(arg=>arg==='--no-sandbox'||arg.startsWith('--remote-debugging')));
fs.writeFileSync('/out/launch.json',JSON.stringify(args));
const descriptor=fs.openSync('/out/chrome.txt','a');
const chrome=spawn('qualification-chrome',args,{stdio:['ignore',descriptor,descriptor]});
function rpc(action,arguments_={}) {
  return new Promise((resolve,reject)=>{
    const socket=net.createConnection('/run/aresos-tools/act.sock');let buffer='';
    socket.setTimeout(20000,()=>socket.destroy(Error('Tool response timeout')));
    socket.on('connect',()=>socket.write(JSON.stringify({v:1,method:'call',action:'chrome_'+action,arguments:arguments_})+'\n'));
    socket.on('data',data=>{buffer+=data;if(buffer.includes('\n')){socket.end();const result=JSON.parse(buffer);fs.appendFileSync('/out/tool.jsonl',JSON.stringify({action,result})+'\n');resolve(result);}});
    socket.on('error',reject);
  });
}
async function call(action,args={}){const result=await rpc(action,args);assert.ok(result.ok,JSON.stringify(result));return result.data;}
async function eventually(fn,label,timeout=15000){const until=Date.now()+timeout;let error;while(Date.now()<until){try{const value=await fn();if(value)return value;}catch(e){error=e;}await delay(150);}throw Error(label+': '+error?.message);}
let tab;
async function read(){let tree='',cursor;do{const result=await call('read',{tab,...(cursor?{cursor}:{})});tree+=result.untrusted_content.tree;cursor=result.cursor;}while(cursor);return tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse);}
async function target(label){const row=await eventually(async()=>(await read()).find(row=>row.expected.name===label),label);return {reference:row.reference,expected:row.expected};}
async function nav(kind){await call('navigate',{tab,url:'http://fixture.test:8765/?case='+kind});await eventually(async()=>{const rows=await read();return rows.length;},'page reader');await delay(250);}
const counts=kind=>fixture.arrivals.filter(row=>row.url.includes('case='+kind)).length;
try {
  const tabs=await eventually(async()=>{const result=await rpc('tabs');return result.ok && result.data.items.length && result.data.items;},'extension native connection',45000);
  // The extension is installed before this owner-created document, then take attaches to it.
  execFileSync('xdotool',['key','--clearmodifiers','ctrl+l']);
  execFileSync('xdotool',['type','--clearmodifiers','--delay','1','http://fixture.test:8765/?case=compose']);
  execFileSync('xdotool',['key','--clearmodifiers','Return']);
  await delay(1000);
  const current=await call('tabs');
  tab=current.items.find(item=>item.url?.includes('fixture.test'))?.tab;assert.ok(tab !== undefined);
  await call('take_tab',{tab});
  const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);
  const listeners=execFileSync('ss',['-lntp'],{encoding:'utf8'}).split('\n').filter(line=>line.includes('"chrome"'));assert.equal(listeners.length,0);fs.writeFileSync('/out/isolation.json',JSON.stringify({processes,listeners}));
  const send=await target('Send');const prepared=await call('click',send);assert.ok(prepared.approval);assert.equal(counts('compose'),0);
  const sent=await call('submit',prepared.approval);assert.equal(sent.operation.state,'done');await eventually(()=>counts('compose')===1,'receiver compose');
  await call('submit',prepared.approval);assert.equal(counts('compose'),1);console.log('GROUP 1 what asks PASS: zero before approval, one after, no replay');
  for(const kind of ['native','event']) {
    await nav(kind);const item=await target('Continue');await call('click',item);assert.equal(counts(kind),0);
    const pending=await new Promise((resolve,reject)=>{const socket=net.createConnection('/run/aresos-tools/act.sock');let b='';socket.on('connect',()=>socket.write(JSON.stringify({v:1,method:'call',action:'control_pending',arguments:{}})+'\n'));socket.on('data',d=>{b+=d;if(b.includes('\n')){socket.end();resolve(JSON.parse(b));}});socket.on('error',reject);});
    const id=pending.data.items.find(item=>item.state==='reserved')?.operation_id;assert.ok(id,JSON.stringify(pending));
    const status=await call('operation_status',{operation_id:id});await call('submit',status.operation.approval);await eventually(()=>counts(kind)===1,'receiver '+kind);
    console.log('GROUP 2 stopped page steps PASS',kind);
  }
  await nav('activation');await call('click',await target('Continue'));await delay(100);assert.equal(counts('activation'),0);console.log('GROUP 2 wrapped non-cancellable activation PASS: no delivery and never resumed');
  await nav('password');const view=JSON.stringify(await read());assert.doesNotMatch(view,/SENTINEL_PRIVATE_PASSWORD_20/);await call('click',await target('Show'));assert.doesNotMatch(JSON.stringify(await read()),/SENTINEL_PRIVATE_PASSWORD_20/);console.log('GROUP 7 password presence and show-password PASS');
  await nav('residual');const rows=await read();const unlabeled=rows.find(row=>row.expected.role==='button');await call('click',{reference:unlabeled.reference,expected:unlabeled.expected});await eventually(()=>counts('residual-click')===1,'residual fetch');console.log('GROUP 13 residual ordinary-click fetch OBSERVED, NOT HELD');
  fs.writeFileSync('/out/smoke.json',JSON.stringify({passed:true,kind:'core smoke only',measurements:(await read()).length}));
  console.log('Chrome fixture smoke PASS');
} catch(error) {
  try{execFileSync('import',['-window','root','/out/failure.png']);}catch{}
  throw error;
} finally {
  chrome.kill('SIGTERM');await delay(500);if(chrome.exitCode===null)chrome.kill('SIGKILL');fixture.close();fs.rmSync(profile,{recursive:true,force:true});
}
