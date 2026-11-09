import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture(){
  const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);
  const registrations=[],rules=[];
  const chrome={scripting:{getRegisteredContentScripts:async()=>[],registerContentScripts:async scripts=>registrations.push(...scripts)},
    declarativeNetRequest:{getSessionRules:async()=>[],updateSessionRules:async value=>rules.push(value)}};
  let source=fs.readFileSync('control/chrome/extension/background.js','utf8').replace("import {POLICY} from './policy.js';",'');
  source=source.slice(0,source.indexOf('async function connect()'));
  const context=vm.createContext({POLICY:policy,chrome,crypto:{randomUUID:()=> 'fixture-session'},URL,Promise,setTimeout,TextEncoder,btoa:value=>Buffer.from(value,'binary').toString('base64')});
  vm.runInContext(source,context);
  return {run:code=>vm.runInContext(code,context),registrations,rules};
}

test('owner exclusions are mandatory and the private audit switch needs no page access',async()=>{
  const f=fixture();
  await assert.rejects(f.run("dispatch({name:'tabs'})"),/owner-only excluded-sites/);
  assert.equal((await f.run("dispatch({name:'audit',enabled:true})")).recording,true);
  await f.run("dispatch({name:'configure',excluded_hosts:['approval.test']})");
  for(const address of ['https://approval.test/','https://approval.test./','https://sub.approval.test./','https://claude.ai./']){
    assert.throws(()=>f.run(`safeURL(${JSON.stringify(address)})`),/approval\/settings/);
  }
  assert.equal(f.run("safeURL('https://fixture.test/')"),'https://fixture.test/');
  assert.equal(f.registrations.length,2);
  for(const script of f.registrations){
    assert.equal(script.runAt,'document_start');
    assert.ok(script.excludeMatches.includes('https://*.approval.test/*'));
    assert.ok(script.excludeMatches.includes('https://*.approval.test./*'));
  }
});

test('oversize browser replies distinguish a refused read from an unknown input outcome',()=>{
  const f=fixture();f.run('globalThis.sent=[];port={postMessage:value=>sent.push(value)}');
  f.run("respond({id:'read',ok:true,data:'x'.repeat(33*1024*1024)})");
  assert.match(f.run('sent[0].error'),/^refused:/);
  f.run("effectStarted=true;respond({id:'input',ok:true,data:'x'.repeat(33*1024*1024)})");
  assert.match(f.run('sent[1].error'),/^unknown:/);
});


test('native dialog reading refuses an excluded opener before returning its text',async()=>{
  const f=fixture();await f.run("dispatch({name:'configure',excluded_hosts:['approval.test']})");
  f.run("chrome.tabs={get:async()=>({url:'http://fixture.test/',groupId:1})};groupId=1;controlled.set(7,{epoch:'private'});dialogs.set(7,{frame_url:'http://approval.test/',frame:2,text:'EXCLUDED_DIALOG_SENTINEL'})");
  await assert.rejects(f.run("dispatch({name:'read',tab:7})"),/approval\/settings/);
});

test('keyboard events carry native codes and printable text for letters and shortcuts',()=>{
  const f=fixture();
  assert.equal(f.run("keyboard('x').text"),'x');assert.equal(f.run("keyboard('x').code"),'KeyX');
  assert.equal(f.run("keyboard('Ctrl+A').text"),undefined);assert.equal(f.run("keyboard('Ctrl+A').windowsVirtualKeyCode"),65);
  assert.equal(f.run("keyboard('#').code"),'Digit3');assert.equal(f.run("keyboard('#').modifiers"),8);assert.equal(f.run("keyboard('#').windowsVirtualKeyCode"),51);
  assert.equal(f.run("keyboard('Space').text"),' ');assert.equal(f.run("keyboard('Cmd+Enter').modifiers"),4);
});

test('a child modal interrupts a blocked finish without letting a later dispatch reuse its completion',async()=>{
  const f=fixture();
  f.run("globalThis.messages=[];globalThis.reply=null;chrome.tabs={sendMessage:(tab,message)=>{messages.push(message);return new Promise(resolve=>{reply=resolve;});}}");
  const pending=f.run("finishFrames(7,[{frame:0},{frame:2}],'epoch','first')");
  f.run("dialogs.set(7,{id:'child'});wakeDialog(7)");await pending;
  assert.equal(f.run('messages.length'),1);assert.equal(f.run('messages[0].dispatch_nonce'),'first');
  assert.equal(f.run('dialogWake.size'),0);f.run("reply({ok:true,data:{finished:true}})");
});

