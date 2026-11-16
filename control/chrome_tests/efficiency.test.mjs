// Brief 28, group 16 without a browser: the efficiency fixtures as served, and
// the scripted tasks against a fake service, so each makes exactly its plan.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {fixtures} from '../chrome/ci/fixture.mjs';
import {efficiencyPage,f1Body,f2Cell,f2Header,f3Name,F2_ROWS,F2_COLUMNS,F3_UNIQUE,ADDRESS_MARK,ADDRESS_QUERY,ADDRESS_LINKS,addressOf,F4_FILLED,tabTitle,HOSTILE,H1_ROLES,H1_ELEMENTS,H1_NAME} from '../chrome/ci/efficiency-fixtures.mjs';
import {TASKS,OUTLINE_TASKS,efficiencyProbe,followsPlan,parseRows,EFFICIENCY_WARMUPS,EFFICIENCY_RUNS,EFFICIENCY_TAB_COUNT} from '../chrome/ci/efficiency-probe.mjs';

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

test('group 14 F6 and H1 pages as served, and H1 puts every hostile string in every place',()=>{
  for(const query of ['case=efficiency-f6','case=efficiency-f6&mode=child','case=efficiency-f6&mode=nested','case=efficiency-h1','case=efficiency-h1&mode=many','case=efficiency-h1&mode=name','case=efficiency-h1&title=99']){
    const {body,script}=efficiencyPage(new URL('http://fixture.test/?'+query));assert.ok(body,query);new vm.Script(script);assert.doesNotMatch(script,/<\/script|<!--/i,query);
  }
  assert.match(efficiencyPage(new URL('http://fixture.test/?case=efficiency-f6')).body,/src="http:\/\/second\.test:8766\/\?case=efficiency-f6&amp;mode=child"/);
  assert.equal(HOSTILE.length,14);assert.equal(H1_ROLES[2].length,10000);assert.equal(H1_ELEMENTS,100000);assert.equal(H1_NAME.length,100000);
  // H1's script against a minimal document: each string in each place, and the chosen title.
  const made=[],fake=tag=>{const node={tag,attributes:{},children:[],setAttribute(key,value){this.attributes[key]=value;},append(...items){this.children.push(...items);}};made.push(node);return node;};
  const main=fake('main'),document={title:'',querySelector:selector=>selector==='main'?main:null,createElement:fake,createTextNode:text=>({text})};
  vm.runInNewContext(efficiencyPage(new URL('http://fixture.test/?case=efficiency-h1&title=13')).script,{document});
  assert.equal(document.title,HOSTILE[13]);
  for(const text of HOSTILE){
    for(const tag of ['section','button'])assert.ok(made.some(node=>node.tag===tag&&node.attributes['aria-label']===text),tag);
    assert.ok(made.some(node=>node.tag==='textarea'&&node.defaultValue===text),'textarea');
    for(const tag of ['option','th','td','span','p'])assert.ok(made.some(node=>node.tag===tag&&node.textContent===text),tag);
  }
  assert.deepEqual(made.filter(node=>node.tag==='div').map(node=>node.attributes.role),H1_ROLES);
  assert.equal(main.children.length,HOSTILE.length+H1_ROLES.length);
});

test('a plan allows repeated cursor calls only where it says so',()=>{
  assert.ok(followsPlan(['read'],['read','read*']));assert.ok(followsPlan(['read','read','read'],['read','read*']));
  assert.ok(!followsPlan(['read','find'],['read','read*']));assert.ok(!followsPlan([],['read']));assert.ok(followsPlan(['find','read_form'],['find','find*','read_form','read_form*']));
  assert.deepEqual(parseRows('{"a":1}\n{"b":\n'+'tail"}\n{"c":2}').map(row=>Object.keys(row)[0]),['a','c']);
});

