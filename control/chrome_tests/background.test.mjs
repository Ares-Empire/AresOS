import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

function fixture(){
  const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);
  const registrations=[],rules=[];
  const chrome={tabs:{get:async()=>({active:false}),update:async()=>({})},scripting:{getRegisteredContentScripts:async()=>[],registerContentScripts:async scripts=>registrations.push(...scripts)},
    declarativeNetRequest:{getSessionRules:async()=>[],updateSessionRules:async value=>rules.push(value)}};
  let source=fs.readFileSync('control/chrome/extension/background.js','utf8').replace("import {POLICY} from './policy.js';",'');
  source=source.slice(0,source.indexOf('async function connect()'));
  const context=vm.createContext({POLICY:policy,chrome,crypto:{randomUUID:()=> 'fixture-session'},URL,Promise,setTimeout,TextEncoder,btoa:value=>Buffer.from(value,'binary').toString('base64')});
  vm.runInContext(source,context);
  return {run:code=>vm.runInContext(code,context),registrations,rules};
}

function stepFixture(){
  const f=fixture();
  f.run("excludedHosts=[];globalThis.forwarded=[];globalThis.poll=[];globalThis.commands=[];controlled.set(7,{epoch:'epoch',inputNonce:'nonce'});port={postMessage:message=>forwarded.push(message)};chrome.runtime={id:'fixture-extension',getURL:path=>'chrome-extension://fixture-extension/'+path,onMessage:{addListener:listener=>{globalThis.runtimeListener=listener}}};chrome.webNavigation={getAllFrames:async()=>[{frameId:2,url:'http://fixture.test/new-document'}]};chrome.tabs={sendMessage:async(tab,message)=>{commands.push(message.command);return {ok:true,data:message.command==='steps'?poll:{}}}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run(source.slice(source.indexOf('chrome.runtime.onMessage.addListener('),source.indexOf('chrome.tabs.onUpdated.addListener(')));
  f.run("globalThis.notify=(step,generation='epoch',sender={id:'fixture-extension',tab:{id:7},frameId:2,url:'http://fixture.test/old-document'})=>{let result;runtimeListener({event:'held_step',step,generation},sender,value=>{result=value});return result;}");
  return f;
}

const heldStep=(id='h1')=>({id,document:'old-document',element:'e1',submitter:null,kind:'activation_unknown',cancellable:false,label:'Delete'});

function lifecycleFixture(){
  const f=fixture();f.run("const nativeTimer=setTimeout;setTimeout=(callback,delay)=>{const timer=nativeTimer(callback,delay);timer.unref?.();return timer};excludedHosts=[];groupId=1;globalThis.lifecycleCalls=[];chrome.runtime={getURL:path=>'chrome-extension://fixture/'+path};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{}};chrome.webNavigation={getAllFrames:async()=>[]};chrome.tabs={get:async()=>({url:'http://fixture.test/',windowId:1,index:0,groupId:1}),group:async()=>{lifecycleCalls.push('group');return 1},ungroup:async()=>{lifecycleCalls.push('ungroup')},move:async()=>{}};chrome.tabGroups={update:async()=>{}};chrome.debugger={attach:async()=>{},detach:async()=>{lifecycleCalls.push('detach')},sendCommand:async(source,method,parameters)=>{lifecycleCalls.push(method);return {};}};");return f;
}
async function spin(f,expression){for(let count=0;count<200&&!f.run(expression);count++)await Promise.resolve();assert.equal(!!f.run(expression),true,expression);}

test('Stop cancels a tab admission still awaiting attach without grouping it',async()=>{
  const f=lifecycleFixture();f.run('chrome.debugger.attach=()=>new Promise(resolve=>{globalThis.finishAttach=resolve})');
  const pending=f.run('take(7)');await spin(f,"typeof finishAttach==='function'");await f.run('stop()');f.run('finishAttach()');
  await assert.rejects(pending,/control stopped/);assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('group')"),false);assert.equal(f.run("lifecycleCalls.includes('detach')"),true);
});

test('a popup whose identity arrives after Stop cannot resurrect control',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'parent',contexts:new Map(),documents:new Map(),installing:new Set()});chrome.debugger.getTargets=()=>new Promise(resolve=>{globalThis.popupIdentity=resolve})");
  const pending=f.run("preloadEvent({tabId:7},'Target.attachedToTarget',{sessionId:'popup-session',targetInfo:{type:'page',targetId:'popup'}})");
  await spin(f,"typeof popupIdentity==='function'");await f.run('stop()');f.run("popupIdentity([{id:'popup',tabId:8}])");await pending;
  assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('Runtime.runIfWaitingForDebugger')"),false);assert.equal(f.run("lifecycleCalls.includes('group')"),false);
});

