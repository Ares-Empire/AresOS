import {POLICY} from './policy.js';

const session = crypto.randomUUID();
const controlled = new Map(), used = new Set(), dialogs = new Map();
let groupId = null, port = null, serial = Promise.resolve();
const audit = value => { /* Browser responses are forwarded verbatim to the CI recorder. */ return value; };
function safeURL(address) {
  if (address === 'about:blank') return address;
  let url; try { url = new URL(address); } catch { throw Error('refused: only web addresses are allowed'); }
  if (!['http:','https:'].includes(url.protocol) || url.username || url.password || POLICY.fixedHosts.some(host => url.hostname === host || url.hostname.endsWith('.' + host))) throw Error('refused: approval/settings pages and non-web addresses belong to the owner');
  return address;
}
async function cdp(tab, method, parameters = {}) {
  if (!POLICY.cdpMethods.includes(method)) throw Error('permission_denied: DevTools method not allowed');
  return audit(await chrome.debugger.sendCommand({tabId:tab}, method, parameters));
}
async function badge() { await chrome.action.setBadgeText({text:controlled.size ? 'ON' : ''}); await chrome.action.setBadgeBackgroundColor({color:'#2468ca'}); }
async function rules() {
  const previous = await chrome.declarativeNetRequest.getSessionRules();
  const tabIds = [...controlled.keys()];
  await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:previous.map(rule=>rule.id),addRules:tabIds.length ? [{id:1,priority:1,action:{type:'block'},condition:{tabIds,requestDomains:POLICY.fixedHosts,resourceTypes:['main_frame','sub_frame']}}] : []});
}
async function take(tab) {
  const current = await chrome.tabs.get(tab); safeURL(current.url);
  if (controlled.has(tab)) return {tab, session, group:groupId};
  const original = {window:current.windowId,index:current.index,group:current.groupId};
  await chrome.debugger.attach({tabId:tab}, '1.3');
  await cdp(tab,'Page.enable');
  groupId = await chrome.tabs.group({tabIds:[tab],...(groupId === null ? {} : {groupId})});
  await chrome.tabGroups.update(groupId,{title:'Claude',color:'blue',collapsed:false});
  controlled.set(tab,original); await rules(); await badge();
  return {tab,session,group:groupId};
}
async function main(tab, frame, command, args=[]) {
  const output = await chrome.scripting.executeScript({target:{tabId:tab,frameIds:[frame]},world:'MAIN',func:(command,args)=> {
    const api = globalThis[Symbol.for('aresos.chrome.page.v1')];
    if (!api || !['arm','resume','drop','stop'].includes(command)) throw Error('refused: page guard absent');
    return api[command](...args);
  },args:[command,args]});
  return audit(output[0]?.result);
}
async function content(tab, frame, command, parameters={}) {
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
  controlled.delete(tab); dialogs.delete(tab);
  try {
    for (const frame of await chrome.webNavigation.getAllFrames({tabId:tab}) || []) await main(tab,frame.frameId,'stop');
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
    result.push({frame:frame.frameId,...snapshot});
  }
  if (reference && !result.some(frame=>frame.frame === reference.frame)) throw Error('stale_reference: frame is gone');
  return {session,tab,group:groupId,url:current.url,title:current.title,frames:result,dialog:dialogs.get(tab) || null};
}
function binding(facts, reference, kind, adapter) {
  const frame = facts.frames.find(frame=>frame.frame === reference.frame);
  if (!frame?.target) throw Error('stale_reference: target not found');
  const target = frame.target;
  return {session,tab:facts.tab,url:facts.url,document:frame.document,frame:frame.frame,frame_url:frame.url,
    target:Object.fromEntries(['element','role','name','label','title','href','value','password','states','editable','search','submit'].filter(key=>key in target).map(key=>[key,target[key]])),
    form:frame.form,
    editable:kind === 'send' && !frame.form && !adapter ? facts.frames.map(frame=>({frame:frame.frame,document:frame.document,url:frame.url,fields:frame.editable})) : null,
    item:['delete','pay','activation','confirmation'].includes(kind) ? frame.item : null,
    adapter:adapter ? frame.adapter:null,dialog:facts.dialog};
}
const stable = value => JSON.stringify(value, function(key,value) { return value && !Array.isArray(value) && typeof value === 'object' ? Object.fromEntries(Object.entries(value).sort(([a],[b])=>a.localeCompare(b))) : value; });
async function dispatch(command) {
  const tab = command.tab ?? command.reference?.tab;
  const reference = command.reference;
  if (command.name === 'tabs') return {session,items:(await chrome.tabs.query({})).map(tab=>({tab:tab.id,title:tab.title,url:tab.url,controlled:controlled.has(tab.id) && tab.groupId === groupId}))};
  if (command.name === 'take_tab') return take(tab);
  if (command.name === 'release_tab') return release(tab);
  if (command.name === 'stop') return stop();
  if (command.name === 'open') { safeURL(command.url); const created = await chrome.tabs.create({url:command.url}); return take(created.id); }
  if (command.name === 'downloads') return {items:await chrome.downloads.search({limit:10,query:command.text ? [command.text]:[]})};
  if (command.name === 'history') return {items:await chrome.history.search({text:command.text || '',maxResults:10})};
  if (command.name === 'bookmarks') return {items:await chrome.bookmarks.search(command.text || {})};
  if (command.name === 'read' || command.name === 'facts') return facts(tab,reference);
  await requireTab(tab);
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
  await main(tab,reference.frame,'arm',[POLICY,target.element,frame.form?.element,command.operation || null]);
  if (command.name === 'resume') await main(tab,reference.frame,'resume',[command.hold,command.operation]);
  else {
    const input = command.input;
    if (target.password) throw Error('owner_signin: password fields belong to the owner');
    if (input.verb === 'click') {
      if (target.href && !target.href.startsWith('javascript:')) safeURL(target.href);
      const x=target.box.x+target.box.width/2, y=target.box.y+target.box.height/2;
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
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyDown',key:normalized,code,modifiers,windowsVirtualKeyCode:{Enter:13,Space:32,Delete:46,Backspace:8}[key] || key.toUpperCase().charCodeAt(0)});
        await cdp(tab,'Input.dispatchKeyEvent',{type:'keyUp',key:normalized,code,modifiers});
      }
    } else if (['select','check'].includes(input.verb)) await content(tab,reference.frame,input.verb,{element:reference.element,...input});
    else if (input.verb === 'scroll') await cdp(tab,'Input.dispatchMouseEvent',{type:'mouseWheel',x:target.box.x+1,y:target.box.y+1,deltaX:input.x,deltaY:input.y});
    else throw Error('permission_denied: unsupported input');
  }
  await new Promise(resolve=>setTimeout(resolve,POLICY.holdMs + 25));
  const steps=[];
  for (const frame of await chrome.webNavigation.getAllFrames({tabId:tab}) || []) {
    try { safeURL(frame.url); steps.push(...(await content(tab,frame.frameId,'steps')).map(step=>({...step,frame:frame.frameId}))); } catch {}
  }
  return {checked:!!command.binding,dispatched:true,steps,page:'Input dispatched once; inspect a fresh read for what the page shows.'};
}
async function connect() {
  port=chrome.runtime.connectNative('org.aresos.chrome');
  const entropy=await navigator.userAgentData.getHighEntropyValues(['fullVersionList']);
  const version=entropy.fullVersionList.find(item=>item.brand === 'Google Chrome')?.version;
  port.postMessage({event:'hello',session,version});
  port.onMessage.addListener(message=>{
    serial=serial.then(async()=>{
      try { port.postMessage({id:message.id,ok:true,data:await dispatch(message.command)}); }
      catch(error) { port?.postMessage({id:message.id,ok:false,error:String(error.message)}); }
    });
  });
  port.onDisconnect.addListener(()=>{ port=null; stop().finally(()=>setTimeout(connect,1000)); });
}
chrome.runtime.onMessage.addListener((message,sender,reply)=>{
  const popup=chrome.runtime.getURL('popup.html'),details=chrome.runtime.getURL('details.html');
  if (sender.id !== chrome.runtime.id || ![popup,details].includes(sender.url) || sender.frameId && sender.frameId !== 0) return;
  if (message?.command === 'stop') { stop().then(reply); return true; }
  // Details requests are data for the service's owner-only endpoint, never page input.
  if (sender.url === details && !sender.tab?.id) return;
});
chrome.tabs.onUpdated.addListener((tab,change,current)=>{
  if (controlled.has(tab) && current.groupId !== groupId) release(tab);
  if (controlled.has(tab) && change.url) { try { safeURL(change.url); } catch { release(tab); } }
});
chrome.tabs.onRemoved.addListener(tab=>{ if (controlled.has(tab)) release(tab); });
chrome.webNavigation.onCreatedNavigationTarget.addListener(event=>{ if (controlled.has(event.sourceTabId)) serial=serial.then(()=>take(event.tabId)).catch(()=>release(event.tabId)); });
chrome.debugger.onEvent.addListener((source,method,params)=>{
  if (method === 'Page.javascriptDialogOpening') dialogs.set(source.tabId,{kind:params.type,text:params.message,frame_url:params.url,button:'OK'});
  if (method === 'Page.javascriptDialogClosed') dialogs.delete(source.tabId);
});
chrome.debugger.onDetach.addListener(source=>{ if (controlled.has(source.tabId)) release(source.tabId); });
connect();
