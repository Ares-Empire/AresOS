// Shared by the Linux fixture and the independent, artifact-only reviewer.
import assert from 'node:assert/strict';
import {browserMixes} from './guard-matrix.mjs';
import {defaultRows,whitespaceKinds,whitespaceText} from './recheck3-fixtures.mjs';
const shown=text=>text.replaceAll('\\','\\\\').replaceAll('\n','\\u000a');
export function assertRecheck3(evidence,snapshots,arrivals){
  const ids=new Set(),cases=new Map();
  for(const row of arrivals){const id=new URL(row.url,'http://fixture.test').searchParams.get('case');if(!cases.has(id))cases.set(id,[]);cases.get(id).push(row);}
  function once(id){
    ids.add(id);const rows=snapshots.filter(row=>row.id===id);
    assert.deepEqual(rows.filter(row=>['before approval','after approval','after repeat'].includes(row.phase)).map(row=>[row.phase,row.count]),[['before approval',0],['after approval',1],['after repeat',1]],id);
    for(const row of rows)if(!['after approval','after repeat','only the approved handler ran','fresh whitespace body received exactly'].includes(row.phase))assert.equal(row.count,0,id+' '+row.phase);
    const raw=cases.get(id)||[];assert.equal(raw.length,1,id+' independent arrival');return raw[0];
  }
  const mixes=browserMixes();assert.equal(evidence.mixed.length,mixes.length);
  for(const row of mixes){
    const id=`recheck3-mix-${row.mask}-${row.mode}-${row.composed}-${row.order}`,found=evidence.mixed.filter(item=>item.id===id);assert.equal(found.length,1,id);const saved=found[0];
    for(const key of Object.keys(row))assert.equal(saved[key],row[key],id+' '+key);
    assert.equal(saved.stopped.untrusted_content.steps.length,1);assert.equal(saved.stopped.untrusted_content.steps[0].kind,'activation');
    assert.equal(once(id).body,'mixed handler');
  }
  const defaults=defaultRows();assert.equal(evidence.defaults.length,defaults.length);
  for(const {id,kind,route}of defaults){
    const found=evidence.defaults.filter(item=>item.id===id);assert.equal(found.length,1,id);assert.equal(found[0].kind,kind);assert.equal(found[0].route,route);
    assert.match(JSON.stringify(found[0].stopped.followups),/non-cancellable default was stopped/);
    const raw=once(id);
    if(kind==='a'||kind==='area'||kind.startsWith('svg'))assert.equal(raw.method,'GET',id);
    else if(kind.endsWith('reset'))assert.equal(raw.body,'reset');
    else{assert.equal(raw.method,'POST');assert.equal(new URLSearchParams(raw.body).get('draft'),'Native default');}
    const ping='ping-'+id,pings=cases.get(ping)||[];
    const held=snapshots.filter(row=>row.id===ping&&row.phase==='native ping held');assert.equal(held.length,1);assert.equal(held[0].count,0);
    assert.equal(pings.length,route==='ping'?1:0,ping);
  }
  const spaces=whitespaceKinds.flatMap(kind=>(kind==='pre-line'?['line']:['indent','line']).map(change=>({kind,change,id:'recheck3-space-'+kind+'-'+change})));
  assert.equal(evidence.whitespace.length,spaces.length);
  for(const {kind,change,id}of spaces){
    const found=evidence.whitespace.filter(item=>item.id===id);assert.equal(found.length,1,id);const row=found[0],render=text=>shown(kind==='pre-line'?text.replace(/^[ \t]+/gm,''):text);
    assert.equal(row.kind,kind);assert.equal(row.change,change);
    for(const key of ['question'])assert(row.prepared.approval[key].includes(render(whitespaceText.before)),id+' original question');
    assert(row.prepared.approval.description.untrusted_content.page_state.compose.text.includes(render(whitespaceText.before)),id+' original binding');
    assert(row.reasked.approval.question.includes(render(whitespaceText.before)));assert(row.reasked.approval.question.includes(render(whitespaceText[change])));
    assert(row.reasked.approval.description.untrusted_content.page_state.compose.text.includes(render(whitespaceText[change])));
    assert.equal(row.reasked.operation.state,'failed');assert.notEqual(row.prepared.approval.operation_id,row.reasked.approval.operation_id);
    assert.equal(row.stopped.operation.state,'failed');assert(!row.stopped.approval);assert.match(row.stopped.operation.reason,/text next to Send keeps changing.*owner/);
    assert(row.fresh.approval.description.untrusted_content.page_state.compose.text.includes(render(whitespaceText.line+'\n')));
    assert.equal(once(id).body,whitespaceText.line+'\n',id+' exact final whitespace');
  }
  return {mixed:mixes.length,defaults:defaults.length,whitespace:spaces.length,complete_0_1_1:ids.size,independent_arrivals_match:true};
}
