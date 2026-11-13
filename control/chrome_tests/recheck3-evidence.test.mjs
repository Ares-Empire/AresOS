// Artifact-only validation; this test starts no browser.
import test from 'node:test';
import assert from 'node:assert/strict';
import {assertRecheck3} from '../chrome/ci/recheck3-evidence.mjs';
import {browserMixes} from '../chrome/ci/guard-matrix.mjs';
import {defaultRows,whitespaceKinds,whitespaceText,whitespaceChanges} from '../chrome/ci/recheck3-fixtures.mjs';
const shown=text=>text.replaceAll('\n','\\u000a');
function fixture(){
  const evidence={mixed:[],defaults:[],whitespace:[]},snapshots=[],arrivals=[];
  const once=(id,body,method='POST')=>{snapshots.push(...[['before approval',0],['after approval',1],['after repeat',1]].map(([phase,count])=>({id,phase,count})));arrivals.push({url:'/receive?case='+id,body,method});};
  for(const row of browserMixes()){
    const id=`recheck3-mix-${row.mask}-${row.mode}-${row.composed}-${row.order}${row.foreign?'-foreign':''}${row.adopted?'-adopted':''}`;
    evidence.mixed.push({...row,id,stopped:{untrusted_content:{steps:[{kind:'activation'}]}},boundaries:row.foreign?[{phase:'mixed-child-ready',exposed:false},{phase:'mixed-parent-ready',exposed:false}]:[]});snapshots.push({id,phase:'mixed handler held',count:0});once(id,'mixed handler');
  }
  for(const row of defaultRows()){
    const {id,kind,route}=row;evidence.defaults.push({...row,stopped:{followups:['non-cancellable default was stopped']}});
    const link=kind==='a'||kind==='area'||kind.startsWith('svg');once(id,link?'':kind.endsWith('reset')?'reset':'draft=Native+default',link?'GET':'POST');
    snapshots.push({id,phase:'native default held',count:0},{id:'ping-'+id,phase:'native ping held',count:0});
    if(route==='ping')arrivals.push({url:'/receive?case=ping-'+id,method:'POST',body:'PING'});
  }
  for(const kind of whitespaceKinds)for(const change of whitespaceChanges(kind)){
    const id='recheck3-space-'+kind+'-'+change,render=text=>shown(kind==='pre-line'?text.replace(/^[ \t]+/gm,''):text);
    const approval=(text,operation_id)=>({operation_id,question:render(text),description:{untrusted_content:{page_state:{compose:{text:render(text)}}}}});
    const prepared={approval:approval(whitespaceText.before,'old')},reasked={operation:{state:'failed'},approval:approval(whitespaceText[change],'new')};reasked.approval.question+=' from '+render(whitespaceText.before);
    evidence.whitespace.push({id,kind,change,prepared,reasked,stopped:{operation:{state:'failed',reason:'text next to Send keeps changing; owner sends himself'}},fresh:{approval:approval(whitespaceText.line+'\n','fresh')}});
    snapshots.push({id,phase:'bounded whitespace stop and repeat',count:0});once(id,whitespaceText.line+'\n');
  }
  return {evidence,snapshots,arrivals};
}
test('recheck3 independent evidence audit accepts the complete 134 exact receiver sequences',()=>{
  const f=fixture();assert.deepEqual(assertRecheck3(f.evidence,f.snapshots,f.arrivals),{mixed:60,defaults:60,whitespace:14,complete_0_1_1:134,independent_arrivals_match:true});
});
test('recheck3 independent evidence audit rejects omitted rows early arrivals whitespace loss and wrong final bytes',()=>{
  for(const mutate of [f=>f.evidence.mixed.pop(),f=>{f.evidence.mixed.find(row=>row.foreign).boundaries[0].exposed=true;},f=>{f.snapshots.find(row=>row.phase==='native default held').count=1;},f=>{f.evidence.whitespace[0].prepared.approval.description.untrusted_content.page_state.compose.text='collapsed';},f=>{f.arrivals.find(row=>row.url.includes('space-')).body=whitespaceText.line;}]){
    const f=fixture();mutate(f);assert.throws(()=>assertRecheck3(f.evidence,f.snapshots,f.arrivals));
  }
});