test('Stop during blocked native cleanup returns pending and preserves handles until restoration',async()=>{
  const f=lifecycleFixture();f.run("globalThis.clockTimers=[];setTimeout=(callback,delay)=>{clockTimers.push({callback,delay});return 0};controlled.set(7,{epoch:'epoch'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,contexts:new Map(),documents:new Map([['main',{cleanup:'restore'}]]),installing:new Set()});chrome.debugger.sendCommand=(source,method)=>{lifecycleCalls.push(method);return method==='Runtime.callFunctionOn'?new Promise(resolve=>{globalThis.unblockCleanup=resolve}):Promise.resolve({})};");
  const stopped=f.run('stop()');await spin(f,"typeof unblockCleanup==='function'");assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('detach')"),false);assert.equal(f.run("lifecycleCalls.includes('ungroup')"),false);
  f.run('clockTimers.find(timer=>timer.delay===1000).callback()');const result=await stopped;assert.equal(result.stopped,true);assert.equal(result.cleanup_pending,1);assert.equal(f.run('preloadTargets.size'),1);
  await assert.rejects(f.run('take(7)'),/cleanup is still pending/);
  f.run('unblockCleanup({})');await spin(f,"releasing.size===0");assert.equal(f.run("lifecycleCalls.includes('detach')"),true);assert.equal(f.run("lifecycleCalls.includes('ungroup')"),true);
});

test('a POST document arriving during reload inspection is never reloaded',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.topDocument='get';globalThis.reloads=0;documentMethods.set('[7,0]',{document:'get',method:'GET'});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:topDocument,url:'http://fixture.test/'}]};cdp=async(tab,method)=>{if(method==='Page.getFrameTree')return {frameTree:{frame:{url:'http://fixture.test/',loaderId:topDocument}}};reloads++};content=async()=>{topDocument='post';documentMethods.set('[7,0]',{document:'post',method:'POST'});return {unsaved:false,playing:false};};");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7,reload_taken_tab:true})"),/form submission/);assert.equal(f.run('reloads'),0);
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'reload'})"),/form submission/);assert.equal(f.run('reloads'),0);
});

test('a failed live native restoration stays grouped until that context is destroyed',async()=>{
  const f=lifecycleFixture();f.run("globalThis.clockTimers=[];setTimeout=(callback,delay)=>{clockTimers.push({callback,delay});return 0};controlled.set(7,{epoch:'epoch'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,contexts:new Map([[1,{id:1,uniqueId:'main',origin:'http://fixture.test/'}]]),scripts:new Map(),documents:new Map([['main',{main:'main',document:'document',cleanup:'restore'}]]),installing:new Set()});chrome.debugger.sendCommand=async(source,method)=>{lifecycleCalls.push(method);return {result:{value:false}}};");
  const pending=f.run('release(7)');await spin(f,"preloadTargets.get('[7,null]').cleanupWaiters?.size===1");
  assert.equal(f.run("lifecycleCalls.includes('ungroup')"),false);assert.equal(f.run('controlled.size'),0);
  f.run('clockTimers.find(timer=>timer.delay===1000).callback()');assert.equal((await pending).cleanup_pending,true);
  await f.run("preloadEvent({tabId:7},'Runtime.executionContextDestroyed',{executionContextId:1})");await spin(f,'releasing.size===0');assert.equal(f.run("lifecycleCalls.includes('ungroup')"),true);
});

test('only exact current-document completion or trusted address/link navigation establishes GET',()=>{
  const f=fixture();f.run("chrome.runtime={getURL:path=>'chrome-extension://fixture/'+path};chrome.webRequest={onCompleted:{addListener:listener=>{globalThis.completed=listener}}};chrome.webNavigation={onCommitted:{addListener:listener=>{globalThis.committed=listener}}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('// Passive, exact-document'),source.indexOf('chrome.debugger.onEvent.addListener(')));
  f.run("committed({tabId:7,frameId:0,documentId:'get',transitionType:'typed'});completed({tabId:7,frameId:0,type:'main_frame',documentId:'older',method:'POST'})");assert.equal(f.run("documentMethods.get('[7,0]').document"),'get');
  f.run("committed({tabId:7,frameId:0,documentId:'post',transitionType:'form_submit'});completed({tabId:7,frameId:0,type:'main_frame',documentId:'get',method:'GET'})");assert.equal(f.run("documentMethods.has('[7,0]')"),false);
  f.run("completed({tabId:7,frameId:0,type:'main_frame',documentId:'post',method:'POST'})");assert.equal(f.run("documentMethods.get('[7,0]').method"),'POST');
  f.run("committed({tabId:7,frameId:0,documentId:'next',transitionType:'link'});completed({tabId:7,frameId:0,type:'main_frame',documentId:'post',method:'POST'})");assert.equal(f.run("documentMethods.get('[7,0]').document"),'next');
  f.run("committed({tabId:7,frameId:0,documentId:'keyword',transitionType:'keyword'})");assert.equal(f.run("documentMethods.has('[7,0]')"),false,'an address-bar search could itself use POST');
  f.run("committed({tabId:7,frameId:0,documentId:'restored',transitionType:'typed',transitionQualifiers:['forward_back']})");assert.equal(f.run("documentMethods.has('[7,0]')"),false,'restoration is not proof of a fresh GET');
});

test('a destroyed child target wakes failed-restoration cleanup while a live detach stays pending',async()=>{
  for(const live of [false,true]){
    const f=lifecycleFixture();f.run("globalThis.clockTimers=[];setTimeout=(callback,delay)=>{clockTimers.push({callback,delay});return 0};controlled.set(8,{epoch:'epoch'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'parent',contexts:new Map(),scripts:new Map(),documents:new Map(),installing:new Set()});preloadTargets.set('[7,\"child\"]',{source:{tabId:7,sessionId:'child'},targetId:'child-target',tab:8,contexts:new Map([[1,{id:1,uniqueId:'main',origin:'http://fixture.test/'}]]),scripts:new Map(),documents:new Map([['main',{main:'main',document:'document',cleanup:'restore'}]]),installing:new Set()});chrome.debugger.sendCommand=async()=>({result:{value:false}});");
    f.run(`chrome.debugger.getTargets=async()=>${live?"[{id:'child-target'}]":"[]"}`);
    const pending=f.run('release(8)');await spin(f,"preloadTargets.get('[7,\"child\"]').cleanupWaiters?.size===1");
    await f.run("preloadEvent({tabId:7},'Target.detachedFromTarget',{sessionId:'child'})");
    if(live){assert.equal(f.run('releasing.has(8)'),true,'a live detached page has not proved native restoration');const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('function removedTab('),source.indexOf('chrome.tabs.onRemoved.addListener(')));f.run('removedTab(8)');}
    await pending;assert.equal(f.run('releasing.has(8)'),false);assert.equal(f.run('preloadTargets.has(\'[7,"child"]\')'),false);
  }
});

