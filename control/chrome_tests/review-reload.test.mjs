// Pure fixture scheduling regression; no browser or profile is accessed.
import test from 'node:test';
import assert from 'node:assert/strict';
import {guardedHandoffClick} from '../chrome/ci/review-matrices.mjs';

function scenario({inputError,initialError}={}){
  const before={reference:{document:'old',view:'old-view'},expected:{name:'Ready'}};
  const revisions=[before,{reference:{document:'new',view:'parser-3'}},{reference:{document:'new',view:'parser-4'}},{reference:{document:'new',view:'parser-4'}}];
  let reads=0,inputs=0;const requests=[],snapshots=[];
  const context={
    id:'synthetic-handoff',
    async target(label){assert.equal(label,'Ready');return reads++===0?before:revisions.shift();},
    async rpc(action,args){
      assert.equal(action,'click');requests.push(args);
      if(args.discard_unsaved)return {ok:false,error:{code:'stale_reference',message:initialError||'The taken tab reloaded to install its page guard. Every old reference is stale; read again.'}};
      assert.deepEqual(args,before);return {ok:false,error:{code:'stale_reference',message:'Document changed'}};
    },
    async eventually(check){for(let index=0;index<8;index++){assert.equal(inputs,0,'No input may run while the parser/view settles');const result=await check();if(result)return result;}throw Error('Fixture failed to settle');},
    receiverEvidence(id,phase){assert.equal(id,'synthetic-handoff');snapshots.push(phase);return {count:1};},
    async call(action,args){assert.equal(action,'click');inputs++;assert.equal(args.reference.document,'new');assert.equal(args.reference.view,'parser-4','The revision-3 snapshot must not dispatch');assert.equal(revisions.length,0,'Two agreeing post-parser reads must precede input');if(inputError)throw inputError;return {};},
  };
  return {context,state:()=>({reads,inputs,requests,snapshots})};
}

test('preexisting dialog fixture waits through delayed parser revisions before one guarded input',async()=>{
  const value=scenario();await guardedHandoffClick(value.context);
  const state=value.state();assert.equal(state.reads,5);assert.equal(state.inputs,1);assert.equal(state.requests.length,2);
  assert.deepEqual(state.snapshots,['reload settled before guarded act','old reference still refuses','first guarded act after handoff']);
});

test('preexisting dialog fixture never retries a dispatched input with an uncertain outcome',async()=>{
  const value=scenario({inputError:Error('unknown: inspect the page; never replay')});
  await assert.rejects(guardedHandoffClick(value.context),/unknown: inspect the page/);
  assert.equal(value.state().inputs,1);
});

test('preexisting dialog fixture requires the intended guarded-reload refusal',async()=>{
  const value=scenario({initialError:'Page changed for another reason'});
  await assert.rejects(guardedHandoffClick(value.context),/reloaded to install its page guard/);
  assert.equal(value.state().reads,1);assert.equal(value.state().inputs,0);
});
