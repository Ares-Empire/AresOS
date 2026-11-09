import {POLICY} from './policy.js';

const session = crypto.randomUUID();
const controlled = new Map(), used = new Set(), dialogs = new Map();
const retiredControls=new Map();
function stepControl(tab,epoch){return controlled.get(tab)?.epoch===epoch?controlled.get(tab):retiredControls.get(JSON.stringify([tab,epoch]));}
function stepStates(tab){return [controlled.get(tab),...[...retiredControls].filter(([key])=>JSON.parse(key)[0]===tab).map(([,value])=>value)].filter(Boolean);}
let groupId = null, port = null, serial = Promise.resolve(), recording = false, effectStarted = false, dispatchEpoch = null;
let excludedHosts = null;
const listSnapshots = new Map(), fixtureBarriers = new Map();
const ownerRequests = new Map(), stagedUploads = new Map(), confirmationPlans = new Map(), dialogWake = new Map();
const dialogInputs=new WeakMap();
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
async function cdp(tab, method, parameters = {}) {
  if (!POLICY.cdpMethods.includes(method)) throw Error('permission_denied: DevTools method not allowed');
  if(method.startsWith('Input.')&&dialogs.has(tab))throw Error('unknown: a page dialog interrupted the input sequence; inspect the dialog and operation status, never retry');
  if(method.startsWith('Input.') || ['Page.navigate','Page.navigateToHistoryEntry','Page.reload','Page.handleJavaScriptDialog','DOM.setFileInputFiles'].includes(method)){assertControl(tab);effectStarted=true;}
  const pending=chrome.debugger.sendCommand({tabId:tab},method,parameters);
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
async function badge() { await chrome.action.setBadgeText({text:controlled.size ? 'ON' : ''}); await chrome.action.setBadgeBackgroundColor({color:'#2468ca'}); }
async function rules() {
  const previous = await chrome.declarativeNetRequest.getSessionRules();
  const tabIds = [...controlled.keys()];
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
  await chrome.scripting.registerContentScripts([{...common,id:'aresos-reader',world:'ISOLATED',js:['guard.js','reader.js']},{...common,id:'aresos-page',world:'MAIN',js:['page.js']}]);
  await rules();
  return {configured:true};
}
async function take(tab) {
  const current = await chrome.tabs.get(tab); safeURL(current.url);
  if (controlled.has(tab)) return {tab, session, group:groupId};
  if (current.url !== 'about:blank') try {
    const ready=await chrome.tabs.sendMessage(tab,{command:'ready'},{frameId:0});
    if(!ready?.ok || !ready.data.preload) throw Error('guard absent');
  } catch {
    throw Error('stale_reference: this document opened before the extension preload; the owner must reload it before control');
  }
  const original = {window:current.windowId,index:current.index,group:current.groupId,epoch:crypto.randomUUID()};
  effectStarted=true;await chrome.debugger.attach({tabId:tab}, '1.3');
  await cdp(tab,'Page.enable');
  groupId = await chrome.tabs.group({tabIds:[tab],...(groupId === null ? {} : {groupId})});
  await chrome.tabGroups.update(groupId,{title:'Claude',color:'blue',collapsed:false});
  controlled.set(tab,original); await rules(); await badge();
  return {tab,session,group:groupId};
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
  if (!controlled.has(tab) || current.groupId !== groupId) { await release(tab); throw Error('stale_reference: tab is outside the Claude group'); }
  try { safeURL(current.url); } catch(error) { await release(tab); throw error; }
  return current;
}
async function release(tab) {
  const original = controlled.get(tab);
  if(original){const key=JSON.stringify([tab,original.epoch]);retiredControls.set(key,original);while(retiredControls.size>32)retiredControls.delete(retiredControls.keys().next().value);setTimeout(()=>{if(retiredControls.get(key)===original)retiredControls.delete(key);},900000);}
  controlled.delete(tab); dialogs.delete(tab);confirmationPlans.delete(tab);
  wakeDialog(tab,{interrupted:true});
  for(const [id,barrier]of fixtureBarriers)if(barrier.tab===tab){fixtureBarriers.delete(id);barrier.reject(Error('unknown: interrupted after input'));}
  for(const [token,stage] of stagedUploads)if(stage.tab===tab)stagedUploads.delete(token);
  try { await chrome.debugger.detach({tabId:tab}); } catch {}
  try {
    const clear=Promise.all((await chrome.webNavigation.getAllFrames({tabId:tab})||[]).map(frame=>content(tab,frame.frameId,'clear').catch(()=>{})));
    await Promise.race([clear,new Promise(resolve=>setTimeout(resolve,1000))]);
  } catch {}
  if (original) {
    try {
      await chrome.tabs.ungroup(tab);
      await chrome.tabs.move(tab,{windowId:original.window,index:original.index});
      if (original.group >= 0) await chrome.tabs.group({tabIds:[tab],groupId:original.group});
    } catch {}
    port?.postMessage({event:'released',tab,session});
  }
  if (!controlled.size) groupId = null;
  await rules(); await badge();
  return {released:tab};
}
async function stop() { for (const tab of [...controlled.keys()]) await release(tab); return {stopped:true}; }
async function facts(tab, reference) {
  const current = await requireTab(tab);
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
    try { safeURL(frame.url); } catch { if (reference?.frame === frame.frameId) throw Error('refused: excluded frame'); continue; }
    const snapshot = await content(tab,frame.frameId,reference?.frame === frame.frameId ? 'facts':'read',reference?.frame === frame.frameId ? {element:reference.element}:{});
    if (reference?.frame === frame.frameId && snapshot.document !== reference.document) throw Error('stale_reference: document changed');
    result.push({frame:frame.frameId,parent:frame.parentFrameId,browser_document:frame.documentId,...snapshot});
  }
  if (reference && !result.some(frame=>frame.frame === reference.frame)) throw Error('stale_reference: frame is gone');
  return {session,tab,group:groupId,control:controlled.get(tab).epoch,url:current.url,title:current.title,frames:result,frame_tree:frames.map(frame=>({frame:frame.frameId,parent:frame.parentFrameId,url:frame.url})),dialog:dialogs.get(tab) || null};
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
  } else {
    let items;
    if(command.name==='downloads')items=await chrome.downloads.search({limit:10001,query:command.text?[command.text]:[]});
    else if(command.name==='history')items=await chrome.history.search({text:command.text||'',startTime:0,maxResults:10001});
    else if(command.name==='bookmarks')items=await chrome.bookmarks.search(command.text||{});
    else items=(await chrome.tabs.query({})).map(tab=>({tab:tab.id,title:tab.title,url:tab.url,controlled:controlled.has(tab.id)&&tab.groupId===groupId}));
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
    effectStarted=true;const created=await chrome.tabs.create({url:'about:blank'});await take(created.id);dispatchEpoch=controlled.get(created.id).epoch;
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
  if (command.name === 'close_tab') { await release(tab); await chrome.tabs.remove(tab); return {closed:tab}; }
  if (command.name === 'navigate') {
    if (command.url) { safeURL(command.url); await cdp(tab,'Page.navigate',{url:command.url}); }
    else if (command.direction === 'reload') await cdp(tab,'Page.reload');
    else {
      const history = await cdp(tab,'Page.getNavigationHistory');
      const entry = history.entries[history.currentIndex + (command.direction === 'back' ? -1:1)];
      if (!entry) throw Error('refused: no history entry in that direction');
      safeURL(entry.url); await cdp(tab,'Page.navigateToHistoryEntry',{entryId:entry.id});
    }
    return {navigated:true};
  }
  if (command.name !== 'input' && command.name !== 'resume') throw Error('permission_denied: unknown fixed command');
  let snapshot = await facts(tab,reference);
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
  if(current.groupId!==groupId){release(tab);return;}
  if(change.url)try{safeURL(current.url);}catch{release(tab);}
});
chrome.tabs.onRemoved.addListener(tab=>{ if (controlled.has(tab)) release(tab); });
chrome.webNavigation.onCreatedNavigationTarget.addListener(event=>{ if (controlled.has(event.sourceTabId)) serial=serial.then(()=>take(event.tabId)).catch(()=>release(event.tabId)); });
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
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