test('owner exclusions are mandatory and the private audit switch needs no page access',async()=>{
  const f=fixture();
  await assert.rejects(f.run("dispatch({name:'tabs'})"),/owner-only excluded-sites/);
  assert.equal((await f.run("dispatch({name:'audit',enabled:true})")).recording,true);
  await f.run("dispatch({name:'configure',excluded_hosts:['approval.test']})");
  for(const address of ['https://approval.test/','https://approval.test./','https://sub.approval.test./','https://claude.ai./']){
    assert.throws(()=>f.run(`safeURL(${JSON.stringify(address)})`),/approval\/settings/);
  }
  assert.equal(f.run("safeURL('https://fixture.test/')"),'https://fixture.test/');
  assert.equal(f.registrations.length,1);
  for(const script of f.registrations){
    assert.equal(script.world,'ISOLATED');assert.deepEqual(Array.from(script.js),['context.js']);
    assert.equal(script.runAt,'document_start');
    assert.ok(script.excludeMatches.includes('https://*.approval.test/*'));
    assert.ok(script.excludeMatches.includes('https://*.approval.test./*'));
  }
  assert.doesNotMatch(fs.readFileSync('control/chrome/extension/context.js','utf8'),/\b(?:window|document|globalThis|addEventListener|preventDefault|stopPropagation)\b/);
  assert.equal(JSON.parse(fs.readFileSync('control/chrome/extension/manifest.json')).content_scripts,undefined);
});

test('startup evaluates only fixed bundles in authenticated private contexts before resuming',async()=>{
  const f=fixture();f.run("globalThis.startup=[];chrome.runtime={getURL:path=>'chrome-extension://fixture/'+path};chrome.debugger={sendCommand:async(source,method,parameters)=>{startup.push({source,method,parameters});if(method==='Debugger.setBreakpointByUrl')return {breakpointId:'inert-breakpoint'};if(method==='Runtime.evaluate')return parameters.returnByValue?{result:{value:'private-document'}}:{result:{objectId:'private-cleanup'}};if(method==='Runtime.callFunctionOn')return parameters.returnByValue?{result:{value:'private-document'}}:{result:{objectId:'relay'}};if(method==='DOM.describeNode')return {node:{backendNodeId:1}};if(method==='DOM.resolveNode')return {object:{objectId:'isolated-relay'}};return {};}};preloadBundle=Promise.resolve(['// guard fixture','// reader fixture','// wrapper fixture']);controlled.set(7,{epoch:'epoch'});");
  await f.run('prepareTarget({tabId:7})');
  for(const context of [{id:1,uniqueId:'main',origin:'http://fixture.test',auxData:{isDefault:true,frameId:'frame'}},{id:2,uniqueId:'isolated',origin:'chrome-extension://fixture',auxData:{isDefault:false,frameId:'frame'}}])await f.run(`preloadEvent({tabId:7},'Runtime.executionContextCreated',{context:${JSON.stringify(context)}})`);
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'bootstrap',executionContextId:2,url:'chrome-extension://fixture/context.js'})");
  await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:['inert-breakpoint'],callFrames:[{location:{scriptId:'bootstrap'}}]})");
  const commands=Array.from(f.run('startup'));
  const evaluated=commands.filter(value=>value.method==='Runtime.evaluate');
  assert.deepEqual(evaluated.map(value=>value.parameters.uniqueContextId),['isolated','main']);
  assert.ok(evaluated.every(value=>value.parameters.disableBreaks===true));
  assert.match(evaluated[0].parameters.expression,/guard fixture/);assert.match(evaluated[0].parameters.expression,/reader fixture/);
  assert.equal(commands.at(-1).method,'Debugger.resume');assert.equal(f.run("isPreloaded(7,'private-document')"),true);
  await f.run("preloadEvent({tabId:7},'Runtime.executionContextsCleared',{})");assert.equal(f.run("isPreloaded(7,'private-document')"),false);
});

