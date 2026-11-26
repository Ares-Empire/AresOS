// Only recorded native replies and public results; no browser or profile.
import test from 'node:test';
import assert from 'node:assert/strict';
import {approvedTypedFields} from '../chrome/ci/outline-asking.mjs';

function sample(){
  const fields=[{element:'e1',label:'Same',type:'text',description:'"Same" (1 of 2)'},
    {element:'e2',label:'Same',type:'text',description:'"Same" (2 of 2)'}];
  const manifest={frames:[{frame:0,document:'doc',reader:'reader',fields}]};
  const native=fields.map(({description,...field},index)=>({...field,value:'ASK_'+index}));
  const boundary=[{reader_ingress:{value:'ASK_0'}},{ok:true,data:{document:'doc',reader:'reader',fields:native}}];
  const result={untrusted_content:{typed_fields:fields.map(({label,description},index)=>({label,description,ref:'kqtvm'+(index+1),value:JSON.stringify('ASK_'+index)}))}};
  return {manifest,boundary,result};
}

test('asking-read public rows retain the approved identities, descriptions and quoted native values',()=>{
  const {result,manifest,boundary}=sample();
  const rows=approvedTypedFields(result,manifest,boundary);
  assert.deepEqual(rows.map(({value,...field})=>field),manifest.frames[0].fields.map(field=>({frame:0,...field})));
  assert.deepEqual(rows.map(field=>field.value),['ASK_0','ASK_1']);
});

test('the asking-read check refuses mismatched native identities and changed public descriptions or values',()=>{
  for(const change of [s=>s.boundary[1].data.fields.reverse(),s=>s.boundary[1].data.reader='other',
    s=>s.result.untrusted_content.typed_fields.pop(),s=>s.result.untrusted_content.typed_fields[0].description='"Same" (2 of 2)',
    s=>s.result.untrusted_content.typed_fields[0].value='ASK_0',s=>s.result.untrusted_content.typed_fields[1].ref='kqtvm1']){
    const s=sample();change(s);assert.throws(()=>approvedTypedFields(s.result,s.manifest,s.boundary));
  }
});

test('the historical catalogue still checks its original asking-read frame result',()=>{
  const {manifest}=sample();
  const result={untrusted_content:{typed_fields:{frames:manifest.frames}}};
  assert.deepEqual(approvedTypedFields(result,manifest,[]),manifest.frames[0].fields.map(field=>({frame:0,...field})));
});
