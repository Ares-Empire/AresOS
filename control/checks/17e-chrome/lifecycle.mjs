export default async function(c){
 const {ev,guard,positive,send,pending,control,approve,delivered,zero,log,delay,assert,rpc}=c;
 const queueEvidence=values=>Object.fromEntries(Object.entries(values).map(([name,value])=>[name,{length:Buffer.byteLength(value),sha256:c.hash(value)}]));
 // Persisted browser-only work exists independently of the checkpoint's queue.
 await positive('e-outbox-control');await c.nav(c.f.base+'/startup?case=e-restore-control');await delivered('e-restore-control');await ev("history.replaceState(null,'','/startup?case=e-restored-first');true");await guard();
 const stored=await ev(`(async()=>{localStorage.syntheticNamed17e='delete42';const root=await navigator.storage.getDirectory(),f=await root.getFileHandle('outbox17e',{create:true}),w=await f.createWritable();await w.write('delete42');await w.close();globalThis.channel=new BroadcastChannel('17e');channel.postMessage('delete42');return {named:localStorage.syntheticNamed17e,opfs:await (await f.getFile()).text(),idb:await outbox17(true)}})()`);
 await ev("outbox17().then(value=>send('e-outbox-later',value));true");await pending('e-outbox-later');await zero('e-outbox-later');log('Q10_UNRESOLVED_STORAGE',{stored:queueEvidence(stored),guard:(await control('state')).guard});
 // Restart checkpoint with guard persisted; it must load state before listening.
 await c.stopProxy();await c.startProxy();assert.equal((await control('state')).guard,true);await send('e-after-proxy-restart');await pending('e-after-proxy-restart');await zero('e-after-proxy-restart');log('Q1_RESTART_BARRIER',{state:await control('state')});
 await c.close();await c.boot('restored-with-guard',true,true);const document=await pending('e-restored-first');assert.equal(document.method,'GET');await zero('e-restored-first');await control('approve',{id:document.id});
 const first=await pending('e-restored-first');assert.notEqual(first.id,document.id);assert.equal(first.method,'POST');await zero('e-restored-first');await control('cancel',{id:first.id});log('Q1_RESTORED_FIRST_SCRIPT',{document,first,receiver:c.rows('e-restored-first'),guard:(await control('state')).guard});
 const persisted=await ev("(async()=>({named:localStorage.syntheticNamed17e,opfs:await (await (await (await navigator.storage.getDirectory()).getFileHandle('outbox17e')).getFile()).text(),idb:await outbox17()}))()");assert.ok(Object.keys(persisted).length===Object.keys(stored).length&&Object.entries(stored).every(([key,value])=>persisted[key]===value),'All three queue contents survive browser restart');log('Q10_BROWSER_RESTART',{persisted:queueEvidence(persisted),guardRetained:true});await c.context();
 await ev("outbox17().then(value=>send('e-outbox-resolution',value));true");await pending('e-outbox-resolution');await zero('e-outbox-resolution');await approve('e-outbox-resolution');await delivered('e-outbox-resolution');assert.equal(c.arrivals('e-outbox-resolution')[0].sha256,c.hash(stored.idb));
 const cleaned=await ev('clearOutbox17()');assert.deepEqual(cleaned,{named:null,idb:null,opfsMissing:true});assert.equal((await control('state')).guard,true);log('Q10_FIXTURE_ADAPTER_RESOLUTION',{receiver:c.rows('e-outbox-resolution'),cleaned,scope:'trusted fixture knows its three queues; not a generic browser observer'});await guard(false);await c.nav();await c.close();await c.boot('post-resolution-fixture');await c.context();
 for(const point of ['held','before-consume','after-consume']){
  for(const actor of ['native-host','extension','browser','checkpoint']){
   const id=`e-crash-${actor}-${point}`;await positive(id+'-control');await guard();await send(id);const op=await pending(id);await zero(id);
   if(point!=='held'){await control('stall',{point});await control('approve',{id:op.id});if(point==='after-consume')await c.eventually(async()=>(await control('state')).rows.some(r=>r.id===op.id&&r.status==='consumed'),'durable consumption');else await delay(150);}
   if(actor==='checkpoint')await c.stopProxy();
   if(actor==='browser')await c.close(true);
   if(actor==='native-host'){const pid=Number(c.fs.readFileSync(c.work+'/host-pids.txt','utf8').trim().split('\n').at(-1));c.sudo('kill','-KILL',String(pid));}
   if(actor==='extension'){
    const lines=c.sh('ps',['-u','areschrome','-o','pid,args']).split('\n').filter(s=>s.includes('--extension-process'));
    assert.ok(lines.length,'extension process exists');for(const line of lines)c.sudo('kill','-KILL',line.trim().split(/\s+/)[0]);
   }
   await delay(300);await zero(id);log('Q6_CRASH_POINT',{actor,point,operation:op,receiver:c.rows(id)});
   // Drop the live operation rather than release during recovery. Consumed
   // operations have uncertain outcomes and never become pending again.
   await c.stopProxy();await c.startProxy();const state=await control('state');const recovered=state.rows.find(r=>r.id===op.id);assert.equal(recovered.status,point==='after-consume'?'unknown':'lost');await zero(id);await assert.rejects(()=>control('approve',{id:op.id}),/NOT_PENDING/);
   log('Q6_RECOVERY',{actor,point,recovered,automaticReplay:false});
   // Reconnect through an unguarded fixture navigation only after the previous
   // operation was lost/unknown; no consumed operation is reused.
   await guard(false);await c.close(true);await c.boot('recovery-'+actor+'-'+point);await c.context();
  }
 }
 // Kill each actor during forwarding, triggered by the independent receiver's
 // first body byte rather than a sleep after approval.
 for(const actor of ['native-host','extension','browser','checkpoint']){
  const id='e-during-forward-'+actor;await positive(id+'-control');await guard();
  await ev(`send('${id}',new Uint8Array(25*1024*1024));true`);const forwarding=await pending(id);await zero(id);let killed;
  c.f.onFirstByte(caseId=>{if(caseId===id&&!killed)killed=(async()=>{
   if(actor==='checkpoint')await c.stopProxy();
   else if(actor==='browser')await c.close(true);
   else if(actor==='native-host'){const pid=Number(c.fs.readFileSync(c.work+'/host-pids.txt','utf8').trim().split('\n').at(-1));c.sudo('kill','-KILL',String(pid));}
   else {const lines=c.sh('ps',['-u','areschrome','-o','pid,args']).split('\n').filter(s=>s.includes('--extension-process'));assert.ok(lines.length);for(const line of lines)c.sudo('kill','-KILL',line.trim().split(/\s+/)[0]);}
  })()});
  await control('approve',{id:forwarding.id});await c.eventually(()=>!!killed,'receiver-triggered forwarding crash');await killed;c.f.onFirstByte(undefined);await delay(500);
  await c.stopProxy();await c.startProxy();await delay(300);const recovered=(await control('state')).rows.find(r=>r.id===forwarding.id);assert.ok(['unknown','response'].includes(recovered.status));
  const complete=c.arrivals(id).length;assert.ok(complete<=1);c.expect(id,'http',complete);c.expect(id,'headers',1);log('Q6_DURING_FORWARD',{actor,recovered,receiver:c.rows(id)});
  await guard(false);await c.close(true);await c.boot('forwarding-recovery-'+actor);await c.context();
 }
 // Real cancellation observations. Do not equate a JS timeout with an abort.
 for(const variant of ['abort','h2-reset','tab-close','timeout']){
  const id='e-cancel-'+variant;await positive(id+'-control');await guard();
  if(variant==='h2-reset')await ev(`globalThis.abort17=new AbortController();fetch('https://fixture.test:18443/receive?case=${id}',{method:'POST',body:'cancel',signal:abort17.signal}).catch(()=>{});true`);
  else await ev(`globalThis.abort17=new AbortController();send('${id}','cancel',{signal:abort17.signal});true`);
  const op=await pending(id);
  if(variant==='abort'||variant==='h2-reset')await ev('abort17.abort();true');
  if(variant==='tab-close'){await rpc('Check.close');await delay(300);}else if(variant==='timeout')await ev("results.internalTimeout='page gave up without aborting';true");
  await delay(400);const before=(await control('state')).rows.find(r=>r.id===op.id);let approval;try{approval=await control('approve',{id:op.id})}catch(e){approval={error:e.message}}await delay(500);
  const after=(await control('state')).rows.find(r=>r.id===op.id);log('Q7_LATE_APPROVAL',{variant,before,after,approval,receiver:c.rows(id),supported:after.status==='cancelled'});
  if(c.arrivals(id).length)await delivered(id);else await zero(id); // Keep late arrivals in the final audit.
  if(variant==='tab-close'){await guard(false);const tab=await rpc('Check.open',{url:c.f.base+'/'});await delay(600);await rpc('Check.attach',{tabId:tab.id});}
 }
 await guard(false);await c.nav();await guard();await send('e-explicit-cancel');const cancelled=await pending('e-explicit-cancel');await control('cancel',{id:cancelled.id});await delay(200);await assert.rejects(()=>control('approve',{id:cancelled.id}),/NOT_PENDING/);await zero('e-explicit-cancel');log('Q7_ACKNOWLEDGED_CANCEL',{cancelled});
 // Extension removal cannot remove the independent checkpoint. Schedule first;
 // removal necessarily destroys the diagnostic channel.
 await ev("setTimeout(()=>send('e-extension-removed'),20000);true");c.policy(true,false);await c.key('ctrl+t');await c.address('chrome://policy');c.x('mousemove',85,170,'click',1);
 await c.eventually(async()=>{try{await rpc('Check.state');return false}catch{return true}},'policy actually removed the extension',90000);const removedAt=Date.now();await c.screenshot(c.out,'extension-removed-by-policy');await delay(10000);const removed=await pending('e-extension-removed');assert.ok(removed.capturedAt>removedAt,'request created after confirmed extension removal');await zero('e-extension-removed');log('Q3_EXTENSION_REMOVAL',{removedAt,held:removed});
 // Retiring requires independent receiver receipt AND explicit fixture cleanup;
 // this is an adapter example, not a negative inference from silence.
 log('Q10_RETIREMENT',{automatic:false,guard:(await control('state')).guard,reason:'Only the trusted fixture adapter proved resolution. The later held send remains unresolved; an empty queue is not generic retirement evidence.'});
}
