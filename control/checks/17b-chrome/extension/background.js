// Feasibility check: deliberately raw RPC, not a product security boundary.
let port, selected, group, mode='hold', backstop=false, nextRule=1, texts=[], publicMode=false;
const attached=new Map(), pending=new Map(), history=[], errors=[];
let permit;
const key=s=>JSON.stringify(s);
const target=()=>attached.get(selected)||{tabId:selected};
const command=(s,m,p={})=>chrome.debugger.sendCommand(s,m,p);
function emit(method,params){history.push({method,params,at:Date.now()});try{port?.postMessage({method,params});}catch{}}
function matchText(r){const raw=r.url+'\n'+(r.postData||'');return texts.filter(t=>[t,encodeURIComponent(t),encodeURIComponent(t).replace(/%20/g,'+'),JSON.stringify(t).slice(1,-1),btoa(unescape(encodeURIComponent(t)))].some(x=>raw.includes(x)));}
async function decide(id,release){
  const p=pending.get(id);if(!p)throw Error('NOT_PENDING');pending.delete(id);
  if(p.rule)await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[p.rule]});
  await command(p.source,release?'Fetch.continueRequest':'Fetch.failRequest',release?{requestId:id}:{requestId:id,errorReason:'Aborted'});
  emit('check.decision',{id,release});
}
async function dropTab(tabId,reason){
  for(const [id,p]of pending)if(p.source.tabId===tabId){try{await decide(id,false);}catch(e){errors.push(String(e));}}
  const s=attached.get(tabId);if(s){await chrome.debugger.detach(s).catch(e=>errors.push(String(e)));attached.delete(tabId);}
  emit('check.controlEnded',{tabId,reason});
}
async function pause(source,p){
  const r=p.request, typed=matchText(r), fixture=new URL(r.url).pathname==='/receive';
  if(!fixture&&!publicMode)return command(source,'Fetch.continueRequest',{requestId:p.requestId});
  const preview={url:r.url,method:r.method,body:r.postData??null,type:p.resourceType,typed,source};
  if(publicMode){
    const block=typed.length||!['GET','HEAD','OPTIONS'].includes(r.method)||['Fetch','XHR','Ping'].includes(p.resourceType);
    emit('check.public',{...preview,block:!!block});
    return command(source,block?'Fetch.failRequest':'Fetch.continueRequest',block?{requestId:p.requestId,errorReason:'Aborted'}:{requestId:p.requestId});
  }
  if(mode==='repeat'){
    const matches=permit&&permit.url===r.url&&permit.method===r.method&&permit.body===(r.postData??null);
    if(matches)permit=null;
    await command(source,matches?'Fetch.continueRequest':'Fetch.failRequest',matches?{requestId:p.requestId}:{requestId:p.requestId,errorReason:'Aborted'});
    emit('check.repeated',{...preview,allowed:!!matches});return;
  }
  if(!port){await command(source,'Fetch.failRequest',{requestId:p.requestId,errorReason:'Aborted'});emit('check.orphanDropped',preview);return;}
  const entry={...preview,source,id:p.requestId,at:Date.now()};
  if(backstop&&source.tabId){
    entry.rule=nextRule++;
    await chrome.declarativeNetRequest.updateSessionRules({addRules:[{id:entry.rule,priority:1,action:{type:'block'},condition:{tabIds:[source.tabId],requestMethods:[r.method.toLowerCase()],regexFilter:'^'+r.url.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$'}}]});
  }
  pending.set(p.requestId,entry);emit('check.held',entry);
}
chrome.debugger.onEvent.addListener((s,m,p)=>{
  if(m==='Fetch.requestPaused')pause(s,p).catch(e=>{errors.push(String(e));emit('check.error',{error:String(e),request:p});});
  else {try{port?.postMessage({method:m,params:p,sessionId:s.sessionId});}catch{}}
});
chrome.debugger.onDetach.addListener((s,reason)=>{attached.delete(s.tabId||s.targetId);emit('check.detached',{source:s,reason});});
chrome.tabs.onUpdated.addListener(async(id,change,tab)=>{if(attached.has(id)&&tab.groupId!==group)await dropTab(id,'left Claude group');});
chrome.tabs.onRemoved.addListener(id=>{attached.delete(id);emit('check.tabClosed',{id});});
async function attach(tabId){
  if(!group){group=await chrome.tabs.group({tabIds:[tabId]});await chrome.tabGroups.update(group,{title:'Claude',color:'blue'});}else await chrome.tabs.group({groupId:group,tabIds:[tabId]});
  selected=tabId;const s={tabId};await chrome.debugger.attach(s,'1.3');attached.set(tabId,s);return {tabId,group};
}
async function rpc(m,p){
  if(m==='Check.config'){({mode='hold',backstop=false,texts=[],publicMode=false}=p);permit=null;return {mode,backstop};}
  if(m==='Check.state')return {selected,group,pending:[...pending.values()],history,errors,version:chrome.runtime.getManifest().version,rules:await chrome.declarativeNetRequest.getSessionRules()};
  if(m==='Check.decide')return decide(p.id,p.release);
  if(m==='Check.arm'){permit=p;return {};}
  if(m==='Check.targets')return chrome.debugger.getTargets();
  if(m==='Check.workerAttach'){const s={targetId:p.targetId};await chrome.debugger.attach(s,'1.3');attached.set(p.targetId,s);return command(s,'Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});}
  if(m==='Check.workerCommand')return command({targetId:p.targetId},p.method,p.params);
  if(m==='Check.attach')return attach(p.tabId);
  if(m==='Check.open'){const t=await chrome.tabs.create({url:p.url});await chrome.tabs.group({groupId:group,tabIds:[t.id]});return t;}
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
