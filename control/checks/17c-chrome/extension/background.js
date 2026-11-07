// CHECK ONLY: raw trusted runner RPC. Never ship this transport as the tool service.
let port,selected,group,publicMode=false,ownerTab,active=true,wrapSource;
const attached=new Map(),pending=new Map(),history=[],errors=[],allowances=[],guards=new Set();
const cmd=(s,m,p={})=>chrome.debugger.sendCommand(s,m,p);
async function initiator(source,p){const info=structuredClone(p.initiator);let stack=info.stack;for(let depth=0;stack&&depth<8;depth++){if(!stack.parent&&stack.parentId){try{stack.parent=(await cmd(source,'Debugger.getStackTrace',{stackTraceId:stack.parentId})).stackTrace;}catch(e){info.unresolved=String(e);break;}}stack=stack.parent;}emit('check.initiator',{source,url:p.request.url,method:p.request.method,initiator:info});}
const ready=chrome.storage.local.get('guards').then(s=>{for(const site of s.guards||[])guards.add(site)});
const emit=(method,params)=>{history.push({method,params,at:Date.now()});try{port?.postMessage({method,params})}catch{}};
const safe=url=>/^https?:/.test(url);
const site=url=>new URL(url).origin; // Loopback fixtures only; NOT a public-suffix implementation.
async function badge(on){await chrome.action.setBadgeText({text:on?'ON':'STOP'});await chrome.action.setBadgeBackgroundColor({color:on?'#1263bd':'#b91c1c'});if(group)await chrome.tabGroups.update(group,{color:on?'blue':'grey'}).catch(()=>{});}
async function guard(url){await ready;guards.add(site(url));await chrome.storage.local.set({guards:[...guards]});emit('check.guard',{sites:[...guards]});}
async function report(p,source){
  if(p.event!=='held'){emit('check.pageEvent',{...p,source});return;}
  if(publicMode){p={...p,stack:undefined,description:{...p.description,...(p.description.body?{body:p.description.body.slice(0,2000),bodyLength:p.description.body.length}:{}),...(p.description.fields?{fields:p.description.fields.slice(0,2000)}:{})}};}
  const id=JSON.stringify(source)+':'+p.id,entry={...p,id,localId:p.id,source,at:Date.now(),owner:source.tabId===ownerTab};pending.set(id,entry);emit('check.pageHeld',entry);
  if(entry.owner){await chrome.notifications.create(id,{type:'basic',iconUrl:'icon.png',title:'Guarded site send',message:p.kind+' '+(p.description.url||''),buttons:[{title:'Send'},{title:"Don't send"}],requireInteraction:true});emit('check.notification',{id,buttons:['Send',"Don't send"]});}
}
async function pageCall(p,release,end=false){
  if(p.source.sessionId||p.source.targetId)return cmd(p.source,'Runtime.evaluate',{expression:end?'globalThis.__hold17?.end()':`globalThis.__hold17?.decide(${JSON.stringify(p.localId)},${release})`});
  return chrome.scripting.executeScript({target:{tabId:p.source.tabId,...(p.source.documentId?{documentIds:[p.source.documentId]}:{frameIds:[p.source.frameId||0]})},world:'MAIN',func:(id,go,end)=>end?globalThis.__hold17?.end():globalThis.__hold17?.decide(id,go),args:[p.localId,release,end]});
}
async function decide(id,release){
  const p=pending.get(id);if(!p)throw Error('NOT_PENDING');pending.delete(id);
  if(p.network){if(release){allowances.push(p);emit('check.repeatArmed',p);}return;}
  let allowance;
  if(release&&['fetch','xhr','beacon','form'].includes(p.kind)){
    const d=p.description,tab=p.source.tabId?await chrome.tabs.get(p.source.tabId).catch(()=>({url:'http://127.0.0.1/'})):{url:'http://127.0.0.1/'};
    let url=new URL(d.url,tab.url).href,body=d.body??null,method=(d.method||'POST').toUpperCase();
    if(p.kind==='form'){body=new URLSearchParams(JSON.parse(d.fields)).toString();if(method==='GET'){url+=(url.includes('?')?'&':'?')+body;body=null;}}
    allowance={url,method,body,source:p.source,inPage:true};allowances.push(allowance);
  }
  try{const result=await pageCall(p,release);if(release&&!(Array.isArray(result)?result[0]?.result:result.result?.value))throw Error('CALL_GONE_OR_CHANGED');}catch(e){const i=allowances.indexOf(allowance);if(i>=0)allowances.splice(i,1);if(!release&&/No document with id|No frame with (?:id|ID)|No session with given id|Target closed/i.test(String(e)))emit('check.dropGone',{id,error:String(e)});else throw e;}emit('check.decision',{id,release});
}
async function stop(reason){active=false;for(const p of [...pending.values()]){try{await decide(p.id,false);await pageCall(p,false,true)}catch(e){emit('check.dropGone',{id:p.id,error:String(e)})}}await badge(false);for(const s of attached.values())await cmd(s,'Runtime.evaluate',{expression:'globalThis.__hold17?.end()'}).catch(()=>{});for(const s of attached.values())await chrome.debugger.detach(s).catch(()=>{});attached.clear();allowances.length=0;emit('check.stopped',{reason});}
async function gate(source,p){
  const r=p.request,u=new URL(r.url),fixture=u.pathname==='/receive';
  if(!fixture&&!publicMode)return cmd(source,'Fetch.continueRequest',{requestId:p.requestId});
  const headers=Object.fromEntries(Object.entries(r.headers||{}).sort(([a],[b])=>a.localeCompare(b)));
  const headerHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(headers))))).map(b=>b.toString(16).padStart(2,'0')).join('');
  const entry={id:'network:'+p.requestId,network:true,url:r.url,method:r.method,body:r.postData??null,headerHash,source,type:p.resourceType};
  if(publicMode){const block=r.url.includes('Synthetic17c')||!['GET','HEAD'].includes(r.method)||['Fetch','XHR','Ping'].includes(p.resourceType);emit('check.public',{...entry,body:entry.body?.slice(0,2000)??null,bodyLength:entry.body?.length||0,block});return cmd(source,block?'Fetch.failRequest':'Fetch.continueRequest',block?{requestId:p.requestId,errorReason:'Aborted'}:{requestId:p.requestId});}
  const i=allowances.findIndex(a=>a.url===entry.url&&a.method===entry.method&&a.body===entry.body&&(a.inPage||a.headerHash===headerHash)&&a.source.tabId===source.tabId);
  if(i>=0){allowances.splice(i,1);await cmd(source,'Fetch.continueRequest',{requestId:p.requestId});emit('check.allowed',entry);return;}
  // Fail immediately. No live Fetch pause may survive an extension lifecycle event.
  await cmd(source,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});pending.set(entry.id,entry);emit('check.networkHeld',entry);
}
async function prepare(s,worker=false){
  const setup=async(m,p={})=>{if(!worker)return cmd(s,m,p);emit('check.workerStage',{source:s,method:m});let timer;try{return await Promise.race([cmd(s,m,p),new Promise((_,reject)=>{timer=setTimeout(()=>reject(Error('WORKER_SETUP_TIMEOUT '+m)),3000)})])}finally{clearTimeout(timer)}};
  await setup('Runtime.enable');await setup('Network.enable');await setup('Debugger.enable');await setup('Debugger.setAsyncCallStackDepth',{maxDepth:32});
  if(worker){await setup('Runtime.addBinding',{name:'__report17'});await setup('Runtime.evaluate',{expression:wrapSource});}
  try{await setup('Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});}catch(e){emit('check.workerGateUnsupported',{source:s,error:String(e)});if(!worker)throw e;}
  try{await cmd(s,'Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:true,flatten:true});}catch(e){emit('check.autoAttachUnsupported',{source:s,error:String(e)})}
}
chrome.debugger.onEvent.addListener((s,m,p)=>{
  if(m==='Fetch.requestPaused')gate(s,p).catch(e=>{errors.push(String(e));emit('check.error',{error:String(e),source:s});cmd(s,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'}).catch(()=>{});});
  else if(m==='Runtime.bindingCalled'&&p.name==='__report17')report(JSON.parse(p.payload),s).catch(e=>errors.push(String(e)));
  else if(m==='Target.attachedToTarget'){
    const child={...s,sessionId:p.sessionId};emit('check.child',{source:child,info:p.targetInfo,waiting:p.waitingForDebugger});
    prepare(child,p.targetInfo.type!=='iframe').catch(e=>emit('check.childError',{source:child,error:String(e)})).finally(()=>cmd(child,'Runtime.runIfWaitingForDebugger').catch(()=>{}));
  }else if(m==='Network.requestWillBeSent'&&!publicMode)initiator(s,p).catch(e=>emit('check.traceError',{error:String(e)}));
  else if(/WebSocket|webTransport/i.test(m))emit(m,{source:s,...p});
});
chrome.debugger.onDetach.addListener((s,reason)=>emit('check.detached',{source:s,reason}));
async function attach(tabId,controlled=true){
  const tab=await chrome.tabs.get(tabId);if(!safe(tab.url))throw Error('FORBIDDEN_PAGE');
  if(controlled){if(!group){group=await chrome.tabs.group({tabIds:[tabId]});await chrome.tabGroups.update(group,{title:'Claude',color:'blue'});}else await chrome.tabs.group({groupId:group,tabIds:[tabId]});selected=tabId;}
  const s={tabId};if(!attached.has(tabId)){await chrome.debugger.attach(s,'1.3');attached.set(tabId,s);await prepare(s);emit('check.gateReady',{source:s,url:tab.url});}active=true;await badge(true);return {tabId,group};
}
async function rpc(m,p){
  await ready;if(!wrapSource)wrapSource=await (await fetch(chrome.runtime.getURL('wrap.js'))).text();
  if(m==='Check.state')return {selected,group,groupInfo:group?await chrome.tabGroups.get(group).catch(()=>null):null,active,pending:[...pending.values()],history,errors,guards:[...guards],badge:await chrome.action.getBadgeText({}),manifest:chrome.runtime.getManifest()};
  if(m==='Check.clearHistory'){history.length=0;return {};}
  if(m==='Check.attach')return attach(p.tabId);
  if(m==='Check.guard'){const tab=await chrome.tabs.get(selected);await guard(tab.url);for(const t of await chrome.tabs.query({}))if(safe(t.url)&&site(t.url)===site(tab.url))await attach(t.id,false);return {};}
  if(m==='Check.ownerTab'){ownerTab=p.tabId;return attach(p.tabId,false);}
  if(m==='Check.ownerCommand')return cmd({tabId:ownerTab},p.method,p.params);
  if(m==='Check.decide')return decide(p.id,p.release);
  if(m==='Check.traceRelease'){const held=pending.get(p.id);if(!held)throw Error('NOT_PENDING');return pageCall(held,true);}
  if(m==='Check.stop')return stop('runner');
  if(m==='Check.popup')return chrome.action.openPopup();
  if(m==='Check.detach'){await chrome.debugger.detach({tabId:selected});attached.delete(selected);return {};}
  if(m==='Check.public'){publicMode=true;await chrome.declarativeNetRequest.updateSessionRules({addRules:[{id:900,priority:1,action:{type:'block'},condition:{resourceTypes:['websocket']}},{id:901,priority:1,action:{type:'block'},condition:{requestMethods:['post','put','patch','delete','connect','options','other']}}]});return {};}
  if(m==='Check.tabs')return chrome.tabs.query({});
  if(m==='Check.open'){if(!safe(p.url))throw Error('FORBIDDEN_PAGE');return chrome.tabs.create({url:p.url});}
  if(m==='Check.targets')return chrome.debugger.getTargets();
  if(m==='Check.workerAttach'){const s={targetId:p.targetId};await chrome.debugger.attach(s,'1.3');attached.set(p.targetId,s);await prepare(s,true);return {};}
  if(m==='Check.auto'){for(const s of attached.values())if(s.tabId)await cmd(s,'Target.setAutoAttach',{autoAttach:p.enabled,waitForDebuggerOnStart:p.enabled,flatten:true});return {};}
  if(m==='Check.primaryAuto')return cmd({tabId:selected},'Target.setAutoAttach',{autoAttach:true,waitForDebuggerOnStart:true,flatten:true});
  if(m==='Check.workerCommand')return cmd({targetId:p.targetId},p.method,p.params);
  if(m==='Check.reload'){setTimeout(()=>chrome.runtime.reload(),100);return {};}
  if(m==='Check.update')return new Promise(resolve=>chrome.runtime.requestUpdateCheck((status,details)=>resolve({status,details})));
  if(m==='Check.contentForge')return chrome.tabs.sendMessage(selected,{probeForge:true,id:p.id,decision:p.decision});
  if(m==='Check.details')return chrome.tabs.create({url:chrome.runtime.getURL('details.html')+'?id='+encodeURIComponent(p.id)});
  if(m==='Check.retire'){if(p.evidence!=='adapter-resolved-all')throw Error('UNRESOLVED_SITE');guards.clear();await chrome.storage.local.set({guards:[]});emit('check.retired',{reason:'synthetic adapter evidence'});return {};}
  if(!(await chrome.tabs.get(selected)).groupId|| (await chrome.tabs.get(selected)).groupId!==group)throw Error('OUTSIDE_CLAUDE_GROUP');
  if(!safe((await chrome.tabs.get(selected)).url))throw Error('FORBIDDEN_PAGE');return cmd({tabId:selected},m,p);
}
chrome.runtime.onMessage.addListener((m,s,reply)=>{
  (async()=>{
    const exact=name=>s.id===chrome.runtime.id&&s.url?.split('?')[0]===chrome.runtime.getURL(name)&&s.frameId===0;
    if(m.attach&&exact('select.html')){await rpc('Check.attach',{tabId:m.attach});connect();return {attached:selected};}
    if(m.report&&s.tab&&(safe(s.url)||safe(s.origin))){await report(m.report,{tabId:s.tab.id,frameId:s.frameId,documentId:s.documentId});return {};}
    // Popup senders omit both frameId and documentId in this Chrome. Stop grants no send authority.
    if(m.stop){const contexts=await chrome.runtime.getContexts({contextTypes:['POPUP'],documentUrls:[chrome.runtime.getURL('popup.html')]});emit('check.stopSender',{sender:{id:s.id,url:s.url,frameId:s.frameId,documentId:s.documentId},contexts});if(s.id===chrome.runtime.id&&s.url===chrome.runtime.getURL('popup.html')&&!s.tab&&contexts.some(c=>c.frameId===0)){await stop('popup Stop');return {stopped:true};}throw Error('UNTRUSTED_STOP');}
    const ownDetails=s.id===chrome.runtime.id&&s.url?.startsWith(chrome.runtime.getURL('details.html')+'?id=')&&s.frameId===0;
    if(m.preview&&ownDetails)return {pending:pending.get(m.preview),unresolved:[...guards]};
    if(m.decision){if(!ownDetails){emit('check.forgeryRefused',{sender:{id:s.id,url:s.url,frameId:s.frameId}});throw Error('UNTRUSTED_DECISION');}if(m.decision==='retire'){guards.clear();await chrome.storage.local.set({guards:[]});return {retired:true};}await decide(m.id,m.decision==='send');return {accepted:true};}
    throw Error('UNTRUSTED_MESSAGE');
  })().then(r=>reply(r??{}),e=>reply({error:String(e)}));return true;
});
chrome.notifications.onButtonClicked.addListener((id,button)=>{emit('check.notificationButton',{id,button});decide(id,button===0).catch(e=>errors.push(String(e)));});
chrome.notifications.onClicked.addListener(id=>chrome.tabs.create({url:chrome.runtime.getURL('details.html')+'?id='+encodeURIComponent(id)}));
chrome.runtime.onStartup.addListener(async()=>{await ready;emit('check.startup',{guards:[...guards]});for(const t of await chrome.tabs.query({}))if(safe(t.url)&&guards.has(site(t.url)))attach(t.id,false).catch(e=>emit('check.startupAttachError',{error:String(e)}));});
function connect(){port=chrome.runtime.connectNative('org.aresos.chrome_check');port.onMessage.addListener(async c=>{try{port?.postMessage({id:c.id,result:(await rpc(c.method,c.params||{}))??{}})}catch(e){port?.postMessage({id:c.id,error:String(e)})}});port.onDisconnect.addListener(()=>{port=undefined;stop('host loss').catch(e=>errors.push(String(e)))});port.postMessage({method:'check.connected',params:{tabId:selected,group,version:chrome.runtime.getManifest().version}});}
chrome.runtime.onUpdateAvailable.addListener(()=>chrome.runtime.reload());
