// Brief 28a, groups 14 and 15 in the browser: the new tools (chrome_open, chrome_go,
// chrome_do, chrome_tabs, chrome_take, chrome_close, chrome_library and the new
// chrome_read) on the fixture pages of act-fixtures.mjs, as named cases of the
// recheck2 shard (verdicts.mjs): cases that prove an asking step asks are in
// group 1 (classification) or group 3 (binding), the password case in group 7
// (password_exclusion), the others beside brief 28's READ cases in SUPPORT.
// Every case runs first and is reported afterwards, in order, so one failure
// can't hide the evidence of the cases after it; each case closes the tabs it
// opened. The cases that restart the service and Chrome come last.
// Brief 20's tools are reached as matrices.mjs reaches them (`call`, `rpc` and
// their old verbs, browser.mjs); the new ones by their full names.
import assert from 'node:assert/strict';
import {pendingCheck} from './failure.mjs';
import fs from 'node:fs';
import net from 'node:net';
import {execFile} from 'node:child_process';
import {promisify} from 'node:util';
import {setTimeout as delay} from 'node:timers/promises';
import {auditRows,boundaryLog,completeIngress} from './ingress-scan.mjs';
import {hostileGrammar} from './outline-checks.mjs';
import {canonicalBytes} from './efficiency-probe.mjs';
import {F4_FILLED,HOSTILE} from './efficiency-fixtures.mjs';
import {ACT_MARK,LARGE_FIELDS,actUrl} from './act-fixtures.mjs';
import {LATE_DRAFT} from './unread-fixtures.mjs';
import {allTabs} from './tabs.mjs';

const OUT='/out/act';
const REFERENCE=/ ([bcdfghjklmnpqrstvwxyz]{5}\d+)(?=$| · )/;
const SECRET='SENTINEL_PRIVATE_PASSWORD_20';
const WITHHELD=/This form holds unread typed text; send it yourself/;
const run=promisify(execFile);
let sequence=0;
// Short, plain ids: an address shows them as they are.
const uid=name=>name+'-'+Date.now().toString(36)+'-'+(++sequence);

// The line of an outline that starts with these words, and the reference that ends it.
export function lineOf(outline,start){
  const line=String(outline).split('\n').find(line=>line.trimStart().startsWith(start));
  assert.ok(line,'a line starting with '+start+' in:\n'+String(outline).slice(0,3000));return line;
}
export function refOf(outline,start){const line=lineOf(outline,start),found=line.match(REFERENCE);assert.ok(found,'a reference on '+line);return found[1];}
const outcomes=result=>result.steps.map(step=>step.outcome);
const pad=index=>String(index).padStart(2,'0');

