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
  const context=vm.createContext({POLICY:policy,chrome,crypto:{randomUUID:()=> 'fixture-session'},URL,Promise,setTimeout,clearTimeout,TextEncoder,btoa:value=>Buffer.from(value,'binary').toString('base64')});
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
  const f=fixture();f.run("const nativeTimer=setTimeout;setTimeout=(callback,delay)=>{const timer=nativeTimer(callback,delay);timer.unref?.();return timer};excludedHosts=[];groupId=1;globalThis.lifecycleCalls=[];chrome.runtime={getURL:path=>'chrome-extension://fixture/'+path};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{},setTitle:async()=>{}};chrome.windows={get:async()=>({type:'normal'})};chrome.webNavigation={getAllFrames:async()=>[]};chrome.tabs={get:async()=>({url:'http://fixture.test/',windowId:1,index:0,groupId:1}),group:async()=>{lifecycleCalls.push('group');return 1},ungroup:async()=>{lifecycleCalls.push('ungroup')},move:async()=>{}};chrome.tabGroups={update:async()=>{}};chrome.debugger={attach:async()=>{},detach:async()=>{lifecycleCalls.push('detach')},sendCommand:async(source,method,parameters)=>{lifecycleCalls.push(method);return {};}};");return f;
}
async function spin(f,expression){for(let count=0;count<200&&!f.run(expression);count++)await Promise.resolve();assert.equal(!!f.run(expression),true,expression);}

test('tab catalogue reports native position and distinguishes active tabs from focused windows',async()=>{
  const f=fixture();f.run("chrome.windows={getAll:async()=>[{id:5,focused:true},{id:6,focused:false}]};chrome.tabs.query=async()=>[{id:7,windowId:5,index:1,active:true,groupId:-1,title:'Owner fixture',url:'http://fixture.test/'},{id:8,windowId:6,index:0,active:true,groupId:-1,title:'Popup fixture',url:'http://popup.test/'}];controlled.set(8,{epoch:'popup',virtualGroup:true,window:6});");
  const result=await f.run("collection({name:'tabs',limit:10})");const rows=JSON.parse(JSON.stringify(result.items));
  assert.deepEqual(rows.map(({tab,window,index,active,focused,controlled})=>({tab,window,index,active,focused,controlled})),[
    {tab:7,window:5,index:1,active:true,focused:true,controlled:false},
    {tab:8,window:6,index:0,active:true,focused:false,controlled:true},
  ]);
});

function startupFixture(){
  const f=fixture();f.run("globalThis.startup=[];excludedHosts=[];groupId=1;chrome.tabs.get=async()=>({url:'http://fixture.test/',groupId:1});chrome.webNavigation={getAllFrames:async()=>[]};chrome.runtime={getURL:path=>'chrome-extension://fixture/'+path};chrome.debugger={sendCommand:async(source,method,parameters)=>{startup.push({source,method,parameters});if(method==='Debugger.setBreakpointByUrl')return {breakpointId:'inert-breakpoint'};if(method==='Runtime.evaluate')return parameters.returnByValue?{result:{value:'private-document'}}:{result:{objectId:'private-cleanup'}};if(method==='Runtime.callFunctionOn')return parameters.returnByValue?{result:{value:'private-document'}}:{result:{objectId:'relay'}};if(method==='DOM.describeNode')return {node:{backendNodeId:1}};if(method==='DOM.resolveNode')return {object:{objectId:'isolated-relay'}};return {};}};preloadBundle=Promise.resolve(['// guard fixture','// reader fixture','// wrapper fixture']);controlled.set(7,{epoch:'epoch'});");return f;
}
async function startupContexts(f,prefix,start=1,source={tabId:7}){
  for(const context of [{id:start,uniqueId:prefix+'-main',origin:'http://fixture.test',auxData:{isDefault:true,frameId:'frame'}},{id:start+1,uniqueId:prefix+'-isolated',origin:'chrome-extension://fixture',auxData:{isDefault:false,frameId:'frame'}}])await f.run(`preloadEvent(${JSON.stringify(source)},'Runtime.executionContextCreated',{context:${JSON.stringify(context)}})`);
  await f.run(`preloadEvent(${JSON.stringify(source)},'Debugger.scriptParsed',{scriptId:${JSON.stringify(prefix)},executionContextId:${start+1},url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})`);
}
const paused=(f,script,source={tabId:7})=>f.run(`preloadEvent(${JSON.stringify(source)},'Debugger.paused',{hitBreakpoints:['inert-breakpoint'],callFrames:[{location:{scriptId:${JSON.stringify(script)}}}]})`);

test('removing a frame during bootstrap does not poison the still-controlled parent',async()=>{
  const f=startupFixture(),source={tabId:7,sessionId:'child'};await f.run("prepareTarget({tabId:7,sessionId:'child'},7,'child-target')");await startupContexts(f,'removed',1,source);
  f.run('preloadBundle=new Promise(resolve=>{globalThis.finishBundle=resolve})');const pending=paused(f,'removed',source);
  await spin(f,"preloadTargets.get('[7,\"child\"]').installing.size===1");f.run("destroyedTarget(preloadTargets.get('[7,\"child\"]'));finishBundle(['//guard','//reader','//page'])");await pending;
  assert.equal(f.run('controlled.has(7)'),true);assert.equal(f.run('controlled.get(7).preloadError'),undefined);assert.equal(f.run('[...preloadTargets.values()].some(state=>state.failures?.size)'),false);
});

test('a cancelled old bootstrap cannot poison or resume the replacement document pause',async()=>{
  const f=startupFixture();await f.run('prepareTarget({tabId:7})');await startupContexts(f,'old');
  f.run("const send=chrome.debugger.sendCommand;chrome.debugger.sendCommand=(source,method,parameters)=>{if(method==='Runtime.evaluate'&&parameters.contextId===2)throw Error('Native old context destroyed');return send(source,method,parameters)};preloadBundle=new Promise(resolve=>{globalThis.finishBundle=resolve});");
  const old=paused(f,'old');await spin(f,"preloadTargets.get('[7,null]').installing.size===1");
  for(const id of [1,2])await f.run(`preloadEvent({tabId:7},'Runtime.executionContextDestroyed',{executionContextId:${id}})`);
  await startupContexts(f,'new',3);const current=paused(f,'new');f.run("finishBundle(['//guard','//reader','//page'])");await Promise.all([old,current]);
  assert.equal(f.run('controlled.get(7).preloadError'),undefined);assert.equal(f.run("preloadTargets.get('[7,null]').failures.size"),0);assert.equal(f.run("preloadTargets.get('[7,null]').documents.get('isolated-4').ready"),true);
  assert.equal(f.run("startup.filter(item=>item.method==='Debugger.resume').length"),1,'only the replacement bootstrap resumes its own pause');
});

test('a real live bootstrap failure refuses until its native document ends',async()=>{
  const f=startupFixture();await f.run('prepareTarget({tabId:7})');await startupContexts(f,'live');
  f.run("const send=chrome.debugger.sendCommand;chrome.debugger.sendCommand=(source,method,parameters)=>method==='Runtime.evaluate'?Promise.resolve({exceptionDetails:{text:'Native startup failure'}}):send(source,method,parameters)");await paused(f,'live');
  await assert.rejects(f.run('facts(7)'),/could not install/);await f.run("preloadEvent({tabId:7},'Runtime.executionContextsCleared',{})");await assert.doesNotReject(f.run('facts(7)'));
});

test('Stop cancels a tab admission still awaiting attach without grouping it',async()=>{
  const f=lifecycleFixture();f.run('chrome.debugger.attach=()=>new Promise(resolve=>{globalThis.finishAttach=resolve})');
  const pending=f.run('take(7)');await spin(f,"typeof finishAttach==='function'");await f.run('stop()');f.run('finishAttach()');
  await assert.rejects(pending,/control stopped/);assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('group')"),false);assert.equal(f.run("lifecycleCalls.includes('detach')"),true);
});

test('a popup admission pending after Stop cannot resurrect control',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});chrome.windows.get=()=>new Promise(resolve=>{globalThis.popupWindow=resolve})");
  const pending=f.run("createdTarget({sourceTabId:7,tabId:8})");
  await spin(f,"typeof popupWindow==='function'");await f.run('stop()');f.run("popupWindow({type:'popup'})");await pending;
  assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('Runtime.runIfWaitingForDebugger')"),false);assert.equal(f.run("lifecycleCalls.includes('group')"),false);
});

test('popup admission preserves its window and uses a private group and tab badge',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});chrome.windows.get=async()=>({type:'popup'});chrome.tabs.move=async()=>{throw Error('must not move a popup')};chrome.action.setBadgeText=async value=>{lifecycleCalls.push(JSON.stringify(value))};chrome.action.setTitle=async value=>{lifecycleCalls.push(JSON.stringify(value))};");
  await f.run('createdTarget({sourceTabId:7,tabId:8})');
  assert.equal(f.run('controlled.get(8).virtualGroup'),true);assert.equal(f.run('controlled.get(8).parentEpoch'),'parent');
  assert.equal(f.run("lifecycleCalls.includes('group')"),false);assert.equal(f.run("lifecycleCalls.some(value=>value.includes('POP'))"),true);
  await f.run('release(8)');assert.equal(f.run("lifecycleCalls.includes('ungroup')"),false);
});

test('ordinary openers and an opener dragged out before notification never admit popups',async()=>{
  const f=lifecycleFixture();await f.run('createdTarget({sourceTabId:7,tabId:8})');assert.equal(f.run('lifecycleCalls.length'),0);
  f.run("controlled.set(7,{epoch:'parent'});chrome.tabs.get=async()=>({groupId:-1,url:'http://fixture.test/'})");
  await f.run('createdTarget({sourceTabId:7,tabId:8})');assert.equal(f.run('controlled.has(8)'),false);assert.equal(f.run("lifecycleCalls.includes('group')"),false);
});

test('popup reads revoke control when its opener no longer belongs to the group',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});controlled.set(8,{epoch:'child',virtualGroup:true,parentTab:7,parentEpoch:'parent'});chrome.tabs.get=async tab=>({groupId:tab===7?-1:1,url:'http://fixture.test/'})");
  await assert.rejects(f.run('requireTab(8)'),/opener is outside/);assert.equal(f.run('controlled.size'),0);
});

test('a popup moved to another native window loses control and a form-target GET cannot reload',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});controlled.set(8,{epoch:'child',virtualGroup:true,window:2,parentTab:7,parentEpoch:'parent'});");
  await assert.rejects(f.run('requireTab(8)'),/outside the Claude group/);assert.equal(f.run('controlled.has(8)'),false);
  f.run("controlled.set(8,{epoch:'child',parentTab:7});documentMethods.set('[8,0]',{document:'form-get',method:'GET'});formLoadedDocuments.set('[8,0]','form-get');chrome.webNavigation.getAllFrames=async()=>[{frameId:0,documentId:'form-get',url:'http://fixture.test/form'}];cdp=async()=>({frameTree:{frame:{url:'http://fixture.test/form',loaderId:'loader'}}});");
  await assert.rejects(f.run('reloadIdentity(8)'),/form submission/);
});

test('Stop during blocked native cleanup returns pending and preserves handles until restoration',async()=>{
  const f=lifecycleFixture();f.run("globalThis.clockTimers=[];setTimeout=(callback,delay)=>{clockTimers.push({callback,delay});return 0};controlled.set(7,{epoch:'epoch'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,contexts:new Map(),documents:new Map([['main',{cleanup:'restore'}]]),installing:new Set()});chrome.debugger.sendCommand=(source,method)=>{lifecycleCalls.push(method);return method==='Runtime.callFunctionOn'?new Promise(resolve=>{globalThis.unblockCleanup=resolve}):Promise.resolve({})};");
  const stopped=f.run('stop()');await spin(f,"typeof unblockCleanup==='function'");assert.equal(f.run('controlled.size'),0);assert.equal(f.run("lifecycleCalls.includes('detach')"),false);assert.equal(f.run("lifecycleCalls.includes('ungroup')"),false);
  f.run('clockTimers.find(timer=>timer.delay===1000).callback()');const result=await stopped;assert.equal(result.stopped,true);assert.equal(result.cleanup_pending,1);assert.equal(f.run('preloadTargets.size'),1);
  await assert.rejects(f.run('take(7)'),/cleanup is still pending/);
  f.run('unblockCleanup({})');await spin(f,"releasing.size===0");assert.equal(f.run("lifecycleCalls.includes('detach')"),true);assert.equal(f.run("lifecycleCalls.includes('ungroup')"),true);
});

test('final F6 navigate reload in a taken tab gives the same unsaved and playing report and never reloads a POST',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.reloaded=0;globalThis.reloadChecks=0;content=async()=>{reloadChecks++;return {unsaved:true,playing:true}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'}]};cdp=async(tab,method,parameters)=>{if(method==='Page.getFrameTree')return {frameTree:{frame:{loaderId:'loader',url:'http://fixture.test/'}}};assertedMethod=method;reloaded++;globalThis.reloadParameters=parameters;};globalThis.assertedMethod=null;");
  f.run("observation=async()=>({});documentMethods.set('[7,0]',{document:'doc',method:'GET'})");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'reload'})"),/reload_required: Reloading this tab would lose unsaved typing in editable content; and media that is playing\. Nothing was done\. Tell the owner what would be lost and get his OK in the chat before you repeat with discard_unsaved=true; only typing marked as typed by Claude may be discarded without asking$/);
  assert.equal(f.run('reloaded'),0);assert.equal(f.run('reloadChecks'),1);
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'reload',discard_unsaved:false})"),/reload_required/);assert.equal(f.run('reloaded'),0);
  f.run("content=async()=>{reloadChecks++;return {unsaved:false,playing:false}};chrome.tabs.get=async()=>({audible:true})");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'reload'})"),/reload_required: Reloading this tab would lose media that is playing\./);assert.equal(f.run('reloaded'),0);
  f.run("chrome.tabs.get=async()=>({audible:false})");
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,direction:'reload'})")).navigated,true,'a clean tab reloads without the flag');assert.equal(f.run('reloaded'),1);
  f.run("content=async()=>{reloadChecks++;return {unsaved:true,playing:false}}");
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,direction:'reload',discard_unsaved:true})")).navigated,true);assert.equal(f.run('reloaded'),2);assert.equal(f.run('assertedMethod'),'Page.reload');
  f.run("documentMethods.set('[7,0]',{document:'doc',method:'POST'})");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'reload',discard_unsaved:true})"),/form submission/);assert.equal(f.run('reloaded'),2);
});

