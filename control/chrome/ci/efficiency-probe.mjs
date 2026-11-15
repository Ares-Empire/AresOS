// Brief 28, group 16: the scripted efficiency tasks, run inside the latency
// harness (latency-pair.sh, EFFICIENCY_PROBE=true). This file holds the
// baseline's tasks: brief 20's tools, used as well as they allow. Each task
// makes exactly the calls listed in its `plan` (a `*` marks a call repeated
// with each cursor the tool returns) and no others; setup calls are not
// counted or timed. A row brief 20's tools can't finish ends in the one refusal
// its task expects, and the baseline records that. efficiency-summary.py turns
// the record into the numbers.
import fs from 'node:fs';
import os from 'node:os';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {setTimeout as delay} from 'node:timers/promises';
import {F2_ROWS,F2_COLUMNS,f2Cell,F3_UNIQUE,F4_FILLED,tabTitle} from './efficiency-fixtures.mjs';

export const EFFICIENCY_WARMUPS=1,EFFICIENCY_RUNS=5,EFFICIENCY_TAB_COUNT=25;
export const fixtureUrl=(name,query='')=>'http://fixture.test:8765/?case=efficiency-'+name+query;

// A view page is a window of the tree's text and may cut a line at either
// end, so rows are parsed from the pages joined so far.
export function parseRows(tree){
  const rows=[];
  for(const line of String(tree??'').split('\n')){if(!line.startsWith('{'))continue;try{rows.push(JSON.parse(line));}catch{}}
  return rows;
}
const named=(role,name)=>row=>row.expected?.role===role&&row.expected?.name===name;
const target=row=>({reference:row.reference,expected:row.expected});
// Follows a read, find or wait through its cursors until a wanted row appears.
async function pagedRow(call,action,args,want,tree=''){
  let cursor;
  do{
    const result=await call(action,{...args,...(cursor?{cursor}:{})});
    tree+=result.untrusted_content.tree;
    const row=parseRows(tree).find(want);if(row)return row;
    cursor=result.cursor;
  }while(cursor);
  throw Error(action+' returned no wanted row');
}

