// Brief 28, group 16 without a browser: the efficiency fixtures as served, and
// the scripted tasks against a fake service, so each makes exactly its plan.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {efficiencyPage,f1Body,f2Cell,f2Header,f3Name,F3_UNIQUE,F4_FILLED,tabTitle} from '../chrome/ci/efficiency-fixtures.mjs';
import {TASKS,efficiencyProbe,followsPlan,parseRows,EFFICIENCY_WARMUPS,EFFICIENCY_RUNS,EFFICIENCY_TAB_COUNT} from '../chrome/ci/efficiency-probe.mjs';

const served=async(base,query)=>{const response=await fetch(base+'/?'+query);return {status:response.status,html:await response.text()};};
const bodyOf=html=>html.slice(html.indexOf('<body>')+6,html.lastIndexOf('<script>'));
const count=(text,pattern)=>(text.match(pattern)||[]).length;

test('F1 is brief 20\'s long page, as the matrix mode "long" serves it',async()=>{
  const fixture=await fixtures({port:0,secondPort:0});const base='http://127.0.0.1:'+fixture.port;
  try{
    const long=await served(base,'case=matrix&id=long&mode=long'),f1=await served(base,'case=efficiency-f1');
    assert.equal(f1.status,200);assert.equal(bodyOf(f1.html),bodyOf(long.html));assert.equal(bodyOf(f1.html),f1Body());
    assert.equal(count(f1.html,/<p>Paragraph /g),120);assert.equal(count(f1.html,/<input name="field/g),80);
    assert.equal((await served(base,'case=efficiency-unknown')).status,404);
  }finally{fixture.close();}
});

test('F2 holds 200 rows of 6 cells of 12 letters and digits under a header, and the small table',()=>{
  const {body,script}=efficiencyPage(new URL('http://fixture.test/?case=efficiency-f2'));
  const cells=[...body.matchAll(/<td>([^<]*)<\/td>/g)].map(match=>match[1]).filter(text=>/^r\d{3}c\d/.test(text));
  assert.equal(cells.length,1200);assert.ok(cells.every(cell=>/^[a-z0-9]{12}$/.test(cell)));assert.equal(new Set(cells).size,1200);
  assert.equal(cells[0],f2Cell(0,0));assert.equal(cells.at(-1),f2Cell(199,5));
  assert.equal(count(body,/<th>/g),6);assert.ok([0,5].every(column=>f2Header(column).length===12&&body.includes('<th>'+f2Header(column)+'</th>')));
  assert.match(body,/<table aria-label="Stock">/);assert.equal(count(body,/<a href="\/order\/\d">Open<\/a>/g),3);assert.equal(count(body,/type="checkbox" aria-label="Select order \d"/g),3);
  new vm.Script(script);
});

test('F3 lists 300 links between navigation and footer, one name contained in no other',()=>{
  const {body}=efficiencyPage(new URL('http://fixture.test/?case=efficiency-f3'));
  const names=[...body.matchAll(/<li><a href="\/result\/\d+">([^<]*)<\/a><\/li>/g)].map(match=>match[1]);
  assert.equal(names.length,300);assert.equal(names.filter(name=>name.includes(F3_UNIQUE)).length,1);assert.equal(names[217],F3_UNIQUE);
  assert.ok(names.every((name,index)=>name===f3Name(index)));
  const all=[...body.matchAll(/<a href="[^"]*">([^<]*)<\/a>/g)].map(match=>match[1]);
  assert.equal(all.length,311);assert.equal(all.filter(name=>name.toLowerCase().includes(F3_UNIQUE.toLowerCase())).length,1);
  assert.match(body,/^<nav aria-label="Site">/);assert.match(body,/<footer>(<a [^>]*>Footer \d<\/a>){5}<\/footer>$/);
});

test('F4 is a form of 25 fields that posts to the receiver under its run id; F5, F7 and the tab pages compile',()=>{
  const {body}=efficiencyPage(new URL('http://fixture.test/?case=efficiency-f4&id=r3'));
  assert.match(body,/<form aria-label="Account" method="post" novalidate action="\/receive\?case=efficiency-f4-r3">/);
  assert.equal(count(body,/<input /g)+count(body,/<select /g),29);assert.equal(count(body,/type="hidden"/g),3);
  assert.equal(count(body,/<option value="c\d+"/g),200);assert.ok(F4_FILLED.every(name=>body.includes('<label>'+name+' <input ')));
  assert.match(body,/type="password"/);assert.match(body,/autocomplete="one-time-code"/);assert.match(body,/<button type="submit">Save<\/button><\/form>$/);
  for(const query of ['case=efficiency-f5','case=efficiency-f5&mode=load','case=efficiency-f5&mode=loaded','case=efficiency-f7&page=3','case=efficiency-tab&id=7'])
    new vm.Script(efficiencyPage(new URL('http://fixture.test/?'+query)).script);
  assert.match(efficiencyPage(new URL('http://fixture.test/?case=efficiency-f7&page=3')).body,/<h1>Results page 3<\/h1>.*href="\/\?case=efficiency-f7&amp;page=4">Next page</);
  assert.ok(tabTitle(25).length>=28&&tabTitle(25).length<=32);
});

test('a plan allows repeated cursor calls only where it says so',()=>{
  assert.ok(followsPlan(['read'],['read','read*']));assert.ok(followsPlan(['read','read','read'],['read','read*']));
  assert.ok(!followsPlan(['read','find'],['read','read*']));assert.ok(!followsPlan([],['read']));assert.ok(followsPlan(['find','read_form'],['find','find*','read_form','read_form*']));
  assert.deepEqual(parseRows('{"a":1}\n{"b":\n'+'tail"}\n{"c":2}').map(row=>Object.keys(row)[0]),['a','c']);
});

// A fake service: just enough of brief 20's results for every task to run.
// Brief 20 refuses F4's Save (its approval would be over 16,384 bytes).
// F2's first page comes from the setup's load check, the second from the first
// read; the task then follows two cursors.
function fakeService(){
  const calls=[];let tabs=1,nextTab=10,page='';
  const row=(role,name,extra={})=>JSON.stringify({reference:{element:role+':'+name},expected:{role,name},text:name,...extra});
  const trees={
    f1:[row('p','Paragraph 0'),row('textbox','Field 0'),'Paragraph 119 Field 79'].join('\n'),
    f2:[row('cell',f2Cell(0,0))].join('\n'),
    f3:[row('link',F3_UNIQUE)].join('\n'),
    f4:F4_FILLED.map(name=>row('textbox',name)).concat(row('button','Save')).join('\n'),
    f5:[row('button','Refresh rows')].join('\n'),
    f7:[row('heading','Results page 1'),row('link','Next page')].join('\n'),
  };
  const view=(tree,extra={})=>({ok:true,data:{untrusted_content:{url:page,title:'',tree},characters:tree.length,cursor:null,...extra}});
  let f2Page=0,f7=1,f5Clicked=false;
  async function rpc(action,args={}){
    calls.push(action);
    const name=(page.match(/efficiency-(\w+)/)||[])[1];
    if(action==='navigate'){page=args.url;f2Page=0;f5Clicked=false;f7=Number(new URL(args.url).searchParams.get('page')||1);return {ok:true,data:{}};}
    if(action==='open'){tabs++;page=args.url;return {ok:true,data:{untrusted_content:{tab:nextTab++}}};}
    if(action==='close_tab'){tabs--;return {ok:true,data:{}};}
    if(action==='tabs'){const offset=Number(args.cursor||0),items=Array.from({length:Math.min(10,tabs-offset)},(_,index)=>({tab:offset+index}));return {ok:true,data:{items,total:tabs,cursor:offset+10<tabs?String(offset+10):null}};}
    if(action==='read'&&name==='f2'){f2Page++;return f2Page<4?view(trees.f2,{cursor:'c'+f2Page}):view(f2Cell(199,5));}
    if(action==='read'&&name==='f5'&&f5Clicked)return view('refreshed item 4');
    if(action==='read'||action==='find')return view(name==='f7'?trees.f7.replace('page 1','page '+f7):trees[name]||'');
    if(action==='read_form')return {ok:true,data:{untrusted_content:{form:'Synthetic value 0 Synthetic value 79'},cursor:null}};
    if(action==='fill_form')return {ok:true,data:{completed:args.fields,remaining:0}};
    if(action==='click'&&name==='f4')return {ok:false,error:{code:'asking_input_too_large',message:'The whole approval exceeds 16384 bytes; prepare a smaller operation. Nothing was reserved.'}};
    if(action==='click'&&name==='f7'){f7++;page=page.replace(/page=\d+/,'page='+f7);return {ok:true,data:{followups:[]}};}
    if(action==='click'){f5Clicked=name==='f5';return {ok:true,data:{followups:[]}};}
    if(action==='wait')return {ok:true,data:{...view(trees.f7.replace('page 1','page '+f7)).data,untrusted_content:{url:page,title:'Results page '+f7,tree:trees.f7.replace('page 1','page '+f7)},condition_met:true}};
    throw Error('unexpected '+action);
  }
  return {rpc,calls,tabCount:()=>tabs};
}

// The fake reads every page at once, so `loaded` must see the address.
const probeRpc=(service,change=()=>null)=>async(action,args)=>{
  const changed=change(action,args);if(changed)return changed;
  const result=await service.rpc(action,args);if(action==='read'&&result.data?.untrusted_content&&!result.data.characters)result.data.characters=1;return result;
};
const probeOptions=(rpc,out,counts=()=>0)=>({rpc,eventually:async fn=>{assert.ok(await fn());},counts,getTab:()=>1,out});

test('every task makes exactly the calls of its plan, recorded and timed, and the tabs reach 25',async()=>{
  const out=fs.mkdtempSync(path.join(os.tmpdir(),'pkg28-efficiency-'));
  try{
    const service=fakeService();
    await efficiencyProbe(probeOptions(probeRpc(service),out));
    const timings=fs.readFileSync(out+'/efficiency-tasks.jsonl','utf8').trim().split('\n').map(line=>JSON.parse(line));
    const calls=fs.readFileSync(out+'/efficiency-calls.jsonl','utf8').trim().split('\n').map(line=>JSON.parse(line));
    assert.equal(timings.length,TASKS.length*(EFFICIENCY_WARMUPS+EFFICIENCY_RUNS));
    for(const task of TASKS){
      const runs=timings.filter(timing=>timing.task===task.name);
      assert.equal(runs.filter(run=>run.warmup).length,EFFICIENCY_WARMUPS);assert.equal(runs.filter(run=>!run.warmup).length,EFFICIENCY_RUNS);
      for(const run of runs){
        assert.ok(followsPlan(run.tools,task.plan),task.name+': '+run.tools);
        assert.deepEqual(calls.filter(call=>call.task===task.name&&call.run===run.run).map(call=>call.action),run.tools.map(tool=>'chrome_'+tool));
      }
    }
    assert.deepEqual(timings.find(timing=>timing.task==='f2_table').tools,['read','read']);
    assert.deepEqual(timings.find(timing=>timing.task==='f4_fill_send').tools,['read','fill_form','find','click']);
    const f4=calls.filter(call=>call.task==='f4_fill_send');
    assert.ok(f4.filter(call=>call.action==='chrome_click').every(call=>call.expected_refusal==='asking_input_too_large'));
    assert.ok(calls.every(call=>call.result.ok||call.expected_refusal===call.result.error.code),'only the expected refusal fails');
    assert.deepEqual(timings.find(timing=>timing.task==='list_25_tabs').tools,['tabs','tabs','tabs']);
    assert.equal(service.tabCount(),EFFICIENCY_TAB_COUNT);
    assert.ok(JSON.parse(fs.readFileSync(out+'/efficiency-runner.json','utf8')).cpus>0);
  }finally{fs.rmSync(out,{recursive:true,force:true});}
});

test('F4 fails when brief 20 sends it, and a failed run is reported over its after check',async()=>{
  for(const [change,counts,message] of [
    // Run 43698395453: the click was refused, and the receiver check in `after` hid that.
    [(action)=>action==='fill_form'?{ok:false,error:{code:'stale_reference'}}:null,()=>1,/f4_fill_send fill_form: \{"code":"stale_reference"\}/],
    [(action,args)=>action==='click'&&args.expected?.name==='Save'?{ok:true,data:{approval:{operation_id:'op'}}}:null,()=>0,/f4_fill_send click should be refused with asking_input_too_large: "it succeeded"/],
    [()=>null,()=>1,/F4 received nothing/],
  ]){
    const out=fs.mkdtempSync(path.join(os.tmpdir(),'pkg28-efficiency-'));
    try{await assert.rejects(efficiencyProbe(probeOptions(probeRpc(fakeService(),change),out,counts)),message);}
    finally{fs.rmSync(out,{recursive:true,force:true});}
  }
});

test('the committed baseline holds every task with its plan, and only F4 ends in a refusal',()=>{
  const baseline=JSON.parse(fs.readFileSync(new URL('../chrome/ci/efficiency-baseline.json',import.meta.url),'utf8'));
  assert.deepEqual(Object.keys(baseline.tasks),TASKS.map(task=>task.name));
  for(const task of TASKS){
    const row=baseline.tasks[task.name];
    assert.equal(row.row,task.row);assert.deepEqual(row.plan,task.plan);
    assert.ok(followsPlan(row.tools.map(tool=>tool.replace(/^chrome_/,'')),task.plan),task.name);
    assert.equal(row.outcome,task.name==='f4_fill_send'?'refused':'done');
  }
  assert.deepEqual(baseline.tasks.f4_fill_send.refusals,[{action:'chrome_click',code:'asking_input_too_large'}]);
  assert.equal(baseline.measured_runs,EFFICIENCY_RUNS);
});