test('taken-tab first input defers dirty or playing GET documents and refuses POST without a request',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.reloaded=0;globalThis.reloadChecks=0;content=async()=>{reloadChecks++;return {unsaved:true,playing:true}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'}]};cdp=async(tab,method,parameters)=>{if(method==='Page.getFrameTree')return {frameTree:{frame:{loaderId:'loader',url:'http://fixture.test/'}}};assertedMethod=method;reloaded++;globalThis.reloadParameters=parameters;};globalThis.assertedMethod=null;");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7,reload_taken_tab:true})"),/request method is unknown/);
  f.run("documentMethods.set('[7,0]',{document:'doc',method:'POST'})");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7,reload_taken_tab:true})"),/form submission/);assert.equal(f.run('reloaded'),0);assert.equal(f.run('reloadChecks'),0);
  f.run("documentMethods.set('[7,0]',{document:'doc',method:'GET'})");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/reload_required:.*unsaved.*playing/);assert.equal(f.run('reloaded'),0);
  assert.equal((await f.run("dispatch({name:'prepare_control',tab:7,reload_taken_tab:true})")).reloaded,true);assert.equal(f.run('reloaded'),1);assert.equal(f.run('assertedMethod'),'Page.reload');
  assert.equal(f.run('reloadParameters.loaderId'),'loader');
  f.run('facts=async()=>({needs_reload:false})');assert.equal((await f.run("dispatch({name:'prepare_control',tab:7})")).ready,true);assert.equal(f.run('reloaded'),1);
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

test('Stop during finish keeps the handler completion uncertain',async()=>{
  const f=fixture();f.run("chrome.tabs={sendMessage:()=>new Promise(()=>{})}");
  const pending=f.run("finishFrames(7,[{frame:0,browser_document:'document'}],'epoch','nonce')");
  f.run("wakeDialog(7,{interrupted:true})");
  assert.equal(await pending,true);assert.equal(f.run('dialogWake.size'),0);
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
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'button',name:'Continue'},form:null}]});content=async()=>({});chrome.tabs={get:async()=>({active:false}),update:async()=>({})};globalThis.inputCalls=[];chrome.debugger={sendCommand:(source,method,parameters)=>{inputCalls.push(parameters.type);if(parameters.type==='keyDown')Promise.resolve().then(()=>{dialogs.set(7,{kind:'confirm'});wakeDialog(7)});return new Promise(()=>{});}};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})"),/page dialog interrupted the input sequence/);
  assert.deepEqual(Array.from(f.run('inputCalls')),['keyDown'],'no keyUp or later text may enter the pending dialog');
  assert.equal(f.run('dialogWake.size'),0);
});

test('answering a dialog collects a resumed handler submission without sending it',async()=>{
  const source=fs.readFileSync('control/chrome_tests/page.test.mjs','utf8');
  const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);
  const createPage=Function('fs','vm','assert','policy',source.slice(source.indexOf('function fixture('),source.indexOf("\ntest('"))+'\nreturn fixture;')(fs,vm,assert,policy);
  const page=createPage(),form=new page.HTMLFormElement();page.arm(form,form);
  page.guard.arm({generation:'epoch',dispatch_nonce:'nonce',config:policy,target:page.id(form),form:page.id(form)});
  const f=fixture();
  f.run('globalThis').onAnswer=()=>form.submit();
  f.run('globalThis').pageReply=async message=>{
    if(message.command==='finish_input')await page.guard.finish(message.generation,message.dispatch_nonce);
    return {ok:true,data:message.command==='steps'?page.guard.steps():{finished:true}};
  };
  f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'epoch',inputNonce:'nonce'});globalThis.commands=[];chrome.tabs={get:async()=>({url:'http://fixture.test/',groupId:1}),sendMessage:(tab,message)=>{commands.push(message.command);return pageReply(message)}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,url:'http://fixture.test/'}]};chrome.debugger={sendCommand:async(source,method)=>{if(method==='Page.handleJavaScriptDialog'){onAnswer();dialogs.delete(7)}return {};}};dialogs.set(7,{id:'dialog',frame:0,frame_url:'http://fixture.test/',kind:'confirm',text:'Continue?',button:'OK'});globalThis.expected={session,tab:7,control:'epoch',url:'http://fixture.test/',dialog:dialogs.get(7)};");
  const result=await f.run("dispatch({name:'dialog',tab:7,binding:expected,input:{accept:true},operation:'approved-dialog'})");
  assert.equal(page.arrivals.length,0,'the resumed handler submission stays held until its own approval');
  assert.equal(result.steps.length,1);assert.equal(result.steps[0].kind,'native_submit');
  assert.equal(result.steps[0].document,'document-1');assert.equal(result.steps[0].frame,0);
  assert.ok(Array.from(f.run('commands')).includes('steps'),'answering the dialog must collect the new held step');
});