test('final discard_unsaved navigate to an address and close_tab give the first input report and act only with the flag',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.navigations=0;globalThis.closed=0;globalThis.inspected=0;content=async()=>{inspected++;return {unsaved:true,fields:['field \\\"Comment\\\"','editor \\\"Message\\\"'],playing:false}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'}]};cdp=async(tab,method)=>{if(method==='Page.navigate'){navigations++;return {loaderId:'next'};}};observation=async()=>({});release=async()=>({released:7});chrome.tabs.get=async()=>({audible:true});chrome.tabs.remove=async()=>{closed++;};");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/next'})"),/^Error: reload_required: Navigating this tab away would lose unsaved typing in field "Comment", editor "Message"; and media that is playing\. Nothing was done\. Tell the owner .*may be discarded without asking$/);
  assert.equal(f.run('navigations'),0);
  for(const flag of ['',',discard_unsaved:false',',discard_unsaved:1']){
    await assert.rejects(f.run("dispatch({name:'close_tab',tab:7"+flag+"})"),/reload_required: Closing this tab would lose unsaved typing in field "Comment"/);
    await assert.rejects(f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/next'"+flag+"})"),/reload_required/);
  }
  assert.equal(f.run('closed'),0);assert.equal(f.run('navigations'),0);
  const inspected=f.run('inspected');
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/next',discard_unsaved:true})")).navigated,true);assert.equal(f.run('navigations'),1);
  assert.equal(JSON.stringify(await f.run("dispatch({name:'close_tab',tab:7,discard_unsaved:true})")),'{"closed":7}');assert.equal(f.run('closed'),1);
  assert.equal(f.run('inspected'),inspected,'the flag discards without reading the tab again');
  f.run("content=async()=>({unsaved:false,fields:[],playing:false});chrome.tabs.get=async()=>({audible:false})");
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/clean'})")).navigated,true,'a clean tab needs no flag');assert.equal(f.run('navigations'),2);
  assert.equal(JSON.stringify(await f.run("dispatch({name:'close_tab',tab:7})")),'{"closed":7}');assert.equal(f.run('closed'),2);
  // A tab Claude just opened has no reader on about:blank and holds nothing;
  // any other frame without an answer may hold typing.
  f.run("chrome.webNavigation.getAllFrames=async()=>[{frameId:0,url:'about:blank'}];content=async()=>{const error=Error('Could not establish connection. Receiving end does not exist.');error.readerUnavailable=true;throw error;}");
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/from-blank'})")).navigated,true);assert.equal(f.run('navigations'),3);
  f.run("chrome.webNavigation.getAllFrames=async()=>[{frameId:0,url:'http://fixture.test/'},{frameId:3,url:'about:blank'}]");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,url:'http://fixture.test/next'})"),/would lose 2 frames that could not be inspected and may hold unsaved typing\./);
  await assert.rejects(f.run("dispatch({name:'close_tab',tab:7})"),/would lose 2 frames that could not be inspected/);assert.equal(f.run('navigations'),3);assert.equal(f.run('closed'),2);
  f.run("chrome.webNavigation.getAllFrames=async()=>[{frameId:0,url:'http://fixture.test/'}];content=async()=>({unsaved:true,fields:Array.from({length:12},(_,index)=>'field \\\"F'+index+'\\\"'),playing:false})");
  await assert.rejects(f.run("dispatch({name:'close_tab',tab:7})"),/field "F9" and 2 more fields\./);
});

test('step 5 back and forward give the same unsaved report and go only with the flag',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.moves=[];globalThis.inspected=0;content=async()=>{inspected++;return {unsaved:true,fields:['field \\\"Comment\\\" (typed by the owner)'],playing:false}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/b'}]};cdp=async(tab,method,parameters)=>{if(method==='Page.getNavigationHistory')return {currentIndex:1,entries:[{id:10,url:'http://fixture.test/a'},{id:11,url:'http://fixture.test/b'},{id:12,url:'http://fixture.test/c'}]};if(method==='Page.navigateToHistoryEntry')moves.push(parameters.entryId);};observation=async()=>({});chrome.tabs.get=async()=>({audible:false});");
  for(const [direction,act,entry] of [['back','Going back in this tab',10],['forward','Going forward in this tab',12]]){
    for(const flag of ['',',discard_unsaved:false',',discard_unsaved:1'])
      await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'"+direction+"'"+flag+"})"),new RegExp('^Error: reload_required: '+act+' would lose unsaved typing in field "Comment" \\(typed by the owner\\)\\. Nothing was done\\. Tell the owner'));
    assert.equal(f.run('JSON.stringify(moves)'),'[]','nothing moves without the flag');
    const inspected=f.run('inspected');
    assert.equal((await f.run("dispatch({name:'navigate',tab:7,direction:'"+direction+"',discard_unsaved:true})")).navigated,true);
    assert.equal(f.run('JSON.stringify(moves)'),JSON.stringify([entry]));assert.equal(f.run('inspected'),inspected,'the flag goes without reading again');f.run('moves.length=0');
  }
  // A clean tab moves without the flag; an end of history or a form-loaded entry refuses before any report.
  f.run("content=async()=>{inspected++;return {unsaved:false,fields:[],playing:false}}");
  assert.equal((await f.run("dispatch({name:'navigate',tab:7,direction:'back'})")).navigated,true);assert.equal(f.run('JSON.stringify(moves)'),'[10]');
  f.run("moves.length=0;inspected=0;cdp=async(tab,method)=>method==='Page.getNavigationHistory'?{currentIndex:0,entries:[{id:10,url:'http://fixture.test/a'},{id:11,url:'http://fixture.test/b',transitionType:'form_submit'}]}:moves.push(method)");
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'back'})"),/no history entry/);
  await assert.rejects(f.run("dispatch({name:'navigate',tab:7,direction:'forward',discard_unsaved:true})"),/form-loaded history entry/);
  assert.equal(f.run('JSON.stringify(moves)'),'[]');assert.equal(f.run('inspected'),0);
});

test('step 5 the report lets Claude discard only his own typing without asking',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.navigations=0;chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'},{frameId:2,documentId:'child',url:'http://fixture.test/child'}]};cdp=async(tab,method)=>{if(method==='Page.navigate'){navigations++;return {loaderId:'next'};}};observation=async()=>({});chrome.tabs.get=async()=>({audible:false});");
  const go="dispatch({name:'navigate',tab:7,url:'http://fixture.test/next'})";
  f.run("content=async(tab,frame)=>({unsaved:true,fields:['field \\\"Search\\\" (typed by Claude)'],claude_only:true,playing:false})");
  await assert.rejects(f.run(go),/would lose unsaved typing in field "Search" \(typed by Claude\), field "Search" \(typed by Claude\)\. Nothing was done\. All of it is Claude's own typing, so it may be discarded without asking: repeat with discard_unsaved=true$/);
  // One frame with the owner's typing, a frame without the mark, playing media or an uninspected frame: ask him.
  for(const setup of ["content=async(tab,frame)=>frame?{unsaved:true,fields:['editor \\\"Body\\\" (typed by the owner)'],claude_only:false,playing:false}:{unsaved:true,fields:['field \\\"Search\\\" (typed by Claude)'],claude_only:true,playing:false}",
                      "content=async(tab,frame)=>frame?{unsaved:true,fields:['field \\\"Body\\\" (typed by the owner)'],playing:false}:{unsaved:true,fields:['field \\\"Search\\\" (typed by Claude)'],claude_only:true,playing:false}",
                      "content=async()=>({unsaved:true,fields:['field \\\"Search\\\" (typed by Claude)'],claude_only:true,playing:true})",
                      "content=async(tab,frame)=>{if(frame)throw Error('no reader');return {unsaved:true,fields:['field \\\"Search\\\" (typed by Claude)'],claude_only:true,playing:false};}"]){
    f.run(setup);await assert.rejects(f.run(go),/Nothing was done\. Tell the owner what would be lost and get his OK in the chat before you repeat with discard_unsaved=true; only typing marked as typed by Claude may be discarded without asking$/,setup);
  }
  assert.equal(f.run('navigations'),0);
});

test('a POST document arriving during reload inspection is never reloaded',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.topDocument='get';globalThis.reloads=0;documentMethods.set('[7,0]',{document:'get',method:'GET'});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:topDocument,url:'http://fixture.test/'}]};cdp=async(tab,method)=>{if(method==='Page.getFrameTree')return {frameTree:{frame:{url:'http://fixture.test/',loaderId:topDocument}}};reloads++};content=async()=>{topDocument='post';documentMethods.set('[7,0]',{document:'post',method:'POST'});return {unsaved:false,playing:false};};");
  // discard_unsaved=true skips the inspection, so the unflagged call is the one with this window.
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/form submission/);assert.equal(f.run('reloads'),0);
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

test('detaching a replaced iframe session preserves its parent and retires only a natively removed frame',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'parent',contexts:new Map(),scripts:new Map(),documents:new Map(),installing:new Set()});preloadTargets.set('[7,\"frame\"]',{source:{tabId:7,sessionId:'frame'},targetId:'frame-target',frameId:'native-frame',tab:7,contexts:new Map([[1,{uniqueId:'old-main'}]]),scripts:new Map(),documents:new Map(),installing:new Set()});chrome.debugger.getTargets=async()=>[{id:'frame-target'}];");
  await f.run("preloadEvent({tabId:7},'Target.detachedFromTarget',{sessionId:'frame'})");
  assert.equal(f.run('controlled.has(7)'),true);assert.equal(f.run('releasing.size'),0);assert.equal(f.run('preloadTargets.has(\'[7,"frame"]\')'),true,'a live old context is not falsely declared restored');
  f.run('chrome.debugger.onEvent={addListener:listener=>{globalThis.nativeEvent=listener}}');
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("nativeEvent({tabId:7},'Page.frameDetached',{frameId:'native-frame',reason:'remove'})");
  assert.equal(f.run('controlled.has(7)'),true);assert.equal(f.run('preloadTargets.has(\'[7,"frame"]\')'),false,'native frame removal retires old cleanup handles');
});

test('release rechecks a detached iframe target that disappeared after its notification',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'parent',contexts:new Map(),scripts:new Map(),documents:new Map(),installing:new Set()});preloadTargets.set('[7,\"frame\"]',{source:{tabId:7,sessionId:'frame'},targetId:'frame-target',tab:7,epoch:'parent',contexts:new Map([[1,{uniqueId:'old-main'}]]),scripts:new Map(),documents:new Map([['old-main',{main:'old-main',cleanup:'old-factory'}]]),installing:new Set()});chrome.debugger.getTargets=async()=>[{id:'frame-target'}];");
  await f.run("preloadEvent({tabId:7},'Target.detachedFromTarget',{sessionId:'frame'})");
  f.run('chrome.debugger.getTargets=async()=>[]');
  const released=await f.run('release(7)');assert.equal(released.cleanup_pending,false);assert.equal(f.run('releasing.size'),0);assert.equal(f.run('preloadTargets.size'),0);
});

test('an old popup detach cannot release a replacement control epoch after target lookup',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(8,{epoch:'old'});preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,contexts:new Map(),scripts:new Map(),documents:new Map()});preloadTargets.set('[7,\"popup\"]',{source:{tabId:7,sessionId:'popup'},targetId:'popup-target',tab:8,epoch:'old',contexts:new Map(),scripts:new Map(),documents:new Map()});chrome.debugger.getTargets=()=>new Promise(resolve=>{globalThis.finishTargets=resolve});");
  const pending=f.run("preloadEvent({tabId:7},'Target.detachedFromTarget',{sessionId:'popup'})");await spin(f,"typeof finishTargets==='function'");
  f.run("controlled.set(8,{epoch:'new'});finishTargets([])");await pending;
  assert.equal(f.run("controlled.get(8).epoch"),'new');assert.equal(f.run('releasing.size'),0);
});

test('a detached target disappearing after the release snapshot still finishes cleanup',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});preloadTargets.set('[7,\"frame\"]',{source:{tabId:7,sessionId:'frame'},targetId:'frame-target',detached:true,tab:7,contexts:new Map([[1,{uniqueId:'old-main'}]]),scripts:new Map(),documents:new Map([['old-main',{main:'old-main',cleanup:'old-factory'}]]),installing:new Set()});globalThis.snapshots=0;chrome.debugger.getTargets=async()=>++snapshots===1?[{id:'frame-target'}]:[];chrome.debugger.sendCommand=async()=>({result:{value:false}});");
  const released=await f.run('release(7)');assert.equal(released.cleanup_pending,false);assert.equal(f.run('releasing.size'),0);assert.equal(f.run('snapshots'),2);
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
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'bootstrap',executionContextId:2,url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:['inert-breakpoint'],callFrames:[{location:{scriptId:'bootstrap'}}]})");
  const commands=Array.from(f.run('startup'));
  const evaluated=commands.filter(value=>value.method==='Runtime.evaluate');
  assert.deepEqual(evaluated.map(value=>value.parameters.contextId),[2,2,2]);
  assert.equal(commands.some(value=>value.method==='Runtime.enable'),false);
  assert.ok(commands.some(value=>value.method==='Runtime.callFunctionOn'&&value.parameters.functionDeclaration.includes('wrapper fixture')));
  assert.ok(commands.some(value=>value.method==='DOM.resolveNode'&&!('executionContextId' in value.parameters)));
  assert.ok(evaluated.every(value=>value.parameters.disableBreaks===true));
  assert.match(evaluated[0].parameters.expression,/globalThis\[Symbol.for\("aresos.chrome.document-start.v1"\)\]=true/);assert.match(evaluated[0].parameters.expression,/guard fixture/);assert.match(evaluated[0].parameters.expression,/reader fixture/);
  assert.equal(commands.at(-1).method,'Debugger.resume');assert.equal(f.run("isPreloaded(7,'private-document')"),true);
  await f.run("preloadEvent({tabId:7},'Runtime.executionContextsCleared',{})");assert.equal(f.run("isPreloaded(7,'private-document')"),false);
});

