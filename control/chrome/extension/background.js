import {POLICY} from './policy.js';

const session = crypto.randomUUID();
const controlled = new Map(), used = new Set(), dialogs = new Map();
const retiredControls=new Map();
function stepControl(tab,epoch){return controlled.get(tab)?.epoch===epoch?controlled.get(tab):releasing.get(tab)?.original.epoch===epoch?releasing.get(tab).original:retiredControls.get(JSON.stringify([tab,epoch]));}
function stepStates(tab){return [...new Set([controlled.get(tab),releasing.get(tab)?.original,...[...retiredControls].filter(([key])=>JSON.parse(key)[0]===tab).map(([,value])=>value)].filter(Boolean))];}
let groupId = null, port = null, serial = Promise.resolve(), recording = false, effectStarted = false, dispatchEpoch = null;
let excludedHosts = null;
const listSnapshots = new Map(), fixtureBarriers = new Map();
const ownerRequests = new Map(), stagedUploads = new Map(), confirmationPlans = new Map(), dialogWake = new Map();
const dialogInputs=new WeakMap();
const preloadTargets=new Map();
const releasing=new Map(),admissions=new Map();
let stopGeneration=0;
let badgeUpdates=Promise.resolve();
const badgedTabs=new Set();
const documentMethods=new Map(),currentDocuments=new Map(),formLoadedDocuments=new Map();
function navigationRecord(map,key,value){map.delete(key);map.set(key,value);if(map.size>20000)map.delete(map.keys().next().value);}
const targetKey=source=>JSON.stringify([source.tabId,source.sessionId||null]);
let preloadBundle;
const bundle=()=>preloadBundle??=Promise.all(['guard.js','reader.js','page.js'].map(async file=>(await fetch(chrome.runtime.getURL(file))).text()));
async function preloadCommand(source,method,parameters={}){
  if(!POLICY.cdpMethods.includes(method))throw Error('permission_denied: DevTools method not allowed');
  return audit(await chrome.debugger.sendCommand(source,method,parameters));
}
function assertTarget(state){if(preloadTargets.get(targetKey(state.source))!==state||controlled.get(state.tab)?.epoch!==state.epoch)throw Error('stale_reference: control ended during document setup');}
function contextChanged(state){for(const done of state.cleanupWaiters||[])done();state.cleanupWaiters?.clear();}
function destroyedTarget(state){state.contexts.clear();state.scripts.clear();state.documents.clear();state.failures?.clear();contextChanged(state);if(preloadTargets.get(targetKey(state.source))===state)preloadTargets.delete(targetKey(state.source));}
async function contextGone(state,identity){
  while([...state.contexts.values()].some(context=>context.uniqueId===identity)){
    if(state.detached&&state.targetId)try{if(!(await chrome.debugger.getTargets()).some(target=>target.id===state.targetId)){destroyedTarget(state);return;}}catch{}
    let done,timer;
    await new Promise(resolve=>{done=resolve;state.cleanupWaiters??=new Set();state.cleanupWaiters.add(done);if(state.detached)timer=setTimeout(resolve,250);});
    state.cleanupWaiters.delete(done);if(timer!==undefined)clearTimeout(timer);
  }
}
async function targetCommand(state,method,parameters={}){assertTarget(state);const value=await preloadCommand(state.source,method,parameters);assertTarget(state);return value;}
async function prepareTarget(source,tab=source.tabId,targetId=null){
  const state={source,tab,targetId,epoch:controlled.get(tab)?.epoch,contexts:new Map(),scripts:new Map(),documents:new Map(),failures:new Map(),installing:new Set()};preloadTargets.set(targetKey(source),state);
  await targetCommand(state,'Page.enable');
  const tree=await targetCommand(state,'Page.getFrameTree');state.frameId=tree.frameTree?.frame.id||targetId;
  await targetCommand(state,'Runtime.enable');
  await targetCommand(state,'Debugger.enable');
  const breakpoint=await targetCommand(state,'Debugger.setBreakpointByUrl',{url:chrome.runtime.getURL('context.js'),lineNumber:1});
  state.breakpoint=breakpoint.breakpointId;
  await targetCommand(state,'Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:true,flatten:true,filter:[{type:'iframe',exclude:false}]});
  return state;
}
async function preloadEvent(source,method,params){
  if(method==='Target.attachedToTarget'){
    const parent=preloadTargets.get(targetKey(source));if(!parent||controlled.get(parent.tab)?.epoch!==parent.epoch)return;
    const child={...source,sessionId:params.sessionId};
    try{
      if(params.targetInfo.type!=='iframe')throw Error('refused: only frame startup is auto-attached');
      assertTarget(parent);const prepared=await prepareTarget(child,parent.tab,params.targetInfo.targetId);await targetCommand(prepared,'Runtime.runIfWaitingForDebugger');
    }
    catch(error){port?.postMessage({event:'reader_error',error:String(error),tab:parent.tab});try{await preloadCommand(source,'Target.detachFromTarget',{sessionId:params.sessionId});}catch{}}
    return;
  }
  const state=preloadTargets.get(targetKey(source));if(!state)return;
  if(method==='Target.detachedFromTarget'){
    const child=preloadTargets.get(targetKey({...source,sessionId:params.sessionId}));if(!child)return;
    child.detached=true;
    contextChanged(child);
    let destroyed=false;try{destroyed=!!child.targetId&&!(await chrome.debugger.getTargets()).some(target=>target.id===child.targetId);}catch{}
    // Detachment alone does not prove that a live page lost its wrappers.
    // Only a missing native target or actual tab removal ends that lifetime.
    if(destroyed)destroyedTarget(child);
    // An iframe session can detach during an ordinary process/frame swap while
    // its old target is still listed. That is not the end of its parent's control.
    // Retain its cleanup handles until native frame/target destruction is known.
    const owner=controlled.get(child.tab);
    if(child.tab!==state.tab&&owner&&owner.epoch===child.epoch)await release(child.tab);return;
  }
  if(method==='Runtime.executionContextCreated'){state.contexts.set(params.context.id,params.context);return;}
  if(method==='Runtime.executionContextDestroyed'){const old=state.contexts.get(params.executionContextId);state.contexts.delete(params.executionContextId);for(const [script,context]of state.scripts)if(context===params.executionContextId)state.scripts.delete(script);for(const [key,document]of state.documents)if(document.main===old?.uniqueId)state.documents.delete(key);else if(document.isolated===old?.uniqueId)document.ready=false;for(const [key,failure]of state.failures||[])if(old?.uniqueId&&(failure.main===old.uniqueId||failure.isolated===old.uniqueId))state.failures.delete(key);contextChanged(state);return;}
  if(method==='Runtime.executionContextsCleared'){state.contexts.clear();state.scripts.clear();state.documents.clear();state.failures?.clear();contextChanged(state);return;}
  if(method==='Debugger.scriptParsed'){if(params.url===chrome.runtime.getURL('context.js'))state.scripts.set(params.scriptId,params.executionContextId);return;}
  if(method!=='Debugger.paused')return;
  const pause=Symbol();state.pause=pause;let startup;
  const sameDocument=()=>!startup||state.contexts.get(startup.main.id)?.uniqueId===startup.main.uniqueId&&state.contexts.get(startup.isolated.id)?.uniqueId===startup.isolated.uniqueId;
  let complete;const installing=new Promise(resolve=>{complete=resolve;});state.installing??=new Set();state.installing.add(installing);
  try{
    assertTarget(state);
    if(!params.hitBreakpoints?.includes(state.breakpoint))return;
    const context=state.contexts.get(state.scripts.get(params.callFrames[0].location.scriptId));
    if(context?.origin!==chrome.runtime.getURL('').replace(/\/$/,'')||context.auxData?.isDefault!==false)throw Error('refused: startup context identity is unavailable');
    const main=[...state.contexts.values()].find(value=>value.auxData?.isDefault&&value.auxData.frameId===context.auxData.frameId);
    if(!main?.uniqueId||!context.uniqueId)throw Error('refused: startup document identity is unavailable');
    startup={main,isolated:context};
    if(state.documents.has(main.uniqueId))return;
    const [guard,reader,page]=await bundle();
    assertTarget(state);
    const isolated=await targetCommand(state,'Runtime.evaluate',{uniqueContextId:context.uniqueId,expression:guard+'\n'+reader+'\n;globalThis[Symbol.for("aresos.chrome.guard.v2")].identity()',returnByValue:true,disableBreaks:true});
    if(isolated.exceptionDetails||typeof isolated.result?.value!=='string')throw Error('refused: isolated guard did not initialize before page scripts');
    const wrapped=await preloadCommand(source,'Runtime.evaluate',{uniqueContextId:main.uniqueId,expression:page,disableBreaks:true});
    if(wrapped.exceptionDetails||!wrapped.result?.objectId)throw Error('refused: page wrappers did not initialize before page scripts');
    const installed={document:isolated.result.value,main:main.uniqueId,isolated:context.uniqueId,cleanup:wrapped.result.objectId,ready:false};state.documents.set(main.uniqueId,installed);
    assertTarget(state);
    const relay=await targetCommand(state,'Runtime.callFunctionOn',{objectId:installed.cleanup,functionDeclaration:'function(){return this.relay;}'});
    const described=await targetCommand(state,'DOM.describeNode',{objectId:relay.result.objectId,depth:0});
    const resolved=await targetCommand(state,'DOM.resolveNode',{backendNodeId:described.node.backendNodeId,executionContextId:context.id});
    const linked=await targetCommand(state,'Runtime.callFunctionOn',{objectId:resolved.object.objectId,functionDeclaration:'function(){return globalThis[Symbol.for("aresos.chrome.guard.v2")].relay(this);}',returnByValue:true});
    if(linked.exceptionDetails||linked.result?.value!==installed.document)throw Error('refused: private native relay did not initialize');
    const activated=await targetCommand(state,'Runtime.callFunctionOn',{objectId:installed.cleanup,functionDeclaration:'function(){return this.activate();}',returnByValue:true});
    if(activated.exceptionDetails)throw Error('refused: document guard activation failed');
    installed.ready=true;
  }catch(error){if(preloadTargets.get(targetKey(source))===state&&controlled.get(state.tab)?.epoch===state.epoch&&sameDocument()){state.failures??=new Map();state.failures.set(startup?.main.uniqueId||'unknown',{main:startup?.main.uniqueId,isolated:startup?.isolated.uniqueId,error:String(error)});port?.postMessage({event:'reader_error',error:String(error),tab:state.tab});}}
  finally{try{if(state.pause===pause&&sameDocument()&&controlled.get(state.tab)?.epoch===state.epoch)await targetCommand(state,'Debugger.resume');}catch{}state.installing.delete(installing);complete();}
}
function isPreloaded(tab,document){return [...preloadTargets.values()].some(state=>state.tab===tab&&[...state.documents.values()].some(value=>value.ready&&value.document===document));}
async function lateReader(tab){
  const owner=controlled.get(tab);if(!owner)throw Error('stale_reference: control ended');
  let complete;const settingUp=new Promise(resolve=>{complete=resolve;});owner.settingUp??=new Set();owner.settingUp.add(settingUp);
  try{for(const frame of await chrome.webNavigation.getAllFrames({tabId:tab})||[]){
    assertControl(tab,owner.epoch);if(frame.url==='about:blank')continue;
    try{safeURL(frame.url);}catch{continue;}
    await chrome.scripting.executeScript({target:{tabId:tab,frameIds:[frame.frameId]},files:['guard.js','reader.js'],world:'ISOLATED',injectImmediately:true});assertControl(tab,owner.epoch);
  }}finally{owner.settingUp.delete(settingUp);complete();}
}
function waitDialog(tab){
  let resolve;const promise=new Promise(done=>{resolve=done;});
  if(!dialogWake.has(tab))dialogWake.set(tab,new Set());dialogWake.get(tab).add(resolve);
  return {promise,dispose(){const waiting=dialogWake.get(tab);waiting?.delete(resolve);if(!waiting?.size)dialogWake.delete(tab);}};
}
function wakeDialog(tab,value={dialog:true}){for(const resolve of dialogWake.get(tab)||[])resolve(value);}
function assertControl(tab,epoch=dispatchEpoch){if(!epoch || controlled.get(tab)?.epoch !== epoch)throw Error('stale_reference: control ended');}
const audit = value => {
  if(recording && port){const text=JSON.stringify(value??null);if(text && text.length>64000){for(let offset=0;offset<text.length;offset+=64000)port.postMessage({event:'audit',data:{json_fragment:text.slice(offset,offset+64000),offset,total:text.length}});}else port.postMessage({event:'audit',data:value??null});}
  return value;
};
function respond(value) {
  const bytes=new TextEncoder().encode(JSON.stringify(value));
  if(bytes.length<=512*1024){port?.postMessage(value);return;}
  if(bytes.length>32*1024*1024){port?.postMessage({id:value.id,ok:false,error:(effectStarted?'unknown: input may have run; ':'refused: ')+'complete browser snapshot exceeds 32 MiB; inspect status and use a smaller document'});return;}
  for(let offset=0;offset<bytes.length;offset+=64*1024){const chunk=bytes.subarray(offset,offset+64*1024);port?.postMessage({id:value.id,chunk:{offset,total:bytes.length,bytes:btoa(Array.from(chunk,value=>String.fromCharCode(value)).join(''))}});}
}
function safeURL(address) {
  if(!excludedHosts)throw Error('refused: owner-only excluded-sites setting is unavailable');
  if (address === 'about:blank') return address;
  let url; try { url = new URL(address); } catch { throw Error('refused: only web addresses are allowed'); }
  const hostname=url.hostname.replace(/\.+$/,'');
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password || excludedHosts.some(host => hostname === host || hostname.endsWith('.' + host))) throw Error('refused: approval/settings pages and non-web addresses belong to the owner');
  return address;
}
function safeDestination(frame,command) {
  const input=command.input||{},target=frame.target||{},key=input.key?.split('+').at(-1);
  const submitting=target.submit&&(['click','check','select'].includes(input.verb)||input.verb==='press'&&['Enter','Space',' '].includes(key))||input.verb==='press'&&key==='Enter'&&target.editable;
  if(frame.form&&(command.kind||command.name==='resume'||submitting))safeURL(frame.form.action);
}
function rememberGet(tab,loaderId){const current=controlled.get(tab);if(!current||!loaderId)return;current.getLoaders??=new Set();current.getLoaders.add(loaderId);while(current.getLoaders.size>64)current.getLoaders.delete(current.getLoaders.values().next().value);}
async function cdp(tab, method, parameters = {}) {
  if (!POLICY.cdpMethods.includes(method)) throw Error('permission_denied: DevTools method not allowed');
  if(method.startsWith('Input.')&&dialogs.has(tab))throw Error('unknown: a page dialog interrupted the input sequence; inspect the dialog and operation status, never retry');
  if(method.startsWith('Input.') || ['Page.navigate','Page.navigateToHistoryEntry','Page.reload','Page.handleJavaScriptDialog','DOM.setFileInputFiles'].includes(method)){assertControl(tab);effectStarted=true;}
  const pending=chrome.debugger.sendCommand(controlled.get(tab)?.debuggee||{tabId:tab},method,parameters);
  if(recording)audit({method,parameters,phase:'dispatched'});
  if(method.startsWith('Input.')) {
    const wake=waitDialog(tab);
    try{const result=await Promise.race([pending,wake.promise]);if(result?.interrupted)throw Error('unknown: control ended while input was in flight; inspect status and never replay');return audit(result);}finally{wake.dispose();}
  }
  return audit(await pending);
}
function keyboard(value) {
  const parts=value.split('+'),name=parts.pop();
  let modifiers=(parts.includes('Ctrl')?2:0)|(parts.includes('Cmd')?4:0)|(parts.includes('Alt')?1:0)|(parts.includes('Shift')?8:0);
  const special={Enter:['Enter',13,'Enter'],Space:['Space',32,' '],' ':['Space',32,' '],Delete:['Delete',46,'Delete'],Backspace:['Backspace',8,'Backspace'],Tab:['Tab',9,'Tab'],Escape:['Escape',27,'Escape'],ArrowLeft:['ArrowLeft',37,'ArrowLeft'],ArrowUp:['ArrowUp',38,'ArrowUp'],ArrowRight:['ArrowRight',39,'ArrowRight'],ArrowDown:['ArrowDown',40,'ArrowDown'],Home:['Home',36,'Home'],End:['End',35,'End'],PageUp:['PageUp',33,'PageUp'],PageDown:['PageDown',34,'PageDown'],'#':['Digit3',51,'#']};
  let tuple=special[name];
  if(name==='#')modifiers|=8;
  if(!tuple&&/^[a-z]$/i.test(name))tuple=['Key'+name.toUpperCase(),name.toUpperCase().charCodeAt(0),name];
  if(!tuple&&/^\d$/.test(name))tuple=['Digit'+name,name.charCodeAt(0),name];
  if(!tuple&&/^F(?:[1-9]|1\d|2[0-4])$/.test(name))tuple=[name,111+Number(name.slice(1)),name];
  if(!tuple)throw Error('refused: unsupported key; use an explicit supported key or fill text');
  const [code,windowsVirtualKeyCode,key]=tuple;
  const text=name==='Enter'?'\r':name==='Space'?' ':key.length===1&&!(modifiers&6)?key:undefined;
  return {key,code,modifiers,windowsVirtualKeyCode,...(text===undefined?{}:{text})};
}
function popupControls(){return [...controlled].filter(([,owner])=>owner.virtualGroup);}
async function popupStatus(){
  const popups=[];
  for(const [tab,owner]of popupControls())try{
    const current=await requireTab(tab);
    if(controlled.get(tab)===owner)popups.push({tab,control:owner.epoch,title:current.title||current.url,url:current.url});
  }catch{}
  return {popups};
}
async function stopPopup(tab,epoch){
  const owner=controlled.get(tab);
  if(!owner?.virtualGroup||owner.epoch!==epoch)return {stopped:false,stale:true};
  return {stopped:true,...await release(tab)};
}
function badge(){
  // Read membership inside the queue, so a slow old update cannot resurrect a badge after Stop.
  const pending=badgeUpdates.catch(()=>{}).then(async()=>{
    const popupCounts=new Map();
    for(const [,owner]of popupControls()){
      let parent=owner;const seen=new Set();
      while(parent.parentTab!==undefined&&!seen.has(parent.parentTab)){
        seen.add(parent.parentTab);const tab=parent.parentTab;parent=controlled.get(tab);
        if(!parent)break;
        if(!parent.virtualGroup){popupCounts.set(tab,(popupCounts.get(tab)||0)+1);break;}
      }
    }
    await chrome.action.setBadgeText({text:''});
    await chrome.action.setBadgeBackgroundColor({color:'#2468ca'});
    for(const tab of new Set([...badgedTabs,...controlled.keys()])){
      const owner=controlled.get(tab),count=popupCounts.get(tab)||0;
      const text=count?'POP':owner?'ON':'';
      const title=count?'Claude controls '+count+' popup'+(count===1?'':'s')+' opened from here: Stop in this toolbar popup':owner?.virtualGroup?'Claude controls this popup: Stop in its opener toolbar popup':owner?'Claude controls this tab: Stop control':'AresOS Chrome: Stop control';
      try{await chrome.action.setBadgeText({tabId:tab,text});await chrome.action.setTitle({tabId:tab,title});}
      catch(error){if(controlled.has(tab))throw error;}
      if(owner)badgedTabs.add(tab);else badgedTabs.delete(tab);
    }
  });
  badgeUpdates=pending;return pending;
}
async function rules() {
  const previous = await chrome.declarativeNetRequest.getSessionRules();
  const tabIds = [...new Set([...controlled.keys(),...releasing.keys()])];
  await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:previous.map(rule=>rule.id),addRules:tabIds.length ? [{id:1,priority:1,action:{type:'block'},condition:{tabIds,requestDomains:(excludedHosts || POLICY.fixedHosts).flatMap(host=>[host,host+'.']),resourceTypes:['main_frame','sub_frame']}}] : []});
}
async function configure(hosts) {
  if(!Array.isArray(hosts) || hosts.length>128 || hosts.some(host=>typeof host!=='string' || !/^[a-z0-9][a-z0-9.-]*$/.test(host)))throw Error('refused: invalid owner-only excluded-sites setting');
  const next=[...new Set([...POLICY.fixedHosts,...hosts])].sort();
  if(excludedHosts && JSON.stringify(next)!==JSON.stringify(excludedHosts))await stop();
  excludedHosts=next;
  const excludeMatches=next.flatMap(host=>[`http://*.${host}/*`,`https://*.${host}/*`,`http://*.${host}./*`,`https://*.${host}./*`]);
  const common={matches:['http://*/*','https://*/*'],excludeMatches,allFrames:true,matchOriginAsFallback:true,runAt:'document_start',persistAcrossSessions:false};
  const existing=await chrome.scripting.getRegisteredContentScripts();
  if(existing.length)await chrome.scripting.unregisterContentScripts({ids:existing.map(script=>script.id)});
  await chrome.scripting.registerContentScripts([{...common,id:'aresos-context',world:'ISOLATED',js:['context.js']}]);
  await rules();
  return {configured:true};
}
function take(tab,opener=null){
  if(releasing.has(tab))return Promise.reject(Error('stale_reference: private cleanup is still pending; leave the tab to the owner until it finishes'));
  if(admissions.has(tab))return admissions.get(tab);
  const pending=admitTab(tab,stopGeneration,opener);admissions.set(tab,pending);
  pending.finally(()=>{if(admissions.get(tab)===pending)admissions.delete(tab);}).catch(()=>{});return pending;
}
async function restoreTab(tab,original){
  if(original.virtualGroup)return;
  try{await chrome.tabs.ungroup(tab);await chrome.tabs.move(tab,{windowId:original.window,index:original.index});if(original.group>=0)await chrome.tabs.group({tabIds:[tab],groupId:original.group});}catch{}
}
async function admitTab(tab,generation,opener=null) {
  const check=()=>{if(stopGeneration!==generation||releasing.has(tab)||opener&&controlled.get(opener.tab)?.epoch!==opener.epoch)throw Error('stale_reference: control stopped during tab admission');};
  if(opener){await requireTab(opener.tab);check();}
  check();const current = await chrome.tabs.get(tab);check();safeURL(current.url||(opener?current.pendingUrl||'about:blank':current.url));
  if (controlled.has(tab)) return {tab, session, group:groupId};
  const window=await chrome.windows.get(current.windowId);check();
  if(window.type!=='normal'&&!opener){
    const parent=controlled.get(current.openerTabId);
    if(!parent)throw Error('refused: popup control requires its opener in the Claude group');
    opener={tab:current.openerTabId,epoch:parent.epoch};await requireTab(opener.tab);check();
  }
  const original = {window:current.windowId,index:current.index,group:current.groupId,epoch:crypto.randomUUID(),debuggee:{tabId:tab},virtualGroup:window.type!=='normal',...(opener?{parentTab:opener.tab,parentEpoch:opener.epoch,popupNeedsReload:true}:{})};
  let attached=false,grouped=false;
  try{
    effectStarted=true;await chrome.debugger.attach({tabId:tab}, '1.3');attached=true;check();
    if(!original.virtualGroup){
      groupId = await chrome.tabs.group({tabIds:[tab],...(groupId === null ? {} : {groupId})});grouped=true;check();
      await chrome.tabGroups.update(groupId,{title:'Claude',color:'blue',collapsed:false});check();
    }
    controlled.set(tab,original);await prepareTarget({tabId:tab});check();
    await rules();check();await badge();check();await lateReader(tab);check();assertControl(tab,original.epoch);
    if(opener){await requireTab(opener.tab);check();}
    if(original.virtualGroup)audit({popup_admitted:{tab,window:current.windowId,type:window.type,opener:opener?.tab,badge:'POP on opener'}});
    return {tab,session,group:groupId};
  }catch(error){
    if(controlled.get(tab)===original)await release(tab);
    else{if(attached)try{await chrome.debugger.detach({tabId:tab});}catch{}if(grouped)await restoreTab(tab,original);}
    throw error;
  }
}
async function createdTarget({sourceTabId,tabId}){
  const parent=controlled.get(sourceTabId);if(!parent)return;
  try{await take(tabId,{tab:sourceTabId,epoch:parent.epoch});}
  catch(error){port?.postMessage({event:'reader_error',error:String(error),tab:tabId});}
}
async function content(tab, frame, command, parameters={}) {
  const effectful=['focus','select','check','install_file'].includes(command);
  const modalError=()=>Error(effectful?'unknown: a page dialog interrupted input handling; inspect the dialog and operation status, never retry the input':'refused: a native dialog blocks this frame query; inspect and answer the dialog before checking prepared elements');
  if(dialogs.has(tab))throw modalError();
  if(effectful){assertControl(tab);parameters={...parameters,generation:dispatchEpoch};effectStarted=true;}
  // Release already bounds best-effort clear; it must leave no modal waiter.
  const wake=command==='clear'?null:waitDialog(tab);
  let reply;
  try{const pending=chrome.tabs.sendMessage(tab,{command,...parameters},{frameId:frame});reply=audit(await (wake?Promise.race([pending,wake.promise]):pending));}
  finally{wake?.dispose();}
  if(reply?.dialog)throw modalError();
  if(reply?.interrupted)throw Error(effectful?'unknown: control ended during input handling; inspect status and never retry the input':'stale_reference: control ended during the frame query');
  if (!reply?.ok) throw Error(reply?.error || 'stale_reference: page changed; read again');
  return reply.data;
}
async function finishFrames(tab,frames,epoch,nonce){
  let uncertain=false;
  for(const frame of frames){
    if(dialogs.has(tab))return uncertain;
    const wake=waitDialog(tab);
    try{const result=await Promise.race([content(tab,frame.frameId??frame.frame,'finish_input',{generation:epoch,dispatch_nonce:nonce}),wake.promise]);if(result?.interrupted)return true;}
    catch{
      // A form may have replaced an armed iframe. Missing cleanup must never
      // discard observed holds; a surviving old reader simply keeps its mark.
      try{const current=await chrome.webNavigation.getFrame({tabId:tab,frameId:frame.frameId??frame.frame});if(current&&current.documentId===(frame.browser_document??frame.documentId))uncertain=true;}catch{uncertain=true;}
    }
    finally{wake.dispose();}
  }
  return uncertain;
}
const stepKey=step=>JSON.stringify([step.document,step.id,step.frame]);
function rememberStep(current,key){
  current.seenSteps??=new Set();current.seenSteps.add(key);
  if(current.seenSteps.size>4096)current.seenSteps.delete(current.seenSteps.values().next().value);
}
function observeStep(message,sender){
  const current=stepControl(sender.tab?.id,message.generation),step=message.step;
  if(!current?.epoch||message.generation!==current.epoch||!Number.isInteger(sender.frameId)||!step||!['native_submit','submit_event','activation','activation_unknown'].includes(step.kind)||typeof step.document!=='string'||typeof step.id!=='string')return false;
  const value={...step,frame:sender.frameId},key=stepKey(value);
  if(current.seenSteps?.has(key))return true;
  rememberStep(current,key);
  current.steps??=new Map();
  if(!current.steps.has(key)){
    if(current.steps.size>=512){
      if(current.stepOverflow)return true;
      current.stepOverflow=true;value.id='overflow-'+value.id;value.kind='activation_unknown';value.cancellable=false;value.label='Additional page steps exceeded the response limit; inspect with the owner and never replay.';
    }
    current.steps.set(stepKey(value),value);
    port?.postMessage({event:'held_step',session,tab:sender.tab.id,step:value});
  }
  return true;
}
async function collectSteps(tab,epoch=controlled.get(tab)?.epoch){
  await new Promise(resolve=>setTimeout(resolve,POLICY.holdMs+25));
  if(dialogs.has(tab))return []; // the private observations remain queued
  const found=new Map();let overflow=null;
  const include=value=>{const key=stepKey(value);if(value.id.startsWith('overflow-')){overflow??=value;return;}if(found.size<512||found.has(key))found.set(key,value);else overflow??={...value,id:'overflow-'+value.id,kind:'activation_unknown',cancellable:false,label:'Additional page steps exceeded the response limit; inspect with the owner and never replay.'};};
  for(const frame of await chrome.webNavigation.getAllFrames({tabId:tab})||[]){
    if(dialogs.has(tab))return [];
    const wake=waitDialog(tab);
    try{
      safeURL(frame.url);
      const values=await Promise.race([content(tab,frame.frameId,'steps'),wake.promise]);
      if(Array.isArray(values))for(const step of values){const value={...step,frame:frame.frameId};include(value);const current=stepControl(tab,epoch);if(current){rememberStep(current,stepKey(value));current.steps??=new Map();if(current.steps.size<512)current.steps.set(stepKey(value),value);}}
    }catch{}finally{wake.dispose();}
  }
  if(dialogs.has(tab))return [];
  const current=stepControl(tab,epoch);
  for(const value of current?.steps?.values()||[])include(value);
  if(overflow){found.set(stepKey(overflow),overflow);if(current){current.steps??=new Map();current.steps.set(stepKey(overflow),overflow);}}
  return [...found.values()];
}
async function requireTab(tab) {
  const current = await chrome.tabs.get(tab);
  const owner=controlled.get(tab);
  if (!owner || (owner.virtualGroup?current.windowId!==owner.window:current.groupId !== groupId)) { await release(tab); throw Error('stale_reference: tab is outside the Claude group'); }
  if(owner.parentTab!==undefined){
    try{if(controlled.get(owner.parentTab)?.epoch!==owner.parentEpoch)throw Error('opener control ended');await requireTab(owner.parentTab);}
    catch{await release(tab);throw Error('stale_reference: popup opener is outside the Claude group');}
  }
  try { safeURL(current.url); } catch(error) { await release(tab); throw error; }
  return current;
}
async function reloadIdentity(tab){
  const tree=await cdp(tab,'Page.getFrameTree'),frames=await chrome.webNavigation.getAllFrames({tabId:tab})||[];
  const top=frames.find(frame=>frame.frameId===0);
  if(!top||!tree.frameTree?.frame.loaderId||tree.frameTree.frame.url!==top.url)throw Error('stale_reference: navigation changed; read again');
  for(const frame of frames){if(frame.url==='about:blank')continue;const key=JSON.stringify([tab,frame.frameId]),method=documentMethods.get(key);if(method?.document===frame.documentId&&method.method!=='GET'||controlled.get(tab)?.parentTab!==undefined&&formLoadedDocuments.get(key)===frame.documentId)throw Error('refused: this document was loaded by a form submission; open its address fresh in a Claude tab');if(frame.frameId===0&&controlled.get(tab)?.getLoaders?.has(tree.frameTree.frame.loaderId))continue;if(method?.document!==frame.documentId||method.method!=='GET')throw Error('refused: this document was loaded by a form submission or its request method is unknown; open its address fresh in a Claude tab');}
  rememberGet(tab,tree.frameTree.frame.loaderId);
  return {loaderId:tree.frameTree.frame.loaderId,frameId:tree.frameTree.frame.id||null,frames:frames.map(frame=>[frame.frameId,frame.documentId,frame.url])};
}
async function reloadChecked(tab,initial){
  const current=await reloadIdentity(tab);
  if(initial&&stable(current)!==stable(initial))throw Error('stale_reference: the document changed before its guarded reload; read again');
  const owner=controlled.get(tab),pending={frameId:current.frameId,document:current.frames.find(frame=>frame[0]===0)?.[1]};owner.getReload=pending;
  try{await cdp(tab,'Page.reload',{loaderId:current.loaderId});owner.popupNeedsReload=false;}catch(error){if(owner.getReload===pending)delete owner.getReload;throw error;}
}
async function release(tab) {
  if(releasing.has(tab))return boundedRelease(tab,releasing.get(tab).promise);
  const original = controlled.get(tab);
  if(!original)return {released:tab};
  const children=[...controlled].filter(([child,value])=>child!==tab&&(value.debuggee?.tabId===tab||value.parentTab===tab)).map(([child])=>child);
  if(original){const key=JSON.stringify([tab,original.epoch]);retiredControls.set(key,original);while(retiredControls.size>32)retiredControls.delete(retiredControls.keys().next().value);setTimeout(()=>{if(retiredControls.get(key)===original)retiredControls.delete(key);},900000);}
  controlled.delete(tab); dialogs.delete(tab);confirmationPlans.delete(tab);
  wakeDialog(tab,{interrupted:true});
  for(const [id,barrier]of fixtureBarriers)if(barrier.tab===tab){fixtureBarriers.delete(id);barrier.reject(Error('unknown: interrupted after input'));}
  for(const [token,stage] of stagedUploads)if(stage.tab===tab)stagedUploads.delete(token);
  port?.postMessage({event:'released',tab,session});
  const record={original,promise:null};releasing.set(tab,record);
  record.promise=(async()=>{
    await Promise.all(children.map(async child=>{await release(child);if(releasing.has(child))await releasing.get(child).promise;}));
    await Promise.allSettled([...original.settingUp||[],...[...preloadTargets.values()].filter(state=>state.tab===tab).flatMap(state=>[...state.installing||[]])]);
    for(const [key,state]of preloadTargets){if(state.tab!==tab)continue;
      if(state.detached&&state.targetId)try{if(!(await chrome.debugger.getTargets()).some(target=>target.id===state.targetId)){destroyedTarget(state);continue;}}catch{}
      const blocked=new Map();
      for(const value of state.documents.values())try{const result=await preloadCommand(state.source,'Runtime.callFunctionOn',{objectId:value.cleanup,functionDeclaration:'function(){return this.cleanup();}',returnByValue:true});if(result.exceptionDetails||result.result?.value!==true)blocked.set(value.main,value.document);}catch{blocked.set(value.main,value.document);}
      for(const context of state.contexts.values())if(context.origin===chrome.runtime.getURL('').replace(/\/$/,'')){
        const document=[...state.documents.values()].find(value=>value.isolated===context.uniqueId)?.document;
        try{const result=await preloadCommand(state.source,'Runtime.evaluate',{uniqueContextId:context.uniqueId,expression:'globalThis[Symbol.for("aresos.chrome.guard.v2")]?.dispose() ?? true',disableBreaks:true,returnByValue:true});if(result.exceptionDetails||result.result?.value!==true)blocked.set(context.uniqueId,document);}catch{blocked.set(context.uniqueId,document);}
      }
      if(blocked.size)try{for(const frame of await chrome.webNavigation.getAllFrames({tabId:tab})||[])try{const result=await content(tab,frame.frameId,'clear');if(result.restored===true)for(const [identity,document]of blocked)if(document===result.document)blocked.delete(identity);}catch{}}catch{}
      await Promise.all([...blocked.keys()].map(identity=>contextGone(state,identity)));
      try{await preloadCommand(state.source,'Debugger.disable');}catch{}
      preloadTargets.delete(key);
    }
    try{if(original.debuggee?.sessionId)await preloadCommand(original.parentSource||{tabId:original.debuggee.tabId},'Target.detachFromTarget',{sessionId:original.debuggee.sessionId});else await chrome.debugger.detach({tabId:tab});}catch{}
    // MAIN is restored before detaching. The remaining isolated-only readers
    // may finish cleanup after a modal; the tab stays grouped until they do.
    try{await Promise.all((await chrome.webNavigation.getAllFrames({tabId:tab})||[]).map(frame=>content(tab,frame.frameId,'clear').catch(()=>{})));}catch{}
    await restoreTab(tab,original);releasing.delete(tab);
    if(!controlled.size&&!releasing.size)groupId=null;
    await rules();await badge();return {released:tab,cleanup_pending:false};
  })();
  badge().catch(error=>port?.postMessage({event:'reader_error',error:'Control badge unavailable: '+String(error),tab}));
  record.promise.catch(error=>port?.postMessage({event:'reader_error',error:'Private cleanup remains pending: '+String(error),tab}));
  return boundedRelease(tab,record.promise);
}
async function boundedRelease(tab,promise){return Promise.race([promise,new Promise(resolve=>setTimeout(()=>resolve({stopped:tab,cleanup_pending:true,message:'Stopped. Close its dialog, or close the tab if returning it remains pending.'}),1000))]);}
async function stop() { stopGeneration++;await Promise.all([...controlled.keys()].map(tab=>release(tab)));await badge();return {stopped:true,cleanup_pending:releasing.size+admissions.size}; }
async function facts(tab, reference) {
  const current = await requireTab(tab);
  if([...preloadTargets.values()].some(state=>state.tab===tab&&state.failures?.size))throw Error('refused: this tab could not install its document-start guard; open its address fresh in a Claude tab');
  if (reference && (reference.session !== session || reference.tab !== tab)) throw Error('stale_reference: browser session changed; read again');
  if(dialogs.has(tab)){
    const dialog=dialogs.get(tab);safeURL(dialog.frame_url);
    if(dialog.frame===undefined)throw Error('refused: dialog opener is not yet established; inspect with the owner');
    if(reference)throw Error('stale_reference: a native dialog is open; inspect and answer it first');
    return {session,tab,group:groupId,control:controlled.get(tab).epoch,url:current.url,title:current.title,frames:[],frame_tree:[],dialog};
  }
  const frames = await chrome.webNavigation.getAllFrames({tabId:tab}) || [];
  const result=[];
  for (const frame of frames) {
    if(frame.url==='about:blank')continue;
    try { safeURL(frame.url); } catch { if (reference?.frame === frame.frameId) throw Error('refused: excluded frame'); continue; }
    const snapshot = await content(tab,frame.frameId,reference?.frame === frame.frameId ? 'facts':'read',reference?.frame === frame.frameId ? {element:reference.element}:{});
    if (reference?.frame === frame.frameId && snapshot.document !== reference.document) throw Error('stale_reference: document changed');
    result.push({frame:frame.frameId,parent:frame.parentFrameId,browser_document:frame.documentId,...snapshot});
  }
  if (reference && !result.some(frame=>frame.frame === reference.frame)) throw Error('stale_reference: frame is gone');
  return {session,tab,group:groupId,control:controlled.get(tab).epoch,url:current.url,title:current.title,needs_reload:controlled.get(tab).popupNeedsReload||result.some(frame=>!isPreloaded(tab,frame.document)),frames:result,frame_tree:frames.map(frame=>({frame:frame.frameId,parent:frame.parentFrameId,url:frame.url})),dialog:dialogs.get(tab) || null};
}
function binding(facts, reference, kind, adapter) {
  const frame = facts.frames.find(frame=>frame.frame === reference.frame);
  if (!frame?.target) throw Error('stale_reference: target not found');
  const target = frame.target;
  return {session,tab:facts.tab,control:facts.control,url:facts.url,document:frame.document,frame:frame.frame,frame_url:frame.url,
    target:Object.fromEntries(['element','role','name','label','title','href','value','password','states','editable','search','submit','page_dialog','options','implicit_submitter'].filter(key=>key in target).map(key=>[key,target[key]])),
    form:frame.form,
    editable:kind === 'send' && !frame.form && !adapter ? facts.frames.map(frame=>({frame:frame.frame,document:frame.document,url:frame.url,fields:frame.editable})) : null,
    item:['delete','pay','activation','confirmation'].includes(kind) ? frame.item : null,
    adapter:adapter ? frame.adapter:null,dialog:facts.dialog};
}
const stable = value => JSON.stringify(value, function(key,value) { return value && !Array.isArray(value) && typeof value === 'object' ? Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b))) : value; });
async function pointer(tab,snapshot,reference,target){
  let x=target.box.x+target.box.width/2,y=target.box.y+target.box.height/2;
  let child=snapshot.frames.find(frame=>frame.frame===reference.frame);
  if(!(await content(tab,child.frame,'hit',{element:target.element,x,y})).hit)throw Error('stale_reference: another element covers the target');
  while(child.parent>=0){
    const parent=snapshot.frames.find(frame=>frame.frame===child.parent);
    if(!parent)throw Error('refused: parent frame is excluded');
    const siblings=snapshot.frame_tree.filter(frame=>frame.parent===child.parent && frame.url===child.url);
    if(siblings.length>1)throw Error('refused: duplicate frame addresses make pointer targeting ambiguous; use a keyboard control or the owner');
    const candidates=parent.embeds.filter(embed=>embed.url===child.url);
    const embed=candidates.length===1 ? candidates[0]:parent.embeds.length===1 ? parent.embeds[0]:null;
    if(!embed?.aligned || !embed.width || !embed.height)throw Error('refused: frame geometry cannot be established safely');
    x=embed.box.x+(x+embed.borderX)*embed.box.width/embed.width;
    y=embed.box.y+(y+embed.borderY)*embed.box.height/embed.height;
    if(!(await content(tab,parent.frame,'hit',{element:embed.element,x,y})).hit)throw Error('stale_reference: parent frame is covered or moved');
    child=parent;
  }
  return {x,y};
}
async function collection(command) {
  const key=stable([command.name,command.text||'']);
  let record,offset=0;
  if(command.cursor){
    const [token,position]=command.cursor.split(':');record=listSnapshots.get(token);offset=Number(position);
    if(!record || record.key!==key || Date.now()-record.time>300000 || !Number.isInteger(offset) || offset<0 || offset>=record.items.length)throw Error('stale_reference: list snapshot changed; read without the cursor');
    record.time=Date.now();
  } else {
    let items;
    if(command.name==='downloads')items=await chrome.downloads.search({limit:10001,query:command.text?[command.text]:[]});
    else if(command.name==='history')items=await chrome.history.search({text:command.text||'',startTime:0,maxResults:10001});
    else if(command.name==='bookmarks')items=await chrome.bookmarks.search(command.text||{});
    else {
      const focused=new Set((await chrome.windows.getAll()).filter(window=>window.focused).map(window=>window.id));
      items=(await chrome.tabs.query({})).map(tab=>({tab:tab.id,window:tab.windowId,index:tab.index,active:tab.active,focused:focused.has(tab.windowId),title:tab.title,url:tab.url,controlled:controlled.has(tab.id)&&(controlled.get(tab.id).virtualGroup||tab.groupId===groupId),cleanup_pending:releasing.has(tab.id)}));
    }
    if(items.length>10000 || JSON.stringify(items).length>8*1024*1024)throw Error('refused: this complete list exceeds the 10000-item or 8 MiB snapshot bound; narrow the search');
    record={id:crypto.randomUUID(),key,items,time:Date.now()};
    for(const [id,value]of listSnapshots)if(Date.now()-value.time>300000)listSnapshots.delete(id);
    if(listSnapshots.size>=2)listSnapshots.delete(listSnapshots.keys().next().value);
    listSnapshots.set(record.id,record);
  }
  const end=Math.min(record.items.length,offset+(command.limit||5));
  return {session,items:record.items.slice(offset,end),total:record.items.length,cursor:end<record.items.length?record.id+':'+end:null};
}
async function dispatch(command) {
  const tab = command.tab ?? command.reference?.tab;
  const reference = command.reference;
  if(command.name==='control_status'){
    const windows=await chrome.windows.getAll();
    const tabs=await chrome.tabs.query({});
    return {windows:windows.map(({id,type,left,top,width,height,focused})=>({id,type,left,top,width,height,focused})),
      tabs:await Promise.all(tabs.map(async({id,windowId,openerTabId})=>({tab:id,window:windowId,opener:openerTabId,badge:await chrome.action.getBadgeText({tabId:id}),title:await chrome.action.getTitle({tabId:id})}))),...await popupStatus()};
  }
  if(command.name==='stop_popup'){await chrome.action.openPopup();return {opened:true};}
  if (command.name === 'audit') { recording=command.enabled === true; return {recording}; }
  if(command.name==='configure')return configure(command.excluded_hosts);
  if(command.name==='ack_steps'){
    for(const current of stepStates(tab))if(current.steps){for(const step of command.steps||[])current.steps.delete(stepKey(step));if(![...current.steps.values()].some(step=>step.id.startsWith('overflow-')))current.stepOverflow=false;}
    return {acknowledged:true};
  }
  if(command.name==='queued_steps')return stepStates(tab).flatMap(current=>[...current.steps?.values()||[]]).slice(0,513);
  if(!excludedHosts)throw Error('refused: owner-only excluded-sites setting is unavailable');
  if (['tabs','downloads','history','bookmarks'].includes(command.name))return collection(command);
  if (command.name === 'take_tab') return take(tab);
  if (command.name === 'release_tab') return release(tab);
  if (command.name === 'stop') return stop();
  if (command.name === 'open') {
    safeURL(command.url);
    effectStarted=true;const created=await chrome.tabs.create({url:'about:blank'});
    let current;
    for(let attempt=0;attempt<100;attempt++){current=await chrome.tabs.get(created.id);if(current.url)break;await new Promise(resolve=>setTimeout(resolve,20));}
    if(current?.url!=='about:blank')throw Error('unknown: the new private blank tab was not established; inspect tabs before opening again');
    await take(created.id);dispatchEpoch=controlled.get(created.id).epoch;
    return {tab:created.id,session,group:groupId};
  }
  if (command.name === 'dialog_facts') {
    const current=await requireTab(tab), dialog=dialogs.get(tab);dispatchEpoch=controlled.get(tab).epoch;
    if(!dialog || dialog.frame === undefined)throw Error('refused: dialog opener is not yet established; inspect with the owner');
    safeURL(dialog.frame_url);return {session,tab,control:controlled.get(tab).epoch,url:current.url,dialog};
  }
  if (command.name === 'dialog') {
    const current=await requireTab(tab), dialog=dialogs.get(tab);dispatchEpoch=controlled.get(tab).epoch;
    const expected={session,tab,control:controlled.get(tab).epoch,url:current.url,dialog};
    if(!dialog || dialog.frame === undefined || stable(expected)!==stable(command.binding))throw Error('stale_approval: dialog or its opener changed');
    safeURL(dialog.frame_url);
    if(command.operation && used.has(command.operation))throw Error('refused: dialog operation already attempted');
    if(command.operation)used.add(command.operation);
    await cdp(tab,'Page.handleJavaScriptDialog',{accept:command.input.accept,...(command.input.text === undefined ? {}:{promptText:command.input.text})});
    const uncertain_finish=await finishFrames(tab,await chrome.webNavigation.getAllFrames({tabId:tab})||[],dispatchEpoch,controlled.get(tab)?.inputNonce);
    const steps=await collectSteps(tab,dispatchEpoch);
    return {checked:true,dispatched:true,page:'Dialog answered once, as the page shows it.',steps,dialog:dialogs.get(tab)||null,uncertain_finish};
  }
  if(command.name==='tab_context'){const current=await chrome.tabs.get(tab);safeURL(current.url);return {session,tab,url:current.url,title:current.title,control:controlled.get(tab)?.epoch||null,frames:(await chrome.webNavigation.getAllFrames({tabId:tab})||[]).map(frame=>({frame:frame.frameId,url:frame.url,document:frame.documentId}))};}
  if (command.name === 'validity') {
    await requireTab(tab);safeURL((await chrome.webNavigation.getFrame({tabId:tab,frameId:reference.frame})).url);
    return {session,control:controlled.get(tab).epoch,...await content(tab,reference.frame,'ready',{element:reference.element})};
  }
  if (command.name === 'read' || command.name === 'facts') return facts(tab,reference);
  if (command.name === 'stage_file') {
    await requireTab(tab);dispatchEpoch=controlled.get(tab).epoch;
    let stage=stagedUploads.get(command.token);
    if(!stage){
      if(command.offset !== 0 || stagedUploads.size>=2)throw Error('refused: upload staging limit');
      stage={tab,epoch:dispatchEpoch,file:command.file,chunks:[],size:0};stagedUploads.set(command.token,stage);
      setTimeout(()=>{if(stagedUploads.get(command.token)===stage)stagedUploads.delete(command.token);},900000);
    }
    assertControl(tab,stage.epoch);
    const bytes=Uint8Array.from(atob(command.bytes),character=>character.charCodeAt(0));
    if(stage.size!==command.offset || stage.size+bytes.length>stage.file.size || stage.size+bytes.length>25*1024*1024)throw Error('refused: upload offset or size mismatch');
    stage.chunks.push(bytes);stage.size+=bytes.length;
    if(stage.size===stage.file.size){
      const complete=new Uint8Array(stage.size);let offset=0;for(const chunk of stage.chunks){complete.set(chunk,offset);offset+=chunk.length;}
      const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',complete))].map(value=>value.toString(16).padStart(2,'0')).join('');
      assertControl(tab,stage.epoch);
      if(stagedUploads.get(command.token)!==stage || hash!==stage.file.sha256)throw Error('stale_approval: staged upload changed');
      await content(tab,reference.frame,'set_control',{generation:stage.epoch});
      offset=0;
      for(const chunk of stage.chunks){
        assertControl(tab,stage.epoch);
        const bytes=btoa(Array.from(chunk,value=>String.fromCharCode(value)).join(''));
        await content(tab,reference.frame,'stage_file',{generation:stage.epoch,token:command.token,offset,bytes,file:stage.file});offset+=chunk.length;
      }
      stagedUploads.delete(command.token);
    }
    return {offset:stage.size};
  }
  await requireTab(tab);dispatchEpoch=controlled.get(tab).epoch;
  if(command.name==='prepare_control'){
    const current=await facts(tab);
    if(!current.needs_reload)return {ready:true};
    const initial=await reloadIdentity(tab);
    let unsaved=false,playing=false;
    for(const frame of current.frames){const state=await content(tab,frame.frame,'reload_state');unsaved ||= state.unsaved;playing ||= state.playing;}
    if((unsaved||playing)&&command.reload_taken_tab!==true)throw Error('reload_required: this taken tab '+[unsaved?'may have unsaved text or editable content':null,playing?'is playing media':null].filter(Boolean).join(' and ')+'; tell the owner, then repeat with reload_taken_tab=true only when the reload is wanted');
    await reloadChecked(tab,initial);
    return {reloaded:true,message:'The taken tab reloaded to install its page guard before page scripts. Every old reference is stale; read again.'};
  }
  if (command.name === 'close_tab') { await release(tab); await chrome.tabs.remove(tab); return {closed:tab}; }
  if (command.name === 'navigate') {
    if (command.url) { safeURL(command.url);const navigated=await cdp(tab,'Page.navigate',{url:command.url});rememberGet(tab,navigated?.loaderId); }
    else if (command.direction === 'reload') await reloadChecked(tab);
    else {
      const history = await cdp(tab,'Page.getNavigationHistory');
      const entry = history.entries[history.currentIndex + (command.direction === 'back' ? -1:1)];
      if (!entry) throw Error('refused: no history entry in that direction');
      safeURL(entry.url);if(entry.transitionType==='form_submit')throw Error('refused: a form-loaded history entry may resubmit; open its address fresh in a Claude tab');await cdp(tab,'Page.navigateToHistoryEntry',{entryId:entry.id});
    }
    return {navigated:true};
  }
  if (command.name !== 'input' && command.name !== 'resume') throw Error('permission_denied: unknown fixed command');
  let snapshot = await facts(tab,reference);
  if(snapshot.needs_reload)throw Error('stale_reference: the taken document needs its guarded reload before input; read and prepare again');
  if (command.binding && stable(binding(snapshot,reference,command.kind,command.adapter)) !== stable(command.binding)) throw Error('stale_approval: page changed; prepare again');
  if (command.operation && used.has(command.operation)) throw Error('refused: operation already dispatched or attempted');
  let frame = snapshot.frames.find(frame=>frame.frame === reference.frame), target = frame.target;
  if (!target) throw Error('stale_reference: read again');
  safeDestination(frame,command);
  if (command.expected && stable(command.expected) !== stable(target)) throw Error('stale_reference: element no longer holds the expected state');
  if (command.operation) used.add(command.operation); // consume before any event can enter the page
  if(command.confirmation && command.operation)confirmationPlans.set(tab,{operation:command.operation,expected:command.confirmation,browser_document:frame.browser_document,matched:[]});
  const keyInput=command.input?.verb==='press'?keyboard(command.input.key):null;
  const inputNonce=crypto.randomUUID();controlled.get(tab).inputNonce=inputNonce;
  for(const other of snapshot.frames){
    assertControl(tab);
    await content(tab,other.frame,'set_control',{generation:dispatchEpoch});
    await content(tab,other.frame,'arm',{config:{...POLICY,blockedHosts:excludedHosts,conservative:command.conservative},target:other.frame===reference.frame ? target.element:null,form:other.frame===reference.frame ? frame.form?.element:null,operation:command.approved && other.frame===reference.frame ? command.operation:null,generation:dispatchEpoch,dispatch_nonce:inputNonce,key_input:other.frame===reference.frame?keyInput:null,primary_submission:!!command.primary_submission && other.frame===reference.frame,implicit:other.frame===reference.frame&&command.input?.verb==='press'&&command.input.key.split('+').at(-1)==='Enter'?target.implicit_submitter:null,approved_form:command.approved&&other.frame===reference.frame?frame.form:null});
  }
  // Native pointer input must address the selected tab in headed Chrome.
  // Arm first because activation can itself run focus/visibility handlers.
  if(command.name==='input'){
    assertControl(tab);const selected=await chrome.tabs.get(tab);assertControl(tab);
    if(!selected.active){effectStarted=true;await chrome.tabs.update(tab,{active:true});}
  }
  if(recording&&command.fixture_arm_delay){port?.postMessage({event:'fixture_arm_wait',operation:command.operation});await new Promise(resolve=>setTimeout(resolve,command.fixture_arm_delay));}
  // Arming other frames may take time. Compare again at the actual input boundary.
  snapshot=await facts(tab,reference);
  if(command.binding&&stable(binding(snapshot,reference,command.kind,command.adapter))!==stable(command.binding))throw Error('stale_approval: page changed during frame setup; prepare again');
  frame=snapshot.frames.find(frame=>frame.frame===reference.frame);target=frame.target;
  safeDestination(frame,command);
  assertControl(tab);
  if (command.name === 'resume') { effectStarted=true; await content(tab,reference.frame,'resume',{hold:command.hold,operation:command.operation,generation:dispatchEpoch,element:reference.element,form:frame.form?.element}); }
  else {
    const input = command.input;
    if (target.password) throw Error('owner_signin: password fields belong to the owner');
    if (input.verb === 'click' || input.verb === 'check' && target.states.checked!==input.checked) {
      if (target.href && !target.href.startsWith('javascript:')) safeURL(target.href);
      const {x,y}=await pointer(tab,snapshot,reference,target);
      await cdp(tab,'Input.dispatchMouseEvent',{type:'mousePressed',x,y,button:'left',clickCount:1});
      await cdp(tab,'Input.dispatchMouseEvent',{type:'mouseReleased',x,y,button:'left',clickCount:1});
    } else if (input.verb === 'fill' || input.verb === 'press') {
      await content(tab,reference.frame,'focus',{element:reference.element});
      if (input.verb === 'fill') {
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyDown',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyUp',key:'a',code:'KeyA',modifiers:2,windowsVirtualKeyCode:65});
        await cdp(tab,'Input.insertText',{text:input.text});
      } else {
        const {text,...key}=keyboard(input.key);
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyDown',...key,...(text===undefined?{}:{text})});
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyUp',...key});
      }
    } else if (input.verb === 'upload') await content(tab,reference.frame,'install_file',{element:reference.element,token:command.upload.token});
    else if (input.verb === 'check') {}
    else if (input.verb === 'select') await content(tab,reference.frame,input.verb,{element:reference.element,...input});
    else if (input.verb === 'scroll') {const point=await pointer(tab,snapshot,reference,target);await cdp(tab,'Input.dispatchMouseEvent',{type:'mouseWheel',...point,deltaX:input.x,deltaY:input.y});}
    else throw Error('permission_denied: unsupported input');
  }
  assertControl(tab);
  const uncertain_finish=await finishFrames(tab,snapshot.frames,dispatchEpoch,inputNonce);
  const steps=await collectSteps(tab,dispatchEpoch);
  if(recording && command.fixture_cut==='after-input'){
    await new Promise((resolve,reject)=>{fixtureBarriers.set(command.operation,{tab,resolve,reject});port?.postMessage({event:'fixture_after_input',operation:command.operation});});
  }
  const confirmation=confirmationPlans.get(tab);confirmationPlans.delete(tab);
  return {checked:!!command.binding,dispatched:true,steps,dialog:dialogs.get(tab)||null,uncertain_finish,confirmations:confirmation?.matched || [],page:'Input dispatched once; inspect a fresh read for what the page shows.'};
}
async function connect() {
  port=chrome.runtime.connectNative('org.aresos.chrome');
  const entropy=await navigator.userAgentData.getHighEntropyValues(['fullVersionList']);
  const version=entropy.fullVersionList.find(item=>item.brand === 'Google Chrome')?.version;
  port.postMessage({event:'hello',session,version});
  port.onMessage.addListener(message=>{
    if (message.owner_reply) { const pending=ownerRequests.get(message.owner_reply); if(pending){ownerRequests.delete(message.owner_reply);pending(message.result);} return; }
    serial=serial.then(async()=>{
      effectStarted=false;dispatchEpoch=null;audit({command:message.command?.name,phase:'begin'});
      try { respond({id:message.id,ok:true,data:await dispatch(message.command)}); }
      catch(error) { port?.postMessage({id:message.id,ok:false,error:effectStarted ? 'unknown: Input may have started; inspect status and the page, never retry. '+String(error.message):String(error.message)}); }
    });
  });
  port.onDisconnect.addListener(()=>{ for(const barrier of fixtureBarriers.values())barrier.reject(Error('unknown: native connection ended after input'));fixtureBarriers.clear();port=null; stop().finally(()=>setTimeout(connect,1000)); });
}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  if(sender.id===chrome.runtime.id&&message?.event==='held_step'){reply({received:observeStep(message,sender)});return;}
  if(sender.id === chrome.runtime.id && message?.event === 'reader_error') { port?.postMessage({event:'reader_error',error:message.error,tab:sender.tab?.id,frame:sender.frameId});reply({received:true});return; }
  const popup=chrome.runtime.getURL('popup.html'),details=chrome.runtime.getURL('details.html');
  if (sender.id !== chrome.runtime.id || ![popup,details].includes(sender.url) || sender.frameId && sender.frameId !== 0) return;
  if (message?.command === 'stop') { stop().then(reply); return true; }
  if(sender.url===popup&&message?.command==='popup_status'){popupStatus().then(reply);return true;}
  if(sender.url===popup&&message?.command==='stop_popup'){stopPopup(message.tab,message.control).then(reply);return true;}
  // Details requests are data for the service's owner-only endpoint, never page input.
  if (sender.url === details && sender.tab?.id && sender.frameId === 0 && message?.command === 'sites') {
    const request_id=crypto.randomUUID();
    ownerRequests.set(request_id,reply);
    port?.postMessage({event:'owner_sites',request_id,arguments:message.arguments});
    setTimeout(()=>{if(ownerRequests.has(request_id)){ownerRequests.delete(request_id);reply({ok:false,error:{message:'Service unavailable; use the admin command.'}});}},10000);
    return true;
  }
});
chrome.tabs.onUpdated.addListener(async(tab,change)=>{
  const previous=controlled.get(tab);if(!previous)return;
  let current;try{current=await chrome.tabs.get(tab);}catch{return;}
  if(controlled.get(tab)!==previous)return;
  if(previous.virtualGroup?current.windowId!==previous.window:current.groupId!==groupId){release(tab);return;}
  if(change.url)try{safeURL(current.url);}catch{release(tab);}
});
function removedTab(tab){if(controlled.has(tab))release(tab);for(const state of preloadTargets.values())if(state.tab===tab)destroyedTarget(state);for(const map of [documentMethods,currentDocuments,formLoadedDocuments])for(const key of map.keys())if(key.startsWith('['+tab+','))map.delete(key);}
chrome.tabs.onRemoved.addListener(removedTab);
chrome.webNavigation.onCreatedNavigationTarget.addListener(createdTarget);
// Passive, exact-document method metadata only: no headers, bodies or interception.
chrome.webRequest.onCompleted.addListener(({tabId,frameId,type,method,documentId})=>{
  const key=JSON.stringify([tabId,frameId]);
  if(tabId>=0&&documentId&&currentDocuments.get(key)===documentId&&['main_frame','sub_frame'].includes(type))navigationRecord(documentMethods,key,{document:documentId,method});
},{urls:['http://*/*','https://*/*'],types:['main_frame','sub_frame']});
chrome.webNavigation.onCommitted.addListener(({tabId,frameId,documentId,transitionType,transitionQualifiers=[]})=>{
  const key=JSON.stringify([tabId,frameId]);
  const previous=currentDocuments.get(key),owner=controlled.get(tabId),reload=frameId===0?owner?.getReload:null;
  navigationRecord(currentDocuments,key,documentId);
  formLoadedDocuments.delete(key);
  if(transitionType==='form_submit')navigationRecord(formLoadedDocuments,key,documentId);
  if(documentMethods.get(key)?.document!==documentId){
    documentMethods.delete(key);
    // Chrome omits the new navigation document ID from some webRequest events.
    // These top-level transitions originate GET requests; form_submit/reload,
    // restoration and ambiguous subframe transitions never get this fallback.
    if(frameId===0&&!transitionQualifiers.includes('forward_back')&&(['typed','link'].includes(transitionType)||transitionType==='reload'&&reload?.document===previous))navigationRecord(documentMethods,key,{document:documentId,method:'GET'});
  }
  if(frameId===0&&owner)delete owner.getReload;
  if(recording)audit({navigation_method:{tab:tabId,frame:frameId,document:documentId,transition:transitionType,method:documentMethods.get(key)?.method||'unknown'}});
});
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
  if(method.startsWith('Runtime.')||method.startsWith('Debugger.')||method.startsWith('Target.')){await preloadEvent(source,method,params);return;}
  if(method==='Page.frameDetached'&&params.reason==='remove'){
    for(const state of preloadTargets.values())if(state.source.tabId===source.tabId&&state.source.sessionId&&state.frameId===params.frameId)destroyedTarget(state);
  }
  if(source.sessionId){const state=preloadTargets.get(targetKey(source));if(!state)return;source={tabId:state.tab};}
  if(method==='Page.frameStartedNavigating'){
    const owner=controlled.get(source.tabId),pending=owner?.getReload;
    if(pending&&params.frameId===pending.frameId){if(['reload','reloadBypassingCache'].includes(params.navigationType))rememberGet(source.tabId,params.loaderId);else delete owner.getReload;}
  }
  if (method === 'Page.javascriptDialogOpening') {
    const tab=source.tabId;
    try{safeURL(params.url);}catch{
      // The browser pushes dialog events for all attached frames. Exclude its
      // opener before accessing or retaining the message, and leave it to him.
      dialogs.set(tab,{frame_url:params.url,blocked:true});wakeDialog(tab);return;
    }
    const dialog={id:crypto.randomUUID(),kind:params.type,text:params.message,frame_url:params.url,button:'OK'};
    const input=controlled.get(tab),nonce=input?.inputNonce,plan=confirmationPlans.get(tab);
    if(nonce)dialogInputs.set(dialog,{epoch:input.epoch,nonce});
    dialogs.set(tab,dialog);
    const frames=await chrome.webNavigation.getAllFrames({tabId:tab}) || [];
    if(dialogs.get(tab)!==dialog||controlled.get(tab)!==input||input?.inputNonce!==nonce)return;
    const origins=frames.filter(frame=>frame.url===params.url);
    if(origins.length===1){dialog.frame=origins[0].frameId;dialog.browser_document=origins[0].documentId;}
    const expected=plan?.expected;
    const matched=confirmationPlans.get(tab)===plan && expected && origins.length===1 && plan.browser_document===dialog.browser_document &&
      ['kind','text','frame_url','button','frame'].every(key=>expected[key]===dialog[key]);
    wakeDialog(tab);
    if(matched){
      // Consume before entering the page again; a nested second dialog is a new question.
      plan.expected=null;plan.matched.push({...expected});
      try{await cdp(tab,'Page.handleJavaScriptDialog',{accept:true});}catch{}
    }
  }
  if (method === 'Page.javascriptDialogClosed') {
    const tab=source.tabId,input=dialogInputs.get(dialogs.get(tab));dialogs.delete(tab);
    // Closing a covered dialog has no separate tool call to finish its input.
    // Use the nonce captured at opening; an old close can never clear a new arm.
    if(input)try{await finishFrames(tab,await chrome.webNavigation.getAllFrames({tabId:tab})||[],input.epoch,input.nonce);}catch{}
  }
});
chrome.debugger.onDetach.addListener(async source=>{
  const tab=source.tabId,previous=controlled.get(tab);if(!previous)return;
  // An old detach notification may arrive after a replacement attachment.
  try{await cdp(tab,'Page.enable');}catch{if(controlled.get(tab)===previous)release(tab);}
});
connect();