test('a private unknown activation survives its source document and is forwarded once',async()=>{
  const f=stepFixture(),step=heldStep();
  assert.equal(f.run(`notify(${JSON.stringify(step)}).received`),true);
  assert.equal(f.run(`notify(${JSON.stringify(step)}).received`),true);
  assert.equal(f.run('forwarded.length'),1,'repeat notification is one durable observation');
  const result=await f.run('collectSteps(7)');
  assert.equal(result.length,1);assert.equal(result[0].kind,'activation_unknown');
  assert.equal(result[0].document,'old-document','replacement document cannot replace the source identity');
  assert.equal(result[0].frame,2);assert.equal(f.run('controlled.get(7).steps.size'),1,'collection is not a durable acknowledgement');
  await f.run(`dispatch({name:'ack_steps',tab:7,steps:${JSON.stringify(result)}})`);
  assert.equal(f.run('controlled.get(7).steps.size'),0);
  assert.equal(f.run(`notify(${JSON.stringify(step)}).received`),true);
  assert.equal(f.run('controlled.get(7).steps.size'),0,'late notification cannot requeue a collected step');
  assert.equal(f.run('forwarded.length'),1);
});

test('private step notifications and later polling deduplicate by source document and frame',async()=>{
  const f=stepFixture(),step=heldStep();f.run(`notify(${JSON.stringify(step)})`);f.run(`poll=[${JSON.stringify(step)}]`);
  const result=await f.run('collectSteps(7)');assert.equal(result.length,1);
  assert.equal(result[0].id,'h1');assert.equal(f.run('forwarded.length'),1);
});

test('step observations require the extension sender and current tab generation',()=>{
  const f=stepFixture(),step=JSON.stringify(heldStep());
  assert.equal(f.run(`notify(${step},'epoch',{id:'other-extension',tab:{id:7},frameId:2})`),undefined);
  for(const call of [`notify(${step},'wrong-generation')`,`notify(${step},'epoch',{id:'fixture-extension',tab:{id:8},frameId:2})`,`notify(${step},'epoch',{id:'fixture-extension',tab:{id:7},frameId:2.5})`,`notify({...${step},kind:'resume'})`,`notify({...${step},document:null})`])assert.equal(f.run(call).received,false,call);
  assert.equal(f.run('forwarded.length'),0);assert.equal(f.run('controlled.get(7).steps'),undefined);
  assert.equal(f.run(`notify({...${step},frame:999}).received`),true);
  assert.equal(f.run('forwarded[0].step.frame'),2,'sender frame overrides any payload frame');
});

test('combined queued and polled steps stay capped with one truthful overflow warning',async()=>{
  const f=stepFixture();
  for(let index=0;index<600;index++)f.run(`notify(${JSON.stringify(heldStep('h'+index))})`);
  assert.equal(f.run('controlled.get(7).steps.size'),513);assert.equal(f.run('forwarded.length'),513);
  assert.equal(f.run("[...controlled.get(7).steps.values()].filter(step=>step.id.startsWith('overflow-')).length"),1);
  f.run(`poll=${JSON.stringify(Array.from({length:600},(_,index)=>heldStep('h'+index)))}`);
  const result=await f.run('collectSteps(7)');
  assert.ok(result.length<=513,'the polled path must not bypass the same response bound');
  assert.equal(result.filter(step=>step.id.startsWith('overflow-')).length,1);
  assert.equal(result.find(step=>step.id.startsWith('overflow-')).kind,'activation_unknown');
  assert.equal(f.run('controlled.get(7).steps.size'),513,'bounded observations stay queued until committed results are acknowledged');
  await f.run(`dispatch({name:'ack_steps',tab:7,steps:${JSON.stringify(result)}})`);
  assert.equal(f.run('controlled.get(7).steps.size'),0);assert.equal(f.run('controlled.get(7).stepOverflow'),false);
});

test('a modal retains page steps through collection until an explicit private acknowledgement',async()=>{
  const f=stepFixture(),step={...heldStep(),kind:'native_submit',cancellable:true};f.run(`notify(${JSON.stringify(step)})`);
  f.run("dialogs.set(7,{kind:'confirm',text:'Still handling the input'})");
  assert.equal((await f.run('collectSteps(7)')).length,0);assert.equal(f.run('controlled.get(7).steps.size'),1);
  f.run('dialogs.delete(7)');
  const first=await f.run('collectSteps(7)'),second=await f.run('collectSteps(7)');
  assert.equal(first.length,1);assert.equal(second.length,1);
  assert.equal(first[0].id,second[0].id);assert.equal(first[0].document,'old-document');
  assert.equal(f.run('controlled.get(7).steps.size'),1,'a failed service check must be able to read the hold again');
  await f.run(`dispatch({name:'ack_steps',tab:7,steps:${JSON.stringify(first)}})`);
  assert.equal(f.run('controlled.get(7).steps.size'),0);
  f.run(`notify(${JSON.stringify(step)})`);assert.equal(f.run('controlled.get(7).steps.size'),0,'a late repeat cannot undo acknowledgement');
  assert.equal(f.run('forwarded.length'),1);
});

