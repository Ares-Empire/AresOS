import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {instrumentLatencyBackground} from '../chrome/ci/latency-instrument.mjs';

test('CI latency overlay preserves results native timers and code with absent historical stages',async()=>{
  for(const modern of [false,true]){
    const messages=[],timers=[];let clock=0;
    const source=`import {POLICY} from './policy.js';
      const port={postMessage:value=>messages.push(value)};const networkHolds=new Map();
      async function rules(){return 7;}async function facts(){return 'Synthetic result';}
      async function finishFrames(){return false;}async function collectSteps(){await new Promise(resolve=>setTimeout(resolve,POLICY.holdMs+25));return [];}
      ${modern?'function holdDefaults(){networkHolds.set(1,{});return rules();}async function observation(){return {available:true};}':''}
      async function dispatch(command){const value=await facts();await collectSteps();return value;}
      async function connect() {return null;}`;
    const instrumented=instrumentLatencyBackground(source).replace("import {POLICY} from './policy.js';",'');
    const context=vm.createContext({POLICY:{holdMs:500},messages,performance:{now:()=>++clock},setTimeout:fn=>{timers.push(525);fn();}});
    vm.runInContext(instrumented,context);
    assert.equal(await vm.runInContext("dispatch({name:'read'})",context),'Synthetic result');
    assert.deepEqual(timers,[525]);assert(messages.some(row=>row.stage==='post_input_observation_wait'));
    assert(messages.every(row=>row.milliseconds>=0));assert(!JSON.stringify(messages).includes('Synthetic result'));
  }
});
