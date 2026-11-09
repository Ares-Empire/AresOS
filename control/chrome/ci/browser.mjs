import fs from 'node:fs';
import net from 'node:net';
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {setTimeout as delay} from 'node:timers/promises';
import {fixtures} from './fixture.mjs';
import {matrices} from './matrices.mjs';
if(process.platform !== 'linux' || process.env.GITHUB_ACTIONS !== 'true' || !fs.existsSync('/.dockerenv'))throw Error('Browser runs only in GitHub Linux containers');
const fixture=await fixtures();
const profile=fs.mkdtempSync('/tmp/aresos-chrome-fixture-');
const args=[`--user-data-dir=${profile}`,'--no-first-run','--no-default-browser-check','--password-store=basic','--start-maximized','--gtk-version=3','--enable-logging=stderr','--disable-background-mode','--host-resolver-rules=MAP *.test 127.0.0.1','about:blank'];
assert.ok(!args.some(arg=>arg==='--no-sandbox'||arg.startsWith('--remote-debugging')));
fs.writeFileSync('/out/launch.json',JSON.stringify(args));
const descriptor=fs.openSync('/out/chrome.txt','a');
let chrome=spawn('qualification-chrome',args,{stdio:['ignore',descriptor,descriptor]});
function rpc(action,arguments_={}) {
  return new Promise((resolve,reject)=>{
    const socket=net.createConnection('/run/aresos-tools/act.sock');let buffer='';
    socket.setTimeout(20000,()=>socket.destroy(Error('Tool response timeout')));
    socket.on('connect',()=>socket.write(JSON.stringify({v:1,method:'call',action:action==='control_pending'?action:'chrome_'+action,arguments:arguments_})+'\n'));
    socket.on('data',data=>{buffer+=data;if(buffer.includes('\n')){socket.end();const result=JSON.parse(buffer);fs.appendFileSync('/out/tool.jsonl',JSON.stringify({action,result})+'\n');resolve(result);}});
    socket.on('end',()=>{if(!buffer.includes('\n'))reject(Error('Service disconnected before its reply; inspect status, never replay'));});
    socket.on('error',reject);
  });
}
async function call(action,args={}){const result=await rpc(action,args);assert.ok(result.ok,JSON.stringify(result));return result.data;}
async function eventually(fn,label,timeout=15000){const until=Date.now()+timeout;let error;while(Date.now()<until){try{const value=await fn();if(value)return value;}catch(e){error=e;}await delay(150);}throw Error(label+': '+error?.message);}
let tab;const baseline={};
async function read(){let tree='',cursor;do{const result=await call('read',{tab,...(cursor?{cursor}:{})});tree+=result.untrusted_content.tree;cursor=result.cursor;}while(cursor);return tree.split('\n').filter(line=>line.startsWith('{')).map(JSON.parse);}
async function target(label){const row=await eventually(async()=>{const rows=(await read()).filter(row=>row.expected.name===label);return rows.find(row=>['button','link','textbox','searchbox','combobox','checkbox','radio','option'].includes(row.expected.role))||rows[0];},label);return {reference:row.reference,expected:row.expected};}
async function nav(kind,host='fixture'){const url='http://'+host+'.test:8765/?case='+kind;await call('navigate',{tab,url});await eventually(async()=>{const page=await call('read',{tab});return page.untrusted_content.url===url&&page.characters>0;},'fixture document committed');await delay(250);}
const counts=kind=>fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===kind).length;
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
  execFileSync('import',['-window','root','/out/controlled.png']);
  const processes=execFileSync('ps',['-C','chrome','-o','pid,args'],{encoding:'utf8'});assert.doesNotMatch(processes,/--no-sandbox|--remote-debugging-(port|pipe)/);
  const listeners=execFileSync('ss',['-lntp'],{encoding:'utf8'}).split('\n').filter(line=>line.includes('"chrome"'));assert.equal(listeners.length,0);fs.writeFileSync('/out/isolation.json',JSON.stringify({processes,listeners}));baseline.isolation=true;
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
  await nav('residual');const rows=await read();const unlabeled=rows.find(row=>row.expected.role==='button');await call('click',{reference:unlabeled.reference,expected:unlabeled.expected});await eventually(()=>counts('residual-click')===1,'residual fetch');console.log('GROUP 13 residual ordinary-click fetch OBSERVED, NOT HELD');baseline.residual=true;
  fs.writeFileSync('/out/smoke.json',JSON.stringify({core_smoke_passed:true,acceptance_complete:false,kind:'core smoke only',measurements:(await read()).length}));
  console.log('Preliminary core smoke cases passed; acceptance is not complete');
  // A real X input belongs to the owner, even while a task from Claude's input is pending.
  // Do not substitute a tool click: that would test another Claude input instead.
  await nav('owner-input');
  const continued=target('Continue').then(item=>call('click',item));
  await eventually(()=>counts('owner-start')===1,'Claude handler started');
  const ownerAt=Date.now();
  execFileSync('xdotool',['key','--clearmodifiers','Tab','Return']);
  const ownerDelay=ownerAt-fixture.arrivals.find(row=>row.url.includes('case=owner-start')).time;
  const continuedResult=await continued;
  await delay(150);
  const evidence={ownerInput:'X keyboard Tab then Return, outside the tool',ownerDelayMs:ownerDelay,
    ownerArrivals:counts('owner-input'),scheduledArrivals:counts('scheduled-input'),result:continuedResult};
  fs.writeFileSync('/out/owner-input.json',JSON.stringify(evidence,null,2));
  console.log('GROUP 8 owner input evidence',JSON.stringify(evidence));
  const failures=[];
  try {
    assert.ok(ownerDelay<300,'Owner test missed the active hold window');
    assert.equal(counts('scheduled-input'),0,'Scheduled submission from Claude input must stay held');
    assert.equal(counts('owner-input'),1,'Owner submission must run normally while a Claude task is pending');
    console.log('GROUP 8 owner input PASS');baseline.owner=true;
  } catch(error) { failures.push(error); console.error('GROUP 8 owner input FAIL',error.message); }
  // A denial must not conceal an unasked send. Every hostile route keeps receiver checks strict.
  let forgedPasses=0;for(const attack of ['page-forgery','hostile']) {
    await nav(attack);const forged=await call('click',await target('Continue'));await delay(100);
    const evidence={attack,arrivalsBefore:counts(attack),result:forged};
    fs.writeFileSync('/out/'+attack+'.json',JSON.stringify(evidence,null,2));
    try {
      assert.equal(counts(attack),0,'A page-forged control mark must never release a Claude-caused submission without approval');
      const operation=forged.followups.find(item=>item.approval);assert.ok(operation,JSON.stringify(forged));
      await call('submit',operation.approval);await eventually(()=>counts(attack)===1,'approved '+attack);
      await call('submit',operation.approval);await delay(100);assert.equal(counts(attack),1,'A second attempt must not dispatch');
      forgedPasses++;console.log('GROUP 7 page forgery PASS',attack,'receiver: 0 before, 1 after, 1 after replay');
    } catch(error) { failures.push(error); console.error('GROUP 7 page forgery FAIL',attack,error.message); }
  }
  baseline.forgery=forgedPasses===2;
  const admin=(action,arguments_)=>{const result=JSON.parse(execFileSync('sudo',['-n','/usr/bin/python3','/workspace/control/chrome/ci/admin.py',JSON.stringify({action,arguments:arguments_})],{encoding:'utf8'}));assert.ok(result.ok,JSON.stringify(result));return result.data;};
  const caller=(verb,args)=>JSON.parse(execFileSync('python3',['control/chrome/ci/call.py',verb,JSON.stringify(args)],{encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'true'}}));
  let browserWindow=execFileSync('xdotool',['getactivewindow'],{encoding:'utf8'}).trim();
  const ownerNavigate=async(url)=>{execFileSync('xdotool',['windowactivate','--sync',browserWindow]);execFileSync('xdotool',['key','--clearmodifiers','ctrl+1']);execFileSync('xdotool',['key','--clearmodifiers','ctrl+l']);execFileSync('xdotool',['type','--clearmodifiers','--delay','1',url]);execFileSync('xdotool',['key','Return']);await delay(400);};
  for(const failure of await matrices({call,read,nav,target,counts,eventually,tab,fixture,admin,rpc,caller,ownerNavigate,baseline,isolationAfter:()=>{const finalListeners=execFileSync('ss',['-lntp'],{encoding:'utf8'}).split('\n').filter(line=>line.includes('\"chrome\"'));assert.equal(finalListeners.length,0,'Chrome must still have no listening port after all tools');fs.writeFileSync('/out/isolation-after.json',JSON.stringify({listeners:finalListeners}));},ownerHistory:async(direction)=>{execFileSync('xdotool',['key','--clearmodifiers',direction==='back'?'alt+Left':'alt+Right']);await delay(400);},ownerBookmark:()=>execFileSync('xdotool',['key','--clearmodifiers','ctrl+d','Return']),lifecycle:async(command)=>{
    if(command==='kill_chrome'){chrome.kill('SIGKILL');return;}
    if(command==='start_chrome'){chrome=spawn('qualification-chrome',args,{stdio:['ignore',descriptor,descriptor]});await delay(1500);browserWindow=execFileSync('xdotool',['getactivewindow'],{encoding:'utf8'}).trim();return;}
    if(command==='kill_host'){const lines=execFileSync('ps',['-u','1000','-o','pid=,args='],{encoding:'utf8'}).split('\n');for(const line of lines)if(line.includes('/usr/libexec/aresos-control/chrome/native_host.py'))process.kill(Number(line.trim().split(/\s+/)[0]),'SIGKILL');return;}
    return JSON.parse(execFileSync('sudo',['-n','/usr/bin/python3','/workspace/control/chrome/ci/admin.py',JSON.stringify(command)],{encoding:'utf8'}));
  },restoreControl:async()=>{await eventually(async()=>{const result=await rpc('tabs');return result.ok&&result.data.items.length;},'native reconnect',45000);const marker='restored-'+Date.now();await ownerNavigate('http://fixture.test:8765/?case=compose&id='+marker);tab=(await call('tabs')).items.find(item=>item.url?.includes(marker))?.tab;assert.ok(tab!==undefined);await call('take_tab',{tab});return tab;},stopClick:()=>{execFileSync('import',['-window','root','/out/stop.png']);execFileSync('xdotool',['key','--clearmodifiers','Return']);},ownerKey:()=>execFileSync('xdotool',['key','--clearmodifiers','Tab','Return'])}))failures.push(Error(failure.name+': '+failure.error));
  if(failures.length)throw new AggregateError(failures,'Strict owner-input and page-forgery regressions failed');
} catch(error) {
  try{execFileSync('import',['-window','root','/out/failure.png']);}catch{}
  throw error;
} finally {
  chrome.kill('SIGTERM');await delay(500);if(chrome.exitCode===null)chrome.kill('SIGKILL');fixture.close();fs.rmSync(profile,{recursive:true,force:true});
}