test('taken-tab first input defers dirty or playing GET documents and refuses POST without a request',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.reloaded=0;globalThis.reloadChecks=0;content=async()=>{reloadChecks++;return {unsaved:true,playing:true}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'}]};cdp=async(tab,method,parameters)=>{if(method==='Page.getFrameTree')return {frameTree:{frame:{loaderId:'loader',url:'http://fixture.test/'}}};assertedMethod=method;reloaded++;globalThis.reloadParameters=parameters;};globalThis.assertedMethod=null;");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7,discard_unsaved:true})"),/request method is unknown/);
  f.run("documentMethods.set('[7,0]',{document:'doc',method:'POST'})");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7,discard_unsaved:true})"),/form submission/);assert.equal(f.run('reloaded'),0);assert.equal(f.run('reloadChecks'),0);
  f.run("documentMethods.set('[7,0]',{document:'doc',method:'GET'})");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/reload_required:.*unsaved.*playing/);assert.equal(f.run('reloaded'),0);
  assert.equal((await f.run("dispatch({name:'prepare_control',tab:7,discard_unsaved:true})")).reloaded,true);assert.equal(f.run('reloaded'),1);assert.equal(f.run('assertedMethod'),'Page.reload');
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
    f.run("armDialog=async()=>({owner:controlled.get(7),frames:[],nonce:'dialog-barrier',ready:Promise.resolve()});excludedHosts=[];controlled.set(7,{epoch:'epoch',inputNonce:'input-nonce'});dispatchEpoch='epoch';globalThis.frames=[];globalThis.accepted=[];chrome.webNavigation={getAllFrames:()=>new Promise(resolve=>frames.push(resolve))};chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}},sendCommand:async(source,method,params)=>{if(method==='Page.handleJavaScriptDialog')accepted.push(dialogs.get(7)?.text);return {};}};confirmationPlans.set(7,{operation:'approved-operation',browser_document:'doc',expected:{kind:'confirm',text:'Delete approved branch?',frame_url:'http://fixture.test/',button:'OK',frame:0},matched:[]});");
    f.run("privacyDocuments.set('doc','private');nativeDialogStarts.set('[7,\"doc\"]',[{kind:'confirm',document:'private'}]);");
    const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
    f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
    return f;
  }
  const valid=setup();
  const current=valid.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete approved branch?',url:'http://fixture.test/'})");
  valid.run("frames[0]([{frameId:0,documentId:'doc',url:'http://fixture.test/'}])");await current;
  assert.deepEqual(Array.from(valid.run('accepted')),['Delete approved branch?'],'the unchanged exact dialog remains covered');

  const borrowed=setup();borrowed.run('nativeDialogStarts.clear()');
  const borrowing=borrowed.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete approved branch?',url:'http://fixture.test/'})");
  borrowed.run("frames[0]([{frameId:0,documentId:'doc',url:'http://fixture.test/'}])");await borrowing;
  assert.equal(borrowed.run('dialogs.get(7).unguarded'),true);assert.equal(borrowed.run('accepted.length'),0,'a borrowed native cannot inherit automatic confirmation');assert.ok(borrowed.run('confirmationPlans.get(7).expected'));

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
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'button',name:'Continue'},form:null}]});content=async()=>({});chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.tabs={get:async()=>({active:false}),update:async()=>({})};globalThis.inputCalls=[];chrome.debugger={sendCommand:(source,method,parameters)=>{inputCalls.push(parameters.type);if(parameters.type==='keyDown')Promise.resolve().then(()=>{dialogs.set(7,{kind:'confirm'});wakeDialog(7)});return new Promise(()=>{});}};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})"),/page dialog interrupted the input sequence/);
  assert.deepEqual(Array.from(f.run('inputCalls')),['keyDown'],'no keyUp or later text may enter the pending dialog');
  assert.equal(f.run('dialogWake.size'),0);
});

test('answering a dialog collects a resumed handler submission without sending it',{timeout:1500},async()=>{
  const source=fs.readFileSync('control/chrome_tests/page.test.mjs','utf8');
  const policy=JSON.parse(fs.readFileSync('control/chrome/extension/policy.js','utf8').match(/\{[\s\S]*\}/)[0]);
  const createPage=Function('fs','vm','assert','policy',source.slice(source.indexOf('function fixture('),source.indexOf("\ntest('"))+'\nreturn fixture;')(fs,vm,assert,policy);
  const page=createPage(),form=new page.HTMLFormElement();page.arm(form,form);
  await page.guard.finish('epoch');page.advance(600);
  const f=fixture();
  f.run('globalThis').assertBarrier=value=>assert.equal(value,true,'native return boundary must be armed before answering');
  f.run('globalThis').onAnswer=()=>form.submit();
  f.run('globalThis').privateArm=parameters=>{if(parameters.expression.includes('dialogBoundary'))return {result:{value:{document:'document-1',token:'d1'}}};page.guard.arm({generation:'epoch',dispatch_nonce:'fixture-session',config:policy});return {result:{value:'document-1'}};};
  f.run('globalThis').pageReply=async message=>{
    if(message.command==='finish_input')await page.guard.finish(message.generation,message.dispatch_nonce);
    return {ok:true,data:message.command==='steps'?page.guard.steps():{finished:true}};
  };
  f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'epoch',inputNonce:'nonce'});globalThis.commands=[];globalThis.modal=true;globalThis.pauseArmed=false;chrome.tabs={get:async()=>({url:'http://fixture.test/',groupId:1}),sendMessage:(tab,message)=>{commands.push(message.command);return pageReply(message)}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'native-document',url:'http://fixture.test/'}]};privacyDocuments.set('native-document','document-1');chrome.debugger={sendCommand:async(source,method,parameters)=>{if(method==='Debugger.pause'){pauseArmed=true;return {}}if(method==='Runtime.evaluate'){if(modal)throw Error('page runtime blocked by native modal');return privateArm(parameters)}if(method==='Page.handleJavaScriptDialog'){assertBarrier(!!preloadTargets.get('[7,null]').dialogBarrier);modal=false;await preloadEvent(source,'Debugger.paused',{hitBreakpoints:[]});onAnswer();dialogs.delete(7)}return {};}};dialogs.set(7,{id:'dialog',frame:0,frame_url:'http://fixture.test/',kind:'confirm',text:'Continue?',button:'OK',browser_document:'native-document'});globalThis.expected={session,tab:7,control:'epoch',url:'http://fixture.test/',dialog:dialogs.get(7)};preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'epoch',contexts:new Map([[1,{id:1,uniqueId:'isolated'}]]),documents:new Map([['isolated',{document:'document-1',ready:true,isolated:'isolated'}],['stale',{document:'stale-private-document',ready:true,isolated:'gone'}]])});nativeDialogStarts.set('[7,\"native-document\"]',[{token:'d1',dialog:'dialog',kind:'confirm',document:'document-1'}]);");
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
  f.run("globalThis.expiry=[];setTimeout=(callback,delay)=>{expiry.push({callback,delay});return 0};chrome.webNavigation.getAllFrames=async()=>[];chrome.debugger={detach:async()=>{}};chrome.tabs.ungroup=async()=>{};chrome.tabs.move=async()=>{};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{},setTitle:async()=>{}};chrome.windows={get:async()=>({type:'normal'})}");
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
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});globalThis.calls=[];globalThis.reads=0;globalThis.snapshot={tab:7,url:'http://fixture.test/',control:'epoch',frames:[{frame:0,browser_document:'native-top',document:'doc',url:'http://fixture.test/',target:{element:'e1',role:'button',name:'Continue'},form:null},{frame:2,browser_document:'native-child',document:'child',url:'http://second.test/',target:null,form:null}]};requireTab=async()=>({url:snapshot.url});facts=async()=>{calls.push('facts-'+(++reads));return snapshot};content=async(tab,frame,command)=>{calls.push(command+'-'+frame);return {}};chrome.tabs={get:async()=>({active:false}),update:async(tab,args)=>{calls.push('activate-'+tab);return {active:args.active}}};chrome.webNavigation={getAllFrames:async()=>snapshot.frames.map(frame=>({frameId:frame.frame,documentId:frame.browser_document}))};chrome.debugger={sendCommand:async(source,method,parameters)=>{calls.push(parameters.type);return {}}};");
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
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';globalThis.calls=[];globalThis.timers=[];setTimeout=(callback,delay)=>{timers.push({callback,delay});return 0};chrome.debugger={sendCommand:()=>new Promise(()=>{}),detach:async()=>{calls.push('detach')}};chrome.tabs={sendMessage:(tab,message)=>{calls.push(message.command);return new Promise(()=>{})},ungroup:async()=>{},move:async()=>{}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,url:'http://fixture.test/'}]};chrome.action={setBadgeText:async()=>{},setBadgeBackgroundColor:async()=>{},setTitle:async()=>{}};chrome.windows={get:async()=>({type:'normal'})};");
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
  f.run("requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,url:'http://fixture.test/',frames:[{frame:0,browser_document:'native-document',target:{element:'e1',role:'button',name:'Continue'},form:null}]});chrome.tabs.get=async()=>({active:false});chrome.tabs.update=async()=>({active:true});chrome.tabs.sendMessage=async(tab,message)=>{if(message.command==='finish_input')throw Error('completion unavailable');return {ok:true,data:message.command==='steps'?[]:{}}};chrome.webNavigation.getAllFrames=async()=>[{frameId:0,documentId:'native-document'}];chrome.webNavigation.getFrame=async()=>({documentId:'native-document'});chrome.debugger={sendCommand:async()=>({})};");
  const reply=await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'}})");
  assert.equal(reply.uncertain_finish,true);assert.equal(reply.steps.length,1);
  assert.equal(reply.steps[0].document,'old-document');assert.equal(reply.steps[0].kind,'activation_unknown');
  assert.equal(f.run('controlled.get(7).steps.size'),1,'an unknown result is not an acknowledgement');
});

test('Stop during the selected-tab read cannot activate the released owner tab',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'button',name:'Continue'},form:null}]});content=async()=>({});globalThis.effects=[];chrome.tabs={get:async()=>{controlled.delete(7);return {active:false}},update:async()=>effects.push('activate')};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'x'}})"),/control ended/);
  assert.deepEqual(Array.from(f.run('effects')),[]);
});

test('form destinations changed to an excluded host during arming refuse input and resume without a binding',async()=>{
  for(const method of ['get','post'])for(const name of ['input','resume']){
    const f=fixture();
    f.run(`excludedHosts=['approval.test'];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.reads=0;globalThis.commands=[];globalThis.effects=[];facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'textbox',name:'Query',editable:true},form:{element:'form1',fields:[],method:'${method}',search:${method==='get'},action:++reads===1?'http://fixture.test/receive':'http://approval.test/receive'}}]});content=async(tab,frame,command)=>{commands.push(command);return {}};chrome.tabs={get:async()=>({active:true}),update:async()=>effects.push('activate')};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};`);
    await assert.rejects(f.run(`dispatch({name:'${name}',tab:7,reference:{frame:0,element:'e1'},input:{verb:'press',key:'Enter'}})`),/approval\/settings/,method+' '+name);
    assert.equal(f.run('reads'),2,'the first destination was allowed and the decisive reread followed arming');
    assert.ok(f.run("commands.includes('arm')"));
    assert.equal(f.run("commands.some(command=>['focus','select','check','install_file','resume'].includes(command))"),false);
    assert.deepEqual(Array.from(f.run('effects')),[],'the excluded destination must refuse before native input');
  }
});

test('an allowed GET search destination reaches native input without a binding',async()=>{
  const f=fixture();
  f.run("excludedHosts=['approval.test'];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});globalThis.effects=[];facts=async()=>({tab:7,frames:[{frame:0,target:{element:'e1',role:'textbox',name:'Search',editable:true},form:{element:'form1',fields:[],method:'get',search:true,action:'http://fixture.test/search'}}]});content=async()=>({});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async(source,method,parameters)=>{effects.push(parameters.type);return {}}};");
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


test('popup opener badges are distinct, clear on Stop, and never open or focus a window',async()=>{
  const f=lifecycleFixture();f.run("globalThis.badges=new Map();globalThis.titles=new Map();chrome.action.setBadgeText=async({tabId,text})=>badges.set(tabId,text);chrome.action.setTitle=async({tabId,title})=>titles.set(tabId,title);chrome.windows.create=chrome.windows.update=chrome.tabs.update=async()=>{throw Error('must never open or focus a window')};controlled.set(7,{epoch:'parent',window:1});controlled.set(8,{epoch:'child',virtualGroup:true,window:2,parentTab:7,parentEpoch:'parent'});controlled.set(9,{epoch:'other',virtualGroup:true,window:3,parentTab:7,parentEpoch:'parent'});chrome.tabs.get=async tab=>({url:'http://popup.test/',title:'Popup fixture',windowId:tab===7?1:tab===8?2:3,groupId:tab===7?1:-1});");
  await f.run('badge()');assert.equal(f.run('badges.get(7)'),'POP');assert.match(f.run('titles.get(7)'),/2 popups opened from here/);
  const status=await f.run('popupStatus()');assert.deepEqual(JSON.parse(JSON.stringify(status.popups.map(({tab,control})=>({tab,control})))),[{tab:8,control:'child'},{tab:9,control:'other'}]);
  await f.run("stopPopup(8,'child')");assert.equal(f.run('controlled.has(8)'),false);assert.equal(f.run('controlled.has(9)'),true);assert.equal(f.run('badges.get(7)'),'POP');
  await f.run("stopPopup(9,'other')");assert.equal(f.run('badges.get(7)'),'ON');assert.equal(f.run('badges.get(9)'),'');
  assert.ok(!f.run("lifecycleCalls.some(value=>['Page.reload','Page.navigate','group','ungroup'].includes(value))"),'Stop never reloads, closes or regroups popups');
  await f.run('release(7)');assert.equal(f.run('badges.get(7)'),'');
});

test('a stale popup Stop cannot end a replacement epoch or an ordinary tab',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'normal'});controlled.set(8,{epoch:'replacement',virtualGroup:true})");
  assert.equal((await f.run("stopPopup(8,'old')")).stale,true);assert.equal((await f.run("stopPopup(7,'normal')")).stale,true);assert.equal(f.run('controlled.size'),2);
});

test('popup Stop revokes input and clears opener badge before blocked document cleanup completes',async()=>{
  const f=lifecycleFixture();f.run("globalThis.clockTimers=[];setTimeout=(callback,delay)=>{clockTimers.push({callback,delay});return 0};globalThis.badges=new Map();chrome.action.setBadgeText=async({tabId,text})=>badges.set(tabId,text);controlled.set(7,{epoch:'parent'});controlled.set(8,{epoch:'child',virtualGroup:true,parentTab:7,parentEpoch:'parent'});preloadTargets.set('[8,null]',{source:{tabId:8},tab:8,contexts:new Map(),documents:new Map([['main',{cleanup:'restore'}]]),installing:new Set()});chrome.debugger.sendCommand=(source,method)=>method==='Runtime.callFunctionOn'?new Promise(resolve=>{globalThis.finishPopupCleanup=resolve}):Promise.resolve({});");
  await f.run('badge()');const pending=f.run("stopPopup(8,'child')");await spin(f,"typeof finishPopupCleanup==='function'&&badges.get(7)==='ON'");
  assert.equal(f.run('controlled.has(8)'),false);assert.equal(f.run('controlled.has(7)'),true);assert.equal(f.run('releasing.has(8)'),true);
  const denied=assert.rejects(f.run('requireTab(8)'),/outside the Claude group/);
  await spin(f,"clockTimers.filter(timer=>timer.delay===1000).length===2");f.run('clockTimers.filter(timer=>timer.delay===1000).forEach(timer=>timer.callback())');
  await denied;assert.equal((await pending).cleanup_pending,true);assert.equal(f.run('releasing.has(8)'),true);
  f.run('finishPopupCleanup({result:{value:true}})');await spin(f,'!releasing.has(8)');
});

