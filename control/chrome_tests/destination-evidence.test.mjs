import test from 'node:test';
import assert from 'node:assert/strict';
import {destinationRows} from '../chrome/ci/destination-fixtures.mjs';
import {assertDestinations} from '../chrome/ci/destination-evidence.mjs';
function fixture(){
  const evidence=[],snapshots=[],arrivals=[];
  for(const row of destinationRows()){
    const before={target:{href:'http://fixture.test/first/receive',browsing_target:'sink-first'}},after=structuredClone(before);
    after.target.href='http://fixture.test/'+(row.change==='target'?'first':'second')+'/receive';
    if(row.change==='target')after.target.browsing_target='sink-second';
    const approval=state=>({operation_id:state===before?'old':'fresh',description:{untrusted_content:{page_state:state}}});
    evidence.push({...row,prepared:{approval:approval(before)},reasked:{operation:{state:'failed'},approval:approval(after)}});
    for(const [phase,count] of [['changed destination held',0],['stale destination approval stays retired',0],['before approval',0],['after approval',1],['after repeat',1]])snapshots.push({id:row.id,phase,count});
    arrivals.push({url:new URL(after.target.href).pathname+'?case='+row.id});
  }
  return {evidence,snapshots,arrivals};
}
test('post18d independent destination audit requires every source and zero arrivals through stale approval',()=>{
  const f=fixture();assert.equal(assertDestinations(f.evidence,f.snapshots,f.arrivals).cases,62);
  for(const mutate of [f=>f.evidence.pop(),f=>f.snapshots[0].count=1,f=>f.arrivals.push(f.arrivals[0]),f=>f.evidence[0].reasked.approval.operation_id='old',f=>f.arrivals[0].url=f.arrivals[0].url.replace('/second/','/first/')]){
    const changed=fixture();mutate(changed);assert.throws(()=>assertDestinations(changed.evidence,changed.snapshots,changed.arrivals));
  }
});