test('a retired control accepts late observations without authorizing input and expires within its bound',async()=>{
  const f=stepFixture(),step=heldStep();
  f.run("globalThis.expiry=[];setTimeout=(callback,delay)=>{expiry.push({callback,delay});return 0};chrome.webNavigation.getAllFrames=async()=>[];chrome.debugger={detach:async()=>{}};chrome.tabs.ungroup=async()=>{};chrome.tabs.move=async()=>{};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{}}");
  await f.run('release(7)');assert.equal(f.run('controlled.has(7)'),false);
  assert.equal(f.run(`notify(${JSON.stringify(step)}).received`),true,'an old private observation survives release');
  assert.equal(f.run("forwarded.filter(message=>message.event==='held_step').length"),1);
  assert.throws(()=>f.run("assertControl(7,'epoch')"),/control ended/);
  f.run("controlled.set(7,{epoch:'replacement-epoch',inputNonce:'new-input'})");
  assert.throws(()=>f.run("assertControl(7,'epoch')"),/control ended/);
  assert.equal(f.run('controlled.get(7).epoch'),'replacement-epoch');
  await f.run(`dispatch({name:'ack_steps',tab:7,steps:[{...${JSON.stringify(step)},frame:2}]})`);
  assert.equal(f.run("stepControl(7,'epoch').steps.size"),0);
  f.run('expiry[0].callback()');
  assert.equal(f.run(`notify(${JSON.stringify(heldStep('later'))}).received`),false,'expired old control has no observation authority');
  assert.equal(f.run('expiry[0].delay'),900000);
  for(let tab=100;tab<133;tab++){f.run(`controlled.set(${tab},{epoch:'epoch-${tab}'})`);await f.run(`release(${tab})`);}
  assert.equal(f.run('retiredControls.size'),32);assert.equal(f.run("stepControl(100,'epoch-100')"),undefined);
  assert.equal(f.run("stepControl(132,'epoch-132').epoch"),'epoch-132');
});

test('headed input arms all frames before activation and rechecks binding before dispatch',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});globalThis.calls=[];globalThis.reads=0;globalThis.snapshot={tab:7,url:'http://fixture.test/',control:'epoch',frames:[{frame:0,document:'doc',url:'http://fixture.test/',target:{element:'e1',role:'button',name:'Continue'},form:null},{frame:2,document:'child',url:'http://second.test/',target:null,form:null}]};requireTab=async()=>({url:snapshot.url});facts=async()=>{calls.push('facts-'+(++reads));return snapshot};content=async(tab,frame,command)=>{calls.push(command+'-'+frame);return {}};chrome.tabs={get:async()=>({active:false}),update:async(tab,args)=>{calls.push('activate-'+tab);return {active:args.active}}};chrome.webNavigation={getAllFrames:async()=>[]};chrome.debugger={sendCommand:async(source,method,parameters)=>{calls.push(parameters.type);return {}}};");
  await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'}})");
  const calls=Array.from(f.run('calls'));
  assert.ok(calls.indexOf('arm-0')<calls.indexOf('activate-7'));
  assert.ok(calls.indexOf('arm-2')<calls.indexOf('activate-7'));
  assert.ok(calls.indexOf('activate-7')<calls.indexOf('facts-2'));
  assert.ok(calls.indexOf('facts-2')<calls.indexOf('keyDown'));
  assert.deepEqual(calls.filter(value=>value==='keyDown'||value==='keyUp'),['keyDown','keyUp']);
  f.run("reads=0;calls=[];globalThis.approved=binding(snapshot,{frame:0},null,false);chrome.tabs.update=async()=>{snapshot.frames[0].target.name='Changed by activation';return {active:true}};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'},binding:approved})"),/page changed during frame setup/);
  assert.equal(f.run("calls.includes('keyDown')"),false,'an activation handler change refuses before native input');
});

test('release wakes pending input and detaches before a bounded blocked clear',{timeout:1000},async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';globalThis.calls=[];globalThis.timers=[];setTimeout=(callback,delay)=>{timers.push({callback,delay});return 0};chrome.debugger={sendCommand:()=>new Promise(()=>{}),detach:async()=>{calls.push('detach')}};chrome.tabs={sendMessage:(tab,message)=>{calls.push(message.command);return new Promise(()=>{})},ungroup:async()=>{},move:async()=>{}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,url:'http://fixture.test/'}]};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{}};");
  const native=assert.rejects(f.run("cdp(7,'Input.dispatchKeyEvent',{type:'keyDown'})"),/control ended while input was in flight/);
  const content=assert.rejects(f.run("content(7,0,'focus',{element:'e1'})"),/control ended during input handling/);
  let settled=false;const released=f.run('release(7)').then(()=>{settled=true});
  await Promise.all([native,content]);
  for(let attempt=0;attempt<100&&!f.run("timers.some(timer=>timer.delay===1000)&&calls.includes('clear')");attempt++)await Promise.resolve();
  assert.ok(f.run("calls.indexOf('detach')<calls.indexOf('clear')"),'debugger must detach before blocked page cleanup');
  assert.equal(settled,false);assert.equal(f.run('controlled.has(7)'),false);assert.equal(f.run('dialogWake.size'),0);
  f.run('timers.find(timer=>timer.delay===1000).callback()');await released;
  assert.equal(settled,true,'cleanup cannot keep Stop or the native serial queue blocked');
});

