import assert from 'node:assert/strict';
import fs from 'node:fs';
import {lateInputTypes,lateTypedTypes} from './late-reader-fixtures.mjs';
import {refOf} from './act-matrix.mjs';

const privateValue=/SENTINEL_PRIVATE_PASSWORD_20|PRIVATE_REVEALED/;
const unreadValue=/PUBLIC_TYPED_(?:text|tel|unknown|search)_20|PUBLIC_TEXTAREA_20|PUBLIC_UNLABELLED_20/;
const fieldLine=(text,label)=>{
  const line=text.split('\n').find(line=>line.includes(' "'+label+'"'));
  assert.ok(line,'the public form shows '+label);return line.trimStart();
};
export async function lateReaderMatrix({check,nav,call,readPage,fixture,ownerNavigate,getTab}){
  const evidence=[];
  await check('GROUP 7 POST18D credentials and revealed passwords stay unreadable before take reload',async()=>{
    for(const watched of [false,true]){
      const id='post18d-late-'+watched;
      if(watched)await nav('review-page&mode=late-reader&id='+id);
      else{
        await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=late-reader&id='+id);
        await call('take_tab',{tab:getTab()});
      }
      const page=await readPage(getTab(),{full:true});
      const form=await readPage(getTab(),{ref:refOf(page.text,'form')});
      assert.doesNotMatch(JSON.stringify([page.pages,form.pages]),privateValue);
      for(const text of [page.text,form.text]){
        for(const type of lateInputTypes){
          const line=fieldLine(text,'Type '+type);
          if(!watched&&lateTypedTypes.includes(type))assert.match(line,/\(filled, not read\)/,type);
          else if(['checkbox','radio'].includes(type))assert.ok(line.startsWith(type+' '),type);
          else assert.match(line,/ = "/,type+' remains readable');
        }
        const textarea=fieldLine(text,'Safe textarea');
        assert.match(textarea,watched?/ = "PUBLIC_TEXTAREA_20"/:/\(filled, not read\)/);
        assert.match(fieldLine(text,'Safe editor'),/ = "PUBLIC_EDITOR_20"/);
        for(const label of ['Previous search','Previous email','Previous url','Long value']){
          const line=fieldLine(text,label);
          assert.match(line,watched?/^password .*\(not read\)/:/\(filled, not read\)/,label);
          assert.doesNotMatch(line,/ = "/,label);
        }
        for(const term of ['Distanz','Tank']){
          const line=fieldLine(text,term);assert.doesNotMatch(line,/^password /,term);
          if(watched)assert.ok(line.includes(' = "PUBLIC_ORDINARY_'+term+'_20"'),term);
          else assert.match(line,/\(filled, not read\)/,term);
        }
      }
      if(!watched){
        assert.doesNotMatch(JSON.stringify([page.pages,form.pages]),unreadValue);
        const prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.ok(prepared.approval);assert.match(prepared.approval.question,/single-line field/);
        assert.doesNotMatch(JSON.stringify(prepared.approval),/SENTINEL_PRIVATE_PASSWORD_20|PUBLIC_TYPED_|PUBLIC_UNLABELLED_20/);
        await call('drop',{operation_id:prepared.approval.operation_id});await call('read_typed_fields',prepared.approval);
        assert.doesNotMatch(JSON.stringify(await readPage(getTab(),{full:true})),unreadValue);
        evidence.push({watched,page,form,denied:prepared});
      }else evidence.push({watched,page,form});
    }
  });
  await check('GROUP 7 POST18D typed field reads require exact one-call approval and reask on list changes',async()=>{
    const id='post18d-typed-approval';await call('release_tab',{tab:getTab()});await ownerNavigate('http://fixture.test:8765/?case=review-page&mode=late-reader&id='+id);await call('take_tab',{tab:getTab()});
    const prepared=await call('prepare_read_typed_fields',{tab:getTab()});assert.ok(prepared.approval);
    const approved=await call('read_typed_fields',prepared.approval);assert.equal(approved.operation.state,'done');
    assert.match(JSON.stringify(approved.untrusted_content),/PUBLIC_TYPED_text_20/);assert.match(JSON.stringify(approved.untrusted_content),/PUBLIC_UNLABELLED_20/);assert.match(JSON.stringify(approved.untrusted_content),/PRIVATE_REVEALED_TEXTAREA_20/);
    assert.doesNotMatch(JSON.stringify(approved),/SENTINEL_PRIVATE_PASSWORD_20/);
    const repeat=await call('read_typed_fields',prepared.approval);assert.ok(!repeat.untrusted_content);assert.doesNotMatch(JSON.stringify(repeat),/PUBLIC_TYPED_|PUBLIC_UNLABELLED_20/);
    assert.doesNotMatch(JSON.stringify(await readPage(getTab(),{full:true})),unreadValue);
    const changing=await call('prepare_read_typed_fields',{tab:getTab()});await fixture.mutate(id,'review-change');
    const reasked=await call('read_typed_fields',changing.approval);assert.equal(reasked.operation.state,'failed');assert.ok(reasked.approval);assert.match(reasked.approval.question,/Changed text label/);assert.match(reasked.approval.question,/Added field/);
    assert.doesNotMatch(JSON.stringify(reasked),/PUBLIC_TYPED_|PUBLIC_ADDED_20|SENTINEL_PRIVATE_PASSWORD_20/);
    const fresh=await call('read_typed_fields',reasked.approval);assert.equal(fresh.operation.state,'done');assert.match(JSON.stringify(fresh.untrusted_content),/PUBLIC_ADDED_20/);
    evidence.push({prepared,approved,repeat,changing,reasked,fresh});
  });
  fs.writeFileSync('/out/late-reader.json',JSON.stringify(evidence,null,2));
}
