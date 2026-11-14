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

test('gate60 the latency client takes the lead sample count for every call and history phase',async()=>{
  // latency-targets.json holds the count (mac-aresos-control, 2026-11-14); the
  // client, the summary and the check all read it.
  const {latencyProbe,LATENCY_SAMPLES}=await import('../chrome/ci/latency-probe.mjs');
  const fs=await import('node:fs');const os=await import('node:os');const path=await import('node:path');
  const targets=JSON.parse(fs.readFileSync(new URL('../chrome/ci/latency-targets.json',import.meta.url),'utf8'));
  assert.equal(LATENCY_SAMPLES,targets.samples_per_call);
  const out=fs.mkdtempSync(path.join(os.tmpdir(),'aresos-latency-client-'));
  try{
    let url=null;const seeds=[];
    const call=async(name,args)=>{
      if(name==='navigate'){url=args.url;return {ok:true};}
      if(name==='read'){const seed=path.join(out,'latency-history-seed.json');if(fs.existsSync(seed)){seeds.push(JSON.parse(fs.readFileSync(seed,'utf8')).count);fs.rmSync(seed);}return {untrusted_content:{url}};}
      if(name==='click')return args.name==='Send'?{approval:{operation:'synthetic'}}:{ok:true};
      if(name==='submit')return {operation:{state:'done'}};
      return {ok:true};
    };
    await latencyProbe({call,target:async name=>({name}),nav:null,eventually:async check=>assert(await check()),getTab:()=>1,out,runtime:'current'});
    const rows=JSON.parse(fs.readFileSync(path.join(out,'latency-client.json'),'utf8')).samples;
    const phases=['fresh','history-1000','history-4000'],calls=['read','navigate','free_click','fill','asking_click','approval_to_done'];
    assert.deepEqual(seeds,[1000,4000]);
    assert.equal(rows.length,phases.length*calls.length*targets.samples_per_call);
    for(const phase of phases)for(const name of calls){
      const samples=rows.filter(row=>row.phase===phase&&row.call===name).map(row=>row.sample);
      assert.deepEqual(samples,Array.from({length:targets.samples_per_call},(_,index)=>phase+':'+index),phase+' '+name);
    }
    assert.equal(fs.existsSync(path.join(out,'latency-marker.json')),false);
  }finally{fs.rmSync(out,{recursive:true,force:true});}
});

test('gate60b the old runtime\'s client takes the reference\'s 20 samples at the reference\'s positions',async()=>{
  // mac-aresos-control, 2026-11-14, after run 43613647256: the old runtime
  // only feeds the runner-noise ratio, so it matches the frozen reference.
  const {latencyProbe,LATENCY_SAMPLES,OLD_RUNTIME_SAMPLES,samplesFor}=await import('../chrome/ci/latency-probe.mjs');
  const fs=await import('node:fs');const os=await import('node:os');const path=await import('node:path');
  const targets=JSON.parse(fs.readFileSync(new URL('../chrome/ci/latency-targets.json',import.meta.url),'utf8'));
  const reference=JSON.parse(fs.readFileSync(new URL('../chrome/ci/latency-reference.json',import.meta.url),'utf8'));
  assert.deepEqual([LATENCY_SAMPLES,OLD_RUNTIME_SAMPLES],[60,20]);
  assert.deepEqual([samplesFor('current'),samplesFor(targets.baseline)],[60,20]);
  assert.throws(()=>samplesFor('other'),/unknown latency runtime/);
  const phases=['fresh','history-1000','history-4000'],calls=['read','navigate','free_click','fill','asking_click','approval_to_done'];
  for(const [runtime,count] of [[targets.baseline,20],['current',60]]){
    // The container names its runtime in LATENCY_BASELINE (latency-pair.sh).
    const out=fs.mkdtempSync(path.join(os.tmpdir(),'aresos-latency-client-')),previous=process.env.LATENCY_BASELINE;
    process.env.LATENCY_BASELINE=runtime;
    try{
      let url=null;
      const call=async(name,args)=>{
        if(name==='navigate'){url=args.url;return {ok:true};}
        if(name==='read'){fs.rmSync(path.join(out,'latency-history-seed.json'),{force:true});return {untrusted_content:{url}};}
        if(name==='click')return args.name==='Send'?{approval:{operation:'synthetic'}}:{ok:true};
        if(name==='submit')return {operation:{state:'done'}};
        return {ok:true};
      };
      await latencyProbe({call,target:async name=>({name}),nav:null,eventually:async check=>assert(await check()),getTab:()=>1,out});
      const client=JSON.parse(fs.readFileSync(path.join(out,'latency-client.json'),'utf8'));
      assert.equal(client.baseline,runtime);assert.equal(client.samples.length,phases.length*calls.length*count);
      for(const phase of phases)for(const name of calls){
        const samples=client.samples.filter(row=>row.phase===phase&&row.call===name).map(row=>row.sample);
        assert.deepEqual(samples,Array.from({length:count},(_,index)=>phase+':'+index),runtime+' '+phase+' '+name);
        if(runtime!==targets.baseline||!['free_click','fill','approval_to_done'].includes(name))continue;
        // The old runtime's input samples sit where the reference's do, in both profiles.
        for(const profile of ['plain','audit'])assert.deepEqual(new Set(samples),new Set(reference.profiles[profile].baseline.input_samples.filter(row=>row.phase===phase&&row.call===name).map(row=>row.sample)),profile+' '+phase+' '+name);
      }
    }finally{if(previous===undefined)delete process.env.LATENCY_BASELINE;else process.env.LATENCY_BASELINE=previous;fs.rmSync(out,{recursive:true,force:true});}
  }
});
