import assert from 'node:assert/strict';
export const nativeLimitModes=['open','closed'];
export const nativeLimitCapabilities=['network','popup','download','clipboard','payment'];
export function assertNativeLimit(rows,arrivals){
  assert.equal(rows.length,10,'both roots and all five capability probes are required');
  const added=[];
  for(const mode of nativeLimitModes)for(const capability of nativeLimitCapabilities){
    const id='recheck2b-limit-'+mode+'-'+capability,matching=rows.filter(row=>row.id===id);
    assert.equal(matching.length,1,id);const row=matching[0];
    assert.equal(row.mode,mode);assert.equal(row.capability,capability);
    for(const [cause,observation]of [['alone',row.alone],['claude',row.clicked]]){
      assert.equal(observation.id,id);assert.equal(observation.cause,cause);assert.equal(observation.capability,capability);
      assert.equal(observation.trusted,false);assert.equal(observation.secure,true);
      assert.equal(typeof observation.atHandler.active,'boolean');assert.equal(typeof observation.before.active,'boolean');
      const receipt=arrivals.filter(value=>new URL(value.url,'http://fixture.test').searchParams.get('case')===id+'-'+cause);
      assert.equal(receipt.length,1,id+' '+cause+' handler must have exactly one independent receipt');
      assert.deepEqual(JSON.parse(receipt[0].body),{cause,before:observation.before,atHandler:observation.atHandler,trusted:false});
    }
    assert.equal(row.alone.before.active,false,'baseline must have no transient activation');
    assert.equal(row.alone.atHandler.active,false,'autonomous native dispatch must not gain activation');
    const extra=!row.alone.atHandler.active&&row.clicked.atHandler.active;
    assert.equal(row.added_transient_activation,extra,'do not label new activation as harmless');if(extra)added.push(id);
    assert.equal(row.result.untrusted_content.dispatched,true);assert.deepEqual(row.result.untrusted_content.steps,[]);assert.deepEqual(row.result.followups,[]);
    assert(row.result.untrusted_content.page.notices.includes('Hostile native Delete handler ran'));
    assert.match(row.status.operation.stages.dispatched,/delivery not proven/);
    assert.match(row.status.operation.reason,/Free input dispatched once/);
    assert.doesNotMatch(row.status.operation.reason,/nothing|stopped|no input/i);
  }
  return {cases:rows.length,added_transient_activation:added,activation_review_required:added.length>0,
    reporting:'The original input is reported as dispatched; the hidden native step has no held/unknown report. The page notice is untrusted.'};
}