test('queued slow badge writes cannot resurrect a stopped popup badge',async()=>{
  const f=lifecycleFixture();f.run("globalThis.badges=new Map();globalThis.slow=true;chrome.action.setBadgeText=async({tabId,text})=>{if(tabId===7&&text==='POP'&&slow){slow=false;await new Promise(resolve=>{globalThis.finishBadge=resolve});}badges.set(tabId,text)};controlled.set(7,{epoch:'parent'});controlled.set(8,{epoch:'child',virtualGroup:true,parentTab:7,parentEpoch:'parent'});");
  const initial=f.run('badge()');await spin(f,"typeof finishBadge==='function'");const stopped=f.run("stopPopup(8,'child')");f.run('finishBadge()');await Promise.all([initial,stopped]);
  assert.equal(f.run('badges.get(7)'),'ON');assert.equal(f.run('badges.get(8)'),'');
});

test('only the exact extension action popup can list or stop a controlled popup',async()=>{
  const f=lifecycleFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run("chrome.runtime.id='fixture';chrome.runtime.onMessage={addListener:listener=>{globalThis.receive=listener}};globalThis.stops=[];stopPopup=async(...args)=>{stops.push(args);return {stopped:true}};");
  f.run(source.slice(source.indexOf('chrome.runtime.onMessage.addListener('),source.indexOf('chrome.tabs.onUpdated.addListener(')));
  for(const url of ['http://fixture.test/','chrome-extension://fixture/popup.html?popups','chrome-extension://fixture/details.html'])f.run(`receive({command:'stop_popup',tab:8,control:'child'},{id:'fixture',url:${JSON.stringify(url)},frameId:0},()=>{})`);
  assert.equal(f.run('stops.length'),0);
  let response;assert.equal(f.run("receive({command:'stop_popup',tab:8,control:'child'},{id:'fixture',url:'chrome-extension://fixture/popup.html',frameId:0},()=>{})"),true);await Promise.resolve();assert.equal(f.run('stops.length'),1);
});

test('the extension has no companion window creation or focusing path',()=>{
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  assert.doesNotMatch(source,/chrome\.windows\.(?:create|update|remove)\s*\(/);
  for(const file of ['popup.html','popup.js','background.js'])assert.doesNotMatch(fs.readFileSync('control/chrome/extension/'+file,'utf8'),/popupPanel|[?]popups|companion|close-note/);
});


test('opener tab removal and native group removal revoke children and clear badges without another tool read',async()=>{
  for(const mode of ['close','ungroup']){
    const f=lifecycleFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
    f.run("globalThis.badges=new Map();chrome.action.setBadgeText=async({tabId,text})=>badges.set(tabId,text);controlled.set(7,{epoch:'parent'});controlled.set(8,{epoch:'child',virtualGroup:true,parentTab:7,parentEpoch:'parent'});chrome.tabs.onUpdated={addListener:listener=>{globalThis.updated=listener}};");
    f.run(source.slice(source.indexOf('chrome.tabs.onUpdated.addListener('),source.indexOf('chrome.tabs.onRemoved.addListener(')));
    await f.run('badge()');assert.equal(f.run('badges.get(7)'),'POP');
    if(mode==='close')f.run('removedTab(7)');else{f.run("chrome.tabs.get=async()=>({url:'http://fixture.test/',groupId:-1})");await f.run('updated(7,{})');}
    await spin(f,"!controlled.has(7)&&!controlled.has(8)&&badges.get(7)===''&&badges.get(8)==='' ");
  }
});


test('manual popup taking requires and binds a currently controlled native opener',async()=>{
  const f=lifecycleFixture();f.run("chrome.tabs.get=async tab=>({url:'http://popup.test/',windowId:tab===7?1:2,index:0,groupId:tab===7?1:-1,openerTabId:tab===8?7:undefined});chrome.windows.get=async window=>({type:window===1?'normal':'popup'});");
  await assert.rejects(f.run('take(8)'),/popup control requires its opener/);assert.equal(f.run('controlled.size'),0);assert.equal(f.run('lifecycleCalls.length'),0,'uncontrolled opener never gets a debugger attach or page injection');
  f.run("controlled.set(7,{epoch:'parent'})");await f.run('take(8)');assert.equal(f.run('controlled.get(8).parentTab'),7);assert.equal(f.run('controlled.get(8).parentEpoch'),'parent');
  await f.run('release(7)');assert.equal(f.run('controlled.has(8)'),false);
});


test('P1 independently opened native dialogs refuse if private arming cannot be established',async()=>{
  const f=fixture();f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'epoch'});chrome.tabs.get=async()=>({url:'http://fixture.test/',groupId:1});chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};globalThis.effects=[];chrome.debugger={sendCommand:async()=>effects.push('answered')};dialogs.set(7,{frame:0,frame_url:'http://fixture.test/',kind:'confirm',text:'Continue?'});globalThis.expected={session,tab:7,control:'epoch',url:'http://fixture.test/',dialog:dialogs.get(7)};");
  await assert.rejects(f.run("dispatch({name:'dialog',tab:7,binding:expected,input:{accept:true}})"),/leave it to the owner/);assert.equal(f.run('effects.length'),0);assert.equal(f.run('dialogs.has(7)'),true);
});
test('P2 inherited blank and srcdoc frames need authenticated origin and enter binding',async()=>{
  const f=fixture();f.run("excludedHosts=[];requireTab=async()=>({url:'http://fixture.test/'});controlled.set(7,{epoch:'epoch'});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:'top',url:'http://fixture.test/'},{frameId:1,parentFrameId:0,documentId:'blank',url:'about:blank'},{frameId:2,parentFrameId:0,documentId:'inline',url:'about:srcdoc'}]};globalThis.queried=[];content=async(tab,frame)=>{queried.push(frame);return {document:'private-'+frame,origin:'http://fixture.test',url:frame===0?'http://fixture.test/':frame===1?'about:blank':'about:srcdoc',editable:[{value:'Draft '+frame}],target:{element:'e1',name:'Send'}};};");
  const result=await f.run('facts(7)');assert.deepEqual(Array.from(f.run('queried')),[0,1,2]);assert.equal(result.frames.length,3);
  f.run('globalThis.current='+JSON.stringify(result));assert.equal(f.run("binding(current,{frame:0},'send',false).editable.length"),3);
  f.run("const previous=content;content=async(tab,frame)=>({...await previous(tab,frame),origin:frame===2?'null':'http://fixture.test'})");
  const unsafe=await f.run('facts(7)');assert.equal(unsafe.uncovered.length,1);f.run('globalThis.current='+JSON.stringify(unsafe));assert.throws(()=>f.run("binding(current,{frame:0},'send',false)"),/complete draft/);
});
test('P17 losing password history in a surviving browser document refuses reads',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'same-native-document',url:'http://fixture.test/'}]};globalThis.privateDocument='first';content=async()=>({document:privateDocument,url:'http://fixture.test/'});");
  await f.run('facts(7)');f.run("privateDocument='replacement'");await assert.rejects(f.run('facts(7)'),/password history was lost/);
});

function latePopupFixture(){
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'popup',popupNeedsReload:true});requireTab=async()=>({url:'http://popup.test/'});globalThis.committed=false;globalThis.installed=false;globalThis.injections=[];globalThis.messages=[];chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:committed?'popup-document':'initial-blank',url:committed?'http://popup.test/':'about:blank'}]};chrome.scripting.executeScript=async request=>{injections.push(request);installed=true;};chrome.tabs.sendMessage=async(tab,message,options)=>{messages.push({message,options});if(!installed)throw Error('Could not establish connection. Receiving end does not exist.');return {ok:true,data:message.command==='set_control'?{controlled:true}:{document:'private-popup',origin:'http://popup.test',url:'http://popup.test/',rows:[{name:'Continue'}]}};};");return f;
}

test('a popup committing after admission acquires a reader without reloading its document',async()=>{
  const f=latePopupFixture();await f.run('lateReader(7)');assert.equal(f.run('injections.length'),0);
  f.run('committed=true');const page=await f.run('facts(7)');assert.equal(page.frames.length,1);assert.equal(page.frames[0].rows[0].name,'Continue');assert.equal(page.needs_reload,true,'first act still requires the normal guarded reload');
  assert.equal(f.run('injections.length'),1);assert.deepEqual(JSON.parse(f.run('JSON.stringify(injections[0].target)')),{tabId:7,documentIds:['popup-document']});
  assert.equal(f.run("messages.every(value=>value.options.documentId==='popup-document'&&!('frameId'in value.options))"),true);
  await f.run('facts(7)');assert.equal(f.run('injections.length'),1,'a healthy reader is never reinstalled');
});

test('a document replaced between frame enumeration and read cannot inherit its successor privacy identity',async()=>{
  const f=latePopupFixture();f.run("committed=true;globalThis.nativeDocument='old';chrome.webNavigation.getAllFrames=async()=>[{frameId:0,parentFrameId:-1,documentId:nativeDocument,url:'http://popup.test/'}];chrome.tabs.sendMessage=async(tab,message,options)=>{if(options.documentId==='old')throw Error('No document with id old');return {ok:true,data:{document:'private-new',url:'http://popup.test/'}};};");
  const stale=await f.run('facts(7)');assert.equal(stale.frames.length,0);assert.equal(f.run("privacyDocuments.has('old')"),false,'a frame-ID reply from the replacement cannot poison the old document');assert.equal(f.run('injections.length'),0);
  f.run("nativeDocument='new'");const current=await f.run('facts(7)');assert.equal(current.frames[0].document,'private-new');assert.equal(f.run("privacyDocuments.get('new')"),'private-new');
});

test('missing-reader recovery never clears or retries a surviving document password-history refusal',async()=>{
  const f=latePopupFixture();f.run("committed=true;privacyDocuments.set('popup-document','original');chrome.tabs.sendMessage=async(tab,message,options)=>{messages.push({message,options});return {ok:false,error:'refused: private password history was lost for this surviving document; ask the owner to reload'};};");
  await assert.rejects(f.run('facts(7)'),/password history was lost/);assert.equal(f.run('injections.length'),0);assert.equal(f.run("privacyDocuments.get('popup-document')"),'original');assert.equal(f.run("messages[0].message.expected_document"),'original');
});

test('a dialog opening during missing-reader recovery is readable while injection is blocked',async()=>{
  const f=latePopupFixture();f.run("committed=true;chrome.scripting.executeScript=request=>{injections.push(request);return new Promise(resolve=>{globalThis.finishInjection=resolve;});};");
  const reading=f.run('facts(7)');await spin(f,"typeof finishInjection==='function'");f.run("dialogs.set(7,{frame:0,frame_url:'http://popup.test/',kind:'alert',text:'Popup alert'});wakeDialog(7)");
  const page=await reading;assert.equal(page.dialog.text,'Popup alert');assert.equal(page.frames.length,0);
  f.run('finishInjection()');await spin(f,'controlled.get(7).settingUp.size===0');
});

test('ending control during missing-reader installation cannot publish a snapshot or set control',async()=>{
  for(const retake of [false,true]){
    const f=latePopupFixture();f.run("committed=true;chrome.scripting.executeScript=()=>new Promise(resolve=>{globalThis.finishInjection=resolve;});");
    const reading=f.run('facts(7)');await spin(f,"typeof finishInjection==='function'");f.run('controlled.delete(7);'+(retake?"controlled.set(7,{epoch:'replacement'});":'')+'installed=true;finishInjection()');
    await assert.rejects(reading,/control ended/);assert.equal(f.run("messages.some(value=>value.message.command==='set_control')"),false);
  }
});
test('P24 final identity query finishes before the last dirty and audible check',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}]});globalThis.identityCalls=0;globalThis.dirty=false;globalThis.reloads=0;chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'doc',url:'http://fixture.test/'}]};documentMethods.set('[7,0]',{document:'doc',method:'GET'});cdp=async(tab,method)=>{if(method==='Page.getFrameTree'){if(++identityCalls===2)dirty=true;return {frameTree:{frame:{url:'http://fixture.test/',loaderId:'loader'}}};}reloads++;};content=async()=>({unsaved:dirty,playing:false});");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/reload_required/);assert.equal(f.run('reloads'),0);
  f.run('dirty=false;identityCalls=0;chrome.tabs.get=async()=>({audible:true})');await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/media that is playing/);assert.equal(f.run('reloads'),0);
});
test('P24 uncovered and unreadable frames count as possibly unsaved before both reload boundaries',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({needs_reload:true,frames:[{frame:0}],uncovered:[{frame:1}]});reloadIdentity=async()=>({loaderId:'loader',frameId:'top',frames:[[0,'top'],[1,'unreadable']]});globalThis.reloads=0;globalThis.unreadable=false;cdp=async()=>reloads++;content=async(tab,frame)=>{if(unreadable&&frame===1)throw Error('reader unavailable');return {unsaved:false,playing:false}};");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/possibly|unsaved/);assert.equal(f.run('reloads'),0);
  f.run('unreadable=true');
  await assert.rejects(f.run('reloadChecked(7,undefined,{})'),/1 frame that could not be inspected and may hold unsaved typing/);assert.equal(f.run('reloads'),0);
  f.run("facts=async()=>({needs_reload:true,frames:[{frame:0},{frame:1}]})");
  await assert.rejects(f.run("dispatch({name:'prepare_control',tab:7})"),/possibly|unsaved/);assert.equal(f.run('reloads'),0);
});
test('P25 satisfied checks and isolated selections do not activate an inactive tab',async()=>{
  for(const input of [{verb:'check',checked:true},{verb:'select',value:'second'}]){
    const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({frames:[{frame:0,target:{element:'e1',states:{checked:true}}}]});globalThis.activated=0;content=async()=>({});chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.tabs.get=async()=>({active:false});chrome.tabs.update=async()=>activated++;collectSteps=async()=>[];");
    const result=await f.run('dispatch('+JSON.stringify({name:'input',tab:7,reference:{frame:0,element:'e1'},input})+')');assert.equal(f.run('activated'),0);assert.equal(result.dispatched,input.verb!=='check');assert.equal(result.no_change,input.verb==='check');
  }
});
test('P27 Stop lifts navigation blocks before deferred native restoration',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'epoch'});preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},contexts:new Map(),documents:new Map([['main',{cleanup:'handle'}]]),installing:new Set()});chrome.debugger.sendCommand=()=>new Promise(()=>{});globalThis.ruleChanges=[];chrome.declarativeNetRequest.updateSessionRules=async value=>ruleChanges.push(value);globalThis.timerCallbacks=[];setTimeout=(callback,delay)=>{timerCallbacks.push({callback,delay})};");
  const pending=f.run('release(7)');await spin(f,'ruleChanges.length>0');const last=f.run('ruleChanges.at(-1)');assert.equal(last.addRules.length,0);await spin(f,'timerCallbacks.some(timer=>timer.delay===1000)');f.run('timerCallbacks.find(timer=>timer.delay===1000).callback()');assert.equal((await pending).cleanup_pending,true);
});
test('P28 final binding refusal finishes every armed frame',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});globalThis.reads=0;globalThis.finished=[];requireTab=async()=>({});facts=async()=>({tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:++reads===1?'Before':'After'}}]});content=async(tab,frame,command)=>{if(command==='finish_input')finished.push(frame);return {}};globalThis.approved=binding({tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Before'}}]},{frame:0},null,false);");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'select'},binding:approved})"),/page changed/);assert.deepEqual(Array.from(f.run('finished')),[0]);
});
test('P23 input page evidence contains the bounded post-input notice',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});facts=async()=>({frames:[{frame:0,target:{element:'e1'}}]});content=async(tab,frame,command)=>command==='observe'?{url:'http://fixture.test/',notices:['ERROR: the change failed']} : {};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};collectSteps=async()=>[];");
  const result=await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'select'}})");assert.equal(result.page.notices[0],'ERROR: the change failed');
});


