// Group 16 runs the public Chrome tools in the latency harness. The old
// task plans below identify the frozen entries in efficiency-baseline.json.
import fs from 'node:fs';
import os from 'node:os';
import assert from 'node:assert/strict';
import {performance} from 'node:perf_hooks';
import {setTimeout as delay} from 'node:timers/promises';
import {F2_ROWS,F2_COLUMNS,f2Cell,F3_UNIQUE,F4_FILLED,tabTitle} from './efficiency-fixtures.mjs';

export const EFFICIENCY_WARMUPS=1,EFFICIENCY_RUNS=5,EFFICIENCY_TAB_COUNT=25;
export const fixtureUrl=(name,query='')=>'http://fixture.test:8765/?case=efficiency-'+name+query;

export const TASKS=[
  {name:'f1_first_read',row:'F1: the first read',plan:['read']},
  {name:'f1_everything',row:'F1: everything, the read and each cursor it returns',plan:['read','read*']},
  {name:'f1_fields',row:'F1: the 80 fields with their values, after the first read',plan:['find','find*','read_form','read_form*']},
  {name:'f2_table',row:'F2: the whole table, after the first read',plan:['read*']},
  {name:'f3_find_link',row:'F3: find the one link with the unique name',plan:['find','find*']},
  {name:'open_fact',row:'Open a fixture page and return one fact from it',plan:['open','wait']},
  {name:'f4_fill_send',row:'F4: fill 6 fields and send the form',plan:['read','fill_form','find','find*','click'], refusals:['asking_input_too_large']},
  {name:'f7_three_pages',row:'F7: three result pages, one click each, the titles collected',plan:['click','wait','click','wait','click','wait']},
  {name:'f5_free_click',row:'F5: a free click that changes part of the page',plan:['click','read']},
  {name:'three_tabs',row:'Compare three open tabs (F1, F2, F3)',plan:['read','read','read']},
  {name:'list_25_tabs',row:'List 25 open tabs (titles of about 30 characters)',plan:['tabs','tabs*']},
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

// The plans call the outline read 'outline'. The probe sends it as chrome_read.
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

// Time F4 only up to its prepared question. Drop that preparation untimed.
export const LATENCY_TASKS=[
  {name:'act_f4_to_question',row:'F4: six fills and the click on Save, up to the question',plan:['do'],page:({run})=>fixtureUrl('f4','&id=n'+run),firstOutline:true,
    async run({call,tab,first,state}){
      const done=await call('do',{tab,steps:f4Steps(outlineOf(first.reads[0]),'New side line')});
      state.approval=done.prepared[0]?.approval;
      assert.deepEqual(outcomes(done),[...F4_FILLED.map(()=>'done'),'prepared'],'chrome_do\'s click on Save comes back prepared: '+JSON.stringify(done.steps));
    },
    async after({rpc,counts,run,state}){await dropPrepared(rpc,state.approval);await delay(250);assert.equal(counts('efficiency-f4-n'+run),0,'F4 received nothing');}},
];

export async function efficiencyProbe({rpc,eventually,settled,counts,getTab,out='/out'}){
  const record=fs.openSync(out+'/efficiency-calls.jsonl','a'),timing=fs.openSync(out+'/efficiency-tasks.jsonl','a');
  const tab=getTab();
  async function open(url){
    const result=await rpc('chrome_open',{url});assert.ok(result.ok,JSON.stringify(result));
    const opened=result.data.tab;await settled(url,opened);return opened;
  }
  async function nav(url){const result=await rpc('chrome_go',{tab,url,discard_unsaved:true});assert.ok(result.ok,JSON.stringify(result));await settled(url,tab);}
  async function perform(task,run,context){
    const tools=[],names=[];let index=0;
    const call=async(action,args={})=>{
      const name='chrome_'+action.replace(/^chrome_/,'').replace(/^outline$/,'read');
      const result=await rpc(name,args);
      fs.writeSync(record,JSON.stringify({task:task.name,run,warmup:run<EFFICIENCY_WARMUPS,index:index++,action:name,arguments:args,result})+'\n');
      tools.push(action);names.push(name);
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
        // Some measured rows start with an outline already in hand.
        if(task.firstOutline){const result=await rpc('chrome_read',{tab});assert.ok(result.ok,JSON.stringify(result.error));first=result.data;}
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
    const all=[...OUTLINE_TASKS,...ACT_TASKS,...LATENCY_TASKS];
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