test('late tab updates use fresh tab state and cannot release a replacement control',async()=>{
  const f=fixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'old'});globalThis.releases=[];globalThis.tabReply=null;release=async tab=>{releases.push(tab)};chrome.tabs={onUpdated:{addListener:listener=>{globalThis.updated=listener}},get:()=>new Promise(resolve=>{tabReply=resolve})};");
  f.run(source.slice(source.indexOf('chrome.tabs.onUpdated.addListener('),source.indexOf('chrome.tabs.onRemoved.addListener(')));
  const old=f.run("updated(7,{url:'http://old.test/'},{groupId:999})");
  f.run("controlled.set(7,{epoch:'replacement'});tabReply({groupId:999,url:'http://old.test/'})");await old;
  assert.equal(f.run('releases.length'),0);
  f.run("chrome.tabs.get=async()=>({groupId:1,url:'http://fixture.test/'})");
  await f.run("updated(7,{url:'http://stale.test/'},{groupId:999})");assert.equal(f.run('releases.length'),0,'event snapshot is not current tab state');
  f.run("chrome.tabs.get=async()=>({groupId:2,url:'http://fixture.test/'})");await f.run('updated(7,{})');
  assert.equal(f.run('releases.length'),1,'a genuine current group change still releases');
});

test('late detach notifications probe the current attachment and preserve replacement controls',async()=>{
  const f=fixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run("controlled.set(7,{epoch:'old'});globalThis.releases=[];globalThis.rejectProbe=null;release=async tab=>{releases.push(tab)};chrome.debugger={onDetach:{addListener:listener=>{globalThis.detached=listener}},sendCommand:()=>new Promise((resolve,reject)=>{rejectProbe=reject})};");
  f.run(source.slice(source.indexOf('chrome.debugger.onDetach.addListener('),source.lastIndexOf('connect();')));
  const old=f.run('detached({tabId:7})');f.run("controlled.set(7,{epoch:'replacement'});rejectProbe(Error('old attachment ended'))");await old;
  assert.equal(f.run('releases.length'),0);
  f.run("chrome.debugger.sendCommand=async()=>({})");await f.run('detached({tabId:7})');assert.equal(f.run('releases.length'),0,'a live attachment survives a stale detach event');
  f.run("chrome.debugger.sendCommand=async()=>{throw Error('not attached')}");await f.run('detached({tabId:7})');
  assert.equal(f.run('releases.length'),1,'failure of the current attachment still releases it');
});

test('navigated iframe cleanup preserves queued holds and distinguishes an uncertain surviving reader',async()=>{
  const f=stepFixture(),step=heldStep();f.run(`notify(${JSON.stringify(step)})`);
  f.run("chrome.tabs.sendMessage=async(tab,message)=>{commands.push(message.command);if(message.command==='finish_input')throw Error('reader disappeared');return {ok:true,data:[]}};chrome.webNavigation.getFrame=async()=>({frameId:2,documentId:'replacement-native-document'});");
  assert.equal(await f.run("finishFrames(7,[{frame:2,browser_document:'old-native-document'}],'epoch','nonce')"),false,'known replacement has no surviving old reader to finish');
  assert.equal(f.run('controlled.get(7).steps.size'),1,'cleanup failure cannot discard the observed hold');
  const steps=await f.run('collectSteps(7)');assert.equal(steps.length,1);assert.equal(steps[0].kind,'activation_unknown');
  assert.equal(steps[0].document,'old-document');assert.equal(f.run('controlled.get(7).steps.size'),1);
  f.run("chrome.webNavigation.getFrame=async()=>({frameId:2,documentId:'old-native-document'})");
  assert.equal(await f.run("finishFrames(7,[{frame:2,browser_document:'old-native-document'}],'epoch','nonce')"),true,'a surviving reader without a completion reply is uncertain');
  f.run("chrome.webNavigation.getFrame=async()=>{throw Error('identity unavailable')}");
  assert.equal(await f.run("finishFrames(7,[{frameId:2,documentId:'old-native-document'}],'epoch','nonce')"),true,'failure to establish replacement stays uncertain');
});

test('input replies propagate uncertain completion while retaining observed steps',async()=>{
  const f=stepFixture(),step=heldStep();f.run(`notify(${JSON.stringify(step)})`);
  f.run("requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,url:'http://fixture.test/',frames:[{frame:0,browser_document:'native-document',target:{element:'e1',role:'button',name:'Continue'},form:null}]});chrome.tabs.get=async()=>({active:false});chrome.tabs.update=async()=>({active:true});chrome.tabs.sendMessage=async(tab,message)=>{if(message.command==='finish_input')throw Error('completion unavailable');return {ok:true,data:message.command==='steps'?[]:{}}};chrome.webNavigation.getFrame=async()=>({documentId:'native-document'});chrome.debugger={sendCommand:async()=>({})};");
  const reply=await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'}})");
  assert.equal(reply.uncertain_finish,true);assert.equal(reply.steps.length,1);
  assert.equal(reply.steps[0].document,'old-document');assert.equal(reply.steps[0].kind,'activation_unknown');
  assert.equal(f.run('controlled.get(7).steps.size'),1,'an unknown result is not an acknowledgement');
});

test('Stop during the selected-tab read cannot activate the released owner tab',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'button',name:'Continue'},form:null}]});content=async()=>({});globalThis.effects=[];chrome.tabs={get:async()=>{controlled.delete(7);return {active:false}},update:async()=>effects.push('activate')};chrome.debugger={sendCommand:async()=>effects.push('input')};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'}})"),/control ended/);
  assert.deepEqual(Array.from(f.run('effects')),[]);
});

