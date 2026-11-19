import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {REQUIRED,ADAPTER_REQUIRED,SUPPORT,verdicts,assertComplete} from '../chrome/ci/verdicts.mjs';

const support=['FEATURE tools forms options find wait fill_form scroll and full catalogues','VIEW representative long article/form complete paging','QUALIFICATION conservative activations ask and core failures gate before reads',
  'READ BRIEF28 a service restart refuses old references after the new counter passes them','READ BRIEF28 Chrome restart and extension reconnect each refuse every old reference without reissuing strings',
  'READ BRIEF28 more than 5000 elements drop an old reference and never issue its string again','READ BRIEF28 release and retake refuse an old reference with the same document and element id',
  'READ BRIEF28 two tabs of one page share no reference and find with role returns its one link','READ BRIEF28 paging joins whole and a cursor keeps its query','READ BRIEF28 typing moves the state token and until meets a value',
  'READ BRIEF28 frames of a second site and shadow roots are read','READ BRIEF28 addresses hold no sign-in and show an ordinary query',
  'READ BRIEF28 100000 characters by ref advance at max 1000 without splitting escapes',
  'READ BRIEF28 a wide table row is returned whole across pages',
  'READ BRIEF28 a 20000 character value is returned in full across pages',
  'READ BRIEF28 non ASCII and quote pages fit with a pending operation and the notice',
  'READ BRIEF28 five tabs each keep their byte share and continue with their own cursor',
  'READ BRIEF28 a change inside a frame moves the state token',
  'READ BRIEF28 an unchanged page keeps its state token over 100 polls',
  'READ BRIEF28 until meets text on a page that never goes quiet',
  'READ BRIEF28 H1 hostile roles stay on the fixed role list',
  'READ BRIEF28 H1 names values options tables forms paths stale lines titles and dialogs stay quoted',
  'READ BRIEF28 H1 a 100000 character name is cut once and read whole by ref',
  'READ BRIEF28 H1 100000 elements report the 20000 node cap',
  'READ BRIEF28 small fixture outlines match the stored green browser results character for character',
  'READ BRIEF28 taken typed fields stay unread until exact one call approval and credentials stay excluded',
  'READ BRIEF28 a field added after the asking question reasks without reading',
  'READ BRIEF28 a same label replacement refuses the asking read before values',
  'READ BRIEF28 a changed field label refuses the asking read before values',
  'READ BRIEF28 swapping duplicate labelled fields refuses the asking read before values',
  'READ BRIEF28 swapping unlabelled fields refuses the asking read before values',
  'READ BRIEF28 a listed frame navigation refuses the asking read before values',
  'READ BRIEF28 a listed field made password refuses the asking read before values',
  'READ BRIEF28 a listed field masked refuses the asking read before values',
  'READ BRIEF28 altered asking questions and field lists read no value',
  'ACT BRIEF28A the steps as defined give every outcome and a list failing at its third step keeps its two operations',
  'ACT BRIEF28A nothing unseen is overwritten and a fill then Enter on the same field runs without a read',
  'ACT BRIEF28A the look between steps stops at a held page submission a dialog and a new document',
  'ACT BRIEF28A a form too large to ask about is refused with its advice and its page submission stays stopped',
  'ACT BRIEF28A steps land far below the fold and in a scrolled box and a scroll handler submission is asked',
  'ACT BRIEF28A the fingerprint refuses a changed element with its present line and keeps unchanged ones acting',
  'ACT BRIEF28A hostile text stays quoted in a change report and in a stale present line',
  'ACT BRIEF28A loaded holds for a fragment and a single page back without a new document and a reload waits for its document',
  'ACT BRIEF28A the read-only site refuses every acting step and still allows wait and scrolling',
  'ACT BRIEF28A addresses hold no sign-in in any result question stage notice or log line and the full address still reaches the page',
  'ACT BRIEF28A staged waits carry a list across the cut-off through the proxy and no input is dispatched after 12 seconds',
  'ACT BRIEF28A twenty fills through the command end by their deadline and the fixture counts exactly the fills that ran',
  'ACT BRIEF28A a caller killed during a list leaves no later input and the next call works',
  'ACT BRIEF28A chrome_tabs marks a tab that plays sound',
  'ACT BRIEF28A closing takes one tab per flag and a taken tab stays his',
  'ACT BRIEF28A a tab list binds his tab and a tab moved on or an old list is refused while the listed address still opens',
  'ACT BRIEF28A the asking read on the new list shows typed fields unread and returns exactly the approved fields whose refs stay unread',
  'ACT BRIEF28A a popup a step opened is named in its step',
  'ACT BRIEF28A a reference from another tab and references and lists from before a restart are refused for an action'];
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
  const names=['control/chrome/ci/matrices.mjs','control/chrome/ci/destination-matrix.mjs','control/chrome/ci/late-reader-matrix.mjs','control/chrome/ci/late-binding-matrix.mjs','control/chrome/ci/animated-default-matrix.mjs','control/chrome/ci/outline-read.mjs','control/chrome/ci/outline-asking.mjs','control/chrome/ci/unread-matrix.mjs','control/chrome/ci/review-matrices.mjs','control/chrome/ci/recheck2-matrices.mjs','control/chrome/ci/recheck3-matrices.mjs','control/chrome/ci/popups.mjs','control/chrome/ci/act-matrix.mjs','control/chrome/ci/sites/matrices.mjs'].flatMap(file=>
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
  const rows=complete();assert.throws(()=>assertComplete(rows,verdicts(rows,baseline,adapters)),'native group 12 is required');
  const native={cases:[false,true].flatMap(skip=>['missing','matching','revoked','other-account','positive'].map(mode=>({case:'chrome-'+(skip?'skip-':'normal-')+mode,mode:skip?'bypassPermissions':'default',owner_entry:mode,arrivals:{tabs:1,submit:Number(mode==='positive'),typed:Number(mode==='positive'),trusted:Number(mode==='matching')},receiver_delta_sha256:'a'.repeat(64)})))};
  const qualified=verdicts(rows,baseline,adapters,native);
  assert.doesNotThrow(()=>assertComplete(rows,qualified));
  for(const changed of [rows.slice(1),[...rows,rows[0]],rows.map((row,index)=>index===0?{...row,passed:false}:row),[...rows,{name:'Unknown case',passed:true}]])assert.throws(()=>assertComplete(changed,verdicts(changed,baseline,adapters)));
  for(const section of ['core','adapters','groups']){const changed=structuredClone(qualified);changed[section][Object.keys(changed[section])[0]]=false;assert.throws(()=>assertComplete(rows,changed));const missing=structuredClone(qualified);delete missing[section][Object.keys(missing[section])[0]];assert.throws(()=>assertComplete(rows,missing));}
  const changed=structuredClone(qualified);changed.groups[12]=false;assert.throws(()=>assertComplete(rows,changed));
});
