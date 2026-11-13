import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {REQUIRED,ADAPTER_REQUIRED,SUPPORT,verdicts,assertComplete} from '../chrome/ci/verdicts.mjs';

const support=['FEATURE tools forms options find wait fill_form scroll and full catalogues','VIEW representative long article/form complete paging','QUALIFICATION conservative activations ask and core failures gate before reads'];
const complete=()=>[...Object.values(REQUIRED).flat(),...support].map(name=>({name,passed:true}));
const baseline={owner:true,forgery:true,isolation:true,residual:true};
const adapters=Object.fromEntries(['gmail','whatsapp','github','bank','gemini','deezer'].map(name=>[name,true]));

test('qualification never turns missing or failed named cases into passing groups',()=>{
  assert.ok(Object.values(verdicts(complete(),baseline,adapters).core).every(Boolean));
  for(const [group,names]of Object.entries(REQUIRED))for(const name of names){
    assert.equal(verdicts(complete().filter(item=>item.name!==name),baseline,adapters).groups[group],false,name);
    assert.equal(verdicts(complete().map(item=>item.name===name?{...item,passed:false}:item),baseline,adapters).groups[group],false,name);
  }
});

test('failed support suites and owner trust checks cannot publish adapter or core passes',()=>{
  for(const name of support){
    const result=verdicts(complete().filter(item=>item.name!==name),baseline,adapters);
    assert.ok(Object.values(result.core).every(value=>value===false));
    assert.ok(Object.values(result.adapters).every(value=>value===false));
  }
  assert.ok(Object.values(verdicts(complete().filter(item=>!item.name.startsWith('GROUP 11')),baseline,adapters).adapters).every(value=>value===false));
});

test('strict owner false hold remains a failing page-script result',()=>{
  const result=verdicts(complete(),{...baseline,owner:false},adapters);
  assert.equal(result.groups[2],false);assert.equal(result.core.page_script,false);
});


test('every mandatory failure reaches a recorded core or adapter switch, not only the unused group map',()=>{
  for(const name of Object.values(REQUIRED).flat()){
    for(const changed of [complete().filter(item=>item.name!==name),complete().map(item=>item.name===name?{...item,passed:false}:item)]){
      const result=verdicts(changed,baseline,adapters);
      assert.ok([...Object.values(result.core),...Object.values(result.adapters)].some(value=>value===false),name);
    }
  }
});

test('duplicate or nonboolean case evidence cannot qualify',()=>{
  const name=REQUIRED[1][0];
  for(const rows of [[...complete(),{name,passed:false}],[...complete(),{name,passed:true}],complete().map(item=>item.name===name?{...item,passed:'false'}:item)]){
    assert.equal(verdicts(rows,baseline,adapters).core.classification,false);
  }
});


test('unmapped additional checks fail closed until explicitly assigned to recorded groups',()=>{
  for(const passed of [true,false]){
    const result=verdicts([...complete(),{name:'GROUP 7 additional isolation regression',passed}],baseline,adapters);
    assert.ok(Object.values(result.core).every(value=>value===false));assert.ok(Object.values(result.adapters).every(value=>value===false));
  }
});

test('every named core popup and adapter case is in the exact required inventory',()=>{
  const names=['control/chrome/ci/matrices.mjs','control/chrome/ci/review-matrices.mjs','control/chrome/ci/recheck2-matrices.mjs','control/chrome/ci/recheck3-matrices.mjs','control/chrome/ci/popups.mjs','control/chrome/ci/sites/matrices.mjs'].flatMap(file=>
    [...fs.readFileSync(file,'utf8').matchAll(/await check\('([^']+)'/g)].flatMap(match=>match[1]==='GROUP 10 adapter '?['gmail','whatsapp','github','gemini','deezer'].map(site=>match[1]+site):[match[1]]));
  assert.deepEqual([...names].sort(),[...Object.values(REQUIRED).flat(),...SUPPORT].sort());
  assert.equal(verdicts(complete(),baseline,adapters).groups[12],false);
});

test('one adapter failure preserves all independent adapter verdicts',()=>{
  for(const [site,names]of Object.entries(ADAPTER_REQUIRED))for(const name of names.filter(name=>Object.values(ADAPTER_REQUIRED).filter(rows=>rows.includes(name)).length===1)){
    for(const rows of [complete().filter(row=>row.name!==name),complete().map(row=>row.name===name?{...row,passed:false}:row)]){
      const result=verdicts(rows,baseline,adapters);
      for(const other of Object.keys(adapters))assert.equal(result.adapters[other],other!==site,site+': '+name+' -> '+other);
      assert.ok(Object.values(result.core).every(Boolean),'adapter-only failure cannot disable core');
    }
  }
});

test('multi-adapter matrices preserve sites outside their actual fixture coverage',()=>{
  for(const [name,affected]of [
    ['GROUP 10 ADAPTER clear merge settings and sharing variants stay guarded',['github','gemini','deezer']],
    ['GROUP 10 adapter shortcuts and account-specific questions',['gmail','whatsapp','gemini']],
  ])for(const rows of [complete().filter(row=>row.name!==name),complete().map(row=>row.name===name?{...row,passed:false}:row)]){
    const result=verdicts(rows,baseline,adapters);
    for(const site of Object.keys(adapters))assert.equal(result.adapters[site],!affected.includes(site),name+' -> '+site);
    assert.ok(Object.values(result.core).every(Boolean),'adapter matrix failure cannot disable generic core');
  }
});

test('shared binding classification isolation and owner prerequisites disable dependent adapters',()=>{
  for(const name of [REQUIRED[1][0],REQUIRED[3][0],REQUIRED[6][0],REQUIRED[7][0],REQUIRED[11][0],'GROUP 10 ADAPTER unfamiliar pages and qualification fallback on all sites']){
    const result=verdicts(complete().filter(row=>row.name!==name),baseline,adapters);
    assert.ok(Object.values(result.adapters).every(value=>value===false),name);
  }
});


test('P29 runtime acceptance rejects missing duplicate failed or unknown named rows and false verdicts',()=>{
  const rows=complete(),qualified=verdicts(rows,baseline,adapters);assert.doesNotThrow(()=>assertComplete(rows,qualified));
  for(const changed of [rows.slice(1),[...rows,rows[0]],rows.map((row,index)=>index===0?{...row,passed:false}:row),[...rows,{name:'Unknown case',passed:true}]])assert.throws(()=>assertComplete(changed,verdicts(changed,baseline,adapters)));
  for(const section of ['core','adapters','groups']){const changed=structuredClone(qualified);changed[section][Object.keys(changed[section])[0]]=false;assert.throws(()=>assertComplete(rows,changed));const missing=structuredClone(qualified);delete missing[section][Object.keys(missing[section])[0]];assert.throws(()=>assertComplete(rows,missing));}
  const changed=structuredClone(qualified);changed.groups[12]=true;assert.throws(()=>assertComplete(rows,changed));
});