test('P3 startup inherits an active hold before activation without any approval allowance',async()=>{
  const f=startupFixture();f.run("controlled.get(7).hold={nonce:'private',inFlight:true,until:Date.now()+500,config:{holdMs:500}};");
  await f.run('prepareTarget({tabId:7})');await startupContexts(f,'inherited');await paused(f,'inherited');
  const calls=Array.from(f.run('startup')),armed=calls.findIndex(row=>row.method==='Runtime.evaluate'&&row.parameters.expression.includes('.inherit('));
  assert.ok(armed>=0);assert.doesNotMatch(calls[armed].parameters.expression,/operation|primary_submission/);
  assert.ok(armed<calls.findIndex(row=>row.method==='Runtime.callFunctionOn'&&row.parameters.functionDeclaration.includes('this.activate()')));
});
test('P3 a frame appearing on the final snapshot is armed without an allowance before input',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.reads=0;globalThis.arms=[];const top={frame:0,document:'top',browser_document:'native-top',target:{element:'e1'}};const child={frame:2,document:'child',browser_document:'native-child'};facts=async()=>({frames:++reads===1?[top]:[top,child]});isPreloaded=()=>true;content=async(tab,frame,command,args)=>{if(command==='arm')arms.push({frame,args});return {}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'native-top'},{frameId:2,documentId:'native-child'}]};collectSteps=async()=>[];");
  await f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'select',value:'a'}})");
  assert.deepEqual(Array.from(f.run('arms.map(row=>row.frame)')),[0,2]);assert.equal(f.run('arms[1].args.operation'),undefined);
});
test('P31 a preloaded popup still crosses its mandatory first-act reload',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'parent'});chrome.windows.get=async()=>({type:'popup'});");await f.run('createdTarget({sourceTabId:7,tabId:8})');
  f.run("chrome.webNavigation.getAllFrames=async()=>[{frameId:0,documentId:'native-popup',parentFrameId:-1,url:'http://fixture.test/'}];content=async(tab,frame,command)=>command==='reload_state'?{unsaved:false,playing:false}:{document:'preloaded',url:'http://fixture.test/'};isPreloaded=()=>true;documentMethods.set('[8,0]',{document:'native-popup',method:'GET'});globalThis.reloads=0;cdp=async(tab,method)=>method==='Page.getFrameTree'?{frameTree:{frame:{loaderId:'loader',url:'http://fixture.test/'}}}:reloads++;");
  assert.equal((await f.run('facts(8)')).needs_reload,true);assert.equal((await f.run("dispatch({name:'prepare_control',tab:8})")).reloaded,true);assert.equal(f.run('reloads'),1);
});


test('P3 a remaining hold never awaits a browser task while startup is paused',{timeout:1000},async()=>{
  const f=startupFixture();f.run("controlled.get(7).hold={nonce:'private',inFlight:false,until:Date.now()+500,config:{holdMs:500}};const original=chrome.debugger.sendCommand;chrome.debugger.sendCommand=(source,method,parameters)=>method==='Runtime.evaluate'&&parameters.awaitPromise?new Promise(()=>{}):original(source,method,parameters);");
  await f.run('prepareTarget({tabId:7})');await startupContexts(f,'remaining');await paused(f,'remaining');
  assert.equal(f.run("isPreloaded(7,'private-document')"),true);assert.equal(f.run("startup.some(row=>row.method==='Debugger.resume')"),true);
  assert.equal(f.run("startup.some(row=>row.method==='Runtime.evaluate'&&row.parameters.awaitPromise)"),false);
});


test('P17 expected privacy identity is enforced inside the reader before a lost-history snapshot',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'same-browser-document',url:'http://fixture.test/'}]};globalThis.privateDocument='original';globalThis.valueReads=0;content=async(tab,frame,command,args)=>{if(args.expected_document&&args.expected_document!==privateDocument)throw Error('refused: private password history was lost');valueReads++;return {document:privateDocument,url:'http://fixture.test/'};};");
  await f.run('facts(7)');f.run("privateDocument='lost'");await assert.rejects(f.run('facts(7)'),/password history was lost/);assert.equal(f.run('valueReads'),1,'the second snapshot must never collect values');
});


test('P2 inherited frame URLs with fragments retain the same authenticated origin path',()=>{
  const f=fixture();f.run("excludedHosts=[];globalThis.parent={frameId:0,parentFrameId:-1,url:'http://fixture.test/'};");
  for(const url of ['about:blank','about:srcdoc','about:blank#editor','about:srcdoc#editor','about:blank?draft=1#editor']){
    assert.equal(f.run('frameAddress({frameId:1,parentFrameId:0,url:'+JSON.stringify(url)+'},[parent])'),'http://fixture.test/');
  }
});
test('P1 native document registration authenticates readiness and never overwrites lost privacy history',()=>{
  const f=stepFixture();f.run("globalThis.readyReply=null;globalThis.sender={id:'fixture-extension',tab:{id:7},documentId:'native',origin:'http://fixture.test',url:'about:blank'};runtimeListener({event:'reader_ready',document:'private'},sender,value=>readyReply=value)");
  assert.equal(f.run('readyReply.received'),true);assert.equal(f.run("privacyDocuments.get('native')"),'private');
  f.run("runtimeListener({event:'reader_ready',document:'lost'},sender,value=>readyReply=value)");assert.equal(f.run('readyReply.received'),false);assert.equal(f.run("privacyDocuments.get('native')"),'private');
  f.run("excludedHosts=['approval.test'];runtimeListener({event:'reader_ready',document:'excluded'},{...sender,documentId:'excluded',origin:'http://approval.test'},value=>readyReply=value)");assert.equal(f.run('readyReply.received'),false);assert.equal(f.run("privacyDocuments.has('excluded')"),false);
});
test('P1 pending debugger commands log their order without script arguments or page values',async()=>{
  const f=fixture();f.run("recording=true;globalThis.events=[];port={postMessage:value=>events.push(value.data)};chrome.debugger={sendCommand:()=>new Promise(resolve=>{globalThis.finishProtocol=resolve})};");
  const pending=f.run("preloadCommand({tabId:7},'Debugger.resume',{secret:'PAGE_VALUE_MUST_NOT_APPEAR'})");
  assert.equal(f.run('events[0].protocol_command.method'),'Debugger.resume');assert.equal(f.run('events[0].protocol_command.phase'),'dispatched');assert.equal(f.run('JSON.stringify(events).includes("PAGE_VALUE_MUST_NOT_APPEAR")'),false);
  f.run('finishProtocol({})');await pending;assert.equal(f.run('events[1].protocol_command.id===events[0].protocol_command.id'),true);assert.equal(f.run('events[1].protocol_command.phase'),'completed');
});
test('P1 only the authenticated native return boundary can arm the continuation',async()=>{
  const f=startupFixture();await f.run('prepareTarget({tabId:7})');await startupContexts(f,'boundary');await paused(f,'boundary');
  f.run("globalThis.boundaryToken=null;globalThis.armCount=0;globalThis.resumeCount=0;globalThis.readyCount=0;globalThis.failure=null;const state=preloadTargets.get('[7,null]'),doc=[...state.documents.values()][0];controlled.get(7).hold={nonce:'n',config:POLICY};state.dialogBarrier={nonce:'n',token:'expected',source:{state,doc},documents:[{state,doc}],resolve:()=>readyCount++,reject:error=>{failure=String(error)}};chrome.debugger.sendCommand=async(source,method,args)=>{if(method==='Debugger.resume'){resumeCount++;return {}}if(args.expression?.includes('dialogBoundary'))return {result:{value:{document:doc.document,token:boundaryToken}}};if(args.expression?.includes('.arm(')){armCount++;return {result:{value:doc.document}}}return {};};");
  await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[]})");assert.equal(f.run('armCount'),0);assert.equal(f.run('resumeCount'),1);assert.equal(f.run('readyCount'),0);
  f.run("boundaryToken='wrong'");await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[]})");assert.equal(f.run('armCount'),0);assert.equal(f.run('resumeCount'),1);assert.match(f.run('failure'),/return boundary changed/);assert.equal(f.run('controlled.get(7).dialogPauseFailed'),true);
});
test('P1 a native boundary after revocation resumes the owner during pending cleanup',async()=>{
  const f=lifecycleFixture();f.run("preloadTargets.set('[7,null]',{source:{tabId:7},tab:7,epoch:'old'});releasing.set(7,{original:{epoch:'old'}})");
  await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[]})");assert.equal(f.run("lifecycleCalls.includes('Debugger.resume')"),true);
});
test('P1 an existing modal hold is reusable only while every current guard proves its nonce',async()=>{
  for(const variant of ['free','approved-confirmation','unmatched-approval','finished','conservative-upgrade','unknown-allowance']){
    const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch',hold:{nonce:'existing',inFlight:true,hasAllowance:false,config:{conservative:false}}});chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'native',url:'http://fixture.test/'}]};privacyDocuments.set('native','private');preloadTargets.set('[7,null]',{tab:7,documents:new Map([['isolated',{document:'private',ready:true,activeNonce:'existing'}]])});dialogs.set(7,{browser_document:'native',kind:'confirm'});");
    if(['approved-confirmation','unmatched-approval'].includes(variant))f.run('controlled.get(7).hold.hasAllowance=true');
    if(variant==='finished')f.run("armedDocument(7,'private',null)");
    if(variant==='unknown-allowance')f.run('delete controlled.get(7).hold.hasAllowance');
    const pending=f.run(`armDialog(7,${variant==='conservative-upgrade'},${variant==='approved-confirmation'})`);
    if(['free','approved-confirmation'].includes(variant)){const armed=await pending;assert.equal(armed.nonce,'existing');await armed.ready;}
    else await assert.rejects(pending,/no authenticated return boundary/,variant);
  }
});
test('P1 Stop rejects a pending native answer barrier and clears its private begin records',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'epoch'});globalThis.answerReady=new Promise((resolve,reject)=>{preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},epoch:'epoch',documents:new Map(),contexts:new Map(),scripts:new Map(),dialogBarrier:{reject}})});answerReady.catch(()=>{});nativeDialogStarts.set('[7,\"native\"]',[{token:'d1'}]);");
  const ready=assert.rejects(f.run('answerReady'),/interrupted by Stop/);await f.run('release(7)');await ready;
  assert.equal(f.run('nativeDialogStarts.size'),0);assert.equal(f.run('controlled.has(7)'),false);
});
test('P27 native missing-context proof retires stale cleanup handles without a Runtime subscription',async()=>{
  for(const missing of [true,false]){
    const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'epoch'});const context={id:4,uniqueId:'old',origin:'chrome-extension://fixture'};preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},contexts:new Map([[4,context]]),documents:new Map([['old',{main:'old',isolated:'old',document:'private',cleanup:'old-object'}]]),scripts:new Map()});globalThis.cleanupAttempted=false;globalThis.finished=false;chrome.debugger.sendCommand=async(source,method)=>{if(method==='Runtime.callFunctionOn')return {exceptionDetails:{text:'old object unavailable'}};if(method==='Runtime.evaluate'){cleanupAttempted=true;throw Error(globalThis.lookupError)}return {};};");
    f.run(`globalThis.lookupError=${JSON.stringify(missing?'Cannot find context with specified id':'Cannot find object with given id')}`);
    const pending=f.run('release(7).then(value=>{finished=true;return value})');await spin(f,'cleanupAttempted');
    if(!missing){await spin(f,"finished||[...preloadTargets.values()].some(state=>state.cleanupWaiters?.size)");assert.equal(f.run('finished'),false,'an arbitrary object/protocol error is not realm destruction');f.run("preloadTargets.get('[7,null]').contexts.clear();contextChanged(preloadTargets.get('[7,null]'))");}
    const result=await pending;assert.equal(result.cleanup_pending,false);assert.equal(f.run('releasing.size'),0);
  }
});
function unguardedDialogFixture(){
  const f=fixture();f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'epoch'});globalThis.answers=[];chrome.tabs.get=async()=>({url:'http://fixture.test/',title:'Fixture',groupId:1});chrome.webNavigation={getAllFrames:async()=>[]};chrome.debugger={sendCommand:async(source,method,args)=>{if(method==='Page.handleJavaScriptDialog'){answers.push(args);dialogs.delete(7)}return {};}};dialogs.set(7,{id:'borrowed',kind:'prompt',text:'Choose answer',frame:0,frame_url:'http://fixture.test/',unguarded:true});globalThis.expected=JSON.parse(JSON.stringify({session,tab:7,control:'epoch',url:'http://fixture.test/',title:'Fixture',dialog:dialogs.get(7),answer:{accept:true,text:'Chosen text'}}));globalThis.command={name:'dialog',tab:7,operation:'exact-answer',approved:true,input:{accept:true,text:'Chosen text'},binding:expected};");return f;
}
test('P1 decided borrowed dialog approval answers exactly once without clearing existing guards',async()=>{
  const f=unguardedDialogFixture();const result=await f.run('dispatch(command)');assert.equal(result.unguarded_continuation,true);assert.equal(result.needs_reload,false);assert.equal(f.run('controlled.get(7).popupNeedsReload'),undefined);
  assert.deepEqual(JSON.parse(f.run('JSON.stringify(answers)')),[{accept:true,promptText:'Chosen text'}]);
  await assert.rejects(f.run('dispatch(command)'),/stale_approval/);assert.equal(f.run('answers.length'),1);
});
test('P1 decided borrowed dialog refuses changed dialog or chosen answer before dispatch',async()=>{
  for(const change of ["command.input.accept=false","command.input.text='Changed text'","dialogs.get(7).text='Changed dialog'","dialogs.get(7).kind='confirm'","command.approved=false","command.operation=null"]){
    const f=unguardedDialogFixture();f.run(change);await assert.rejects(f.run('dispatch(command)'),/stale_approval|requires its exact approval/);assert.equal(f.run('answers.length'),0,change);assert.equal(f.run('dialogs.has(7)'),true);
  }
});
test('P1 an uncertain borrowed native answer is consumed before dispatch and never replayed',async()=>{
  const f=unguardedDialogFixture();f.run("chrome.debugger.sendCommand=async(source,method,args)=>{if(method==='Page.handleJavaScriptDialog'){answers.push(args);throw Error('native answer response was lost')}return {}};");
  await assert.rejects(f.run('dispatch(command)'),/response was lost/);assert.equal(f.run('answers.length'),1);
  await assert.rejects(f.run('dispatch(command)'),/already attempted/);assert.equal(f.run('answers.length'),1);
});
test('P1 native opening metadata makes borrowed functions ask without downgrading guarded dialogs',async()=>{
  const f=unguardedDialogFixture();f.run("chrome.debugger.onEvent={addListener:callback=>{globalThis.nativeEvent=callback}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'native',url:'http://fixture.test/'}]};controlled.get(7).admitting=true;");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("nativeEvent({tabId:7},'Page.javascriptDialogOpening',{url:'http://fixture.test/',type:'prompt',message:'Already open'})");assert.equal(f.run('dialogs.get(7).unguarded'),true);
  f.run("controlled.get(7).admitting=false;privacyDocuments.set('native','private');nativeDialogStarts.set('[7,\"native\"]',[{kind:'confirm',document:'private',token:'d1'}]);");await f.run("nativeEvent({tabId:7},'Page.javascriptDialogOpening',{url:'http://fixture.test/',type:'confirm',message:'Guarded dialog'})");assert.equal(f.run('dialogs.get(7).unguarded'),undefined);
});