test('a modal from focus refuses the rest of an input instead of blocking the serial queue',async()=>{
  const f=fixture();f.run("controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';chrome.tabs={sendMessage:()=>new Promise(()=>{})}");
  const pending=f.run("content(7,0,'focus',{element:'e1'})");f.run('wakeDialog(7)');
  await assert.rejects(pending,/unknown: a page dialog interrupted input handling/);assert.equal(f.run('dialogWake.size'),0);
});
test('overlapping private dialog waits wake independently and dispose only themselves',async()=>{
  const f=fixture();const first=f.run('globalThis.first=waitDialog(7);first.promise'),second=f.run('globalThis.second=waitDialog(7);second.promise');
  f.run('first.dispose();wakeDialog(7)');assert.equal((await second).dialog,true);f.run('second.dispose()');assert.equal(f.run('dialogWake.size'),0);
  void first;
});

test('a stale approved dialog opening never accepts the different dialog that replaced it',async()=>{
  function setup(){
    const f=fixture();
    f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch',inputNonce:'input-nonce'});dispatchEpoch='epoch';globalThis.frames=[];globalThis.accepted=[];chrome.webNavigation={getAllFrames:()=>new Promise(resolve=>frames.push(resolve))};chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}},sendCommand:async(source,method,params)=>{if(method==='Page.handleJavaScriptDialog')accepted.push(dialogs.get(7)?.text);return {};}};confirmationPlans.set(7,{operation:'approved-operation',browser_document:'doc',expected:{kind:'confirm',text:'Delete approved branch?',frame_url:'http://fixture.test/',button:'OK',frame:0},matched:[]});");
    const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
    f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
    return f;
  }
  const valid=setup();
  const current=valid.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete approved branch?',url:'http://fixture.test/'})");
  valid.run("frames[0]([{frameId:0,documentId:'doc',url:'http://fixture.test/'}])");await current;
  assert.deepEqual(Array.from(valid.run('accepted')),['Delete approved branch?'],'the unchanged exact dialog remains covered');

  const stale=setup();
  const original=stale.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete approved branch?',url:'http://fixture.test/'})");
  const closed=stale.run("onEvent({tabId:7},'Page.javascriptDialogClosed',{})");
  stale.run('frames[1]([])');await closed;
  const different=stale.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete DIFFERENT branch?',url:'http://fixture.test/'})");
  stale.run("frames[0]([{frameId:0,documentId:'doc',url:'http://fixture.test/'}])");await original;
  assert.deepEqual(Array.from(stale.run('accepted')),[],'the stale matching event must not accept the DIFFERENT current dialog');
  assert.equal(stale.run('dialogs.get(7).text'),'Delete DIFFERENT branch?');
  assert.equal(stale.run('confirmationPlans.get(7).expected.text'),'Delete approved branch?','stale evidence must not consume the approval');
  stale.run("frames[2]([{frameId:0,documentId:'doc',url:'http://fixture.test/'}])");await different;
  assert.deepEqual(Array.from(stale.run('accepted')),[],'the different dialog stays unaccepted after its own lookup');
});

test('a keydown modal stops the remaining CDP input instead of waiting for a lost opening wake',{timeout:1000},async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'button',name:'Continue'},form:null}]});content=async()=>({});globalThis.inputCalls=[];chrome.debugger={sendCommand:(source,method,parameters)=>{inputCalls.push(parameters.type);if(parameters.type==='keyDown')Promise.resolve().then(()=>{dialogs.set(7,{kind:'confirm'});wakeDialog(7)});return new Promise(()=>{});}};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})"),/page dialog interrupted the input sequence/);
  assert.deepEqual(Array.from(f.run('inputCalls')),['keyDown'],'no keyUp or later text may enter the pending dialog');
  assert.equal(f.run('dialogWake.size'),0);
});
