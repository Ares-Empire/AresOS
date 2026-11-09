import {POLICY} from './policy.js';

const session = crypto.randomUUID();
const controlled = new Map(), used = new Set(), dialogs = new Map();
let groupId = null, port = null, serial = Promise.resolve(), recording = false, effectStarted = false, dispatchEpoch = null;
let excludedHosts = null;
const listSnapshots = new Map();
const ownerRequests = new Map(), stagedUploads = new Map(), confirmationPlans = new Map(), dialogWake = new Map();
function assertControl(tab,epoch=dispatchEpoch){if(!epoch || controlled.get(tab)?.epoch !== epoch)throw Error('stale_reference: control ended');}
const audit = value => { if (recording && port) port.postMessage({event:'audit',data:value}); return value; };
function safeURL(address) {
  if(!excludedHosts)throw Error('refused: owner-only excluded-sites setting is unavailable');
  if (address === 'about:blank') return address;
  let url; try { url = new URL(address); } catch { throw Error('refused: only web addresses are allowed'); }
  const hostname=url.hostname.replace(/\.+$/,'');
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password || excludedHosts.some(host => hostname === host || hostname.endsWith('.' + host))) throw Error('refused: approval/settings pages and non-web addresses belong to the owner');
  return address;
}
async function cdp(tab, method, parameters = {}) {
  if (!POLICY.cdpMethods.includes(method)) throw Error('permission_denied: DevTools method not allowed');
  if(method.startsWith('Input.') || ['Page.navigate','Page.navigateToHistoryEntry','Page.reload','Page.handleJavaScriptDialog','DOM.setFileInputFiles'].includes(method)){assertControl(tab);effectStarted=true;}
  const pending=chrome.debugger.sendCommand({tabId:tab},method,parameters);
  if(method.startsWith('Input.')) {
    const wake=new Promise(resolve=>dialogWake.set(tab,resolve));
    try{return audit(await Promise.race([pending,wake]));}finally{dialogWake.delete(tab);}
  }
  return audit(await pending);
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
  await chrome.debugger.attach({tabId:tab}, '1.3');
  await cdp(tab,'Page.enable');
  groupId = await chrome.tabs.group({tabIds:[tab],...(groupId === null ? {} : {groupId})});
  await chrome.tabGroups.update(groupId,{title:'Claude',color:'blue',collapsed:false});
  controlled.set(tab,original); await rules(); await badge();
  return {tab,session,group:groupId};
}
async function content(tab, frame, command, parameters={}) {
  if(['focus','select','check','install_file'].includes(command)){assertControl(tab);parameters={...parameters,generation:dispatchEpoch};effectStarted=true;}
  const reply = audit(await chrome.tabs.sendMessage(tab,{command,...parameters},{frameId:frame}));
  if (!reply?.ok) throw Error(reply?.error || 'stale_reference: page changed; read again');
  return reply.data;
}
async function requireTab(tab) {
  const current = await chrome.tabs.get(tab);
  if (!controlled.has(tab) || current.groupId !== groupId) { await release(tab); throw Error('stale_reference: tab is outside the Claude group'); }
  try { safeURL(current.url); } catch(error) { await release(tab); throw error; }
  return current;
}
async function release(tab) {
  const original = controlled.get(tab);
  controlled.delete(tab); dialogs.delete(tab);confirmationPlans.delete(tab);
  for(const [token,stage] of stagedUploads)if(stage.tab===tab)stagedUploads.delete(token);
  try {
    for (const frame of await chrome.webNavigation.getAllFrames({tabId:tab}) || []) { await content(tab,frame.frameId,'clear'); }
  } catch {}
  try { await chrome.debugger.detach({tabId:tab}); } catch {}
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
    target:Object.fromEntries(['element','role','name','label','title','href','value','password','states','editable','search','submit'].filter(key=>key in target).map(key=>[key,target[key]])),
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
  if (command.name === 'audit') { recording=command.enabled === true; return {recording}; }
  if(command.name==='configure')return configure(command.excluded_hosts);
  if(!excludedHosts)throw Error('refused: owner-only excluded-sites setting is unavailable');
  if (['tabs','downloads','history','bookmarks'].includes(command.name))return collection(command);
  if (command.name === 'take_tab') return take(tab);
  if (command.name === 'release_tab') return release(tab);
  if (command.name === 'stop') return stop();
  if (command.name === 'open') {
    safeURL(command.url);
    const created=await chrome.tabs.create({url:'about:blank'});await take(created.id);dispatchEpoch=controlled.get(created.id).epoch;
    if(command.url !== 'about:blank')await cdp(created.id,'Page.navigate',{url:command.url});
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
    for(const frame of await chrome.webNavigation.getAllFrames({tabId:tab})||[])try{await content(tab,frame.frameId,'finish_input',{generation:dispatchEpoch});}catch{}
    return {checked:true,dispatched:true,page:'Dialog answered once, as the page shows it.',steps:[]};
  }
  if (command.name === 'validity') {
    await requireTab(tab);safeURL((await chrome.webNavigation.getFrame({tabId:tab,frameId:reference.frame})).url);
    return {session,control:controlled.get(tab).epoch,...await content(tab,reference.frame,'ready')};
  }
  if (command.name === 'read' || command.name === 'facts') return facts(tab,reference);
  if (command.name === 'stage_file') {
    await requireTab(tab);dispatchEpoch=controlled.get(tab).epoch;
    let stage=stagedUploads.get(command.token);
    if(!stage){
      if(command.offset !== 0 || stagedUploads.size>=2)throw Error('refused: upload staging limit');
      stage={tab,epoch:dispatchEpoch,file:command.file,chunks:[],size:0};stagedUploads.set(command.token,stage);
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
  const snapshot = await facts(tab,reference);
  if (command.binding && stable(binding(snapshot,reference,command.kind,command.adapter)) !== stable(command.binding)) throw Error('stale_approval: page changed; prepare again');
  if (command.operation && used.has(command.operation)) throw Error('refused: operation already dispatched or attempted');
  const frame = snapshot.frames.find(frame=>frame.frame === reference.frame), target = frame.target;
  if (!target) throw Error('stale_reference: read again');
  if (command.expected && stable(command.expected) !== stable(target)) throw Error('stale_reference: element no longer holds the expected state');
  if (command.operation) used.add(command.operation); // consume before any event can enter the page
  if(command.confirmation && command.operation)confirmationPlans.set(tab,{operation:command.operation,expected:command.confirmation,browser_document:frame.browser_document,matched:[]});
  for(const other of snapshot.frames){
    assertControl(tab);
    await content(tab,other.frame,'set_control',{generation:dispatchEpoch});
    await content(tab,other.frame,'arm',{config:{...POLICY,conservative:command.conservative},target:other.frame===reference.frame ? target.element:null,form:other.frame===reference.frame ? frame.form?.element:null,operation:command.approved && other.frame===reference.frame ? command.operation:null,generation:dispatchEpoch,primary_submission:!!command.primary_submission && other.frame===reference.frame});
  }
  assertControl(tab);
  if (command.name === 'resume') { effectStarted=true; await content(tab,reference.frame,'resume',{hold:command.hold,operation:command.operation,generation:dispatchEpoch}); }
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
        const parts=input.key.split('+'), key=parts.pop(), modifiers=(parts.includes('Ctrl')?2:0)|(parts.includes('Cmd')?4:0)|(parts.includes('Alt')?1:0)|(parts.includes('Shift')?8:0);
        const normalized=key === 'Space' ? ' ':key, code=normalized === ' ' ? 'Space':key;
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyDown',key:normalized,code,modifiers,windowsVirtualKeyCode:{Enter:13,Space:32,Delete:46,Backspace:8}[key] || key.toUpperCase().charCodeAt(0),...(['Enter','Space'].includes(key)?{text:key==='Enter'?'\r':' '}: {})});
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyUp',key:normalized,code,modifiers});
      }
    } else if (input.verb === 'upload') await content(tab,reference.frame,'install_file',{element:reference.element,token:command.upload.token});
    else if (input.verb === 'check') {}
    else if (input.verb === 'select') await content(tab,reference.frame,input.verb,{element:reference.element,...input});
    else if (input.verb === 'scroll') {const point=await pointer(tab,snapshot,reference,target);await cdp(tab,'Input.dispatchMouseEvent',{type:'mouseWheel',...point,deltaX:input.x,deltaY:input.y});}
    else throw Error('permission_denied: unsupported input');
  }
  if(!dialogs.has(tab))for(const other of snapshot.frames)await content(tab,other.frame,'finish_input',{generation:dispatchEpoch});
  await new Promise(resolve=>setTimeout(resolve,POLICY.holdMs + 25));
  const steps=[];
  for (const frame of dialogs.has(tab) ? [] : await chrome.webNavigation.getAllFrames({tabId:tab}) || []) {
    try { safeURL(frame.url); steps.push(...(await content(tab,frame.frameId,'steps')).map(step=>({...step,frame:frame.frameId}))); } catch {}
  }
  const confirmation=confirmationPlans.get(tab);confirmationPlans.delete(tab);
  return {checked:!!command.binding,dispatched:true,steps,dialog:dialogs.get(tab)||null,confirmations:confirmation?.matched || [],page:'Input dispatched once; inspect a fresh read for what the page shows.'};
}
async function connect() {
  port=chrome.runtime.connectNative('org.aresos.chrome');
  const entropy=await navigator.userAgentData.getHighEntropyValues(['fullVersionList']);
  const version=entropy.fullVersionList.find(item=>item.brand === 'Google Chrome')?.version;
  port.postMessage({event:'hello',session,version});
  port.onMessage.addListener(message=>{
    if (message.owner_reply) { const pending=ownerRequests.get(message.owner_reply); if(pending){ownerRequests.delete(message.owner_reply);pending(message.result);} return; }
    serial=serial.then(async()=>{
      effectStarted=false;dispatchEpoch=null;
      try { port.postMessage({id:message.id,ok:true,data:await dispatch(message.command)}); }
      catch(error) { port?.postMessage({id:message.id,ok:false,error:effectStarted ? 'unknown: Input may have started; inspect status and the page, never retry. '+String(error.message):String(error.message)}); }
    });
  });
  port.onDisconnect.addListener(()=>{ port=null; stop().finally(()=>setTimeout(connect,1000)); });
}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
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
chrome.tabs.onUpdated.addListener((tab,change,current)=>{
  if (controlled.has(tab) && current.groupId !== groupId) release(tab);
  if (controlled.has(tab) && change.url) { try { safeURL(change.url); } catch { release(tab); } }
});
chrome.tabs.onRemoved.addListener(tab=>{ if (controlled.has(tab)) release(tab); });
chrome.webNavigation.onCreatedNavigationTarget.addListener(event=>{ if (controlled.has(event.sourceTabId)) serial=serial.then(()=>take(event.tabId)).catch(()=>release(event.tabId)); });
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
  if (method === 'Page.javascriptDialogOpening') {
    const tab=source.tabId,dialog={id:crypto.randomUUID(),kind:params.type,text:params.message,frame_url:params.url,button:'OK'};
    dialogs.set(tab,dialog);
    const frames=await chrome.webNavigation.getAllFrames({tabId:tab}) || [];
    const origins=frames.filter(frame=>frame.url===params.url);
    if(origins.length===1){dialog.frame=origins[0].frameId;dialog.browser_document=origins[0].documentId;}
    const plan=confirmationPlans.get(tab),expected=plan?.expected;
    const matched=expected && origins.length===1 && plan.browser_document===dialog.browser_document &&
      ['kind','text','frame_url','button','frame'].every(key=>expected[key]===dialog[key]);
    if(matched){
      // Consume before entering the page again; a nested second dialog is a new question.
      plan.expected=null;plan.matched.push({...expected});
      try{await cdp(tab,'Page.handleJavaScriptDialog',{accept:true});}catch{}
    }
    dialogWake.get(tab)?.({dialog:true});
  }
  if (method === 'Page.javascriptDialogClosed') dialogs.delete(source.tabId);
});
chrome.debugger.onDetach.addListener(source=>{ if (controlled.has(source.tabId)) release(source.tabId); });
connect();