function pendingDialogFixture(){
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/',title:'Fixture'});chrome.webNavigation={getAllFrames:()=>new Promise(resolve=>{globalThis.finishOpeningFrames=resolve})};chrome.debugger={onEvent:{addListener:callback=>{globalThis.nativeEvent=callback}}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  return f;
}
const openingPrompt=f=>f.run("nativeEvent({tabId:7},'Page.javascriptDialogOpening',{url:'http://fixture.test/',type:'prompt',message:'Borrowed native'})");
const finishOpening=f=>f.run("finishOpeningFrames([{frameId:0,documentId:'native',url:'http://fixture.test/'}])");

test('P1 native dialog metadata waits for classification across every read path',async()=>{
  for(const guarded of [false,true])for(const command of ['facts(7)',"dispatch({name:'dialog_facts',tab:7})",'observation(7)']){
    const f=pendingDialogFixture();
    if(guarded)f.run("privacyDocuments.set('native','private');nativeDialogStarts.set('[7,\"native\"]',[{kind:'prompt',document:'private',token:'return'}]);");
    const opening=openingPrompt(f);let settled=false;
    const read=f.run(command).then(value=>{settled=true;return {value}},error=>{settled=true;return {error}});
    for(let turn=0;turn<20;turn++)await Promise.resolve();
    assert.equal(settled,false,'no partial dialog or transient refusal before private classification');
    finishOpening(f);await opening;const result=await read;
    assert.equal(result.error,undefined);assert.equal(result.value.dialog.frame,0);assert.equal(result.value.dialog.browser_document,'native');
    assert.equal(result.value.dialog.unguarded,guarded?undefined:true);
  }
});

test('P1 a dialog opening during the final reader reply cannot escape unclassified',async()=>{
  const f=pendingDialogFixture();
  f.run("const openingFrames=chrome.webNavigation.getAllFrames;globalThis.frameReads=0;chrome.webNavigation.getAllFrames=()=>++frameReads===1?Promise.resolve([{frameId:0,documentId:'native',url:'http://fixture.test/'}]):openingFrames();content=()=>new Promise(resolve=>{globalThis.finishReader=resolve});");
  let settled=false;const read=f.run('facts(7)').then(value=>{settled=true;return {value}},error=>{settled=true;return {error}});
  await spin(f,"typeof finishReader==='function'");const opening=openingPrompt(f);
  f.run("finishReader({document:'private',url:'http://fixture.test/',rows:[]})");
  for(let turn=0;turn<20;turn++)await Promise.resolve();
  assert.equal(settled,false,'the last reader reply must not publish a pending dialog');
  finishOpening(f);await opening;const result=await read;
  assert.equal(result.error,undefined);assert.equal(result.value.dialog.unguarded,true);assert.equal(result.value.dialog.frame,0);assert.equal(result.value.frames.length,0);
});

test('P1 dialog classification waits are bounded and a later completed lookup recovers',async()=>{
  const f=pendingDialogFixture();f.run("globalThis.timers=[];setTimeout=(fn,ms)=>{const timer={fn,ms};timers.push(timer);return timer};clearTimeout=()=>{};");
  const opening=openingPrompt(f),read=assert.rejects(f.run('facts(7)'),/dialog opener is still being established; read again/);
  await spin(f,'timers.length===1');assert.equal(f.run('timers[0].ms'),5000);f.run('timers[0].fn()');await read;
  finishOpening(f);await opening;const current=await f.run('facts(7)');assert.equal(current.dialog.unguarded,true);assert.equal(current.dialog.frame,0);
});
test('P1 the owner may close a borrowed dialog before approval without any tool answer',async()=>{
  const f=unguardedDialogFixture();f.run("chrome.debugger.onEvent={addListener:callback=>{globalThis.nativeEvent=callback}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("nativeEvent({tabId:7},'Page.javascriptDialogClosed',{result:false})");assert.equal(f.run('dialogs.has(7)'),false);await assert.rejects(f.run('dispatch(command)'),/stale_approval/);assert.equal(f.run('answers.length'),0);
});
test('P1 preexisting modal handoff is bounded detaches and recovers the same control after owner answer',async()=>{
  const f=lifecycleFixture();f.run("globalThis.timers=[];setTimeout=(fn,ms)=>{const timer={fn,ms};timers.push(timer);return timer};clearTimeout=()=>{};globalThis.attached=false;globalThis.ownerAnswered=false;globalThis.readerSetups=0;chrome.debugger.attach=async()=>{attached=true};chrome.debugger.detach=async()=>{attached=false;lifecycleCalls.push('detach')};chrome.debugger.sendCommand=async(source,method)=>{if(!attached)throw Error('not attached');if(method==='Page.enable'&&!ownerAnswered)return new Promise(()=>{});return {}};lateReader=async()=>{readerSetups++};chrome.debugger.onDetach={addListener:callback=>{globalThis.nativeDetached=callback}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.debugger.onDetach.addListener('),source.lastIndexOf('connect();')));
  const pending=f.run('globalThis.handedOff=false;take(7).then(value=>{handedOff=true;return value})');await spin(f,'timers.some(timer=>timer.ms===5000)');f.run("globalThis.original=controlled.get(7);original.kept='pending state';timers.find(timer=>timer.ms===5000).fn()");await spin(f,'handedOff');
  const result=await pending;assert.equal(result.owner_dialog,true);assert.match(result.ask_owner,/answer the dialog yourself/);assert.equal(f.run('attached'),false);assert.equal(f.run('preloadTargets.size'),0);assert.equal(f.run('readerSetups'),0);
  await f.run('nativeDetached({tabId:7})');assert.equal(f.run('controlled.get(7)===original'),true);
  f.run('ownerAnswered=true');await f.run('requireTab(7)');assert.equal(f.run('attached'),true);assert.equal(f.run('readerSetups'),1);assert.equal(f.run('controlled.get(7)===original'),true);assert.equal(f.run('original.kept'),'pending state');assert.equal(f.run('original.popupNeedsReload'),true);assert.equal(f.run('original.modalHandoff'),false);
});
test('P1 a responding Page domain may finish slow setup without a false owner handoff',async()=>{
  const f=lifecycleFixture();f.run("globalThis.timers=[];setTimeout=(fn,ms)=>{const timer={fn,ms};timers.push(timer);return timer};clearTimeout=()=>{};lateReader=()=>new Promise(resolve=>{globalThis.finishReader=resolve});globalThis.taken=false;");
  const pending=f.run('take(7).then(value=>{taken=true;return value})');await spin(f,"typeof finishReader==='function'");f.run('timers.find(timer=>timer.ms===5000).fn()');await Promise.resolve();assert.equal(f.run('taken'),false);assert.equal(f.run("lifecycleCalls.includes('detach')"),false);
  f.run('finishReader()');const result=await pending;assert.equal(result.owner_dialog,undefined);assert.equal(f.run('controlled.get(7).modalHandoff'),false);
});
test('P1 a borrowed answer preserves and finishes a previous hold before returning its followups',async()=>{
  const f=unguardedDialogFixture();f.run("controlled.get(7).hold={nonce:'old',inFlight:true};globalThis.finished=false;finishFrames=()=>new Promise(resolve=>{globalThis.finishOld=resolve});chrome.debugger.onEvent={addListener:callback=>{globalThis.nativeEvent=callback}};");
  f.run('globalThis').verifyOldFinished=()=>assert.equal(f.run('controlled.get(7).hold.inFlight'),false,'followup collection waits for the old input completion');f.run('collectSteps=async()=>{verifyOldFinished();return []}');
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  f.run("chrome.debugger.sendCommand=async(source,method,args)=>{if(method==='Page.handleJavaScriptDialog'){answers.push(args);nativeEvent(source,'Page.javascriptDialogClosed',{});}return {}};");
  const pending=f.run('dispatch(command).then(value=>{finished=true;return value})');pending.catch(()=>{});await spin(f,"typeof finishOld==='function'");for(let n=0;n<30;n++)await Promise.resolve();assert.equal(f.run('finished'),false);assert.equal(f.run('controlled.get(7).hold.inFlight'),true);
  f.run('finishOld(false)');await pending;assert.equal(f.run('controlled.get(7).hold.inFlight'),false);assert.equal(f.run('answers.length'),1);
});
test('P23 a borrowed dialog result observes the actual page after its native answer',async()=>{
  const f=unguardedDialogFixture();f.run("globalThis.address='http://fixture.test/';chrome.tabs.get=async()=>({url:address,title:'Fixture',groupId:1});chrome.tabs.sendMessage=async()=>({ok:true,data:{url:address,title:'After native answer',notices:['Native handler completed']}});chrome.debugger.sendCommand=async(source,method,args)=>{if(method==='Page.handleJavaScriptDialog'){answers.push(args);dialogs.delete(7);address='http://fixture.test/after-native';}return {}};");
  const result=await f.run('dispatch(command)');assert.equal(result.page.available,true);assert.equal(result.page.url,'http://fixture.test/after-native');assert.deepEqual(Array.from(result.page.notices),['Native handler completed']);
});

test('P2 native dialogs in blank and srcdoc frames use authenticated private documents',async()=>{
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  for(const address of ['about:blank','about:srcdoc'])for(const authentic of [true,false]){
    const f=fixture();f.run("excludedHosts=[];groupId=1;controlled.set(7,{epoch:'epoch'});chrome.tabs.get=async()=>({url:'http://fixture.test/editor',groupId:1});chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}}};");
    f.run(`chrome.webNavigation={getAllFrames:async()=>[{frameId:0,parentFrameId:-1,documentId:'parent-native',url:'http://fixture.test/editor'},{frameId:2,parentFrameId:0,documentId:'child-native',url:${JSON.stringify(address)}}]};privacyDocuments.set('child-native',${JSON.stringify(authentic?'private-child':'replacement')});preloadTargets.set('child',{tab:7,documents:new Map([['main',{document:'private-child',frameId:'cdp-child',ready:true}]])});nativeDialogStarts.set('[7,"child-native"]',[{kind:'prompt',document:'private-child'}]);`);
    f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
    await f.run(`onEvent({tabId:7},'Page.javascriptDialogOpening',{frameId:'cdp-child',type:'prompt',message:'Inline native prompt',url:${JSON.stringify(address)}})`);
    if(authentic){
      const facts=await f.run("dispatch({name:'dialog_facts',tab:7})");assert.equal(facts.effective_url,'http://fixture.test/editor');assert.equal(facts.dialog.frame,2);assert.equal(facts.dialog.browser_document,'child-native');assert.equal(facts.dialog.unguarded,undefined);assert.equal(facts.dialog.text,'Inline native prompt');
      assert.equal((await f.run('facts(7)')).dialog.frame,2);
      f.run("globalThis.answers=0;armDialog=async()=>({nonce:'armed',frames:[],owner:controlled.get(7),ready:Promise.resolve()});cdp=async()=>{answers++;dialogs.delete(7)};finishFrames=async()=>false;collectSteps=async()=>[];observation=async()=>({available:false})");
      await f.run(`dispatch({name:'dialog',tab:7,binding:${JSON.stringify(facts)},input:{accept:true,text:'Answer'}})`);assert.equal(f.run('answers'),1);
    }else{
      assert.equal(f.run('dialogs.get(7).text'),undefined,'no text retained before inherited opener authentication');await assert.rejects(f.run("dispatch({name:'dialog_facts',tab:7})"),/opener is not yet established/);
    }
  }
});

test('P2 native frame identity distinguishes two documents with the same HTTP address',async()=>{
  const f=fixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'a',url:'http://fixture.test/editor'},{frameId:2,documentId:'b',url:'http://fixture.test/editor'}]};privacyDocuments.set('b','private-child');preloadTargets.set('child',{tab:7,documents:new Map([['main',{document:'private-child',frameId:'cdp-child',ready:true}]])});");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{frameId:'cdp-child',type:'alert',message:'Exact child',url:'http://fixture.test/editor'})");assert.equal(f.run('dialogs.get(7).frame'),2);
});


