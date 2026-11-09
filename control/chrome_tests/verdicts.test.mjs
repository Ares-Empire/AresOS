import test from 'node:test';
import assert from 'node:assert/strict';
import {REQUIRED,verdicts} from '../chrome/ci/verdicts.mjs';

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
