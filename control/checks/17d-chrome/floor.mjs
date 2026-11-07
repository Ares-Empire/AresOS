export default async function(c){
 const {rpc,ev,nav,log,state,count,delay,f,end,restart,arrivals,discovery,save}=c;
 // Positive controls qualify each generator; form navigation is last.
 await rpc('Check.mode',{mode:'pass'});
 for(const kind of ['fetch','xhr','beacon','ping','ws','form']){await nav();const id='control-'+kind;await ev(`attempt('${id}','${kind}')`);await count(id,1);}
 await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'fail'});
 for(const kind of ['fetch','xhr','beacon','ping','ws','form'])for(const cross of [false,true]){
  await nav();await rpc('Check.clear');const id='floor-'+kind+'-'+cross;await ev(`attempt('${id}','${kind}',${cross})`);await delay(600);await count(id,0);const s=await state();c.assert.equal(s.history.filter(e=>e.method==='check.gate').length,0,'DNR must precede Fetch: '+id);log('Q1_BLOCK',{id,kind,cross,gate:s.history.filter(e=>e.method==='check.gate'),events:s.history,arrivals:arrivals(id)});
 }
 // Session rule covers a foreign frame, even when its initiator is not guarded.
 await nav();await rpc('Check.floor',{tabId:c.selected});await ev(`window.foreign=document.createElement('iframe');foreign.src='${f.base.replace('127.0.0.1','localhost')}/';document.body.append(foreign);true`);await delay(700);
 const frames=await rpc('Check.frameProbe');c.assert.ok(frames.some(r=>r.result?.includes('localhost')),'foreign frame actually executed');await count('foreign-frame',0);log('Q1_FOREIGN_FRAME',{frames,events:(await state()).history.slice(-20)});
 // Park at Fetch if Chrome exposes it, then break control while producers keep running.
 for(const ending of ['detach','reload','update','worker-crash','host-loss','normal','kill','policy']){
  await nav();await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'park'});await rpc('Check.clear');const id='ending-'+ending;
  await ev(`attempt('${id}');setTimeout(()=>attempt('${id}-after'),600);true`);await delay(150);save(id+'-before',await state());await end(ending);await delay(800);
  if(ending==='policy'){await c.address(f.base+'/startup?prefix=policy-unloaded');log('Q1_POLICY_UNLOADED',{same:discovery('policy-unloaded-same','first send after policy block'),cross:discovery('policy-unloaded-cross','cross-site first send after policy block')});}
  log('Q1_END',{ending,before:discovery(id,'ending-control diagnostic'),after:discovery(id+'-after','requests while/after ending control'),zero:arrivals(id).length+arrivals(id+'-after').length===0});await restart('after-'+ending);
 }
 // Persisted dynamic guard; no automatic debugger attach at extension/browser start.
 await rpc('Check.floor',{domains:['127.0.0.1']});await rpc('Check.mode',{mode:'pass'});
 for(const killed of [false,true]){
  await nav(f.base+'/startup');await rpc('Page.bringToFront');await count('startup-same',0);await count('startup-cross',0);
  const before=f.rows.filter(r=>r.kind==='attempt'&&r.case==='startup-executed').length;
  if(killed)await delay(7000);await c.close(killed);await c.boot('restored-'+killed,true);await c.eventually(()=>f.rows.filter(r=>r.kind==='attempt'&&r.case==='startup-executed').length>before,'restored first script really ran');await count('startup-same',0);await count('startup-cross',0);
  log('Q2_RESTART',{killed,dynamic:(await state()).dynamic,ready:(await state()).history.filter(e=>e.method==='check.ready'),documents:f.rows.filter(r=>r.kind==='document'&&r.url==='/startup'),arrivals:[...arrivals('startup-same'),...arrivals('startup-cross')]});
 }
}