test('P1 a cross-site dialog arms its authenticated child guard despite root event routing',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});dispatchEpoch='epoch';chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'parent-native',url:'http://fixture.test/'},{frameId:2,documentId:'child-native',url:'http://second.test/'}]};privacyDocuments.set('parent-native','parent-private');privacyDocuments.set('child-native','child-private');preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},documents:new Map([['parent',{document:'parent-private',ready:true}]])});preloadTargets.set('[7,\"child\"]',{tab:7,source:{tabId:7,sessionId:'child'},documents:new Map([['child',{document:'child-private',ready:true}]])});dialogs.set(7,{id:'child-dialog',kind:'confirm',frame:2,browser_document:'child-native'});nativeDialogStarts.set('[7,\"child-native\"]',[{kind:'confirm',token:'native-child-return',dialog:'child-dialog',document:'child-private'}]);");
  const result=await f.run('armDialog(7)');assert.equal(result.frames.length,2);assert.equal(f.run("preloadTargets.get('[7,null]').dialogBarrier"),undefined);assert.equal(f.run("preloadTargets.get('[7,\"child\"]').dialogBarrier.token"),'native-child-return');assert.equal(f.run("preloadTargets.get('[7,\"child\"]').dialogBarrier.documents.length"),2);
  f.run("nativeDialogStarts.get('[7,\"child-native\"]')[0].dialog='another-opening'");await assert.rejects(f.run('armDialog(7)'),/no authenticated return boundary/);
});

test('P19 root navigation retires descendant records before a renderer reuses context numbers',async()=>{
  const f=startupFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');await f.run('prepareTarget({tabId:7})');await startupContexts(f,'first');await paused(f,'first');
  f.run("preloadTargets.get('[7,null]').frameId='frame';preloadTargets.get('[7,null]').contexts.get(2).auxData.frameId='old-child';chrome.debugger.onEvent={addListener:fn=>{globalThis.onEvent=fn}};");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("onEvent({tabId:7},'Page.frameNavigated',{frame:{id:'frame',loaderId:'second-native-document'}})");
  assert.equal(f.run("preloadTargets.get('[7,null]').documents.size"),0);assert.equal(f.run("preloadTargets.get('[7,null]').contexts.size"),0);
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'reused',executionContextId:2,url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})");await paused(f,'reused');
  assert.equal(f.run("startup.filter(row=>row.method==='Runtime.evaluate'&&row.parameters.expression.includes('guard fixture')).length"),2,'both native documents install before page code');
  assert.equal(f.run("preloadTargets.get('[7,null]').documents.get('isolated-2-navigation-1').ready"),true);
  const before=f.run("preloadTargets.get('[7,null]').documents.size");await f.run("onEvent({tabId:7},'Page.frameNavigated',{frame:{id:'unrelated-child',parentId:'frame'}})");assert.equal(f.run("preloadTargets.get('[7,null]').documents.size"),before,'a child navigation cannot retire the current parent guard');
});

test('P19 a cancelled startup cannot evaluate or resume a reused native context',async()=>{
  const f=startupFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');await f.run('prepareTarget({tabId:7})');await startupContexts(f,'old');
  f.run("preloadTargets.get('[7,null]').frameId='frame';preloadBundle=new Promise(resolve=>{globalThis.oldBundle=resolve});chrome.debugger.onEvent={addListener:fn=>{globalThis.onEvent=fn}};");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  const old=paused(f,'old');await spin(f,"typeof oldBundle==='function'");
  await f.run("onEvent({tabId:7},'Page.frameNavigated',{frame:{id:'frame',loaderId:'replacement'}})");
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'replacement',executionContextId:2,url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  f.run("oldBundle(['// guard fixture','// reader fixture','// wrapper fixture'])");await old;
  assert.equal(f.run("startup.filter(row=>row.method==='Runtime.evaluate').length"),0,'old setup cannot run in the replacement context');assert.equal(f.run("startup.filter(row=>row.method==='Debugger.resume').length"),0,'old setup cannot release a replacement pause');
  await paused(f,'replacement');assert.equal(f.run("preloadTargets.get('[7,null]').documents.get('isolated-2-navigation-1').ready"),true);assert.equal(f.run("startup.filter(row=>row.method==='Debugger.resume').length"),1);
});


test('P1 a private native token cannot authenticate a second dialog before its end message arrives',async()=>{
  const f=fixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});privacyDocuments.set('native','private');nativeDialogStarts.set('[7,\"native\"]',[{kind:'confirm',token:'first',document:'private'}]);globalThis.answers=[];chrome.debugger={onEvent:{addListener:fn=>{globalThis.onEvent=fn}}};chrome.webNavigation={getAllFrames:async()=>[{frameId:0,documentId:'native',url:'http://fixture.test/'}]};armDialog=async()=>({frames:[],nonce:'nonce',ready:Promise.resolve(),owner:controlled.get(7)});finishFrames=async()=>false;cdp=async()=>{answers.push('answered')};confirmationPlans.set(7,{browser_document:'native',expected:{kind:'confirm',text:'Delete expected?',frame_url:'http://fixture.test/',button:'OK',frame:0},matched:[]});");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'First native',url:'http://fixture.test/'})");assert.equal(f.run('dialogs.get(7).unguarded'),undefined);
  await f.run("onEvent({tabId:7},'Page.javascriptDialogClosed',{})");
  await f.run("onEvent({tabId:7},'Page.javascriptDialogOpening',{type:'confirm',message:'Delete expected?',url:'http://fixture.test/'})");assert.equal(f.run('dialogs.get(7).unguarded'),true);assert.equal(f.run('answers.length'),0,'a delayed private end cannot let a borrowed dialog inherit an approved confirmation');assert.ok(f.run('confirmationPlans.get(7).expected'));
});

test('P1 a dialog changed during the final native frame query refuses before answering',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/'});chrome.webNavigation={getAllFrames:()=>new Promise(resolve=>{globalThis.framesReady=resolve})};privacyDocuments.set('native','private');preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},documents:new Map([['doc',{document:'private',ready:true}]])});dialogs.set(7,{id:'original',kind:'confirm',frame:0,frame_url:'http://fixture.test/',browser_document:'native'});nativeDialogStarts.set('[7,\"native\"]',[{kind:'confirm',token:'one',dialog:'original',document:'private'}]);globalThis.expected={session,tab:7,control:'epoch',url:'http://fixture.test/',dialog:dialogs.get(7)};globalThis.answers=0;cdp=async()=>{answers++;preloadTargets.get('[7,null]').dialogBarrier.resolve()};finishFrames=async()=>false;collectSteps=async()=>[];observation=async()=>({available:false});");
  const pending=f.run("dispatch({name:'dialog',tab:7,binding:expected,input:{accept:true},operation:'old-answer'})");await spin(f,"typeof framesReady==='function'");
  f.run("dialogs.set(7,{id:'replacement',kind:'confirm',frame:0,frame_url:'http://fixture.test/',browser_document:'native'});nativeDialogStarts.set('[7,\"native\"]',[{kind:'confirm',token:'two',dialog:'replacement',document:'private'}]);framesReady([{frameId:0,documentId:'native',url:'http://fixture.test/'}])");
  await assert.rejects(pending,/stale_approval: dialog changed/);assert.equal(f.run('answers'),0);assert.equal(f.run("used.has('old-answer')"),false);assert.equal(f.run('controlled.get(7).hold'),undefined);
});


test('catalogue snapshots survive active pagination and expire after five idle minutes',async()=>{
  const f=fixture();f.run("globalThis.now=0;Date.now=()=>now;globalThis.queries=0;chrome.history={search:async()=>{queries++;return Array.from({length:8},(_,id)=>({id:String(id),url:'http://fixture.test/'+id}))}};");
  let page=await f.run("collection({name:'history',text:'fixture.test',limit:1})"),items=[...page.items];
  for(let index=0;index<5;index++){f.run('now+=250000');page=await f.run(`collection({name:'history',text:'fixture.test',limit:1,cursor:${JSON.stringify(page.cursor)}})`);items.push(...page.items);}
  assert.deepEqual(items.map(item=>item.id),['0','1','2','3','4','5']);assert.equal(f.run('queries'),1,'active pages use the original immutable snapshot');
  f.run('now+=300001');await assert.rejects(f.run(`collection({name:'history',text:'fixture.test',limit:1,cursor:${JSON.stringify(page.cursor)}})`),/snapshot changed/);assert.equal(f.run('queries'),1,'expired cursors never silently restart');
});

test('P1 a private end pause retires unclaimed authority before resume and rejects a late begin',async()=>{
  const f=startupFixture();await f.run('prepareTarget({tabId:7})');await startupContexts(f,'private');await paused(f,'private');
  f.run("privacyDocuments.set('native','private-document');nativeDialogStarts.set('[7,\"native\"]',[{kind:'confirm',token:'ended-token',document:'private-document'}]);const send=chrome.debugger.sendCommand;chrome.debugger.sendCommand=async(source,method,args)=>{if(method==='Runtime.evaluate'&&args.expression.includes('dialogBoundary'))return {result:{value:{document:'private-document',token:'ended-token'}}};if(method==='Debugger.resume'&&nativeDialogStarts.size)throw Error('Private authority survived the native return');return send(source,method,args)};");
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'guard-native-end',executionContextId:2,url:'',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  await f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[],callFrames:[{location:{scriptId:'guard-native-end'}}]})");assert.equal(f.run('nativeDialogStarts.size'),0);assert.equal(f.run("nativeDialogEnds.has('[7,\"private-document\",\"ended-token\"]')"),true);
  f.run("chrome.runtime.id='fixture-extension';chrome.runtime.onMessage={addListener:fn=>{globalThis.onMessage=fn}};");
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');f.run(source.slice(source.indexOf('chrome.runtime.onMessage.addListener('),source.indexOf('chrome.tabs.onUpdated.addListener(')));
  f.run("onMessage({event:'native_dialog_boundary',phase:'begin',generation:'epoch',document:'private-document',token:'ended-token',kind:'confirm'},{id:'fixture-extension',tab:{id:7},documentId:'native'},()=>{})");assert.equal(f.run('nativeDialogStarts.size'),0,'an asynchronous old begin cannot resurrect an ended native call');
});

test('P1 an old private end query cannot resume a replacement startup',async()=>{
  const f=startupFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');await f.run('prepareTarget({tabId:7})');await startupContexts(f,'first');await paused(f,'first');
  f.run("preloadTargets.get('[7,null]').frameId='frame';const send=chrome.debugger.sendCommand;chrome.debugger.sendCommand=(source,method,args)=>method==='Runtime.evaluate'&&args.expression.includes('dialogBoundary')?new Promise(resolve=>{globalThis.endReply=resolve}):send(source,method,args);chrome.debugger.onEvent={addListener:fn=>{globalThis.onEvent=fn}};");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'old-private-end',executionContextId:2,url:'',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  const old=f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[],callFrames:[{location:{scriptId:'old-private-end'}}]})");await spin(f,"typeof endReply==='function'");
  await f.run("onEvent({tabId:7},'Page.frameNavigated',{frame:{id:'frame'}})");await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'new-startup',executionContextId:2,url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  f.run("preloadBundle=new Promise(resolve=>{globalThis.newBundle=resolve})");const next=paused(f,'new-startup');await spin(f,"typeof newBundle==='function'");f.run("endReply({result:{value:{document:'private-document',token:'old-token'}}})");await old;
  assert.equal(f.run("startup.filter(row=>row.method==='Debugger.resume').length"),1,'only the first completed startup has resumed');f.run("newBundle(['// guard fixture','// reader fixture','// wrapper fixture'])");await next;assert.equal(f.run("startup.filter(row=>row.method==='Debugger.resume').length"),2);
});

test('P1 an old dialog return query cannot poison a replacement document',async()=>{
  const f=startupFixture(),source=fs.readFileSync('control/chrome/extension/background.js','utf8');await f.run('prepareTarget({tabId:7})');await startupContexts(f,'first');await paused(f,'first');
  f.run("const state=preloadTargets.get('[7,null]');state.frameId='frame';const doc=state.documents.get('isolated-2');controlled.get(7).hold={nonce:'old-hold',config:POLICY,inFlight:false,until:0};globalThis.barrierReady=new Promise((resolve,reject)=>{state.dialogBarrier={nonce:'old-hold',token:'old-token',documents:[{state,doc}],source:{state,doc},resolve,reject}});barrierReady.catch(()=>{});const send=chrome.debugger.sendCommand;chrome.debugger.sendCommand=(source,method,args)=>method==='Runtime.evaluate'&&args.expression.includes('dialogBoundary')?new Promise(resolve=>{globalThis.oldReturn=resolve}):send(source,method,args);chrome.debugger.onEvent={addListener:fn=>{globalThis.onEvent=fn}};");
  f.run(source.slice(source.indexOf('chrome.debugger.onEvent.addListener('),source.indexOf('chrome.debugger.onDetach.addListener(')));
  const old=f.run("preloadEvent({tabId:7},'Debugger.paused',{hitBreakpoints:[]})");await spin(f,"typeof oldReturn==='function'");
  await f.run("onEvent({tabId:7},'Page.frameNavigated',{frame:{id:'frame'}})");await f.run("preloadEvent({tabId:7},'Debugger.scriptParsed',{scriptId:'replacement-startup',executionContextId:2,url:'chrome-extension://fixture/context.js',executionContextAuxData:{isDefault:false,frameId:'frame'}})");
  f.run("preloadBundle=new Promise(resolve=>{globalThis.replacementBundle=resolve})");const next=paused(f,'replacement-startup');f.run("oldReturn({result:{value:{document:'private-document',token:'old-token'}}})");await old;
  await assert.rejects(f.run('barrierReady'),/source changed|context disappeared/);assert.equal(f.run('controlled.get(7).dialogPauseFailed'),undefined,'the old failure cannot disable the replacement control');assert.equal(f.run("startup.filter(row=>row.method==='Debugger.resume').length"),1);
  f.run("replacementBundle(['// guard fixture','// reader fixture','// wrapper fixture'])");await next;assert.equal(f.run("preloadTargets.get('[7,null]').documents.get('isolated-2-navigation-1').ready"),true);
});

test('recheck confirmation form binds outside drafts at final dispatch and requires complete coverage',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'OK',page_dialog:{text:'Send this message?'}},form:{element:'f1',method:'dialog',fields:[]},editable:[{element:'draft',value:'Approved draft'}]}]};facts=async()=>snapshot;content=async()=>({});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'confirmation',false)));snapshot.frames[0].editable[0].value='Different draft';");
  assert.ok(f.run('approved.editable'));
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'confirmation',binding:approved})"),/page changed/);assert.equal(f.run('effects.length'),0);
  f.run('snapshot.uncovered=[{eligible:true}]');assert.throws(()=>f.run("binding(snapshot,{frame:0},'confirmation',false)"),/complete draft/);
});

