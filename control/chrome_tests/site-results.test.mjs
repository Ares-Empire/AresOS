import test from 'node:test';
import assert from 'node:assert/strict';
import {REQUIRED,verdicts} from '../chrome/ci/verdicts.mjs';
import {collectSiteResults} from '../chrome/ci/site-results.mjs';

const names=Object.values(REQUIRED).flat().filter(name=>name.includes(' ADAPTER '));
const rows=()=>names.map(name=>({name,passed:true}));
const failure=results=>Object.assign(new AggregateError([Error('fixture assertion')],'Adapter requirements failed; see adapters.json and adapters-receiver.jsonl'),{results});
test('a completed adapter failure reaches final failing matrix while independent adapters remain eligible',async()=>{
  const results=rows().map(row=>row.name==='GROUP 10 ADAPTER Gemini question uses its required semantic name'?{...row,passed:false,error:'strict fixture assertion'}:row);
  const collected=await collectSiteResults(async()=>{throw failure(results);});assert.equal(collected,results);
  const core=Object.values(REQUIRED).flat().filter(name=>!names.includes(name)).map(name=>({name,passed:true}));
  const support=['FEATURE tools forms options find wait fill_form scroll and full catalogues','VIEW representative long article/form complete paging','QUALIFICATION conservative activations ask and core failures gate before reads'].map(name=>({name,passed:true}));
  const result=verdicts([...core,...collected,...support],{owner:true,forgery:true,isolation:true,residual:true},Object.fromEntries(['gmail','whatsapp','github','bank','gemini','deezer'].map(site=>[site,true])));
  assert.equal(result.adapters.gemini,false);assert.equal(result.adapters.gmail,true);
  assert.equal([...core,...collected].filter(row=>!row.passed).length,1,'the browser final aggregate still fails');
});
test('adapter crashes missing rows duplicated rows and nonboolean outcomes never become completed evidence',async()=>{
  const candidates=[new Error('crash'),failure(rows().slice(1)),failure([...rows(),rows()[0]]),failure(rows().map((row,i)=>i?row:{...row,passed:'false'})),failure(rows())];
  for(const error of candidates)await assert.rejects(collectSiteResults(async()=>{throw error;}),actual=>actual===error);
  await assert.rejects(collectSiteResults(async()=>rows().slice(1)),/Incomplete/);
  assert.equal((await collectSiteResults(async()=>rows())).length,names.length);
});
