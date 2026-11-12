// Test-build observation only: no mark writes, timers, messages back or allowances.
import assert from 'node:assert/strict';
export function instrumentOwnerGuard(source){
  const insert=(before,after)=>{assert.equal(source.split(before).length,2,before);source=source.replace(before,after);};
  insert('const ownerTasks=new MessageChannel();',`const ownerTasks=new MessageChannel();
  function traceOwner(phase,step=null){
    const url=new URL(location.href);if(url.searchParams.get('mode')!=='owner-overlap')return;
    chrome.runtime.sendMessage({event:'owner_trace',id:url.searchParams.get('id'),phase,step,time:performance.timeOrigin+performance.now(),token:owner?.token??null,key:owner?.event.key??null,input:owner?type(owner.event):null,consumed:owner?.consumed??null,in_flight:inFlight}).catch(()=>{});
  }`);
  insert('if(owner?.token===event.data)owner=null;',"if(owner?.token===event.data){traceOwner('clear');owner=null;}");
  insert('owner={event,form,submitter,token,defaultSubmission,consumed:false,changed:false};',"traceOwner('replace');owner={event,form,submitter,token,defaultSubmission,consumed:false,changed:false};traceOwner('set');");
  insert('owner.consumed=true;return true;',"owner.consumed=true;traceOwner('pass');return true;");
  insert('held.set(id,{...step,node:element,button:submitter});',"traceOwner('held',id);held.set(id,{...step,node:element,button:submitter});");
  return source;
}
export function assertOwnerOverlap(id,arrivals,traces){
  const rows=arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='trace-'+id).map(row=>({...JSON.parse(row.body),receiver_time:row.time}));
  const phase=name=>{const matching=rows.filter(row=>row.phase===name);assert.equal(matching.length,1,name);return matching[0];};
  const entered=phase('owner-enter'),submitted=phase('owner-submit'),timer=phase('timer-fire');
  assert(entered.time<=submitted.time&&submitted.time<=timer.time,'owner Enter submits before the timer callback');
  const entering=traces.find(row=>row.id===id&&row.phase==='set'&&row.key==='Enter'&&row.input==='keydown'&&!row.in_flight&&row.time<=entered.time);
  // Chrome's implicit Enter submission generates a trusted submitter click.
  // That click has its own exact owner mark rather than a keyboard key.
  const pass=traces.find(row=>row.id===id&&row.phase==='pass'&&row.consumed===true&&!row.in_flight&&row.time>=entered.time&&row.time<=submitted.time&&(row.input==='click'||row.key==='Enter'&&['keydown','keypress'].includes(row.input)));
  const passSet=pass&&traces.find(row=>row.id===id&&row.phase==='set'&&row.token===pass.token&&row.input===pass.input&&!row.in_flight&&row.time<=pass.time);
  assert(entering&&pass&&passSet,'the immediate native owner submission must consume its private input allowance');
  const held=traces.find(row=>row.id===id&&row.phase==='held'&&row.key==='Enter'&&!row.in_flight);
  assert(held,'the private Enter mark must still exist when the timer submission is held');
  const set=traces.find(row=>row.id===id&&row.phase==='set'&&row.token===held.token);
  const ended=traces.find(row=>row.id===id&&['clear','replace'].includes(row.phase)&&row.token===held.token&&row.time>=held.time);
  assert(set&&ended,'mark interval needs both independent endpoints');
  assert(set.time<=timer.time&&timer.time<=held.time&&held.time<=ended.time,'the real timer fires inside the private mark interval');
  const owner=arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')==='owner-'+id);
  assert.equal(owner.length,1,'his own Enter reaches the receiver once without approval');
  assert(owner[0].time>=submitted.time-1&&owner[0].time-submitted.time<200,'his Enter is delivered immediately');
  return {id,page:rows,mark:{set,held,ended},owner_enter:entering,owner_pass:pass,owner_arrival:owner[0]};
}
