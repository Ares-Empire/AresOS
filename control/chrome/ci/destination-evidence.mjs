import assert from 'node:assert/strict';
import {destinationRows} from './destination-fixtures.mjs';
export function assertDestinations(evidence,snapshots,arrivals){
  const rows=destinationRows();assert.equal(evidence.length,rows.length);
  for(const row of rows){
    const saved=evidence.filter(item=>item.id===row.id);assert.equal(saved.length,1,row.id);
    for(const key of Object.keys(row))assert.equal(saved[0][key],row[key]);
    const {prepared,reasked}=saved[0],before=prepared.approval.description.untrusted_content.page_state,after=reasked.approval.description.untrusted_content.page_state;
    assert.equal(new URL(before.form?.action||before.target.href).pathname,'/first/receive');
    assert.equal(new URL(after.form?.action||after.target.href).pathname,row.change==='target'?'/first/receive':'/second/receive');
    assert.equal(before.form?.browsing_target||before.target.browsing_target,'sink-first');
    assert.equal(after.form?.browsing_target||after.target.browsing_target,row.change==='target'?'sink-second':'sink-first');
    assert.equal(reasked.operation.state,'failed');assert.notEqual(prepared.approval.operation_id,reasked.approval.operation_id);
    const temporal=snapshots.filter(item=>item.id===row.id);
    assert.deepEqual(temporal.map(item=>[item.phase,item.count]),[['changed destination held',0],['stale destination approval stays retired',0],['before approval',0],['after approval',1],['after repeat',1]],row.id);
    const raw=arrivals.filter(item=>new URL(item.url,'http://fixture.test').searchParams.get('case')===row.id);
    assert.equal(raw.length,1,row.id);assert.equal(new URL(raw[0].url,'http://fixture.test').pathname,row.change==='target'?'/first/receive':'/second/receive');
  }
  return {sources:7,cases:rows.length,complete_0_1_1:rows.length,independent_arrivals_match:true};
}
