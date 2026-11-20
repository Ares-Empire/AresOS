// Brief 28, item 4 and group 14's time cases, through the real transports: the
// MCP proxy and the aresos command (call.py). They read with chrome_read and
// run in the core shard right after GROUP 1, while nothing is pending yet, so
// the approval of the last case is the first row of a result's pending page;
// they leave nothing pending or unacknowledged, and stay outside the named
// qualification inventory: group 14 is no qualification group. The test build
// holds replies back (prepare.mjs, fixture_hold_reader and fixture_hold_reply).
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {execFile,execFileSync} from 'node:child_process';
import {promisify} from 'node:util';
import {setTimeout as delay} from 'node:timers/promises';

const CALL_SECONDS=8,NOT_READ='time ran out; read this tab by itself';
// F7's result pages (efficiency-fixtures.mjs): a heading "Results page N".
const resultsPage=page=>'http://fixture.test:8765/?case=efficiency-f7&page='+page;
const run=promisify(execFile);

// One call through the proxy or the command; call.py times the call alone.
// Asynchronous, so the fixture server in this process keeps serving.
async function through(route,verb,args){
  const {stdout}=await run('python3',['control/chrome/ci/call.py',...(route==='command'?['--command']:[]),'--timed',verb,JSON.stringify(args)],{encoding:'utf8',env:{...process.env,GITHUB_ACTIONS:'true'},maxBuffer:16*1024*1024});
  const out=JSON.parse(stdout);
  fs.appendFileSync('/out/outline-time.jsonl',JSON.stringify({route,verb,args,seconds:out.seconds,ok:out.result.ok,
    reads:out.result.data?.reads?.map(entry=>({tab:entry.tab,error:entry.error,until_met:entry.until_met,characters:entry.characters})),
    error:out.result.error,pending:out.result.pending?.items})+'\n');
  return out;
}
const own=(result,tab,page)=>{
  assert.equal(result.ok,true,JSON.stringify(result));
  const entry=result.data.reads.find(row=>row.tab===tab);
  assert.ok(entry&&!entry.error,JSON.stringify(entry));
  assert.ok(entry.untrusted_content.outline.includes('Results page '+page),'tab '+tab+' answers with its own page '+page);
  return entry;
};

export async function outlineTime({call,nav,target,eventually,getTab}){
  // The service sets the hold right after the admin request it rides on (admin.py, service.py).
  const hold=async(command,args)=>{
    fs.rmSync('/out/fixture-hold.json',{force:true});
    const answer=JSON.parse(execFileSync('sudo',['-n','/usr/bin/python3','/workspace/control/chrome/ci/admin.py',JSON.stringify({fixture:'hold',command,arguments:args})],{encoding:'utf8'}));
    assert.equal(answer.ok,true,JSON.stringify(answer));
    assert.deepEqual(JSON.parse(fs.readFileSync('/out/fixture-hold.json','utf8')),{held:args.tab});
    return Date.now();
  };
  // Until a reader hold set at `at` has ended and the last reply it held has come.
  const holdOver=(at,{ms,duration})=>delay(Math.max(0,at+duration+ms+500-Date.now()));
  const tabs=[];let reserved=null;
  try{
    for(let page=1;page<=5;page++)tabs.push((await call('open',{url:resultsPage(page)})).untrusted_content.tab);
    for(const [index,tab] of tabs.entries())
      await eventually(async()=>(await call('wait',{tab,text:'Results page '+(index+1),timeout_ms:3000})).condition_met,'time tab '+(index+1)+' loaded');

    // until on a text that never comes: until_met false, inside the deadline.
    for(const route of ['proxy','command']){
      const {result,seconds}=await through(route,'outline',{tab:tabs[0],until:{text:'Never on this page '+route},timeout_ms:6000});
      const entry=own(result,tabs[0],1);
      assert.equal(entry.until_met,false);
      assert.ok(seconds<CALL_SECONDS,route+': '+seconds+' s');
      assert.ok(seconds>=5.5,route+': the wait ran to its timeout, '+seconds+' s');
    }
    console.log('GROUP 14 TIME until on a text that never comes PASS');

    // Five tabs, the third's reader holds its replies back past its share.
    const readerHold={tab:tabs[2],ms:4000,duration:5000},heldAt=await hold('fixture_hold_reader',readerHold);
    const five=await through('command','outline',{tabs});
    assert.equal(five.result.ok,true,JSON.stringify(five.result));
    assert.deepEqual(five.result.data.reads.map(row=>row.tab),tabs);
    assert.deepEqual(five.result.data.reads[2].error,{code:'not_read',message:NOT_READ});
    for(const index of [0,1,3,4])own(five.result,tabs[index],index+1);
    assert.ok(five.seconds<CALL_SECONDS,'five tabs: '+five.seconds+' s');
    // The next call on the same connection gets its own answer, while the
    // held reply is still out; then the held tab, after the reply came late.
    own((await through('proxy','outline',{tab:tabs[3]})).result,tabs[3],4);
    await holdOver(heldAt,readerHold);
    own((await through('proxy','outline',{tab:tabs[2]})).result,tabs[2],3);
    console.log('GROUP 14 TIME five tabs with one held reader PASS',five.seconds);

    // An extension that overruns its time: its reply to the outline is held
    // past the bridge's wait. The bridge gives it up, the read says not_read,
    // and the late reply is dropped by its id while the next call waits.
    await hold('fixture_hold_reply',{command:'outline',tab:tabs[1],ms:9000});
    const late=await through('proxy','outline',{tab:tabs[1]});
    assert.equal(late.result.ok,true,JSON.stringify(late.result));
    assert.deepEqual(late.result.data.reads[0].error,{code:'not_read',message:NOT_READ});
    assert.ok(late.seconds<CALL_SECONDS,'held reply: '+late.seconds+' s');
    own((await through('command','outline',{tab:tabs[4]})).result,tabs[4],5);
    own((await through('proxy','outline',{tab:tabs[1]})).result,tabs[1],2);
    console.log('GROUP 14 TIME a reply held past the bridge is given up and drained PASS',late.seconds);

    // An approval outstanding whose frame doesn't answer: the read still ends
    // inside its deadline, and the approval is unchecked, never refused.
    await nav('compose&id=time-approval');
    const prepared=await call('click',await target('Send'));assert.ok(prepared.approval,JSON.stringify(prepared));
    reserved=prepared.approval.operation_id;
    const checkHold={tab:getTab(),ms:6000,duration:5000,commands:['ready']},checkAt=await hold('fixture_hold_reader',checkHold);
    const blocked=await through('proxy','outline',{tab:tabs[4]});
    own(blocked.result,tabs[4],5);
    const row=blocked.result.pending.items.find(item=>item.operation_id===reserved);
    assert.ok(row,'nothing older is pending: '+JSON.stringify(blocked.result.pending));
    assert.equal(row.state,'reserved');assert.equal(row.validity,'unchecked',JSON.stringify(row));
    assert.ok(blocked.seconds<CALL_SECONDS,'approval check held: '+blocked.seconds+' s');
    // Dropping it checks it without time, as brief 20's tools do: after the hold.
    await holdOver(checkAt,checkHold);
    console.log('GROUP 14 TIME an approval whose frame does not answer is unchecked PASS',blocked.seconds);
  }finally{
    if(reserved){await call('drop',{operation_id:reserved});await call('notice_ack',{operation_id:reserved});}
    for(const tab of tabs)await call('close_tab',{tab,discard_unsaved:true});
  }
}