test('the address fixture carries one marker in every place a sign-in travels, beside an ordinary query',()=>{
  const url=new URL(addressOf());
  for(const name of ['code','access_token','sig','session','ref'])assert.equal(url.searchParams.get(name),ADDRESS_MARK,name);
  assert.equal(url.hash,'#access_token='+ADDRESS_MARK);assert.equal(ADDRESS_MARK.length,40);
  assert.deepEqual([url.searchParams.get('v'),url.searchParams.get('q'),url.searchParams.get('page')],['dQw4w9WgXcQ','red shoes','2']);
  const {body}=efficiencyPage(url),html=body.replaceAll('&amp;','&');
  assert.equal(ADDRESS_LINKS.length,6);
  for(const [name,href] of ADDRESS_LINKS){assert.ok(href.includes(ADDRESS_MARK),name);assert.ok(html.includes('<a href="'+href+'">'+name+'</a>'),name);}
  assert.ok(ADDRESS_LINKS.some(([,href])=>href.includes('name:'+ADDRESS_MARK+'@')),'a user name and password');
  assert.ok(ADDRESS_LINKS.some(([,href])=>href.includes('/reset/'+ADDRESS_MARK)),'a path segment after /reset/');
  assert.ok(html.includes('action="/receive?case=efficiency-address-form&session='+ADDRESS_MARK+'&'+ADDRESS_QUERY+'"'),'a form action');
  assert.ok(html.includes('<iframe title="Marker frame" src="/?case=efficiency-address&mode=frame&code='+ADDRESS_MARK+'&ref='+ADDRESS_MARK+'">'),'a frame address');
  assert.match(efficiencyPage(new URL('http://fixture.test/?case=efficiency-address&mode=frame')).body,/Address frame text/);
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
  // The new read (chrome_outline): one entry a tab, the outline's lines as text.
  const entry=(tab,outline,cursor=null)=>({tab,whose:'claude',characters:outline.length,total:outline.length,cursor,mid_line:false,typed_fields:0,
    untrusted_content:{url:page,title:'',scroll:'0/0',dialog:null,outline}});
  const reads=(...entries)=>({ok:true,data:{reads:entries,version_notice:null}});
  function outline(name,args){
    if(args.tabs)return reads(...args.tabs.map(tab=>entry(tab,'p "Tab '+tab+'"')));
    if(name==='f1'&&args.full)return reads(entry(1,args.cursor?'p "Paragraph 119"\ntextbox "Field 79" = "Synthetic value 79"':'p "Paragraph 0"\n',args.cursor?null:'c1'));
    if(name==='f1'&&args.ref)return reads(entry(1,Array.from({length:80},(_,index)=>'textbox "Field '+index+'" = "Synthetic value '+index+'" kqtvm'+(10+index)).join('\n')));
    if(name==='f1')return reads(entry(1,'p "Paragraph 0"\n… 115 more (48000 characters) kqtvm9\nform kqtvm1\n  textbox "Field 0" = "Synthetic value 0" kqtvm2'));
    if(name==='f2'&&args.ref)return reads(entry(1,Array.from({length:F2_ROWS},(_,row)=>Array.from({length:F2_COLUMNS},(_,column)=>'"'+f2Cell(row,column)+'"').join(' | ')).join('\n')));
    if(name==='f2')return reads(entry(1,'h1 "Stock"\ntable "Stock" kqtvm3\n  … 200 rows, 6 columns (14400 characters)'));
    if(name==='f3'&&args.find===F3_UNIQUE&&args.role==='link')return reads(entry(1,'link "'+F3_UNIQUE+'" → fixture.test kqtvm4'));
    throw Error('unexpected outline of '+name+' '+JSON.stringify(args));
  }
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
    if(action==='outline')return outline(name,args);
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
    const all=[...TASKS,...OUTLINE_TASKS];
    assert.equal(timings.length,all.length*(EFFICIENCY_WARMUPS+EFFICIENCY_RUNS));
    for(const task of all){
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
    // The read rows: old and new in every run, in that order, and the new read's first read uncounted.
    assert.deepEqual(timings.filter(timing=>timing.run===1).map(timing=>timing.task).filter(name=>name.endsWith('f1_first_read')),['f1_first_read','outline_f1_first_read']);
    assert.deepEqual(timings.find(timing=>timing.task==='outline_f1_everything').tools,['outline','outline']);
    for(const name of ['outline_f1_first_read','outline_f1_fields','outline_f2_table','outline_f3_find_link','outline_three_tabs'])
      assert.deepEqual(timings.find(timing=>timing.task===name).tools,['outline'],name);
    const fields=calls.find(call=>call.task==='outline_f1_fields');assert.equal(fields.arguments.ref,'kqtvm1','the form line\'s reference');
    const table=calls.find(call=>call.task==='outline_f2_table');assert.deepEqual([table.arguments.ref,table.arguments.max],['kqtvm3',40000]);
    // The same three tabs brief 20's row reads one by one (open_fact opens a tab in every run before them).
    const three=calls.filter(call=>call.task==='three_tabs'&&call.run===0).map(call=>call.arguments.tab);
    assert.equal(new Set(three).size,3);
    assert.deepEqual(calls.find(call=>call.task==='outline_three_tabs').arguments,{tabs:three});
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
