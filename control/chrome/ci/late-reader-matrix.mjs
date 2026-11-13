import assert from 'node:assert/strict';
import fs from 'node:fs';
import {lateInputTypes} from './late-reader-fixtures.mjs';
export async function lateReaderMatrix({check,nav,call,rpc,read,target,fixture,eventually,ownerNavigate,getTab}){
  const evidence=[];
  await check('GROUP 7 POST18D credentials and revealed passwords stay unreadable before take reload',async()=>{
    for(const watched of [false,true]){
      const id='post18d-late-'+watched;
      if(watched)await nav('review-page&mode=late-reader&id='+id);
      else{
        await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=late-reader&id='+id);
        await call('take_tab',{tab:getTab()});
      }
      const rows=await read();assert.doesNotMatch(JSON.stringify(rows),/SENTINEL_PRIVATE_PASSWORD_20/);
      for(const type of lateInputTypes){
        const row=rows.find(row=>row.expected.name==='Type '+type);assert.ok(row,type);
        if(!watched&&['text','tel','number','unknown'].includes(type)){assert.equal(row.expected.value_status,'filled',type);assert.equal(row.expected.value,undefined);}
        else assert.equal(typeof row.expected.value,'string',type+' remains readable');
      }
      assert.equal(rows.find(row=>row.expected.name==='Safe textarea').expected.value,'PUBLIC_TEXTAREA_20');
      assert.equal(rows.find(row=>row.expected.name==='Safe editor').expected.value,'PUBLIC_EDITOR_20');
      const form=await call('read_form',{tab:getTab(),reference:(await target('Type text')).reference});assert.doesNotMatch(JSON.stringify(form),/SENTINEL_PRIVATE_PASSWORD_20/);
      if(!watched){
        assert.doesNotMatch(JSON.stringify(form),/PUBLIC_TYPED_(?:text|tel|unknown)_20/);
        const prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.ok(prepared.approval);assert.match(prepared.approval.question,/single-line field/);
        assert.doesNotMatch(JSON.stringify(prepared.approval),/SENTINEL_PRIVATE_PASSWORD_20|PUBLIC_TYPED_|PUBLIC_UNLABELLED_20/);
        await call('drop',{operation_id:prepared.approval.operation_id});await call('read_typed_fields',prepared.approval);
        assert.doesNotMatch(JSON.stringify(await read()),/PUBLIC_TYPED_(?:text|tel|unknown)_20|PUBLIC_UNLABELLED_20/);
        evidence.push({watched,rows,form,denied:prepared});
      }else evidence.push({watched,rows,form});
    }
  });
  await check('GROUP 7 POST18D typed field reads require exact one-call approval and reask on list changes',async()=>{
    const id='post18d-typed-approval';await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=late-reader&id='+id);await call('take_tab',{tab:getTab()});
    const prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.ok(prepared.approval);
    const approved=await call('read_typed_fields',prepared.approval);assert.equal(approved.operation.state,'done');
    assert.match(JSON.stringify(approved.untrusted_content),/PUBLIC_TYPED_text_20/);assert.match(JSON.stringify(approved.untrusted_content),/PUBLIC_UNLABELLED_20/);
    assert.doesNotMatch(JSON.stringify(approved),/SENTINEL_PRIVATE_PASSWORD_20/);
    const repeat=await call('read_typed_fields',prepared.approval);assert.ok(!repeat.untrusted_content);assert.doesNotMatch(JSON.stringify(repeat),/PUBLIC_TYPED_|PUBLIC_UNLABELLED_20/);
    assert.doesNotMatch(JSON.stringify(await read()),/PUBLIC_TYPED_(?:text|tel|unknown)_20|PUBLIC_UNLABELLED_20/);
    const changing=await call('prepare_read_typed_fields',{tab:getTab()});await fixture.mutate(id,'review-change');
    const reasked=await call('read_typed_fields',changing.approval);assert.equal(reasked.operation.state,'failed');assert.ok(reasked.approval);assert.match(reasked.approval.question,/Changed text label/);assert.match(reasked.approval.question,/Added field/);
    assert.doesNotMatch(JSON.stringify(reasked),/PUBLIC_TYPED_|PUBLIC_ADDED_20|SENTINEL_PRIVATE_PASSWORD_20/);
    const fresh=await call('read_typed_fields',reasked.approval);assert.equal(fresh.operation.state,'done');assert.match(JSON.stringify(fresh.untrusted_content),/PUBLIC_ADDED_20/);
    evidence.push({prepared,approved,repeat,changing,reasked,fresh});
  });
  fs.writeFileSync('/out/late-reader.json',JSON.stringify(evidence,null,2));
}
