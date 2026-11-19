import test from 'node:test';
import assert from 'node:assert/strict';
import {harnessTools} from '../chrome/ci/harness-tools.mjs';

const ok=data=>({ok:true,data,pending:{items:[]}});
const outline=(text,other={})=>ok({reads:[{untrusted_content:{outline:text,...other}}]});
const action=entry=>ok({steps:[entry],prepared:[],untrusted_content:{stopped:[]}});
const row=(element,name='Send',role='button')=>({reference:{tab:7,element,document:'d1',view:'old'},
  expected:{name,role,value:'synthetic evidence'}});
const lossMessage='This action may discard work. Nothing was done; inspect the loss report.';
const lossEntry={code:'reload_required',message:lossMessage};
const loss={act:'first_input',fields:[{description:'field "Draft"',by:'owner'}],more_fields:0,frames_uninspected:0,media:false};

function harness(respond,{modern=true}={}){
  const requests=[];
  return {requests,...harnessTools({
    wire:async(name,args)=>{requests.push([name,args]);return respond(name,args);},
    modern:async()=>modern,eventually:async check=>check(),currentTab:()=>7,
  })};
}

test('an asking click on the second equally named field uses its actual contextual ref and preserves the approval',async()=>{
  const approval={question:'Exact question?',description:{untrusted_content:{binding:'synthetic'}},operation_id:'one'};
  const h=harness(name=>name==='chrome_read'
    ? outline('button "Send" bcdft1 · in form "First"\nbutton "Send" bcdft2 · in form "Second"')
    : ok({...action({do:'click',outcome:'prepared'}).data,prepared:[{approval}]}));
  const rows=[row('e1'),row('e2')];
  const second=await h.selectedTarget(rows[1],rows);
  assert.equal((await h.call('click',second)).approval,approval);
  assert.deepEqual(h.requests,[
    ['chrome_read',{tab:7,find:'Send',max:40000}],
    ['chrome_do',{tab:7,steps:[{do:'click',ref:'bcdft2'}]}],
  ]);
});

test('a held input never regenerates a stale reference or resubmits its step',async()=>{
  const h=harness(name=>name==='chrome_read'?outline('button "Send" bcdft7')
    : {...action({outcome:'stale',code:'stale_reference',message:'It changed.'}),
      data:{...action({outcome:'stale',code:'stale_reference',message:'It changed.'}).data,
        untrusted_content:{now:'button "Changed" bcdft7',stopped:[]}}});
  const only=row('e7');
  const target=await h.selectedTarget(only,[only]);
  const result=await h.rpc('press',{...target,key:'Enter',discard_unsaved:true});
  assert.deepEqual(result.error,{code:'stale_reference',message:'It changed.',
    untrusted_content:{now:'button "Changed" bcdft7'}});
  assert.deepEqual(h.requests.map(([name])=>name),['chrome_read','chrome_do']);
  assert.deepEqual(h.requests[1][1],{tab:7,steps:[{do:'press',ref:'bcdft7',key:'Enter'}],discard_unsaved:true});
});

test('an ordinary dialog is shown at observation time and its separate preparation stays a followup',async()=>{
  const dialog={id:'native-one',kind:'prompt',text:'Continue?'};
  const held={approval:{question:'Send exact form?'}};
  const h=harness(name=>{
    if(name==='read')return ok({untrusted_content:{dialog}});
    if(name==='chrome_read')return outline('',{dialog:{kind:dialog.kind,text:dialog.text}});
    return ok({steps:[{do:'dialog',outcome:'done',operation_id:'answer'}],prepared:[held],untrusted_content:{stopped:[]}});
  });
  await h.call('read',{tab:7});
  const result=await h.call('dialog',{tab:7,expected:dialog,accept:true,text:'Yes'});
  assert.equal(result.approval,undefined);
  assert.deepEqual(result.followups,[held]);
  assert.deepEqual(h.requests,[
    ['read',{tab:7}],['chrome_read',{tab:7}],['chrome_do',{tab:7,steps:[{do:'dialog',accept:true,text:'Yes'}]}],
  ]);
});

test('loss reports must remain in the raw step, bare error, and matching kept tab envelope',async()=>{
  const h=harness(name=>{
    if(name==='chrome_do')return ok({steps:[{outcome:'refused',...lossEntry}],prepared:[],untrusted_content:{loss:{...loss,step:0}}});
    if(name==='chrome_go')return {ok:false,error:{...lossEntry,untrusted_content:{loss:{...loss,act:'reload'}}}};
    return ok({closed:[],kept:[{tab:7,...lossEntry,untrusted_content:{title:'"Example"',loss:{...loss,act:'close'}}}]});
  });
  for(const [name,args,act] of [
    ['click',{tab:7,ref:'bcdft9'},'first_input'],['navigate',{tab:7,direction:'reload'},'reload'],['close_tab',{tab:7},'close'],
  ]){
    const result=await h.rpc(name,args);
    assert.equal(result.ok,false);
    assert.equal(result.error.message,lossMessage);
    assert.equal(result.error.untrusted_content.loss.act,act);
  }
  const malformed=harness(()=>ok({steps:[{outcome:'refused',...lossEntry}],prepared:[],untrusted_content:{loss}}));
  await assert.rejects(malformed.rpc('click',{tab:7,ref:'bcdft9'}));
  const unsafe=harness(()=>({ok:false,error:{...lossEntry,message:loss.fields[0].description,untrusted_content:{loss}}}));
  await assert.rejects(unsafe.rpc('navigate',{tab:7,direction:'reload'}));
});

test('a committed observation belongs to the exact dispatched operation',async()=>{
  const page={dispatched:true,page:{notices:['Synthetic notice']},steps:[]};
  const h=harness(name=>name==='chrome_do'?action({outcome:'done',operation_id:'dispatched-one'})
    : ok({operation:{stages:{page:{untrusted_content:page}}}}));
  const result=await h.call('click',{tab:7,ref:'bcdft1'},{committed:true});
  assert.equal(result.untrusted_content,page);
  assert.deepEqual(h.requests[1],['chrome_operation_status',{operation_id:'dispatched-one'}]);
});

test('explicit public calls and legacy measurements keep their wire arguments and result',async()=>{
  const a=action({outcome:'done'}),h=harness(()=>a);
  const input={tab:7,steps:[{do:'click',ref:'bcdft1'}]};
  assert.equal(await h.rpc('chrome_do',input),a);
  assert.deepEqual(h.requests,[['chrome_do',input]]);
  const old=harness(()=>a,{modern:false}),target=row('e1');
  assert.equal(await old.rpc('click',target),a);
  assert.deepEqual(old.requests,[['click',target]]);
});
