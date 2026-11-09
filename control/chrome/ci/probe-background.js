// Disposable runner experiment, never included in the installed extension.
const report=value=>fetch('http://fixture.test:8765/report',{method:'POST',body:JSON.stringify(value)});
const command=(tabId,method,parameters={})=>chrome.debugger.sendCommand({tabId},method,parameters);
const privateTabs=new Set();
const contexts=new Map(),contextWaiters=new Map();
chrome.debugger.onEvent.addListener(async(source,method,params)=>{
  if(method==='Runtime.executionContextCreated'){
    await report({phase:'context',context:params.context});
    if(params.context.origin===chrome.runtime.getURL('').replace(/\/$/,'')){
      contexts.set(source.tabId,params.context);contextWaiters.get(source.tabId)?.(params.context);
    }
  }
  if(method!=='Debugger.paused'||!privateTabs.has(source.tabId))return;
  const started=Date.now();let timeout;
  try{
    const ready=new Promise(resolve=>{contextWaiters.set(source.tabId,resolve);});
    const injection=chrome.scripting.executeScript({target:{tabId:source.tabId},func:()=>{},injectImmediately:true});
    injection.catch(error=>report({phase:'late-injection-error',error:String(error)}));
    const context=await Promise.race([ready,new Promise((_,reject)=>{timeout=setTimeout(()=>reject(Error('No real extension world while paused')),5000);})]);
    clearTimeout(timeout);
    const evaluated=await command(source.tabId,'Runtime.evaluate',{contextId:context.id,expression:"globalThis.probePrivate=true;window.addEventListener('probe-event',event=>{event.preventDefault();event.stopImmediatePropagation();},true);JSON.stringify({runtime:chrome.runtime.id,closedShadowAPI:typeof chrome.dom.openOrClosedShadowRoot})",returnByValue:true});
    await report({phase:'private-extension-evaluation-before-resume',evaluated});
    const result='Extension world installed before page scripts';
    await report({phase:'isolated-before-resume',elapsed:Date.now()-started,result});
  }catch(error){await report({phase:'injection-error',error:String(error)});}
  finally{clearTimeout(timeout);await command(source.tabId,'Debugger.resume');}
});
(async()=>{
  await report({phase:'ready'});
  const tab=await chrome.tabs.create({url:'about:blank'});privateTabs.add(tab.id);
  await chrome.debugger.attach({tabId:tab.id},'1.3');
  await command(tab.id,'Page.enable');await command(tab.id,'Debugger.enable');await command(tab.id,'Runtime.enable');
  await command(tab.id,'Page.addScriptToEvaluateOnNewDocument',{source:'debugger;'});
  await command(tab.id,'Page.navigate',{url:'http://fixture.test:8765/page'});
})().catch(error=>report({phase:'error',error:String(error)}));
