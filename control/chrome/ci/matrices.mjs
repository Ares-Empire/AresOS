// Synthetic browser cases, imported only by the Linux-container entry point.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {setTimeout as delay} from 'node:timers/promises';

export async function matrices({call,read,nav,target,counts,eventually,tab,fixture}) {
  const results=[];
  async function check(name,fn) {
    try {await fn();results.push({name,passed:true});console.log(name,'PASS');}
    catch(error){results.push({name,passed:false,error:String(error.stack)});console.error(name,'FAIL',error.stack);}
  }
  async function approval(result,id) {
    const prepared=result.approval ? result:result.followups?.find(item=>item.approval);
    assert.ok(prepared?.approval,JSON.stringify(result));assert.equal(counts(id),0,'zero arrivals before approval');
    await call('submit',prepared.approval);await eventually(()=>counts(id)===1,'one receiver arrival '+id);
    await call('submit',prepared.approval);await delay(30);assert.equal(counts(id),1,'a second attempt sends nothing');
  }
  async function setup(parameters) {await nav('matrix&'+new URLSearchParams(parameters));}
  const words=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]).words;
  await check('GROUP 1 what asks word/label/key matrix',async()=>{
    for(const word of words)for(const label of ['name','aria','title','value','labelledby','label'])for(const route of ['click','Enter','Space']){
      const id='word-'+word+'-'+label+'-'+route;await setup({id,mode:'word',word,label});
      const row=(await read()).find(row=>row.expected.role==='button');assert.ok(row);
      const args={reference:row.reference,expected:row.expected};
      const result=route==='click'?await call('click',args):await call('press',{...args,key:route});
      await approval(result,id);
    }
  });
  await check('GROUP 2 stopped page steps handler/resume matrix',async()=>{
    for(const submit of ['native','event','button'])for(const route of ['click','key','fill','select','check']){
      const id='stopped-'+submit+'-'+route;await setup({id,mode:'stopped',submit,route});let result;
      if(route==='click')result=await call('click',await target('Continue'));
      else if(route==='key')result=await call('press',{...await target('Continue'),key:'x'});
      else if(route==='fill')result=await call('fill',{...await target('Trigger text'),text:'Changed'});
      else if(route==='select')result=await call('select',{...await target('Trigger choice'),value:'b'});
      else result=await call('check',{...await target('Trigger check'),checked:true});
      await approval(result,id);
    }
  });
  await check('GROUP 2 script activations never replay',async()=>{
    for(const wrapped of ['click','cancelable','noncancelable']){
      const id='activation-'+wrapped;await setup({id,mode:'activation',wrapped});
      const result=await call('click',await target('Continue'));
      assert.equal(counts(id),0);assert.equal(counts('handler-'+id),0);assert.ok(result.followups.some(item=>item.stopped));
      const direct=await call('click',await target('Delete'));await approval(direct,id);
      assert.equal(counts('handler-'+id),1);
    }
  });
  await check('GROUP 13 autosave and after-limit submissions are not held',async()=>{
    await nav('residual');await call('fill',{...await target('Autosave'),text:'Synthetic autosave'});
    await eventually(()=>counts('residual-autosave')>=1,'autosave residual');
    await setup({id:'residual-late',mode:'residual-delay'});const result=await call('click',await target('Continue'));
    assert.equal(result.followups.length,0);await eventually(()=>counts('residual-late')===1,'after-limit residual');
  });
  await check('VIEW representative long article/form complete paging',async()=>{
    await setup({id:'long',mode:'long'});let cursor,tree='',pages=0;const started=Date.now();
    do{const page=await call('read',{tab,...(cursor?{cursor}:{})});assert.ok(page.untrusted_content.tree.length<=16000);tree+=page.untrusted_content.tree;cursor=page.cursor;pages++;}while(cursor);
    assert.match(tree,/Paragraph 119/);assert.match(tree,/Field 79/);
    const measurement={characters:tree.length,utf8_bytes:Buffer.byteLength(tree),pages,milliseconds:Date.now()-started,token_estimate:Math.ceil(tree.length/4)};
    fs.writeFileSync('/out/view-measurements.json',JSON.stringify(measurement,null,2));console.log('VIEW MEASURED',JSON.stringify(measurement));
  });
  fs.writeFileSync('/out/matrices.json',JSON.stringify(results,null,2));
  return results.filter(item=>!item.passed);
}
