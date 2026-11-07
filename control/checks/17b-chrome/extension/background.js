// Feasibility check: deliberately raw RPC, not a product security boundary.
let port, selected, group, mode='hold', backstop=false, nextRule=1, texts=[], publicMode=false, publicDenyAll=false;
const attached=new Map(), pending=new Map(), history=[], errors=[];
let permit;
const denied=new Set();
const contentKey=p=>JSON.stringify([p.url,p.method,p.body,p.headerHash]);
const ending=new Map();
const persist=()=>chrome.storage.session.set({held:[...pending.values()],denied:[...denied]});
// Browser-owned debugger state can outlive a crashed extension renderer. Recover only to drop.
const recovery=(async()=>{const stored=await chrome.storage.session.get(['held','denied']);for(const k of stored.denied||[])denied.add(k);const saved=stored.held||[];for(const p of saved){try{await chrome.debugger.sendCommand(p.source,'Fetch.failRequest',{requestId:p.id,errorReason:'Aborted'});emit('check.recoveredDrop',{id:p.id,url:p.url});}catch(e){emit('check.recoveryUnavailable',{id:p.id,url:p.url,error:String(e)});}}await chrome.storage.session.set({held:[]});})();
const key=s=>JSON.stringify(s);
const target=()=>attached.get(selected)||{tabId:selected};
const command=(s,m,p={})=>chrome.debugger.sendCommand(s,m,p);
function emit(method,params){history.push({method,params,at:Date.now()});try{port?.postMessage({method,params});}catch{}}
function matchText(r){const raw=r.url+'\n'+(r.postData||'');return texts.filter(t=>[t,encodeURIComponent(t),encodeURIComponent(t).replace(/%20/g,'+'),JSON.stringify(t).slice(1,-1),btoa(unescape(encodeURIComponent(t)))].some(x=>raw.includes(x)));}
async function decide(id,release){
  const p=pending.get(id);if(!p)throw Error('NOT_PENDING');pending.delete(id);if(!release)denied.add(contentKey(p));await persist();
  if(p.rule)await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[p.rule]});
  await command(p.source,release?'Fetch.continueRequest':'Fetch.failRequest',release?{requestId:id}:{requestId:id,errorReason:'Aborted'});
  emit('check.decision',{id,release});
}
function dropTab(tabId,reason){
  if(ending.has(tabId))return ending.get(tabId);
  const task=(async()=>{
    for(const [id,p]of pending)if(p.source.tabId===tabId){try{await decide(id,false);}catch(e){errors.push(String(e));}}
    const s=attached.get(tabId);if(s){await chrome.debugger.detach(s).catch(e=>errors.push(String(e)));attached.delete(tabId);}
    emit('check.controlEnded',{tabId,reason});
  })();
  ending.set(tabId,task);return task.finally(()=>ending.delete(tabId));
}
async function pause(source,p){
  await recovery;
  if(source.tabId&&ending.has(source.tabId))return command(source,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});
  const r=p.request, typed=matchText(r), fixture=['/receive','/socket'].includes(new URL(r.url).pathname);
  if(new URL(r.url).pathname==='/socket')emit('check.socketPause',{source,request:p});
  if(!fixture&&!publicMode)return command(source,'Fetch.continueRequest',{requestId:p.requestId});
  const headers=Object.fromEntries(Object.entries(r.headers||{}).sort(([a],[b])=>a.localeCompare(b)));
  const headerHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(headers))))).map(b=>b.toString(16).padStart(2,'0')).join('');
  const preview={networkId:p.networkId,headerHash,...(!publicMode?{headers}:{}),url:r.url,method:r.method,body:r.postData??null,type:p.resourceType,typed,source};
  if(publicMode){
    const block=publicDenyAll||typed.length||!['GET','HEAD','OPTIONS'].includes(r.method)||['Fetch','XHR','Ping'].includes(p.resourceType);
    emit('check.public',{...preview,block:!!block});
    return command(source,block?'Fetch.failRequest':'Fetch.continueRequest',block?{requestId:p.requestId,errorReason:'Aborted'}:{requestId:p.requestId});
  }
  if(mode==='repeat'){
    const matches=permit&&permit.url===r.url&&permit.method===r.method&&permit.body===(r.postData??null)&&permit.headerHash===headerHash;
    if(matches)permit=null;
    await command(source,matches?'Fetch.continueRequest':'Fetch.failRequest',matches?{requestId:p.requestId}:{requestId:p.requestId,errorReason:'Aborted'});
    emit('check.repeated',{...preview,allowed:!!matches});return;
  }
  if(denied.has(contentKey(preview))){await command(source,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});emit('check.retryDropped',preview);return;}
  if(!port){await command(source,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});emit('check.orphanDropped',preview);return;}
  const entry={...preview,source,id:p.requestId,at:Date.now()};
  if(backstop&&source.tabId){
    entry.rule=1+(await chrome.declarativeNetRequest.getSessionRules()).reduce((n,r)=>Math.max(n,r.id),0);
    await chrome.declarativeNetRequest.updateSessionRules({addRules:[{id:entry.rule,priority:1,action:{type:'block'},condition:{tabIds:[source.tabId],requestMethods:[r.method.toLowerCase()],regexFilter:'^'+r.url.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'}}]});
  }
  pending.set(p.requestId,entry);await persist();if(!port){await decide(p.requestId,false);return;}emit('check.held',entry);
}
chrome.debugger.onEvent.addListener((s,m,p)=>{
  if(m==='Fetch.requestPaused')pause(s,p).catch(e=>{errors.push(String(e));emit('check.error',{error:String(e),request:p});});
  else {if(m==='Network.loadingFailed')emit('check.networkFailed',{source:s,event:p});try{port?.postMessage({method:m,params:p,sessionId:s.sessionId});}catch{}}
});
chrome.debugger.onDetach.addListener((s,reason)=>{attached.delete(s.tabId||s.targetId);emit('check.detached',{source:s,reason});});
chrome.tabs.onUpdated.addListener(async(id,change,tab)=>{if(attached.has(id)&&tab.groupId!==group)await dropTab(id,'left Claude group');});
chrome.tabs.onRemoved.addListener(id=>{attached.delete(id);emit('check.tabClosed',{id});});
async function attach(tabId){
  await recovery;
  if(!group){group=await chrome.tabs.group({tabIds:[tabId]});await chrome.tabGroups.update(group,{title:'Claude',color:'blue'});}else await chrome.tabs.group({groupId:group,tabIds:[tabId]});
  selected=tabId;const s={tabId};try{await chrome.debugger.attach(s,'1.3');}catch(e){await command(s,'Runtime.enable');emit('check.recoveredAttachment',{tabId,attachError:String(e)});}attached.set(tabId,s);return {tabId,group};
}
async function rpc(m,p){
  if(m==='Check.config'){({mode='hold',backstop=false,texts=[],publicMode=false}=p);permit=null;return {mode,backstop};}
  if(m==='Check.publicGuard'){publicDenyAll=p.denyAll;return {};}
  if(m==='Check.publicSocketBlock'){await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[999999],addRules:[{id:999999,priority:1,action:{type:'block'},condition:{tabIds:[selected],resourceTypes:['websocket']}}]});return {};}
  if(m==='Check.state')return {selected,group,groupInfo:group?await chrome.tabGroups.get(group).catch(()=>null):null,pending:[...pending.values()],history,errors,version:chrome.runtime.getManifest().version,rules:await chrome.declarativeNetRequest.getSessionRules()};
  if(m==='Check.decide')return decide(p.id,p.release);
  if(m==='Check.arm'){permit=p;return {};}
  if(m==='Check.targets')return chrome.debugger.getTargets();
  if(m==='Check.workerAttach'){const s={targetId:p.targetId};await chrome.debugger.attach(s,'1.3');attached.set(p.targetId,s);return command(s,'Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});}
  if(m==='Check.workerCommand')return command({targetId:p.targetId},p.method,p.params);
  if(m==='Check.attach')return attach(p.tabId);
  if(m==='Check.open'){const t=await chrome.tabs.create({url:p.url});await chrome.tabs.group({groupId:group,tabIds:[t.id]});return chrome.tabs.get(t.id);}
  if(m==='Check.tabs')return chrome.tabs.query({});
  if(m==='Check.ungroup'){await chrome.tabs.ungroup(p.tabId||selected);return {};}
  if(m==='Check.closeGroup'){await chrome.tabs.remove((await chrome.tabs.query({groupId:group})).map(t=>t.id));return {};}
  if(m==='Check.closeTab'){await chrome.tabs.remove(selected);return {};}
  if(m==='Check.detach'){await chrome.debugger.detach(target());return {};}
  if(m==='Check.reload'){setTimeout(()=>chrome.runtime.reload(),100);return {};}
  if(m==='Check.update')return new Promise(resolve=>chrome.runtime.requestUpdateCheck((status,details)=>resolve({status,details})));
  if(m==='Check.disable'){await chrome.management.setEnabled(chrome.runtime.id,false);return {};}
  if(m==='Check.info')return chrome.management.getSelf();
  if(m==='Check.uninstall'){await chrome.management.uninstallSelf({showConfirmDialog:false});return {};}
  if(m==='Check.versions')return chrome.management.getAll();
  if(m==='Check.enableGate'){await command(target(),'Network.enable');return command(target(),'Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});}
  if(!(await chrome.tabs.get(selected)).groupId|| (await chrome.tabs.get(selected)).groupId!==group)throw Error('OUTSIDE_CLAUDE_GROUP');
  return command(target(),m,p);
}
function connect(){
  port=chrome.runtime.connectNative('org.aresos.chrome_check');
  port.onMessage.addListener(async c=>{let result,error;try{result=await rpc(c.method,c.params||{});}catch(e){error=String(e);}try{port?.postMessage({id:c.id,result:result??{},error});}catch{}});
  port.onDisconnect.addListener(async()=>{port=undefined;for(const id of [...pending.keys()])try{await decide(id,false);}catch(e){errors.push(String(e));}});
  port.postMessage({method:'check.connected',params:{tabId:selected,group,version:chrome.runtime.getManifest().version}});
}
chrome.runtime.onMessage.addListener((m,s,reply)=>{if(s.id!==chrome.runtime.id||!m.attach)return; (async()=>{await attach(m.attach);connect();reply({attached:selected});})().catch(e=>reply({error:String(e)}));return true;});
chrome.runtime.onUpdateAvailable.addListener(d=>{emit('check.updateAvailable',d);chrome.runtime.reload();});
