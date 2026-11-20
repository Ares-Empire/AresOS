// Brief 28, group 16: the scripted efficiency tasks, run inside the latency
// harness (latency-pair.sh, EFFICIENCY_PROBE=true). This file holds the
// baseline's tasks: brief 20's tools, used as well as they allow. Each task
// makes exactly the calls listed in its `plan` (a `*` marks a call repeated
// with each cursor the tool returns) and no others; setup calls are not
// counted or timed. A row brief 20's tools can't finish ends in the one refusal
// its task expects, and the baseline records that. efficiency-summary.py turns
// the record into the numbers. OUTLINE_TASKS are the second half, the read rows
// with the new read; each run makes both, so old and new are timed in one run.
// Brief 28a (item 8, step 1d) adds ACT_TASKS, group 16's acting rows with the
// new tools, and LATENCY_TASKS, the side-by-side timing of F4's six fills and
// Save up to the question with brief 20's tools and with chrome_do. The record
// names each call by the tool the service ran (chrome_old_<verb> for brief 20's
// tools under the CI-only switch, chrome_read for the new read).
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
    async after({rpc,state}){await closeTab(rpc,state.tab);}},
  // Brief 20 can't send F4: Save's approval would carry the form's facts, the
  // 200 options of Country among them (14,380 bytes alone), over the 16,384
  // bytes an approval may hold (run 43698395453). Its tools, used as well as
  // they allow, end in that refusal; nothing is reserved and nothing received.
  // Retired from the runs at brief 28a's step 1d (item 3a): brief 20's click on Save
  // now goes through the same prepare and is asked, so it can't end in the refusal the
  // frozen baseline records. The task stays as the baseline's definition; the side-by-side
  // timing of the same work is LATENCY_TASKS' f4_old_to_question.
  {name:'f4_fill_send',row:'F4: fill 6 fields and send the form',plan:['read','fill_form','find','find*','click'],retired:true,page:({run})=>fixtureUrl('f4','&id=r'+run),
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

// Group 16's read rows: the new read, chrome_read (its verb `outline` here is the
// harness's: browser.mjs sends it to chrome_read since brief 28a's switch), with
// the rows and the exact calls of the brief's table. The row names the baseline
// task of the same row; efficiency-summary.py holds the budgets and fails the
// step when a row misses its budget or the baseline.
const REFERENCE=/ ([bcdfghjklmnpqrstvwxyz]{5}\d+)$/;
// The reference on the first outline line that starts with these words.
function lineRef(outline,start){
  const line=outline.split('\n').find(line=>line.trimStart().startsWith(start));assert.ok(line,'a line starting with '+start);
  const found=line.match(REFERENCE);assert.ok(found,line);return found[1];
}
const readOf=entry=>{assert.ok(entry&&!entry.error,JSON.stringify(entry?.error));return entry;};
export const OUTLINE_TASKS=[
  {name:'outline_f1_first_read',row:'F1: the first read',plan:['outline'],page:()=>fixtureUrl('f1'),
    async run({call,tab}){const entry=readOf((await call('outline',{tab})).reads[0]);assert.equal(entry.cursor,null,'the whole outline in one call');}},
  {name:'outline_f1_everything',row:'F1: everything, the read and each cursor it returns',plan:['outline','outline*'],page:()=>fixtureUrl('f1'),
    async run({call,tab}){
      let cursor,text='';
      do{const entry=readOf((await call('outline',{tab,full:true,max:40000,...(cursor?{cursor}:{})})).reads[0]);text+=entry.untrusted_content.outline;cursor=entry.cursor;}while(cursor);
      assert.match(text,/Paragraph 119/);assert.match(text,/Synthetic value 79/);assert.doesNotMatch(text,/… \d+ more/,'full folds nothing');
    }},
  {name:'outline_f1_fields',row:'F1: the 80 fields with their values, after the first read',plan:['outline'],page:()=>fixtureUrl('f1'),firstOutline:true,
    async run({call,tab,first}){
      const entry=readOf((await call('outline',{tab,ref:lineRef(first.reads[0].untrusted_content.outline,'form')})).reads[0]);
      assert.equal(entry.cursor,null);assert.equal(entry.untrusted_content.outline.match(/Synthetic value \d+/g)?.length,80);
    }},
  {name:'outline_f2_table',row:'F2: the whole table, after the first read',plan:['outline'],page:()=>fixtureUrl('f2'),firstOutline:true,
    async run({call,tab,first}){
      const entry=readOf((await call('outline',{tab,ref:lineRef(first.reads[0].untrusted_content.outline,'table "Stock"'),max:40000})).reads[0]);
      assert.equal(entry.cursor,null);const text=entry.untrusted_content.outline;
      for(let row=0;row<F2_ROWS;row++)for(let column=0;column<F2_COLUMNS;column++)assert.ok(text.includes('"'+f2Cell(row,column)+'"'),f2Cell(row,column));
    }},
  {name:'outline_f3_find_link',row:'F3: find the one link with the unique name',plan:['outline'],page:()=>fixtureUrl('f3'),
    async run({call,tab}){const entry=readOf((await call('outline',{tab,find:F3_UNIQUE,role:'link'})).reads[0]);assert.ok(entry.untrusted_content.outline.includes('link "'+F3_UNIQUE+'"'),entry.untrusted_content.outline);}},
  {name:'outline_three_tabs',row:'Compare three open tabs (F1, F2, F3)',plan:['outline'],phase:'tabs',
    async run({call,tabs}){const result=await call('outline',{tabs:tabs.slice(0,3)});assert.deepEqual(result.reads.map(entry=>readOf(entry).tab),tabs.slice(0,3));}},
];

// Bytes of an approval as the service counts them (common.canonical: sorted keys,
// no spaces, ASCII escapes), for F4's 9,000-byte row.
const sortedKeys=value=>Array.isArray(value)?value.map(sortedKeys):value&&typeof value==='object'?
  Object.fromEntries(Object.keys(value).sort().map(key=>[key,sortedKeys(value[key])])):value;
export const canonicalBytes=value=>Buffer.byteLength(JSON.stringify(sortedKeys(value)).replace(/[\u0080-\uffff]/g,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0')));
const outlineOf=result=>{const text=result?.untrusted_content?.outline;assert.ok(typeof text==='string'&&text,'an outline: '+JSON.stringify(result?.error||result?.untrusted_content));return text;};
const outcomes=result=>result.steps.map(step=>step.outcome);
// Six fills on F4's lines and the click on Save, by the references of an outline.
const f4Steps=(outline,text)=>[...F4_FILLED.map((name,index)=>({do:'fill',ref:lineRef(outline,'textbox "'+name+'"'),text:text+' '+index})),
  {do:'click',ref:lineRef(outline,'button "Save"')}];
// Work a task prepared and didn't send is dropped, untimed, so no later result carries it as pending.
async function dropPrepared(rpc,approval){
  if(!approval?.operation_id)return;
  const dropped=await rpc('chrome_drop',{operation_id:approval.operation_id});assert.ok(dropped.ok,JSON.stringify(dropped.error));
  await rpc('chrome_notice_ack',{operation_id:approval.operation_id});
}
async function closeTab(rpc,tab){
  if(tab===undefined)return;
  const result=await rpc('chrome_close',{tabs:[tab],discard_unsaved:true});
  assert.ok(result.ok,'close tab '+tab);
  assert.deepEqual(result.data.closed.map(item=>item.tab),[tab]);
}

// Group 16's acting rows (brief 28a): each with the new tools and exactly the calls of its row. The
// row names its baseline task; efficiency-summary.py (ACT_ROWS) holds the budgets.
export const ACT_TASKS=[
  {name:'act_open_fact',row:'Open a fixture page and return one fact from it',plan:['chrome_open'],
    async run({call,state}){
      const opened=await call('chrome_open',{url:fixtureUrl('f7','&page=1')});state.tab=opened.tab;
      assert.match(outlineOf(opened),/h1 "Results page 1"/,'the fact is in the one result');
    },
    async after({rpc,state}){await closeTab(rpc,state.tab);}},
  {name:'act_f4_fill_send',row:'F4: fill 6 fields and send the form',plan:['chrome_open','do','submit'],
    async run({call,state,run,counts}){
      state.id='act-'+run;
      const opened=await call('chrome_open',{url:fixtureUrl('f4','&id='+state.id)});state.tab=opened.tab;
      const done=await call('do',{tab:opened.tab,steps:f4Steps(outlineOf(opened),'Efficiency line')});
      assert.deepEqual(outcomes(done),[...F4_FILLED.map(()=>'done'),'prepared'],JSON.stringify(done.steps));
      assert.equal(done.prepared.length,1,'one question');
      const approval=done.prepared[0].approval;state.measures={approval_bytes:canonicalBytes(approval)};
      assert.equal(counts('efficiency-f4-'+state.id),0,'nothing before chrome_submit');
      const sent=await call('submit',approval);assert.equal(sent.operation.state,'done',JSON.stringify(sent.operation));
    },
    async after({rpc,counts,eventually,state}){
      await eventually(()=>counts('efficiency-f4-'+state.id)===1,'F4 received once');
      await delay(250);assert.equal(counts('efficiency-f4-'+state.id),1,'F4 received exactly once');
      await closeTab(rpc,state.tab);
    }},
  {name:'act_f7_three_pages',row:'F7: three result pages, one click each, the titles collected',plan:['do','do','do'],page:()=>fixtureUrl('f7','&page=1'),firstOutline:true,
    async run({call,tab,first}){
      let outline=outlineOf(first.reads[0]);const titles=[];
      for(const page of [2,3,4]){
        const done=await call('do',{tab,steps:[{do:'click',ref:lineRef(outline,'link "Next page"')}]});
        assert.deepEqual(outcomes(done),['done'],'a link click is free');
        outline=outlineOf(done);assert.match(outline,new RegExp('h1 "Results page '+page+'"'),'the next page comes back');
        titles.push(done.untrusted_content.title);
      }
      assert.deepEqual(titles,['Results page 2','Results page 3','Results page 4']);
    }},
  {name:'act_f5_free_click',row:'F5: a free click that changes part of the page',plan:['do'],page:()=>fixtureUrl('f5'),firstOutline:true,
    async run({call,tab,first}){
      const done=await call('do',{tab,steps:[{do:'click',ref:lineRef(outlineOf(first.reads[0]),'button "Refresh rows"')}]});
      assert.deepEqual(outcomes(done),['done']);assert.deepEqual([done.prepared,done.untrusted_content.stopped],[[],[]],'a free click');
      const changed=done.untrusted_content.changed;assert.equal(done.untrusted_content.more_changes,0,'every changed line named');
      for(let index=0;index<5;index++)assert.ok(changed.includes('refreshed item '+index),changed);
      for(const part of ['Showing 8 rows, refreshed once','Queue summary, updated'])assert.ok(changed.includes(part),changed);
      assert.match(changed,/^- .*Tip: rows refresh on request/m,'the removed paragraph is a gone line');
    }},
  {name:'act_list_25_tabs',row:'List 25 open tabs (titles of about 30 characters)',plan:['chrome_tabs'],phase:'many',
    async run({call}){
      const listed=await call('chrome_tabs',{});
      assert.equal(listed.total,EFFICIENCY_TAB_COUNT);assert.equal(listed.cursor,null,'one page');
      assert.ok(listed.untrusted_content.list.includes(tabTitle(1)),'the titles are listed');
    }},
];

// Group 16's latency comparison of F4 (brief 28a, "The form is timed up to the question"): the
// same work with brief 20's tools and with chrome_do, the read or the outline in hand before the
// clock, until the click on Save comes back prepared. Its prepared work is dropped untimed and
// the receiver has nothing from either side. Brief 20's references carry the page's view, which
// its own fills change, so its click needs the fresh reference a find gives (as the frozen
// baseline's F4 task did); the find is part of its side.
export const LATENCY_TASKS=[
  {name:'f4_old_to_question',row:'F4: six fills and the click on Save, up to the question',plan:['fill_form','find','find*','click'],page:({run})=>fixtureUrl('f4','&id=o'+run),firstRead:true,
    async run({call,tab,first,state}){
      const rows=parseRows(first.untrusted_content.tree);
      const fields=F4_FILLED.map((name,index)=>{const row=rows.find(named('textbox',name));assert.ok(row,name+' on the first page');return {...target(row),text:'Old side line '+index};});
      assert.equal((await call('fill_form',{fields})).remaining,0);
      const save=await pagedRow(call,'find',{tab,text:'Save'},named('button','Save'));
      const prepared=await call('click',target(save));state.approval=prepared.approval;
      assert.ok(prepared.approval?.operation_id,'brief 20\'s click on Save comes back prepared: '+JSON.stringify(prepared));
    },
    async after({rpc,counts,run,state}){await dropPrepared(rpc,state.approval);await delay(250);assert.equal(counts('efficiency-f4-o'+run),0,'F4 received nothing');}},
  {name:'act_f4_to_question',row:'F4: six fills and the click on Save, up to the question',plan:['do'],page:({run})=>fixtureUrl('f4','&id=n'+run),firstOutline:true,
    async run({call,tab,first,state}){
      const done=await call('do',{tab,steps:f4Steps(outlineOf(first.reads[0]),'New side line')});
      state.approval=done.prepared[0]?.approval;
      assert.deepEqual(outcomes(done),[...F4_FILLED.map(()=>'done'),'prepared'],'chrome_do\'s click on Save comes back prepared: '+JSON.stringify(done.steps));
    },
    async after({rpc,counts,run,state}){await dropPrepared(rpc,state.approval);await delay(250);assert.equal(counts('efficiency-f4-n'+run),0,'F4 received nothing');}},
];

// `toolName` is browser.mjs's: the tool the service runs for a harness verb. Without
// it (the browser-free test) a verb names chrome_<verb>.
export async function efficiencyProbe({rpc,eventually,settled,counts,getTab,out='/out',toolName=async action=>action.startsWith('chrome_')?action:'chrome_'+action}){
  const record=fs.openSync(out+'/efficiency-calls.jsonl','a'),timing=fs.openSync(out+'/efficiency-tasks.jsonl','a');
  const tab=getTab();
  async function open(url){
    const result=await rpc('chrome_open',{url});assert.ok(result.ok,JSON.stringify(result));
    const opened=result.data.tab;await settled(url,opened);return opened;
  }
  async function nav(url){const result=await rpc('chrome_go',{tab,url,discard_unsaved:true});assert.ok(result.ok,JSON.stringify(result));await settled(url,tab);}
  async function perform(task,run,context){
    const tools=[],names=[];let index=0;
    // `refusal` is the one error code a call must end in; any other outcome,
    // success included, fails the task.
    const call=async(action,args={},{refusal}={})=>{
      const result=await rpc(action,args),name=await toolName(action);
      const refused=refusal!==undefined&&!result.ok&&result.error?.code===refusal;
      fs.writeSync(record,JSON.stringify({task:task.name,run,warmup:run<EFFICIENCY_WARMUPS,index:index++,action:name,arguments:args,result,...(refused?{expected_refusal:refusal}:{})})+'\n');
      tools.push(action);names.push(name);
      if(refusal!==undefined){assert.ok(refused,task.name+' '+action+' should be refused with '+refusal+': '+JSON.stringify(result.ok?'it succeeded':result.error));return result.error;}
      assert.ok(result.ok,task.name+' '+action+': '+JSON.stringify(result.error));return result.data;
    };
    const state={};
    const started=performance.now();
    let failed=true;
    try{await task.run({...context,run,counts,call,state});failed=false;}
    finally{
      const milliseconds=performance.now()-started;
      fs.writeSync(timing,JSON.stringify({task:task.name,row:task.row,plan:task.plan,run,warmup:run<EFFICIENCY_WARMUPS,milliseconds,tools,names,...(state.measures?{measures:state.measures}:{})})+'\n');
      // `after` cleans up after a failed run too, but never hides why it failed
      // (run 43698395453 reported F4's receiver, not the click's refusal).
      if(task.after){try{await task.after({rpc,eventually,counts,run,state});}catch(error){if(!failed)throw error;console.error(task.name+' run '+run+', after the failure below: '+error.message);}}
    }
    assert.ok(followsPlan(tools,task.plan),task.name+' made '+tools.join(',')+' against its plan '+task.plan.join(','));
  }
  async function rounds(tasks,context){
    for(let run=0;run<EFFICIENCY_WARMUPS+EFFICIENCY_RUNS;run++)for(const task of tasks){
      let first=null;
      if(task.page){
        await nav(task.page({run}));
        // The first read a row comes after: brief 20's for its tasks, the new read for the read rows. Not counted.
        if(task.firstRead){const result=await rpc('read',{tab});assert.ok(result.ok);first=result.data;}
        if(task.firstOutline){const result=await rpc('outline',{tab});assert.ok(result.ok,JSON.stringify(result.error));first=result.data;}
      }
      await perform(task,run,{...context,tab,first});
    }
  }
  try{
    fs.writeFileSync(out+'/efficiency-runner.json',JSON.stringify({
      runner:{image_os:process.env.ImageOS||null,image_version:process.env.ImageVersion||null,environment:process.env.RUNNER_ENVIRONMENT||null,arch:process.env.RUNNER_ARCH||null},
      cpu:os.cpus()[0]?.model||null,cpus:os.cpus().length,memory_bytes:os.totalmem(),node:process.version,
      chrome:fs.existsSync(out+'/chrome-version.txt')?fs.readFileSync(out+'/chrome-version.txt','utf8').trim():null,
      run_id:process.env.GITHUB_RUN_ID||null,sha:process.env.GITHUB_SHA||null},null,2));
    // Brief 20's retired F4 task stays in TASKS as the frozen baseline's definition and isn't run.
    const all=[...TASKS,...OUTLINE_TASKS,...ACT_TASKS,...LATENCY_TASKS].filter(task=>!task.retired);
    await rounds(all.filter(task=>!task.phase),{});
    // Three tabs show F1, F2 and F3, then more tabs until 25 are open in all.
    const tabs=[];for(const name of ['f1','f2','f3'])tabs.push(await open(fixtureUrl(name)));
    await rounds(all.filter(task=>task.phase==='tabs'),{tabs});
    const listed=async()=>{const result=await rpc('chrome_tabs');assert.ok(result.ok);return result.data.total;};
    for(let id=1,count=await listed();count<EFFICIENCY_TAB_COUNT;id++,count++)await open(fixtureUrl('tab','&id='+id));
    assert.equal(await listed(),EFFICIENCY_TAB_COUNT);assert.ok(tabTitle(1).length>=28&&tabTitle(1).length<=32);
    await rounds(all.filter(task=>task.phase==='many'),{tabs});
    console.log('Efficiency probe complete:',all.length,'tasks,',EFFICIENCY_WARMUPS,'warm-up and',EFFICIENCY_RUNS,'measured runs each');
  }finally{fs.closeSync(record);fs.closeSync(timing);}
}
