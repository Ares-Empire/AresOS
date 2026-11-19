// Brief 28a, items 5 and 5a, in background.js' input (chrome_do's steps).
// "Time": input checks its command's time once more, as the last thing before
// the dispatch. An input whose time runs out during its setup dispatches
// nothing, answers `expired` and releases its hold; one whose time runs out
// after the dispatch finishes as before. Item 5a: the popups an input opened
// are named in its reply with their admission's outcome.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function inputFixture(){
  let code=fs.readFileSync('control/chrome/extension/background.js','utf8').replace("import {POLICY} from './policy.js';",'');
  code=code.slice(0,code.indexOf('async function connect()'));
  const context=vm.createContext({POLICY:{holdMs:100},chrome:{},URL,TextEncoder,performance,crypto:{randomUUID:()=> 'fixture-nonce'},setTimeout,clearTimeout});
  vm.runInContext(code,context);
  const run=source=>vm.runInContext(source,context);
  run(`excludedHosts=[];controlled.set(7,{epoch:'epoch'});globalThis.log=[];globalThis.posted=[];port={postMessage:message=>posted.push(message)};
    globalThis.factsDelay=0;globalThis.dispatchDelay=0;globalThis.reads=0;
    requireTab=async()=>({url:'https://fixture.test/',title:'Page'});
    safeDestination=()=>{};holdDefaults=async(tab,nonce)=>{log.push('hold '+nonce);};armedDocument=()=>{};expireDefaults=(tab,nonce)=>{log.push('release '+nonce);};
    finishFrames=async()=>{log.push('finish');return false;};collectSteps=async()=>{log.push('collect');return [];};observation=async()=>({});readyDialog=async()=>null;
    chrome.tabs={get:async()=>({active:false}),update:async()=>{log.push('activate');return {active:true};}};
    chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:'native',url:'https://fixture.test/'}]};
    globalThis.target={element:'e1',role:'button',name:'Go',states:{checked:false},box:{x:1,y:1,width:10,height:10}};
    facts=async()=>{log.push('facts');if(++reads===2&&factsDelay)await new Promise(resolve=>setTimeout(resolve,factsDelay));
      return {session,tab:7,control:'epoch',url:'https://fixture.test/',title:'Page',dialog:null,
      frames:[{frame:0,parent:-1,document:'doc',browser_document:'native',url:'https://fixture.test/',title:'Frame',target,form:null,selected_files:[],editable:[],embeds:[]}]};};
    chrome.tabs.sendMessage=async(tab,{command})=>{log.push(command);return {ok:true,data:command==='hit'?{hit:true}:{}};};
    pointer=async()=>{log.push('hit');return {x:2,y:2};};
    cdp=async(tab,method,parameters)=>{log.push(method+(parameters?.type?' '+parameters.type:''));if(dispatchDelay&&parameters?.type==='mousePressed')await new Promise(resolve=>setTimeout(resolve,dispatchDelay));return {};};`);
  const command=input=>`{name:'input',tab:7,reference:{session,tab:7,frame:0,document:'doc',element:'e1'},input:${JSON.stringify(input)}}`;
  return {run,log:()=>JSON.parse(run('JSON.stringify(log)')),
    dispatch:(input,expiresIn)=>run(`dispatch(${command(input)},performance.now()+${expiresIn})`),
    enqueue:(input,left)=>run(`enqueue({id:'native-1',time_left_ms:${left},command:${command(input)}})`)};
}
const dispatched=log=>log.filter(entry=>entry.startsWith('Input.')||['focus','select','install_file','resume'].includes(entry));
async function settled(f){for(let count=0;count<500&&!f.run('posted.length');count++)await new Promise(resolve=>setTimeout(resolve,2));return JSON.parse(f.run('JSON.stringify(posted[0])'));}

test('28a time: an input whose time runs out during its setup dispatches nothing, answers expired and releases its hold',async()=>{
  for(const input of [{verb:'click'},{verb:'fill',text:'x'},{verb:'press',key:'Enter'},{verb:'scroll',x:0,y:100},{verb:'check',checked:true}]){
    const f=inputFixture();f.run('factsDelay=60');
    await assert.rejects(f.dispatch(input,30),/^Error: expired: the time of this input ran out before its dispatch; nothing was dispatched$/,JSON.stringify(input));
    const log=f.log();
    assert.deepEqual(dispatched(log),[],'nothing reached the page: '+JSON.stringify(input));
    assert.ok(log.lastIndexOf('facts')<log.indexOf('finish'),'the last facts read came, then the hold was finished');
    assert.ok(log.includes('release fixture-nonce'),'the armed hold is released as after a refusal');
    assert.ok(!log.includes('collect'),'no page steps are collected for an input that never ran');
  }
});

test('28a time: the native answer is expired even after the tab was selected, and nothing else changes its meaning',async()=>{
  const f=inputFixture();f.run('factsDelay=60');
  f.enqueue({verb:'click'},30);
  const reply=await settled(f);
  assert.equal(f.log().includes('activate'),true,'the tab was selected first (an effect, but no input)');
  assert.deepEqual(reply,{id:'native-1',ok:false,error:'expired: the time of this input ran out before its dispatch; nothing was dispatched'});
  // Any other refusal after the selection keeps brief 20's meaning: it may have started.
  const g=inputFixture();g.run("facts=(()=>{const first=facts;return async(...args)=>{const value=await first(...args);if(reads===2)throw Error('stale_reference: element is gone; read again');return value;};})()");
  g.enqueue({verb:'click'},5000);
  const other=await settled(g);
  assert.match(other.error,/^unknown: Input may have started; .*stale_reference: element is gone/);
});

