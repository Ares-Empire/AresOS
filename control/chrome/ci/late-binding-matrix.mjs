import assert from 'node:assert/strict';
import fs from 'node:fs';
export async function lateBindingMatrix({check,call,rpc,read,target,fixture,eventually,ownerNavigate,getTab}){
  const evidence=[];
  const take=async(mode,id,extra='')=>{await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode='+mode+'&id='+id+extra);};
  await check('GROUP 7 POST18DF prepared typed reads bind exact elements frames readers questions and one call',async()=>{
    for(const variant of ['replacement','relabel','frame','credential']){
      const id='post18df-binding-'+variant;await take('late-binding',id,'&variant='+variant);
      await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='late-frame-ready'&&row.version==='first'),'owner frame loaded before take');await call('take_tab',{tab:getTab()});
      const prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.ok(prepared.approval);assert.match(prepared.approval.question,/single-line field 3/);
      const manifest=prepared.approval.description.untrusted_content.fields;
      assert(manifest.frames.every(frame=>frame.reader&&frame.document&&frame.browser_document));
      const top=manifest.frames.find(frame=>frame.frame===0);assert.equal(top.fields.filter(field=>field.label==='Value').length,2);assert.equal(new Set(top.fields.map(field=>field.element)).size,3);
      assert.doesNotMatch(JSON.stringify(prepared),/PRIVATE_FIRST|PRIVATE_SECOND|PRIVATE_UNLABELLED|PRIVATE_FRAME/);
      const altered=await rpc('read_typed_fields',{...prepared.approval,question:prepared.approval.question+' changed'});assert.equal(altered.ok,false);
      await fixture.mutate(id,'review-change');if(variant==='frame')await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='late-frame-ready'&&row.version==='next'),'new native frame committed');
      const reasked=await call('read_typed_fields',prepared.approval);assert.equal(reasked.operation.state,'failed');assert.ok(reasked.approval);assert.notEqual(reasked.approval.operation_id,prepared.approval.operation_id);
      assert.doesNotMatch(JSON.stringify(reasked),/PRIVATE_FIRST|PRIVATE_SECOND|PRIVATE_UNLABELLED|PRIVATE_REPLACED|PRIVATE_FRAME|SENTINEL_PRIVATE_PASSWORD_20/);
      const stale=await call('read_typed_fields',prepared.approval);assert.ok(!stale.untrusted_content);
      const approved=await call('read_typed_fields',reasked.approval);assert.equal(approved.operation.state,'done');assert.match(JSON.stringify(approved.untrusted_content),/PRIVATE_SECOND_20/);assert.doesNotMatch(JSON.stringify(approved),/SENTINEL_PRIVATE_PASSWORD_20/);
      if(variant==='replacement')assert.match(JSON.stringify(approved.untrusted_content),/PRIVATE_REPLACED_20/);
      const repeated=await call('read_typed_fields',reasked.approval);assert.ok(!repeated.untrusted_content);
      evidence.push({id,variant,prepared,altered,reasked,stale,approved,repeated});
    }
  });
  await check('GROUP 3 POST18DF late shadow forms refuse withheld content after approved reads and value changes',async()=>{
    const id='post18df-withheld-form';await take('late-withheld-form',id);await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='late-form-ready'),'owner closed shadow form ready');await call('take_tab',{tab:getTab()});
    assert.doesNotMatch(JSON.stringify(await read()),/PRIVATE_LATE_FORM/);
    const submit=async()=>{const result=await rpc('click',await target('Send'));assert.equal(result.ok,false);assert.match(result.error.message,/send it yourself, or reload the tab first with chrome_navigate direction=reload/);assert.equal(fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===id).length,0);return result;};
    const refused=await submit(),prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.match(prepared.approval.question,/Draft/);await fixture.mutate(id,'review-change');
    const approved=await call('read_typed_fields',prepared.approval);assert.match(JSON.stringify(approved.untrusted_content),/PRIVATE_LATE_FORM_B_20/);
    const afterRead=await submit();assert.doesNotMatch(JSON.stringify(await read()),/PRIVATE_LATE_FORM/);const repeat=await call('read_typed_fields',prepared.approval);assert.ok(!repeat.untrusted_content);
    evidence.push({id,refused,prepared,approved,afterRead,repeat});
  });
  fs.writeFileSync('/out/late-binding.json',JSON.stringify(evidence,null,2));
}
