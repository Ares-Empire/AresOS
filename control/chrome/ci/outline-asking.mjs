// Taken tabs, before their reload, through PR #27's unchanged asking tools.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {completeIngress} from './ingress-scan.mjs';

export async function outlineAskingMatrix({check,call,rpc,read,fixture,eventually,ownerNavigate,getTab}){
  const out='/out/outline-read/asking.jsonl';
  const record=(name,result)=>{fs.appendFileSync(out,JSON.stringify({name,result})+'\n');return result;};
  const ingress=()=>completeIngress(fs.readFileSync('/out/browser-boundary.jsonl','utf8')).filter(row=>row?.reader_ingress);
  const unreadSince=start=>{
    const rows=ingress().slice(start);record('unapproved native getters',{count:rows.length});
    assert.ok(!rows.some(row=>/ASK_[A-Z_]+_28/.test(JSON.stringify(row.reader_ingress.value))),'no native getter read an unapproved value');
    assert.ok(!rows.some(row=>JSON.stringify(row).includes('SENTINEL_PRIVATE_PASSWORD_20')),'credentials never reach a getter recording');
  };
  const take=async mode=>{
    const id='outline-ask-'+mode;await call('release_tab',{tab:getTab()});
    await ownerNavigate('http://fixture.test:8765/?case=password-outline&mode='+mode+'&id='+id);
    await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='ask-frame-first'),'asking frame loaded before take');
    await call('take_tab',{tab:getTab()});return id;
  };
  const outline=async extra=>{
    const result=record('normal',await rpc('outline',{tab:getTab(),...extra}));assert.equal(result.ok,true);
    const entry=result.data.reads[0];assert.ok(!entry.error);return entry;
  };
  const prepare=async()=>record('prepare',await call('prepare_read_typed_fields',{tab:getTab()}));
  const clear=async approval=>{await call('drop',{operation_id:approval.operation_id});await call('notice_ack',{operation_id:approval.operation_id});};
  const changed=async mode=>{
    const id=await take(mode),before=await prepare(),binding=before.approval.description.untrusted_content.fields;
    const top=binding.frames.find(frame=>frame.frame===0);assert.ok(top.document&&top.browser_document&&top.reader);
    // Brief 28a, item 3b: the two fields read apart in the question and in the description, by position.
    const alike=(frames,test)=>frames.find(frame=>frame.frame===0).fields.filter(test);
    const same=field=>field.label==='Same',bareField=field=>field.unnamed===true;
    if(mode==='duplicate'){
      assert.equal(new Set(alike(binding.frames,same).map(field=>field.element)).size,2);
      assert.deepEqual(alike(binding.frames,same).map(field=>field.description),['"Same" (1 of 2)','"Same" (2 of 2)']);
      assert.ok(before.approval.question.includes('"Same" (1 of 2), "Same" (2 of 2)'),before.approval.question);
    }
    if(mode==='unlabelled'){
      const bare=alike(binding.frames,bareField);assert.equal(bare.length,2);
      assert.ok(bare.every(field=>field.label.startsWith('single-line field ')));assert.equal(new Set(bare.map(field=>field.element)).size,2);
      assert.deepEqual(bare.map(field=>field.description),['unnamed single-line field (1 of 2)','unnamed single-line field (2 of 2)']);
      for(const field of bare)assert.ok(before.approval.question.includes(field.description),before.approval.question);
    }
    const start=ingress().length;await fixture.mutate(id,'review-change');
    if(mode==='frame')await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='ask-frame-next'),'listed frame navigated');
    const refused=record(mode,await call('read_typed_fields',before.approval));
    assert.equal(refused.operation.state,'failed');assert.ok(refused.approval);assert.notEqual(refused.approval.operation_id,before.approval.operation_id);
    assert.ok(!refused.untrusted_content);assert.doesNotMatch(JSON.stringify(refused),/ASK_[A-Z_]+_28|SENTINEL_PRIVATE_PASSWORD_20/);unreadSince(start);
    const next=refused.approval.description.untrusted_content.fields;
    if(mode==='frame'){
      assert.equal(next.frames.find(frame=>frame.frame===0).document,top.document,'top document stayed');
      assert.notEqual(next.frames.find(frame=>frame.frame!==0).browser_document,binding.frames.find(frame=>frame.frame!==0).browser_document);
    }
    if(mode==='added')assert.ok(refused.approval.question.includes('Added field'));
    // The swapped pair keeps its words; the fresh question binds them to the new order.
    if(mode==='duplicate'||mode==='unlabelled'){
      const test=mode==='duplicate'?same:bareField,old=alike(binding.frames,test),fresh=alike(next.frames,test);
      assert.deepEqual(fresh.map(field=>field.element),old.map(field=>field.element).reverse());
      assert.deepEqual(fresh.map(field=>field.description),old.map(field=>field.description));
    }
    if(mode==='replacement'){
      const field=frames=>frames.find(frame=>frame.frame===0).fields.find(field=>field.label==='Text note');
      assert.notEqual(field(next.frames).element,field(binding.frames).element,'same label, another element');
    }
    await clear(refused.approval);
  };

  await check('READ BRIEF28 taken typed fields stay unread until exact one call approval and credentials stay excluded',async()=>{
    await take('plain');const start=ingress().length,entry=await outline({max:40000});
    assert.equal(entry.typed_fields,9);
    for(const label of ['Text note','Search note','Email note','Area note'])assert.ok(entry.untrusted_content.outline.includes('"'+label+'" (filled, not read)'));
    assert.ok(entry.untrusted_content.outline.includes('"Empty note" (empty)'));
    const refs=[...entry.untrusted_content.outline.matchAll(/(?:textbox|searchbox) [^\n]* ([bcdfghjklmnpqrstvwxyz]{5}\d+)$/gm)].map(match=>match[1]);
    assert.equal(refs.length,10,'every eligible field has a reference, including the two without labels and the frame');
    const normal=[entry,await outline({full:true,max:40000}),await outline({find:'ASK_'})];
    for(const ref of refs)normal.push(await outline({ref,full:true,max:40000}));
    normal.push(await read());assert.doesNotMatch(JSON.stringify(normal),/ASK_[A-Z_]+_28|SENTINEL_PRIVATE_PASSWORD_20/);unreadSince(start);
    const denied=await prepare();await clear(denied.approval);const refused=record('denied',await call('read_typed_fields',denied.approval));assert.ok(!refused.untrusted_content);
    assert.equal((await outline()).typed_fields,9);
    const prepared=await prepare(),manifest=prepared.approval.description.untrusted_content.fields;
    const listed=manifest.frames.flatMap(frame=>frame.fields.map(field=>({frame:frame.frame,...field})));
    assert.equal(listed.length,10);assert.ok(!listed.some(field=>['One time','Password','Covered'].includes(field.label)));
    assert.doesNotMatch(JSON.stringify(prepared),/ASK_[A-Z_]+_28|SENTINEL_PRIVATE_PASSWORD_20/);
    const approved=record('approved',await call('read_typed_fields',prepared.approval));assert.equal(approved.operation.state,'done');
    const returned=approved.untrusted_content.typed_fields.frames.flatMap(frame=>frame.fields.map(field=>({frame:frame.frame,...field})));
    assert.deepEqual(returned.map(({value,...field})=>field),listed,'exactly the identities and descriptions approved');
    assert.deepEqual(returned.map(field=>field.value).sort(),['','ASK_TEXT_28','ASK_SEARCH_28','ASK_EMAIL_28','ASK_AREA_28','ASK_SAME_A_28','ASK_SAME_B_28','ASK_BARE_A_28','ASK_BARE_B_28','ASK_FRAME_28'].sort());
    assert.doesNotMatch(JSON.stringify(approved),/SENTINEL_PRIVATE_PASSWORD_20/);
    const recorded=ingress();
    assert.ok(recorded.some(row=>row.reader_ingress.value==='ASK_TEXT_28'),'approved read reaches the native getter recording');
    assert.ok(!recorded.some(row=>JSON.stringify(row).includes('SENTINEL_PRIVATE_PASSWORD_20')),'credentials never enter the recording, even after approval');
    const replay=record('replay',await call('read_typed_fields',prepared.approval));assert.ok(!replay.untrusted_content);
    assert.doesNotMatch(JSON.stringify(replay),/ASK_[A-Z_]+_28/);assert.equal((await outline()).typed_fields,9);
    const next=await prepare();assert.ok(next.approval,'another one-call read needs a fresh question');await clear(next.approval);
  });

  await check('READ BRIEF28 a field added after the asking question reasks without reading',async()=>changed('added'));
  await check('READ BRIEF28 a same label replacement refuses the asking read before values',async()=>changed('replacement'));
  await check('READ BRIEF28 a changed field label refuses the asking read before values',async()=>changed('label'));
  await check('READ BRIEF28 swapping duplicate labelled fields refuses the asking read before values',async()=>changed('duplicate'));
  await check('READ BRIEF28 swapping unlabelled fields refuses the asking read before values',async()=>changed('unlabelled'));
  await check('READ BRIEF28 a listed frame navigation refuses the asking read before values',async()=>changed('frame'));
  await check('READ BRIEF28 a listed field made password refuses the asking read before values',async()=>changed('type'));
  await check('READ BRIEF28 a listed field masked refuses the asking read before values',async()=>changed('mask'));
  await check('READ BRIEF28 altered asking questions and field lists read no value',async()=>{
    await take('altered');const prepared=await prepare(),start=ingress().length;
    for(const part of ['question','list']){
      const approval=structuredClone(prepared.approval);
      if(part==='question')approval.question+=' changed';else approval.description.untrusted_content.fields.frames[0].fields.pop();
      const result=record('altered '+part,await rpc('read_typed_fields',approval));assert.equal(result.ok,false);
      assert.doesNotMatch(JSON.stringify(result),/ASK_[A-Z_]+_28|SENTINEL_PRIVATE_PASSWORD_20/);
    }
    // Another normal read drains recording events and proves the fields are
    // still withheld, without invoking the approved read.
    assert.equal((await outline()).typed_fields,9);unreadSince(start);await clear(prepared.approval);
  });
}