export const TASKS=[
  {name:'f1_first_read',row:'F1: the first read',plan:['read'],page:()=>fixtureUrl('f1'),
    async run({call,tab}){await call('read',{tab});}},
  {name:'f1_everything',row:'F1: everything, the read and each cursor it returns',plan:['read','read*'],page:()=>fixtureUrl('f1'),
    async run({call,tab}){
      let cursor,tree='';
      do{const result=await call('read',{tab,...(cursor?{cursor}:{})});tree+=result.untrusted_content.tree;cursor=result.cursor;}while(cursor);
      assert.match(tree,/Paragraph 119/);assert.match(tree,/Field 79/);
    }},
  {name:'f1_fields',row:'F1: the 80 fields with their values, after the first read',plan:['find','find*','read_form','read_form*'],page:()=>fixtureUrl('f1'),firstRead:true,
    async run({call,tab}){
      const field=await pagedRow(call,'find',{tab,text:'Field 0'},named('textbox','Field 0'));
      let form='',cursor;
      do{const result=await call('read_form',{tab,reference:field.reference,...(cursor?{cursor}:{})});form+=JSON.stringify(result.untrusted_content);cursor=result.cursor;}while(cursor);
      assert.match(form,/Synthetic value 0\b/);assert.match(form,/Synthetic value 79/);
    }},
  {name:'f2_table',row:'F2: the whole table, after the first read',plan:['read*'],page:()=>fixtureUrl('f2'),firstRead:true,
    async run({call,tab,first}){
      let cursor=first.cursor,tree=first.untrusted_content.tree;
      assert.ok(cursor,'F2 fits no single page of brief 20\'s read');
      while(cursor){const result=await call('read',{tab,cursor});tree+=result.untrusted_content.tree;cursor=result.cursor;}
      assert.ok(tree.includes(f2Cell(0,0))&&tree.includes(f2Cell(F2_ROWS-1,F2_COLUMNS-1)),'every cell read');
    }},
  {name:'f3_find_link',row:'F3: find the one link with the unique name',plan:['find','find*'],page:()=>fixtureUrl('f3'),
    async run({call,tab}){await pagedRow(call,'find',{tab,text:F3_UNIQUE},named('link',F3_UNIQUE));}},
  {name:'open_fact',row:'Open a fixture page and return one fact from it',plan:['open','wait'],
    async run({call,state}){
      const opened=await call('open',{url:fixtureUrl('f7','&page=1')});state.tab=opened.untrusted_content.tab;
      const page=await call('wait',{tab:state.tab,text:'Results page 1',timeout_ms:8000});assert.equal(page.condition_met,true);
    },
    async after({rpc,state}){if(state.tab!==undefined)assert.ok((await rpc('close_tab',{tab:state.tab,discard_unsaved:true})).ok);}},
  // Brief 20 can't send F4: Save's approval would carry the form's facts, the
  // 200 options of Country among them (14,380 bytes alone), over the 16,384
  // bytes an approval may hold (run 43698395453). Its tools, used as well as
  // they allow, end in that refusal; nothing is reserved and nothing received.
  {name:'f4_fill_send',row:'F4: fill 6 fields and send the form',plan:['read','fill_form','find','find*','click'],page:({run})=>fixtureUrl('f4','&id=r'+run),
    async run({call,tab}){
      const rows=parseRows((await call('read',{tab})).untrusted_content.tree);
      const fields=F4_FILLED.map((name,index)=>{const row=rows.find(named('textbox',name));assert.ok(row,name+' on the first page');return {...target(row),text:'Efficiency line '+index};});
      assert.equal((await call('fill_form',{fields})).remaining,0);
      const save=await pagedRow(call,'find',{tab,text:'Save'},named('button','Save'));
      await call('click',target(save),{refusal:'asking_input_too_large'});
    },
    async after({counts,run}){await delay(250);assert.equal(counts('efficiency-f4-r'+run),0,'F4 received nothing');}},
  {name:'f7_three_pages',row:'F7: three result pages, one click each, the titles collected',plan:['click','wait','click','wait','click','wait'],page:()=>fixtureUrl('f7','&page=1'),firstRead:true,
    async run({call,tab,first}){
      let next=parseRows(first.untrusted_content.tree).find(named('link','Next page'));const titles=[];
      for(const page of [2,3,4]){
        assert.ok(next,'Next page link');
        const clicked=await call('click',target(next));assert.ok(!clicked.approval,'a link click is free');
        const view=await call('wait',{tab,text:'Results page '+page,timeout_ms:8000});assert.equal(view.condition_met,true);
        titles.push(view.untrusted_content.title);next=parseRows(view.untrusted_content.tree).find(named('link','Next page'));
      }
      assert.deepEqual(titles,['Results page 2','Results page 3','Results page 4']);
    }},
  {name:'f5_free_click',row:'F5: a free click that changes part of the page',plan:['click','read'],page:()=>fixtureUrl('f5'),firstRead:true,
    async run({call,tab,first}){
      const refresh=parseRows(first.untrusted_content.tree).find(named('button','Refresh rows'));assert.ok(refresh,'Refresh rows');
      const clicked=await call('click',target(refresh));assert.ok(!clicked.approval&&!clicked.followups?.length,'a free click');
      assert.match((await call('read',{tab})).untrusted_content.tree,/refreshed item 4/);
    }},
  {name:'three_tabs',row:'Compare three open tabs (F1, F2, F3)',plan:['read','read','read'],phase:'tabs',
    async run({call,tabs}){for(const tab of tabs.slice(0,3))await call('read',{tab});}},
  {name:'list_25_tabs',row:'List 25 open tabs (titles of about 30 characters)',plan:['tabs','tabs*'],phase:'many',
    async run({call}){
      let cursor,count=0;
      do{const result=await call('tabs',{limit:10,...(cursor?{cursor}:{})});count+=result.items.length;cursor=result.cursor;}while(cursor);
      assert.equal(count,EFFICIENCY_TAB_COUNT);
    }},
];

// Checks a recorded call sequence against a plan; `x*` matches zero or more x.
export function followsPlan(tools,plan){
  let index=0;
  for(const step of plan){
    if(step.endsWith('*')){while(tools[index]===step.slice(0,-1))index++;continue;}
    if(tools[index]!==step)return false;index++;
  }
  return index===tools.length;
}