test('form destinations changed to an excluded host during arming refuse input and resume without a binding',async()=>{
  for(const method of ['get','post'])for(const name of ['input','resume']){
    const f=fixture();
    f.run(`excludedHosts=['approval.test'];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.reads=0;globalThis.commands=[];globalThis.effects=[];facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'textbox',name:'Query',editable:true},form:{element:'form1',method:'${method}',search:${method==='get'},action:++reads===1?'http://fixture.test/receive':'http://approval.test/receive'}}]});content=async(tab,frame,command)=>{commands.push(command);return {}};chrome.tabs={get:async()=>({active:true}),update:async()=>effects.push('activate')};chrome.debugger={sendCommand:async()=>effects.push('input')};`);
    await assert.rejects(f.run(`dispatch({name:'${name}',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})`),/approval\/settings/,method+' '+name);
    assert.equal(f.run('reads'),2,'the first destination was allowed and the decisive reread followed arming');
    assert.ok(f.run("commands.includes('arm')"));
    assert.equal(f.run("commands.some(command=>['focus','select','check','install_file','resume'].includes(command))"),false);
    assert.deepEqual(Array.from(f.run('effects')),[],'the excluded destination must refuse before native input');
  }
});

test('an allowed GET search destination reaches native input without a binding',async()=>{
  const f=fixture();
  f.run("excludedHosts=['approval.test'];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.effects=[];facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'textbox',name:'Search',editable:true},form:{element:'form1',method:'get',search:true,action:'http://fixture.test/search'}}]});content=async()=>({});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[]};chrome.debugger={sendCommand:async(source,method,parameters)=>{effects.push(parameters.type);return {}}};");
  const reply=await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})");
  assert.equal(reply.dispatched,true);assert.deepEqual(Array.from(f.run('effects')),['keyDown','keyUp']);
});

test('validity refuses an already open modal without contacting the renderer',{timeout:1000},async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});dialogs.set(7,{kind:'confirm'});globalThis.readyCalls=0;chrome.webNavigation={getFrame:async()=>({url:'http://fixture.test/'})};chrome.tabs={sendMessage:()=>{readyCalls++;return new Promise(()=>{})}};");
  await assert.rejects(f.run("dispatch({name:'validity',tab:7,reference:{frame:0,element:'e1'}})"),error=>/^refused:/.test(error.message)&&/dialog/i.test(error.message));
  assert.equal(f.run('readyCalls'),0);assert.equal(f.run('effectStarted'),false);assert.equal(f.run('dialogWake.size'),0);
});

test('a modal opening during ready promptly refuses validity and disposes its private waiter',{timeout:1000},async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.readyCalls=0;chrome.webNavigation={getFrame:async()=>({url:'http://fixture.test/'})};chrome.tabs={sendMessage:()=>{readyCalls++;return new Promise(()=>{})}};");
  const pending=f.run("dispatch({name:'validity',tab:7,reference:{frame:0,element:'e1'}})");
  const rejected=assert.rejects(pending,error=>/^refused:/.test(error.message)&&/dialog/i.test(error.message));
  for(let attempt=0;attempt<20&&!f.run('readyCalls');attempt++)await Promise.resolve();
  assert.equal(f.run('readyCalls'),1);f.run("dialogs.set(7,{kind:'confirm'});wakeDialog(7)");await rejected;
  assert.equal(f.run('dialogWake.size'),0);assert.equal(f.run('effectStarted'),false);
});

test('validity returns the same no-modal ready facts without dispatching input',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.readyMessages=[];chrome.webNavigation={getFrame:async()=>({url:'http://fixture.test/'})};chrome.tabs={sendMessage:async(tab,message,options)=>{readyMessages.push({tab,message,frame:options.frameId});return {ok:true,data:{preload:true,document:'native-reader-document',element_present:true}}}};");
  const result=await f.run("dispatch({name:'validity',tab:7,reference:{frame:2,element:'e7'}})");
  assert.equal(result.session,'fixture-session');assert.equal(result.control,'epoch');
  assert.equal(result.document,'native-reader-document');assert.equal(result.element_present,true);
  assert.equal(f.run('readyMessages.length'),1);assert.equal(f.run('readyMessages[0].message.element'),'e7');assert.equal(f.run('readyMessages[0].frame'),2);
  assert.equal(f.run('dialogWake.size'),0);assert.equal(f.run('effectStarted'),false);
});

test('a modal during native frame lookup refuses validity before starting ready',{timeout:1000},async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.frameReply=null;globalThis.readyCalls=0;chrome.webNavigation={getFrame:()=>new Promise(resolve=>{frameReply=resolve})};chrome.tabs={sendMessage:()=>{readyCalls++;return new Promise(()=>{})}};");
  const pending=f.run("dispatch({name:'validity',tab:7,reference:{frame:0,element:'e1'}})");
  const rejected=assert.rejects(pending,error=>/^refused:/.test(error.message)&&/dialog/i.test(error.message));
  for(let attempt=0;attempt<20&&!f.run('frameReply');attempt++)await Promise.resolve();
  assert.ok(f.run('frameReply'));f.run("dialogs.set(7,{kind:'confirm'});wakeDialog(7);frameReply({url:'http://fixture.test/'})");await rejected;
  assert.equal(f.run('readyCalls'),0);assert.equal(f.run('effectStarted'),false);
});
