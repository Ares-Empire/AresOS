import test from 'node:test';
import assert from 'node:assert/strict';
import {assertNativeLimit,nativeLimitModes,nativeLimitCapabilities,settleClipboard} from '../chrome/ci/activation-evidence.mjs';
function evidence(active=true){
  const rows=[],arrivals=[];
  for(const mode of nativeLimitModes)for(const capability of nativeLimitCapabilities){
    const id='recheck2b-limit-'+mode+'-'+capability;
    const observations={};
    for(const cause of ['alone','claude']){
      const observed={id,cause,capability,trusted:false,secure:true,before:{active:cause==='claude'&&active},atHandler:{active:cause==='claude'&&active},outcome:'synthetic capability outcome'};observations[cause]=observed;
      arrivals.push({url:'/receive?case='+id+'-'+cause,body:JSON.stringify({cause,before:observed.before,atHandler:observed.atHandler,trusted:false})});
    }
    rows.push({id,mode,capability,alone:observations.alone,clicked:observations.claude,added_transient_activation:active,
      result:{untrusted_content:{dispatched:true,steps:[],page:{notices:['Hostile native Delete handler ran']}},followups:[]},
      status:{operation:{stages:{dispatched:{untrusted_content:'Input dispatched once; delivery not proven.'}},reason:'Free input dispatched once, as the page shows it.'}}});
  }
  return {rows,arrivals};
}
test('native limit audit distinguishes new activation from autonomous native dispatch',()=>{
  for(const active of [true,false]){const e=evidence(active),result=assertNativeLimit(e.rows,e.arrivals);assert.equal(result.activation_review_required,active);assert.equal(result.added_transient_activation.length,active?10:0);}
});
test('native limit audit rejects missing roots capabilities receipts and forged receipt bodies',()=>{
  for(const change of [e=>e.rows.pop(),e=>{e.rows[0].id=e.rows[1].id;},e=>e.arrivals.pop(),e=>{e.arrivals[0].body='{}';}]){const e=evidence();change(e);assert.throws(()=>assertNativeLimit(e.rows,e.arrivals));}
});
test('native limit audit never accepts an activated baseline or a concealed activation increase',()=>{
  for(const change of [e=>{e.rows[0].alone.before.active=true;const observation=e.rows[0].alone;e.arrivals[0].body=JSON.stringify({cause:'alone',before:observation.before,atHandler:observation.atHandler,trusted:false});},e=>{e.rows[0].added_transient_activation=false;}]){const e=evidence();change(e);assert.throws(()=>assertNativeLimit(e.rows,e.arrivals));}
});
test('native limit audit refuses a false stopped or no-effect description',()=>{
  for(const change of [e=>{e.rows[0].result.followups=[{stopped:true}];},e=>{e.rows[0].status.operation.reason='Nothing happened';},e=>{e.rows[0].status.operation.stages.dispatched.untrusted_content='No delivery claim';}]){const e=evidence();change(e);assert.throws(()=>assertNativeLimit(e.rows,e.arrivals));}
});

test('capability measurement keeps pending permission separate from an accepted or rejected write',{timeout:1000},async()=>{
  assert.deepEqual(await settleClipboard(Promise.resolve()),{outcome:'write accepted',error:null});
  assert.deepEqual(await settleClipboard(Promise.reject({name:'NotAllowedError',message:'Permission denied'})),{outcome:'rejected',error:{name:'NotAllowedError',message:'Permission denied'}});
  let complete;const pending=new Promise(resolve=>{complete=resolve;});const result=await settleClipboard(pending,10);
  assert.deepEqual(result,{outcome:'pending browser permission',error:null});complete();await pending;await Promise.resolve();
  assert.equal(result.outcome,'pending browser permission','a later permission outcome cannot rewrite the measurement');
});
