import assert from 'node:assert/strict';
import fs from 'node:fs';
import {performance} from 'node:perf_hooks';
export async function latencyProbe({call,target,nav,eventually,getTab}){
  const rows=[];
  async function measure(sample,name,fn){fs.writeFileSync('/out/latency-marker.json',JSON.stringify({sample,call:name}));const start=performance.now();try{return await fn();}finally{rows.push({sample,call:name,milliseconds:performance.now()-start});fs.rmSync('/out/latency-marker.json',{force:true});}}
  for(let sample=0;sample<20;sample++){
    const url='http://localhost:8765/?case=latency&id='+sample;
    await measure(sample,'navigate',()=>call('navigate',{tab:getTab(),url}));
    await eventually(async()=>String((await call('read',{tab:getTab()})).untrusted_content.url)===url,'latency fixture committed');
    await measure(sample,'read',()=>call('read',{tab:getTab()}));
    const free=await target('Continue');await measure(sample,'free_click',()=>call('click',free));
    const draft=await target('Draft');await measure(sample,'fill',()=>call('fill',{...draft,text:'Synthetic latency draft '+sample}));
    const send=await target('Send');const prepared=await measure(sample,'asking_click',()=>call('click',send));assert(prepared.approval);
    const approved=await measure(sample,'approval_to_done',()=>call('submit',prepared.approval));assert.equal(approved.operation.state,'done');
  }
  fs.writeFileSync('/out/latency-client.json',JSON.stringify({samples:rows,privacy:process.env.LATENCY_PRIVACY||'plain',baseline:process.env.LATENCY_BASELINE||'current'},null,2));
  console.log('Latency probe complete:',rows.length,'calls, 20 per category; no owner think time');
}
