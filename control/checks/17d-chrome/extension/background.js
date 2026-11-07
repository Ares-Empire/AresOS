// CHECK ONLY: trusted runner RPC, diagnostic delays and deliberately exposed originals.
let port,selected,group,gateMode='fail',delayMs=0,expected,autoClean=true,owner=false;
const history=[],attached=new Map(),pending=new Map();
const emit=(method,params)=>{const row={method,params,at:Date.now()};history.push(row);try{port?.postMessage({method,params,at:row.at})}catch{}};
const cmd=(s,m,p={})=>chrome.debugger.sendCommand(s,m,p);
const hash=async s=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',typeof s==='string'?new TextEncoder().encode(s):s))).map(v=>v.toString(16).padStart(2,'0')).join('');
async function body(r){return {hasPostData:r.hasPostData,postData:r.postData===undefined?{missing:true}:{missing:false,length:new TextEncoder().encode(r.postData).length,sha256:await hash(r.postData),preview:r.postData.slice(0,120),syntheticDiskFilePresent:r.postData.includes('SYNTHETIC_DISK_FILE_17D')},entries:r.postDataEntries?.map(e=>({bytesPresent:e.bytes!==undefined,base64Length:e.bytes?.length}))};}
const ready=(async()=>{
 const s=await chrome.storage.local.get('autoClean');autoClean=s.autoClean!==false;
 const rules=await chrome.declarativeNetRequest.getSessionRules();
 if(autoClean)await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:rules.filter(r=>r.id>=8000).map(r=>r.id)});
 await chrome.storage.local.set({lastStart:{at:Date.now(),autoClean,before:rules,after:await chrome.declarativeNetRequest.getSessionRules()}});
})();
async function floor({domains=[],tabId,clear=false}){
 const dnr=chrome.declarativeNetRequest;
 if(clear){await dnr.updateDynamicRules({removeRuleIds:(await dnr.getDynamicRules()).map(r=>r.id)});await dnr.updateSessionRules({removeRuleIds:(await dnr.getSessionRules()).map(r=>r.id)});return {};}
 const base=tabId?{tabIds:[tabId]}:{initiatorDomains:domains};
 const rules=[{id:tabId?201:101,priority:10,action:{type:'block'},condition:{...base,excludedRequestMethods:['get','head'],resourceTypes:['main_frame','sub_frame','stylesheet','script','image','font','object','xmlhttprequest','ping','csp_report','media','websocket','webtransport','webbundle','other']}},{id:tabId?202:102,priority:10,action:{type:'block'},condition:{...base,resourceTypes:['websocket','webtransport']}}];
 if(tabId)await dnr.updateSessionRules({removeRuleIds:[201,202],addRules:rules});
 else await dnr.updateDynamicRules({removeRuleIds:[101,102],addRules:rules});
 return rules;
}
async function attach(tabId){
 const tab=await chrome.tabs.get(tabId);if(!/^https?:/.test(tab.url))throw Error('FORBIDDEN_PAGE');
 selected=tabId;if(!group){group=await chrome.tabs.group({tabIds:[tabId]});await chrome.tabGroups.update(group,{title:'Claude',color:'blue'});}
 const s={tabId};if(!attached.has(tabId)){try{await chrome.debugger.attach(s,'1.3')}catch(e){if(!String(e).includes('already attached'))throw e;emit('check.recoveredDebugger',{tabId,error:String(e)})}attached.set(tabId,s);await cmd(s,'Runtime.enable');await cmd(s,'Page.enable');await cmd(s,'Network.enable',{maxPostDataSize:65536});await cmd(s,'Fetch.enable',{patterns:[{urlPattern:'*',requestStage:'Request'}]});emit('check.ready',{tabId,url:tab.url});}
 return {tabId,group};
}
async function gate(s,p){
 const r=p.request;
 if(!r.url.includes('/receive'))return cmd(s,'Fetch.continueRequest',{requestId:p.requestId});
 const seen={source:s,requestId:p.requestId,url:r.url,method:r.method,headers:r.headers,...await body(r),enteredAt:Date.now()};emit('check.gate',seen);
 if(gateMode==='park')return;
 const approval=expected;expected=undefined;
 if(delayMs)await new Promise(r=>setTimeout(r,delayMs));
 const match=approval&&approval.url===r.url&&approval.method===r.method&&r.postData!==undefined&&await hash(r.postData)===approval.sha256&&Object.entries(approval.headers||{}).every(([k,v])=>Object.entries(r.headers).some(([a,b])=>a.toLowerCase()===k.toLowerCase()&&b===v));
 // Remove on the first request-stage candidate, before checking or answering it.
 await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[8001]});
 emit('check.allowRemoved',{requestId:p.requestId,match:!!match,expected:approval});
 await cmd(s,gateMode==='pass'||match?'Fetch.continueRequest':'Fetch.failRequest',gateMode==='pass'||match?{requestId:p.requestId}:{requestId:p.requestId,errorReason:'Aborted'});
 emit('check.gateAnswered',{requestId:p.requestId,allowed:gateMode==='pass'||!!match,at:Date.now()});
}
chrome.debugger.onEvent.addListener((s,m,p)=>{
 if(m==='Fetch.requestPaused'){gate(s,p).catch(e=>emit('check.gateError',{error:String(e),source:s}));return;}
 if(m==='Network.requestWillBeSent'){
  if(p.request.url.includes('/receive'))(async()=>{emit(m,{source:s,requestId:p.requestId,url:p.request.url,method:p.request.method,...await body(p.request)});try{const data=await cmd(s,'Network.getRequestPostData',{requestId:p.requestId});emit('check.getPostData',{requestId:p.requestId,length:new TextEncoder().encode(data.postData).length,sha256:await hash(data.postData),preview:data.postData.slice(0,120),syntheticDiskFilePresent:data.postData.includes('SYNTHETIC_DISK_FILE_17D')});}catch(e){emit('check.getPostData',{requestId:p.requestId,missing:true,error:String(e)})}})();
 }else if(m==='Runtime.bindingCalled'&&p.name==='__report17'){emit('check.script',{source:s,...JSON.parse(p.payload)});}
 else if(/^(Storage\.|DOMStorage\.|ServiceWorker\.|BackgroundService\.)|WebSocket|webTransport|Network.loadingFailed/.test(m))emit(m,{source:s,...p});
});
chrome.debugger.onDetach.addListener((s,reason)=>{attached.delete(s.tabId||s.targetId);emit('check.detached',{source:s,reason})});
chrome.webRequest.onBeforeRequest.addListener(p=>{if(p.url.includes('/receive')||!['GET','HEAD'].includes(p.method)||p.type==='websocket'||p.type==='webtransport')emit('check.webRequest',{url:p.url,method:p.method,type:p.type,tabId:p.tabId,initiator:p.initiator,requestId:p.requestId,at:p.timeStamp});if(expected&&p.url===expected.url&&p.method===expected.method)chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[8001]}).then(()=>emit('check.firstMatchRemoved',{url:p.url,tabId:p.tabId,at:Date.now()}));},{urls:['<all_urls>']});
chrome.webRequest.onErrorOccurred.addListener(p=>{if(p.url.includes('/receive')||!['GET','HEAD'].includes(p.method))emit('check.webError',{url:p.url,method:p.method,error:p.error,tabId:p.tabId})},{urls:['<all_urls>']});
async function account(tabId){return {cookies:await cmd({tabId},'Network.getCookies',{}),page:(await cmd({tabId},'Runtime.evaluate',{expression:'document.querySelector("#account")?.textContent',returnByValue:true})).result.value};}
async function release(id){const p=pending.get(id);if(!p)throw Error('NOT_PENDING');pending.delete(id);if(JSON.stringify(await account(p.source.tabId))!==JSON.stringify(p.account))throw Error('ACCOUNT_CHANGED');await rpc('Check.allow',{url:p.description.url,method:p.description.method,sha256:p.description.sha256,headers:Object.fromEntries(p.description.headers),tabId:p.source.tabId});await chrome.scripting.executeScript({target:{tabId:p.source.tabId,documentIds:[p.source.documentId]},world:'MAIN',func:id=>{__floor.release(id).catch(()=>{});return true},args:[p.localId]});return {};}
async function rpc(m,p={}){
 await ready;
 if(m==='Check.state')return {selected,group,history,pending:[...pending.values()],manifest:chrome.runtime.getManifest(),dynamic:await chrome.declarativeNetRequest.getDynamicRules(),session:await chrome.declarativeNetRequest.getSessionRules(),startup:await chrome.storage.local.get('lastStart')};
 if(m==='Check.attach')return attach(p.tabId);
 if(m==='Check.floor')return floor(p);
 if(m==='Check.rules')return chrome.declarativeNetRequest.updateSessionRules(p);
 if(m==='Check.frameProbe')return chrome.scripting.executeScript({target:{tabId:selected,allFrames:true},world:'MAIN',func:()=>{if(location.hostname==='localhost')fetch('/receive?case=foreign-frame',{method:'POST',body:'synthetic foreign'}).catch(()=>{});return location.href;}});
 if(m==='Check.mode'){gateMode=p.mode||'fail';delayMs=p.delayMs||0;owner=!!p.owner;return {};}
 if(m==='Check.allow'){
  expected=p;const condition={resourceTypes:['main_frame','sub_frame','stylesheet','script','image','font','object','xmlhttprequest','ping','csp_report','media','websocket','webtransport','webbundle','other'],regexFilter:'^'+p.url.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'$',requestMethods:[p.method.toLowerCase()],...(p.site?{initiatorDomains:[p.site]}:{tabIds:[p.tabId||selected]})};
  const before=Date.now();await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[8001],addRules:[{id:8001,priority:100,action:{type:'allow'},condition}]});emit('check.allowAdded',{...p,before,after:Date.now()});return {before,after:Date.now()};
 }
 if(m==='Check.cleanup'){await chrome.storage.local.set({autoClean:p.enabled});return {};}
 if(m==='Check.clear'){history.length=0;return {};}
 if(m==='Check.targets')return chrome.debugger.getTargets();
 if(m==='Check.tabs')return chrome.tabs.query({});
 if(m==='Check.open')return chrome.tabs.create({url:p.url});
 if(m==='Check.closeTab')return chrome.tabs.remove(p.tabId);
 if(m==='Check.command')return cmd(p.source||{tabId:selected},p.method,p.params);
 if(m==='Check.workerAttach'){const s={targetId:p.targetId};await chrome.debugger.attach(s,'1.3');attached.set(p.targetId,s);await cmd(s,'Runtime.enable');await cmd(s,'Network.enable');return {};}
 if(m==='Check.detach'){for(const s of attached.values())await chrome.debugger.detach(s).catch(()=>{});attached.clear();return {};}
 if(m==='Check.reload'){setTimeout(()=>chrome.runtime.reload(),100);return {};}
 if(m==='Check.update')return new Promise(resolve=>chrome.runtime.requestUpdateCheck((status,details)=>resolve({status,details})));
 if(m==='Check.account')return account(selected);
 if(m==='Check.release')return release(p.id);
 return cmd({tabId:selected},m,p);
}
chrome.runtime.onMessage.addListener((m,s,reply)=>{
 (async()=>{
  if(m.attach&&s.id===chrome.runtime.id&&s.url?.split('?')[0]===chrome.runtime.getURL('select.html')&&s.frameId===0){await attach(m.attach);connect();return {};}
  if(m.report&&s.tab){
   emit('check.script',{...m.report,source:{tabId:s.tab.id,frameId:s.frameId,documentId:s.documentId}});
   if(m.report.event==='held'){const p={...m.report,id:s.documentId+':'+m.report.id,localId:m.report.id,source:{tabId:s.tab.id,documentId:s.documentId},account:await account(s.tab.id)};pending.set(p.id,p);if(owner)await chrome.notifications.create(p.id,{type:'basic',iconUrl:'icon.png',title:'Guarded fixture send',message:p.description.url,buttons:[{title:'Send'},{title:"Don't send"}],requireInteraction:true});}
   return {};
  }
  throw Error('UNTRUSTED_MESSAGE');
 })().then(v=>reply(v??{}),e=>reply({error:String(e)}));return true;
});
chrome.notifications.onButtonClicked.addListener((id,button)=>{emit('check.notificationButton',{id,button});if(button===0)release(id).catch(e=>emit('check.releaseError',{error:String(e)}));else pending.delete(id)});
chrome.runtime.onUpdateAvailable.addListener(()=>chrome.runtime.reload());
function connect(){port=chrome.runtime.connectNative('org.aresos.chrome_check');port.onMessage.addListener(c=>rpc(c.method,c.params).then(result=>port?.postMessage({id:c.id,result:result??{}}),e=>port?.postMessage({id:c.id,error:String(e)})));port.onDisconnect.addListener(()=>{port=undefined;emit('check.hostLost',{})});port.postMessage({method:'check.connected',params:{tabId:selected,group,version:chrome.runtime.getManifest().version}});}