test('28a time: the check is the last thing before the dispatch, after the arming, the reveal and the last comparison',async()=>{
  const f=inputFixture();f.run('factsDelay=60');
  await assert.rejects(f.dispatch({verb:'click'},30),/^Error: expired:/);
  const log=f.log();
  assert.ok(log.indexOf('arm')<log.indexOf('reveal')&&log.indexOf('reveal')<log.lastIndexOf('facts'),JSON.stringify(log));
  assert.ok(!log.includes('hit'),'no hit test and no pointer event after the time ran out');
  // With time left, the same input runs once.
  const g=inputFixture();
  const done=await g.dispatch({verb:'click'},5000);
  assert.equal(done.dispatched,true);
  assert.deepEqual(dispatched(g.log()),['Input.dispatchMouseEvent mousePressed','Input.dispatchMouseEvent mouseReleased']);
});

test('28a time: an input whose time runs out after its dispatch finishes as before',async()=>{
  const f=inputFixture();f.run('dispatchDelay=80');
  const done=await f.dispatch({verb:'click'},40);
  assert.equal(done.dispatched,true,'nothing is cut short after the dispatch');
  const log=f.log();
  assert.deepEqual(dispatched(log),['Input.dispatchMouseEvent mousePressed','Input.dispatchMouseEvent mouseReleased']);
  assert.ok(log.indexOf('finish')>log.indexOf('Input.dispatchMouseEvent mouseReleased')&&log.includes('collect'),'the hold and the page steps run as in brief 20');
  // A command without a time (an approved input) never meets the check.
  const g=inputFixture();g.run('factsDelay=40');
  assert.equal((await g.run(`dispatch({name:'input',tab:7,reference:{session,tab:7,frame:0,document:'doc',element:'e1'},input:{verb:'click'}})`)).dispatched,true);
});

// --- item 5a: the popups a step opened -----------------------------------------

function popupFixture(){
  const f=inputFixture();
  f.run(`globalThis.admitted=[];
    take=(tab,opener)=>{admitted.push([tab,opener]);
      if(tab===21)return Promise.reject(Error('refused: popup control requires its opener in the Claude group'));
      if(tab===22)return Promise.reject(Error('debugger attach failed'));
      if(tab===23)return new Promise(()=>{});
      return Promise.resolve({tab,session,group:1});};
    controlled.set(8,{epoch:'other'});
    globalThis.popupUrls={20:'https://fixture.test/popup?q=red',21:'https://fixture.test/refused',22:'https://fixture.test/failed',23:'about:blank',24:'https://claude.ai/chat'};
    chrome.tabs.get=async tab=>tab===7?{active:true}:{id:tab,url:popupUrls[tab]};
    globalThis.opening=[];cdp=(previous=>async(tab,method,parameters)=>{const value=await previous(tab,method,parameters);
      if(parameters?.type==='mouseReleased')for(const [source,frame,popup] of opening)createdTarget({sourceTabId:source,sourceFrameId:frame,tabId:popup});return value;})(cdp);`);
  return f;
}
const named=reply=>JSON.parse(JSON.stringify(reply.popups||[]));

test('28a 5a: a click names its popups with their admission: admitted, refused, failed, pending, two from one click',async()=>{
  const f=popupFixture();
  f.run('opening=[[7,0,20],[7,0,21],[7,0,22],[7,0,23]]');
  const reply=await f.dispatch({verb:'click'},5000);
  assert.deepEqual(named(reply),[{tab:20,controlled:true,url:'https://fixture.test/popup?q=red'},{tab:21,controlled:false,url:'https://fixture.test/refused'},
    {tab:22,controlled:false,url:'https://fixture.test/failed'},{tab:23,controlled:'pending',url:'about:blank'}],'the service writes the short form and the no mark');
  assert.deepEqual(JSON.parse(f.run('JSON.stringify(admitted.map(([tab,opener])=>[tab,opener.tab]))')),[[20,7],[21,7],[22,7],[23,7]],'admission runs as before, for every one');
  assert.equal(f.run('popupWatches.size'),0,'the window ended with the hold');
  // Two popups of one click, one of them a page Claude may never read.
  const g=popupFixture();g.run('opening=[[7,0,20],[7,0,24]]');
  assert.deepEqual(named(await g.dispatch({verb:'click'},5000)).map(popup=>[popup.tab,popup.controlled]),[[20,true],[24,true]]);
});

test('28a 5a: a popup that can\'t be tied to the step isn\'t named: another opener, another frame, after the hold, no input',async()=>{
  const f=popupFixture();
  f.run('opening=[[8,0,20],[7,3,21],[7,undefined,22]]');
  const reply=await f.dispatch({verb:'click'},5000);
  assert.deepEqual(named(reply),[],'another tab, another frame, and an event without its frame stay in the tab list');
  assert.equal('popups' in reply,false);
  // After the reply the window is closed: a later popup of the same tab is admitted, not named anywhere.
  await f.run('createdTarget({sourceTabId:7,sourceFrameId:0,tabId:25})');
  assert.equal(f.run('popupWatches.size'),0);
  // A refused input watches nothing.
  const g=popupFixture();g.run("factsDelay=60;opening=[[7,0,20]]");
  await assert.rejects(g.dispatch({verb:'click'},30),/^Error: expired:/);
  assert.equal(g.run('popupWatches.size'),0);assert.equal(g.run('admitted.length'),0);
});