export async function efficiencyProbe({rpc,eventually,counts,getTab,out='/out'}){
  const record=fs.openSync(out+'/efficiency-calls.jsonl','a'),timing=fs.openSync(out+'/efficiency-tasks.jsonl','a');
  const tab=getTab();
  async function open(url){
    const result=await rpc('open',{url});assert.ok(result.ok,JSON.stringify(result));
    const opened=result.data.untrusted_content.tab;await loaded(opened,url);return opened;
  }
  async function loaded(tabId,url){
    await eventually(async()=>{const page=await rpc('read',{tab:tabId});return page.ok&&page.data.untrusted_content.url===url&&page.data.characters>0;},'efficiency fixture committed');
    await delay(250);
  }
  async function nav(url){const result=await rpc('navigate',{tab,url,discard_unsaved:true});assert.ok(result.ok,JSON.stringify(result));await loaded(tab,url);}
  async function perform(task,run,context){
    const tools=[];let index=0;
    // `refusal` is the one error code a call must end in; any other outcome,
    // success included, fails the task.
    const call=async(action,args={},{refusal}={})=>{
      const result=await rpc(action,args);
      const refused=refusal!==undefined&&!result.ok&&result.error?.code===refusal;
      fs.writeSync(record,JSON.stringify({task:task.name,run,warmup:run<EFFICIENCY_WARMUPS,index:index++,action:'chrome_'+action,arguments:args,result,...(refused?{expected_refusal:refusal}:{})})+'\n');
      tools.push(action);
      if(refusal!==undefined){assert.ok(refused,task.name+' '+action+' should be refused with '+refusal+': '+JSON.stringify(result.ok?'it succeeded':result.error));return result.error;}
      assert.ok(result.ok,task.name+' '+action+': '+JSON.stringify(result.error));return result.data;
    };
    const state={};
    const started=performance.now();
    let failed=true;
    try{await task.run({...context,call,state});failed=false;}
    finally{
      const milliseconds=performance.now()-started;
      fs.writeSync(timing,JSON.stringify({task:task.name,row:task.row,plan:task.plan,run,warmup:run<EFFICIENCY_WARMUPS,milliseconds,tools})+'\n');
      // `after` cleans up after a failed run too, but never hides why it failed
      // (run 43698395453 reported F4's receiver, not the click's refusal).
      if(task.after){try{await task.after({rpc,eventually,counts,run,state});}catch(error){if(!failed)throw error;console.error(task.name+' run '+run+', after the failure below: '+error.message);}}
    }
    assert.ok(followsPlan(tools,task.plan),task.name+' made '+tools.join(',')+' against its plan '+task.plan.join(','));
  }
  async function rounds(tasks,context){
    for(let run=0;run<EFFICIENCY_WARMUPS+EFFICIENCY_RUNS;run++)for(const task of tasks){
      let first=null;
      if(task.page){await nav(task.page({run}));if(task.firstRead){const result=await rpc('read',{tab});assert.ok(result.ok);first=result.data;}}
      await perform(task,run,{...context,tab,first});
    }
  }
  try{
    fs.writeFileSync(out+'/efficiency-runner.json',JSON.stringify({
      runner:{image_os:process.env.ImageOS||null,image_version:process.env.ImageVersion||null,environment:process.env.RUNNER_ENVIRONMENT||null,arch:process.env.RUNNER_ARCH||null},
      cpu:os.cpus()[0]?.model||null,cpus:os.cpus().length,memory_bytes:os.totalmem(),node:process.version,
      chrome:fs.existsSync(out+'/chrome-version.txt')?fs.readFileSync(out+'/chrome-version.txt','utf8').trim():null,
      run_id:process.env.GITHUB_RUN_ID||null,sha:process.env.GITHUB_SHA||null},null,2));
    await rounds(TASKS.filter(task=>!task.phase),{});
    // Three tabs show F1, F2 and F3, then more tabs until 25 are open in all.
    const tabs=[];for(const name of ['f1','f2','f3'])tabs.push(await open(fixtureUrl(name)));
    await rounds(TASKS.filter(task=>task.phase==='tabs'),{tabs});
    const listed=async()=>{let cursor,count=0;do{const result=await rpc('tabs',{limit:10,...(cursor?{cursor}:{})});assert.ok(result.ok);count+=result.data.items.length;cursor=result.data.cursor;}while(cursor);return count;};
    for(let id=1,count=await listed();count<EFFICIENCY_TAB_COUNT;id++,count++)await open(fixtureUrl('tab','&id='+id));
    assert.equal(await listed(),EFFICIENCY_TAB_COUNT);assert.ok(tabTitle(1).length>=28&&tabTitle(1).length<=32);
    await rounds(TASKS.filter(task=>task.phase==='many'),{tabs});
    console.log('Efficiency probe complete:',TASKS.length,'tasks,',EFFICIENCY_WARMUPS,'warm-up and',EFFICIENCY_RUNS,'measured runs each');
  }finally{fs.closeSync(record);fs.closeSync(timing);}
}