export async function actMatrix({check:report,call,rpc,nav,counts,eventually,fixture,admin,lifecycle,restoreControl,ownerNavigate,ownerOpenTab,ownerClickPage,ownerType,ownerKey,ownerDismiss,getTab,setTab}){
  fs.mkdirSync(OUT,{recursive:true});
  let current='',opened=[];
  const results=[];
  // Run now, report later (see the top); the case's tabs close either way.
  const check=async(name,fn)=>{
    current=name;opened=[];
    try{await fn();results.push({name});console.log('ACT CASE',name,'ran');}
    catch(error){results.push({name,error});console.error('ACT CASE',name,'failed',error.stack);}
    finally{try{await cleanup();}catch(error){console.error('ACT CASE cleanup',name,error.message);}}
  };

  // --- calls -------------------------------------------------------------------
  const record=(name,args,result)=>fs.appendFileSync(OUT+'/calls.jsonl',JSON.stringify({case:current,name,args,result})+'\n');
  async function tool(name,args={}){const result=await rpc('chrome_'+name,args);record(name,args,result);return result;}
  async function data(name,args={}){const result=await tool(name,args);assert.equal(result.ok,true,'chrome_'+name+': '+JSON.stringify(result.error));return result.data;}
  const refusal=(result,code)=>{assert.equal(result.ok,false,'refused: '+JSON.stringify(result.data??null).slice(0,600));if(code)assert.equal(result.error.code,code,JSON.stringify(result.error));return result.error;};
  async function open(url,extra={}){
    const page=await data('open',{url,...extra});opened.push(page.tab);
    assert.equal(page.error,undefined,'the opened page reads: '+JSON.stringify(page.error));return page;
  }
  const act=(tab,steps,extra={})=>data('do',{tab,steps,...extra});
  async function readTab(tab,args={}){
    const result=await data('read',{tab,...args}),entry=result.reads[0];
    assert.ok(entry&&!entry.error,'chrome_read: '+JSON.stringify(entry?.error));return entry;
  }
  async function cleanup(){
    for(const tab of opened.splice(0)){
      const closed=await rpc('chrome_close',{tabs:[tab],discard_unsaved:true}).catch(()=>null);
      if(closed?.ok&&closed.data.closed.some(row=>row.tab===tab))continue;
      // A tab that became a taken one is given back; his tabs stay his.
      await rpc('chrome_release',{tab}).catch(()=>null);
    }
  }
  async function drop(approval){
    if(!approval?.operation_id)return;
    await tool('drop',{operation_id:approval.operation_id});await tool('notice_ack',{operation_id:approval.operation_id});
  }
  // Zero arrivals before chrome_submit, one after, still one after a repeat.
  async function approve(approval,kind){
    assert.ok(approval?.operation_id,'an approval: '+JSON.stringify(approval));
    await delay(300);assert.equal(counts(kind),0,kind+': nothing before chrome_submit');
    const sent=await data('submit',approval);assert.equal(sent.operation.state,'done',JSON.stringify(sent.operation));
    await eventually(()=>counts(kind)===1,kind+': one arrival after chrome_submit');
    await tool('submit',approval);await delay(300);assert.equal(counts(kind),1,kind+': nothing on a repeat');
  }
  const arrivals=kind=>fixture.arrivals.filter(row=>new URL(row.url,'http://fixture.test').searchParams.get('case')===kind);
  const reported=kind=>arrivals(kind).map(row=>{try{return JSON.parse(row.body);}catch{return {};}});
  // What the page's fields reported (act-fixtures.mjs `inputs`): every value, with its field.
  const typed=(id,field)=>reported('act-input-'+id).filter(row=>!field||row.field===field);
  async function reserved(){
    let cursor,count=0;
    do{const page=await call('control_pending',{limit:10,...(cursor?{cursor}:{})});count+=page.items.filter(row=>row.app==='chrome'&&row.state==='reserved').length;cursor=page.cursor;}while(cursor);
    return count;
  }
  const seenOf=async()=>(await data('tabs',{})).seen;
  const listLine=(list,tab)=>list.split('\n').find(line=>new RegExp('^\\s*'+tab+' (claude|his|taken)\\b').test(line));
  // One call through the MCP proxy or the aresos command (call.py), timed alone; asynchronous,
  // so the fixture server in this process keeps serving.
  async function through(route,verb,args){
    const {stdout}=await run('python3',['control/chrome/ci/call.py',...(route==='command'?['--command']:[]),'--timed',verb,JSON.stringify(args)],
      {encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'true'},maxBuffer:16*1024*1024});
    const out=JSON.parse(stdout);record(route+':'+verb,args,out);return out;
  }
  async function throughData(route,verb,args){
    const out=await through(route,verb,args);
    assert.equal(out.result.ok,true,JSON.stringify(out.result.error));
    return {data:out.result.data,seconds:out.seconds};
  }
  // Reuse the fixture-only admin route to the instrumented worker.
  async function fixtureCommand(command,tab){
    const path='/out/fixture-hold.json';fs.rmSync(path,{force:true});
    const answer=await lifecycle({fixture:'hold',command,arguments:{tab}});
    assert.equal(answer.ok,true,JSON.stringify(answer));
    return JSON.parse(fs.readFileSync(path,'utf8'));
  }
  const countryOf=approval=>{
    const fields=approval.description.untrusted_content.page_state.form.fields;
    const country=fields.find(field=>field.label==='Country');assert.ok(country,'the Country list is described');
    assert.ok(!('options' in country),'the options he didn\'t choose are left out');return country;
  };

  // --- group 15 ---------------------------------------------------------------

  await check('GROUP 1 BRIEF28A opening a link by reference refuses a link whose click would ask and opens an ordinary one',async()=>{
    const id=uid('links'),page=await open(actUrl('links',id)),outline=page.untrusted_content.outline;
    for(const [name,what] of [['Delete','delete'],['Unsubscribe','unsub']]){
      const result=await tool('open',{ref:refOf(outline,'link "'+name+'"')});
      assert.match(refusal(result,'refused').message,/asks first; nothing was opened/);
      await delay(300);assert.equal(counts('act-link'+what+'-'+id),0,name+': nothing was fetched');
    }
    const plain=await data('open',{ref:refOf(outline,'link "Read more"')});opened.push(plain.tab);
    await eventually(()=>counts('act-linkplain-'+id)===1,'the ordinary link opens once');
  });

  await check('GROUP 3 BRIEF28A F4 is asked once through chrome_do with every filled value and its long list and is sent once',async()=>{
    const id=uid('f4'),page=await open(actUrl('f4',id)),outline=page.untrusted_content.outline;
    const steps=[...F4_FILLED.map((name,index)=>({do:'fill',ref:refOf(outline,'textbox "'+name+'"'),text:'Act line '+index})),{do:'click',ref:refOf(outline,'button "Save"')}];
    const done=await act(page.tab,steps);
    assert.deepEqual(outcomes(done),[...F4_FILLED.map(()=>'done'),'prepared']);assert.equal(done.not_run,0);
    assert.equal(done.prepared.length,1,'one question');
    const approval=done.prepared[0].approval,bytes=canonicalBytes(approval);
    console.log('ACT F4 approval bytes',bytes);fs.appendFileSync(OUT+'/f4-approval.jsonl',JSON.stringify({id,bytes,question:approval.question.length})+'\n');
    assert.ok(bytes<=9000,'the approval is at most 9,000 bytes: '+bytes);
    const fields=approval.description.untrusted_content.page_state.form.fields;
    F4_FILLED.forEach((name,index)=>assert.ok(fields.some(field=>field.value==='Act line '+index&&field.description==='"'+name+'"'),name+' shows its filled value'));
    const country=countryOf(approval);
    assert.deepEqual(country.chosen.map(option=>[option.label,option.value]),[['Country 7','c7']]);assert.equal(country.option_count,200);
    await approve(approval,'efficiency-f4-'+id);
    const sent=new URLSearchParams(arrivals('efficiency-f4-'+id)[0].body);
    F4_FILLED.forEach((_,index)=>assert.equal(sent.get('line'+index),'Act line '+index));assert.equal(sent.get('country'),'c7');
    // Enter in one of F4's fields is prepared the same way.
    const enter=uid('f4-enter'),second=await open(actUrl('f4',enter));
    const pressed=await act(second.tab,[{do:'press',ref:refOf(second.untrusted_content.outline,'textbox "Line 0"'),key:'Enter'}]);
    assert.deepEqual(outcomes(pressed),['prepared']);assert.ok(canonicalBytes(pressed.prepared[0].approval)<=9000);
    await drop(pressed.prepared[0].approval);await delay(300);assert.equal(counts('efficiency-f4-'+enter),0);
  });

  await check('GROUP 3 BRIEF28A options swapped while F4 approval waits are refused and a new preparation shows the same choice',async()=>{
    let tab=null;
    for(const change of ['act-rename','act-revalue','act-swap','act-chosen']){
      const id=uid(change.slice(4));
      const page=tab===null?await open(actUrl('f4',id)):await data('go',{tab,url:actUrl('f4',id),discard_unsaved:true});
      tab=page.tab;const save=refOf(page.untrusted_content.outline,'button "Save"');
      const first=await act(tab,[{do:'click',ref:save}]);assert.deepEqual(outcomes(first),['prepared']);
      const approval=first.prepared[0].approval,before=countryOf(approval);
      await fixture.mutate(id,change);
      for(const attempt of ['first','repeat']){
        const result=await tool('submit',approval);
        assert.ok(!result.ok||result.data.operation.state!=='done',change+' '+attempt+': '+JSON.stringify(result).slice(0,600));
        if(result.ok&&result.data.approval)await drop(result.data.approval);
        await delay(300);assert.equal(counts('efficiency-f4-'+id),0,change+' '+attempt+': the receiver has nothing');
      }
      if(change==='act-chosen')continue;
      // The comparison covered what the description doesn't list: a new question shows the same choice.
      const again=await act(tab,[{do:'click',ref:save}]);assert.deepEqual(outcomes(again),['prepared']);
      const after=countryOf(again.prepared[0].approval);
      assert.deepEqual(after.chosen,before.chosen,change);assert.equal(after.option_count,200,change);
      await drop(again.prepared[0].approval);
    }
  });

  await check('GROUP 1 BRIEF28A a list whose third step asks runs its first two inputs and after approval exactly the third',async()=>{
    const id=uid('third'),page=await open(actUrl('steps',id)),outline=page.untrusted_content.outline;
    const done=await act(page.tab,[{do:'fill',ref:refOf(outline,'textbox "Alpha"'),text:'One'},{do:'fill',ref:refOf(outline,'textbox "Beta"'),text:'Two'},
      {do:'click',ref:refOf(outline,'button "Send"')},{do:'fill',ref:refOf(outline,'textbox "Delta"'),text:'Four'},{do:'fill',ref:refOf(outline,'textbox "Epsilon"'),text:'Five'}]);
    assert.deepEqual(outcomes(done),['done','done','prepared']);assert.equal(done.not_run,2);
    assert.ok(done.steps.slice(0,2).every(step=>step.operation_id),'each input is its own operation');
    const fields=()=>new Set(typed(id).map(row=>row.field));
    assert.deepEqual([...fields()].sort(),['alpha','beta'],'the first two inputs reached the page, nothing after them');
    await approve(done.prepared[0].approval,'act-send-'+id);
    assert.deepEqual([...fields()].sort(),['alpha','beta'],'steps four and five never ran');
  });

  await check('GROUP 1 BRIEF28A a Delete control found in a folded part with find still asks',async()=>{
    const id=uid('fold'),page=await open(actUrl('fold',id));
    assert.ok(!page.untrusted_content.outline.includes('button "Delete"'),'the control is in a folded part');
    const found=await readTab(page.tab,{find:'Delete',role:'button'});
    const done=await act(page.tab,[{do:'click',ref:refOf(found.untrusted_content.outline,'button "Delete"')}]);
    assert.deepEqual(outcomes(done),['prepared']);await delay(300);assert.equal(counts('act-delete-'+id),0);
    await drop(done.prepared[0].approval);
  });

  await check('GROUP 1 BRIEF28A in conservative mode chrome_do asks for the same inputs as brief 20 and an asking select shows what it will choose',async()=>{
    await lifecycle({fixture:'qualification',mode:'conservative'});
    try{
      const notice=result=>assert.match(String(result.version_notice),/not qualified/,'the notice comes with the result');
      // F4's Country list by its label, and a three-option list: choosing is the option the step selects, chosen the one selected now.
      const id=uid('choose'),page=await open(actUrl('f4',id));notice(page);
      const outline=page.untrusted_content.outline;
      const country=await act(page.tab,[{do:'select',ref:refOf(outline,'combobox "Country"'),value:'Country 12'}]);
      assert.deepEqual(outcomes(country),['prepared']);notice(country);
      const shown=country.prepared[0].approval.description.untrusted_content.page_state.target;
      assert.deepEqual(shown.choosing.map(option=>[option.label,option.value]),[['Country 12','c12']]);
      assert.deepEqual(shown.chosen.map(option=>[option.label,option.value]),[['Country 7','c7']]);assert.equal(shown.option_count,200);
      const bytes=canonicalBytes(country.prepared[0].approval);
      // Lead decision, 2026-11-19: retain the repeated affected-item fields.
      assert.ok(bytes<16384&&bytes<=14000,'the asking select approval is under ASK_LIMIT and at most 14,000 bytes: '+bytes);
      const size=await act(page.tab,[{do:'select',ref:refOf(outline,'combobox "Size"'),value:'L'}]);assert.deepEqual(outcomes(size),['prepared']);
      const sized=size.prepared[0].approval.description.untrusted_content.page_state.target;
      assert.deepEqual(sized.choosing.map(option=>option.label),['L']);assert.deepEqual(sized.chosen.map(option=>option.label),['M']);
      await drop(size.prepared[0].approval);
      await data('submit',country.prepared[0].approval);await data('submit',country.prepared[0].approval);
      const read=await readTab(page.tab);assert.match(lineOf(read.untrusted_content.outline,'combobox "Country"'),/Country 12/);
      await delay(300);assert.equal(typed(id,'country').length,1,'the list changed once');
      // Brief 20's conservative matrix, through chrome_do: each activating input asks, typing and scrolling stay free.
      let tab=null;
      for(const [index,step] of [{do:'click',name:'button "Continue"'},{do:'select',name:'combobox "Choice"',value:'b'},{do:'check',name:'checkbox "Tick"',checked:true},
        {do:'click',name:'link "Read more"'},{do:'press',name:'button "Continue"',key:'Enter'},{do:'press',name:'button "Continue"',key:'Space'},{do:'click',name:'button "Search now"'}].entries()){
        const kind=uid('cons'+index),url='http://fixture.test:8765/?case=action-matrix&mode=conservative&id='+kind;
        const view=tab===null?await open(url):await data('go',{tab,url,discard_unsaved:true});tab=view.tab;
        const {name,...rest}=step;
        const result=await act(tab,[{...rest,ref:refOf(view.untrusted_content.outline,name)}]);notice(result);
        assert.deepEqual(outcomes(result),['prepared'],name+' '+step.do);await approve(result.prepared[0].approval,kind);
      }
      const view=await readTab(tab);
      const free=await act(tab,[{do:'fill',ref:refOf(view.untrusted_content.outline,'textbox "Text"'),text:'Plain text'},
        {do:'scroll',ref:refOf(view.untrusted_content.outline,'textbox "Text"'),y:40}]);
      assert.ok(outcomes(free).every(outcome=>['done','unchanged'].includes(outcome)),JSON.stringify(free.steps));
    }finally{await lifecycle({fixture:'qualification',mode:'qualified'});}
  });

  await check('ACT BRIEF28A the steps as defined give every outcome and a list failing at its third step keeps its two operations',async()=>{
    const id=uid('defined'),page=await open(actUrl('steps',id)),tab=page.tab,outline=page.untrusted_content.outline;
    const fruit=refOf(outline,'combobox "Fruit"');
    const one=async step=>(await act(tab,[step])).steps[0];
    // select by an option's value, by its label (runs of spaces joined), and the three refusals.
    // A select dispatches even for the current value; unchanged is checked below on a box.
    assert.equal((await one({do:'select',ref:fruit,value:'a'})).outcome,'done');
    assert.equal((await one({do:'select',ref:fruit,value:'b'})).outcome,'done');
    assert.equal((await one({do:'select',ref:fruit,value:'Apple'})).outcome,'done');
    assert.equal((await one({do:'select',ref:fruit,value:'Banana split'})).outcome,'done');
    for(const [value,message] of [['Twin','several options carry this label; pass the value'],['c','that option is disabled'],['Cherry','that option is disabled'],['Nope','no such option']]){
      const step=await one({do:'select',ref:fruit,value});assert.equal(step.outcome,'refused',value);assert.equal(step.message,message,value);
    }
    assert.equal((await one({do:'check',ref:refOf(outline,'checkbox "Extra"'),checked:false})).outcome,'unchanged');
    refusal(await tool('do',{tab,steps:[{do:'scroll',y:100}]}),'invalid_input');
    const waited=await act(tab,[{do:'wait',until:{text:'never on this page'},timeout_ms:500},{do:'fill',ref:refOf(outline,'textbox "Delta"'),text:'Never'}]);
    assert.deepEqual(outcomes(waited),['timeout']);assert.equal(waited.not_run,1);assert.equal(typed(id,'delta').length,0);
    const asked=await act(tab,[{do:'click',ref:refOf(outline,'button "Send"')}]);assert.deepEqual(outcomes(asked),['prepared']);await drop(asked.prepared[0].approval);
    // A list that fails at its third step after two inputs: a normal result, two operations chrome_operation_status knows.
    const failed=await act(tab,[{do:'fill',ref:refOf(outline,'textbox "Alpha"'),text:'A1'},{do:'fill',ref:refOf(outline,'textbox "Beta"'),text:'B1'},{do:'select',ref:fruit,value:'Nope'}]);
    assert.deepEqual(outcomes(failed),['done','done','refused']);
    for(const step of failed.steps.slice(0,2))assert.equal((await data('operation_status',{operation_id:step.operation_id})).operation.state,'done');
    // A dialog step on another dialog than the one the last result showed is stale, with the present one shown.
    assert.equal((await one({do:'click',ref:refOf(outline,'button "Notice later"')})).outcome,'done');
    await delay(3800);
    const unseen=await act(tab,[{do:'dialog',accept:true}]);
    assert.deepEqual(outcomes(unseen),['stale']);assert.match(JSON.stringify(unseen.untrusted_content.dialog),/Unseen notice/);
    assert.deepEqual(outcomes(await act(tab,[{do:'dialog',accept:true}])),['done'],'answered once it was shown');
  });

  await check('ACT BRIEF28A nothing unseen is overwritten and a fill then Enter on the same field runs without a read',async()=>{
    const id=uid('unseen'),page=await open(actUrl('steps',id)),tab=page.tab,outline=page.untrusted_content.outline;
    const epsilon=refOf(outline,'textbox "Epsilon"');
    const result=await act(tab,[{do:'click',ref:refOf(outline,'button "Load draft"')},{do:'fill',ref:epsilon,text:'Claude text'}]);
    assert.deepEqual(outcomes(result),['done','stale']);assert.equal(result.steps[1].code,'stale_reference');
    assert.match(String(result.untrusted_content.now),/Page draft/,'the field\'s present line');
    assert.ok(!typed(id,'epsilon').some(row=>row.value==='Claude text'),'the draft was not overwritten');
    assert.match(lineOf((await readTab(tab)).untrusted_content.outline,'textbox "Epsilon"'),/Page draft/);
    const alpha=refOf(outline,'textbox "Alpha"');
    const entered=await act(tab,[{do:'fill',ref:alpha,text:'Enter me'},{do:'press',ref:alpha,key:'Enter'}]);
    assert.equal(entered.steps[0].outcome,'done');assert.notEqual(entered.steps[1]?.outcome,'stale',JSON.stringify(entered.steps));
    for(const approval of entered.prepared)await drop(approval.approval);
  });

  await check('ACT BRIEF28A real owner keys during the first step leave the next fill stale with its present line',async()=>{
    const id=uid('owner-draft'),page=await open(actUrl('owner-draft',id)),tab=page.tab;
    const shown=await data('show',{tab});
    assert.equal(shown.shown,tab);
    const nativeWindow=await ownerClickPage(page.untrusted_content.title);
    const evidence=(phase,details)=>fs.appendFileSync(OUT+'/owner-draft.jsonl',JSON.stringify({id,tab,phase,at:Date.now(),...details})+'\n');
    evidence('native click',{nativeWindow,chromeWindow:shown.window});
    const inDraft=row=>row.field==='draft'&&row.trusted&&row.focused&&row.visible;
    const focus=await eventually(()=>reported('act-focus-'+id).find(inDraft),'native click focused the visible Draft field',5000);
    const active=(await allTabs(call)).items.find(row=>row.tab===tab);
    assert.ok(active?.active&&active.focused&&active.window===shown.window&&active.url===page.untrusted_content.url,
      'the fixture tab is active in the focused Chrome window: '+JSON.stringify(active));
    evidence('draft focused',{focus});
    const ref=refOf(page.untrusted_content.outline,'textbox "Draft"');
    assert.deepEqual(typed(id,'draft'),[],'the owner has yet to type');
    const offset=boundaryLog.size();
    const pending=pendingCheck(throughData('proxy','do',{tab,steps:[{do:'wait',until:{text:'Draft entered'},timeout_ms:8000},
      {do:'fill',ref,text:'Replacement'}]}));
    let result,typingAt;
    try{
      // Three page states establish the start, pre-step outline and wait outline.
      // The fourth is the first poll after the wait has checked for Draft entered.
      const polls=await eventually(()=>{
        const states=auditRows(offset,'command').filter(row=>row.command==='page_state'&&row.phase==='begin').length;
        return states>=4&&states;
      },
        'the first step is polling for the owner draft',6000);
      typingAt=Date.now();
      evidence('sending keys',{typingAt,pageStates:polls});
      ownerType('Owner words');
    }finally{({data:result}=await pending);}
    assert.deepEqual(outcomes(result),['done','stale']);
    assert.equal(result.steps[1].code,'stale_reference');
    assert.match(lineOf(result.untrusted_content.now,'textbox "Draft"'),/Owner words/);
    assert.match(lineOf((await readTab(tab)).untrusted_content.outline,'textbox "Draft"'),/Owner words/);
    await eventually(()=>typed(id,'draft').some(row=>row.value==='Owner words'&&inDraft(row)&&row.at>=typingAt),
      'the focused Draft received the full trusted text after the wait began',2000);
    assert.ok(reported('act-key-'+id).some(row=>inDraft(row)&&row.at>=typingAt),'a real key reached the focused Draft during the wait');
    assert.ok(typed(id,'draft').every(row=>inDraft(row)&&row.at>=typingAt&&'Owner words'.startsWith(row.value)),
      'every input was a trusted prefix of the owner draft entered during the wait');
  });

  await check('ACT BRIEF28A a dialog during input records one unknown operation and stops the list',async()=>{
    const id=uid('input-dialog'),page=await open(actUrl('input-dialog',id)),tab=page.tab,outline=page.untrusted_content.outline;
    const ref=refOf(outline,'button "Show notice"');
    const steps=[{do:'click',ref},{do:'fill',ref:refOf(outline,'textbox "Next field"'),text:'Too late'}];
    try{
      const {data:result}=await throughData('proxy','do',{tab,steps});
      assert.deepEqual(outcomes(result),['unknown']);
      const [entry]=result.steps;
      assert.equal(entry.do,'click');assert.equal(entry.ref,ref);
      assert.ok(entry.operation_id,'the unknown step has a committed operation');
      assert.deepEqual(result.unknown,[entry.operation_id]);assert.equal(result.not_run,1);
      assert.match(JSON.stringify(result.untrusted_content.dialog),/Input handler notice/);
      const {operation}=await data('operation_status',{operation_id:entry.operation_id});
      assert.equal(operation.id,entry.operation_id);assert.equal(operation.state,'unknown');
    }finally{ownerDismiss();}
    await eventually(async()=>!(await readTab(tab)).untrusted_content.dialog,'the owner dismissed the notice');
    await eventually(()=>reported('act-notice-click-'+id).length>0,'the page handled the click');
    await delay(500);
    assert.deepEqual(reported('act-notice-click-'+id).map(row=>row.trusted),[true],'one trusted click, without retry');
    assert.deepEqual(typed(id,'next'),[],'the next fill did not run');
  });

  await check('ACT BRIEF28A the look between steps stops at a held page submission a dialog and a new document',async()=>{
    const id=uid('look'),page=await open(actUrl('look',id)),tab=page.tab,outline=page.untrusted_content.outline,next=refOf(outline,'textbox "Next field"');
    const held=await act(tab,[{do:'click',ref:refOf(outline,'button "Start"')},{do:'fill',ref:next,text:'After start'}]);
    assert.deepEqual(outcomes(held),['done']);assert.equal(held.not_run,1);assert.equal(held.prepared.length,1,'the page\'s submission is held and asked');
    assert.equal(typed(id,'next').length,0,'the next step did not run');
    await approve(held.prepared[0].approval,'act-look-'+id);
    const dialog=await act(tab,[{do:'click',ref:refOf(outline,'button "Arm dialog"')},{do:'wait',until:{text:'never on this page'},timeout_ms:6000},{do:'fill',ref:next,text:'After dialog'}]);
    assert.deepEqual(outcomes(dialog),['done','timeout']);assert.equal(dialog.not_run,1);assert.match(JSON.stringify(dialog.untrusted_content.dialog),/Look notice/);
    assert.equal(typed(id,'next').length,0);
    assert.deepEqual(outcomes(await act(tab,[{do:'dialog',accept:true}])),['done']);
    const loaded=await act(tab,[{do:'click',ref:refOf(outline,'button "Arm load"')},{do:'wait',until:{text:'Landed page'},timeout_ms:6000},{do:'fill',ref:next,text:'After load'}]);
    assert.deepEqual(outcomes(loaded),['done','done']);assert.equal(loaded.not_run,1);
    assert.match(String(loaded.untrusted_content.outline),/Landed page/,'the new page\'s outline');assert.equal(typed(id,'next').length,0);
  });

  await check('ACT BRIEF28A a form too large to ask about is refused with its advice and its page submission stays stopped',async()=>{
    for(const mode of ['fields','text']){
      const id=uid('large-'+mode),page=await open(actUrl('large',id,'&mode='+mode)),tab=page.tab;
      const send=refOf((await readTab(tab,{find:'Send',role:'button'})).untrusted_content.outline,'button "Send"');
      const before=await reserved();
      const result=await act(tab,[{do:'click',ref:send}]);
      assert.deepEqual(outcomes(result),['refused']);assert.equal(result.steps[0].code,'asking_input_too_large');
      if(mode==='text')assert.match(result.steps[0].message,/Shorten the text you filled/);
      else{assert.match(result.steps[0].message,/ask the owner to send it himself/);assert.doesNotMatch(result.steps[0].message,/Shorten/);}
      assert.deepEqual(result.prepared,[]);assert.equal(await reserved(),before,'no operation is reserved');
      await delay(300);assert.equal(counts('act-large-'+id),0);
      if(mode==='fields'){
        const start=refOf((await readTab(tab,{find:'Start',role:'button'})).untrusted_content.outline,'button "Start"');
        const started=await act(tab,[{do:'click',ref:start}]);
        assert.deepEqual(outcomes(started),['done']);assert.deepEqual(started.prepared,[]);
        assert.ok(started.untrusted_content.stopped.length>=1,'the page\'s submission is named in stopped: '+JSON.stringify(started.untrusted_content));
        await delay(300);assert.equal(counts('act-large-'+id),0);
        await readTab(tab);
      }
    }
  });

  await check('ACT BRIEF28A steps land far below the fold and in a scrolled box and a scroll handler submission is asked',async()=>{
    const id=uid('far'),page=await open(actUrl('far',id)),tab=page.tab,outline=page.untrusted_content.outline;
    const done=await act(tab,[{do:'click',ref:refOf(outline,'button "Far button"')},{do:'fill',ref:refOf(outline,'textbox "Far field"'),text:'Far text'},
      {do:'check',ref:refOf(outline,'checkbox "Far tick"'),checked:true},{do:'click',ref:refOf(outline,'button "Inner button"')}]);
    assert.deepEqual(outcomes(done),['done','done','done','done']);
    await eventually(()=>reported('act-click-'+id).length===2,'both clicks landed');
    assert.deepEqual(reported('act-click-'+id).map(row=>row.name).sort(),['Far button','Inner button']);
    assert.ok(typed(id,'far').some(row=>row.value==='Far text'));assert.deepEqual(reported('act-tick-'+id).map(row=>row.checked),[true]);
    // An approved click on a Send button that is off screen when chrome_submit runs is dispatched once.
    const asked=await act(tab,[{do:'click',ref:refOf(outline,'button "Send far"')}]);assert.deepEqual(outcomes(asked),['prepared']);
    await act(tab,[{do:'scroll',ref:refOf(outline,'button "Top button"'),y:-30000}]);
    await approve(asked.prepared[0].approval,'act-farsend-'+id);
    const scrolled=uid('scroll'),second=await open(actUrl('far',scrolled,'&mode=scroll'));
    const go=await act(second.tab,[{do:'click',ref:refOf(second.untrusted_content.outline,'button "Far go"')}]);
    assert.equal(go.prepared.length,1,'the scroll handler\'s submission is held and asked: '+JSON.stringify(go));
    await approve(go.prepared[0].approval,'act-scroll-'+scrolled);
  });

  // --- group 14 ---------------------------------------------------------------

  await check('ACT BRIEF28A the fingerprint refuses a changed element with its present line and keeps unchanged ones acting',async()=>{
    const id=uid('print'),page=await open(actUrl('fingerprint',id)),tab=page.tab;
    const clicks=name=>reported('act-click-'+id).filter(row=>row.name.trim()===name).length;
    // Each pair: the page changes one element (a click Claude makes), then the list acts on that element.
    const pair=async(change,target,step)=>{
      // The default outline folds the last change buttons and inlines Open in its row.
      // Find each control just as a caller would; the long field's value stays cut.
      const changeOutline=(await readTab(tab,{find:change,role:'button'})).untrusted_content.outline;
      const [,role,label]=target.match(/^(\w+) "(.*)"$/);
      const targetOutline=(await readTab(tab,{find:label,role})).untrusted_content.outline;
      const result=await act(tab,[{do:'click',ref:refOf(changeOutline,'button "'+change+'"')},{...step,ref:refOf(targetOutline,target)}]);
      assert.equal(result.steps[0].outcome,'done',change);return result;
    };
    for(const [change,target,step,role] of [['Change path','link "Report"',{do:'click'},'link "Report"'],['Change query','link "Report"',{do:'click'},'link "Report"'],
      ['Change options','combobox "Plan list"',{do:'select',value:'b'},'combobox "Plan list"'],['Tick it','checkbox "Agree"',{do:'check',checked:true},'checkbox "Agree"'],
      ['Expand menu','button "Menu"',{do:'click'},'button "Menu"'],['Change end','textbox "Long note"',{do:'fill',text:'Replaced'},'textbox "Long note"']]){
      const result=await pair(change,target,step);
      assert.equal(result.steps[1]?.outcome,'stale',change+': '+JSON.stringify(result.steps));assert.equal(result.steps[1].code,'stale_reference');
      assert.ok(String(result.untrusted_content.now).includes(role),change+': the element\'s present line: '+result.untrusted_content.now);
    }
    await delay(300);
    assert.equal(counts('act-fplink-'+id),0,'the changed link was never followed');assert.equal(clicks('Menu'),0);
    assert.equal(reported('act-plan-'+id).length,0);assert.equal(reported('act-tick-'+id).length,0);assert.ok(!typed(id,'note').some(row=>row.value==='Replaced'));
    for(const [change,target,step] of [['Enable','button "Later"',{do:'click'}],['Require','textbox "Code box"',{do:'fill',text:'Code 1'}],['Move','button "Mover"',{do:'click'}],
      // The known limit, shown honestly: a button without a destination whose row shows another item.
      ['Swap row','button "Open"',{do:'click'}]]){
      const result=await pair(change,target,step);assert.equal(result.steps[1]?.outcome,'done',change+': '+JSON.stringify(result.steps));
    }
    await eventually(()=>clicks('Later')===1&&clicks('Mover')===1&&clicks('Open')===1,'the unchanged elements were acted on');
    assert.ok(typed(id,'code').some(row=>row.value==='Code 1'));
  });

  await check('ACT BRIEF28A hostile text stays quoted in a change report and in a stale present line',async()=>{
    const messages=new Set();let tab=null;
    for(let index=0;index<HOSTILE.length;index++){
      const id=uid('hostile'),url=actUrl('hostile',id,'&index='+index);
      const page=tab===null?await open(url):await data('go',{tab,url,discard_unsaved:true});tab=page.tab;
      const outline=page.untrusted_content.outline;
      const renamed=await act(tab,[{do:'click',ref:refOf(outline,'button "Rename status"')}]);
      assert.deepEqual(outcomes(renamed),['done']);hostileGrammar(renamed.untrusted_content.changed);
      const fresh=(await readTab(tab)).untrusted_content.outline;
      const stale=await act(tab,[{do:'click',ref:refOf(fresh,'button "Rename target"')},{do:'click',ref:refOf(fresh,'button "Target"')}]);
      assert.deepEqual(outcomes(stale),['done','stale'],'string '+index);
      hostileGrammar(String(stale.untrusted_content.now));messages.add(stale.steps[1].message);
      await delay(200);assert.equal(counts('act-click-'+id),0,'the renamed target was not clicked');
    }
    assert.equal(messages.size,1,'a stale step\'s message holds nothing from the page: '+[...messages].join(' | '));
  });

  await check('ACT BRIEF28A loaded holds for a fragment and a single page back without a new document and a reload waits for its document',async()=>{
    const id=uid('loaded'),page=await open(actUrl('loaded',id)),tab=page.tab;assert.equal(page.loaded,true);
    const stamp=outline=>{const found=String(outline).match(/Load stamp ([a-z0-9]+)/);assert.ok(found,outline);return found[1];};
    // Test reload before adding a fragment: the frozen guard compares CDP's URL
    // without its separate urlFragment to webNavigation's full URL (known limit).
    const initial=stamp(page.untrusted_content.outline),reloaded=await data('go',{tab,to:'reload'});
    assert.equal(reloaded.loaded,true);assert.notEqual(stamp(reloaded.untrusted_content.outline),initial,'loaded after the new document is there');
    const first=stamp(reloaded.untrusted_content.outline);
    const fragment=await data('go',{tab,url:actUrl('loaded',id)+'#part2'});
    assert.equal(fragment.loaded,true);assert.equal(stamp(fragment.untrusted_content.outline),first,'the fragment stays in its document');
    const view=await act(tab,[{do:'click',ref:refOf(fragment.untrusted_content.outline,'button "Go to view 2"')}]);assert.deepEqual(outcomes(view),['done']);
    const back=await data('go',{tab,to:'back'});
    assert.equal(back.loaded,true);assert.equal(stamp(back.untrusted_content.outline),first,'back inside the single-page fixture');
    assert.match(back.untrusted_content.outline,/View 1/);
    // until on a page that never goes quiet returns when the text is there, with loaded false.
    const busy=await open(actUrl('loaded',uid('busy'),'&mode=busy'),{until:{text:'Busy ready'},timeout_ms:5000});
    assert.equal(busy.until_met,true);assert.equal(busy.loaded,false);
  });

  await check('ACT BRIEF28A the read-only site refuses every acting step and still allows wait and scrolling',async()=>{
    const site='http://look.test:8765/';admin('chrome_sites',{command:'readonly',site,enabled:true});
    try{
      const id=uid('look-only'),page=await open(site+'?case=act-steps&id='+id),tab=page.tab,outline=page.untrusted_content.outline;
      for(const step of [{do:'fill',ref:refOf(outline,'textbox "Alpha"'),text:'x'},{do:'click',ref:refOf(outline,'button "Send"')},{do:'select',ref:refOf(outline,'combobox "Fruit"'),value:'b'},
        {do:'check',ref:refOf(outline,'checkbox "Extra"'),checked:true},{do:'press',ref:refOf(outline,'textbox "Alpha"'),key:'Enter'}]){
        const result=await act(tab,[step]);assert.deepEqual(outcomes(result),['refused'],step.do);assert.equal(result.steps[0].code,'readonly_site',step.do);
      }
      const allowed=await act(tab,[{do:'wait',until:{text:'Steps'},timeout_ms:2000},{do:'scroll',ref:refOf(outline,'textbox "Alpha"'),y:40}]);
      assert.equal(allowed.steps[0].outcome,'done');assert.ok(['done','unchanged'].includes(allowed.steps[1]?.outcome),JSON.stringify(allowed.steps));
      await delay(300);assert.deepEqual(typed(id),[]);assert.equal(counts('act-send-'+id),0);
    }finally{try{admin('chrome_sites',{command:'readonly',site,enabled:false});}catch(error){console.error('ACT read-only site stays marked:',error.message);}}
  });

  await check('ACT BRIEF28A addresses hold no sign-in in any result question stage notice or log line and the full address still reaches the page',async()=>{
    const id=uid('addr'),url=actUrl('address',id,'&q=red+shoes&page=2&code='+ACT_MARK),seen=[];
    const clean=(name,value)=>{const text=JSON.stringify(value);seen.push(name);assert.ok(!text.includes(ACT_MARK)&&!text.includes(ACT_MARK.slice(0,12)),name+' holds the marker');return text;};
    const queryless=(name,value)=>{const text=clean(name,value);assert.ok(!text.includes('shoes')&&!text.includes('page=2'),name+' holds a query');};
    const page=await open(url),tab=page.tab;clean('chrome_open',page);
    for(const part of ['q=red+shoes','page=2','code=…'])assert.ok(page.untrusted_content.url.includes(part),page.untrusted_content.url+' shows '+part);
    await eventually(()=>reported('act-addrseen-'+id).some(row=>String(row.href).includes(ACT_MARK)),'the page loaded at its full address');
    const listed=await data('tabs',{});clean('chrome_tabs',listed);
    const line=listLine(listed.untrusted_content.list,tab);assert.ok(line,listed.untrusted_content.list);assert.match(line,/\?…$/,'a list shows no query: '+line);
    // The full address behind a link's reference, a Claude tab and a library entry.
    const outline=page.untrusted_content.outline;
    const linked=await data('open',{ref:refOf(outline,'link "Plain link"')});opened.push(linked.tab);clean('chrome_open by a link',linked);
    await eventually(()=>arrivals('act-addrlink-'+id).length===1,'the link\'s full address');
    assert.ok(arrivals('act-addrlink-'+id)[0].url.includes(ACT_MARK)&&arrivals('act-addrlink-'+id)[0].url.includes('q=red+shoes'));
    const copy=await data('open',{tab});opened.push(copy.tab);clean('chrome_open by a tab',copy);
    await eventually(()=>reported('act-addrseen-'+id).filter(row=>String(row.href).includes(ACT_MARK)).length===2,'the tab\'s full address');
    const history=await data('library',{kind:'history',text:'Address acts'});clean('chrome_library',history);
    const entry=history.untrusted_content.items.find(item=>item.ref&&item.title==='Address acts');assert.ok(entry,JSON.stringify(history));
    assert.match(String(entry.url),/\?…$/);
    const reopened=await data('open',{ref:entry.ref});opened.push(reopened.tab);clean('chrome_open by a library entry',reopened);
    await eventually(()=>reported('act-addrseen-'+id).filter(row=>String(row.href).includes(ACT_MARK)).length>=3,'the entry\'s full address');
    // Records: a free click and an approved send; the stage texts, the notices and the log hold no query.
    const free=await act(tab,[{do:'click',ref:refOf(outline,'button "Note"')}]);clean('a free click',free);
    const asked=await act(tab,[{do:'click',ref:refOf(outline,'button "Send order"')}]);assert.deepEqual(outcomes(asked),['prepared']);
    clean('the question and description',asked.prepared[0].approval);
    await approve(asked.prepared[0].approval,'act-addrsend-'+id);
    assert.ok(arrivals('act-addrsend-'+id)[0].url.includes(ACT_MARK),'the form went to its full address');
    for(const operation of [free.steps[0].operation_id,asked.prepared[0].approval.operation_id]){
      const status=await data('operation_status',{operation_id:operation});clean('chrome_operation_status',status);queryless('stage texts',status.operation.stages);
    }
    clean('chrome_notices',await data('notices',{}));
    let cursor,pages=0;
    do{const log=await call('control_log',{limit:10,...(cursor?{cursor}:{})});queryless('control_log',log.items);cursor=log.cursor;pages++;}while(cursor&&pages<200);
    // Group 3's binding still refuses a destination whose query changed while the approval waited, also in a part shown as ….
    const waiting=uid('addr-wait'),second=await open(actUrl('address',waiting,'&q=red+shoes'));
    const prepared=await act(second.tab,[{do:'click',ref:refOf(second.untrusted_content.outline,'button "Send order"')}]);assert.deepEqual(outcomes(prepared),['prepared']);
    assert.match(JSON.stringify(prepared.prepared[0].approval),/session=…/);
    await fixture.mutate(waiting,'act-session');
    const late=await tool('submit',prepared.prepared[0].approval);clean('the changed destination',late);
    assert.ok(!late.ok||late.data.operation.state!=='done',JSON.stringify(late).slice(0,600));
    if(late.ok&&late.data.approval)await drop(late.data.approval);
    await delay(300);assert.equal(counts('act-addrsend-'+waiting),0,'nothing was sent to the changed destination');
  });

  await check('ACT BRIEF28A staged waits carry a list across the cut-off through the proxy and no input is dispatched after 12 seconds',async()=>{
    const id=uid('stage'),page=await open(actUrl('stage',id)),note=refOf(page.untrusted_content.outline,'textbox "Stage note"');
    const steps=[];for(let index=1;index<=10;index++)steps.push({do:'wait',until:{text:'stage '+index},timeout_ms:8000},{do:'fill',ref:note,text:'Fill '+pad(index)+'.'});
    await fixture.mutate(id,'act-start');
    const sent=Date.now(),out=await through('proxy','do',{tab:page.tab,steps}),returned=Date.now();
    assert.ok(out.seconds<=18,'the result within 18 seconds: '+out.seconds);assert.equal(out.result.ok,true,JSON.stringify(out.result.error));
    const result=out.result.data;
    assert.deepEqual(outcomes(result),['done','done','done','done','done','done','timeout']);assert.equal(result.deadline,true);assert.equal(result.not_run,13);
    await delay(10000);
    const rows=typed(id,'note');
    assert.deepEqual([...new Set(rows.map(row=>row.value))].filter(value=>/^Fill \d\d\.$/.test(value)).sort(),['Fill 01.','Fill 02.','Fill 03.']);
    for(const row of rows){assert.ok(row.at<=sent+12500,'an input at '+(row.at-sent)+' ms');assert.ok(row.at<=returned,'no input after the result');}
    fs.appendFileSync(OUT+'/time.jsonl',JSON.stringify({case:'staged',seconds:out.seconds,inputs:rows.map(row=>row.at-sent)})+'\n');
  });

  await check('ACT BRIEF28A twenty fills through the command end by their deadline and the fixture counts exactly the fills that ran',async()=>{
    const id=uid('many'),page=await open(actUrl('f4',id)),outline=page.untrusted_content.outline;
    const steps=Array.from({length:20},(_,index)=>({do:'fill',ref:refOf(outline,'textbox "Line '+(index%10)+'"'),text:'Many '+pad(index)+'.'}));
    const sent=Date.now(),out=await through('command','do',{tab:page.tab,steps});
    assert.ok(out.seconds<=18,'the result within 18 seconds: '+out.seconds);assert.equal(out.result.ok,true,JSON.stringify(out.result.error));
    const result=out.result.data,ran=result.steps.length;
    assert.ok(outcomes(result).every(outcome=>outcome==='done'),JSON.stringify(result.steps));assert.equal(ran+result.not_run,20);
    assert.equal(result.deadline,result.not_run>0);
    await delay(10000);
    const rows=typed(id).filter(row=>/^Many \d\d\.$/.test(row.value));
    assert.equal(new Set(rows.map(row=>row.value)).size,ran,'the fixture counts exactly the fills that ran');
    for(const row of typed(id))assert.ok(row.at<=sent+12500,'an input at '+(row.at-sent)+' ms');
    fs.appendFileSync(OUT+'/time.jsonl',JSON.stringify({case:'many',seconds:out.seconds,ran,not_run:result.not_run})+'\n');
  });

  await check('ACT BRIEF28A a frame answer held at the dispatch boundary leaves its committed fill unrun',async()=>{
    const otherId=uid('after-boundary'),other=await open(actUrl('plain',otherId));
    const id=uid('boundary'),page=await open(actUrl('stage',id,'&mode=boundary')),tab=page.tab;
    const ref=refOf(page.untrusted_content.outline,'textbox "Stage note"');
    const steps=['stage 1','stage 2'].map(text=>({do:'wait',until:{text},timeout_ms:8000}));
    steps.push({do:'fill',ref,text:'Beyond the boundary'});
    assert.deepEqual(await fixtureCommand('fixture_hold_input_boundary',tab),{held:tab});
    const offset=boundaryLog.size();
    await fixture.mutate(id,'act-start');
    const sent=Date.now(),{data:result,seconds}=await throughData('proxy','do',{tab,steps});
    assert.ok(seconds<=18,'the result within 18 seconds: '+seconds);
    assert.deepEqual(outcomes(result),['done','done']);
    assert.equal(result.deadline,true);assert.equal(result.not_run,1);
    assert.deepEqual(result.unknown,[]);
    assert.deepEqual(typed(id,'note'),[],'no input at return');

    const {data:next}=await throughData('command','chrome_read',{tab:other.tab});
    assert.equal(next.reads.length,1);assert.equal(next.reads[0].tab,other.tab);
    assert.equal(next.reads[0].untrusted_content.title,'Plain '+otherId,'the next call got its own page');
    const traces=()=>auditRows(offset,'fixture_input_boundary').map(row=>row.fixture_input_boundary).filter(row=>row.tab===tab);
    await eventually(()=>traces().some(row=>row.phase==='released'),'the held reader answer was released');
    const [held,ended,released]=traces();
    assert.deepEqual(traces().map(row=>row.phase),['held','setup-ended','released']);
    assert.equal(held.answered,true,'a real frame answer was held');
    assert.ok(held.at-sent>=10500&&held.at-sent<12000,JSON.stringify(held));
    assert.ok(held.remainingMs>0&&held.remainingMs<=1800,JSON.stringify(held));
    assert.equal(ended.expired,true);assert.equal(ended.whileHeld,true,'setup expired before the frame answered');
    assert.ok(released.remainingMs<=-950,JSON.stringify(released));
    assert.equal(released.sameConnection,true);
    assert.ok(held.operation&&[ended,released].every(row=>row.session===held.session&&row.operation===held.operation));
    const {operation}=await data('operation_status',{operation_id:held.operation});
    assert.equal(operation.id,held.operation);assert.equal(operation.state,'failed');
    assert.match(operation.reason,/^Nothing dispatched:/);
    assert.ok(!Object.hasOwn(operation.stages,'dispatched'));
    await delay(10000);
    assert.deepEqual(typed(id,'note'),[],'no input after the late answer');
    const fresh=await readTab(tab);
    assert.equal(refOf(fresh.untrusted_content.outline,'textbox "Stage note"'),ref,'the undelivered fill kept its reference');
    fs.appendFileSync(OUT+'/time.jsonl',JSON.stringify({case:'held-frame',seconds,sent,held,ended,released,operation:operation.id})+'\n');
  });

  await check('ACT BRIEF28A a caller killed during a list leaves no later input and the next call works',async()=>{
    const id=uid('killed'),page=await open(actUrl('f4',id)),outline=page.untrusted_content.outline;
    const steps=Array.from({length:20},(_,index)=>({do:'fill',ref:refOf(outline,'textbox "Line '+(index%10)+'"'),text:'Killed '+pad(index)+'.'}));
    const socket=net.createConnection('/run/aresos-tools/act.sock');socket.on('error',()=>{});
    await new Promise(resolve=>socket.once('connect',resolve));
    const sent=Date.now();socket.write(JSON.stringify({v:1,method:'call',action:'chrome_do',arguments:{tab:page.tab,steps}})+'\n');
    await delay(3000);socket.destroy();
    await delay(Math.max(0,sent+20000-Date.now()));
    assert.ok(typed(id).length>0,'some fills ran before the caller went');
    for(const row of typed(id))assert.ok(row.at<=sent+12500,'an input at '+(row.at-sent)+' ms');
    await readTab(page.tab);
  });

  await check('ACT BRIEF28A chrome_tabs marks sound and replaces it with muted during playback',async()=>{
    const id=uid('media'),page=await open(actUrl('media',id));
    assert.deepEqual(outcomes(await act(page.tab,[{do:'click',ref:refOf(page.untrusted_content.outline,'button "Play"')}])),['done']);
    const marks=async()=>(listLine((await data('tabs',{})).untrusted_content.list,page.tab)||'').split('"',1)[0].trim().split(/\s+/);
    const sound=await eventually(async()=>{const row=await marks();return row.includes('sound')&&row;},'the sound mark');
    assert.ok(!sound.includes('muted'));
    assert.deepEqual(await fixtureCommand('fixture_mute_tab',page.tab),{muted:true});
    const mutedAt=Date.now();
    const muted=await eventually(async()=>{const row=await marks();return row.includes('muted')&&row;},'the muted mark');
    assert.ok(!muted.includes('sound'),'the muted tab no longer shows sound');
    await eventually(()=>reported('act-playback-'+id).some(row=>row.at>=mutedAt&&row.position>0),'the audio keeps playing while its tab is muted');
  });

  await check('ACT BRIEF28A closing takes one tab per flag and a taken tab stays his',async()=>{
    const one=await open(actUrl('plain',uid('one'))),two=await open(actUrl('plain',uid('two')));
    assert.deepEqual(outcomes(await act(one.tab,[{do:'fill',ref:refOf(one.untrusted_content.outline,'textbox "Note"'),text:'Unsaved words'}])),['done']);
    assert.match(refusal(await tool('close',{tabs:[one.tab,two.tab],discard_unsaved:true}),'invalid_input').message,/one at a time/);
    const both=(await data('tabs',{})).untrusted_content.list;assert.ok(listLine(both,one.tab)&&listLine(both,two.tab),'both stay open');
    const kept=await data('close',{tabs:[one.tab]});assert.equal(kept.kept[0]?.code,'reload_required',JSON.stringify(kept));
    assert.deepEqual((await data('close',{tabs:[one.tab],discard_unsaved:true})).closed.map(row=>row.tab),[one.tab]);
    assert.deepEqual((await data('close',{tabs:[two.tab]})).closed.map(row=>row.tab),[two.tab]);
    opened=opened.filter(tab=>tab!==one.tab&&tab!==two.tab);
    // A taken tab that holds his typing: chrome_close refuses it, chrome_go answers reload_required and replaces nothing.
    const typedId=uid('typed'),url=actUrl('typed',typedId),tab=await ownerOpenTab(url);opened.push(tab);
    await delay(1500);ownerType('His own words');await delay(500);
    const taken=await data('take',{tab,seen:await seenOf()});assert.equal(taken.reload_due,true,JSON.stringify(taken));
    const closing=await data('close',{tabs:[tab]});assert.equal(closing.kept[0]?.code,'refused',JSON.stringify(closing));
    assert.ok(listLine((await data('tabs',{})).untrusted_content.list,tab),'the taken tab stays open');
    refusal(await tool('go',{tab,url:actUrl('plain',uid('elsewhere'))}),'reload_required');
    const row=(await allTabs(call)).items.find(item=>item.tab===tab);assert.equal(row?.url,url,'the page was not replaced');
    await data('release',{tab});
    // In an unwatched owner document even an empty textarea has unknown
    // history. Keep that refusal; the no-typing path uses no editable fields.
    const unreadUrl=actUrl('plain',uid('unread-empty')),unread=await ownerOpenTab(unreadUrl);opened.push(unread);
    const unreadTake=await data('take',{tab:unread,seen:await seenOf()});assert.equal(unreadTake.reload_due,true);assert.equal(unreadTake.typed_fields,0,'the field is empty');
    const unreadGo=refusal(await tool('go',{tab:unread,url:actUrl('plain',uid('unread-target'))}),'reload_required');
    assert.ok(unreadGo.untrusted_content.loss.fields.some(field=>field.by==='owner'&&field.description==='text area "Note"'));
    assert.equal((await allTabs(call)).items.find(item=>item.tab===unread)?.url,unreadUrl,'the unread empty field is not discarded');
    await data('release',{tab:unread});
    const plainId=uid('plain'),other=await ownerOpenTab(actUrl('plain',plainId,'&mode=empty'));opened.push(other);
    const empty=await data('take',{tab:other,seen:await seenOf()});assert.equal(empty.reload_due,true);assert.equal(empty.typed_fields,0);
    const target=uid('target'),went=await data('go',{tab:other,url:actUrl('plain',target)});
    assert.equal(went.loaded,true);assert.ok(String(went.untrusted_content.url).includes(target),went.untrusted_content.url);
  });

  await check('ACT BRIEF28A a tab list binds his tab and a tab moved on or an old list is refused while the listed address still opens',async()=>{
    const id=uid('seen'),his=await ownerOpenTab(actUrl('plain',id));opened.push(his);
    refusal(await tool('take',{tab:his}),'invalid_input');refusal(await tool('open',{tab:his}),'invalid_input');
    let listed=await data('tabs',{});assert.match(listLine(listed.untrusted_content.list,his)||'',/ his\b/);
    assert.equal((await data('take',{tab:his,seen:listed.seen})).tab,his,'an unchanged tab is taken without a further question');
    await data('release',{tab:his});
    const copy=await data('open',{tab:his,seen:(await data('tabs',{})).seen});opened.push(copy.tab);assert.ok(String(copy.untrusted_content.url).includes('id='+id),copy.untrusted_content.url);
    // He moves the listed tab on: to a new document, then to a new address in the same document.
    listed=await data('tabs',{});const moved=actUrl('plain',id+'-b');await ownerNavigate(moved,{tab:his});
    refusal(await tool('take',{tab:his,seen:listed.seen}),'stale_reference');
    const row=async()=>(await allTabs(call)).items.find(item=>item.tab===his);
    assert.equal((await row()).url,moved,'not reloaded or moved');assert.equal((await row()).controlled,false,'not attached');
    const listedAddress=await data('open',{tab:his,seen:listed.seen});opened.push(listedAddress.tab);
    assert.ok(String(listedAddress.untrusted_content.url).includes('id='+id+'&')||String(listedAddress.untrusted_content.url).endsWith('id='+id),'the address the list showed: '+listedAddress.untrusted_content.url);
    listed=await data('tabs',{});await ownerNavigate(moved+'#moved',{tab:his});
    refusal(await tool('take',{tab:his,seen:listed.seen}),'stale_reference');
    // A seen older than eight lists.
    const old=(await data('tabs',{})).seen;for(let index=0;index<8;index++)await data('tabs',{});
    refusal(await tool('take',{tab:his,seen:old}),'stale_reference');
    assert.equal((await data('take',{tab:his,seen:await seenOf()})).tab,his);await data('release',{tab:his});
  });

  await check('GROUP 7 BRIEF28A no password reaches the new tools results questions or records',async()=>{
    const none=(name,value)=>{assert.ok(!JSON.stringify(value).includes(SECRET),name+' holds the password');return value;};
    const page=none('chrome_open',await open('http://fixture.test:8765/?case=password-matrix')),tab=page.tab,outline=page.untrusted_content.outline;
    none('chrome_read',await data('read',{tab,full:true,max:40000}));
    const shown=none('the change report after Show',await act(tab,[{do:'click',ref:refOf(outline,'button "Show"')}]));assert.deepEqual(outcomes(shown),['done']);
    none('chrome_read after Show',await data('read',{tab,full:true,max:40000}));
    const fresh=(await readTab(tab,{full:true,max:40000})).untrusted_content.outline;
    const asked=none('the question of a form holding a password field',await act(tab,[{do:'click',ref:refOf(fresh,'button "Submit top 0"')}]));
    assert.deepEqual(outcomes(asked),['prepared']);await drop(asked.prepared[0].approval);
    // The password fixture has subframes with unknown request methods: its reload
    // correctly refuses. A fresh GET still exercises the go result's password rule.
    none('chrome_go',await data('go',{tab,url:'http://fixture.test:8765/?case=password-matrix&id='+uid('fresh'),discard_unsaved:true}));
    const his=await open('http://fixture.test:8765/?case=password-matrix&id='+uid('his'));await data('release',{tab:his.tab});
    none('chrome_take',await data('take',{tab:his.tab,seen:await seenOf()}));await data('release',{tab:his.tab});
    const ingress=completeIngress(fs.readFileSync('/out/browser-boundary.jsonl','utf8'));
    assert.ok(!ingress.some(row=>JSON.stringify(row).includes(SECRET)),'browser-boundary.jsonl');
    for(const file of ['tool.jsonl','service.txt',OUT.slice(5)+'/calls.jsonl'])assert.ok(!fs.readFileSync('/out/'+file,'utf8').includes(SECRET),file);
  });

  await check('ACT BRIEF28A the asking read on the new list shows typed fields unread and returns exactly the approved fields whose refs stay unread',async()=>{
    const tab=getTab(),id=uid('ask');await tool('release',{tab});
    await ownerNavigate('http://fixture.test:8765/?case=password-outline&mode=plain&id='+id+'&code='+ACT_MARK,{tab});
    await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='ask-frame-first'),'asking frame loaded before take');
    const kept=await data('take',{tab,seen:await seenOf()});assert.equal(kept.reload_due,true);
    const entry=await readTab(tab,{max:40000});assert.equal(entry.typed_fields,9);
    for(const label of ['Text note','Area note'])assert.ok(entry.untrusted_content.outline.includes('"'+label+'" (filled, not read)'),label);
    assert.doesNotMatch(JSON.stringify(entry),/ASK_[A-Z_]+_28/);
    const prepared=await data('prepare_read_typed_fields',{tab}),approval=prepared.approval;
    assert.ok(!JSON.stringify(approval).includes(ACT_MARK),'the question shows the address in its public form');
    const values=await data('read_typed_fields',approval),fields=values.untrusted_content.typed_fields;
    const listed=approval.description.untrusted_content.fields.frames.flatMap(frame=>frame.fields);
    assert.equal(fields.length,listed.length,'exactly the fields the question listed');
    assert.ok(fields.every(field=>typeof field.label==='string'&&typeof field.value==='string'),JSON.stringify(fields));
    const text=fields.find(field=>field.label==='Text note'&&field.ref);assert.ok(text,JSON.stringify(fields));
    const again=await readTab(tab,{ref:text.ref});assert.match(again.untrusted_content.outline,/\(filled, not read\)/);
    assert.doesNotMatch(JSON.stringify(again),/ASK_[A-Z_]+_28/);
    const fill=await act(tab,[{do:'fill',ref:text.ref,text:'Replaced'}]);assert.notEqual(fill.steps[0]?.outcome,'done',JSON.stringify(fill.steps));
  });

  await check('GROUP 3 BRIEF28A a form holding an unread field is not sent through chrome_do',async()=>{
    const tab=getTab(),id=uid('late');
    await call('release_tab',{tab});await ownerNavigate('http://fixture.test:8765/?case=compose&id='+id,{tab});await call('take_tab',{tab});
    await nav('password-unread&mode=late&id='+id+'&variant=form');await readTab(tab);
    await fixture.mutate(id,'review-change');
    await eventually(()=>fixture.compatibility.some(row=>row.id===id&&row.phase==='late-ready'),'the component attached its root');
    ownerType(LATE_DRAFT);ownerKey(true);
    await eventually(()=>fixture.compatibility.find(row=>row.id===id&&row.phase==='late-typed'),'the owner typed into the late root');await delay(700);
    const outline=(await readTab(tab,{full:true,max:40000})).untrusted_content.outline;assert.ok(!outline.includes(LATE_DRAFT));
    const notSent=async(name,result)=>{
      const own=JSON.stringify({steps:result.steps,stopped:result.untrusted_content.stopped,error:result.error});
      assert.match(own,WITHHELD,name+': '+own);assert.deepEqual(result.prepared,[],name+': no question');assert.ok(!JSON.stringify(result).includes(LATE_DRAFT),name);
      await delay(700);assert.equal(counts(id),0,name+': the receiver has nothing');
    };
    const send=await act(tab,[{do:'click',ref:refOf(outline,'button "Send"')}]);assert.deepEqual(outcomes(send),['refused']);await notSent('a click on Send',send);
    const enter=await act(tab,[{do:'press',ref:refOf(outline,'textbox "Comment"'),key:'Enter'}]);assert.deepEqual(outcomes(enter),['refused']);await notSent('Enter in its field',enter);
    await notSent('a submission the page starts',await act(tab,[{do:'click',ref:refOf(outline,'button "Continue"')}]));
  });

  await check('ACT BRIEF28A a popup a step opened is named in its step',async()=>{
    const page=await open(actUrl('popup',uid('popup')));
    const done=await act(page.tab,[{do:'click',ref:refOf(page.untrusted_content.outline,'button "Open window"')}]);
    assert.deepEqual(outcomes(done),['done']);const popups=done.steps[0].popups||[];
    assert.equal(popups.length,1,JSON.stringify(done.steps));opened.push(popups[0].tab);
    assert.ok([true,false,'pending'].includes(popups[0].controlled));
    // The short address, as chrome_tabs shows it (about:blank if the popup hadn't left it yet): never its query.
    assert.doesNotMatch(popups[0].untrusted_content.url,/case=|mode=child/,popups[0].untrusted_content.url);
  });

  // Last: they restart the service and Chrome.
  await check('ACT BRIEF28A a reference from another tab and references and lists from before a restart are refused for an action',async()=>{
    const first=uid('tab-a'),second=uid('tab-b'),a=await open(actUrl('plain',first)),b=await open(actUrl('plain',second));
    const press=refOf(a.untrusted_content.outline,'button "Press me"');
    const notDone=(name,result)=>{assert.ok(!result.ok||result.data.steps[0]?.outcome!=='done',name+': '+JSON.stringify(result).slice(0,600));};
    const cross=await act(b.tab,[{do:'click',ref:press}]);assert.deepEqual(outcomes(cross),['stale'],'tab A\'s reference in tab B');
    const listed=await seenOf();
    await lifecycle({fixture:'kill_service'});await lifecycle({fixture:'start_service'});
    await eventually(async()=>(await rpc('chrome_tabs',{})).ok,'the service is back',45000);
    notDone('after a service restart',await tool('do',{tab:a.tab,steps:[{do:'click',ref:press}]}));
    refusal(await tool('take',{tab:b.tab,seen:listed}),'stale_reference');
    const before=await seenOf(),fresh=await readTab(a.tab).catch(()=>null);
    const ref=fresh?refOf(fresh.untrusted_content.outline,'button "Press me"'):press;
    opened=[];await lifecycle('kill_chrome');await lifecycle('start_chrome');setTab(await restoreControl());
    notDone('after a Chrome restart',await tool('do',{tab:getTab(),steps:[{do:'click',ref}]}));
    notDone('the reference from before both restarts',await tool('do',{tab:getTab(),steps:[{do:'click',ref:press}]}));
    refusal(await tool('take',{tab:getTab(),seen:before}),'stale_reference');
    await delay(300);assert.equal(counts('act-press-'+first)+counts('act-press-'+second),0,'nothing was pressed');
  });

  fs.writeFileSync(OUT+'/cases.json',JSON.stringify(results.map(row=>({name:row.name,passed:!row.error,error:row.error?String(row.error.stack):undefined})),null,2));
  for(const row of results)await report(row.name,async()=>{if(row.error)throw row.error;});
}
