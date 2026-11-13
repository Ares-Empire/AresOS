import test from 'node:test';
import assert from 'node:assert/strict';
import {destinationRows} from '../chrome/ci/destination-fixtures.mjs';
import {assertDestinations} from '../chrome/ci/destination-evidence.mjs';
function fixture(){
  const evidence=[],snapshots=[],arrivals=[],contexts=[];
  for(const row of destinationRows()){
    const before={tab:77,target:{href:'http://fixture.test/first/receive',browsing_target:row.change==='svg-self'?'_self':'sink-first'}},after=structuredClone(before);
    after.target.href='http://fixture.test/'+(row.change.endsWith('target')?'first':'second')+'/receive';
    if(row.change.endsWith('target'))after.target.browsing_target='sink-second';
    const approval=state=>({operation_id:state===before?'old':'fresh',description:{untrusted_content:{page_state:state}}});
    const context={id:row.id,phase:'destination-context',name:after.target.browsing_target,top:row.change==='svg-self',url:after.target.href+'?case='+row.id};contexts.push(context);
    evidence.push({...row,prepared:{approval:approval(before)},reasked:{operation:{state:'failed'},approval:approval(after)},context,nativeTab:{tab:77,controlled:true,url:context.top?context.url:'http://fixture.test/?case=review-page&id='+row.id}});
    for(const [phase,count] of [['changed destination held',0],['stale destination approval stays retired',0],['before approval',0],['after approval',1],['after repeat',1]])snapshots.push({id:row.id,phase,count});
    arrivals.push({url:new URL(after.target.href).pathname+'?case='+row.id});
  }
  return {evidence,snapshots,arrivals,contexts};
}
test('post18d independent destination audit requires every source and zero arrivals through stale approval',()=>{
  const f=fixture();assert.equal(assertDestinations(f.evidence,f.snapshots,f.arrivals,f.contexts).cases,66);
  for(const mutate of [f=>f.evidence.pop(),f=>f.contexts.pop(),f=>f.evidence[0].nativeTab.url='http://fixture.test/?id=wrong',f=>f.contexts[0].top=true,f=>f.snapshots[0].count=1,f=>f.arrivals.push(f.arrivals[0]),f=>f.evidence[0].reasked.approval.operation_id='old',f=>f.arrivals[0].url=f.arrivals[0].url.replace('/second/','/first/')]){
    const changed=fixture();mutate(changed);assert.throws(()=>assertDestinations(changed.evidence,changed.snapshots,changed.arrivals,changed.contexts));
  }
});
