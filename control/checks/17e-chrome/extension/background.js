// Trusted CI diagnostic RPC. Never a product authorization endpoint.
let port, selected;
const browserGeneration=crypto.randomUUID(), documents=new Map(), attached=new Set();
const cmd=(method,params={})=>chrome.debugger.sendCommand({tabId:selected},method,params);
async function tag(tabId,documentId=crypto.randomUUID()){
 const value=browserGeneration+':'+documentId;
 await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:[tabId+1000],addRules:[{id:tabId+1000,priority:1000,action:{type:'modifyHeaders',requestHeaders:[{header:'x-ares-check',operation:'set',value}]},condition:{tabIds:[tabId],resourceTypes:['main_frame','sub_frame','stylesheet','script','image','font','object','xmlhttprequest','ping','csp_report','media','websocket','webtransport','webbundle','other']}}]});
 documents.set(tabId,{tabId,documentId,value});return value;
}
chrome.webNavigation.onCommitted.addListener(p=>{if(p.frameId===0)tag(p.tabId,p.documentId).catch(()=>{});});
async function attach(tabId){selected=tabId;if(!attached.has(tabId)){await chrome.debugger.attach({tabId},'1.3');attached.add(tabId);}await cmd('Runtime.enable');await cmd('Page.enable');await tag(tabId);return {tabId};}
async function rpc(m,p){
 if(m==='Check.state')return {selected,browserGeneration,documents:[...documents.values()],manifest:chrome.runtime.getManifest()};
 if(m==='Check.tag')return {token:await tag(selected,p.documentId)};
 if(m==='Check.untag'){await chrome.declarativeNetRequest.updateSessionRules({removeRuleIds:(await chrome.declarativeNetRequest.getSessionRules()).map(r=>r.id)});return {};}
 if(m==='Check.safety'){await chrome.declarativeNetRequest.updateDynamicRules({removeRuleIds:[1,2],addRules:p.clear?[]:[{id:1,priority:2000,action:{type:'block'},condition:{excludedRequestMethods:['get','head'],resourceTypes:['main_frame','sub_frame','stylesheet','script','image','font','object','xmlhttprequest','ping','csp_report','media','websocket','webtransport','webbundle','other']}},{id:2,priority:2000,action:{type:'block'},condition:{resourceTypes:['websocket','webtransport']}}]});return {};}
 if(m==='Check.reload'){setTimeout(()=>chrome.runtime.reload(),100);return {};}
 if(m==='Check.open')return chrome.tabs.create(p);
 if(m==='Check.attach')return attach(p.tabId);
 if(m==='Check.close')return chrome.tabs.remove(p.tabId||selected);
 if(m==='Check.targets')return chrome.debugger.getTargets();
 if(m==='Check.worker'){await chrome.debugger.attach({targetId:p.targetId},'1.3');return {};}
 if(m==='Check.command')return chrome.debugger.sendCommand(p.source,p.method,p.params||{});
 return cmd(m,p);
}
function connect(){port=chrome.runtime.connectNative('org.aresos.chrome_check');port.onMessage.addListener(c=>rpc(c.method,c.params||{}).then(result=>port?.postMessage({id:c.id,result:result??{}}),e=>port?.postMessage({id:c.id,error:String(e)})));port.onDisconnect.addListener(()=>{port=undefined});port.postMessage({method:'check.connected',params:{tabId:selected}});}
chrome.runtime.onMessage.addListener((m,s,reply)=>{if(m.attach&&s.id===chrome.runtime.id&&s.url?.split('?')[0]===chrome.runtime.getURL('select.html')){attach(m.attach).then(()=>{connect();reply({})},e=>reply({error:String(e)}));return true;}});