test('recheck payment dispatch refuses a changed item quantity',async()=>{
  const f=fixture();
  f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Pay'},item:'Unit price 25 Pay',item_fields:[{element:'quantity',label:'Quantity',value:'1'}]}]};facts=async()=>snapshot;content=async()=>({});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'pay',false)));snapshot.frames[0].item_fields[0].value='2';");
  assert.equal(f.run('approved.item_fields[0].value'),'1');
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'pay',binding:approved})"),/page changed/);assert.equal(f.run('effects.length'),0);
});

test('recheck2 session default blocks are tab scoped cover every resource and expire exactly once',async()=>{
  const f=fixture();f.run("controlled.set(7,{epoch:'epoch'});globalThis.timers=[];setTimeout=(fn,delay)=>{timers.push({fn,delay});return timers.length};clearTimeout=()=>{};");
  await f.run("holdDefaults(7,'old')");await f.run("holdDefaults(7,'current')");
  const block=f.rules.at(-1).addRules.find(rule=>rule.id===2);
  assert.deepEqual(JSON.parse(JSON.stringify(block.condition.tabIds)),[7]);
  assert.deepEqual(JSON.parse(JSON.stringify(block.condition.resourceTypes)),['main_frame','sub_frame','ping','other']);
  f.run("expireDefaults(7,'old');expireDefaults(7,'current')");assert.equal(f.run('timers.length'),1);
  assert.equal(f.run('timers[0].delay'),500);f.run('timers[0].fn()');await f.run('ruleUpdates');
  assert.equal(f.rules.at(-1).addRules.some(rule=>rule.id===2),false);
});
test('recheck2 startup reconciles a surviving session block before the native handshake',async()=>{
  const f=fixture();f.run("chrome.declarativeNetRequest.getSessionRules=async()=>[{id:1},{id:2}]");await f.run('rules()');
  assert.deepEqual(JSON.parse(JSON.stringify(f.rules.at(-1))),{removeRuleIds:[1,2],addRules:[]});
  const source=fs.readFileSync('control/chrome/extension/background.js','utf8');
  const connect=source.slice(source.indexOf('async function connect()'),source.indexOf('chrome.runtime.onMessage.addListener('));
  assert.ok(connect.indexOf('await rules()')<connect.indexOf('chrome.runtime.connectNative'));
});
test('recheck2 release removes a live default block before blocked wrapper cleanup',async()=>{
  const f=lifecycleFixture();f.run("controlled.set(7,{epoch:'epoch'});preloadTargets.set('[7,null]',{tab:7,source:{tabId:7},contexts:new Map(),documents:new Map([['main',{cleanup:'handle'}]]),installing:new Set()});chrome.debugger.sendCommand=()=>new Promise(()=>{});globalThis.timerCallbacks=[];setTimeout=(callback,delay)=>{timerCallbacks.push({callback,delay})};");
  await f.run("holdDefaults(7,'nonce')");assert.ok(f.rules.at(-1).addRules.some(rule=>rule.id===2));
  const pending=f.run('release(7)');await f.run('ruleUpdates');await spin(f,"timerCallbacks.some(timer=>timer.delay===1000)");
  assert.equal(f.rules.at(-1).addRules.some(rule=>rule.id===2),false);
  f.run('timerCallbacks.find(timer=>timer.delay===1000).callback()');assert.equal((await pending).cleanup_pending,true);
});

test('recheck2 final extension binding refuses a changed compose preview before native input',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Send'},form:null,editable:[{value:'Draft'}],compose:{element:'area',text:'Original preview'}}]};facts=async()=>snapshot;content=async()=>({});pointer=async()=>({x:1,y:1});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'send',false)));snapshot.frames[0].compose.text='Changed preview';");
  await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'send',binding:approved})"),/page changed/);assert.equal(f.run('effects.length'),0);
});

test('2c private clipboard facts survive frame navigation and carry no written content',async()=>{
  const f=stepFixture();
  f.run("privacyDocuments.set('native-old','old-document');globalThis.clip=(route,generation='epoch',sender={id:'fixture-extension',tab:{id:7},frameId:2,documentId:'native-old'})=>{let result;runtimeListener({event:'clipboard_write',document:'old-document',route,generation},sender,value=>result=value);return result;}");
  assert.equal(f.run("clip('writeText').received"),true);
  f.run("currentDocuments.set('[7,2]','native-new');content=async()=>{throw Error('Old frame document gone')};chrome.tabs.get=async()=>({url:'http://fixture.test/new-document',title:'New page'})");
  const report=JSON.parse(JSON.stringify(await f.run("observation(7,{frame:2},'epoch')")));
  assert.equal(report.available,false);assert.equal(report.url,'http://fixture.test/new-document');
  assert.deepEqual(report.clipboard,{written:true,message:'The page wrote to the clipboard.',routes:['writeText']});assert.equal(f.run("clipboardObservation(7,'epoch')"),null);
});
test('2c clipboard messages cannot cross sender identity control epoch or route boundaries',()=>{
  const f=stepFixture();f.run("globalThis.clip=(message,sender)=>{let result;runtimeListener(message,sender,value=>result=value);return result;}");
  for(const [message,sender]of [
    [{event:'clipboard_write',document:'d',route:'writeText',generation:'epoch'},{id:'page',tab:{id:7},frameId:0}],
    [{event:'clipboard_write',document:'d',route:'writeText',generation:'old'},{id:'fixture-extension',tab:{id:7},frameId:0}],
    [{event:'clipboard_write',document:'d',route:'readText',generation:'epoch'},{id:'fixture-extension',tab:{id:7},frameId:0}],
  ]){f.run(`clip(${JSON.stringify(message)},${JSON.stringify(sender)})`);assert.equal(f.run("clipboardObservation(7,'epoch')"),null);}
});


test('recheck3 final extension binding catches indentation and linebreak drift before native dispatch',async()=>{
  for(const next of ['if approved:\n    send()\n    audit()','if approved:\n    send() audit()']){
    const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Send'},form:null,editable:[{value:'Draft'}],compose:{element:'area',text:'if approved:\\n    send()\\naudit()'}}]};facts=async()=>snapshot;content=async()=>({});pointer=async()=>({x:1,y:1});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'send',false)));");
    f.run('snapshot.frames[0].compose.text='+JSON.stringify(next));
    await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'send',binding:approved})"),/page changed/);assert.equal(f.run('effects.length'),0);
  }
});

test('recheck3 private cross-document wiring uses the native MAIN context observed during factory setup',async()=>{
  const f=startupFixture();await f.run('prepareTarget({tabId:7})');await startupContexts(f,'private');
  f.run("const nativeSend=chrome.debugger.sendCommand;chrome.debugger.sendCommand=async(source,method,parameters)=>{if(method==='Runtime.callFunctionOn'&&parameters.functionDeclaration.includes('wrapper fixture'))await preloadEvent(source,'Debugger.scriptParsed',{scriptId:'private-factory',executionContextId:33,url:'',executionContextAuxData:{isDefault:true,frameId:'frame'}});return nativeSend(source,method,parameters);}");
  await paused(f,'private');assert.equal(f.run("[...preloadTargets.get('[7,null]').documents.values()][0].mainContext"),33);
  assert.equal(f.run("startup.some(row=>row.method==='Runtime.enable')"),false);
});

test('recheck3 private cross-document wiring rejects mismatched native carriers and caches only authenticated links',async()=>{
  const f=lifecycleFixture();f.run("globalThis.wiring=[];globalThis.acceptLink=false;controlled.set(7,{epoch:'a'});controlled.set(8,{epoch:'b'});for(const [tab,epoch,context]of [[7,'a',17],[8,'b',18],[9,'outside',19]])preloadTargets.set(JSON.stringify([tab,null]),{tab,epoch,source:{tabId:tab},contexts:new Map([[context+10,{id:context+10,uniqueId:epoch+'-isolated'}]]),documents:new Map([[epoch,{isolated:epoch+'-isolated',mainContext:context,cleanup:epoch+'-factory',backend:context,relayKey:'data-private-'+epoch,relayValue:'nonce-'+epoch}]])});chrome.debugger.sendCommand=async(source,method,parameters)=>{wiring.push({source,method,parameters});return method==='DOM.resolveNode'?{object:{objectId:'private-node-in-'+parameters.executionContextId}}:{result:{value:acceptLink}};}");
  await f.run('linkPrivateDocuments()');assert.equal(f.run("[...preloadTargets.values()].flatMap(state=>[...state.documents.values()]).some(doc=>doc.links?.size)"),false);
  f.run('acceptLink=true');await f.run('linkPrivateDocuments()');
  const commands=JSON.parse(f.run('JSON.stringify(wiring)'));assert.ok(commands.every(row=>row.source.tabId!==9));
  assert.deepEqual(commands.filter(row=>row.method==='DOM.resolveNode').map(row=>[row.source.tabId,row.parameters.executionContextId,row.parameters.backendNodeId]),[[7,27,18],[8,28,17],[7,27,18],[8,28,17],[7,17,18],[8,18,17]]);
  const length=commands.length;await f.run('linkPrivateDocuments()');assert.equal(f.run('wiring.length'),length);
  f.run("controlled.delete(8);[...preloadTargets.values()].forEach(state=>state.documents.forEach(doc=>doc.links?.clear()))");await f.run('linkPrivateDocuments()');assert.equal(f.run('wiring.length'),length);
});

test('post18d final destination binding refuses href targets actions and form owners before native input',async()=>{
  for(const [object,key,value] of [['target','href','http://fixture.test/second/delete'],['target','browsing_target','second'],['form','action','http://fixture.test/second/delete'],['form','target','second'],['form','browsing_target','second'],['form','element','second']]){
    const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Delete',href:'http://fixture.test/first/delete',browsing_target:'first'},form:{element:'f1',action:'http://fixture.test/first/delete',target:'first',browsing_target:'first',fields:[]}}]};facts=async()=>snapshot;content=async()=>({});pointer=async()=>({x:1,y:1});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'delete',false)));");
    f.run(`snapshot.frames[0][${JSON.stringify(object)}][${JSON.stringify(key)}]=${JSON.stringify(value)}`);
    await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'delete',binding:approved})"),/page changed/);assert.equal(f.run('effects.length'),0);
  }
});

test('post18d typed reads require approval consume once and check the complete list before extracting',async()=>{
  const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});globalThis.list={session,tab:7,control:'epoch',url:'http://fixture.test/',title:'Fixture',frames:[{frame:0,document:'doc',browser_document:'native-doc',fields:[{element:'e1',label:'Draft',type:'text'}]}]};typedFacts=async()=>JSON.parse(JSON.stringify(list));globalThis.reads=0;content=async()=>{reads++;return {document:'doc',fields:[{element:'e1',value:'Public typed text'}]}};globalThis.command={name:'read_typed_fields',tab:7,operation:'first',binding:JSON.parse(JSON.stringify(list))};");
  await assert.rejects(f.run('dispatch(command)'),/fresh one-call approval/);assert.equal(f.run('reads'),0);
  const value=await f.run('dispatch({...command,approved:true})');assert.equal(value.frames[0].fields[0].value,'Public typed text');assert.equal(f.run('reads'),1);
  await assert.rejects(f.run('dispatch({...command,approved:true})'),/fresh one-call approval/);assert.equal(f.run('reads'),1);
  f.run("list.frames[0].fields[0].label='Changed';command.operation='second';");
  await assert.rejects(f.run('dispatch({...command,approved:true})'),/list or document changed/);assert.equal(f.run('reads'),1);
});

test('post18df asking preparation uses value-free frame metadata and binds reader plus native document identity',async()=>{
  for(const change of ['element','reader','frame']){
    const f=fixture();await f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({url:'http://fixture.test/',title:'Fixture'});globalThis.nativeFrames=[{frameId:0,parentFrameId:-1,documentId:'native-doc',url:'http://fixture.test/'}];chrome.webNavigation={getAllFrames:async()=>nativeFrames};globalThis.metadata={document:'doc',reader:'reader-one',origin:'http://fixture.test',url:'http://fixture.test/',title:'Fixture',fields:[{element:'first',label:'Draft',type:'text'},{element:'second',label:'Draft',type:'textarea'}]};globalThis.valueReads=0;globalThis.metadataCommands=[];content=async(tab,frame,command)=>{metadataCommands.push(command);if(command==='typed_fields')return JSON.parse(JSON.stringify(metadata));if(command==='read_typed_fields'){valueReads++;return {fields:[]}}throw Error('Preparation attempted an ordinary value read');};(async()=>{globalThis.prepared=await typedFacts(7)})()");
    assert.deepEqual(JSON.parse(f.run('JSON.stringify(metadataCommands)')),['typed_fields']);assert.equal(f.run('valueReads'),0);assert.equal(f.run('prepared.frames[0].reader'),'reader-one');assert.equal(f.run('prepared.frames[0].fields.length'),2);
    if(change==='element')f.run("metadata.fields[0].element='same-label-replacement'");
    if(change==='reader')f.run("metadata.reader='reader-two'");
    if(change==='frame')f.run("nativeFrames[0].documentId='new-native-document'");
    await assert.rejects(f.run("dispatch({name:'read_typed_fields',tab:7,approved:true,operation:'old',binding:prepared})"),/list or document changed/);assert.equal(f.run('valueReads'),0);
  }
});

test('post18df final native boundary refuses forms holding withheld content even after frame arming',async()=>{
  for(const late of [false,true]){
    const f=fixture();f.run("excludedHosts=[];controlled.set(7,{epoch:'epoch'});requireTab=async()=>({});globalThis.effects=[];globalThis.snapshot={tab:7,frames:[{frame:0,document:'doc',target:{element:'e1',name:'Send',submit:true},form:{element:'f1',action:'http://fixture.test/receive',method:'post',fields:[]}}]};facts=async()=>snapshot;content=async(tab,frame,name)=>{if(name==='arm'&&globalThis.late)snapshot.frames[0].form.fields.push({unknown_history:true,value_status:'filled'});return {finished:true}};pointer=async()=>({x:1,y:1});chrome.tabs={get:async()=>({active:true})};chrome.webNavigation={getAllFrames:async()=>[{frameId:0}]};chrome.debugger={sendCommand:async()=>effects.push('input')};globalThis.approved=JSON.parse(JSON.stringify(binding(snapshot,{frame:0},'send',false)));");
    f.run(`globalThis.late=${late};${late?'':"snapshot.frames[0].form.fields.push({unknown_history:true,value_status:'filled'});"}`);
    await assert.rejects(f.run("dispatch({name:'input',tab:7,reference:{frame:0,element:'e1'},input:{verb:'click'},kind:'send',binding:approved})"),/send it yourself, or reload the tab first with chrome_navigate direction=reload/);assert.equal(f.run('effects.length'),0);
  }
});
